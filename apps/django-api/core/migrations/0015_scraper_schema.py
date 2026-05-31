from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_product_image_url_userprofile_dob"),
    ]

    operations = [

        # 1. StagingProduct: add source + scraped_at
        migrations.AddField(
            model_name="stagingproduct",
            name="source",
            field=models.CharField(
                max_length=20,
                default="csv",
                choices=[("csv", "CSV Import"), ("scraper", "Scraper")],
            ),
        ),
        migrations.AddField(
            model_name="stagingproduct",
            name="scraped_at",
            field=models.DateTimeField(null=True, blank=True),
        ),

        # 2. RetailerBranch: add is_active + external_id
        migrations.AddField(
            model_name="retailerbranch",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="retailerbranch",
            name="external_id",
            field=models.CharField(max_length=200, null=True, blank=True),
        ),

        # 3. Deal: add nullable branch FK
        migrations.AddField(
            model_name="deal",
            name="branch",
            field=models.ForeignKey(
                to="core.retailerbranch",
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True,
                related_name="deals",
            ),
        ),

        # 4. CREATE PriceHistory
        migrations.CreateModel(
            name="PriceHistory",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "product",
                    models.ForeignKey(
                        to="core.product",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="price_history",
                    ),
                ),
                (
                    "retailer",
                    models.ForeignKey(
                        to="core.retailer",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="price_history",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        to="core.retailerbranch",
                        on_delete=django.db.models.deletion.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="price_history",
                    ),
                ),
                ("price", models.DecimalField(max_digits=12, decimal_places=2)),
                (
                    "old_price",
                    models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True),
                ),
                (
                    "source",
                    models.CharField(
                        max_length=20,
                        default="scraper",
                        choices=[("csv", "CSV Import"), ("scraper", "Scraper")],
                    ),
                ),
                (
                    "recorded_at",
                    models.DateTimeField(default=django.utils.timezone.now, db_index=True),
                ),
            ],
            options={
                "db_table": "core_pricehistory",
                "ordering": ["-recorded_at"],
                "indexes": [
                    models.Index(
                        fields=["product", "retailer", "recorded_at"],
                        name="ph_product_retailer_idx",
                    ),
                    models.Index(
                        fields=["product", "branch", "recorded_at"],
                        name="ph_product_branch_idx",
                    ),
                ],
            },
        ),

        # 5. CREATE ScraperRun
        migrations.CreateModel(
            name="ScraperRun",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "retailer",
                    models.ForeignKey(
                        to="core.retailer",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scraper_runs",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        to="core.retailerbranch",
                        on_delete=django.db.models.deletion.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="scraper_runs",
                    ),
                ),
                (
                    "strategy",
                    models.CharField(
                        max_length=20,
                        default="api",
                        choices=[("api", "API"), ("scraper", "Web scraper (fallback)")],
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        default="running",
                        choices=[
                            ("running", "Running"),
                            ("success", "Success"),
                            ("failed", "Failed"),
                            ("partial", "Partial"),
                        ],
                    ),
                ),
                ("deals_found", models.IntegerField(default=0)),
                ("deals_changed", models.IntegerField(default=0)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(null=True, blank=True)),
                ("error", models.TextField(blank=True)),
            ],
            options={
                "db_table": "core_scraperrun",
                "ordering": ["-started_at"],
                "indexes": [
                    models.Index(
                        fields=["retailer", "started_at"],
                        name="sr_retailer_time_idx",
                    ),
                ],
            },
        ),
    ]
