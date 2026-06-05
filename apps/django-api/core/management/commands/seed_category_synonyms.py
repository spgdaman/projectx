from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Seed CategorySynonym and CategoryKeywordRule tables with a starter set '
        'covering Naivas, Quickmart, Carrefour, and Chandarana. IDEMPOTENT — safe '
        'to run multiple times.'
    )

    def handle(self, *args, **options):
        from core.models import (
            Category, CategoryKeywordRule, CategorySynonym, Retailer,
        )
        from core.services.category_mapper import CategoryMapper

        # ── Load master categories ──────────────────────────────────────── #
        categories = {c.name.lower(): c for c in Category.objects.all()}

        def cat(name):
            c = categories.get(name.lower())
            if not c:
                self.stderr.write(f'WARNING: master category "{name}" not found in DB — skipping')
            return c

        # ── Load retailers ──────────────────────────────────────────────── #
        retailers = {r.name: r for r in Retailer.objects.all()}

        # ── Check for staging data ──────────────────────────────────────── #
        from core.models import StagingProduct
        if StagingProduct.objects.count() == 0:
            self.stdout.write(
                'NOTE: StagingProduct table is empty. SYNONYMS list is empty because '
                'seed data is derived from actual retailer category strings in the DB. '
                'Import product data first, then re-run this command to populate synonyms.\n'
                'Keyword rules will still be seeded.'
            )

        # ── Synonym seed data ───────────────────────────────────────────── #
        # Format: (raw_string, level, retailer_name_or_None, master_category_name)
        # Populated from actual DB query output of StagingProduct category strings.
        # StagingProduct table is currently empty — add rows here once data is imported.
        SYNONYMS = [
            # (raw, level, retailer_or_None, master_cat_name)
            # Level 0 (category_name) mappings — add from actual DB query output
            # Level 1 (sub_category_name) mappings — add from actual DB query output
            # Level 2 (sub_category_2_name) mappings — add from actual DB query output
        ]

        # ── Keyword rule seed data ──────────────────────────────────────── #
        # Format: (keyword, master_cat_name, priority, match_field)
        # Uses actual master category names from the Category table.
        KEYWORD_RULES = [
            # ── High priority (100+): specific brand/product names ──────── #
            ('pampers',       'Personal Care > Baby Care & Diapers', 110, 'product_name'),
            ('huggies',       'Personal Care > Baby Care & Diapers', 110, 'product_name'),
            ('aptamil',       'Personal Care > Baby Care & Diapers', 110, 'product_name'),
            ('nan ',          'Personal Care > Baby Care & Diapers', 110, 'product_name'),
            ('similac',       'Personal Care > Baby Care & Diapers', 110, 'product_name'),
            ('weetabix',      'Food & Beverages > Breakfast & Cereals', 105, 'product_name'),
            ('quaker',        'Food & Beverages > Breakfast & Cereals', 105, 'product_name'),
            ('colgate',       'Personal Care > Oral Care',             105, 'product_name'),
            ('oral-b',        'Personal Care > Oral Care',             105, 'product_name'),
            ('safaricom',     'Electronics & Appliances > Phones & Tablets', 105, 'product_name'),
            ('samsung',       'Electronics & Appliances',              100, 'product_name'),
            ('infinix',       'Electronics & Appliances > Phones & Tablets', 100, 'product_name'),
            ('tecno',         'Electronics & Appliances > Phones & Tablets', 100, 'product_name'),
            ('ariel',         'Home Care > Laundry & Detergents',      100, 'product_name'),
            ('omo',           'Home Care > Laundry & Detergents',      100, 'product_name'),
            ('dettol',        'Personal Care > Body & Skin Care',       100, 'product_name'),
            ('nivea',         'Personal Care > Body & Skin Care',       100, 'product_name'),
            ('head & shoulders', 'Personal Care > Hair Care',          100, 'product_name'),
            ('dove',          'Personal Care > Body & Skin Care',       100, 'product_name'),

            # ── Medium priority (10–99): product type keywords ───────────── #
            ('diaper',        'Personal Care > Baby Care & Diapers',    90, 'any'),
            ('nappy',         'Personal Care > Baby Care & Diapers',    90, 'any'),
            ('nappies',       'Personal Care > Baby Care & Diapers',    90, 'any'),
            ('baby wipe',     'Personal Care > Baby Care & Diapers',    85, 'any'),
            ('baby food',     'Personal Care > Baby Care & Diapers',    85, 'any'),
            ('toothpaste',    'Personal Care > Oral Care',              80, 'product_name'),
            ('toothbrush',    'Personal Care > Oral Care',              80, 'product_name'),
            ('mouthwash',     'Personal Care > Oral Care',              80, 'product_name'),
            ('shampoo',       'Personal Care > Hair Care',              80, 'product_name'),
            ('conditioner',   'Personal Care > Hair Care',              75, 'product_name'),
            ('lotion',        'Personal Care > Body & Skin Care',       75, 'product_name'),
            ('sunscreen',     'Personal Care > Body & Skin Care',       75, 'product_name'),
            ('deodorant',     'Personal Care > Body & Skin Care',       75, 'product_name'),
            ('perfume',       'Personal Care > Beauty & Cosmetics',     75, 'product_name'),
            ('lipstick',      'Personal Care > Beauty & Cosmetics',     75, 'product_name'),
            ('mascara',       'Personal Care > Beauty & Cosmetics',     75, 'product_name'),
            ('pad',           'Personal Care > Sanitary Products',      70, 'product_name'),
            ('tampon',        'Personal Care > Sanitary Products',      70, 'product_name'),
            ('sanitary',      'Personal Care > Sanitary Products',      70, 'any'),
            ('milk',          'Food & Beverages > Dairy Products',      70, 'product_name'),
            ('yoghurt',       'Food & Beverages > Dairy Products',      70, 'product_name'),
            ('yogurt',        'Food & Beverages > Dairy Products',      70, 'product_name'),
            ('cheese',        'Food & Beverages > Dairy Products',      70, 'product_name'),
            ('butter',        'Food & Beverages > Dairy Products',      65, 'product_name'),
            ('bread',         'Food & Beverages > Bakery & Deli',       70, 'product_name'),
            ('cake',          'Food & Beverages > Bakery & Deli',       65, 'product_name'),
            ('biscuit',       'Food & Beverages > Snacks & Confectionery', 70, 'product_name'),
            ('chocolate',     'Food & Beverages > Snacks & Confectionery', 70, 'product_name'),
            ('crisps',        'Food & Beverages > Snacks & Confectionery', 70, 'product_name'),
            ('chips',         'Food & Beverages > Snacks & Confectionery', 65, 'product_name'),
            ('sweets',        'Food & Beverages > Snacks & Confectionery', 65, 'product_name'),
            ('juice',         'Food & Beverages > Beverages',           70, 'product_name'),
            ('water',         'Food & Beverages > Beverages',           60, 'product_name'),
            ('soda',          'Food & Beverages > Beverages',           65, 'product_name'),
            ('tea',           'Food & Beverages > Beverages',           65, 'product_name'),
            ('coffee',        'Food & Beverages > Beverages',           65, 'product_name'),
            ('cereal',        'Food & Beverages > Breakfast & Cereals', 70, 'product_name'),
            ('porridge',      'Food & Beverages > Breakfast & Cereals', 70, 'product_name'),
            ('oats',          'Food & Beverages > Breakfast & Cereals', 70, 'product_name'),
            ('rice',          'Food & Beverages > Pasta, Rice & Grains', 70, 'product_name'),
            ('pasta',         'Food & Beverages > Pasta, Rice & Grains', 70, 'product_name'),
            ('flour',         'Food & Beverages > Pasta, Rice & Grains', 65, 'product_name'),
            ('oil',           'Food & Beverages > Cooking Oils & Fats', 60, 'product_name'),
            ('fat',           'Food & Beverages > Cooking Oils & Fats', 55, 'product_name'),
            ('margarine',     'Food & Beverages > Cooking Oils & Fats', 65, 'product_name'),
            ('sauce',         'Food & Beverages > Condiments & Seasoning', 65, 'product_name'),
            ('ketchup',       'Food & Beverages > Condiments & Seasoning', 70, 'product_name'),
            ('spice',         'Food & Beverages > Condiments & Seasoning', 65, 'product_name'),
            ('salt',          'Food & Beverages > Condiments & Seasoning', 55, 'product_name'),
            ('sugar',         'Food & Beverages > Condiments & Seasoning', 55, 'product_name'),
            ('chicken',       'Food & Beverages > Meat, Fish & Eggs',   75, 'product_name'),
            ('beef',          'Food & Beverages > Meat, Fish & Eggs',   75, 'product_name'),
            ('fish',          'Food & Beverages > Meat, Fish & Eggs',   70, 'product_name'),
            ('egg',           'Food & Beverages > Meat, Fish & Eggs',   65, 'product_name'),
            ('vegetable',     'Food & Beverages > Fresh Produce',       65, 'product_name'),
            ('fruit',         'Food & Beverages > Fresh Produce',       65, 'product_name'),
            ('frozen',        'Food & Beverages > Frozen Foods',        60, 'product_name'),
            ('beer',          'Liquor > Beer & Cider',                  80, 'product_name'),
            ('wine',          'Liquor > Wines',                         80, 'product_name'),
            ('whisky',        'Liquor > Spirits & Liqueurs',            80, 'product_name'),
            ('vodka',         'Liquor > Spirits & Liqueurs',            80, 'product_name'),
            ('gin',           'Liquor > Spirits & Liqueurs',            75, 'product_name'),
            ('detergent',     'Home Care > Laundry & Detergents',       75, 'product_name'),
            ('fabric softener', 'Home Care > Laundry & Detergents',     75, 'product_name'),
            ('bleach',        'Home Care > Surface Cleaners',           70, 'product_name'),
            ('disinfectant',  'Home Care > Surface Cleaners',           70, 'product_name'),
            ('toilet paper',  'Home Care > Tissue & Paper Products',    75, 'product_name'),
            ('tissue',        'Home Care > Tissue & Paper Products',    65, 'product_name'),
            ('air freshener', 'Home Care > Air Fresheners & Candles',   75, 'product_name'),
            ('candle',        'Home Care > Air Fresheners & Candles',   70, 'product_name'),
            ('insecticide',   'Home Care > Pest Control',               75, 'product_name'),
            ('mosquito',      'Home Care > Pest Control',               70, 'product_name'),
            ('phone',         'Electronics & Appliances > Phones & Tablets', 70, 'product_name'),
            ('tablet',        'Electronics & Appliances > Phones & Tablets', 70, 'product_name'),
            ('laptop',        'Electronics & Appliances',               70, 'product_name'),
            ('television',    'Electronics & Appliances > TV & Audio',  75, 'product_name'),
            ('tv',            'Electronics & Appliances > TV & Audio',  65, 'product_name'),
            ('blender',       'Electronics & Appliances > Small Kitchen Appliances', 75, 'product_name'),
            ('kettle',        'Electronics & Appliances > Small Kitchen Appliances', 75, 'product_name'),
            ('fridge',        'Electronics & Appliances > Large Appliances', 75, 'product_name'),
            ('washing machine', 'Electronics & Appliances > Large Appliances', 75, 'product_name'),
            ('pot',           'Household & Kitchen > Kitchen & Dining',  65, 'product_name'),
            ('pan',           'Household & Kitchen > Kitchen & Dining',  60, 'product_name'),
            ('plate',         'Household & Kitchen > Kitchen & Dining',  60, 'product_name'),
            ('cup',           'Household & Kitchen > Kitchen & Dining',  55, 'product_name'),
            ('dog food',      'Pet & Animal Care',                       80, 'product_name'),
            ('cat food',      'Pet & Animal Care',                       80, 'product_name'),
            ('pet',           'Pet & Animal Care',                       60, 'any_category'),

            # ── Low priority (1–9): generic category-level fallbacks ──────── #
            ('food',          'Food & Beverages',                        5, 'any_category'),
            ('drink',         'Food & Beverages > Beverages',            5, 'any_category'),
            ('electronic',    'Electronics & Appliances',                5, 'any_category'),
            ('appliance',     'Electronics & Appliances',                5, 'any_category'),
            ('home',          'Home Care',                               3, 'any_category'),
            ('personal',      'Personal Care',                           3, 'any_category'),
            ('kitchen',       'Household & Kitchen > Kitchen & Dining',  3, 'any_category'),
        ]

        # ── Create synonyms ─────────────────────────────────────────────── #
        created_s = skipped_s = 0
        for raw, level, retailer_name, cat_name in SYNONYMS:
            master = cat(cat_name)
            if not master:
                continue
            retailer = retailers.get(retailer_name) if retailer_name else None
            norm = CategoryMapper.normalise(raw)
            _, created = CategorySynonym.objects.get_or_create(
                raw_name=norm,
                level=level,
                retailer=retailer,
                defaults={'master_category': master, 'source': 'manual'},
            )
            if created:
                created_s += 1
            else:
                skipped_s += 1

        # ── Create keyword rules ────────────────────────────────────────── #
        created_k = skipped_k = 0
        for kw, cat_name, priority, match_field in KEYWORD_RULES:
            master = cat(cat_name)
            if not master:
                continue
            _, created = CategoryKeywordRule.objects.get_or_create(
                keyword=kw.lower(),
                defaults={
                    'master_category': master,
                    'priority': priority,
                    'match_field': match_field,
                    'is_active': True,
                },
            )
            if created:
                created_k += 1
            else:
                skipped_k += 1

        self.stdout.write(
            f'Synonyms:  {created_s} created, {skipped_s} already existed\n'
            f'Keywords:  {created_k} created, {skipped_k} already existed'
        )
