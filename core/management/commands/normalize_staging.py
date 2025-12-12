# core/management/commands/normalize_staging.py

from django.core.management.base import BaseCommand
from core.models import (
    StagingProduct, Retailer, RetailerCategory, RetailerBranch,
    Product, CategoryMapping, Deal
)
from decimal import Decimal

class Command(BaseCommand):
    help = "Normalize staged products into proper models (skipping products without prices)"

    def handle(self, *args, **options):
        staged_products = StagingProduct.objects.all()
        self.stdout.write(f"Found {staged_products.count()} staged products")

        for sp in staged_products:

            # Skip products with no price
            if not sp.price:
                self.stdout.write(f"Skipping {sp.product_name}: no price available")
                continue

            # 1️⃣ Retailer
            retailer, _ = Retailer.objects.get_or_create(name=sp.retailer_name)

            # 2️⃣ Branch (variable name untouched)
            branch_obj = None
            if sp.branch_name:
                branch_obj, _ = RetailerBranch.objects.get_or_create(
                    retailer=retailer,
                    name=sp.branch_name
                )

            # 3️⃣ Retailer Category Hierarchy
            parent_cat = None
            if sp.category_name:
                parent_cat, _ = RetailerCategory.objects.get_or_create(
                    retailer=retailer,
                    name=sp.category_name
                )

            sub_cat = parent_cat
            if sp.sub_category_name:
                sub_cat, _ = RetailerCategory.objects.get_or_create(
                    retailer=retailer,
                    name=sp.sub_category_name
                )

            sub_cat_2 = sub_cat
            if sp.sub_category_2_name:
                sub_cat_2, _ = RetailerCategory.objects.get_or_create(
                    retailer=retailer,
                    name=sp.sub_category_2_name
                )

            final_retailer_cat = sub_cat_2 or sub_cat or parent_cat

            # 4️⃣ Master Category Mapping
            master_category = None
            if final_retailer_cat:
                try:
                    mapping = CategoryMapping.objects.get(
                        retailer_category=final_retailer_cat
                    )
                    master_category = mapping.master_category
                except CategoryMapping.DoesNotExist:
                    pass

            # 5️⃣ Product Create/Update
            price_decimal = Decimal(sp.price)

            product, created = Product.objects.get_or_create(
                retailer=retailer,
                retailer_category=final_retailer_cat,
                name=sp.product_name,
                defaults={
                    "price": price_decimal,
                    "master_category": master_category
                }
            )

            if not created:
                product.price = price_decimal
                if master_category:
                    product.master_category = master_category
                product.save()

            # 6️⃣ Deal (NOW WITH BRANCH SUPPORT)
            Deal.objects.create(
                product=product,
                retailer=retailer,
                branch=branch_obj,  # ← Correct FK usage
                current_price=price_decimal,
                old_price=Decimal(sp.old_price) if sp.old_price else None,
                link=sp.product_url
            )

            self.stdout.write(f"Processed: {product.name}")

        self.stdout.write(self.style.SUCCESS("Normalization complete!"))
