"""
Normalize staged products into proper models:
  StagingProduct → Retailer / RetailerBranch / RetailerCategory / Product / Deal

Key behaviour
─────────────
• Deals are UPSERTED on (product, retailer) — one live row per product.
  PostgreSQL `ON CONFLICT DO UPDATE` keeps the table lean and the
  `scraped_at` timestamp always reflects the scraper's actual run time,
  not the normalization time.

• Products are upserted too: price, image_url, url, and master_category
  are refreshed if changed.

• StagingProduct rows with source='scraper' are filtered to only those
  touched since the last successful normalization (scraped_at >
  last_run), so CSV-only rows are not re-processed on every scraper run.
  Pass --all to force a full reprocess.

Usage
─────
  python manage.py normalize_staging
  python manage.py normalize_staging --all        # reprocess every row
  python manage.py normalize_staging --batch 500
  python manage.py normalize_staging --dry-run
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

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
        parser.add_argument("--batch", type=int, default=500)
        parser.add_argument(
            "--all",
            action="store_true",
            default=False,
            help="Reprocess all staging rows, not just recently scraped ones",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Preview without writing to the database",
        )

    def handle(self, *args, **options):
        batch_size: int = options["batch"]
        dry_run: bool = options["dry_run"]
        process_all: bool = options["all"]

        # Only reprocess scraper rows that are newer than the most recent
        # Deal.scraped_at — avoids reprocessing thousands of unchanged CSV rows
        # on every scraper run. CSV rows (scraped_at=None) are always included.
        qs = StagingProduct.objects.all()
        if not process_all:
            latest_deal = Deal.objects.order_by('-scraped_at').first()
            if latest_deal and latest_deal.scraped_at:
                qs = StagingProduct.objects.filter(
                    models_scraped_at_filter(latest_deal.scraped_at)
                )

        staged = list(qs.order_by('id'))
        total_staged = len(staged)
        self.stdout.write(f"Normalizing {total_staged} staged products...")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN — no writes."))

        # ── Pre-load lookup caches ────────────────────────────────────────────
        retailer_cache: dict[str, Retailer] = {
            r.name: r for r in Retailer.objects.all()
        }
        branch_cache: dict[tuple, RetailerBranch] = {
            (b.retailer_id, b.name): b for b in RetailerBranch.objects.all()
        }
        rcat_cache: dict[tuple, RetailerCategory] = {
            (rc.retailer_id, rc.name): rc
            for rc in RetailerCategory.objects.all()
        }
        mapping_cache: dict[int, int] = {
            m.retailer_category_id: m.master_category_id
            for m in CategoryMapping.objects.all()
        }
        product_cache: dict[tuple, Product] = {
            (p.retailer_id, p.name): p for p in Product.objects.all()
        }

        # ── Helpers ───────────────────────────────────────────────────────────

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

        def get_or_create_branch(retailer: Retailer, branch_name: str):
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

        # ── Main loop ─────────────────────────────────────────────────────────
        deals_to_upsert: list[Deal] = []
        products_to_update: list[Product] = []
        processed = skipped = new_products = updated_products = 0

        def flush_deals():
            if dry_run or not deals_to_upsert:
                deals_to_upsert.clear()
                return
            # PostgreSQL upsert: INSERT ... ON CONFLICT (product_id, retailer_id)
            # DO UPDATE SET current_price=…, old_price=…, link=…, scraped_at=…
            Deal.objects.bulk_create(
                deals_to_upsert,
                update_conflicts=True,
                unique_fields=['product', 'retailer'],
                update_fields=['current_price', 'old_price', 'link', 'scraped_at'],
            )
            deals_to_upsert.clear()

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

                master_category_id: Optional[int] = None
                if rcat and rcat.pk:
                    master_category_id = mapping_cache.get(rcat.pk)

                current_price = Decimal(str(sp.price))
                old_price = Decimal(str(sp.old_price)) if sp.old_price else None

                # Upsert Product
                pkey = (retailer.pk, sp.product_name)
                existing = product_cache.get(pkey)

                if existing:
                    changed = False
                    if existing.price != current_price:
                        existing.price = current_price
                        changed = True
                    if sp.image_url and existing.image_url != sp.image_url:
                        existing.image_url = sp.image_url
                        changed = True
                    if sp.product_url and existing.url != sp.product_url:
                        existing.url = sp.product_url
                        changed = True
                    if master_category_id and existing.master_category_id != master_category_id:
                        existing.master_category_id = master_category_id
                        changed = True
                    if rcat and rcat.pk and existing.retailer_category_id != rcat.pk:
                        existing.retailer_category_id = rcat.pk
                        changed = True
                    if changed and not dry_run:
                        products_to_update.append(existing)
                    product = existing
                    if changed:
                        updated_products += 1
                else:
                    product = Product(
                        retailer=retailer,
                        retailer_category=rcat,
                        name=sp.product_name,
                        price=current_price,
                        master_category_id=master_category_id,
                        url=sp.product_url or "",
                        image_url=sp.image_url or "",
                    )
                    if not dry_run:
                        product.save()
                    product_cache[pkey] = product
                    new_products += 1

                if product.pk:
                    deals_to_upsert.append(
                        Deal(
                            product=product,
                            retailer=retailer,
                            current_price=current_price,
                            old_price=old_price,
                            link=sp.product_url or "",
                            # Carry the scraper's actual timestamp; fall back to now
                            # for CSV rows that have no scraped_at
                            scraped_at=sp.scraped_at or timezone.now(),
                        )
                    )

                processed += 1

                if len(deals_to_upsert) >= batch_size:
                    flush_deals()

                if processed % 500 == 0:
                    self.stdout.write(f"  {processed}/{total_staged} processed...")

            if not dry_run and products_to_update:
                Product.objects.bulk_update(
                    products_to_update,
                    ["price", "image_url", "url", "master_category_id", "retailer_category_id"],
                )

            flush_deals()

            if not dry_run:
                from core.services.alerts import process_deal_alerts
                recent_deals = Deal.objects.order_by("-scraped_at")[:total_staged]
                for deal in recent_deals:
                    try:
                        process_deal_alerts(deal)
                    except Exception as exc:
                        logger.warning("Alert dispatch failed for deal %s: %s", deal.pk, exc)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. processed={processed} | "
                f"new_products={new_products} | "
                f"updated_products={updated_products} | "
                f"skipped={skipped}"
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN — no changes written."))


def models_scraped_at_filter(since):
    """
    Return a Q object: staging rows that are either:
      - CSV rows (scraped_at is null — always reprocess)
      - Scraper rows newer than `since`
    """
    from django.db.models import Q
    return Q(scraped_at__isnull=True) | Q(scraped_at__gt=since)
