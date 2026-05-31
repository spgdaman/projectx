"""
Migration: deal_upsert
-----------------------
1. Deduplicate Deal rows — keep the most-recent row per (product, retailer),
   delete the rest. Necessary before adding the unique constraint.
2. Change Deal.scraped_at from auto_now_add=True to default=timezone.now
   so the normalization pipeline can write the scraper's actual timestamp.
3. Add unique_together = (('product', 'retailer'),) — one live deal per product.
4. Add ordering = ['-scraped_at'] so the default queryset is most-recent-first.
"""

from django.db import migrations, models
import django.utils.timezone


def deduplicate_deals(apps, schema_editor):
    """Keep the highest-pk Deal per (product_id, retailer_id), delete the rest."""
    Deal = apps.get_model('core', 'Deal')
    db = schema_editor.connection.alias

    # Find the canonical (latest) pk per group
    from django.db.models import Max
    keep_ids = (
        Deal.objects.using(db)
        .values('product_id', 'retailer_id')
        .annotate(keep=Max('id'))
        .values_list('keep', flat=True)
    )
    deleted, _ = Deal.objects.using(db).exclude(pk__in=list(keep_ids)).delete()
    print(f'\n  Deduplication: deleted {deleted} duplicate Deal rows')


class Migration(migrations.Migration):
    # atomic=False lets each operation commit separately so PostgreSQL's
    # pending trigger events from the RunPython delete don't block ALTER TABLE.
    atomic = False

    dependencies = [
        ('core', '0015_scraper_schema'),
    ]

    operations = [
        # 1. Remove duplicates before the unique constraint is applied
        migrations.RunPython(deduplicate_deals, migrations.RunPython.noop),

        # 2. Make scraped_at writable (drop auto_now_add)
        migrations.AlterField(
            model_name='deal',
            name='scraped_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),

        # 3. One live Deal per product+retailer
        migrations.AlterUniqueTogether(
            name='deal',
            unique_together={('product', 'retailer')},
        ),

        # 4. Default ordering: most-recent-first
        migrations.AlterModelOptions(
            name='deal',
            options={'ordering': ['-scraped_at']},
        ),
    ]
