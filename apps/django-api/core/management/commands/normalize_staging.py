"""
Normalize staged products into proper models:
  StagingProduct → Retailer / RetailerBranch / RetailerCategory / Product / Deal

Performance notes:
- All lookups are pre-cached in memory dicts to eliminate N+1 queries.
- Products and Deals are bulk-inserted per batch.
- The whole run is wrapped in a single transaction for atomicity.

Usage:
  python manage.py normalize_staging
  python manage.py normalize_staging --batch 500
  python manage.py normalize_staging --dry-run   # preview only, no DB writes
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    CategoryMapping,
    Deal,
    Product,
    Retailer,
    RetailerBranch,
    RetailerCategory,
    StagingProduct,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Normalize staged products into Retailer/Product/Deal tables"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch",
            type=int,
            default=500,
            help="Bulk-insert batch size for Deals (default: 500)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Preview normalization without writing to the database",
        )

    def handle(self, *args, **options):
        batch_size: int = options["batch"]
        dry_run: bool = options["dry_run"]

        staged = list(StagingProduct.objects.all())
        total_staged = len(staged)
        self.stdout.write(f"Normalizing {total_staged} staged products...")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN mode — no database writes."))

        # ── Pre-load lookup caches ────────────────────────────────────────────
        # Retailer cache: name → Retailer
        retailer_cache: dict[str, Retailer] = {
            r.name: r for r in Retailer.objects.all()
        }
        # RetailerBranch cache: (retailer_id, branch_name) → RetailerBranch
        branch_cache: dict[tuple, RetailerBranch] = {
            (b.retailer_id, b.name): b for b in RetailerBranch.objects.all()
        }
        # RetailerCategory cache: (retailer_id, cat_name) → RetailerCategory
        rcat_cache: dict[tuple, RetailerCategory] = {
            (rc.retailer_id, rc.name): rc
            for rc in RetailerCategory.objects.all()
        }
        # CategoryMapping cache: retailer_category_id → master_category_id
        mapping_cache: dict[int, int] = {
            m.retailer_category_id: m.master_category_id
            for m in CategoryMapping.objects.select_related("master_category").all()
        }
        # Product cache: (retailer_id, name) → Product
        product_cache: dict[tuple, Product] = {
            (p.retailer_id, p.name): p
            for p in Product.objects.all()
        }

        def get_or_create_retailer(name: str) -> Optional[Retailer]:
            if not name:
                return None
            if name not in retailer_cache:
                if not dry_run:
                    obj, _ = Retailer.objects.get_or_create(name=name)
                    retailer_cache[name] = obj
                else:
                    retailer_cache[name] = Retailer(name=name)
            return retailer_cache[name]

        def get_or_create_branch(retailer: Retailer, branch_name: str) -> Optional[RetailerBranch]:
            if not branch_name:
                return None
            key = (retailer.pk, branch_name)
            if key not in branch_cache:
                if not dry_run:
                    obj, _ = RetailerBranch.objects.get_or_create(
                        retailer=retailer, name=branch_name
                    )
                    branch_cache[key] = obj
                else:
                    branch_cache[key] = RetailerBranch(retailer=retailer, name=branch_name)
            return branch_cache[key]

        def get_or_create_rcat(retailer: Retailer, cat_name: str) -> Optional[RetailerCategory]:
            if not cat_name or not cat_name.strip():
                return None
            name = cat_name.strip()
            key = (retailer.pk, name)
            if key not in rcat_cache:
                if not dry_run:
                    obj, _ = RetailerCategory.objects.get_or_create(
                        retailer=retailer, name=name
                    )
                    rcat_cache[key] = obj
                else:
                    rcat_cache[key] = RetailerCategory(retailer=retailer, name=name)
            return rcat_cache[key]

        # ── Process each staged product ───────────────────────────────────────
        deals_to_create: list[Deal] = []
        products_to_update: list[Product] = []
        processed = 0
        skipped = 0
        new_products = 0
        updated_products = 0

        def flush_deals():
            if not dry_run and deals_to_create:
                Deal.objects.bulk_create(deals_to_create, ignore_conflicts=False)
            deals_to_create.clear()

        with transaction.atomic():
            for sp in staged:
                if not sp.price:
                    skipped += 1
                    continue

                retailer = get_or_create_retailer(sp.retailer_name)
                if not retailer:
                    skipped += 1
                    continue

                get_or_create_branch(retailer, sp.branch_name)

                rcat = get_or_create_rcat(retailer, sp.category_name)

                # Resolve master category from mapping cache
                master_category_id: Optional[int] = None
                if rcat and rcat.pk:
                    master_category_id = mapping_cache.get(rcat.pk)

                current_price = Decimal(str(sp.price))
                old_price = Decimal(str(sp.old_price)) if sp.old_price else None

                # Upsert Product via cache
                pkey = (retailer.pk, sp.product_name)
                existing = product_cache.get(pkey)

                if existing:
                    changed = False
                    if existing.price != current_price:
                        existing.price = current_price
                        changed = True
                    if master_category_id and existing.master_category_id != master_category_id:
                        existing.master_category_id = master_category_id
                        changed = True
                    if rcat and existing.retailer_category_id != rcat.pk:
                        existing.retailer_category_id = rcat.pk if rcat.pk else None
                        changed = True
                    if changed and not dry_run:
                        products_to_update.append(existing)
                    product = existing
                    updated_products += 1 if changed else 0
                else:
                    product = Product(
                        retailer=retailer,
                        retailer_category=rcat,
                        name=sp.product_name,
                        price=current_price,
                        master_category_id=master_category_id,
                        url=sp.product_url or "",
                    )
                    if not dry_run:
                        product.save()
                    product_cache[pkey] = product
                    new_products += 1

                # Queue Deal record
                if product.pk:
                    deals_to_create.append(
                        Deal(
                            product=product,
                            retailer=retailer,
                            current_price=current_price,
                            old_price=old_price,
                            link=sp.product_url or "",
                        )
                    )

                processed += 1

                if len(deals_to_create) >= batch_size:
                    flush_deals()

                if processed % 500 == 0:
                    self.stdout.write(f"  {processed}/{total_staged} processed...")

            # Bulk-update changed products
            if not dry_run and products_to_update:
                Product.objects.bulk_update(
                    products_to_update,
                    ["price", "master_category_id", "retailer_category_id"],
                )

            flush_deals()

            if not dry_run:
                # Fire alerts for newly created deals (done after bulk insert)
                from core.services.alerts import process_deal_alerts
                recent_deals = Deal.objects.order_by("-id")[: len(staged)]
                for deal in recent_deals:
                    try:
                        process_deal_alerts(deal)
                    except Exception as exc:
                        logger.warning("Alert dispatch failed for deal %s: %s", deal.pk, exc)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Processed {processed} | "
                f"New products: {new_products} | "
                f"Updated: {updated_products} | "
                f"Skipped: {skipped}"
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN — no changes were written."))
