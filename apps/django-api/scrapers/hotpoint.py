"""
scrapers/hotpoint.py
----------------------
Hotpoint Kenya scraper — hotpoint.co.ke (Django Oscar)

API strategy: not available — /api/ returns HTTP 500 (Oscar DRF not exposed publicly).
scrape_api() immediately raises APIError to trigger the Playwright fallback.

Playwright strategy (primary working path):
  Navigates to /catalogue/on-sale/ — the on-sale listing page.
  The page is server-rendered (SSR Django Oscar), so static selectors work reliably.

  Confirmed selectors (inspected from live HTML):
    Card wrapper : div.product-item
    Name         : h5.product-card-name  (or .card-title)
    Sale price   : span.stockrecord-price-current
    Old price    : span.stockrecord-price-old
    Link         : a[href^="/catalogue/"]  (first anchor inside card)
    Image        : img.product-card-img
    Discount badge: span.sale-label

  Pagination: ul.pagination → a.page-paginator-link with href="?page=N"
  Iterates pages until the current page has no next-page link.

  External ID: numeric suffix from product URL slug
    e.g. /catalogue/product-name_1869/ → "1869"
"""

import re
from decimal import Decimal
from typing import Optional
from urllib.parse import urljoin

from .base import APIError, BaseScraper, logger

BASE_URL    = 'https://hotpoint.co.ke'
ON_SALE_URL = f'{BASE_URL}/catalogue/on-sale/'

HOTPOINT_CATEGORIES = {
    'tv-entertainment':    'TVs & Entertainment',
    'audio':               'Audio',
    'fridges-freezers':    'Fridges & Freezers',
    'washers-dryers':      'Washers & Dryers',
    'cookers-ovens':       'Cookers & Ovens',
    'small-appliances':    'Kitchen & Small Home Appliances',
    'water-dispensers':    'Water Dispensers',
    'built-in-appliances': 'Built-in Appliances',
    'ac-fans-heaters':     "AC's, Fans & Heaters",
    'personal-care':       'Personal Care',
}


def parse_kes_price(text: str) -> Optional[Decimal]:
    if not text:
        return None
    cleaned = re.sub(r'[^\d.]', '', text.replace(',', ''))
    if not cleaned:
        return None
    try:
        from decimal import Decimal, InvalidOperation
        return Decimal(cleaned)
    except Exception:
        return None


def _extract_external_id(product_url: str) -> str:
    """Extract numeric ID from /catalogue/product-slug_1869/ style URL."""
    m = re.search(r'_(\d+)/?$', product_url)
    return m.group(1) if m else product_url


def _category_from_url(product_url: str) -> Optional[str]:
    """
    Try to infer category from a Hotpoint category URL embedded in the page.
    Falls back to None — category is passed separately from the listing page heading.
    """
    for slug, name in HOTPOINT_CATEGORIES.items():
        if slug in product_url:
            return name
    return None


class HotpointScraper(BaseScraper):
    retailer_name = 'Hotpoint'
    rate_limit_seconds = 0.5

    def get_offers_url(self) -> str:
        return ON_SALE_URL

    # ── API strategy — not available, go straight to Playwright ─────── #

    def scrape_api(self) -> list:
        raise APIError(
            'hotpoint.co.ke /api/ returns HTTP 500 — using Playwright scraper'
        )

    # ── Playwright strategy ──────────────────────────────────────────── #

    def scrape_web(self, page, run=None) -> list:
        all_items: list = []
        page_num = 1

        while True:
            url = f'{ON_SALE_URL}?page={page_num}'
            logger.info('[Hotpoint] Scraping page %d: %s', page_num, url)

            try:
                resp = page.goto(url, wait_until='domcontentloaded', timeout=30_000)
                if resp and resp.status >= 400:
                    logger.warning('[Hotpoint] %s returned HTTP %d', url, resp.status)
                    if run:
                        self.record_page_scraped(run, http_error=True)
                    break
            except Exception as e:
                logger.warning('[Hotpoint] Failed to load %s: %s', url, e)
                if run:
                    self.record_page_scraped(run, http_error=True)
                break

            if run:
                self.record_page_scraped(run, http_error=False)

            # Wait for product cards — generous timeout to absorb Cloudflare challenge
            # redirect (networkidle can fire on the challenge page before it redirects)
            try:
                page.wait_for_selector('div.product-item', timeout=45_000)
            except Exception:
                logger.info('[Hotpoint] No product cards on page %d — stopping', page_num)
                break

            cards = page.query_selector_all('div.product-item')
            if not cards:
                logger.info('[Hotpoint] Empty page %d — stopping', page_num)
                break

            logger.info('[Hotpoint] Page %d: %d cards', page_num, len(cards))

            for card in cards:
                try:
                    item = self._parse_card(card)
                    if item:
                        all_items.append(item)
                except Exception as e:
                    logger.debug('[Hotpoint] Skipping card: %s', e)

            # Check for next page
            if not self._has_next_page(page, page_num):
                logger.info('[Hotpoint] No next page after page %d — done', page_num)
                break

            page_num += 1

        logger.info('[Hotpoint] Scraped %d products across %d pages', len(all_items), page_num)
        return all_items

    def _has_next_page(self, page, current_page: int) -> bool:
        """Return True if a link to current_page+1 exists in the pagination."""
        next_page = current_page + 1
        try:
            link = page.query_selector(f'a.page-paginator-link[href="?page={next_page}"]')
            return link is not None
        except Exception:
            return False

    def _parse_card(self, card) -> Optional[dict]:
        # Link — first product catalogue link
        link_el = card.query_selector('a[href^="/catalogue/"]')
        if not link_el:
            return None

        href = link_el.get_attribute('href') or ''
        product_url = urljoin(BASE_URL, href) if href else None
        if not product_url:
            return None

        external_id = _extract_external_id(href)

        # Name
        name_el = card.query_selector('h5.product-card-name')
        if not name_el:
            name_el = card.query_selector('.card-title')
        if not name_el:
            name_el = link_el
        name = (name_el.inner_text() or name_el.get_attribute('alt') or '').strip()
        if not name:
            return None

        # Image
        img_el = card.query_selector('img.product-card-img')
        if not img_el:
            img_el = card.query_selector('img')
        image_url = None
        if img_el:
            src = img_el.get_attribute('src')
            if src:
                image_url = urljoin(BASE_URL, src) if not src.startswith('http') else src

        # Prices
        price_el     = card.query_selector('span.stockrecord-price-current')
        old_price_el = card.query_selector('span.stockrecord-price-old')

        deal_price = parse_kes_price(price_el.inner_text()) if price_el else None
        old_price  = parse_kes_price(old_price_el.inner_text()) if old_price_el else None

        if not deal_price:
            return None

        if old_price and old_price <= deal_price:
            old_price = None

        return {
            'product_name':        name,
            'external_id':         external_id,
            'product_url':         product_url,
            'image_url':           image_url,
            'price':               deal_price,
            'old_price':           old_price,
            'category_name':       None,
            'sub_category_name':   None,
            'sub_category_2_name': None,
        }
