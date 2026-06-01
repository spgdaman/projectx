"""
Quickmart scraper — correct 4-step flow with parallel subcategory workers.

Step 1  Get all branches  (/shops + Load More until exhausted)
Step 2  Per branch: seed session + switch branch → extract cookies once
Step 3  Get categories via hamburger menu → /category listing → all subcategory URLs
Step 4  Spawn N workers; each injects branch cookies + scrapes subcategory paginated

Cookie injection means workers skip the 20s seed/popup overhead entirely.
Writes to StagingProduct via Django ORM. Redis gates duplicate prices.

Usage:
  python quickmart_scraper.py                       # all branches, 5 workers
  python quickmart_scraper.py --branches 2          # first 2 branches only
  python quickmart_scraper.py --branches 2 --workers 10
  python quickmart_scraper.py --workers 5 --normalize
"""
import sys, io, os, re, time, argparse, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from decimal import Decimal

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalogue.settings')
import django; django.setup()

from django.db import connection
from core.models import StagingProduct, RetailerBranch
import scrapers.base as _base
# Patch Redis for price-change gate
import redis as _redis_mod
_redis_client = _redis_mod.from_url(
    getattr(__import__('django').conf.settings, 'REDIS_URL', 'redis://localhost:6379/1'),
    decode_responses=True,
)

from playwright.sync_api import sync_playwright

# ── Config ────────────────────────────────────────────────────────────────── #
UA   = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
BASE = 'https://www.quickmart.co.ke'
SEED = f'{BASE}/5301'   # any working branch to seed the session cookie

parser = argparse.ArgumentParser()
parser.add_argument('--branches',  type=int, default=None, help='Max branches (default: all)')
parser.add_argument('--workers',   type=int, default=5,    help='Parallel workers per branch (default: 5)')
parser.add_argument('--normalize', action='store_true',    help='Run normalize_staging after scraping')
args = parser.parse_args()

lock = __import__('threading').Lock()

def ts(): return datetime.now().strftime('%H:%M:%S')
def log(msg):
    with lock: print(f"[{ts()}] {msg}", flush=True)


# ── Playwright helpers ────────────────────────────────────────────────────── #

def new_browser(p):
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        user_agent=UA,
        viewport={'width': 1280, 'height': 900},
    )
    # Block heavy assets — speeds up page loads significantly
    ctx.route('**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,otf,mp4,mp3}',
              lambda r: r.abort())
    return browser, ctx


def dismiss_popup(page, timeout=5_000):
    for sel in ['//button[contains(text(),"Continue")]',
                '//button[contains(text(),"Yes")]',
                '//button[contains(text(),"Switch")]']:
        try:
            btn = page.wait_for_selector(sel, timeout=timeout)
            btn.click()
            page.wait_for_timeout(1500)
            return True
        except Exception:
            pass
    return False


def clear_overlays(page):
    """
    Remove any UI overlays that block clicks:
      - #shopPopupJs  branch-switch modal (appears even with cookies set)
      - .cookies-notice-js  cookie consent banner
    Uses JavaScript removal so we never try to click through them.
    """
    try:
        page.evaluate("""() => {
            // Branch-switch modal
            const modal = document.getElementById('shopPopupJs');
            if (modal) {
                modal.classList.remove('show');
                modal.style.display = 'none';
            }
            // Bootstrap backdrop
            document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            // Cookie notice
            document.querySelectorAll('.cookies-notice-js, .cookies-mobile').forEach(el => el.style.display = 'none');
        }""")
        page.wait_for_timeout(200)
    except Exception:
        pass


# ── STEP 1: Get all branches ─────────────────────────────────────────────── #

def get_all_branches(page) -> list[dict]:
    """Navigate /shops, click Load More until done, return all branch dicts."""
    log("STEP 1 — Loading /shops...")
    t0 = time.time()

    # First seed session so /shops renders properly
    page.goto(SEED, wait_until='domcontentloaded', timeout=30_000)
    page.wait_for_timeout(2500)
    dismiss_popup(page)

    page.goto(f'{BASE}/shops', wait_until='domcontentloaded', timeout=30_000)
    page.wait_for_timeout(2000)

    # Dismiss cookie consent banner if present (it blocks clicks)
    try:
        cookie_btn = page.query_selector('button.cc-cookie-accept-js, .cc-cookie-accept-js, [class*="cookie-accept"]')
        if cookie_btn:
            cookie_btn.click()
            page.wait_for_timeout(1000)
    except Exception:
        pass
    # Also hide via JS as a fallback
    page.evaluate("() => { const el = document.querySelector('.cookies-notice-js,.cookies-mobile'); if(el) el.style.display='none'; }")

    # Click "All branches" tab
    for sel in ['#all-shops', 'a#all-shops']:
        el = page.query_selector(sel)
        if el: el.click(); page.wait_for_timeout(2500); break

    # Click Load More until gone — use JS click to avoid overlay issues
    clicks = 0
    while True:
        lm = page.query_selector('#loadMoreBtn')
        if not lm or not lm.is_visible(): break
        try:
            page.evaluate('el => el.click()', lm)
            page.wait_for_timeout(2000)
            clicks += 1
        except Exception:
            break

    anchors = page.query_selector_all('a.products.product-item')
    branches = []
    for a in anchors:
        href    = a.get_attribute('href') or ''
        onclick = a.get_attribute('onclick') or ''
        m       = re.search(r'switch to (.+?)\s*\?', onclick, re.I)
        name    = m.group(1).strip() if m else href.strip('/').split('/')[-1]
        if href:
            url = f"{BASE}{href}" if href.startswith('/') else href
            branches.append({'name': name, 'url': url, 'slug': href.strip('/')})

    log(f"STEP 1 — {len(branches)} branches found  (Load More ×{clicks}, {time.time()-t0:.1f}s)")
    return branches


# ── STEP 2: Set branch context, extract cookies ───────────────────────────── #

def get_branch_cookies(page, branch: dict) -> list[dict]:
    """Switch to branch via its URL, confirm popup, return cookies."""
    log(f"  STEP 2 — Switching to '{branch['name']}'")
    page.goto(branch['url'], wait_until='domcontentloaded', timeout=30_000)
    page.wait_for_timeout(2500)
    popup = dismiss_popup(page)
    log(f"  STEP 2 — Popup {'confirmed' if popup else 'not shown'}  url={page.url!r}")
    cookies = page.context.cookies()
    return cookies


# ── STEP 3: Get categories and subcategory URLs ───────────────────────────── #

def get_categories(page, branch: dict) -> list[dict]:
    """
    Clicks hamburger → navigates to /category listing →
    returns [{'category': str, 'sub_category': str, 'url': str}, ...]
    """
    log(f"  STEP 3 — Getting categories for '{branch['name']}'")
    t0 = time.time()

    # Go home (branch already set in page context)
    page.goto(f'{BASE}/home', wait_until='domcontentloaded', timeout=20_000)
    page.wait_for_timeout(1500)

    # Open hamburger categories menu
    for sel in ['button.navigation-link.hamburger-categories',
                'button.categoriesMenuJs', '.hamburger-categories']:
        el = page.query_selector(sel)
        if el and el.is_enabled():
            el.click(); page.wait_for_timeout(1500); break

    # Navigate to full category listing (last link in the open menu)
    cat_listing_href = ''
    for sel in ['ul.category-menu.categoryListJs.activeJs li:last-child a',
                'ul.categoryListJs.activeJs li:last-child a']:
        el = page.query_selector(sel)
        if el: cat_listing_href = el.get_attribute('href') or ''; break

    if not cat_listing_href:
        log(f"  STEP 3 — No category listing link found")
        return []

    full = f"{BASE}{cat_listing_href}" if cat_listing_href.startswith('/') else cat_listing_href
    page.goto(full, wait_until='domcontentloaded', timeout=20_000)
    page.wait_for_timeout(1500)

    categories = []
    items = page.query_selector_all('div.categories-listing-item')
    for item in items:
        anchor = item.query_selector('h4 a, h3 a')
        if not anchor: continue
        cat_name = anchor.inner_text().strip()
        cat_href = anchor.get_attribute('href') or ''

        sub_links = item.query_selector_all('ul li a')
        if sub_links:
            for sub in sub_links:
                sn = sub.inner_text().strip()
                sh = sub.get_attribute('href') or ''
                if sn and sh:
                    categories.append({
                        'category':     cat_name,
                        'sub_category': sn,
                        'url':          f"{BASE}{sh}" if sh.startswith('/') else sh,
                    })
        elif cat_href:
            categories.append({
                'category':     cat_name,
                'sub_category': cat_name,
                'url':          f"{BASE}{cat_href}" if cat_href.startswith('/') else cat_href,
            })

    log(f"  STEP 3 — {len(categories)} subcategories  ({time.time()-t0:.1f}s)")
    return categories


# ── STEP 4: Scrape one subcategory (run by a worker thread) ──────────────── #

def scrape_subcategory(branch_name: str, cat: dict, cookies: list[dict]) -> dict:
    """
    Worker function. Injects branch cookies → scrapes subcategory page by page.
    Returns {'sub': str, 'products': int, 'written': int, 'pages': int, 'secs': float}
    """
    t0 = time.time()
    products_found = []
    pages = 0

    with sync_playwright() as p:
        browser, ctx = new_browser(p)
        ctx.add_cookies(cookies)   # inject branch session — no seed/popup needed
        page = ctx.new_page()

        try:
            page.goto(cat['url'], wait_until='domcontentloaded', timeout=20_000)
            page.wait_for_timeout(2000)
            clear_overlays(page)   # dismiss any branch popup on initial load

            while True:
                cards = page.query_selector_all('div.products.productInfoJs')
                if not cards: break
                pages += 1

                for card in cards:
                    item = _parse_card(card, branch_name, cat)
                    if item: products_found.append(item)

                # Dismiss modal before attempting pagination
                clear_overlays(page)

                nxt = page.query_selector('li.next button, li.forward button')
                if not nxt or not nxt.is_enabled(): break
                page.evaluate('el => el.scrollIntoView({block:"center"})', nxt)
                nxt.click()
                page.wait_for_timeout(2500)
                clear_overlays(page)   # modal may reappear after navigation

        except Exception as e:
            log(f"  [worker] {branch_name}/{cat['sub_category']}: {e}")
        finally:
            browser.close()

    written = _write_to_staging(products_found, branch_name)
    elapsed = round(time.time() - t0, 1)

    log(f"    ✓ {branch_name} / {cat['sub_category']:<35} "
        f"pages={pages} found={len(products_found)} written={written} ({elapsed}s)")

    connection.close()   # release thread's DB connection
    return {
        'sub':      cat['sub_category'],
        'category': cat['category'],
        'products': len(products_found),
        'written':  written,
        'pages':    pages,
        'secs':     elapsed,
    }


def _parse_card(card, branch_name: str, cat: dict) -> dict | None:
    try:
        name_el = card.query_selector('a.products-title')
        if not name_el: return None

        name  = name_el.inner_text().strip()
        href  = name_el.get_attribute('href') or ''
        url   = f"{BASE}{href}" if href.startswith('/') else href

        price_el = card.query_selector('span.products-price-new')
        old_el   = card.query_selector('del.products-price-old')
        img_el   = card.query_selector('div.products-img img, img')

        price_txt = price_el.inner_text().strip() if price_el else ''
        old_txt   = old_el.inner_text().strip()   if old_el   else ''
        img_src   = img_el.get_attribute('src')   if img_el   else ''
        if img_src and img_src.startswith('/'):
            img_src = f'{BASE}{img_src}'

        def parse_price(raw):
            digits = re.sub(r'[^\d.]', '', raw.replace(',', ''))
            return Decimal(digits) if digits else None

        price = parse_price(price_txt)
        if not name or not price: return None

        return {
            'product_name':      name,
            'retailer_name':     'Quickmart',
            'branch_name':       branch_name,
            'category_name':     cat['category'],
            'sub_category_name': cat['sub_category'],
            'product_url':       url,
            'image_url':         img_src or None,
            'price':             price,
            'old_price':         parse_price(old_txt),
            'external_id':       url.rstrip('/').split('/')[-1] or name,
        }
    except Exception:
        return None


def _write_to_staging(items: list, branch_name: str) -> int:
    from django.utils import timezone
    written = 0
    for item in items:
        ext_id = item['external_id']
        price  = item['price']

        # Redis price-change gate
        cache_key = f"price:Quickmart:{branch_name}:{ext_id}"
        cached    = _redis_client.get(cache_key)
        _redis_client.set(cache_key, str(price), ex=7 * 86400)
        if cached and Decimal(cached) == price:
            continue   # price unchanged — skip DB write

        qs    = StagingProduct.objects.filter(
            retailer_name=item['retailer_name'],
            branch_name=item['branch_name'],
            product_name=item['product_name'],
        )
        count = qs.count()
        defaults = {
            'category_name':       item.get('category_name'),
            'sub_category_name':   item.get('sub_category_name'),
            'product_url':         item.get('product_url'),
            'image_url':           item.get('image_url'),
            'price':               price,
            'old_price':           item.get('old_price'),
            'source':              'scraper',
            'is_manual':           False,
            'scraped_at':          timezone.now(),
        }
        if count > 1:
            qs.exclude(pk=qs.first().pk).delete()
            qs.update(**defaults)
        elif count == 1:
            qs.update(**defaults)
        else:
            StagingProduct.objects.create(
                retailer_name=item['retailer_name'],
                branch_name=item['branch_name'],
                product_name=item['product_name'],
                **defaults,
            )
        written += 1
    return written


# ── Main ─────────────────────────────────────────────────────────────────── #

def scrape_branch(branch: dict, workers: int) -> dict:
    """Full scrape of one branch. Returns timing + count metrics."""
    t_branch = time.time()
    log(f"\n{'═'*65}")
    log(f"Branch: {branch['name']}  ({branch['url']})")
    log(f"{'═'*65}")

    with sync_playwright() as p:
        browser, ctx = new_browser(p)
        page = ctx.new_page()

        # Seed session (needed once per branch discovery context)
        page.goto(SEED, wait_until='domcontentloaded', timeout=30_000)
        page.wait_for_timeout(2000)
        dismiss_popup(page)

        # Switch to target branch and get cookies
        cookies    = get_branch_cookies(page, branch)
        categories = get_categories(page, branch)
        browser.close()

    if not categories:
        log(f"  No categories — skipping {branch['name']}")
        return {'branch': branch['name'], 'subs': 0, 'products': 0, 'written': 0,
                'workers': workers, 'secs': 0, 'sub_results': []}

    log(f"  Spawning {workers} workers for {len(categories)} subcategories...")
    t_scrape = time.time()
    sub_results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(scrape_subcategory, branch['name'], cat, cookies): cat
            for cat in categories
        }
        for future in as_completed(futures):
            try:
                sub_results.append(future.result())
            except Exception as e:
                cat = futures[future]
                log(f"  ✗ {cat['sub_category']}: {e}")

    elapsed      = round(time.time() - t_branch, 1)
    scrape_secs  = round(time.time() - t_scrape, 1)
    total_found  = sum(r['products'] for r in sub_results)
    total_written = sum(r['written']  for r in sub_results)
    total_pages  = sum(r['pages']    for r in sub_results)

    log(f"\n  ── Branch '{branch['name']}' summary ──")
    log(f"  Subcategories : {len(sub_results)}")
    log(f"  Total pages   : {total_pages}")
    log(f"  Products found: {total_found:,}")
    log(f"  Written to DB : {total_written:,}")
    log(f"  Workers       : {workers}")
    log(f"  Scrape time   : {scrape_secs:.0f}s  (branch total: {elapsed:.0f}s)")
    log(f"  Throughput    : {total_found / max(scrape_secs,1):.1f} products/sec")

    return {
        'branch':      branch['name'],
        'subs':        len(sub_results),
        'pages':       total_pages,
        'products':    total_found,
        'written':     total_written,
        'workers':     workers,
        'secs':        elapsed,
        'scrape_secs': scrape_secs,
        'sub_results': sub_results,
    }


if __name__ == '__main__':
    t_total = time.time()
    log(f"{'═'*65}")
    log(f"  Quickmart Parallel Scraper — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"  Workers per branch: {args.workers}")
    log(f"{'═'*65}")

    # ── Step 1: discover all branches ──────────────────────────────────────
    with sync_playwright() as p:
        browser, ctx = new_browser(p)
        pg = ctx.new_page()
        all_branches = get_all_branches(pg)
        browser.close()

    if args.branches:
        all_branches = all_branches[:args.branches]

    log(f"\nScraping {len(all_branches)} branch(es) with {args.workers} workers each\n")

    branch_results = []
    for branch in all_branches:
        result = scrape_branch(branch, args.workers)
        branch_results.append(result)

    # ── Final summary ───────────────────────────────────────────────────────
    elapsed_total = round(time.time() - t_total)
    total_products = sum(r['products'] for r in branch_results)
    total_written  = sum(r['written']  for r in branch_results)
    total_pages    = sum(r['pages']    for r in branch_results)

    log(f"\n{'═'*65}")
    log(f"  FINAL SUMMARY")
    log(f"{'═'*65}")
    log(f"  {'Branch':<40} {'Subs':>5} {'Pages':>6} {'Found':>8} {'Written':>8} {'Time':>6}")
    log(f"  {'─'*63}")
    for r in branch_results:
        log(f"  {r['branch']:<40} {r['subs']:>5} {r.get('pages',0):>6} "
            f"{r['products']:>8,} {r['written']:>8,} {r['secs']:>5.0f}s")
    log(f"  {'─'*63}")
    log(f"  {'TOTAL':<40} {sum(r['subs'] for r in branch_results):>5} "
        f"{total_pages:>6} {total_products:>8,} {total_written:>8,} {elapsed_total:>5}s")
    log(f"\n  StagingProduct (Quickmart): "
        f"{StagingProduct.objects.filter(retailer_name='Quickmart').count():,} rows")

    if args.normalize:
        log(f"\n{'═'*65}")
        log(f"  Running normalize_staging --all...")
        import subprocess
        r = subprocess.run(
            [sys.executable, 'manage.py', 'normalize_staging', '--all'],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        log(r.stdout[-500:] if r.stdout else '')
        if r.returncode != 0:
            log(f"Error: {r.stderr[-300:]}")
