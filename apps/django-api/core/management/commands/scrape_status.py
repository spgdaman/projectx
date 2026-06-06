"""
python manage.py scrape_status

Prints a dashboard of the last scraper run per retailer and the current
beat schedule state. Safe to run at any time — read-only.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Show scraper status dashboard.'

    def handle(self, *args, **options):
        from django.conf import settings
        from core.models import Retailer, ScraperRun, MappingReviewQueue

        beat = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})

        # Map task name → schedule string
        schedule_map: dict = {}
        for entry_name, cfg in beat.items():
            task = cfg.get('task', '')
            sched = cfg.get('schedule')
            schedule_map[task] = str(sched) if sched else 'unknown'

        retailer_task_map = {
            'Naivas':     'scrapers.tasks.scrape_naivas',
            'Chandarana': 'scrapers.tasks.scrape_chandarana',
            'Quickmart':  'scrapers.tasks.scrape_quickmart_all',
            'Carrefour':  'scrapers.tasks.scrape_carrefour',
        }

        now = timezone.now()
        rows = []

        retailers = Retailer.objects.all().order_by('name')
        for r in retailers:
            last = (
                ScraperRun.objects
                .filter(retailer=r)
                .order_by('-started_at')
                .first()
            )

            if last:
                delta = now - last.started_at
                hours = delta.total_seconds() / 3600
                if hours < 1:
                    ago = f'{int(delta.total_seconds() / 60)}m ago'
                elif hours < 24:
                    ago = f'{hours:.1f}h ago'
                else:
                    ago = f'{delta.days}d ago'
                status = last.status
                products = str(last.deals_found) if last.deals_found else '0'
            else:
                ago = 'never'
                status = '—'
                products = '—'

            task_name = retailer_task_map.get(r.name)
            if task_name and task_name in schedule_map:
                scheduled = schedule_map[task_name]
            else:
                scheduled = 'DISABLED'

            rows.append((r.name, ago, status, products, scheduled))

        # Table widths
        W = [14, 10, 9, 9, 22]
        sep = '+' + '+'.join('-' * (w + 2) for w in W) + '+'
        header = '|'.join(
            f' {h:<{w}} '
            for h, w in zip(['Retailer', 'Last run', 'Status', 'Products', 'Scheduled'], W)
        )

        self.stdout.write('')
        self.stdout.write(sep)
        self.stdout.write('|' + header + '|')
        self.stdout.write(sep)
        for name, ago, status, products, scheduled in rows:
            row = '|'.join(
                f' {v:<{w}} '
                for v, w in zip([name, ago, status, products, scheduled], W)
            )
            self.stdout.write('|' + row + '|')
        self.stdout.write(sep)

        # Review queue
        try:
            pending = MappingReviewQueue.objects.filter(resolved=False).count()
            if pending:
                self.stdout.write(
                    f'\n  Review queue: {pending} pending'
                    '  ->  python manage.py map_categories'
                )
        except Exception:
            pass

        self.stdout.write('')
