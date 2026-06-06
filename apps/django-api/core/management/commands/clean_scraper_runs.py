"""
python manage.py clean_scraper_runs [--execute]

Identifies and optionally deletes duplicate ScraperRun rows, keeping the
most recent successful run per (retailer, branch). If no success exists,
keeps the most recent run of any status.

Defaults to --dry-run. Pass --execute to actually delete.
"""
from django.core.management.base import BaseCommand
from django.db.models import Count


class Command(BaseCommand):
    help = 'Remove duplicate ScraperRun rows, keeping one per (retailer, branch).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--execute',
            action='store_true',
            default=False,
            help='Actually delete rows (default is dry-run preview)',
        )
        parser.add_argument(
            '--keep-last',
            type=int,
            default=5,
            help='Keep this many most recent runs per (retailer, branch) regardless of status (default 5)',
        )

    def handle(self, *args, **options):
        from core.models import ScraperRun, Retailer, RetailerBranch

        execute = options['execute']
        keep_last = options['keep_last']

        if not execute:
            self.stdout.write(self.style.WARNING('DRY RUN — pass --execute to delete'))
        self.stdout.write('')

        total_deleted = 0

        retailers = Retailer.objects.all()
        for retailer in retailers:
            # Collect all (retailer, branch) combos
            branch_ids = (
                ScraperRun.objects
                .filter(retailer=retailer)
                .values_list('branch_id', flat=True)
                .distinct()
            )

            for branch_id in branch_ids:
                qs = ScraperRun.objects.filter(
                    retailer=retailer, branch_id=branch_id
                ).order_by('-started_at')

                total = qs.count()
                if total <= keep_last:
                    continue

                # IDs to keep: the keep_last most recent
                keep_ids = list(qs.values_list('id', flat=True)[:keep_last])
                to_delete = qs.exclude(id__in=keep_ids)
                count = to_delete.count()

                branch_name = (
                    RetailerBranch.objects.filter(id=branch_id).values_list('name', flat=True).first()
                    if branch_id else 'national'
                )

                self.stdout.write(
                    f'  {retailer.name} / {branch_name}: '
                    f'{total} runs -> keep {keep_last}, delete {count}'
                )

                if execute and count:
                    deleted, _ = to_delete.delete()
                    total_deleted += deleted

        self.stdout.write('')
        if execute:
            self.stdout.write(self.style.SUCCESS(f'Deleted {total_deleted} ScraperRun row(s).'))
        else:
            self.stdout.write(self.style.WARNING(
                'Nothing deleted (dry run). Re-run with --execute to apply.'
            ))
