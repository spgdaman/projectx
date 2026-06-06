"""
python manage.py scrape_quickmart [--branch NAME] [--list-branches] [--force]

Manual Quickmart scraper. Scheduled scraping is DISABLED (see tasks.py).
Runs a single-branch scrape if --branch is given, otherwise scrapes all
active branches one at a time (no parallel fan-out).
"""
import sys
import time

from django.core.management.base import BaseCommand


_BANNER = """\
===================================================
  QUICKMART - MANUAL SCRAPE (scheduled disabled)
  Branch Playwright scraping is memory-heavy.
  Re-enable after confirming a working API endpoint.
==================================================="""


class Command(BaseCommand):
    help = 'Manually scrape Quickmart (scheduled scraping is disabled).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--branch',
            type=str,
            default=None,
            help='Scrape only this named branch (must match RetailerBranch.name exactly)',
        )
        parser.add_argument(
            '--list-branches',
            action='store_true',
            default=False,
            help='List all Quickmart branches in the DB and exit',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            default=False,
            help='Bypass the 2-hour recent-run guard',
        )
        parser.add_argument(
            '--no-categorise',
            action='store_true',
            default=False,
            help='Skip category mapping after scraping',
        )

    def handle(self, *args, **options):
        from core.models import Retailer, RetailerBranch

        self.stdout.write(_BANNER)
        self.stdout.write('')

        try:
            retailer = Retailer.objects.get(name='Quickmart')
        except Retailer.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                'Quickmart Retailer not found in DB. Create it in Django admin first.'
            ))
            sys.exit(1)

        if options['list_branches']:
            branches = RetailerBranch.objects.filter(retailer=retailer).order_by('name')
            self.stdout.write(f'Quickmart branches ({branches.count()}):')
            for b in branches:
                self.stdout.write(
                    f'  [{b.id}] {b.name}  active={b.is_active}  url={b.external_id or "—"}'
                )
            return

        branch_name = options['branch']
        force = options['force']
        no_categorise = options['no_categorise']

        if branch_name:
            try:
                branch_obj = RetailerBranch.objects.get(retailer=retailer, name=branch_name)
            except RetailerBranch.DoesNotExist:
                self.stderr.write(self.style.ERROR(
                    f'Branch "{branch_name}" not found. '
                    'Run --list-branches to see available names.'
                ))
                sys.exit(1)
            branches = [branch_obj]
        else:
            branches = list(
                RetailerBranch.objects.filter(
                    retailer=retailer,
                    is_active=True,
                    external_id__isnull=False,
                ).order_by('name')
            )
            if not branches:
                self.stdout.write(self.style.WARNING(
                    'No active Quickmart branches with URLs found. '
                    'Run: python manage.py shell -c '
                    '"from scrapers.tasks import discover_quickmart_branches; '
                    'discover_quickmart_branches()"'
                ))
                return

        from scrapers.quickmart import QuickmartBranchScraper

        total_found = total_changed = 0
        for branch in branches:
            self.stdout.write(f'[Quickmart/{branch.name}] Scraping...')
            try:
                scraper = QuickmartBranchScraper(
                    branch_name=branch.name,
                    branch_url=branch.external_id,
                )
                t0 = time.time()
                run = scraper.run(force=force)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(
                    f'[Quickmart/{branch.name}] Failed: {exc}'
                ))
                import traceback
                traceback.print_exc()
                continue

            if run is None:
                self.stdout.write(self.style.WARNING(
                    f'[Quickmart/{branch.name}] Skipped — recent run within 2h. Use --force.'
                ))
                continue

            elapsed = time.time() - t0
            self.stdout.write(
                f'  found={run.deals_found} changed={run.deals_changed} '
                f'status={run.status} duration={elapsed:.0f}s'
            )
            total_found += run.deals_found
            total_changed += run.deals_changed

        self.stdout.write('')
        self.stdout.write(f'Total: found={total_found} changed={total_changed}')

        if no_categorise:
            self.stdout.write('[Quickmart] Skipping category mapping (--no-categorise).')
            return

        self.stdout.write('')
        self.stdout.write('[Quickmart] Running category mapping...')
        try:
            from django.core.management import call_command
            call_command('map_categories', retailer='Quickmart', stdout=self.stdout)
        except Exception as exc:
            self.stderr.write(self.style.WARNING(f'[Quickmart] Category mapping failed: {exc}'))

        self.stdout.write(self.style.SUCCESS('[Quickmart] Done.'))
