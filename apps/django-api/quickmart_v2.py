"""
Quickmart Scraper v2 — standalone, no Django dependency.

Step 1  /shops → click Load More until exhausted → collect all branch URLs
Step 2  Navigate to branch URL → confirm popup → branch cookie set → redirect to home
Step 3  Open hamburger menu → hover each top-level category → collect subcategory links
Step 4  ThreadPoolExecutor workers: inject branch cookies → scrape each subcategory
        page-by-page until pagination ends

Outputs (inside quickmart_output/):
  branches.csv                  — all discovered branches
  categories_<branch>.csv       — subcategory list per branch
  products_<branch>.csv         — products per branch
  run_summary.json              — timing + count metrics

Usage:
  python quickmart_v2.py                        # 2 branches (default), 5 workers
  python quickmart_v2.py --branches 5           # first 5 branches
  python quickmart_v2.py --branches 2 --workers 8
  python quickmart_v2.py --all --workers 10     # every branch
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

# ── Config ────────────────────────────────────────────────────────────────── #

BASE = "https://www.quickmart.co.ke"
SEED = f"{BASE}/5301"   # any known branch slug to seed session cookie
OUT  = Path("quickmart_output")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_lock = threading.Lock()

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def ts():
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str):
    with _lock:
        print(f"[{ts()}] {msg}", flush=True)


# ── Browser factory ───────────────────────────────────────────────────────── #

def _new_context(p, headless: bool = True):
    browser = p.chromium.launch(headless=headless)
    ctx = browser.new_context(
        user_agent=UA,
        viewport={"width": 1280, "height": 900},
    )
    # Block heavy assets to speed up page loads
    ctx.route(
        "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,otf,mp4,mp3}",
        lambda r: r.abort(),
    )
    return browser, ctx


# ── Overlay / popup helpers ───────────────────────────────────────────────── #

def _try_dismiss_popup(page, timeout_ms: int = 5_000) -> bool:
    """Click any branch-switch / cookie confirmation popup. Returns True if found."""
    for sel in [
        '//button[contains(text(),"Continue")]',
        '//button[contains(text(),"Switch")]',
        '//button[contains(text(),"Yes")]',
        '//a[contains(text(),"Continue")]',
    ]:
        try:
            btn = page.wait_for_selector(sel, timeout=timeout_ms)
            if btn:
                btn.click()
                page.wait_for_timeout(1_500)
                return True
        except Exception:
            pass
    return False


def _clear_overlays(page):
    """
    JS-remove all known overlays so clicks aren't intercepted:
      - #shopPopupJs      branch-switch modal
      - #consentPopupJs   promotions / consent modal (with image)
      - .modal-backdrop   Bootstrap backdrop
      - .cookies-notice-js / .cookies-mobile  cookie banner
      - .processing.loaderJs   page-load spinner overlay
    """
    try:
        page.evaluate("""() => {
            ['shopPopupJs', 'consentPopupJs'].forEach(id => {
                const el = document.getElementById(id);
                if (el) { el.classList.remove('show'); el.style.display = 'none'; }
            });
            document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.querySelectorAll(
                '.cookies-notice-js, .cookies-mobile, [class*="cookie-notice"]'
            ).forEach(el => el.style.display = 'none');
        }""")
        page.wait_for_timeout(200)
    except Exception:
        pass


def _wait_for_page_ready(page, timeout_ms: int = 10_000):
    """Wait until the .processing.loaderJs spinner disappears (page has settled)."""
    try:
        page.wait_for_selector(".processing.loaderJs", state="hidden", timeout=timeout_ms)
    except Exception:
        pass  # spinner may not exist on this page


# ════════════════════════════════════════════════════════════════════════════ #
#  STEP 1 — Discover all branches                                             #
# ════════════════════════════════════════════════════════════════════════════ #

def step1_get_branches(page) -> list[dict]:
    """
    1. Seed session via SEED url (establishes required cookie)
    2. Navigate to /shops
    3. Click "All branches" tab
    4. Click Load More until the button disappears
    5. Extract all branch anchor tags
    """
    log("STEP 1 ─ Discovering branches from /shops ...")
    t0 = time.time()

    # Seed session cookie
    page.goto(SEED, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(2_500)
    _try_dismiss_popup(page)

    # Navigate to shops page
    page.goto(f"{BASE}/shops", wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(2_000)

    # Hide cookie banner so it doesn't block clicks
    try:
        page.evaluate(
            "() => { document.querySelectorAll('.cookies-notice-js,.cookies-mobile')"
            ".forEach(el => el.style.display='none'); }"
        )
    except Exception:
        pass

    # Click "All branches" tab (shows every branch, not just nearby)
    # Use regular click — JS click doesn't fire the event handlers this tab needs.
    all_shops_clicked = False
    for sel in ["#all-shops", "a#all-shops", "button#all-shops"]:
        try:
            el = page.wait_for_selector(sel, timeout=10_000)
            if el:
                el.click()                 # must be regular click (fires mousedown etc.)
                page.wait_for_timeout(3_000)
                all_shops_clicked = True
                break
        except Exception:
            continue

    if not all_shops_clicked:
        log("  ⚠ #all-shops tab not found — showing default (nearby) branches only")

    # Click Load More until it disappears
    clicks = 0
    while True:
        lm = page.query_selector("#loadMoreBtn")
        if not lm or not lm.is_visible():
            break
        try:
            page.evaluate("el => el.click()", lm)
            page.wait_for_timeout(2_000)
            clicks += 1
            log(f"  Load More ×{clicks} ...")
        except Exception:
            break

    # Parse branch anchors
    anchors = page.query_selector_all("a.products.product-item")
    branches: list[dict] = []
    for a in anchors:
        href    = a.get_attribute("href") or ""
        onclick = a.get_attribute("onclick") or ""
        m       = re.search(r"switch to (.+?)\s*\?", onclick, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
        else:
            # Fallback: humanise slug from href
            slug = href.strip("/").split("/")[-1]
            name = re.sub(r"[-_]", " ", slug).title()

        if href:
            url = f"{BASE}{href}" if href.startswith("/") else href
            branches.append({"name": name, "url": url, "slug": href.strip("/")})

    elapsed = round(time.time() - t0, 1)
    log(f"STEP 1 ─ {len(branches)} branches found  (Load More ×{clicks}, {elapsed}s)")
    return branches


# ════════════════════════════════════════════════════════════════════════════ #
#  STEP 2 — Switch branch, extract cookies                                    #
# ════════════════════════════════════════════════════════════════════════════ #

def step2_switch_branch(page, branch: dict) -> list[dict]:
    """
    Navigate to branch URL → popup appears asking to switch branch →
    confirm it → browser redirects to home page with branch cookie set.
    Returns the cookies so workers can inject them (skipping seed+popup).
    """
    log(f"  STEP 2 ─ Switching to '{branch['name']}' ...")
    t0 = time.time()

    page.goto(branch["url"], wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(3_000)

    switched = _try_dismiss_popup(page, timeout_ms=6_000)
    log(
        f"  STEP 2 ─ Popup {'confirmed ✓' if switched else 'not shown'} | "
        f"url={page.url!r} ({round(time.time()-t0,1)}s)"
    )

    cookies = page.context.cookies()
    return cookies


# ════════════════════════════════════════════════════════════════════════════ #
#  STEP 3 — Category discovery via hover                                      #
# ════════════════════════════════════════════════════════════════════════════ #

def step3_get_categories(page, branch: dict) -> list[dict]:
    """
    1. Navigate directly to /category (branch cookie already set → branch-specific)
    2. Parse all categories + subcategories from div.categories-listing-item
    3. If that yields 0: open hamburger menu → /category via menu link
    4. If still 0: hover each top-level category to reveal subcategory links
    Returns [{'category': str, 'sub_category': str, 'url': str}, ...]
    """
    log(f"  STEP 3 ─ Getting categories for '{branch['name']}' ...")
    t0 = time.time()

    # ── Primary: navigate directly to /category (no hamburger menu needed) ── #
    # Branch cookie is already set, so this page returns branch-specific URLs.
    categories = _direct_category_page(page)

    # ── Fallback A: open hamburger → use menu's last link to /category ────── #
    if not categories:
        log(f"  STEP 3 ─ Direct /category yielded 0 — trying via hamburger menu ...")
        page.goto(f"{BASE}/home", wait_until="domcontentloaded", timeout=20_000)
        page.wait_for_timeout(2_000)
        _clear_overlays(page)

        opened = False
        for sel in [
            "button.navigation-link.hamburger-categories",
            "button.categoriesMenuJs",
            ".hamburger-categories",
        ]:
            try:
                el = page.wait_for_selector(sel, timeout=6_000)
                if el:
                    page.evaluate("el => el.click()", el)
                    page.wait_for_timeout(1_500)
                    opened = True
                    break
            except Exception:
                continue

        if opened:
            categories = _listing_page_categories(page)

    # ── Fallback B: hover each top-level category in the open menu ───────── #
    if not categories:
        log(f"  STEP 3 ─ Listing page yielded 0 — trying hover approach ...")
        page.goto(f"{BASE}/home", wait_until="domcontentloaded", timeout=20_000)
        page.wait_for_timeout(2_000)
        _clear_overlays(page)
        for sel in [
            "button.navigation-link.hamburger-categories",
            "button.categoriesMenuJs",
            ".hamburger-categories",
        ]:
            try:
                el = page.wait_for_selector(sel, timeout=6_000)
                if el:
                    page.evaluate("el => el.click()", el)
                    page.wait_for_timeout(1_500)
                    break
            except Exception:
                continue
        categories = _hover_scrape_categories(page)

    # Deduplicate by URL
    seen: set[str] = set()
    unique: list[dict] = []
    for c in categories:
        if c["url"] not in seen:
            seen.add(c["url"])
            unique.append(c)

    elapsed = round(time.time() - t0, 1)
    log(f"  STEP 3 ─ {len(unique)} unique subcategories ({elapsed}s)")
    return unique


def _hover_scrape_categories(page) -> list[dict]:
    """
    Hover each li in the open categories menu → collect subcategory links
    that become visible in the flyout/submenu.
    """
    categories: list[dict] = []

    # Top-level category items in the active/open menu
    menu_items = page.query_selector_all(
        "ul.category-menu.categoryListJs.activeJs > li, "
        "ul.categoryListJs.activeJs > li"
    )

    if not menu_items:
        # Try a broader selector if the specific one misses
        menu_items = page.query_selector_all("ul.category-menu > li")

    log(f"    hover: found {len(menu_items)} top-level menu items")

    for item in menu_items:
        try:
            anchor = item.query_selector("a")
            if not anchor:
                continue

            cat_name = anchor.inner_text().strip()
            cat_href = anchor.get_attribute("href") or ""

            # Skip utility entries like "View All", "Categories", etc.
            if not cat_name or cat_name.lower() in ("all", "view all", "all categories"):
                continue

            # Hover to reveal subcategory flyout
            item.hover()
            page.wait_for_timeout(700)  # allow CSS transition to complete

            # Look for revealed subcategory links (various possible selectors)
            sub_links = item.query_selector_all(
                "ul li a, "
                ".sub-menu li a, "
                ".category-sub-menu li a, "
                ".submenu li a, "
                "[class*='sub'] li a"
            )

            if sub_links:
                for sub in sub_links:
                    sn = sub.inner_text().strip()
                    sh = sub.get_attribute("href") or ""
                    if sn and sh and sn.lower() != cat_name.lower():
                        full = f"{BASE}{sh}" if sh.startswith("/") else sh
                        categories.append({
                            "category":     cat_name,
                            "sub_category": sn,
                            "url":          full,
                        })
            elif cat_href:
                # No subcategories visible — treat category as a leaf
                full = f"{BASE}{cat_href}" if cat_href.startswith("/") else cat_href
                categories.append({
                    "category":     cat_name,
                    "sub_category": cat_name,
                    "url":          full,
                })

        except Exception as e:
            log(f"    hover: skipping item — {e}")
            continue

    return categories


def _direct_category_page(page) -> list[dict]:
    """
    Navigate directly to /category — branch cookie is already set so this
    returns branch-specific URLs without needing the hamburger menu at all.
    """
    target = f"{BASE}/category"
    log(f"    category listing: direct → {target}")
    try:
        page.goto(target, wait_until="domcontentloaded", timeout=20_000)
        page.wait_for_timeout(2_000)
        _clear_overlays(page)
    except Exception as e:
        log(f"    category listing: failed to load {target}: {e}")
        return []

    return _parse_category_listing_page(page, target)


def _listing_page_categories(page) -> list[dict]:
    """
    Navigate to the full /category listing page via the hamburger menu's last link,
    then parse all div.categories-listing-item blocks.
    Branch cookies are already set, so URLs returned are branch-specific.
    """
    # Ensure the categories menu is open
    for sel in [
        "button.navigation-link.hamburger-categories",
        "button.categoriesMenuJs",
        ".hamburger-categories",
    ]:
        el = page.query_selector(sel)
        if el and el.is_enabled():
            el.click()
            page.wait_for_timeout(1_500)
            break

    # The last link in the open menu leads to the full /category listing
    cat_listing_href = ""
    for sel in [
        "ul.category-menu.categoryListJs.activeJs li:last-child a",
        "ul.categoryListJs.activeJs li:last-child a",
        "ul.category-menu li:last-child a",
    ]:
        el = page.query_selector(sel)
        if el:
            cat_listing_href = el.get_attribute("href") or ""
            break

    if not cat_listing_href:
        log("    category listing: menu link not found")
        return []

    full_url = f"{BASE}{cat_listing_href}" if cat_listing_href.startswith("/") else cat_listing_href
    page.goto(full_url, wait_until="domcontentloaded", timeout=20_000)
    page.wait_for_timeout(2_000)
    return _parse_category_listing_page(page, full_url)


def _parse_category_listing_page(page, url: str) -> list[dict]:
    """Parse div.categories-listing-item blocks on the current page."""
    categories: list[dict] = []
    items = page.query_selector_all("div.categories-listing-item")
    log(f"    category listing: {len(items)} blocks at {url}")

    for item in items:
        try:
            anchor   = item.query_selector("h4.categories-listing-title a, h4 a, h3 a")
            if not anchor:
                continue
            cat_name = anchor.inner_text().strip()
            cat_href = anchor.get_attribute("href") or ""

            sub_links = item.query_selector_all("ul li a")
            if sub_links:
                for sub in sub_links:
                    sn = sub.inner_text().strip()
                    sh = sub.get_attribute("href") or ""
                    if sn and sh:
                        full = f"{BASE}{sh}" if sh.startswith("/") else sh
                        categories.append({
                            "category":     cat_name,
                            "sub_category": sn,
                            "url":          full,
                        })
            elif cat_href:
                full = f"{BASE}{cat_href}" if cat_href.startswith("/") else cat_href
                categories.append({
                    "category":     cat_name,
                    "sub_category": cat_name,
                    "url":          full,
                })
        except Exception as e:
            log(f"    category listing: skipping item — {e}")

    return categories


# ════════════════════════════════════════════════════════════════════════════ #
#  STEP 4 — Worker: scrape one subcategory (runs in thread)                   #
# ════════════════════════════════════════════════════════════════════════════ #

def step4_scrape_subcategory(branch_name: str, cat: dict, cookies: list[dict]) -> dict:
    """
    Worker function. Opens its own Playwright browser, injects branch cookies
    (so no seed/popup needed), scrapes subcategory URL page by page.
    Returns metrics dict including the list of scraped products.
    """
    t0     = time.time()
    items  = []
    pages  = 0

    with sync_playwright() as p:
        browser, ctx = _new_context(p)
        ctx.add_cookies(cookies)   # inject branch session
        page = ctx.new_page()

        try:
            page.goto(cat["url"], wait_until="domcontentloaded", timeout=20_000)
            page.wait_for_timeout(2_000)
            _clear_overlays(page)

            while True:
                cards = page.query_selector_all("div.products.productInfoJs")
                if not cards:
                    break
                pages += 1

                for card in cards:
                    product = _parse_card(card, branch_name, cat)
                    if product:
                        items.append(product)

                _clear_overlays(page)

                # Paginate — use JS click to avoid overlay interception
                nxt = page.query_selector("li.next button, li.forward button")
                if not nxt or not nxt.is_enabled():
                    break

                page.evaluate("el => el.scrollIntoView({block:'center'})", nxt)
                page.evaluate("el => el.click()", nxt)   # JS click bypasses overlay checks
                _wait_for_page_ready(page)                # wait for spinner to clear
                page.wait_for_timeout(1_500)
                _clear_overlays(page)

        except Exception as e:
            log(f"  [worker] {branch_name} / {cat['sub_category']}: {e}")
        finally:
            browser.close()

    elapsed = round(time.time() - t0, 1)
    log(
        f"    ✓ {branch_name} / {cat['sub_category']:<35} "
        f"pages={pages}  products={len(items)}  ({elapsed}s)"
    )
    return {
        "branch":       branch_name,
        "category":     cat["category"],
        "sub_category": cat["sub_category"],
        "url":          cat["url"],
        "products":     items,
        "pages":        pages,
        "secs":         elapsed,
    }


def _parse_card(card, branch_name: str, cat: dict) -> dict | None:
    try:
        name_el = card.query_selector("a.products-title")
        if not name_el:
            return None

        name = name_el.inner_text().strip()
        href = name_el.get_attribute("href") or ""
        url  = f"{BASE}{href}" if href.startswith("/") else href

        price_el = card.query_selector("span.products-price-new")
        old_el   = card.query_selector("del.products-price-old")
        img_el   = card.query_selector("div.products-img img, img")

        price_txt = price_el.inner_text().strip() if price_el else ""
        old_txt   = old_el.inner_text().strip()   if old_el   else ""
        img_src   = img_el.get_attribute("src")   if img_el   else ""
        if img_src and img_src.startswith("/"):
            img_src = f"{BASE}{img_src}"

        def _p(raw: str) -> float | None:
            d = re.sub(r"[^\d.]", "", raw.replace(",", ""))
            return float(d) if d else None

        price = _p(price_txt)
        if not name or not price:
            return None

        return {
            "branch_name":  branch_name,
            "category":     cat["category"],
            "sub_category": cat["sub_category"],
            "product_name": name,
            "product_url":  url,
            "image_url":    img_src or "",
            "price":        price,
            "old_price":    _p(old_txt),
            "scraped_at":   datetime.now().isoformat(),
        }
    except Exception:
        return None


# ════════════════════════════════════════════════════════════════════════════ #
#  Per-branch orchestration                                                   #
# ════════════════════════════════════════════════════════════════════════════ #

def scrape_branch(branch: dict, workers: int, headless: bool) -> dict:
    t_branch = time.time()
    log(f"\n{'═'*65}")
    log(f"Branch : {branch['name']}")
    log(f"URL    : {branch['url']}")
    log(f"{'═'*65}")

    # Steps 2 + 3 run sequentially in a single browser (cheap — one context)
    with sync_playwright() as p:
        browser, ctx = _new_context(p, headless=headless)
        page = ctx.new_page()

        # Seed the session first
        page.goto(SEED, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(2_000)
        _try_dismiss_popup(page)

        cookies    = step2_switch_branch(page, branch)
        categories = step3_get_categories(page, branch)
        browser.close()

    # Save categories to CSV
    OUT.mkdir(exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", branch["name"])[:60]
    if categories:
        cat_file = OUT / f"categories_{safe_name}.csv"
        with open(cat_file, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["category", "sub_category", "url"])
            w.writeheader()
            w.writerows(categories)
        log(f"  Categories saved → {cat_file}  ({len(categories)} subcategories)")

    if not categories:
        log(f"  No categories — skipping {branch['name']}")
        return {
            "branch": branch["name"], "subs": 0, "pages": 0,
            "products": 0, "workers": workers,
            "secs": round(time.time() - t_branch, 1), "scrape_secs": 0,
        }

    # Step 4: spawn workers
    log(f"  Spawning {workers} worker(s) for {len(categories)} subcategories ...")
    t_scrape   = time.time()
    sub_results: list[dict] = []
    all_products: list[dict] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(step4_scrape_subcategory, branch["name"], cat, cookies): cat
            for cat in categories
        }
        for future in as_completed(futures):
            try:
                r = future.result()
                sub_results.append(r)
                all_products.extend(r["products"])
            except Exception as e:
                cat = futures[future]
                log(f"  ✗ Worker failed — {cat['sub_category']}: {e}")

    elapsed      = round(time.time() - t_branch, 1)
    scrape_secs  = round(time.time() - t_scrape, 1)
    total_prods  = len(all_products)
    total_pages  = sum(r["pages"] for r in sub_results)
    throughput   = total_prods / max(scrape_secs, 1)

    # Save products to CSV
    if all_products:
        prod_file = OUT / f"products_{safe_name}.csv"
        fieldnames = list(all_products[0].keys())
        with open(prod_file, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(all_products)
        log(f"  Products saved → {prod_file}")

    log(f"\n  ── Summary: {branch['name']} ──")
    log(f"  Subcategories  : {len(sub_results)}")
    log(f"  Total pages    : {total_pages}")
    log(f"  Products found : {total_prods:,}")
    log(f"  Workers used   : {workers}")
    log(f"  Scrape time    : {scrape_secs:.0f}s  (branch total: {elapsed:.0f}s)")
    log(f"  Throughput     : {throughput:.1f} products/sec")

    return {
        "branch":      branch["name"],
        "url":         branch["url"],
        "subs":        len(sub_results),
        "pages":       total_pages,
        "products":    total_prods,
        "workers":     workers,
        "secs":        elapsed,
        "scrape_secs": scrape_secs,
        "throughput":  round(throughput, 2),
        "sub_results": [
            {k: v for k, v in r.items() if k != "products"}
            for r in sub_results
        ],
    }


# ════════════════════════════════════════════════════════════════════════════ #
#  Main                                                                       #
# ════════════════════════════════════════════════════════════════════════════ #

def main():
    parser = argparse.ArgumentParser(description="Quickmart standalone scraper v2")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--branches", type=int, default=2,
                     help="Number of branches to scrape (default: 2)")
    grp.add_argument("--all", dest="all_branches", action="store_true",
                     help="Scrape all branches")
    parser.add_argument("--workers", type=int, default=5,
                        help="Parallel workers per branch (default: 5)")
    parser.add_argument("--headed", action="store_true",
                        help="Run browser in headed (visible) mode for debugging")
    parser.add_argument("--branch-url", dest="branch_url", default=None,
                        help="Skip discovery and test a single branch URL directly "
                             "(e.g. --branch-url https://www.quickmart.co.ke/nakurustatehouse)")
    args = parser.parse_args()

    headless = not args.headed
    OUT.mkdir(exist_ok=True)
    t_total = time.time()

    log("═" * 65)
    log(f"  Quickmart Scraper v2 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"  Workers  : {args.workers}")
    log(f"  Headless : {headless}")
    log("═" * 65)

    # ── Direct single-branch test mode ─────────────────────────────────────
    if args.branch_url:
        url   = args.branch_url
        slug  = url.rstrip("/").split("/")[-1]
        name  = re.sub(r"[-_]", " ", slug).title()
        target = [{"name": name, "url": url, "slug": slug}]
        log(f"\nDirect branch test: {name}  ({url})\n")
        branch_results = [scrape_branch(target[0], workers=args.workers, headless=headless)]
        _print_summary(branch_results, t_total)
        return

    # ── STEP 1: Discover all branches ──────────────────────────────────────
    with sync_playwright() as p:
        browser, ctx = _new_context(p, headless=headless)
        pg = ctx.new_page()
        all_branches = step1_get_branches(pg)
        browser.close()

    if not all_branches:
        log("No branches discovered — aborting.")
        return

    # Save full branch list
    branches_file = OUT / "branches.csv"
    with open(branches_file, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "url", "slug"])
        w.writeheader()
        w.writerows(all_branches)
    log(f"All branches saved → {branches_file}")

    # Slice to requested count
    target = all_branches if args.all_branches else all_branches[:args.branches]
    log(f"\nScraping {len(target)} of {len(all_branches)} branch(es) "
        f"with {args.workers} worker(s) each\n")

    # ── STEPS 2-4: Scrape each branch ──────────────────────────────────────
    branch_results: list[dict] = []
    for branch in target:
        result = scrape_branch(branch, workers=args.workers, headless=headless)
        branch_results.append(result)

    _print_summary(branch_results, t_total)


def _print_summary(branch_results: list[dict], t_total: float):
    elapsed_total  = round(time.time() - t_total, 1)
    grand_products = sum(r["products"] for r in branch_results)
    grand_pages    = sum(r["pages"]    for r in branch_results)
    grand_subs     = sum(r["subs"]     for r in branch_results)

    log(f"\n{'═'*65}")
    log(f"  FINAL SUMMARY")
    log(f"{'═'*65}")
    log(f"  {'Branch':<42} {'Subs':>5} {'Pages':>6} {'Products':>9} {'Time':>7}")
    log(f"  {'─'*63}")
    for r in branch_results:
        log(
            f"  {r['branch']:<42} {r['subs']:>5} {r['pages']:>6} "
            f"{r['products']:>9,} {r['secs']:>6.0f}s"
        )
    log(f"  {'─'*63}")
    log(
        f"  {'TOTAL':<42} {grand_subs:>5} {grand_pages:>6} "
        f"{grand_products:>9,} {elapsed_total:>6.0f}s"
    )
    log(f"\n  Output directory : {OUT.resolve()}")

    summary = {
        "run_at":   datetime.now().isoformat(),
        "totals": {
            "products":        grand_products,
            "pages":           grand_pages,
            "subcategories":   grand_subs,
            "elapsed_secs":    elapsed_total,
            "throughput":      round(grand_products / max(elapsed_total, 1), 2),
        },
        "branches": branch_results,
    }
    summary_file = OUT / "run_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    log(f"  Run summary      : {summary_file.resolve()}")
    log("═" * 65)


if __name__ == "__main__":
    main()
