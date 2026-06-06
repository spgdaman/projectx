"""
scrapers/chandarana.py
-----------------------
Chandarana Foodplus scraper — foodplus.co.ke (Magento 2)

API strategy (primary — no auth required):
  GET /rest/V1/products with two filter groups:
    1. special_price is not null  (has a sale price)
    2. special_to_date >= today   (deal is still active)
  Paginates at 200 products/page. ~1 500 active deals as of 2026-06.

  Key field mappings:
    external_id  ← product['sku']
    price        ← special_price custom_attribute  (current sale price)
    old_price    ← product['price']               (regular shelf price)
    product_url  ← https://foodplus.co.ke/{url_key}.html
    image_url    ← https://foodplus.co.ke/pub/media/catalog/product{image}

Playwright fallback:
  Navigates to /specials — the main on-sale listing page.
  Standard Magento 2 Luma/Blank theme selectors:
    Card wrapper : .product-item
    Name/URL     : a.product-item-link
    Image        : .product-image-photo
    Sale price   : .special-price .price
    Old price    : .old-price .price
"""

import time
from datetime import date
from typing import Optional

import requests

from .base import APIError, BaseScraper, logger

BASE_URL  = 'https://foodplus.co.ke'
MEDIA_URL = f'{BASE_URL}/pub/media/catalog/product'
API_URL   = f'{BASE_URL}/rest/V1/products'
CAT_URL   = f'{BASE_URL}/rest/V1/categories'
PAGE_SIZE = 200
UA = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
)


class ChandaranaScraper(BaseScraper):
    retailer_name = 'Chandarana'
    rate_limit_seconds = 0.3

    def __init__(self):
        super().__init__()
        self._category_tree: dict = {}  # populated once per scrape_api() call

    def get_offers_url(self) -> str:
        return f'{BASE_URL}/specials'

    # ── Category tree ────────────────────────────────────────────────── #

    def _fetch_category_tree(self, session: requests.Session) -> None:
        """Fetch Magento 2 category tree once per run into self._category_tree."""
        try:
            resp = session.get(CAT_URL, timeout=30)
            if resp.status_code != 200:
                logger.warning('[Chandarana] Category tree: HTTP %d', resp.status_code)
                return
            tree: dict = {}
            self._walk_category_node(resp.json(), tree)
            self._category_tree = tree
            logger.info('[Chandarana] Category tree: %d nodes loaded', len(tree))
        except Exception as exc:
            logger.warning('[Chandarana] Category tree fetch failed: %s', exc)

    def _walk_category_node(self, node: dict, tree: dict) -> None:
        cat_id = node.get('id')
        if cat_id:
            tree[str(cat_id)] = {
                'name':      node.get('name', ''),
                'level':     node.get('level', 0),
                'parent_id': str(node.get('parent_id', 0)),
            }
        for child in node.get('children_data', []):
            self._walk_category_node(child, tree)

    def _resolve_categories(self, cat_ids: list) -> tuple:
        """
        Given a list of Magento category IDs, return the 3-level path
        (category_name, sub_category_name, sub_category_2_name) by walking
        up from the deepest matched node.  Skips Magento root nodes (level < 2).
        """
        if not cat_ids or not self._category_tree:
            return None, None, None

        tree = self._category_tree

        # Pick the deepest (most specific) category
        best_cid, best_level = None, -1
        for cid in cat_ids:
            cat = tree.get(str(cid))
            if cat and cat['level'] > best_level:
                best_level = cat['level']
                best_cid = str(cid)

        if not best_cid:
            return None, None, None

        # Walk up and collect names; skip Magento system roots (level 0 and 1)
        path: list = []
        cid = best_cid
        visited: set = set()
        while cid and cid not in visited:
            visited.add(cid)
            cat = tree.get(cid)
            if not cat:
                break
            if cat['level'] >= 2:
                path.append(cat['name'])
            parent_id = cat.get('parent_id', '0')
            if parent_id in ('0', '1', cid):
                break
            cid = parent_id

        path.reverse()  # top-level first
        return (
            path[0] if len(path) > 0 else None,
            path[1] if len(path) > 1 else None,
            path[2] if len(path) > 2 else None,
        )

    # ── API strategy ─────────────────────────────────────────────────── #

    def scrape_api(self) -> list:
        today = date.today().strftime('%Y-%m-%d 00:00:00')
        session = requests.Session()
        session.headers.update({'User-Agent': UA, 'Accept': 'application/json'})

        self._fetch_category_tree(session)

        all_items: list = []
        page = 1

        while True:
            params = {
                'searchCriteria[filterGroups][0][filters][0][field]':         'special_price',
                'searchCriteria[filterGroups][0][filters][0][conditionType]': 'notnull',
                'searchCriteria[filterGroups][1][filters][0][field]':         'special_to_date',
                'searchCriteria[filterGroups][1][filters][0][value]':         today,
                'searchCriteria[filterGroups][1][filters][0][conditionType]': 'gteq',
                'searchCriteria[pageSize]':    PAGE_SIZE,
                'searchCriteria[currentPage]': page,
            }

            try:
                resp = session.get(API_URL, params=params, timeout=30)
            except requests.RequestException as exc:
                raise APIError(f'Request failed on page {page}: {exc}') from exc

            if resp.status_code != 200:
                raise APIError(
                    f'Chandarana API returned HTTP {resp.status_code} on page {page}'
                )

            try:
                data = resp.json()
            except ValueError as exc:
                raise APIError(f'Invalid JSON on page {page}: {exc}') from exc

            products = data.get('items', [])
            total    = data.get('total_count', 0)

            if not products:
                break

            for product in products:
                item = self._parse_product(product)
                if item:
                    all_items.append(item)

            logger.info(
                '[Chandarana] Page %d: %d products (total %d)',
                page, len(products), total,
            )

            if page * PAGE_SIZE >= total:
                break

            page += 1
            time.sleep(self.rate_limit_seconds)

        logger.info('[Chandarana] API done — %d active deals scraped', len(all_items))
        return all_items

    def _parse_product(self, product: dict) -> Optional[dict]:
        name = (product.get('name') or '').strip()
        if not name:
            return None

        sku           = product.get('sku', '')
        regular_price = self.parse_price(product.get('price'))

        ca = {
            attr['attribute_code']: attr['value']
            for attr in product.get('custom_attributes', [])
        }

        special_price = self.parse_price(ca.get('special_price'))
        if not special_price:
            return None

        # Reject stale entries where the "deal" price isn't actually lower
        if regular_price and special_price >= regular_price:
            return None

        url_key     = ca.get('url_key') or ca.get('url_path') or ''
        product_url = f'{BASE_URL}/{url_key}.html' if url_key else None

        image_path = ca.get('image') or ca.get('small_image') or ca.get('thumbnail')
        image_url  = f'{MEDIA_URL}{image_path}' if image_path else None

        # Extract category IDs: prefer extension_attributes.category_links,
        # fall back to the category_ids custom attribute (comma-separated string)
        cat_ids: list = []
        ext = product.get('extension_attributes', {})
        for link in ext.get('category_links', []):
            cid = link.get('category_id')
            if cid:
                cat_ids.append(str(cid))
        if not cat_ids:
            raw = ca.get('category_ids', '')
            if isinstance(raw, str):
                cat_ids = [x.strip() for x in raw.split(',') if x.strip()]
            elif isinstance(raw, list):
                cat_ids = [str(x) for x in raw]

        cat_name, sub_cat, sub_cat_2 = self._resolve_categories(cat_ids)

        return {
            'product_name':        name,
            'external_id':         sku,
            'product_url':         product_url,
            'image_url':           image_url,
            'price':               special_price,
            'old_price':           regular_price,
            'category_name':       cat_name,
            'sub_category_name':   sub_cat,
            'sub_category_2_name': sub_cat_2,
        }

    # ── Playwright fallback ──────────────────────────────────────────── #

    def scrape_web(self, page, run=None) -> list:
        all_items: list = []
        specials_url = f'{BASE_URL}/specials'

        logger.info('[Chandarana] Fallback → Playwright: %s', specials_url)
        try:
            resp = page.goto(specials_url, wait_until='networkidle', timeout=30_000)
            if resp and resp.status >= 400:
                logger.warning('[Chandarana] /specials returned HTTP %d', resp.status)
                if run:
                    self.record_page_scraped(run, http_error=True)
                return all_items
        except Exception as exc:
            logger.warning('[Chandarana] Failed to load /specials: %s', exc)
            if run:
                self.record_page_scraped(run, http_error=True)
            return all_items

        if run:
            self.record_page_scraped(run)

        # Scroll to trigger Magento lazy-loading
        for _ in range(8):
            page.keyboard.press('End')
            page.wait_for_timeout(1500)

        items = self._parse_specials_page(page)
        logger.info('[Chandarana] Playwright scraped %d products', len(items))
        all_items.extend(items)
        return all_items

    def _parse_specials_page(self, page) -> list:
        items = []
        cards = page.query_selector_all('.product-item')
        if not cards:
            logger.warning('[Chandarana] No .product-item cards found on /specials')
            return items

        logger.debug('[Chandarana] %d product cards found', len(cards))
        for card in cards:
            try:
                item = self._parse_card(card)
                if item:
                    items.append(item)
            except Exception as exc:
                logger.debug('[Chandarana] Skipping card: %s', exc)

        return items

    def _parse_card(self, card) -> Optional[dict]:
        link_el = card.query_selector('a.product-item-link')
        if not link_el:
            return None

        name = (link_el.inner_text() or link_el.get_attribute('title') or '').strip()
        if not name:
            return None

        href = link_el.get_attribute('href') or ''
        url  = href if href.startswith('http') else f'{BASE_URL}{href}'

        img_el = card.query_selector('.product-image-photo')
        image  = img_el.get_attribute('src') if img_el else None

        sale_el = card.query_selector('.special-price .price')
        old_el  = card.query_selector('.old-price .price')

        deal_price = self.parse_price(sale_el.inner_text()) if sale_el else None
        old_price  = self.parse_price(old_el.inner_text()) if old_el else None

        if not deal_price:
            return None

        return {
            'product_name': name,
            'external_id':  url,
            'product_url':  url,
            'image_url':    image,
            'price':        deal_price,
            'old_price':    old_price,
        }
