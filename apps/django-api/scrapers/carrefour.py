"""
scrapers/carrefour.py
----------------------
Carrefour Kenya scraper — SAP Commerce Cloud (Hybris) via MAF.

API strategy:
  !! GET THE TOKEN FIRST — 5-minute one-time step !!
  1. Open https://www.carrefour.ke in Chrome
  2. DevTools → Network → XHR/Fetch
  3. Navigate to any category (e.g. Groceries → Beverages)
  4. Find requests to a path containing /occ/v2/
  5. Copy the Authorization: Bearer <token> header value
  6. Paste the token into BEARER_TOKEN below
  7. Confirm BASE_API_URL matches what you see

  Token typically expires in 24h–7d. Re-paste when it does.

Playwright fallback:
  Carrefour Kenya is a React/Next.js SPA.
  data-testid attributes are the most stable selectors.
"""

import time
from typing import Optional

import requests

from .base import APIError, BaseScraper, logger

STORE_ID  = 'mafken'
BASE_URL  = 'https://www.carrefour.ke'

# !! UPDATE THESE after DevTools investigation !!
BASE_API_URL        = f'{BASE_URL}/occ/v2/{STORE_ID}'
PRODUCTS_SEARCH_URL = f'{BASE_API_URL}/products/search'
CATEGORIES_URL      = f'{BASE_API_URL}/catalogs/mafkenProductCatalog/Online/categories'
OFFERS_PAGE_URL     = f'{BASE_URL}/mafken/en/c/exc-ken-carrefour'

# Paste token from DevTools here. Re-paste when it expires.
BEARER_TOKEN = 'PASTE_TOKEN_FROM_DEVTOOLS_HERE'

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept':           'application/json',
    'Accept-Language':  'en-US,en;q=0.9',
    'x-store-id':       STORE_ID,
    'Authorization':    f'Bearer {BEARER_TOKEN}',
}

PAGE_SIZE = 48


class CarrefourScraper(BaseScraper):
    retailer_name = 'Carrefour'
    rate_limit_seconds = 0.5

    def get_offers_url(self):
        return OFFERS_PAGE_URL

    # ── API strategy ─────────────────────────────────────────────────── #

    def scrape_api(self) -> list:
        if BEARER_TOKEN == 'PASTE_TOKEN_FROM_DEVTOOLS_HERE':
            raise APIError(
                'Carrefour BEARER_TOKEN not set — '
                'follow DevTools instructions in this file'
            )

        categories = self._fetch_categories()
        if not categories:
            categories = [{'id': None, 'name': 'On Sale'}]

        all_items = []
        for cat in categories:
            cat_items = self._scrape_category(cat)
            all_items.extend(cat_items)
            time.sleep(self.rate_limit_seconds)

        if not all_items:
            raise APIError(
                'Carrefour API returned 0 products — '
                'token may be expired, paste a fresh one'
            )

        logger.info('[Carrefour] API: %d products', len(all_items))
        return all_items

    def _fetch_categories(self) -> list:
        try:
            resp = requests.get(CATEGORIES_URL, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                return []
            data = resp.json()
            cats = data.get('subcategories', data.get('categories', []))
            return [{'id': c.get('id'), 'name': c.get('name', '')} for c in cats]
        except Exception as e:
            logger.debug('[Carrefour] Category tree failed: %s', e)
            return []

    def _scrape_category(self, cat: dict) -> list:
        items = []
        cat_id   = cat.get('id')
        cat_name = cat.get('name', 'Unknown')
        page     = 0

        while True:
            query = (
                f':relevance:allCategories:{cat_id}:onSale:true'
                if cat_id else ':relevance:onSale:true'
            )
            params = {
                'query':       query,
                'currentPage': page,
                'pageSize':    PAGE_SIZE,
                'lang':        'en',
                'curr':        'KES',
                'fields':      'FULL',
            }

            try:
                resp = requests.get(PRODUCTS_SEARCH_URL, params=params, headers=HEADERS, timeout=20)
            except requests.RequestException as e:
                raise APIError(f'Network error [{cat_name}]: {e}')

            if resp.status_code == 401:
                raise APIError('Carrefour token expired — paste a new BEARER_TOKEN')
            if resp.status_code == 403:
                raise APIError('Carrefour returned 403 — IP rate-limited, wait and retry')
            if resp.status_code != 200:
                logger.warning('[Carrefour] %s page %d: HTTP %d', cat_name, page, resp.status_code)
                break

            try:
                data = resp.json()
            except ValueError as e:
                raise APIError(f'Non-JSON: {e}')

            products = data.get('products', [])
            if not products:
                break

            for p in products:
                item = self._parse_product(p, cat_name)
                if item:
                    items.append(item)

            total_pages = data.get('pagination', {}).get('totalPages', 1)
            if page >= total_pages - 1:
                break

            page += 1
            time.sleep(self.rate_limit_seconds)

        logger.debug('[Carrefour] %s: %d products', cat_name, len(items))
        return items

    def _parse_product(self, p: dict, cat_name: str) -> Optional[dict]:
        try:
            name = p.get('name', '').strip()
            if not name:
                return None

            price_obj      = p.get('price', {})
            base_price_obj = p.get('basePrice') or p.get('originalPrice') or {}

            deal_price = self.parse_price(price_obj.get('value'))
            old_price  = self.parse_price(base_price_obj.get('value'))

            if not deal_price:
                return None
            if old_price and old_price <= deal_price:
                old_price = None

            images    = p.get('images', [])
            image_url = None
            for img in images:
                if img.get('imageType') == 'PRIMARY':
                    image_url = f"{BASE_URL}{img.get('url', '')}"
                    break

            product_url = p.get('url', '')
            if product_url and not product_url.startswith('http'):
                product_url = f'{BASE_URL}{product_url}'

            return {
                'product_name':  name,
                'external_id':   p.get('code', name),
                'product_url':   product_url or None,
                'image_url':     image_url,
                'price':         deal_price,
                'old_price':     old_price,
                'category_name': cat_name,
            }
        except Exception as e:
            logger.debug('[Carrefour] Skipping product: %s', e)
            return None

    # ── Playwright fallback ──────────────────────────────────────────── #

    def scrape_web(self, page) -> list:
        items = []

        CARD_SELECTORS = [
            '[data-testid="product-card"]',
            '.sf-product-card',
            '[class*="ProductCard"]',
            '.product-card',
        ]

        card_selector = None
        for sel in CARD_SELECTORS:
            try:
                page.wait_for_selector(sel, timeout=5_000)
                card_selector = sel
                break
            except Exception:
                continue

        if not card_selector:
            logger.warning('[Carrefour] Fallback: no product card selector matched — check selectors')
            return items

        cards = page.query_selector_all(card_selector)
        logger.info('[Carrefour] Fallback: %d product cards', len(cards))

        for card in cards:
            try:
                name_el = card.query_selector(
                    '[data-testid="product-name"],'
                    '.sf-product-card__title,'
                    '[class*="ProductTitle"],'
                    '[class*="ProductName"],'
                    'h3,h4'
                )
                price_el = card.query_selector(
                    '.sf-price__regular,'
                    '[class*="CurrentPrice"],'
                    '[data-testid="product-price"] .sf-price__regular,'
                    '.price'
                )
                orig_el = card.query_selector(
                    '.sf-price__old,'
                    '[class*="OldPrice"],'
                    '[data-testid="product-price-old"]'
                )
                link_el = card.query_selector('a')
                img_el  = card.query_selector('img')

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
                    'product_name':  name,
                    'external_id':   name,
                    'product_url':   link,
                    'image_url':     image,
                    'price':         deal_price,
                    'old_price':     old_price,
                    'category_name': None,
                })
            except Exception as e:
                logger.debug('[Carrefour] Fallback: skipping card: %s', e)

        return items
