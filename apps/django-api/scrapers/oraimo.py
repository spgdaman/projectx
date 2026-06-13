"""
scrapers/oraimo.py
-------------------
Oraimo Kenya scraper — ke.oraimo.com (custom Vue SPA)

API strategy: not available — all API endpoints return 404 or HTML.
The site is a custom Vue SPA with no public REST API.
scrape_api() immediately raises APIError to trigger the Playwright fallback.

Playwright strategy (primary working path):
  Navigates to the daily deals page first, then each product collection.
  The site is Vue-rendered; wait 5s after domcontentloaded for hydration.

  Confirmed selectors (inspected from live rendered DOM 2026-06):
    Card wrapper  : div.site-product        (also has class js_product, data-id attr)
    Name          : h3 a.js_select_item     (also has data-name, data-sku attributes)
    Sale price    : p.product-price > span  (first span, e.g. "KES 4,900")
    Old price     : p.product-price > del   (e.g. "KES 5,800")
    Link          : a[href^="/product/"]    (first such anchor inside card)
    Image         : img.product-picture     (src or data-src attribute)
    External ID   : data-id on the card div
    Category      : data-category on the product link anchor

  Deduplicates by product name across all pages.
"""

import re
from typing import Optional
from urllib.parse import urljoin

from .base import APIError, BaseScraper, logger

BASE_URL  = 'https://ke.oraimo.com'
DEALS_URL = f'{BASE_URL}/oraimo-daily-deals.html'

COLLECTIONS = [
    (f'{BASE_URL}/collections/audio',           'Audio'),
    (f'{BASE_URL}/collections/power',           'Power'),
    (f'{BASE_URL}/collections/smart-office',    'Smart Office'),
    (f'{BASE_URL}/collections/personal-care',   'Personal Care'),
    (f'{BASE_URL}/collections/home-appliances', 'Home Appliances'),
]


class OraimoScraper(BaseScraper):
    retailer_name = 'Oraimo'
    rate_limit_seconds = 0.5

    def get_offers_url(self) -> str:
        return DEALS_URL

    # ── API strategy — not available, go straight to Playwright ─────── #

    def scrape_api(self) -> list:
        raise APIError(
            'ke.oraimo.com is a Vue SPA with no public REST API — using Playwright'
        )

    # ── Playwright strategy ──────────────────────────────────────────── #

    def scrape_web(self, page, run=None) -> list:
        all_items: list = []
        seen_ids: set = set()

        pages_to_scrape = [(DEALS_URL, 'Daily Deals')] + COLLECTIONS

        for url, fallback_category in pages_to_scrape:
            logger.info('[Oraimo] Scraping %s (%s)', url, fallback_category)
            try:
                resp = page.goto(url, wait_until='domcontentloaded', timeout=30_000)
                if resp and resp.status >= 400:
                    logger.warning('[Oraimo] %s returned HTTP %d', url, resp.status)
                    if run:
                        self.record_page_scraped(run, http_error=True)
                    continue
            except Exception as e:
                logger.warning('[Oraimo] Failed to load %s: %s', url, e)
                if run:
                    self.record_page_scraped(run, http_error=True)
                continue

            if run:
                self.record_page_scraped(run, http_error=False)

            # Wait for Vue SPA hydration — generous timeout to absorb Cloudflare
            # challenge redirect (networkidle may fire on the challenge page first)
            try:
                page.wait_for_selector('div.site-product', timeout=45_000)
            except Exception:
                logger.warning('[Oraimo] No div.site-product found on %s after 45s', url)
                continue

            # Scroll to trigger lazy-loading
            for _ in range(4):
                page.keyboard.press('End')
                page.wait_for_timeout(1200)

            cards = page.query_selector_all('div.site-product')
            logger.info('[Oraimo] %s: %d cards', url, len(cards))

            for card in cards:
                try:
                    item = self._parse_card(card, fallback_category)
                    if item:
                        card_id = item['external_id']
                        if card_id not in seen_ids:
                            seen_ids.add(card_id)
                            all_items.append(item)
                except Exception as e:
                    logger.debug('[Oraimo] Skipping card: %s', e)

        logger.info('[Oraimo] Total unique products scraped: %d', len(all_items))
        return all_items

    def _parse_card(self, card, fallback_category: str) -> Optional[dict]:
        # External ID from data-id attribute on the card div
        external_id = card.get_attribute('data-id') or ''

        # Product link and name
        link_el = card.query_selector('a[href^="/product/"]')
        if not link_el:
            return None

        href = link_el.get_attribute('href') or ''
        product_url = urljoin(BASE_URL, href) if href else None

        # Prefer data-name attribute; fall back to h3 text
        name = (link_el.get_attribute('data-name') or '').strip()
        if not name:
            h3_el = card.query_selector('h3 a.js_select_item')
            if h3_el:
                name = (h3_el.inner_text() or '').strip()
        if not name:
            return None

        if not external_id:
            external_id = link_el.get_attribute('data-id') or name

        # Category from data-category attribute, with fallback to page category
        category = (link_el.get_attribute('data-category') or fallback_category).strip()

        # Image — src first (lazyloaded), then data-src
        img_el = card.query_selector('img.product-picture')
        image_url = None
        if img_el:
            src = img_el.get_attribute('src') or ''
            data_src = img_el.get_attribute('data-src') or ''
            # Skip loading placeholder SVG
            chosen = src if ('cdn-img.oraimo.com' in src) else data_src
            if chosen and 'cdn-img.oraimo.com' in chosen:
                image_url = chosen

        # Prices from p.product-price
        price_el     = card.query_selector('p.product-price > span')
        old_price_el = card.query_selector('p.product-price > del')

        deal_price = self.parse_price(price_el.inner_text()) if price_el else None
        old_price  = self.parse_price(old_price_el.inner_text()) if old_price_el else None

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
            'category_name':       category,
            'sub_category_name':   None,
            'sub_category_2_name': None,
        }
