"""
Map existing Product rows that have no master_category.

These products have no corresponding StagingProduct so the normal
map_categories command cannot reach them. This script uses the
CategoryMapper's internal tiers directly, skipping the review-queue
step (which requires a StagingProduct FK).

Usage:
    python map_products_direct.py
    python map_products_direct.py --dry-run
    python map_products_direct.py --retailer Chandarana
"""
import argparse
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalogue.settings')
django.setup()

from core.models import Product
from core.services.category_mapper import CategoryMapper, MappingResult


class ProductProxy:
    """Makes a Product look like a StagingProduct for CategoryMapper."""
    __slots__ = ('product_name', 'retailer_name',
                 'category_name', 'sub_category_name', 'sub_category_2_name')

    def __init__(self, product):
        self.product_name = product.name
        self.retailer_name = product.retailer.name
        self.category_name = (
            product.retailer_category.name
            if product.retailer_category else None
        )
        self.sub_category_name = None
        self.sub_category_2_name = None


def map_product(mapper, product) -> MappingResult:
    """Run tiers 1-4 without touching MappingReviewQueue."""
    proxy = ProductProxy(product)
    levels = mapper._get_levels(proxy)
    retailer = mapper._get_retailer(proxy)

    for tier_fn in (
        lambda: mapper._tier1_exact(levels, retailer),
        lambda: mapper._tier2_synonym(levels, retailer),
        lambda: mapper._tier3_keyword(proxy),
        lambda: mapper._tier4_fuzzy(levels),
    ):
        result = tier_fn()
        if result.matched:
            if result.tier == 4:
                mapper._record_fuzzy_synonym(
                    raw=result.matched_on,
                    level=result.level,
                    retailer=retailer,
                    category=result.category,
                    score=result.score,
                )
            return result
    return MappingResult()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--retailer', default=None)
    args = parser.parse_args()

    qs = Product.objects.filter(
        master_category__isnull=True
    ).select_related('retailer', 'retailer_category')

    if args.retailer:
        qs = qs.filter(retailer__name=args.retailer)

    total = qs.count()
    print(f'Unmapped products to process: {total}')

    mapper = CategoryMapper()
    mapper._load_master_categories()
    mapper._load_keyword_rules()

    counters = dict(t1=0, t2=0, t3=0, t4=0, miss=0)
    misses = []

    for product in qs.iterator(chunk_size=500):
        result = map_product(mapper, product)

        if result.matched:
            counters[f't{result.tier}'] += 1
            if not args.dry_run:
                product.master_category = result.category
                product.save(update_fields=['master_category'])
        else:
            counters['miss'] += 1
            misses.append(product)

    total_matched = total - counters['miss']
    pct = (total_matched / total * 100) if total else 0

    print()
    print(f'  Tier 1 (exact):   {counters["t1"]:>5}')
    print(f'  Tier 2 (synonym): {counters["t2"]:>5}')
    print(f'  Tier 3 (keyword): {counters["t3"]:>5}')
    print(f'  Tier 4 (fuzzy):   {counters["t4"]:>5}')
    print(f'  {"-"*27}')
    print(f'  Matched:          {total_matched:>5} / {total} ({pct:.1f}%)')
    print(f'  Unmatched:        {counters["miss"]:>5}')

    if args.dry_run:
        print('\n  (dry-run — no DB writes)')

    if misses:
        print(f'\nUnmatched products ({len(misses)}):')
        for p in misses[:60]:
            rc = p.retailer_category.name if p.retailer_category else '—'
            print(f'  [{p.retailer.name}] rc={rc!r:20s} | {p.name}')
        if len(misses) > 60:
            print(f'  … and {len(misses) - 60} more')


if __name__ == '__main__':
    main()
