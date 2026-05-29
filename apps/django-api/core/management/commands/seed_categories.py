"""
Seed master categories and map retailer categories to them.

Creates the full Category hierarchy derived from the Naivas + Quickmart data,
then creates CategoryMapping entries for every matched RetailerCategory.

Safe to run multiple times — uses get_or_create throughout.

Usage:
    python manage.py seed_categories
    python manage.py seed_categories --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Category, CategoryMapping, RetailerCategory

# ── Master category tree ──────────────────────────────────────────────────────
# Format: { "Parent Name": ["Child 1", "Child 2", ...], ... }
# A parent with an empty list is a leaf / flat category.

CATEGORY_TREE = {
    "Electronics & Appliances": [
        "Large Appliances",
        "Small Kitchen Appliances",
        "TV & Audio",
        "Phones & Tablets",
        "Electrical Accessories",
    ],
    "Food & Beverages": [
        "Beverages",
        "Fresh Produce",
        "Meat, Fish & Eggs",
        "Dairy Products",
        "Bakery & Deli",
        "Breakfast & Cereals",
        "Cooking Oils & Fats",
        "Pasta, Rice & Grains",
        "Snacks & Confectionery",
        "Condiments & Seasoning",
        "Frozen Foods",
    ],
    "Personal Care": [
        "Body & Skin Care",
        "Hair Care",
        "Oral Care",
        "Sanitary Products",
        "Baby Care & Diapers",
        "Beauty & Cosmetics",
        "Health & Wellness",
    ],
    "Home Care": [
        "Laundry & Detergents",
        "Surface Cleaners",
        "Cleaning Equipment",
        "Tissue & Paper Products",
        "Air Fresheners & Candles",
        "Pest Control",
    ],
    "Household & Kitchen": [
        "Kitchen & Dining",
        "Furniture",
        "Home Textiles",
        "Home Improvement & Hardware",
        "Toys & Games",
        "Bicycles & Outdoor",
        "Car Care",
        "Cookers & Ovens",
    ],
    "Liquor": [
        "Beer & Cider",
        "Wines",
        "Spirits & Liqueurs",
    ],
    "Fashion & Accessories": [
        "Luggage & Bags",
    ],
    "Pet & Animal Care": [],
}

# ── Retailer category → master category mapping ───────────────────────────────
# Each entry: (retailer_name_fragment, retailer_cat_name, master_cat_name)
# retailer_name_fragment is matched case-insensitively against Retailer.name.

RETAILER_MAPPINGS = [
    # Naivas
    ("naivas", "Electronics",       "Electronics & Appliances"),
    ("naivas", "Beverage",          "Food & Beverages"),
    ("naivas", "Food Cupboard",     "Food & Beverages"),
    ("naivas", "Fresh Food",        "Food & Beverages"),
    ("naivas", "Beauty & Cosmetics","Personal Care"),
    # Quickmart
    ("quickmart", "ELECTRONICS",   "Electronics & Appliances"),
    ("quickmart", "FOODS",         "Food & Beverages"),
    ("quickmart", "FRESH",         "Food & Beverages"),
    ("quickmart", "HOMECARE",      "Home Care"),
    ("quickmart", "HOUSEHOLDS",    "Household & Kitchen"),
    ("quickmart", "LIQUOR",        "Liquor"),
    ("quickmart", "PERSONAL CARE", "Personal Care"),
    ("quickmart", "TEXTILE",       "Fashion & Accessories"),
]


class Command(BaseCommand):
    help = "Seed master categories and map retailer categories"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Preview what would be created without writing to the database",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN — no changes will be written.\n"))

        cats_created = 0
        mappings_created = 0
        mappings_skipped = 0

        with transaction.atomic():

            # ── Step 1: Create category hierarchy ────────────────────────────
            self.stdout.write("Creating master categories...")
            master_cat_objects: dict[str, Category] = {}

            for parent_name, children in CATEGORY_TREE.items():
                if dry_run:
                    self.stdout.write(f"  [DRY] Would create: {parent_name}")
                    parent_obj = Category(name=parent_name)
                else:
                    parent_obj, created = Category.objects.get_or_create(
                        name=parent_name, parent=None
                    )
                    if created:
                        cats_created += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"  + Created: {parent_name}")
                        )
                    else:
                        self.stdout.write(f"  · Exists:  {parent_name}")

                master_cat_objects[parent_name] = parent_obj

                for child_name in children:
                    if dry_run:
                        self.stdout.write(f"       [DRY] Would create: {parent_name} → {child_name}")
                    else:
                        child_obj, created = Category.objects.get_or_create(
                            name=child_name, parent=parent_obj
                        )
                        if created:
                            cats_created += 1
                            self.stdout.write(
                                self.style.SUCCESS(f"       + {parent_name} → {child_name}")
                            )

            # ── Step 2: Map retailer categories ──────────────────────────────
            self.stdout.write("\nMapping retailer categories...")

            for retailer_fragment, rcat_name, master_name in RETAILER_MAPPINGS:
                # Find the retailer category
                try:
                    rcat = RetailerCategory.objects.select_related("retailer").get(
                        retailer__name__icontains=retailer_fragment,
                        name=rcat_name,
                    )
                except RetailerCategory.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ! Not found: [{retailer_fragment}] {rcat_name!r} — skipping"
                        )
                    )
                    continue
                except RetailerCategory.MultipleObjectsReturned:
                    rcat = RetailerCategory.objects.filter(
                        retailer__name__icontains=retailer_fragment,
                        name=rcat_name,
                    ).first()

                # Find the master category
                master_cat = master_cat_objects.get(master_name)
                if not master_cat:
                    # Fallback: look up from DB (useful after a previous run)
                    try:
                        master_cat = Category.objects.get(name=master_name, parent=None)
                    except Category.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(
                                f"  X Master category not found: {master_name!r}"
                            )
                        )
                        continue

                if dry_run:
                    self.stdout.write(
                        f"  [DRY] Would map: {rcat.retailer.name} › {rcat_name!r}  →  {master_name}"
                    )
                    continue

                mapping, created = CategoryMapping.objects.get_or_create(
                    retailer_category=rcat,
                    defaults={"master_category": master_cat},
                )
                if created:
                    mappings_created += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  + Mapped: {rcat.retailer.name} › {rcat_name!r}  →  {master_name}"
                        )
                    )
                else:
                    mappings_skipped += 1
                    self.stdout.write(
                        f"  · Already mapped: {rcat.retailer.name} › {rcat_name!r}"
                    )

            if dry_run:
                raise transaction.TransactionManagementError("dry-run rollback")

        # ── Summary ──────────────────────────────────────────────────────────
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f"Done.\n"
                f"  Categories created : {cats_created}\n"
                f"  Mappings created   : {mappings_created}\n"
                f"  Mappings existing  : {mappings_skipped}"
            )
        )
