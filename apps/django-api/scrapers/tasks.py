"""
scrapers/tasks.py
------------------
Celery tasks for all three scrapers.
"""

import logging

from celery import group, shared_task

logger = logging.getLogger(__name__)


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
    try:
        run = NaivasScraper().run()
        return {
            'retailer': 'Naivas',
            'status':   run.status,
            'strategy': run.strategy,
            'found':    run.deals_found,
            'changed':  run.deals_changed,
        }
    except Exception as exc:
        logger.error('[Naivas] Task failed: %s', exc)
        raise self.retry(exc=exc)


# ── Quickmart ─────────────────────────────────────────────────────────────── #

@shared_task(name='scrapers.tasks.scrape_quickmart_all')
def scrape_quickmart_all():
    """Fan-out: fires one scrape_quickmart_branch task per active branch."""
    from core.models import RetailerBranch

    branches = RetailerBranch.objects.filter(
        retailer__name='Quickmart',
        is_active=True,
    ).values('name', 'external_id')

    if not branches:
        logger.warning(
            '[Quickmart] No active branches — add them via Django admin '
            'or run scrapers.tasks.discover_quickmart_branches'
        )
        return {'enqueued': 0}

    job = group(
        scrape_quickmart_branch.s(b['name'], b['external_id'])
        for b in branches
    )
    job.apply_async()
    logger.info('[Quickmart] Enqueued %d branch tasks', len(branches))
    return {'enqueued': len(branches)}


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=180,
    queue='quickmart-queue',
    name='scrapers.tasks.scrape_quickmart_branch',
)
def scrape_quickmart_branch(self, branch_name: str, branch_external_id: str = None):
    from scrapers.quickmart import QuickmartBranchScraper
    try:
        run = QuickmartBranchScraper(
            branch_name=branch_name,
            branch_external_id=branch_external_id,
        ).run()
        return {
            'retailer': 'Quickmart',
            'branch':   branch_name,
            'status':   run.status,
            'strategy': run.strategy,
            'found':    run.deals_found,
            'changed':  run.deals_changed,
        }
    except Exception as exc:
        logger.error('[Quickmart/%s] Task failed: %s', branch_name, exc)
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


# ── One-time: seed Quickmart branches ─────────────────────────────────────── #

@shared_task(name='scrapers.tasks.discover_quickmart_branches')
def discover_quickmart_branches():
    """
    Scrapes the Quickmart store locator and populates RetailerBranch.
    Run once before starting the beat schedule:

      python manage.py shell
      >>> from scrapers.tasks import discover_quickmart_branches
      >>> discover_quickmart_branches()

    If this fails (selector mismatch), add branches manually in
    Django admin → Core → Retailer branches.
    """
    import requests
    from bs4 import BeautifulSoup
    from core.models import Retailer, RetailerBranch

    try:
        retailer = Retailer.objects.get(name='Quickmart')
    except Retailer.DoesNotExist:
        logger.error('[Quickmart] Retailer not in DB — create it in Django admin first')
        return {'error': 'Retailer not found'}

    HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        )
    }

    created = 0
    try:
        resp = requests.get('https://www.quickmart.co.ke/stores', headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        els = (
            soup.select('.store-name')
            or soup.select('.location-name')
            or soup.select('h3.branch-title')
            or soup.select('[class*="store"] h3')
        )

        for el in els:
            name = el.get_text(strip=True)
            if name:
                _, was_created = RetailerBranch.objects.get_or_create(
                    retailer=retailer,
                    name=name,
                    defaults={'is_active': True},
                )
                if was_created:
                    created += 1

        logger.info('[Quickmart] Branch discovery: %d new branches created', created)

    except Exception as e:
        logger.error('[Quickmart] Branch discovery failed: %s', e)
        logger.info('Add branches manually: Django admin → Core → Retailer branches')

    return {'created': created}
