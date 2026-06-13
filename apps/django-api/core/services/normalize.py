"""
core/services/normalize.py
---------------------------
Promotes StagingProduct rows → Product + Deal + PriceHistory.

Bulk strategy (per batch of 500 rows):
  1. Pre-load Retailer / RetailerBranch / CategoryMapping caches once.
  2. Bulk-resolve RetailerCategories (one SELECT + one bulk_create per batch).
  3. Bulk-resolve Products by (retailer_id, name):
       one SELECT → split into new / changed → bulk_create + bulk_update.
  4. Same bulk pattern for Deals.
  5. bulk_create all PriceHistory records for the batch.
  6. Delete only fully-mapped staging rows (product + deal + master_category).
     Rows that have no master_category are left in staging for manual review.

~12 queries per 500-row batch vs ~600 k queries for the old per-row approach.

Category resolution uses three paths in order:
  1. Fast path: (retailer_id, cat_name) lookup in cat_map for L2 → L1 → L0.
     cat_map is pre-built from CategoryMapping (Tier 1 only). Covers the common
     case with zero extra queries per product.
  2. Full 4-tier pipeline: if the fast path misses on all three levels, falls
     back to CategoryMapper.map() which tries Tiers 1-4 (exact, synonym,
     keyword, fuzzy) across all levels.
  3. No match: master_category is left None. The staging row is NOT deleted —
     it stays in StagingProduct for manual review / re-run after mappings are
     updated.

Call from Celery:  scrapers.tasks.normalize_staging
Call manually:     from core.services.normalize import normalize_staging
"""
import logging
from collections import defaultdict

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

BATCH = 500


def normalize_staging(batch_size: int = BATCH) -> dict:
    from core.models import (
        CategoryMapping, Deal, PriceHistory, Product,
        Retailer, RetailerBranch, RetailerCategory, StagingProduct,
    )

    # ── One-time lookup caches ────────────────────────────────────────── #
    retailers   = {r.name: r for r in Retailer.objects.all()}
    branches    = {
        (b.retailer_id, b.name): b
        for b in RetailerBranch.objects.select_related('retailer').all()
    }
    # (retailer_id, cat_name) → master Category
    cat_map = {
        (m.retailer_category.retailer_id, m.retailer_category.name): m.master_category
        for m in CategoryMapping.objects.select_related(
            'retailer_category', 'master_category'
        ).all()
    }

    stats = dict(
        products_created=0, products_updated=0,
        deals_created=0,    deals_updated=0,
        history_written=0,  skipped=0,        errors=0,
    )

    while True:
        # Always fetch from the top — rows are deleted per batch so offset
        # shifts would skip unprocessed rows if we incremented an offset.
        batch = list(StagingProduct.objects.order_by('id')[:batch_size])
        if not batch:
            break

        try:
            _process_batch(
                batch, retailers, branches, cat_map, stats,
            )
        except Exception as exc:
            logger.error('normalize_staging: batch %d..%d failed: %s',
                         batch[0].id, batch[-1].id, exc)
            stats['errors'] += len(batch)
            # Delete the failed batch so we don't loop forever on it
            StagingProduct.objects.filter(id__in=[s.id for s in batch]).delete()

    logger.info(
        'normalize_staging done — products +%d ~%d | deals +%d ~%d | '
        'history +%d | skipped %d | errors %d',
        stats['products_created'], stats['products_updated'],
        stats['deals_created'],    stats['deals_updated'],
        stats['history_written'],  stats['skipped'],        stats['errors'],
    )
    return stats


# ── Batch processor ──────────────────────────────────────────────────────── #

def _process_batch(batch, retailers, branches, cat_map, stats) -> None:
    from core.models import (
        Deal, PriceHistory, Product, RetailerCategory, StagingProduct,
    )

    # Filter rows we can actually process
    valid: list[tuple] = []  # (sp, retailer, branch)
    for sp in batch:
        retailer = retailers.get(sp.retailer_name)
        if not retailer or sp.price is None:
            stats['skipped'] += 1
            continue
        branch = branches.get((retailer.id, sp.branch_name)) if sp.branch_name else None
        valid.append((sp, retailer, branch))

    if not valid:
        StagingProduct.objects.filter(id__in=[sp.id for sp in batch]).delete()
        return

    # ── 1. Bulk-resolve RetailerCategories ───────────────────────────── #
    # Collect (retailer_id, cat_name) pairs that have a category_name
    needed_cats: set[tuple] = {
        (retailer.id, sp.category_name)
        for sp, retailer, _ in valid
        if sp.category_name
    }
    # Fetch existing
    existing_rcats: dict[tuple, object] = {}
    if needed_cats:
        retailer_ids = {r for r, _ in needed_cats}
        cat_names    = {n for _, n in needed_cats}
        for rc in RetailerCategory.objects.filter(
            retailer_id__in=retailer_ids, name__in=cat_names
        ):
            existing_rcats[(rc.retailer_id, rc.name)] = rc

        # Bulk-create missing ones
        missing_rcats = [
            RetailerCategory(retailer_id=rid, name=cname)
            for rid, cname in needed_cats
            if (rid, cname) not in existing_rcats
        ]
        if missing_rcats:
            created = RetailerCategory.objects.bulk_create(
                missing_rcats, ignore_conflicts=True
            )
            # Re-fetch to get PKs (bulk_create may not set them on conflict)
            for rc in RetailerCategory.objects.filter(
                retailer_id__in=retailer_ids, name__in=cat_names
            ):
                existing_rcats[(rc.retailer_id, rc.name)] = rc

    def get_rcat(retailer_id, cat_name):
        if not cat_name:
            return None
        return existing_rcats.get((retailer_id, cat_name))

    # ── 2. Bulk-resolve Products ─────────────────────────────────────── #
    # Key: (retailer_id, product_name) → first staging row wins
    sp_by_product: dict[tuple, tuple] = {}
    for sp, retailer, branch in valid:
        key = (retailer.id, sp.product_name)
        if key not in sp_by_product:
            sp_by_product[key] = (sp, retailer, branch)

    retailer_ids_needed = {rid for rid, _ in sp_by_product}
    names_needed        = {name for _, name in sp_by_product}

    existing_products: dict[tuple, object] = {
        (p.retailer_id, p.name): p
        for p in Product.objects.filter(
            retailer_id__in=retailer_ids_needed,
            name__in=names_needed,
        ).select_related('retailer')
    }

    new_products:     list = []
    update_products:  list = []
    update_fields_set: dict = {}  # product_key → set of fields

    for (rid, name), (sp, retailer, branch) in sp_by_product.items():
        rcat = get_rcat(rid, sp.category_name)
        # Fast path: check L2 → L1 → L0 against cat_map (CategoryMapping Tier 1 only)
        master_cat = (
            cat_map.get((rid, sp.sub_category_2_name))
            or cat_map.get((rid, sp.sub_category_name))
            or cat_map.get((rid, sp.category_name))
        ) if sp.category_name else None

        # Full 4-tier pipeline if fast path missed
        if master_cat is None:
            try:
                from core.services.category_mapper import category_mapper as _cm
                _r = _cm.map(sp)
                if _r.matched:
                    master_cat = _r.category
            except Exception as _exc:
                logger.debug('category_mapper failed for %s: %s', sp.product_name, _exc)
        shelf_price   = sp.old_price if sp.old_price else sp.price

        existing = existing_products.get((rid, name))
        if existing is None:
            new_products.append(Product(
                retailer=retailer,
                name=name,
                price=shelf_price,
                url=sp.product_url,
                image_url=sp.image_url,
                retailer_category=rcat,
                master_category=master_cat,
            ))
        else:
            changed = []
            if shelf_price and existing.price != shelf_price:
                existing.price = shelf_price; changed.append('price')
            if sp.product_url and existing.url != sp.product_url:
                existing.url = sp.product_url; changed.append('url')
            if sp.image_url and existing.image_url != sp.image_url:
                existing.image_url = sp.image_url; changed.append('image_url')
            if rcat and existing.retailer_category_id != rcat.id:
                existing.retailer_category = rcat; changed.append('retailer_category')
            if master_cat and existing.master_category_id != master_cat.id:
                existing.master_category = master_cat; changed.append('master_category')
            if changed:
                update_products.append(existing)
                update_fields_set[(rid, name)] = changed

    if new_products:
        # ignore_conflicts=True: races between two concurrent normalize tasks
        # hitting the (retailer, name) unique constraint are silently skipped;
        # the re-fetch below loads the winner's row for the deal step.
        Product.objects.bulk_create(new_products, ignore_conflicts=True)
        stats['products_created'] += len(new_products)

    if update_products:
        all_update_fields = set()
        for fields in update_fields_set.values():
            all_update_fields.update(fields)
        Product.objects.bulk_update(update_products, list(all_update_fields))
        stats['products_updated'] += len(update_products)

    # Re-fetch to ensure PKs are set after bulk_create
    if new_products:
        for p in Product.objects.filter(
            retailer_id__in=retailer_ids_needed, name__in=names_needed
        ):
            existing_products[(p.retailer_id, p.name)] = p

    # ── 3. Bulk-resolve Deals ────────────────────────────────────────── #
    # Deal.unique_together = (product, retailer) → one deal per product per retailer
    product_pks = {p.id for p in existing_products.values() if p.id}
    existing_deals: dict[int, object] = {
        d.product_id: d
        for d in Deal.objects.filter(product_id__in=product_pks)
    }

    new_deals:    list = []
    update_deals: list = []
    history_rows: list = []

    # Iterate valid staging rows (not deduplicated — every row contributes to deals)
    for sp, retailer, branch in valid:
        product = existing_products.get((retailer.id, sp.product_name))
        if product is None or product.id is None:
            stats['errors'] += 1
            continue

        scraped_at  = sp.scraped_at or timezone.now()
        existing_deal = existing_deals.get(product.id)

        if existing_deal is None:
            new_deals.append(Deal(
                product=product,
                retailer=retailer,
                current_price=sp.price,
                old_price=sp.old_price,
                link=sp.product_url,
                scraped_at=scraped_at,
                branch=branch,
            ))
            history_rows.append(PriceHistory(
                product=product,
                retailer=retailer,
                branch=branch,
                price=sp.price,
                old_price=sp.old_price,
                source='scraper',
                recorded_at=scraped_at,
            ))
        elif existing_deal.current_price != sp.price:
            existing_deal.current_price = sp.price
            existing_deal.old_price     = sp.old_price
            existing_deal.link          = sp.product_url or existing_deal.link
            existing_deal.scraped_at    = scraped_at
            if branch:
                existing_deal.branch = branch
            update_deals.append(existing_deal)
            history_rows.append(PriceHistory(
                product=product,
                retailer=retailer,
                branch=branch,
                price=sp.price,
                old_price=sp.old_price,
                source='scraper',
                recorded_at=scraped_at,
            ))

    if new_deals:
        Deal.objects.bulk_create(new_deals, ignore_conflicts=True)
        stats['deals_created'] += len(new_deals)

    if update_deals:
        Deal.objects.bulk_update(
            update_deals,
            ['current_price', 'old_price', 'link', 'scraped_at', 'branch'],
        )
        stats['deals_updated'] += len(update_deals)

    if history_rows:
        PriceHistory.objects.bulk_create(history_rows, ignore_conflicts=False)
        stats['history_written'] += len(history_rows)

    # ── 4. Delete only fully-mapped staging rows ─────────────────────── #
    # Rows with no master_category stay in staging for manual review.
    to_delete_ids: list = []
    to_skip_ids: list = []

    for sp, retailer, branch in valid:
        product = existing_products.get((retailer.id, sp.product_name))
        if product and product.master_category_id:
            to_delete_ids.append(sp.id)
        else:
            to_skip_ids.append(sp.id)
            logger.debug(
                'Staging row %d (%s) has no master_category — leaving in staging',
                sp.id, sp.product_name)

    if to_delete_ids:
        StagingProduct.objects.filter(id__in=to_delete_ids).delete()

    logger.info(
        'Batch: deleted=%d kept_unmapped=%d',
        len(to_delete_ids), len(to_skip_ids))
