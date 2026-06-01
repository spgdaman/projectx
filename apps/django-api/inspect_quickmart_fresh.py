"""
Step-by-step Quickmart investigation starting from scratch.
Finds the branch selector entry point on the homepage.
"""
import sys, io, re, time, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

UA   = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

def ts(): return time.strftime('%H:%M:%S')

api_calls = []
def on_response(resp):
    ct  = resp.headers.get('content-type', '')
    url = resp.url
    rt  = resp.request.resource_type
    if rt in ('xhr','fetch') or ('json' in ct and 'google' not in url and 'cdn-cgi' not in url):
        try:
            body = resp.body()
            if len(body) > 30:
                api_calls.append({'url': url, 'status': resp.status,
                                  'body': body[:500].decode('utf-8','replace')})
        except Exception:
            pass

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(user_agent=UA, viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()
    page.on('response', on_response)

    # ─── Try homepage first — see branch selector ─────────────────────────
    print(f"[{ts()}] Loading homepage...")
    page.goto('https://www.quickmart.co.ke', wait_until='domcontentloaded', timeout=30_000)
    page.wait_for_timeout(3000)
    print(f"[{ts()}] Title: {page.title()!r}")

    # Look for branch selector / "Change Branch" button on homepage
    print(f"\n[{ts()}] Looking for branch selector on homepage...")
    for sel in [
        '[class*="branch"]', '[class*="shop-select"]', '[class*="location"]',
        '#changeShop', '.change-branch', '[class*="changeBranch"]',
        'button[class*="shop"]', '[id*="shop"]',
        '[class*="selectShop"]', '.header-shop',
    ]:
        els = page.query_selector_all(sel)
        if els:
            txt = (els[0].inner_text() or '')[:50].replace('\n',' ')
            cls = (els[0].get_attribute('class') or '')[:50]
            print(f"  {sel!r}: {len(els)}  cls={cls!r}  txt={txt!r}")

    # Intercept API calls fired on homepage
    print(f"\n[{ts()}] API calls from homepage: {len(api_calls)}")
    for c in api_calls:
        print(f"  [{c['status']}] {c['url'][:100]}")
    api_calls.clear()

    # ─── Try /5301 as seed — the ONLY known working start point ──────────
    print(f"\n[{ts()}] ─── Seeding session via /5301 ───")
    page.goto('https://www.quickmart.co.ke/5301', wait_until='domcontentloaded', timeout=30_000)
    page.wait_for_timeout(3000)
    print(f"[{ts()}] Title: {page.title()!r}  url: {page.url!r}")

    # Popup
    for sel in ['//button[contains(text(),"Continue")]','//button[contains(text(),"Yes")]']:
        try:
            btn = page.wait_for_selector(sel, timeout=5_000)
            txt = btn.inner_text().strip()
            print(f"[{ts()}] Popup: {txt!r} → clicking")
            btn.click(); page.wait_for_timeout(2000)
            print(f"[{ts()}] After click: {page.url!r}  title={page.title()!r}")
            break
        except: pass

    # ─── Now go to /shops ─────────────────────────────────────────────────
    print(f"\n[{ts()}] ─── /shops after session seed ───")
    page.goto('https://www.quickmart.co.ke/shops', wait_until='domcontentloaded', timeout=30_000)
    page.wait_for_timeout(2500)
    print(f"[{ts()}] Title: {page.title()!r}")

    # Click all-shops
    for sel in ['#all-shops', 'a#all-shops', 'button#all-shops']:
        el = page.query_selector(sel)
        if el:
            el.click(); page.wait_for_timeout(2500); print(f"[{ts()}] Clicked {sel!r}"); break

    # Load More
    clicks = 0
    while True:
        lm = page.query_selector('#loadMoreBtn')
        if not lm or not lm.is_visible(): break
        lm.click(); page.wait_for_timeout(2000); clicks += 1

    anchors = page.query_selector_all('a.products.product-item')
    print(f"[{ts()}] Load More ×{clicks}  →  {len(anchors)} branches")

    # Extract branch name + URL
    branches = []
    for a in anchors:
        href    = a.get_attribute('href') or ''
        onclick = a.get_attribute('onclick') or ''
        m       = re.search(r'switch to (.+?)\s*\?', onclick, re.I)
        name    = m.group(1).strip() if m else href.strip('/').split('/')[-1]
        if href:
            url = f"https://www.quickmart.co.ke{href}" if href.startswith('/') else href
            branches.append({'name': name, 'url': url})

    print(f"\n{'Branch':<40}  URL")
    print(f"{'─'*70}")
    for b in branches[:15]:
        print(f"  {b['name']:<40}  {b['url']}")
    if len(branches) > 15:
        print(f"  ... and {len(branches)-15} more")

    if not branches:
        print("No branches found"); browser.close(); exit(1)

    # ─── STEP 2: Switch to second branch ─────────────────────────────────
    print(f"\n[{ts()}] ─── STEP 2: Switch to branch '{branches[1]['name']}' ───")
    page.goto(branches[1]['url'], wait_until='domcontentloaded', timeout=30_000)
    page.wait_for_timeout(3000)
    print(f"[{ts()}] Title: {page.title()!r}  url: {page.url!r}")

    # Confirm popup
    for sel in ['//button[contains(text(),"Continue")]','//button[contains(text(),"Yes")]',
                '//button[contains(text(),"Switch")]']:
        try:
            btn = page.wait_for_selector(sel, timeout=5_000)
            print(f"[{ts()}] Popup: {btn.inner_text().strip()!r}")
            btn.click(); page.wait_for_timeout(2500)
            print(f"[{ts()}] After switch: {page.url!r}")
            break
        except: pass

    # ─── STEP 3: Categories via hamburger hover ───────────────────────────
    print(f"\n[{ts()}] ─── STEP 3: Categories ───")

    # Click hamburger
    for sel in ['button.navigation-link.hamburger-categories', 'button.categoriesMenuJs',
                '.hamburger-categories']:
        el = page.query_selector(sel)
        if el and el.is_enabled():
            el.click(); page.wait_for_timeout(1500)
            print(f"[{ts()}] Opened categories via {sel!r}")
            break

    # Navigate to full category listing
    last_cat_link = None
    for sel in ['ul.category-menu.categoryListJs.activeJs li:last-child a',
                'ul.categoryListJs.activeJs li:last-child a']:
        el = page.query_selector(sel)
        if el:
            last_cat_link = el.get_attribute('href') or ''
            break

    categories = []
    if last_cat_link:
        full = f"https://www.quickmart.co.ke{last_cat_link}" if last_cat_link.startswith('/') else last_cat_link
        page.goto(full, wait_until='domcontentloaded', timeout=20_000)
        page.wait_for_timeout(2000)
        print(f"[{ts()}] Category listing: {page.title()!r}")

        items = page.query_selector_all('div.categories-listing-item')
        for item in items:
            anchor = item.query_selector('h4 a, h3 a')
            if not anchor: continue
            cat_name = anchor.inner_text().strip()
            cat_href = anchor.get_attribute('href') or ''
            subs = []
            for sub in item.query_selector_all('ul li a'):
                sn = sub.inner_text().strip()
                sh = sub.get_attribute('href') or ''
                if sn and sh:
                    full_sh = f"https://www.quickmart.co.ke{sh}" if sh.startswith('/') else sh
                    subs.append({'name': sn, 'url': full_sh})
            if not subs and cat_href:
                full_ch = f"https://www.quickmart.co.ke{cat_href}" if cat_href.startswith('/') else cat_href
                subs = [{'name': cat_name, 'url': full_ch}]
            categories.append({'category': cat_name, 'subs': subs})
            print(f"  {cat_name}  ({len(subs)} subs)")
            for s in subs[:3]:
                print(f"      {s['name']:<30}  {s['url']}")

    total_subs = sum(len(c['subs']) for c in categories)
    print(f"\n[{ts()}] {len(categories)} categories, {total_subs} subcategories")

    # ─── STEP 4: Products from first subcategory + verify URL ─────────────
    print(f"\n[{ts()}] ─── STEP 4: Products from first subcategory ───")
    all_subs = [s for c in categories for s in c['subs']]
    if not all_subs:
        print("No subcategories"); browser.close(); exit(1)

    sub = all_subs[0]
    print(f"[{ts()}] Subcategory: {sub['name']}  →  {sub['url']}")

    page.goto(sub['url'], wait_until='domcontentloaded', timeout=20_000)
    page.wait_for_timeout(2500)
    print(f"[{ts()}] Title: {page.title()!r}  url: {page.url!r}")

    products = []
    cards = page.query_selector_all('div.products.productInfoJs')
    print(f"[{ts()}] {len(cards)} product cards on page 1")
    for card in cards[:5]:
        name_el = card.query_selector('a.products-title')
        if not name_el: continue
        name  = name_el.inner_text().strip()
        href  = name_el.get_attribute('href') or ''
        full  = f"https://www.quickmart.co.ke{href}" if href.startswith('/') else href
        price = (card.query_selector('span.products-price-new') or card.query_selector('[class*="price"]'))
        price_txt = price.inner_text().strip() if price else ''
        print(f"  {name[:50]:<52}  {price_txt:<15}  url={full}")
        products.append({'name': name, 'url': full, 'price': price_txt})

    # Verify product URL
    if products:
        test_url = products[0]['url']
        print(f"\n[{ts()}] Verifying product URL: {test_url}")
        r = page.goto(test_url, wait_until='domcontentloaded', timeout=15_000)
        page.wait_for_timeout(1500)
        print(f"[{ts()}] HTTP {r.status}  Title: {page.title()!r}  Final URL: {page.url!r}")

    browser.close()
    print(f"\n[{ts()}] DONE")
