from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_subscription_expires_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="image_url",
            field=models.URLField(blank=True, max_length=1000, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True),
        ),
    ]
