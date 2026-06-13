"""
python manage.py scrape_hotpoint [--force] [--limit N] [--no-categorise]

Scrape Hotpoint Kenya (Playwright) and optionally run category mapping.
Prints real-time progress. Exits with code 1 on failure.
"""
import sys
import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Scrape Hotpoint Kenya deals and write to staging -> products/deals.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            default=False,
            help='Bypass the 2-hour recent-run guard and scrape unconditionally',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Stop after writing N products (useful for testing)',
        )
        parser.add_argument(
            '--no-categorise',
            action='store_true',
            default=False,
            help='Skip category mapping after scraping',
        )

    def handle(self, *args, **options):
        force = options['force']
        limit = options['limit']
        no_categorise = options['no_categorise']

        self.stdout.write('[Hotpoint] Starting scrape — strategy: Playwright (API returns 500)')

        from scrapers.hotpoint import HotpointScraper

        try:
            scraper = HotpointScraper()
            if limit:
                original_write = scraper.write_to_staging
                written_total = [0]

                def limited_write(items, run):
                    remaining = limit - written_total[0]
                    if remaining <= 0:
                        return 0
                    count = original_write(items[:remaining], run)
                    written_total[0] += count
                    return count

                scraper.write_to_staging = limited_write

            t0 = time.time()
            run = scraper.run(force=force)
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'[Hotpoint] Scrape failed: {exc}'))
            import traceback
            traceback.print_exc()
            sys.exit(1)

        if run is None:
            self.stdout.write(self.style.WARNING(
                '[Hotpoint] Skipped — successful run already completed within last 2h. '
                'Use --force to override.'
            ))
            return

        elapsed = time.time() - t0
        self.stdout.write('')
        self.stdout.write('[Hotpoint] Scrape complete:')
        self.stdout.write(f'  Strategy:         {run.strategy}')
        self.stdout.write(f'  Products found:   {run.deals_found}')
        self.stdout.write(f'  Products changed: {run.deals_changed}')
        self.stdout.write(f'  Products new:     {run.products_new}')
        self.stdout.write(f'  Products skipped: {run.products_skipped}')
        self.stdout.write(f'  Pages scraped:    {run.pages_scraped}')
        self.stdout.write(f'  HTTP errors:      {run.http_errors}')
        self.stdout.write(f'  Duration:         {elapsed:.0f}s')
        self.stdout.write(f'  ScraperRun ID:    {run.pk}')
        self.stdout.write(f'  Status:           {run.status}')

        if run.status == 'failed':
            self.stderr.write(self.style.ERROR('[Hotpoint] Run finished with status=failed'))
            sys.exit(1)

        if no_categorise:
            self.stdout.write('[Hotpoint] Skipping category mapping (--no-categorise).')
            return

        self.stdout.write('')
        self.stdout.write('[Hotpoint] Running category mapping...')
        try:
            from django.core.management import call_command
            call_command('map_categories', retailer='Hotpoint', stdout=self.stdout)
        except Exception as exc:
            self.stderr.write(self.style.WARNING(f'[Hotpoint] Category mapping failed: {exc}'))

        self.stdout.write(self.style.SUCCESS('[Hotpoint] Done.'))
