"""
Ingest product CSV files into StagingProduct.

Supports two CSV formats (auto-detected):
  - Naivas format: columns include 'category', 'sub_category_1', 'sub_category_2', 'product_url', 'image_url'
  - Quickmart format: columns include 'category_name', 'sub_category_name', 'branch_name', 'product_link'

Usage:
  python manage.py ingest_products path/to/file.csv
  python manage.py ingest_products path/to/file.csv --append      # keep existing staging rows
  python manage.py ingest_products path/to/file.csv --batch 500   # bulk-insert batch size
"""

import csv
import sys
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import StagingProduct


PRICE_PERIODS = [7, 14, 21, 30]  # fall back through these periods for price data


def _coerce_price(value: str | None) -> Decimal | None:
    """Return a Decimal or None; ignore empty/invalid strings."""
    if not value or not str(value).strip():
        return None
    try:
        d = Decimal(str(value).strip())
        return d if d > 0 else None
    except InvalidOperation:
        return None


def _best_price(row: dict, prefix: str) -> Decimal | None:
    """Try price columns for multiple periods and return the first non-null value."""
    for period in PRICE_PERIODS:
        val = _coerce_price(row.get(f"{prefix}{period}"))
        if val is not None:
            return val
    return None


def _parse_naivas(row: dict) -> dict:
    return dict(
        retailer_name=row.get("retailer", "").strip(),
        category_name=(row.get("category") or "").strip() or None,
        sub_category_name=(row.get("sub_category_1") or "").strip() or None,
        sub_category_2_name=(row.get("sub_category_2") or "").strip() or None,
        product_name=(row.get("product_name") or "").strip(),
        product_url=(row.get("product_url") or "").strip() or None,
        image_url=(row.get("image_url") or "").strip() or None,
        price=_best_price(row, "last_new_price_"),
        old_price=_best_price(row, "last_old_price_"),
        is_manual=False,
    )


def _parse_quickmart(row: dict) -> dict:
    return dict(
        retailer_name=row.get("retailer", "").strip(),
        branch_name=(row.get("branch_name") or "").strip() or None,
        category_name=(row.get("category_name") or "").strip() or None,
        sub_category_name=(row.get("sub_category_name") or "").strip() or None,
        product_name=(row.get("product_name") or "").strip(),
        product_url=(row.get("product_link") or "").strip() or None,
        price=_best_price(row, "last_new_price_"),
        old_price=_best_price(row, "last_old_price_"),
        is_manual=False,
    )


class Command(BaseCommand):
    help = "Ingest product CSV files (Naivas / Quickmart) into the staging table"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to CSV file")
        parser.add_argument(
            "--append",
            action="store_true",
            default=False,
            help="Append to existing staging rows instead of clearing first",
        )
        parser.add_argument(
            "--batch",
            type=int,
            default=500,
            help="Bulk-insert batch size (default: 500)",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        append = options["append"]
        batch_size = options["batch"]

        if not append:
            deleted, _ = StagingProduct.objects.all().delete()
            self.stdout.write(f"Cleared {deleted} existing staging rows.")

        # Detect encoding — try UTF-8-BOM first, fall back to UTF-8
        encodings = ["utf-8-sig", "utf-8", "latin-1"]
        rows = []
        detected_fmt = None

        for enc in encodings:
            try:
                with open(csv_file, newline="", encoding=enc) as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    if rows:
                        detected_fmt = "naivas" if "category" in rows[0] else "quickmart"
                    break
            except (UnicodeDecodeError, OSError) as e:
                self.stderr.write(f"Encoding {enc} failed: {e}")
                continue

        if not rows:
            self.stderr.write(self.style.ERROR("Could not read CSV file."))
            sys.exit(1)

        self.stdout.write(
            f"Detected format: {detected_fmt}  |  Rows: {len(rows)}  |  Batch: {batch_size}"
        )

        parse = _parse_naivas if detected_fmt == "naivas" else _parse_quickmart

        to_create: list[StagingProduct] = []
        skipped = 0
        total = 0

        with transaction.atomic():
            for row in rows:
                data = parse(row)

                if not data["product_name"]:
                    skipped += 1
                    continue
                if data["price"] is None:
                    skipped += 1
                    continue

                to_create.append(StagingProduct(**data))

                if len(to_create) >= batch_size:
                    StagingProduct.objects.bulk_create(to_create, ignore_conflicts=False)
                    total += len(to_create)
                    self.stdout.write(f"  Inserted {total} rows...")
                    to_create = []

            if to_create:
                StagingProduct.objects.bulk_create(to_create, ignore_conflicts=False)
                total += len(to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Ingested {total} products ({skipped} skipped — missing name or price)."
            )
        )
