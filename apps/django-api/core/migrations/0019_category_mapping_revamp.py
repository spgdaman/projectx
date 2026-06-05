from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_seed_chandarana_retailer'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategorySynonym',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('raw_name', models.CharField(
                    help_text='Exact string from the retailer (after normalisation — lowercased, stripped, no double spaces)',
                    max_length=255,
                )),
                ('level', models.IntegerField(
                    choices=[(0, 'L0 category'), (1, 'L1 sub-category'), (2, 'L2 sub-category 2')],
                    default=0,
                    help_text='Which StagingProduct field this raw_name came from',
                )),
                ('source', models.CharField(
                    choices=[
                        ('manual', 'Added manually'),
                        ('human', 'Confirmed by human review'),
                        ('fuzzy', 'Auto-confirmed by fuzzy match'),
                    ],
                    default='manual',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('master_category', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='synonyms',
                    to='core.category',
                )),
                ('retailer', models.ForeignKey(
                    blank=True,
                    help_text='Null means this alias applies to all retailers',
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    to='core.retailer',
                )),
            ],
            options={
                'verbose_name_plural': 'Category synonyms',
            },
        ),
        migrations.AlterUniqueTogether(
            name='categorysynonym',
            unique_together={('raw_name', 'retailer', 'level')},
        ),
        migrations.AddIndex(
            model_name='categorysynonym',
            index=models.Index(fields=['raw_name', 'level'], name='catsynonym_name_level_idx'),
        ),
        migrations.CreateModel(
            name='CategoryKeywordRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('keyword', models.CharField(
                    help_text='Case-insensitive. Matched as a whole word where possible.',
                    max_length=100,
                )),
                ('priority', models.IntegerField(
                    default=0,
                    help_text='Higher value = checked first. Use 100+ for specific brand rules, 10-99 for product type rules, 1-9 for generic category rules.',
                )),
                ('match_field', models.CharField(
                    choices=[
                        ('product_name', 'Product name only'),
                        ('any_category', 'Any category field'),
                        ('any', 'Product name + all category fields'),
                    ],
                    default='product_name',
                    max_length=20,
                )),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('master_category', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='keyword_rules',
                    to='core.category',
                )),
            ],
            options={
                'verbose_name_plural': 'Category keyword rules',
                'ordering': ['-priority'],
            },
        ),
        migrations.AddIndex(
            model_name='categorykeywordrule',
            index=models.Index(fields=['keyword', 'is_active'], name='catkeyword_kw_active_idx'),
        ),
        migrations.CreateModel(
            name='MappingReviewQueue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tier_reached', models.IntegerField(
                    default=4,
                    help_text='Last tier attempted before giving up',
                )),
                ('best_fuzzy_score', models.FloatField(
                    blank=True,
                    null=True,
                    help_text='rapidfuzz score 0-100 for the fuzzy suggestion',
                )),
                ('best_fuzzy_level', models.IntegerField(
                    blank=True,
                    null=True,
                    help_text='Which level (0/1/2) produced the best fuzzy score',
                )),
                ('resolved', models.BooleanField(default=False)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('best_fuzzy_suggestion', models.ForeignKey(
                    blank=True,
                    help_text='Highest-scoring fuzzy match, shown as a suggestion in admin',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='fuzzy_suggestions',
                    to='core.category',
                )),
                ('resolved_category', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='resolved_review_queue',
                    to='core.category',
                )),
                ('retailer', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='core.retailer',
                )),
                ('staging_product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='review_queue_entries',
                    to='core.stagingproduct',
                )),
            ],
            options={
                'verbose_name_plural': 'Mapping review queue',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='mappingreviewqueue',
            index=models.Index(fields=['resolved', 'created_at'], name='reviewqueue_resolved_idx'),
        ),
    ]
