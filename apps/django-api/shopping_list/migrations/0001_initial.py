from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0016_deal_upsert'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ── ShoppingList ───────────────────────────────────────────────
        migrations.CreateModel(
            name='ShoppingList',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                (
                    'user',
                    models.ForeignKey(
                        to=settings.AUTH_USER_MODEL,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='shopping_lists',
                    ),
                ),
                ('name', models.CharField(max_length=200, default='My shopping list')),
                (
                    'mode',
                    models.CharField(
                        max_length=20,
                        default='split',
                        choices=[
                            ('single', 'Cheapest single store'),
                            ('split',  'Best price per item (split basket)'),
                            ('budget', 'Budget fit'),
                        ],
                    ),
                ),
                (
                    'budget',
                    models.DecimalField(
                        max_digits=10, decimal_places=2,
                        null=True, blank=True,
                    ),
                ),
                (
                    'status',
                    models.CharField(
                        max_length=20,
                        default='draft',
                        choices=[
                            ('draft',     'Draft'),
                            ('optimised', 'Optimised'),
                            ('completed', 'Completed'),
                        ],
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'shopping_list', 'ordering': ['-updated_at']},
        ),

        # ── ShoppingListItem ───────────────────────────────────────────
        migrations.CreateModel(
            name='ShoppingListItem',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                (
                    'list',
                    models.ForeignKey(
                        to='shopping_list.ShoppingList',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='items',
                    ),
                ),
                ('raw_query', models.CharField(max_length=500)),
                (
                    'product',
                    models.ForeignKey(
                        to='core.Product',
                        on_delete=django.db.models.deletion.SET_NULL,
                        null=True, blank=True,
                        related_name='shopping_list_items',
                    ),
                ),
                (
                    'deal',
                    models.ForeignKey(
                        to='core.Deal',
                        on_delete=django.db.models.deletion.SET_NULL,
                        null=True, blank=True,
                        related_name='shopping_list_items',
                    ),
                ),
                (
                    'branch',
                    models.ForeignKey(
                        to='core.RetailerBranch',
                        on_delete=django.db.models.deletion.SET_NULL,
                        null=True, blank=True,
                        related_name='shopping_list_items',
                    ),
                ),
                ('qty', models.PositiveIntegerField(default=1)),
                ('is_matched', models.BooleanField(default=False)),
                ('match_score', models.FloatField(null=True, blank=True)),
                ('position', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'shopping_list_item',
                'ordering': ['position', 'created_at'],
            },
        ),

        # ── UserBranchPreference ───────────────────────────────────────
        migrations.CreateModel(
            name='UserBranchPreference',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                (
                    'user',
                    models.ForeignKey(
                        to=settings.AUTH_USER_MODEL,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='branch_preferences',
                    ),
                ),
                (
                    'branch',
                    models.ForeignKey(
                        to='core.RetailerBranch',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='user_preferences',
                    ),
                ),
                ('priority', models.PositiveIntegerField(default=0)),
                (
                    'home_lat',
                    models.DecimalField(
                        max_digits=9, decimal_places=6,
                        null=True, blank=True,
                    ),
                ),
                (
                    'home_lng',
                    models.DecimalField(
                        max_digits=9, decimal_places=6,
                        null=True, blank=True,
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'shopping_user_branch_preference',
                'ordering': ['priority'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='userbranchpreference',
            unique_together={('user', 'branch')},
        ),

        # ── ListOptimisationResult ─────────────────────────────────────
        migrations.CreateModel(
            name='ListOptimisationResult',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                (
                    'list',
                    models.OneToOneField(
                        to='shopping_list.ShoppingList',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='optimisation_result',
                    ),
                ),
                ('mode', models.CharField(max_length=20)),
                (
                    'grand_total',
                    models.DecimalField(
                        max_digits=10, decimal_places=2,
                        null=True, blank=True,
                    ),
                ),
                (
                    'total_saving',
                    models.DecimalField(
                        max_digits=10, decimal_places=2,
                        null=True, blank=True,
                    ),
                ),
                ('branch_plan', models.JSONField(default=dict)),
                ('computed_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'shopping_list_optimisation_result'},
        ),
    ]
