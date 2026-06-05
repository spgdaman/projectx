from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Run the four-tier category mapping pipeline against unresolved StagingProduct rows.'

    def add_arguments(self, parser):
        parser.add_argument('--retailer', type=str, default=None, help='Only process this retailer (by name)')
        parser.add_argument('--limit', type=int, default=None, help='Process at most N products (default: all)')
        parser.add_argument('--dry-run', action='store_true', help='Print results without writing to DB')
        parser.add_argument('--rematch', action='store_true', help='Re-run even on already-matched products')
        parser.add_argument('--verbose', action='store_true', help='Print each product result')

    def handle(self, *args, **options):
        from core.models import (
            CategoryMapping, MappingReviewQueue, RetailerCategory, StagingProduct,
        )
        from core.services.category_mapper import CategoryMapper

        dry_run = options['dry_run']
        verbose = options['verbose']
        retailer_filter = options['retailer']
        limit = options['limit']

        # ── Build queryset ──────────────────────────────────────────────── #
        if options['rematch']:
            qs = StagingProduct.objects.all()
        else:
            # Rows whose linked product has no master_category OR are in the
            # review queue as unresolved.
            from django.db.models import Q
            from core.models import Product
            unmapped_product_names = set(
                Product.objects.filter(master_category__isnull=True)
                .values_list('name', flat=True)
            )
            queued_ids = set(
                MappingReviewQueue.objects.filter(resolved=False)
                .values_list('staging_product_id', flat=True)
            )
            qs = StagingProduct.objects.filter(
                Q(id__in=queued_ids) | Q(product_name__in=unmapped_product_names)
            )

        if retailer_filter:
            qs = qs.filter(retailer_name=retailer_filter)

        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f'Processing {total} staging products…')

        mapper = CategoryMapper()
        counters = dict(
            matched_t1=0, matched_t2=0, matched_t3=0, matched_t4=0,
            unmatched=0, already_mapped=0, errors=0,
        )

        for sp in qs.iterator():
            try:
                result = mapper.map(sp)

                if verbose:
                    cats = ' > '.join(filter(None, [sp.category_name, sp.sub_category_name, sp.sub_category_2_name]))
                    if result.matched:
                        self.stdout.write(
                            f'  [T{result.tier}/L{result.level}] {sp.product_name} '
                            f'({cats}) → {result.category}'
                        )
                    else:
                        self.stdout.write(f'  [MISS] {sp.product_name} ({cats})')

                if not result.matched:
                    counters['unmatched'] += 1
                    continue

                tier_key = f'matched_t{result.tier}'
                counters[tier_key] = counters.get(tier_key, 0) + 1

                if dry_run:
                    continue

                # ── Persist the mapping ─────────────────────────────────── #
                # 1. Ensure RetailerCategory exists for the matched level
                from core.models import Retailer
                try:
                    retailer_obj = Retailer.objects.get(name=sp.retailer_name)
                except Retailer.DoesNotExist:
                    continue

                # Use the deepest populated category field for the RetailerCategory
                level_field_map = {
                    2: sp.sub_category_2_name,
                    1: sp.sub_category_name,
                    0: sp.category_name,
                }
                cat_name_for_level = level_field_map.get(result.level) or sp.category_name
                if cat_name_for_level:
                    rc, _ = RetailerCategory.objects.get_or_create(
                        retailer=retailer_obj,
                        name=cat_name_for_level,
                    )
                    CategoryMapping.objects.get_or_create(
                        retailer_category=rc,
                        defaults={'master_category': result.category},
                    )

                # 2. Update linked Product.master_category
                from core.models import Product
                products_to_update = Product.objects.filter(
                    retailer__name=sp.retailer_name,
                    name=sp.product_name,
                    master_category__isnull=True,
                )
                updated = products_to_update.update(master_category=result.category)

                # 3. Mark review queue entry as resolved
                MappingReviewQueue.objects.filter(
                    staging_product=sp,
                    resolved=False,
                ).update(
                    resolved=True,
                    resolved_category=result.category,
                    resolved_at=timezone.now(),
                )

            except Exception as exc:
                self.stderr.write(f'ERROR processing {sp.id} ({sp.product_name}): {exc}')
                counters['errors'] += 1
                continue

        # ── Summary ──────────────────────────────────────────────────────── #
        total_matched = sum(counters[k] for k in ('matched_t1', 'matched_t2', 'matched_t3', 'matched_t4'))
        self.stdout.write('')
        self.stdout.write('  Tier 1 (exact):    {:>6} products'.format(counters['matched_t1']))
        self.stdout.write('  Tier 2 (synonym):  {:>6} products'.format(counters['matched_t2']))
        self.stdout.write('  Tier 3 (keyword):  {:>6} products'.format(counters['matched_t3']))
        self.stdout.write('  Tier 4 (fuzzy):    {:>6} products'.format(counters['matched_t4']))
        self.stdout.write('  ' + '─' * 30)
        self.stdout.write('  Total matched:     {:>6} / {}'.format(total_matched, total))
        self.stdout.write('  Unmatched (queue): {:>6}'.format(counters['unmatched']))
        self.stdout.write('  Errors:            {:>6}'.format(counters['errors']))
        if dry_run:
            self.stdout.write('\n  (dry-run — no DB writes)')
