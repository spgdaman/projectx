"""
scrapers/tasks.py
------------------
Celery tasks for all four scrapers + staging normalization.
"""

import contextlib
import logging

import redis as redis_lib
from celery import group, shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


# ── Distributed scraper lock ──────────────────────────────────────────────── #

@contextlib.contextmanager
def scraper_lock(retailer_name: str, timeout: int = 3600):
    """
    Acquire a Redis NX lock for a scraper run. Yields True if acquired,
    False if another worker already holds the lock. Always releases on exit.
    timeout: seconds before Redis auto-expires the key (safety net for crashes).
    """
    r = redis_lib.from_url(
        getattr(settings, 'REDIS_URL', 'redis://localhost:6379/1'),
        decode_responses=True,
    )
    key = f'scraper_lock:{retailer_name}'
    acquired = r.set(key, '1', nx=True, ex=timeout)
    try:
        yield acquired
    finally:
        if acquired:
            r.delete(key)


# ── Orphan reaper ─────────────────────────────────────────────────────────── #

@shared_task(
    name='scrapers.tasks.reap_orphaned_runs',
    queue='default',
)
def reap_orphaned_runs():
    """
    Mark any ScraperRun stuck in 'running' for > 2 h as failed.
    Guards against worker crashes or pod evictions that skip the finish() call.
    """
    from django.utils import timezone
    from datetime import timedelta
    from core.models import ScraperRun

    cutoff = timezone.now() - timedelta(hours=2)
    qs = ScraperRun.objects.filter(status='running', started_at__lt=cutoff)
    count = qs.update(
        status='failed',
        finished_at=timezone.now(),
        error='Orphaned — worker terminated before completion',
    )
    if count:
        logger.warning('[reaper] Marked %d orphaned run(s) as failed', count)
    return {'reaped': count}


# ── Staging → Products / Deals ────────────────────────────────────────────── #

@shared_task(
    name='scrapers.tasks.normalize_staging',
    queue='default',
    max_retries=2,
    default_retry_delay=60,
)
def normalize_staging():
    """Drain StagingProduct → Product + Deal + PriceHistory."""
    from core.services.normalize import normalize_staging as _run
    result = _run()
    process_alerts_task.delay()
    return result


@shared_task(name='core.tasks.process_alerts', queue='default')
def process_alerts_task():
    """Run after every normalize_staging completes and on the 4-hour schedule."""
    from django.core.management import call_command
    call_command('process_alerts')


# ── Naivas ─────────────────────────────────────────────────────────────────── #

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    queue='naivas-queue',
    name='scrapers.tasks.scrape_naivas',
)
def scrape_naivas(self):
    from scrapers.naivas import NaivasScraper
    with scraper_lock('naivas') as acquired:
        if not acquired:
            logger.info('[Naivas] Already running — skipping duplicate task')
            return {'skipped': 'locked'}
        try:
            run = NaivasScraper().run()
            if run is None:
                return {'skipped': 'recent_run_exists'}
            run.celery_task_id = self.request.id or ''
            run.save(update_fields=['celery_task_id'])
            normalize_staging.delay()
            return {
                'retailer':         'Naivas',
                'status':           run.status,
                'strategy':         run.strategy,
                'found':            run.deals_found,
                'changed':          run.deals_changed,
                'new':              run.products_new,
                'skipped':          run.products_skipped,
                'pages':            run.pages_scraped,
                'http_errors':      run.http_errors,
                'duration_seconds': run.duration_seconds,
            }
        except Exception as exc:
            logger.error('[Naivas] Task failed: %s', exc)
            raise self.retry(exc=exc)


# ── Quickmart ─────────────────────────────────────────────────────────────── #

# QUICKMART SCRAPING PAUSED
# Branch-specific Playwright produces one Playwright instance per branch (~200–300 MB each).
# With 9+ branches this OOMs the worker. Scheduled scraping is disabled until a lightweight
# API endpoint is confirmed via DevTools. Use: python manage.py scrape_quickmart (manual only).
# Re-enable by removing the early-return guards below and adding scrape-quickmart back to
# CELERY_BEAT_SCHEDULE in settings.py.

@shared_task(name='scrapers.tasks.scrape_quickmart_all')
def scrape_quickmart_all():
    """Fan-out: fires one scrape_quickmart_branch task per active branch."""
    logger.warning(
        '[Quickmart] Scheduled scraping is PAUSED. '
        'Run manually: python manage.py scrape_quickmart'
    )
    return {'status': 'paused'}


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=180,
    queue='quickmart-queue',
    name='scrapers.tasks.scrape_quickmart_branch',
)
def scrape_quickmart_branch(self, branch_name: str, branch_url: str):
    """
    Scrape one Quickmart branch.
    branch_url  — full URL, e.g. https://quickmart.co.ke/5301
                  stored in RetailerBranch.external_id
    """
    logger.warning(
        '[Quickmart/%s] Branch scraping is PAUSED. '
        'Run manually: python manage.py scrape_quickmart',
        branch_name,
    )
    return {'status': 'paused', 'branch': branch_name}


# ── Chandarana ────────────────────────────────────────────────────────────── #

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    queue='chandarana-queue',
    name='scrapers.tasks.scrape_chandarana',
)
def scrape_chandarana(self):
    from scrapers.chandarana import ChandaranaScraper
    with scraper_lock('chandarana') as acquired:
        if not acquired:
            logger.info('[Chandarana] Already running — skipping duplicate task')
            return {'skipped': 'locked'}
        try:
            run = ChandaranaScraper().run()
            if run is None:
                return {'skipped': 'recent_run_exists'}
            run.celery_task_id = self.request.id or ''
            run.save(update_fields=['celery_task_id'])
            normalize_staging.delay()
            return {
                'retailer':         'Chandarana',
                'status':           run.status,
                'strategy':         run.strategy,
                'found':            run.deals_found,
                'changed':          run.deals_changed,
                'new':              run.products_new,
                'skipped':          run.products_skipped,
                'pages':            run.pages_scraped,
                'http_errors':      run.http_errors,
                'duration_seconds': run.duration_seconds,
            }
        except Exception as exc:
            logger.error('[Chandarana] Task failed: %s', exc)
            raise self.retry(exc=exc)


# ── Carrefour ─────────────────────────────────────────────────────────────── #

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    queue='carrefour-queue',
    name='scrapers.tasks.scrape_carrefour',
)
def scrape_carrefour(self):
    from scrapers.carrefour import CarrefourScraper
    try:
        run = CarrefourScraper().run()
        normalize_staging.delay()
        return {
            'retailer': 'Carrefour',
            'status':   run.status,
            'strategy': run.strategy,
            'found':    run.deals_found,
            'changed':  run.deals_changed,
        }
    except Exception as exc:
        logger.error('[Carrefour] Task failed: %s', exc)
        raise self.retry(exc=exc)


# ── One-time: seed Quickmart branches via Playwright ─────────────────────── #

@shared_task(name='scrapers.tasks.discover_quickmart_branches')
def discover_quickmart_branches():
    """
    Use Playwright to scrape quickmart.co.ke/shops and populate RetailerBranch.
    Stores the full branch URL in external_id so scrape_quickmart_branch
    can navigate directly.

    Run once before the beat schedule:
      python manage.py shell
      >>> from scrapers.tasks import discover_quickmart_branches
      >>> discover_quickmart_branches()
    """
    from playwright.sync_api import sync_playwright
    from core.models import Retailer, RetailerBranch

    try:
        retailer = Retailer.objects.get(name='Quickmart')
    except Retailer.DoesNotExist:
        logger.error('[Quickmart] Retailer not in DB — create it in Django admin first')
        return {'error': 'Retailer not found'}

    try:
        from scrapers.quickmart import discover_branches, UA
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=UA,
                viewport={'width': 1280, 'height': 900},
            )
            page = ctx.new_page()
            branches = discover_branches(page)
            browser.close()
    except Exception as e:
        logger.error('[Quickmart] Branch discovery failed: %s', e)
        return {'error': str(e)}

    created = updated = 0
    for b in branches:
        obj, was_created = RetailerBranch.objects.get_or_create(
            retailer=retailer,
            name=b['name'],
            defaults={
                'is_active':   True,
                'external_id': b['url'],  # full URL e.g. https://quickmart.co.ke/5301
            },
        )
        if was_created:
            created += 1
        elif obj.external_id != b['url']:
            # Update URL if it changed
            obj.external_id = b['url']
            obj.save(update_fields=['external_id'])
            updated += 1

    logger.info('[Quickmart] Branch discovery: %d created, %d updated', created, updated)
    return {'total': len(branches), 'created': created, 'updated': updated}
