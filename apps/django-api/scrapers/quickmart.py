"""
scrapers/quickmart.py
----------------------
Quickmart branch scraper — one instance per branch.

API strategy:
  !! VERIFY FIRST — open quickmart.co.ke DevTools → Network → XHR/Fetch
  Browse any product/offers page and look for JSON responses.

  Most likely candidates:
    A) WooCommerce:  GET /wp-json/wc/v3/products?on_sale=true&store_id={id}
    B) Custom API:   GET /api/v1/products?branch={id}&on_sale=true

  Update PRODUCTS_URL_TEMPLATE after DevTools investigation.

Playwright fallback:
  Update BRANCH_OFFERS_URL_TEMPLATE and CSS selectors after inspecting the live site.
"""

import time
from typing import Optional

import requests

from .base import APIError, BaseScraper, logger

BASE_URL = 'https://www.quickmart.co.ke'

# !! UPDATE after DevTools investigation !!
PRODUCTS_URL_TEMPLATE = f'{BASE_URL}/wp-json/wc/v3/products'
BRANCH_OFFERS_URL_TEMPLATE = f'{BASE_URL}/store/{{branch_slug}}/offers'

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json',
}

PAGE_SIZE = 100


class QuickmartBranchScraper(BaseScraper):
    retailer_name = 'Quickmart'
    rate_limit_seconds = 0.4

    def __init__(self, branch_name: str, branch_external_id: str = None):
        self.branch_name = branch_name
        self.branch_external_id = branch_external_id
        super().__init__()

    def get_offers_url(self) -> str:
        slug = self.branch_name.lower().replace(' ', '-').replace("'", '')
        return BRANCH_OFFERS_URL_TEMPLATE.format(branch_slug=slug)

    # ── API strategy ─────────────────────────────────────────────────── #

    def scrape_api(self) -> list:
        items = []
        page = 1

        while True:
            params = {
                'per_page': PAGE_SIZE,
                'page': page,
                'on_sale': 'true',
            }
            if self.branch_external_id:
                params['store_id'] = self.branch_external_id
            elif self.branch_name:
                params['branch'] = self.branch_name

            try:
                resp = requests.get(
                    PRODUCTS_URL_TEMPLATE,
                    params=params,
                    headers=HEADERS,
                    timeout=20,
                )
            except requests.RequestException as e:
                raise APIError(f'Network error [{self.branch_name}]: {e}')

            if resp.status_code == 401:
                raise APIError('WooCommerce API requires auth key — check DevTools')
            if resp.status_code == 404:
                raise APIError('Quickmart API endpoint not found — verify URL in DevTools')
            if resp.status_code != 200:
                raise APIError(f'Quickmart API HTTP {resp.status_code}')

            try:
                data = resp.json()
            except ValueError as e:
                raise APIError(f'Non-JSON response: {e}')

            products = (
                data if isinstance(data, list)
                else data.get('products', data.get('items', []))
            )
            if not products:
                break

            for p in products:
                item = self._parse_product(p)
                if item:
                    items.append(item)

            if len(products) < PAGE_SIZE:
                break

            page += 1
            time.sleep(self.rate_limit_seconds)

        if not items:
            raise APIError(f'Quickmart [{self.branch_name}] API returned 0 products')

        logger.info('[Quickmart/%s] API: %d products', self.branch_name, len(items))
        return items

    def _parse_product(self, p: dict) -> Optional[dict]:
        try:
            name = p.get('name', '').strip()
            if not name:
                return None

            deal_price = self.parse_price(p.get('sale_price') or p.get('price'))
            old_price  = self.parse_price(p.get('regular_price') or p.get('original_price'))

            if not deal_price:
                return None

            cats = p.get('categories', [])
            cat_name = cats[0].get('name') if cats else None
            sub_cat  = cats[1].get('name') if len(cats) > 1 else None

            images = p.get('images', [])
            image_url = images[0].get('src') if images else None

            return {
                'product_name':      name,
                'external_id':       str(p.get('id', name)),
                'product_url':       p.get('permalink') or p.get('url'),
                'image_url':         image_url,
                'price':             deal_price,
                'old_price':         old_price,
                'category_name':     cat_name,
                'sub_category_name': sub_cat,
            }
        except Exception as e:
            logger.debug('[Quickmart/%s] Skipping product: %s', self.branch_name, e)
            return None

    # ── Playwright fallback ──────────────────────────────────────────── #

    def scrape_web(self, page) -> list:
        items = []

        CARD_SELECTORS = (
            '.product-card',
            '.product-item',
            '[class*="ProductCard"]',
            '[class*="product-card"]',
        )
        card_selector = None
        for sel in CARD_SELECTORS:
            try:
                page.wait_for_selector(sel, timeout=4_000)
                card_selector = sel
                break
            except Exception:
                continue

        if not card_selector:
            logger.warning('[Quickmart/%s] No product card selector matched', self.branch_name)
            return items

        cards = page.query_selector_all(card_selector)
        logger.info('[Quickmart/%s] Fallback: %d cards', self.branch_name, len(cards))

        for card in cards:
            try:
                name_el  = card.query_selector('.product-title,.product-name,h3,h4')
                price_el = card.query_selector('.sale-price,.current-price,.price')
                orig_el  = card.query_selector('.original-price,.regular-price,.was-price')
                link_el  = card.query_selector('a')
                img_el   = card.query_selector('img')

                if not name_el or not price_el:
                    continue

                name       = name_el.inner_text().strip()
                deal_price = self.parse_price(price_el.inner_text())
                old_price  = self.parse_price(orig_el.inner_text()) if orig_el else None
                link       = link_el.get_attribute('href') if link_el else None
                if link and not link.startswith('http'):
                    link = f'{BASE_URL}{link}'
                image = img_el.get_attribute('src') if img_el else None

                if not name or not deal_price:
                    continue

                items.append({
                    'product_name': name,
                    'external_id':  name,
                    'product_url':  link,
                    'image_url':    image,
                    'price':        deal_price,
                    'old_price':    old_price,
                    'category_name': None,
                })
            except Exception as e:
                logger.debug('[Quickmart/%s] Fallback: skipping card: %s', self.branch_name, e)

        return items
