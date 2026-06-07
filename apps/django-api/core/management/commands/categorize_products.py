"""
Categorize existing Product rows directly using keyword rules (Tier 3).

Use this when products exist in the DB but have no corresponding StagingProduct
rows, so map_categories cannot process them.
"""

import re
from django.core.management.base import BaseCommand


class _ProductProxy:
    """Minimal duck-type of StagingProduct for CategoryMapper._tier3_keyword."""
    def __init__(self, name):
        self.product_name = name
        self.category_name = ''
        self.sub_category_name = ''
        self.sub_category_2_name = ''


class Command(BaseCommand):
    help = 'Categorize uncategorized Products using keyword rules on product name.'

    def add_arguments(self, parser):
        parser.add_argument('--retailer', type=str, default=None)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--rematch', action='store_true', help='Re-run on already-categorized products')

    def handle(self, *args, **options):
        from core.models import Product
        from core.services.category_mapper import CategoryMapper

        qs = Product.objects.select_related('retailer')
        if not options['rematch']:
            qs = qs.filter(master_category__isnull=True)
        if options['retailer']:
            qs = qs.filter(retailer__name=options['retailer'])

        total = qs.count()
        self.stdout.write(f'Processing {total} products...')

        mapper = CategoryMapper()
        matched = 0
        skipped = 0

        for product in qs.iterator(chunk_size=500):
            proxy = _ProductProxy(product.name)
            result = mapper._tier3_keyword(proxy)
            if not result.matched:
                skipped += 1
                continue
            matched += 1
            if not options['dry_run']:
                Product.objects.filter(pk=product.pk).update(master_category=result.category)

        self.stdout.write('')
        self.stdout.write(f'  Matched:   {matched:>6} / {total}')
        self.stdout.write(f'  Unmatched: {skipped:>6}')
        if options['dry_run']:
            self.stdout.write('\n  (dry-run - no DB writes)')
