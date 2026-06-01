"""
scrapers/quickmart.py
----------------------
Quickmart scraper — Playwright only (no public REST API).

Confirmed 2026-06-01 via live inspection of quickmart.co.ke.

Strategy
────────
Base URL : https://www.quickmart.co.ke

Step 1 — Branch discovery  (quickmart.co.ke/shops)
  Seed URL /5301 first to establish session cookie, then navigate to /shops.
  Click #all-shops → click #loadMoreBtn until gone.
  Branch anchors : a.products.product-item
    href : e.g. /nakurustatehouse   (relative, prepend BASE_URL)
    name : extracted from onclick via  r"switch to (.+?) \?"

Step 2 — Category discovery  (per branch)
  Navigate to branch URL → dismiss popup ("Continue" button).
  Click: button.navigation-link.hamburger-categories
  Wait:  ul.category-menu.categoryListJs.activeJs li a  (last item = /category)
  Navigate to /category → wait for div.categories-listing-item
  Each item:
    Category  : h4.categories-listing-title a  → name + href (e.g. /foods)
    Sub-cats  : ul li a  → sub_name + sub_href
  If no sub-cats, use the category entry directly.

Step 3 — Products per subcategory  (paginated)
  Navigate to subcategory URL (branch cookie already set → branch-specific pricing).
  Repeat until li.next button is missing or disabled:
    Cards       : div.products.productInfoJs
    Name        : a.products-title  (text + href)
    Image       : div.products-img img  → src
    Sale price  : span.products-price-new
    Old price   : del.products-price-old
  Next page     : li.next button → click → wait 2s
"""

import re
import time
from decimal import Decimal
from typing import Optional

from .base import APIError, BaseScraper, logger

BASE_URL  = 'https://www.quickmart.co.ke'
SHOPS_URL = f'{BASE_URL}/shops'
SEED_URL  = f'{BASE_URL}/5301'   # seed URL to establish session cookie

UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
)

_BRANCH_NAME_RE = re.compile(r'switch to (.+?)\s*\?', re.IGNORECASE)


# ── Helpers ──────────────────────────────────────────────────────────────── #

def _full_url(href: str) -> str:
    if not href:
        return ''
    if href.startswith('http'):
        return href
    return f'{BASE_URL}{href}'


def _dismiss_popup(page):
    try:
        btn = page.wait_for_selector(
            '//button[contains(text(),"Continue")]', timeout=5_000
        )
        btn.click()
        page.wait_for_timeout(800)
        logger.debug('[Quickmart] Popup dismissed')
    except Exception:
        pass


def _clean_price(raw: str) -> Optional[float]:
    if not raw:
        return None
    digits = re.sub(r'[^\d.]', '', raw.replace(',', ''))
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


# ── Branch discovery ─────────────────────────────────────────────────────── #

def discover_branches(page) -> list[dict]:
    """
    Return list of {'name': str, 'url': str}.
    Must be called with a Playwright page that has NOT visited any branch URL
    — or call with a fresh context so we can set the seed cookie.
    """
    # Seed session so /shops renders branch anchors
    logger.info('[Quickmart] Seeding session via %s', SEED_URL)
    page.goto(SEED_URL, wait_until='domcontentloaded', timeout=30_000)
    page.wait_for_timeout(2500)
    _dismiss_popup(page)

    logger.info('[Quickmart] Loading /shops')
    page.goto(SHOPS_URL, wait_until='domcontentloaded', timeout=30_000)
    page.wait_for_timeout(2000)

    # Expand all branches
    try:
        page.click('#all-shops')
        page.wait_for_timeout(2000)
    except Exception:
        pass

    for _ in range(30):
        lm = page.query_selector('#loadMoreBtn')
        if not lm:
            break
        lm.click()
        page.wait_for_timeout(2000)

    anchors = page.query_selector_all('a.products.product-item')
    logger.info('[Quickmart] Found %d branch anchors', len(anchors))

    branches = []
    for a in anchors:
        href = a.get_attribute('href') or ''
        if not href:
            continue

        # Extract name from onclick: "switch to Nakuru Statehouse ?"
        onclick = a.get_attribute('onclick') or ''
        m = _BRANCH_NAME_RE.search(onclick)
        if m:
            name = m.group(1).strip()
        else:
            # Fallback: humanise slug
            slug = href.strip('/').split('/')[-1]
            name = re.sub(r'[-_]', ' ', slug).title()

        branches.append({'name': name, 'url': _full_url(href)})

    return branches


# ── Category discovery ────────────────────────────────────────────────────── #

def get_categories(page, branch_url: str) -> list[dict]:
    """
    Navigate to branch, set cookie, open category menu, parse all
    categories and subcategories. Returns:
      [{'category': str, 'sub_category': str, 'url': str}, ...]
    """
    logger.info('[Quickmart] Loading branch %s for categories', branch_url)
    page.goto(branch_url, wait_until='domcontentloaded', timeout=30_000)
    page.wait_for_timeout(3000)
    _dismiss_popup(page)

    # Open categories hamburger menu
    opened = False
    for sel in [
        'button.navigation-link.hamburger-categories',
        'button.categoriesMenuJs',
        '.hamburger-categories',
    ]:
        el = page.query_selector(sel)
        if el:
            if not el.is_enabled():
                logger.debug('[Quickmart/%s] Categories button disabled — inactive branch', branch_url)
                return []
            try:
                el.click(timeout=8_000)
                page.wait_for_timeout(1500)
                opened = True
            except Exception:
                pass
            break

    if not opened:
        logger.warning('[Quickmart/%s] Could not open categories menu', branch_url)
        return []

    # Navigate to full category listing (last item in the menu)
    cat_listing_href = ''
    for sel in [
        'ul.category-menu.categoryListJs.activeJs li:last-child a',
        'ul.categoryListJs.activeJs li:last-child a',
        'ul.category-menu li:last-child a',
    ]:
        el = page.query_selector(sel)
        if el:
            cat_listing_href = el.get_attribute('href') or ''
            break

    if not cat_listing_href:
        logger.warning('[Quickmart/%s] No category listing link found', branch_url)
        return []

    page.goto(_full_url(cat_listing_href), wait_until='domcontentloaded', timeout=20_000)
    page.wait_for_timeout(2000)

    # Parse category items
    categories = []
    items = page.query_selector_all('div.categories-listing-item')
    for item in items:
        try:
            anchor   = item.query_selector('h4.categories-listing-title a, h4 a')
            cat_name = anchor.inner_text().strip() if anchor else ''
            cat_href = anchor.get_attribute('href') if anchor else ''

            sub_anchors = item.query_selector_all('ul li a')
            if sub_anchors:
                for sub in sub_anchors:
                    sub_name = sub.inner_text().strip()
                    sub_href = sub.get_attribute('href') or ''
                    if sub_name and sub_href:
                        categories.append({
                            'category':     cat_name,
                            'sub_category': sub_name,
                            'url':          _full_url(sub_href),
                        })
            elif cat_href:
                categories.append({
                    'category':     cat_name,
                    'sub_category': cat_name,
                    'url':          _full_url(cat_href),
                })
        except Exception as e:
            logger.debug('[Quickmart] Skipping category item: %s', e)

    logger.info('[Quickmart] Found %d subcategories', len(categories))
    return categories


# ── Product scraping ─────────────────────────────────────────────────────── #

def scrape_category_products(page, branch_name: str, cat: dict) -> list[dict]:
    """Scrape all products from one subcategory URL, paginating."""
    url      = cat['url']
    cat_name = cat['category']
    sub_cat  = cat['sub_category']
    products = []
    page_num = 1

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=20_000)
        page.wait_for_timeout(2500)
    except Exception as e:
        logger.warning('[Quickmart/%s] Cannot load %s: %s', branch_name, url, e)
        return []

    while True:
        cards = page.query_selector_all('div.products.productInfoJs')
        if not cards:
            break

        for card in cards:
            item = _parse_card(card, branch_name, cat_name, sub_cat)
            if item:
                products.append(item)

        # Paginate
        try:
            next_btn = page.query_selector('li.next button, li.forward button')
            if not next_btn or not next_btn.is_enabled():
                break
            page.evaluate('el => el.scrollIntoView({block:"center"})', next_btn)
            next_btn.click()
            page.wait_for_timeout(2500)
            page_num += 1
        except Exception:
            break

    logger.debug('[Quickmart/%s] %s > %s: %d products (%d pages)',
                 branch_name, cat_name, sub_cat, len(products), page_num)
    return products


def _parse_card(card, branch_name, cat_name, sub_cat) -> Optional[dict]:
    try:
        name_el = card.query_selector('a.products-title')
        if not name_el:
            return None

        name        = name_el.inner_text().strip()
        product_url = _full_url(name_el.get_attribute('href') or '')

        img_el    = card.query_selector('div.products-img img')
        image_url = img_el.get_attribute('src') if img_el else None
        if image_url and image_url.startswith('/'):
            image_url = f'{BASE_URL}{image_url}'

        price_el  = card.query_selector('span.products-price-new')
        old_el    = card.query_selector('del.products-price-old')

        price_raw = price_el.inner_text().strip() if price_el else ''
        old_raw   = old_el.inner_text().strip() if old_el else ''

        price     = _clean_price(price_raw)
        old_price = _clean_price(old_raw)

        if not name or not price:
            return None

        # External ID from product URL slug
        ext_id = (product_url.rstrip('/').split('/')[-1] or name)

        return {
            'product_name':      name,
            'external_id':       ext_id,
            'category_name':     cat_name,
            'sub_category_name': sub_cat,
            'product_url':       product_url,
            'image_url':         image_url,
            'price':             Decimal(str(price)),
            'old_price':         Decimal(str(old_price)) if old_price else None,
        }
    except Exception as e:
        logger.debug('[Quickmart/%s] Skipping card: %s', branch_name, e)
        return None


# ── BaseScraper subclass ─────────────────────────────────────────────────── #

class QuickmartBranchScraper(BaseScraper):
    """
    One instance = one branch.
    branch_url: full URL, e.g. https://www.quickmart.co.ke/nakurustatehouse
                stored in RetailerBranch.external_id
    """
    retailer_name    = 'Quickmart'
    rate_limit_seconds = 1.0

    def __init__(self, branch_name: str, branch_url: str, branch_external_id: str = None):
        self.branch_name        = branch_name
        self.branch_url         = branch_url
        self.branch_external_id = branch_external_id or branch_url
        super().__init__()

    def get_offers_url(self) -> str:
        return self.branch_url

    def scrape_api(self) -> list:
        raise APIError('Quickmart has no public product API — using Playwright')

    def scrape_web(self, page) -> list:
        """
        Called by BaseScraper._run_playwright_fallback() after loading
        get_offers_url(). Navigate through all categories and collect products.
        """
        # Dismiss any popup that appeared on initial load
        _dismiss_popup(page)

        categories = get_categories(page, self.branch_url)
        if not categories:
            logger.warning('[Quickmart/%s] No categories found', self.branch_name)
            return []

        all_items = []
        for cat in categories:
            items = scrape_category_products(page, self.branch_name, cat)
            all_items.extend(items)
            time.sleep(self.rate_limit_seconds)

        logger.info('[Quickmart/%s] Total: %d products across %d subcategories',
                    self.branch_name, len(all_items), len(categories))
        return all_items
