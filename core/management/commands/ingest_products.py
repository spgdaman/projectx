# core/management/commands/ingest_products.py
import csv
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from core.models import StagingProduct
from django.db import connection

def parse_decimal(value):
    if value is None:
        return None
    # Remove commas and extra spaces
    value = value.replace(',', '').strip()
    if value == '':
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None

def clear_staging():
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM core_stagingproduct")

class Command(BaseCommand):
    help = "Ingest product CSV files from multiple sources"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')

    def handle(self, *args, **options):
        csv_file = options['csv_file']

        try:
            with open(csv_file, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0

                clear_staging()

                for row in reader:
                    # Detect CSV format
                    if 'category' in row:  # Sample1
                        staging = StagingProduct.objects.create(
                            retailer_name=row['retailer'],
                            branch_name=row.get('branch_name'),
                            category_name=row.get('category'),
                            sub_category_name=row.get('sub_category_1'),
                            sub_category_2_name=row.get('sub_category_2'),
                            product_name=row.get('product_name'),
                            product_url=row.get('product_url'),
                            image_url=row.get('image_url'),
                            price=parse_decimal(row.get('last_new_price_7')),
                            old_price=parse_decimal(row.get('last_old_price_7')),
                            is_manual=False
                        )
                    else:  # Sample2
                        staging = StagingProduct.objects.create(
                            retailer_name=row['retailer'],
                            branch_name=row.get('branch_name'),
                            category_name=row.get('category_name'),
                            sub_category_name=row.get('sub_category_name'),
                            product_name=row.get('product_name'),
                            product_url=row.get('product_link'),
                            image_url=row.get('image_url'),
                            price=parse_decimal(row.get('last_new_price_7')),
                            old_price=parse_decimal(row.get('last_old_price_7')),
                            is_manual=False
                        )

                    self.stdout.write(f"Staged: {staging.product_name} | Price: {staging.price}")
                    count += 1

                self.stdout.write(self.style.SUCCESS(f"Staging complete. {count} products ingested."))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found: {csv_file}"))
