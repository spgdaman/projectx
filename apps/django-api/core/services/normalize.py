"""
core/services/normalize.py
---------------------------
Promotes StagingProduct rows → Product + Deal + PriceHistory.

Logic per staging row:
  1. Resolve Retailer (skip if unknown)
  2. Optionally resolve RetailerBranch and RetailerCategory
  3. get_or_create Product by (retailer, name); update url/image/price/category
  4. get_or_create Deal by (product, retailer); update if current_price changed
  5. Write PriceHistory only when the deal is new or the price changed
  6. Delete the staging row on success

Call from Celery:   scrapers.tasks.normalize_staging
Call manually:      from core.services.normalize import normalize_staging
"""
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def normalize_staging(batch_size: int = 500) -> dict:
    from core.models import (
        CategoryMapping, Deal, PriceHistory, Product, RetailerBranch,
        RetailerCategory, StagingProduct,
    )
    from core.models import Retailer

    # ── Pre-load lookup caches ────────────────────────────────────────── #
    retailers = {r.name: r for r in Retailer.objects.all()}

    branches: dict = {}
    for b in RetailerBranch.objects.select_related('retailer').all():
        branches[(b.retailer_id, b.name)] = b

    # (retailer_id, category_name) → master Category
    cat_map: dict = {}
    for m in CategoryMapping.objects.select_related(
        'retailer_category', 'master_category'
    ).all():
        cat_map[(m.retailer_category.retailer_id, m.retailer_category.name)] = (
            m.master_category
        )

    stats = dict(
        products_created=0, products_updated=0,
        deals_created=0,    deals_updated=0,
        history_written=0,  skipped=0,         errors=0,
    )

    processed_ids: list[int] = []

    offset = 0
    while True:
        batch = list(StagingProduct.objects.all().order_by('id')[offset: offset + batch_size])
        if not batch:
            break

        for sp in batch:
            try:
                _promote_one(sp, retailers, branches, cat_map, stats)
                processed_ids.append(sp.id)
            except Exception as exc:
                logger.error(
                    'normalize_staging: StagingProduct %d (%s / %s) failed: %s',
                    sp.id, sp.retailer_name, sp.product_name, exc,
                )
                stats['errors'] += 1

        offset += batch_size

    if processed_ids:
        deleted, _ = StagingProduct.objects.filter(id__in=processed_ids).delete()
        logger.info('normalize_staging: deleted %d staging rows', deleted)

    logger.info(
        'normalize_staging: products +%d ~%d | deals +%d ~%d | '
        'history +%d | skipped %d | errors %d',
        stats['products_created'], stats['products_updated'],
        stats['deals_created'],    stats['deals_updated'],
        stats['history_written'],  stats['skipped'],        stats['errors'],
    )
    return stats


# ── Internal helpers ─────────────────────────────────────────────────────── #

def _promote_one(sp, retailers, branches, cat_map, stats) -> None:
    from core.models import Deal, PriceHistory, Product, RetailerCategory

    retailer = retailers.get(sp.retailer_name)
    if not retailer:
        logger.warning('normalize_staging: unknown retailer %r — skipping', sp.retailer_name)
        stats['skipped'] += 1
        return

    if sp.price is None:
        stats['skipped'] += 1
        return

    branch = branches.get((retailer.id, sp.branch_name)) if sp.branch_name else None

    # ── RetailerCategory + master category ───────────────────────────── #
    retailer_category = None
    master_category = None
    if sp.category_name:
        retailer_category, _ = RetailerCategory.objects.get_or_create(
            retailer=retailer,
            name=sp.category_name,
        )
        master_category = cat_map.get((retailer.id, sp.category_name))

    # ── Product ───────────────────────────────────────────────────────── #
    # Shelf price is the undiscounted price; use old_price when available.
    shelf_price = sp.old_price if sp.old_price else sp.price

    product, created = Product.objects.get_or_create(
        retailer=retailer,
        name=sp.product_name,
        defaults={
            'price':             shelf_price,
            'url':               sp.product_url,
            'image_url':         sp.image_url,
            'retailer_category': retailer_category,
            'master_category':   master_category,
        },
    )

    if created:
        stats['products_created'] += 1
    else:
        update_fields = []
        if sp.product_url and product.url != sp.product_url:
            product.url = sp.product_url
            update_fields.append('url')
        if sp.image_url and product.image_url != sp.image_url:
            product.image_url = sp.image_url
            update_fields.append('image_url')
        if shelf_price and product.price != shelf_price:
            product.price = shelf_price
            update_fields.append('price')
        if retailer_category and product.retailer_category_id != retailer_category.id:
            product.retailer_category = retailer_category
            update_fields.append('retailer_category')
        if master_category and product.master_category_id != master_category.id:
            product.master_category = master_category
            update_fields.append('master_category')
        if update_fields:
            product.save(update_fields=update_fields)
            stats['products_updated'] += 1

    # ── Deal ──────────────────────────────────────────────────────────── #
    scraped_at = sp.scraped_at or timezone.now()

    deal, deal_created = Deal.objects.get_or_create(
        product=product,
        retailer=retailer,
        defaults={
            'current_price': sp.price,
            'old_price':     sp.old_price,
            'link':          sp.product_url,
            'scraped_at':    scraped_at,
            'branch':        branch,
        },
    )

    if deal_created:
        stats['deals_created'] += 1
        _write_history(product, retailer, branch, sp.price, sp.old_price, scraped_at)
        stats['history_written'] += 1
    elif deal.current_price != sp.price:
        deal.current_price = sp.price
        deal.old_price     = sp.old_price
        deal.link          = sp.product_url or deal.link
        deal.scraped_at    = scraped_at
        if branch:
            deal.branch = branch
        deal.save(update_fields=['current_price', 'old_price', 'link', 'scraped_at', 'branch'])
        stats['deals_updated'] += 1
        _write_history(product, retailer, branch, sp.price, sp.old_price, scraped_at)
        stats['history_written'] += 1


def _write_history(product, retailer, branch, price, old_price, recorded_at) -> None:
    from core.models import PriceHistory

    PriceHistory.objects.create(
        product=product,
        retailer=retailer,
        branch=branch,
        price=price,
        old_price=old_price,
        source='scraper',
        recorded_at=recorded_at,
    )
