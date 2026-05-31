"""
scrapers/naivas.py
-------------------
Naivas scraper — naivas.online (Laravel + Livewire, NOT Magento)

API strategy:
  naivas.online has no public REST API. The site uses Laravel Livewire and
  loads products server-side. The /rest/V1/products endpoint does not exist.
  scrape_api() immediately raises APIError to trigger the Playwright fallback.

Playwright strategy (primary working path):
  Navigates to /food-cupboard-deals (the main promo listing page).
  Product cards are Livewire child components. Selectors confirmed live:

  Card wrapper  : div[wire:id]:has(.product-price)
  Name          : a[wire:click="redirectToProductPage"] → title attribute
  URL           : a[wire:click="redirectToProductPage"] → href
  Image         : img inside the card
  Sale price    : .product-price .font-bold          (green, current price)
  Old price     : .product-price .line-through        (red, was-price)

  The page lazy-loads more products on scroll — we scroll 6x to capture ~45+ items.
  Additional deal pages (e.g. /beverage-deals) can be added to DEAL_PAGES.
"""

from typing import Optional

from .base import APIError, BaseScraper, logger

BASE_URL = 'https://www.naivas.online'

# Deal category pages to scrape. Add more as needed.
DEAL_PAGES = [
    f'{BASE_URL}/food-cupboard-deals',
    f'{BASE_URL}/fresh-deals',
    f'{BASE_URL}/beverage-deals',
    f'{BASE_URL}/beauty-cosmetics-deals',
    f'{BASE_URL}/cleaning-deals',
    f'{BASE_URL}/snacks-deals',
    f'{BASE_URL}/baby-kids-deals',
    f'{BASE_URL}/electronics-deals',
]


class NaivasScraper(BaseScraper):
    retailer_name = 'Naivas'
    rate_limit_seconds = 0.3

    def get_offers_url(self) -> str:
        return DEAL_PAGES[0]

    # ── API strategy — not available, go straight to Playwright ─────── #

    def scrape_api(self) -> list:
        raise APIError(
            'naivas.online has no public REST API — using Playwright scraper'
        )

    # ── Playwright strategy ──────────────────────────────────────────── #

    def scrape_web(self, page) -> list:
        """
        Scrape all DEAL_PAGES. Called by BaseScraper._run_playwright_fallback()
        which has already navigated to get_offers_url(). We navigate further
        pages ourselves.
        """
        all_items = []

        for page_url in DEAL_PAGES:
            logger.info('[Naivas] Scraping %s', page_url)
            try:
                resp = page.goto(page_url, wait_until='networkidle', timeout=30_000)
                if resp.status >= 400:
                    logger.warning('[Naivas] %s returned HTTP %d', page_url, resp.status)
                    continue
            except Exception as e:
                logger.warning('[Naivas] Failed to load %s: %s', page_url, e)
                continue

            # Scroll down to trigger Livewire lazy-loading
            for _ in range(6):
                page.keyboard.press('End')
                page.wait_for_timeout(1200)

            items = self._parse_page(page, page_url)
            logger.info('[Naivas] %s: %d products', page_url, len(items))
            all_items.extend(items)

        return all_items

    def _parse_page(self, page, page_url: str) -> list:
        items = []

        # Each product is a Livewire child component that contains .product-price
        try:
            cards = page.query_selector_all('div[wire\\:id]:has(.product-price)')
        except Exception:
            # :has() fallback — find via .product-price parent
            price_divs = page.query_selector_all('.product-price')
            cards = []
            seen_ids = set()
            for pd in price_divs:
                parent = pd.evaluate_handle(
                    'el => el.closest("[wire\\\\:id]")'
                ).as_element()
                if parent:
                    wid = parent.get_attribute('wire:id')
                    if wid and wid not in seen_ids:
                        seen_ids.add(wid)
                        cards.append(parent)

        if not cards:
            logger.warning('[Naivas] No product cards found on %s', page_url)
            return items

        logger.debug('[Naivas] %d product cards on %s', len(cards), page_url)

        for card in cards:
            try:
                item = self._parse_card(card)
                if item:
                    items.append(item)
            except Exception as e:
                logger.debug('[Naivas] Skipping card: %s', e)

        return items

    def _parse_card(self, card) -> Optional[dict]:
        # Name, URL, image from the product anchor
        link_el = card.query_selector('a[wire\\:click="redirectToProductPage"]')
        if not link_el:
            return None

        name = (link_el.get_attribute('title') or '').strip()
        if not name:
            return None

        href = link_el.get_attribute('href') or ''
        url  = href if href.startswith('http') else f'{BASE_URL}{href}'

        img_el = card.query_selector('img')
        image  = img_el.get_attribute('src') if img_el else None

        # Prices
        price_el = card.query_selector('.product-price .font-bold')
        old_el   = card.query_selector('.product-price .line-through')

        deal_price = self.parse_price(price_el.inner_text()) if price_el else None
        old_price  = self.parse_price(old_el.inner_text()) if old_el else None

        if not deal_price:
            return None

        # Extract product ID from pill span (id="pill-{id}")
        pill = card.query_selector('[id^="pill-"]')
        pid  = pill.get_attribute('id').replace('pill-', '') if pill else name

        return {
            'product_name': name,
            'external_id':  pid,
            'product_url':  url,
            'image_url':    image,
            'price':        deal_price,
            'old_price':    old_price,
        }
