"""
scrapers/naivas.py
-------------------
Naivas scraper — Magento 2 (naivas.online)

API strategy:
  Magento 2 public REST API at /rest/V1/products, filtering for special_price.
  No auth token needed for guest catalog reads on most Magento 2 setups.

  !! VERIFY FIRST (one-time, 30 min) !!
  Open naivas.online → DevTools → Network → XHR/Fetch → browse Special Offers.
  Look for requests to /rest/V1/products or /graphql.
  If auth header present, add to HEADERS dict.

Playwright fallback:
  Navigates to OFFERS_URL, scrolls, parses Magento 2 Luma/Hyva product cards.
"""

import time
from decimal import Decimal
from typing import Optional

import requests

from .base import APIError, BaseScraper, logger

BASE_URL = 'https://www.naivas.online'
PRODUCTS_URL = f'{BASE_URL}/rest/V1/products'
OFFERS_URL = f'{BASE_URL}/special-offers'
PAGE_SIZE = 100

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json',
}


class NaivasScraper(BaseScraper):
    retailer_name = 'Naivas'
    rate_limit_seconds = 0.3

    def get_offers_url(self):
        return OFFERS_URL

    # ── API strategy ─────────────────────────────────────────────────── #

    def scrape_api(self) -> list:
        items = []
        page = 1

        while True:
            params = {
                'searchCriteria[filterGroups][0][filters][0][field]': 'special_price',
                'searchCriteria[filterGroups][0][filters][0][conditionType]': 'notnull',
                'searchCriteria[pageSize]': PAGE_SIZE,
                'searchCriteria[currentPage]': page,
            }

            try:
                resp = requests.get(PRODUCTS_URL, params=params, headers=HEADERS, timeout=20)
            except requests.RequestException as e:
                raise APIError(f'Network error page {page}: {e}')

            if resp.status_code == 401:
                raise APIError('Naivas API requires a token — check DevTools for auth header')
            if resp.status_code == 403:
                raise APIError('Naivas API returned 403 — may need session cookie')
            if resp.status_code != 200:
                raise APIError(f'Naivas API returned HTTP {resp.status_code}')

            try:
                data = resp.json()
            except ValueError as e:
                raise APIError(f'Non-JSON response: {e}')

            products = data.get('items', [])
            if not products:
                break

            for p in products:
                item = self._parse_product(p)
                if item:
                    items.append(item)

            total = data.get('total_count', 0)
            if page * PAGE_SIZE >= total:
                break

            page += 1
            time.sleep(self.rate_limit_seconds)

        if not items:
            raise APIError('Naivas API returned 0 products — endpoint may have moved')

        logger.info('[Naivas] API: %d discounted products', len(items))
        return items

    def _get_custom_attr(self, product: dict, code: str):
        for attr in product.get('custom_attributes', []):
            if attr.get('attribute_code') == code:
                return attr.get('value')
        return None

    def _parse_product(self, p: dict) -> Optional[dict]:
        try:
            name = p.get('name', '').strip()
            if not name:
                return None

            regular_price = self.parse_price(p.get('price'))
            special_price = self.parse_price(self._get_custom_attr(p, 'special_price'))

            deal_price = special_price or regular_price
            old_price = regular_price if special_price else None

            if not deal_price:
                return None

            url_key = self._get_custom_attr(p, 'url_key') or ''
            product_url = f'{BASE_URL}/{url_key}.html' if url_key else None

            media = p.get('media_gallery_entries', [])
            image_url = None
            if media:
                image_url = f'{BASE_URL}/pub/media/catalog/product{media[0].get("file", "")}'

            cat_links = p.get('extension_attributes', {}).get('category_links', [])
            category_name = cat_links[0].get('category_id', '') if cat_links else None

            return {
                'product_name': name,
                'external_id':  p.get('sku', name),
                'product_url':  product_url,
                'image_url':    image_url,
                'price':        deal_price,
                'old_price':    old_price,
                'category_name': category_name,
            }
        except Exception as e:
            logger.debug('[Naivas] Skipping product: %s', e)
            return None

    # ── Playwright fallback ──────────────────────────────────────────── #

    def scrape_web(self, page) -> list:
        items = []

        try:
            page.wait_for_selector('.product-item, li.item.product', timeout=15_000)
        except Exception:
            logger.warning('[Naivas] Fallback: product-item selector not found — check CSS selectors')
            return items

        cards = page.query_selector_all('.product-item, li.item.product')
        logger.info('[Naivas] Fallback: %d product cards found', len(cards))

        for card in cards:
            try:
                name_el = card.query_selector(
                    '.product-item-name a, .product-name a, [class*="product-name"] a'
                )
                deal_el = card.query_selector(
                    '.special-price .price, '
                    '.price-wrapper[data-price-type="finalPrice"] .price'
                )
                orig_el = card.query_selector(
                    '.old-price .price, '
                    '.price-wrapper[data-price-type="oldPrice"] .price'
                )
                link_el = card.query_selector('a')
                img_el  = card.query_selector('img.product-image-photo, img[class*="product"]')
                pid     = card.get_attribute('data-product-id') or ''

                if not name_el or not deal_el:
                    continue

                name       = name_el.inner_text().strip()
                deal_price = self.parse_price(deal_el.inner_text())
                old_price  = self.parse_price(orig_el.inner_text()) if orig_el else None
                link       = name_el.get_attribute('href') or (
                    link_el.get_attribute('href') if link_el else None
                )
                image = img_el.get_attribute('src') if img_el else None

                if not name or not deal_price:
                    continue

                items.append({
                    'product_name': name,
                    'external_id':  pid or name,
                    'product_url':  link,
                    'image_url':    image,
                    'price':        deal_price,
                    'old_price':    old_price,
                    'category_name': None,
                })
            except Exception as e:
                logger.debug('[Naivas] Fallback: skipping card: %s', e)

        return items
