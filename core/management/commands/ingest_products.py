import csv
from django.core.management.base import BaseCommand
from core.models import StagingProduct


class Command(BaseCommand):
    help = "Ingest product CSV files from multiple sources"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')

    def handle(self, *args, **options):
        csv_file = options['csv_file']

        self.stdout.write("Clearing staging table...")
        StagingProduct.objects.all().delete()

        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:

                # Detect format dynamically
                if 'category' in row:
                    staging = StagingProduct.objects.create(
                        retailer_name=row['retailer'],
                        category_name=row.get('category'),
                        sub_category_name=row.get('sub_category_1'),
                        sub_category_2_name=row.get('sub_category_2'),
                        product_name=row.get('product_name'),
                        product_url=row.get('product_url'),
                        image_url=row.get('image_url'),
                        price=row.get('last_new_price_7') or None,
                        old_price=row.get('last_old_price_7') or None,
                    )
                else:
                    staging = StagingProduct.objects.create(
                        retailer_name=row['retailer'],
                        branch_name=row.get('branch_name'),
                        category_name=row.get('category_name'),
                        sub_category_name=row.get('sub_category_name'),
                        product_name=row.get('product_name'),
                        product_url=row.get('product_link'),
                        price=row.get('last_new_price_7') or None,
                        old_price=row.get('last_old_price_7') or None,
                    )

                self.stdout.write(f"Staged: {staging.product_name}")

        self.stdout.write(self.style.SUCCESS("Staging complete."))
