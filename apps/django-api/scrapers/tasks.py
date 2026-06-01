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

    # external_id stores the full branch URL e.g. https://quickmart.co.ke/5301
    branches = list(
        RetailerBranch.objects.filter(
            retailer__name='Quickmart',
            is_active=True,
            external_id__isnull=False,
        ).values('name', 'external_id')
    )

    if not branches:
        logger.warning(
            '[Quickmart] No active branches with URLs — '
            'run scrapers.tasks.discover_quickmart_branches first'
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
def scrape_quickmart_branch(self, branch_name: str, branch_url: str):
    """
    Scrape one Quickmart branch.
    branch_url  — full URL, e.g. https://quickmart.co.ke/5301
                  stored in RetailerBranch.external_id
    """
    from scrapers.quickmart import QuickmartBranchScraper
    try:
        run = QuickmartBranchScraper(
            branch_name=branch_name,
            branch_url=branch_url,
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
