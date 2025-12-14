from django.core.management.base import BaseCommand
from core.models import StagingProduct, Retailer, RetailerCategory, RetailerBranch, Product, CategoryMapping, Deal
from decimal import Decimal


class Command(BaseCommand):
    help = "Normalize staged products into proper models"

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

            # 3 Retailer category mapping chain
            # parent_cat = None
            # if sp.category_name:
            #     parent_cat, _ = RetailerCategory.objects.get_or_create(
            #         retailer=retailer,
            #         name=sp.category_name
            #     )

            # 3️⃣ Retailer category (MAIN CATEGORY ONLY)
            final_retailer_cat = None
            if sp.category_name and sp.category_name.strip():
                final_retailer_cat, _ = RetailerCategory.objects.get_or_create(
                    retailer=retailer,
                    name=sp.category_name.strip()
                )

                
            # sub_cat = parent_cat
            # if sp.sub_category_name:
            #     sub_cat, _ = RetailerCategory.objects.get_or_create(
            #         retailer=retailer,
            #         name=sp.sub_category_name
            #     )

            # sub_cat_2 = sub_cat
            # if sp.sub_category_2_name:
            #     sub_cat_2, _ = RetailerCategory.objects.get_or_create(
            #         retailer=retailer,
            #         name=sp.sub_category_2_name
            #     )

            # final_retailer_cat = sub_cat_2 or sub_cat or parent_cat
            # final_retailer_cat = parent_cat

            # 3️⃣ Mapping → master category
            master_category = None
            if final_retailer_cat:
                try:
                    mapping = CategoryMapping.objects.get(retailer_category__id=final_retailer_cat.id)
                    master_category = mapping.master_category
                except CategoryMapping.DoesNotExist:
                    pass

            # 4️⃣ Product upsert
            product, created = Product.objects.get_or_create(
                retailer=retailer,
                retailer_category=final_retailer_cat,
                name=sp.product_name,
                defaults={
                    'price': Decimal(sp.price) if sp.price not in [None, '', ' '] else Decimal("0.00"),
                    'master_category': master_category
                }
            )

            if not created:
                if sp.price not in [None, '', ' ']:
                    product.price = Decimal(sp.price)
                if master_category:
                    product.master_category = master_category
                product.save()

            # 5️⃣ Price history (Deal)
            if sp.price or sp.old_price:
                from core.services.alerts import process_deal_alerts

                deal = Deal.objects.create(
                    product=product,
                    retailer=retailer,
                    link=sp.product_url,
                    current_price=Decimal(sp.price),
                    old_price=Decimal(sp.old_price) if sp.old_price else None
                )

                process_deal_alerts(deal)

            self.stdout.write(f"Processed: {product.name}")

        self.stdout.write(self.style.SUCCESS("Normalization complete!"))
