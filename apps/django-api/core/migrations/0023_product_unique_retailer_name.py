"""
Migration 0023: Enforce unique (retailer, name) on Product.

Step 1 (RunPython): remove duplicate Product rows before adding the constraint.
  - For each (retailer_id, name) group with > 1 row, keep the lowest-ID row
    and delete the rest plus their associated Deals.
  - "Lowest ID" = the first-created copy; deals from later duplicates are lost,
    which is acceptable since they carry identical prices.

Step 2 (AlterUniqueTogether): add the DB-level unique constraint so that future
  normalize_staging races can use ignore_conflicts=True safely.
"""
from django.db import migrations


def _remove_duplicate_products(apps, schema_editor):
    Product = apps.get_model('core', 'Product')
    Deal    = apps.get_model('core', 'Deal')

    from django.db.models import Count, Min

    # Find every (retailer_id, name) pair that has more than one Product row.
    dupes = (
        Product.objects
        .values('retailer_id', 'name')
        .annotate(cnt=Count('id'), keep_id=Min('id'))
        .filter(cnt__gt=1)
    )

    for group in dupes:
        to_delete_qs = Product.objects.filter(
            retailer_id=group['retailer_id'],
            name=group['name'],
        ).exclude(id=group['keep_id'])

        # Cascade-delete associated deals before removing the products.
        Deal.objects.filter(product__in=to_delete_qs).delete()
        to_delete_qs.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_seed_oraimo_hotpoint'),
    ]

    operations = [
        migrations.RunPython(
            _remove_duplicate_products,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterUniqueTogether(
            name='product',
            unique_together={('retailer', 'name')},
        ),
    ]
