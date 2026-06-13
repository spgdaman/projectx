from django.db import migrations


def seed(apps, schema_editor):
    Retailer = apps.get_model('core', 'Retailer')
    Retailer.objects.get_or_create(name='Oraimo')
    Retailer.objects.get_or_create(name='Hotpoint')


def unseed(apps, schema_editor):
    Retailer = apps.get_model('core', 'Retailer')
    Retailer.objects.filter(name__in=['Oraimo', 'Hotpoint']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_emailconfig_userprofile_digest'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
