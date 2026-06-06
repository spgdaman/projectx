"""
scrapers/base.py
-----------------
Base class for all retailer scrapers.

Pattern:
  1. scrape_api()  — fast, clean, no browser
  2. On APIError   — falls back to _run_playwright_fallback() → scrape_web()
  3. Writes to StagingProduct (same table your CSV import uses)
  4. Records a ScraperRun for every execution

Dependencies (add to requirements.txt):
  playwright>=1.44.0
  beautifulsoup4>=4.12.0
  requests>=2.31.0
  redis>=5.0.0

After pip install: playwright install chromium
"""

import logging
import time
import traceback
from decimal import Decimal, InvalidOperation
from typing import Optional

import redis
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

_redis = redis.from_url(
    getattr(settings, 'REDIS_URL', 'redis://localhost:6379/1'),
    decode_responses=True,
)
PRICE_CACHE_TTL = 60 * 60 * 24 * 7  # 7 days


class APIError(Exception):
    """Raised inside scrape_api() to signal: try Playwright fallback."""


class ScraperError(Exception):
    """Raised when both API and Playwright fallback fail."""


class BaseScraper:
    """
    Subclasses must set:
      retailer_name: str          — must match Retailer.name in DB exactly

    Subclasses must implement:
      scrape_api()   → list[dict]   primary strategy; raise APIError on failure
      scrape_web(page) → list[dict] Playwright fallback; receives navigated Page

    Each dict must have at minimum:
      product_name: str
      price: Decimal | None

    Optional keys:
      external_id, product_url, image_url, old_price,
      category_name, sub_category_name, sub_category_2_name
    """

    retailer_name: str = None
    branch_name: Optional[str] = None
    branch_external_id: Optional[str] = None
    rate_limit_seconds: float = 0.4

    def __init__(self):
        if not self.retailer_name:
            raise NotImplementedError('Set retailer_name on the subclass')

        from core.models import Retailer, RetailerBranch
        self.retailer = Retailer.objects.get(name=self.retailer_name)
        self.branch = self._resolve_branch(RetailerBranch)

    def _resolve_branch(self, RetailerBranch):
        if not self.branch_name:
            return None
        branch, _ = RetailerBranch.objects.get_or_create(
            retailer=self.retailer,
            name=self.branch_name,
            defaults={
                'is_active': True,
                'external_id': self.branch_external_id,
            },
        )
        return branch

    # ── Price utilities ──────────────────────────────────────────────── #

    def parse_price(self, raw) -> Optional[Decimal]:
        if raw is None:
            return None
        try:
            import re
            cleaned = re.sub(r'[^\d.]', '', str(raw).replace(',', ''))
            return Decimal(cleaned) if cleaned else None
        except (InvalidOperation, Exception):
            return None

    def calc_discount_pct(
        self, original: Optional[Decimal], deal: Optional[Decimal]
    ) -> Optional[int]:
        if original and deal and original > deal:
            return int(((original - deal) / original) * 100)
        return None

    # ── Redis price-change gate ──────────────────────────────────────── #

    def _cache_key(self, external_id: str) -> str:
        branch_part = (
            self.branch.external_id or self.branch.name
            if self.branch else 'none'
        )
        return f'price:{self.retailer_name}:{branch_part}:{external_id}'

    def price_has_changed(self, external_id: str, new_price: Decimal) -> bool:
        key = self._cache_key(external_id)
        try:
            cached = _redis.get(key)
            _redis.set(key, str(new_price), ex=PRICE_CACHE_TTL)
        except Exception:
            # Redis unavailable — fail open so writes always proceed
            return True
        if cached is None:
            return True
        try:
            return Decimal(cached) != new_price
        except InvalidOperation:
            return True

    # ── Staging write ────────────────────────────────────────────────── #

    def write_to_staging(self, items: list, run) -> int:
        from core.models import StagingProduct

        written = new_count = skipped = 0
        for item in items:
            price = item.get('price')
            external_id = item.get('external_id') or item.get('product_name', '')

            if price and not self.price_has_changed(str(external_id), price):
                skipped += 1
                continue

            lookup = dict(
                retailer_name=self.retailer_name,
                branch_name=self.branch_name,
                product_name=item['product_name'],
            )
            defaults = {
                'category_name':       item.get('category_name'),
                'sub_category_name':   item.get('sub_category_name'),
                'sub_category_2_name': item.get('sub_category_2_name'),
                'product_url':         item.get('product_url'),
                'image_url':           item.get('image_url'),
                'price':               price,
                'old_price':           item.get('old_price'),
                'source':              'scraper',
                'is_manual':           False,
                'scraped_at':          timezone.now(),
            }
            qs = StagingProduct.objects.filter(**lookup)
            count = qs.count()
            if count > 1:
                qs.exclude(pk=qs.first().pk).delete()
                qs.update(**defaults)
            elif count == 1:
                qs.update(**defaults)
            else:
                StagingProduct.objects.create(**lookup, **defaults)
                new_count += 1
            written += 1

        run.deals_found += len(items)
        run.deals_changed += written
        run.products_new += new_count
        run.products_skipped += skipped
        run.save(update_fields=['deals_found', 'deals_changed', 'products_new', 'products_skipped'])
        return written

    def record_page_scraped(self, run, http_error: bool = False):
        """Call once per page/URL fetched to increment page and error counters."""
        run.pages_scraped += 1
        if http_error:
            run.http_errors += 1
        run.save(update_fields=['pages_scraped', 'http_errors'])

    # ── Playwright fallback ──────────────────────────────────────────── #

    def get_offers_url(self) -> str:
        raise NotImplementedError(
            f'{self.__class__.__name__} must implement get_offers_url()'
        )

    def scrape_web(self, page) -> list:
        raise NotImplementedError(
            f'{self.__class__.__name__} must implement scrape_web(page)'
        )

    def _run_playwright_fallback(self) -> list:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ScraperError(
                'Playwright not installed.\n'
                'Run: pip install playwright && playwright install chromium'
            )

        url = self.get_offers_url()
        logger.info('[%s] Fallback → Playwright: %s', self.retailer_name, url)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
                ),
                viewport={'width': 1280, 'height': 800},
                locale='en-US',
            )
            page = context.new_page()

            page.route(
                '**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,otf}',
                lambda route: route.abort(),
            )

            try:
                # domcontentloaded avoids hanging on sites with persistent
                # WebSocket / analytics connections (networkidle never fires)
                page.goto(url, wait_until='domcontentloaded', timeout=30_000)
                page.wait_for_timeout(2_000)
                items = self.scrape_web(page, run=getattr(self, '_current_run', None))
            finally:
                browser.close()

        return items

    # ── Subclass hooks ───────────────────────────────────────────────── #

    def scrape_api(self) -> list:
        raise NotImplementedError(
            f'{self.__class__.__name__} must implement scrape_api()'
        )

    # ── Main entry point ─────────────────────────────────────────────── #

    def run(self, force: bool = False):
        from datetime import timedelta
        from core.models import ScraperRun

        label = (
            f'{self.retailer_name}'
            + (f'/{self.branch_name}' if self.branch_name else '')
        )

        # Skip if a successful run finished within the last 2 hours.
        # Pass force=True (or set _force=True before calling run()) to bypass.
        if not force and not getattr(self, '_force', False):
            recent = ScraperRun.objects.filter(
                retailer=self.retailer,
                branch=self.branch,
                status='success',
                finished_at__gte=timezone.now() - timedelta(hours=2),
            ).exists()
            if recent:
                logger.info(
                    '[%s] Skipping — successful run completed within last 2 h', label
                )
                return None

        run = ScraperRun.objects.create(
            retailer=self.retailer,
            branch=self.branch,
            strategy='api',
            status='running',
        )
        self._current_run = run

        try:
            logger.info('[%s] Starting API strategy', label)
            items = self.scrape_api()
            run.strategy = 'api'
            run.save(update_fields=['strategy'])

        except APIError as api_err:
            logger.warning('[%s] API failed (%s) — trying Playwright', label, api_err)
            run.strategy = 'scraper'
            run.save(update_fields=['strategy'])

            try:
                items = self._run_playwright_fallback()
            except Exception as fb_err:
                full_tb = traceback.format_exc()
                logger.error('[%s] Playwright also failed: %s', label, fb_err)
                run.finish(status='failed', error=full_tb)
                raise ScraperError(f'{label}: both strategies failed') from fb_err

        except Exception:
            full_tb = traceback.format_exc()
            logger.exception('[%s] Unexpected error', label)
            run.finish(status='failed', error=full_tb)
            raise

        try:
            self.write_to_staging(items, run)
            run.finish(status='success')
        except Exception:
            full_tb = traceback.format_exc()
            run.finish(status='partial', error=full_tb)
            raise

        logger.info(
            '[%s] Done — found %d, changed %d (via %s)',
            label, run.deals_found, run.deals_changed, run.strategy,
        )
        return run
