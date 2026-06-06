from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Seed CategorySynonym and CategoryKeywordRule tables. IDEMPOTENT.'
    )

    def handle(self, *args, **options):
        from core.models import (
            Category, CategoryKeywordRule, CategorySynonym, Retailer,
        )
        from core.services.category_mapper import CategoryMapper

        categories = {c.name.lower(): c for c in Category.objects.all()}

        def cat(name):
            c = categories.get(name.lower())
            if not c:
                self.stderr.write(f'WARNING: "{name}" not found — skipping')
            return c

        retailers = {r.name: r for r in Retailer.objects.all()}

        # ── L0 / L1 / L2 synonyms ──────────────────────────────────────────
        # Raw strings exactly as they appear in StagingProduct, mapped to
        # master Category short names (c.name, not the full __str__ path).
        SYNONYMS = [
            # ── L0 (category_name) ─────────────────────────────────────────
            ('Beauty & Cosmetics',  0, 'Naivas',    'Beauty & Cosmetics'),
            ('Beverage',            0, None,        'Beverages'),
            ('ELECTRONICS',         0, None,        'Electronics & Appliances'),
            ('Electronics',         0, None,        'Electronics & Appliances'),
            ('FOODS',               0, None,        'Food & Beverages'),
            ('Foods',               0, None,        'Food & Beverages'),
            ('FRESH',               0, None,        'Food & Beverages'),
            ('Fresh',               0, None,        'Food & Beverages'),
            ('Fresh Food',          0, 'Naivas',    'Fresh Produce'),
            ('Food Cupboard',       0, 'Naivas',    'Food & Beverages'),
            ('HOMECARE',            0, None,        'Home Care'),
            ('Homecare',            0, None,        'Home Care'),
            ('HOUSEHOLDS',          0, None,        'Household & Kitchen'),
            ('Households',          0, None,        'Household & Kitchen'),
            ('LIQUOR',              0, None,        'Liquor'),
            ('Liquor',              0, None,        'Liquor'),
            ('PERSONAL CARE',       0, None,        'Personal Care'),
            ('Personal Care',       0, None,        'Personal Care'),
            ('TEXTILE',             0, None,        'Fashion & Accessories'),
            ('Textile',             0, None,        'Fashion & Accessories'),

            # ── L1 (sub_category_name) ─────────────────────────────────────
            ('Animal Feeds & Pets',             1, None, 'Pet & Animal Care'),
            ('Apparel Accessories',             1, None, 'Fashion & Accessories'),
            ('Baby Care',                       1, None, 'Baby Care & Diapers'),
            ('Beauty Cosmetics',                1, None, 'Beauty & Cosmetics'),
            ('Beer',                            1, None, 'Beer & Cider'),
            ('Beverages',                       1, None, 'Beverages'),
            ('Beverage Deals',                  1, 'Naivas', 'Beverages'),
            ('Bicycles',                        1, None, 'Bicycles & Outdoor'),
            ('Body Care',                       1, None, 'Body & Skin Care'),
            ('Breakfast',                       1, None, 'Breakfast & Cereals'),
            ('Cakes & Bread',                   1, None, 'Bakery & Deli'),
            ('Candles & Fragrances',            1, None, 'Air Fresheners & Candles'),
            ('Car Care',                        1, None, 'Car Care'),
            ('Cleaners & Polish',               1, None, 'Surface Cleaners'),
            ('Cleaning Equipments',             1, None, 'Cleaning Equipment'),
            ('Confectioneries (Sweets)',         1, None, 'Snacks & Confectionery'),
            ('Commodities',                     1, None, 'Food & Beverages'),
            ('Cookers And Ovens',               1, None, 'Cookers & Ovens'),
            ('Cooking Equipment And Fuel',      1, None, 'Cookers & Ovens'),
            ('Cooking Oils & Fats',             1, None, 'Cooking Oils & Fats'),
            ('Dairy Products',                  1, None, 'Dairy Products'),
            ('Diapers & Wipes',                 1, None, 'Baby Care & Diapers'),
            ('Electrical Accessories',          1, None, 'Electrical Accessories'),
            ('Electronics',                     1, None, 'Electronics & Appliances'),
            ('Electronics Deals',               1, 'Naivas', 'Electronics & Appliances'),
            ('Ethnic',                          1, None, 'Food & Beverages'),
            ('Fats & Oils',                     1, None, 'Cooking Oils & Fats'),
            ('Flour',                           1, None, 'Pasta, Rice & Grains'),
            ('Food Additives',                  1, None, 'Condiments & Seasoning'),
            ('Foods',                           1, None, 'Food & Beverages'),
            ('Footwear',                        1, None, 'Fashion & Accessories'),
            ('Fresh',                           1, None, 'Fresh Produce'),
            ('Fresh Deals',                     1, 'Naivas', 'Fresh Produce'),
            ('Fridges & Freezers',              1, None, 'Large Appliances'),
            ('Fridges And Freezers',            1, None, 'Large Appliances'),
            ('Frozen Food Consignment',         1, None, 'Frozen Foods'),
            ('Frozen Foods',                    1, None, 'Frozen Foods'),
            ('Fruits & Veggies',                1, None, 'Fresh Produce'),
            ('Furniture',                       1, None, 'Furniture'),
            ('Hair Care Products',              1, None, 'Hair Care'),
            ('Hardware',                        1, None, 'Home Improvement & Hardware'),
            ('Health & Wellness',               1, None, 'Health & Wellness'),
            ('Home Audio',                      1, None, 'TV & Audio'),
            ('Home Improvement',                1, None, 'Home Improvement & Hardware'),
            ('Home Textile',                    1, None, 'Home Textiles'),
            ('Homecare',                        1, None, 'Home Care'),
            ('Hot Beverage',                    1, None, 'Beverages'),
            ('Households',                      1, None, 'Household & Kitchen'),
            ('Housekeeping',                    1, None, 'Home Care'),
            ('Juices & Carbonates',             1, None, 'Beverages'),
            ('Kitchen & Dining',                1, None, 'Kitchen & Dining'),
            ('Kitchen Appliances',              1, None, 'Small Kitchen Appliances'),
            ('Light Plastic',                   1, None, 'Household & Kitchen'),
            ('Liquor',                          1, None, 'Liquor'),
            ('Luggage & Bags',                  1, None, 'Luggage & Bags'),
            ('Meat Products & Eggs',            1, None, 'Meat, Fish & Eggs'),
            ("Men's Apparel",                   1, None, 'Fashion & Accessories'),
            ('Naivas Bakery',                   1, 'Naivas', 'Bakery & Deli'),
            ('Naivas Butchery',                 1, 'Naivas', 'Meat, Fish & Eggs'),
            ('Office Supplies And Stationery',  1, None, 'Household & Kitchen'),
            ('Oral Care Products',              1, None, 'Oral Care'),
            ('Party And Occasions',             1, None, 'Snacks & Confectionery'),
            ('Pasta & Noodles',                 1, None, 'Pasta, Rice & Grains'),
            ('Personal Care',                   1, None, 'Personal Care'),
            ('Personal Wash',                   1, None, 'Body & Skin Care'),
            ('Pest Control',                    1, None, 'Pest Control'),
            ('Phones, Tablets & Accessories',   1, None, 'Phones & Tablets'),
            ('Processed Canned Foods',          1, None, 'Food & Beverages'),
            ('Protective Wear',                 1, None, 'Fashion & Accessories'),
            ('Quickmart Bakery',                1, 'Quickmart', 'Bakery & Deli'),
            ('Quickmart Butchery & Fishery',    1, 'Quickmart', 'Meat, Fish & Eggs'),
            ('Quickmart Deli',                  1, 'Quickmart', 'Bakery & Deli'),
            ('Quickmart Veges',                 1, 'Quickmart', 'Fresh Produce'),
            ('Quickmart(Internal)',             1, 'Quickmart', 'Food & Beverages'),
            ('Rice & Cereals',                  1, None, 'Pasta, Rice & Grains'),
            ('Sanitary',                        1, None, 'Sanitary Products'),
            ('Seasoning & Condiments',          1, None, 'Condiments & Seasoning'),
            ('Small Kitchen & Home Appliance',  1, None, 'Small Kitchen Appliances'),
            ('Snack Foods',                     1, None, 'Snacks & Confectionery'),
            ('Snacks',                          1, None, 'Snacks & Confectionery'),
            ('Soaps & Detergents',              1, None, 'Laundry & Detergents'),
            ('Spirits',                         1, None, 'Spirits & Liqueurs'),
            ('Sports And Fitness Equipment',    1, None, 'Bicycles & Outdoor'),
            ('Sugar',                           1, None, 'Pasta, Rice & Grains'),
            ('Televisions',                     1, None, 'TV & Audio'),
            ('Textile',                         1, None, 'Fashion & Accessories'),
            ('Tissue',                          1, None, 'Tissue & Paper Products'),
            ('Toys And Games',                  1, None, 'Toys & Games'),
            ('Tv',                              1, None, 'TV & Audio'),
            ('Washers And Dryers',              1, None, 'Large Appliances'),
            ('Water',                           1, None, 'Beverages'),
            ('Wines',                           1, None, 'Wines'),

            # ── L2 (sub_category_2_name) ───────────────────────────────────
            ('Corn Snacks',             2, None,     'Snacks & Confectionery'),
            ('Deodorant & Anti-Perspirant', 2, None, 'Body & Skin Care'),
            ('Flour',                   2, None,     'Pasta, Rice & Grains'),
            ('Freezers',                2, None,     'Large Appliances'),
            ('Fresh Chicken',           2, None,     'Meat, Fish & Eggs'),
            ('Fruits',                  2, None,     'Fresh Produce'),
            ('Naivas Cakes',            2, 'Naivas', 'Bakery & Deli'),
            ('Plastic Furniture Sets',  2, None,     'Furniture'),
            ('Smart TVs',               2, None,     'TV & Audio'),
            ('Spreads',                 2, None,     'Cooking Oils & Fats'),
            ('Tea & Tea Bags',          2, None,     'Beverages'),
            ('Vegetable Oils',          2, None,     'Cooking Oils & Fats'),
            ('Water Dispensers',        2, None,     'Small Kitchen Appliances'),
        ]

        # ── Keyword rules ───────────────────────────────────────────────────
        # Format: (keyword, master_cat_SHORT_name, priority, match_field)
        # Priority: 100+ brand names · 10-99 product types · 1-9 generic
        KEYWORD_RULES = [
            # ── Liquor brands (120) ────────────────────────────────────────
            ('absolut',        'Spirits & Liqueurs', 120, 'product_name'),
            ('smirnoff',       'Spirits & Liqueurs', 120, 'product_name'),
            ('jameson',        'Spirits & Liqueurs', 120, 'product_name'),
            ('jamesons',       'Spirits & Liqueurs', 120, 'product_name'),
            ('chivas',         'Spirits & Liqueurs', 120, 'product_name'),
            ('glenlivet',      'Spirits & Liqueurs', 120, 'product_name'),
            ('captain morgan', 'Spirits & Liqueurs', 120, 'product_name'),
            ('olmeca',         'Spirits & Liqueurs', 120, 'product_name'),
            ('martell',        'Spirits & Liqueurs', 120, 'product_name'),
            ('beefeater',      'Spirits & Liqueurs', 120, 'product_name'),
            ('malfy',          'Spirits & Liqueurs', 120, 'product_name'),
            ('kibao',          'Spirits & Liqueurs', 120, 'product_name'),
            ('khor',           'Spirits & Liqueurs', 120, 'product_name'),
            ('morosha',        'Spirits & Liqueurs', 120, 'product_name'),
            ('pervak',         'Spirits & Liqueurs', 120, 'product_name'),
            ('richot',         'Spirits & Liqueurs', 120, 'product_name'),
            ('shustoff',       'Spirits & Liqueurs', 120, 'product_name'),
            ('royal king',     'Spirits & Liqueurs', 120, 'product_name'),
            ('caribia',        'Spirits & Liqueurs', 120, 'product_name'),
            ('royal circle',   'Spirits & Liqueurs', 115, 'product_name'),
            ('harrison',       'Spirits & Liqueurs', 110, 'product_name'),
            ('macintyres',     'Spirits & Liqueurs', 110, 'product_name'),
            ('black & white',  'Spirits & Liqueurs', 110, 'product_name'),
            ('hunters choice', 'Spirits & Liqueurs', 110, 'product_name'),

            # Wine brands (115)
            ('frontera',  'Wines', 115, 'product_name'),
            ('drostdy',   'Wines', 115, 'product_name'),
            ('calvet',    'Wines', 115, 'product_name'),
            ('argento',   'Wines', 115, 'product_name'),
            ('esporao',   'Wines', 115, 'product_name'),
            ('vondeling', 'Wines', 115, 'product_name'),
            ('boska',     'Wines', 115, 'product_name'),
            ('bacalhoa',  'Wines', 115, 'product_name'),
            ('oreanda',   'Wines', 115, 'product_name'),
            ('itinera',   'Wines', 115, 'product_name'),
            ('assobio',   'Wines', 115, 'product_name'),
            ('mikado',    'Wines', 115, 'product_name'),
            ('alandra',   'Wines', 115, 'product_name'),
            ('amarone',   'Wines', 115, 'product_name'),
            ('angelo',    'Wines', 110, 'product_name'),
            ('mosketto',  'Wines', 110, 'product_name'),
            ('steinbock', 'Wines', 110, 'product_name'),

            # Beer/cider brands (115)
            ('hunters cider',  'Beer & Cider', 115, 'product_name'),
            ('hunters 330ml',  'Beer & Cider', 115, 'product_name'),

            # ── Liquor product-type keywords (80-95) ──────────────────────
            ('vodka',    'Spirits & Liqueurs', 95, 'product_name'),
            ('whisky',   'Spirits & Liqueurs', 95, 'product_name'),
            ('whiskey',  'Spirits & Liqueurs', 95, 'product_name'),
            ('brandy',   'Spirits & Liqueurs', 90, 'product_name'),
            ('cognac',   'Spirits & Liqueurs', 90, 'product_name'),
            ('tequila',  'Spirits & Liqueurs', 90, 'product_name'),
            ('gin',      'Spirits & Liqueurs', 85, 'product_name'),
            ('rum',      'Spirits & Liqueurs', 85, 'product_name'),
            ('cider',    'Beer & Cider',        90, 'product_name'),
            ('prosecco', 'Wines',               90, 'product_name'),
            ('malbec',   'Wines',               90, 'product_name'),
            ('merlot',   'Wines',               90, 'product_name'),
            ('chardonnay','Wines',              90, 'product_name'),
            ('sauvignon','Wines',               90, 'product_name'),
            ('cabernet', 'Wines',               90, 'product_name'),
            ('shiraz',   'Wines',               90, 'product_name'),
            ('port wine','Wines',               85, 'product_name'),
            ('wine',     'Wines',               80, 'product_name'),

            # ── Dairy brands (115) ─────────────────────────────────────────
            ('brookside', 'Dairy Products', 115, 'product_name'),
            ('daima',     'Dairy Products', 115, 'product_name'),
            ('tuzo',      'Dairy Products', 115, 'product_name'),
            ('lato',      'Dairy Products', 115, 'product_name'),
            ('fresha',    'Dairy Products', 115, 'product_name'),
            ('molo',      'Dairy Products', 115, 'product_name'),
            ('kcc',       'Dairy Products', 115, 'product_name'),
            ('vito',      'Dairy Products', 115, 'product_name'),
            ('creambell', 'Dairy Products', 115, 'product_name'),
            ('aberdare',  'Dairy Products', 115, 'product_name'),
            ('abony',     'Dairy Products', 115, 'product_name'),
            ('sirimon',   'Dairy Products', 115, 'product_name'),
            ('dairyland', 'Dairy Products', 115, 'product_name'),

            # Dairy product types (70-85)
            ('yoghurt',  'Dairy Products', 85, 'product_name'),
            ('yogurt',   'Dairy Products', 85, 'product_name'),
            ('cheese',   'Dairy Products', 80, 'product_name'),
            ('milk',     'Dairy Products', 75, 'product_name'),

            # ── Beverages brands (115) ─────────────────────────────────────
            ('aquamist',     'Beverages', 115, 'product_name'),
            ('dormans',      'Beverages', 115, 'product_name'),
            ('gibsons',      'Beverages', 115, 'product_name'),
            ('kericho gold', 'Beverages', 115, 'product_name'),
            ('baraka chai',  'Beverages', 115, 'product_name'),
            ('faraja',       'Beverages', 115, 'product_name'),
            ('nescafe',      'Beverages', 115, 'product_name'),
            ('maccoffee',    'Beverages', 115, 'product_name'),
            ('alicafe',      'Beverages', 115, 'product_name'),
            ('score',        'Beverages', 115, 'product_name'),
            ('monster',      'Beverages', 115, 'product_name'),
            ('highlands',    'Beverages', 115, 'product_name'),
            ('orchid valley','Beverages', 115, 'product_name'),
            ('pepsi',        'Beverages', 115, 'product_name'),
            ('mirinda',      'Beverages', 115, 'product_name'),
            ('fix8',         'Beverages', 115, 'product_name'),
            ('quencher',     'Beverages', 115, 'product_name'),
            ('ketepa',       'Beverages', 115, 'product_name'),
            ('club soda',    'Beverages', 110, 'product_name'),
            ('aquaclear',    'Beverages', 110, 'product_name'),
            ('pep',          'Beverages', 100, 'product_name'),

            # Beverage product types (60-80)
            ('kombucha',  'Beverages', 85, 'product_name'),
            ('cordial',   'Beverages', 80, 'product_name'),
            ('juice',     'Beverages', 75, 'product_name'),
            ('coffee',    'Beverages', 70, 'product_name'),
            ('soda',      'Beverages', 70, 'product_name'),
            ('water',     'Beverages', 60, 'product_name'),

            # ── Cooking oils brands (115) ──────────────────────────────────
            ('fresh fri',   'Cooking Oils & Fats', 115, 'product_name'),
            ('kasuku',      'Cooking Oils & Fats', 115, 'product_name'),
            ('tily',        'Cooking Oils & Fats', 115, 'product_name'),
            ('rinsun',      'Cooking Oils & Fats', 115, 'product_name'),
            ('rina',        'Cooking Oils & Fats', 115, 'product_name'),
            ('elianto',     'Cooking Oils & Fats', 115, 'product_name'),
            ('prestige',    'Cooking Oils & Fats', 115, 'product_name'),
            ('blue band',   'Cooking Oils & Fats', 110, 'product_name'),
            ('avena',       'Cooking Oils & Fats', 110, 'product_name'),
            ('captain cook','Cooking Oils & Fats', 110, 'product_name'),
            ('kentaste',    'Cooking Oils & Fats', 110, 'product_name'),
            ('breadbest',   'Cooking Oils & Fats', 110, 'product_name'),

            # Cooking oil product types (70-85)
            ('sunflower',  'Cooking Oils & Fats', 80, 'product_name'),
            ('olive oil',  'Cooking Oils & Fats', 80, 'product_name'),
            ('margarine',  'Cooking Oils & Fats', 80, 'product_name'),
            ('olive',      'Cooking Oils & Fats', 70, 'product_name'),

            # ── Condiments brands (115) ────────────────────────────────────
            ('kaputei',  'Condiments & Seasoning', 115, 'product_name'),
            ('peptang',  'Condiments & Seasoning', 115, 'product_name'),
            ('lyons',    'Condiments & Seasoning', 110, 'product_name'),

            # Condiment product types (65-85)
            ('ketchup',    'Condiments & Seasoning', 85, 'product_name'),
            ('mayonnaise', 'Condiments & Seasoning', 85, 'product_name'),
            ('mustard',    'Condiments & Seasoning', 85, 'product_name'),
            ('vinegar',    'Condiments & Seasoning', 85, 'product_name'),
            ('chutney',    'Condiments & Seasoning', 80, 'product_name'),
            ('pesto',      'Condiments & Seasoning', 80, 'product_name'),
            ('jam',        'Condiments & Seasoning', 75, 'product_name'),
            ('sauce',      'Condiments & Seasoning', 65, 'product_name'),

            # ── Snacks & Confectionery brands (115) ───────────────────────
            ('cadbury',   'Snacks & Confectionery', 115, 'product_name'),
            ('nuvita',    'Snacks & Confectionery', 115, 'product_name'),
            ('manji',     'Snacks & Confectionery', 115, 'product_name'),
            ('bdelo',     'Snacks & Confectionery', 115, 'product_name'),
            ('nutro',     'Snacks & Confectionery', 115, 'product_name'),
            ('maltesers', 'Snacks & Confectionery', 115, 'product_name'),
            ('twix',      'Snacks & Confectionery', 115, 'product_name'),
            ('mars',      'Snacks & Confectionery', 110, 'product_name'),
            ('skittles',  'Snacks & Confectionery', 115, 'product_name'),
            ('haldiram',  'Snacks & Confectionery', 115, 'product_name'),
            ('bugles',    'Snacks & Confectionery', 115, 'product_name'),
            ('bazooka',   'Snacks & Confectionery', 115, 'product_name'),
            ('poco loco', 'Snacks & Confectionery', 115, 'product_name'),

            # Snack product types (70-85)
            ('biscuit',   'Snacks & Confectionery', 80, 'product_name'),
            ('biscuits',  'Snacks & Confectionery', 80, 'product_name'),
            ('chocolate', 'Snacks & Confectionery', 75, 'product_name'),
            ('crisps',    'Snacks & Confectionery', 80, 'product_name'),
            ('wafer',     'Snacks & Confectionery', 80, 'product_name'),
            ('cookie',    'Snacks & Confectionery', 75, 'product_name'),
            ('cookies',   'Snacks & Confectionery', 75, 'product_name'),
            ('cracker',   'Snacks & Confectionery', 75, 'product_name'),
            ('candy',     'Snacks & Confectionery', 75, 'product_name'),
            ('tortilla',  'Snacks & Confectionery', 80, 'product_name'),
            ('snack',     'Snacks & Confectionery', 65, 'product_name'),
            ('snacks',    'Snacks & Confectionery', 65, 'product_name'),

            # ── Breakfast & Cereals (90-115) ───────────────────────────────
            ('weetabix',  'Breakfast & Cereals', 115, 'product_name'),
            ('quaker',    'Breakfast & Cereals', 115, 'product_name'),
            ('alpen',     'Breakfast & Cereals', 115, 'product_name'),
            ('grainmill', 'Breakfast & Cereals', 115, 'product_name'),
            ('temmys',    'Breakfast & Cereals', 115, 'product_name'),
            ('oats',      'Breakfast & Cereals', 85, 'product_name'),
            ('cereal',    'Breakfast & Cereals', 75, 'product_name'),
            ('cereals',   'Breakfast & Cereals', 75, 'product_name'),
            ('porridge',  'Breakfast & Cereals', 75, 'product_name'),

            # ── Pasta, Rice & Grains (85-115) ─────────────────────────────
            ('daawat',     'Pasta, Rice & Grains', 115, 'product_name'),
            ('sunrice',    'Pasta, Rice & Grains', 115, 'product_name'),
            ('pearl rice', 'Pasta, Rice & Grains', 115, 'product_name'),
            ('ranee',      'Pasta, Rice & Grains', 115, 'product_name'),
            ('kpl',        'Pasta, Rice & Grains', 115, 'product_name'),
            ('royal umbrella', 'Pasta, Rice & Grains', 115, 'product_name'),
            ('nala',       'Pasta, Rice & Grains', 110, 'product_name'),
            ('santa lucia','Pasta, Rice & Grains', 110, 'product_name'),
            ('italiano',   'Pasta, Rice & Grains', 110, 'product_name'),
            ('pembe',      'Pasta, Rice & Grains', 115, 'product_name'),
            ('ndovu',      'Pasta, Rice & Grains', 115, 'product_name'),
            ('amaize',     'Pasta, Rice & Grains', 115, 'product_name'),
            ('dola',       'Pasta, Rice & Grains', 115, 'product_name'),
            ('soko',       'Pasta, Rice & Grains', 115, 'product_name'),
            ('spaghetti',  'Pasta, Rice & Grains', 90, 'product_name'),
            ('pasta',      'Pasta, Rice & Grains', 85, 'product_name'),
            ('rice',       'Pasta, Rice & Grains', 75, 'product_name'),
            ('flour',      'Pasta, Rice & Grains', 75, 'product_name'),
            ('noodle',     'Pasta, Rice & Grains', 80, 'product_name'),
            ('noodles',    'Pasta, Rice & Grains', 80, 'product_name'),
            ('maize',      'Pasta, Rice & Grains', 70, 'product_name'),

            # ── Meat, Fish & Eggs (80-115) ─────────────────────────────────
            ('farmers choice', 'Meat, Fish & Eggs', 115, 'product_name'),
            ('kenchic',        'Meat, Fish & Eggs', 115, 'product_name'),
            ('qmp',            'Meat, Fish & Eggs', 115, 'product_name'),
            ('sardines',    'Meat, Fish & Eggs', 90, 'product_name'),
            ('sardine',     'Meat, Fish & Eggs', 90, 'product_name'),
            ('tuna',        'Meat, Fish & Eggs', 90, 'product_name'),
            ('anchovies',   'Meat, Fish & Eggs', 90, 'product_name'),
            ('sausage',     'Meat, Fish & Eggs', 85, 'product_name'),
            ('smokies',     'Meat, Fish & Eggs', 85, 'product_name'),
            ('pork mince',  'Meat, Fish & Eggs', 85, 'product_name'),
            ('beef',        'Meat, Fish & Eggs', 80, 'product_name'),
            ('chicken',     'Meat, Fish & Eggs', 75, 'product_name'),

            # ── Bakery & Deli (90-115) ─────────────────────────────────────
            ('bread',   'Bakery & Deli', 85, 'product_name'),
            ('cake',    'Bakery & Deli', 75, 'product_name'),

            # ── Frozen Foods (70-80) ───────────────────────────────────────
            ('frozen',  'Frozen Foods', 70, 'product_name'),

            # ── Laundry & Detergents brands (115) ─────────────────────────
            ('ariel',   'Laundry & Detergents', 115, 'product_name'),
            ('persil',  'Laundry & Detergents', 115, 'product_name'),
            ('omo',     'Laundry & Detergents', 115, 'product_name'),
            ('toss',    'Laundry & Detergents', 115, 'product_name'),
            ('gama',    'Laundry & Detergents', 115, 'product_name'),
            ('comfort', 'Laundry & Detergents', 110, 'product_name'),
            ('downy',   'Laundry & Detergents', 115, 'product_name'),
            ('sta-soft','Laundry & Detergents', 115, 'product_name'),
            ('sta soft','Laundry & Detergents', 115, 'product_name'),
            ('sunlight','Laundry & Detergents', 115, 'product_name'),
            ('jamaa',   'Laundry & Detergents', 110, 'product_name'),
            ('cuddles', 'Laundry & Detergents', 115, 'product_name'),

            # Laundry product types (70-85)
            ('detergent',      'Laundry & Detergents', 80, 'product_name'),
            ('laundry',        'Laundry & Detergents', 80, 'product_name'),
            ('washing powder', 'Laundry & Detergents', 85, 'product_name'),
            ('machine wash',   'Laundry & Detergents', 85, 'product_name'),
            ('fabric softener','Laundry & Detergents', 80, 'product_name'),

            # ── Surface Cleaners brands (115) ──────────────────────────────
            ('clorox',   'Surface Cleaners', 115, 'product_name'),
            ('topex',    'Surface Cleaners', 115, 'product_name'),
            ('rinz',     'Surface Cleaners', 110, 'product_name'),
            ('bytex',    'Surface Cleaners', 115, 'product_name'),
            ('magnee',   'Surface Cleaners', 115, 'product_name'),
            ('biochem',  'Surface Cleaners', 115, 'product_name'),
            ('bioclean', 'Surface Cleaners', 115, 'product_name'),
            ('germol',   'Surface Cleaners', 115, 'product_name'),
            ('roberts',  'Surface Cleaners', 110, 'product_name'),
            ('rush',     'Surface Cleaners', 100, 'product_name'),
            ('sanex',    'Surface Cleaners', 110, 'product_name'),
            ('wills',    'Surface Cleaners', 100, 'product_name'),

            # Surface cleaner product types (70-85)
            ('bleach',        'Surface Cleaners', 80, 'product_name'),
            ('disinfectant',  'Surface Cleaners', 80, 'product_name'),
            ('antiseptic',    'Surface Cleaners', 75, 'product_name'),

            # ── Tissue & Paper Products brands (110) ──────────────────────
            ('bella',    'Tissue & Paper Products', 110, 'product_name'),
            ('celine',   'Tissue & Paper Products', 110, 'product_name'),
            ('dawn',     'Tissue & Paper Products', 110, 'product_name'),
            ('fiesta',   'Tissue & Paper Products', 110, 'product_name'),
            ('flora',    'Tissue & Paper Products', 110, 'product_name'),
            ('livelle',  'Tissue & Paper Products', 110, 'product_name'),
            ('petals',   'Tissue & Paper Products', 110, 'product_name'),
            ('rosy',     'Tissue & Paper Products', 110, 'product_name'),
            ('tena',     'Tissue & Paper Products', 110, 'product_name'),
            ('toilex',   'Tissue & Paper Products', 110, 'product_name'),
            ('velvex',   'Tissue & Paper Products', 100, 'product_name'),
            ('hanan',    'Tissue & Paper Products', 100, 'product_name'),

            # Tissue product types (65-80)
            ('tissue',      'Tissue & Paper Products', 75, 'product_name'),
            ('serviette',   'Tissue & Paper Products', 80, 'product_name'),
            ('serviettes',  'Tissue & Paper Products', 80, 'product_name'),
            ('napkin',      'Tissue & Paper Products', 75, 'product_name'),
            ('napkins',     'Tissue & Paper Products', 75, 'product_name'),
            ('toilet roll', 'Tissue & Paper Products', 80, 'product_name'),
            ('toilet rolls','Tissue & Paper Products', 80, 'product_name'),

            # ── Air Fresheners & Candles brands (110) ─────────────────────
            ('general fresh', 'Air Fresheners & Candles', 115, 'product_name'),
            ('dr marcus',     'Air Fresheners & Candles', 115, 'product_name'),
            ('fresh day',     'Air Fresheners & Candles', 115, 'product_name'),
            ('tropikal',      'Air Fresheners & Candles', 115, 'product_name'),

            # Air freshener product types (70-80)
            ('freshener',  'Air Fresheners & Candles', 80, 'product_name'),
            ('diffuser',   'Air Fresheners & Candles', 80, 'product_name'),
            ('rim block',  'Air Fresheners & Candles', 80, 'product_name'),
            ('toilet block','Air Fresheners & Candles', 80, 'product_name'),

            # ── Cleaning Equipment (75-110) ────────────────────────────────
            ('scotch brite', 'Cleaning Equipment', 115, 'product_name'),
            ('kleenit',      'Cleaning Equipment', 115, 'product_name'),
            ('scouring',     'Cleaning Equipment', 75, 'product_name'),
            ('scrubber',     'Cleaning Equipment', 75, 'product_name'),
            ('loofah',       'Cleaning Equipment', 80, 'product_name'),
            ('sponge',       'Cleaning Equipment', 65, 'product_name'),

            # ── Pest Control (80-115) ──────────────────────────────────────
            ('mortein',       'Pest Control', 115, 'product_name'),
            ('doom',          'Pest Control', 115, 'product_name'),
            ('insecticide',   'Pest Control', 85, 'product_name'),
            ('mosquito',      'Pest Control', 80, 'product_name'),

            # ── Personal Care — Oral Care brands (115) ─────────────────────
            ('colgate',    'Oral Care', 115, 'product_name'),
            ('sensodyne',  'Oral Care', 115, 'product_name'),
            ('aquafresh',  'Oral Care', 115, 'product_name'),
            ('dabur',      'Oral Care', 110, 'product_name'),

            # Oral product types (75-85)
            ('toothpaste', 'Oral Care', 85, 'product_name'),
            ('toothbrush', 'Oral Care', 85, 'product_name'),
            ('t/paste',    'Oral Care', 80, 'product_name'),
            ('tbrush',     'Oral Care', 80, 'product_name'),
            ('mouthwash',  'Oral Care', 85, 'product_name'),

            # ── Body & Skin Care brands (115) ──────────────────────────────
            ('dettol',          'Body & Skin Care', 115, 'product_name'),
            ('nivea',           'Body & Skin Care', 115, 'product_name'),
            ('dove',            'Body & Skin Care', 115, 'product_name'),
            ('carex',           'Body & Skin Care', 115, 'product_name'),
            ('imperial leather','Body & Skin Care', 115, 'product_name'),
            ('palmolive',       'Body & Skin Care', 115, 'product_name'),
            ('radox',           'Body & Skin Care', 115, 'product_name'),
            ('dalan',           'Body & Skin Care', 115, 'product_name'),
            ('sawa',            'Body & Skin Care', 115, 'product_name'),
            ('geisha',          'Body & Skin Care', 115, 'product_name'),
            ('flamingo',        'Body & Skin Care', 110, 'product_name'),
            ('nice & lovely',   'Body & Skin Care', 115, 'product_name'),
            ('nice and lovely', 'Body & Skin Care', 115, 'product_name'),
            ('ixora',           'Body & Skin Care', 115, 'product_name'),
            ('hobby',           'Body & Skin Care', 115, 'product_name'),
            ('clere',           'Body & Skin Care', 115, 'product_name'),
            ('vaseline',        'Body & Skin Care', 115, 'product_name'),
            ('brio',            'Body & Skin Care', 110, 'product_name'),
            ('lanzo',           'Body & Skin Care', 115, 'product_name'),
            ('astonish',        'Body & Skin Care', 110, 'product_name'),
            ('biogel',          'Body & Skin Care', 110, 'product_name'),
            ('unac',            'Body & Skin Care', 100, 'product_name'),
            ('il ',             'Body & Skin Care', 100, 'product_name'),

            # Body care product types (65-80)
            ('body wash',   'Body & Skin Care', 80, 'product_name'),
            ('bodywash',    'Body & Skin Care', 80, 'product_name'),
            ('body lotion', 'Body & Skin Care', 80, 'product_name'),
            ('lotion',      'Body & Skin Care', 75, 'product_name'),
            ('handwash',    'Body & Skin Care', 70, 'product_name'),
            ('hand wash',   'Body & Skin Care', 70, 'product_name'),
            ('soap',        'Body & Skin Care', 65, 'product_name'),
            ('petroleum',   'Body & Skin Care', 75, 'product_name'),
            ('deodorant',   'Body & Skin Care', 75, 'product_name'),
            ('roll on',     'Body & Skin Care', 75, 'product_name'),
            ('roll-on',     'Body & Skin Care', 75, 'product_name'),

            # ── Hair Care brands (115) ──────────────────────────────────────
            ('pantene',    'Hair Care', 115, 'product_name'),
            ('tresemme',   'Hair Care', 115, 'product_name'),
            ('head & shoulders', 'Hair Care', 115, 'product_name'),
            ('loreal elvive',    'Hair Care', 115, 'product_name'),
            ('organics',   'Hair Care', 110, 'product_name'),
            ('vatika',     'Hair Care', 115, 'product_name'),
            ('clear',      'Hair Care', 100, 'product_name'),
            ('snf',        'Hair Care', 110, 'product_name'),

            # Hair product types (70-85)
            ('shampoo',    'Hair Care', 85, 'product_name'),
            ('hair oil',   'Hair Care', 80, 'product_name'),
            ('styling gel','Hair Care', 75, 'product_name'),
            ('relaxer',    'Hair Care', 80, 'product_name'),

            # ── Beauty & Cosmetics brands (115) ────────────────────────────
            ('garnier',   'Beauty & Cosmetics', 115, 'product_name'),
            ('himalaya',  'Beauty & Cosmetics', 115, 'product_name'),
            ('loreal paris','Beauty & Cosmetics', 115, 'product_name'),
            ('mamaearth', 'Beauty & Cosmetics', 115, 'product_name'),
            ('cheetah',   'Beauty & Cosmetics', 110, 'product_name'),
            ('brut',      'Beauty & Cosmetics', 100, 'product_name'),
            ('girlfriend','Beauty & Cosmetics', 100, 'product_name'),

            # Beauty product types (70-85)
            ('serum',     'Beauty & Cosmetics', 80, 'product_name'),
            ('edt',       'Beauty & Cosmetics', 85, 'product_name'),
            ('edp',       'Beauty & Cosmetics', 85, 'product_name'),
            ('perfume',   'Beauty & Cosmetics', 80, 'product_name'),
            ('face wash', 'Beauty & Cosmetics', 80, 'product_name'),

            # ── Baby Care & Diapers brands (115) ───────────────────────────
            ('pampers',   'Baby Care & Diapers', 115, 'product_name'),
            ('huggies',   'Baby Care & Diapers', 115, 'product_name'),
            ('cussons',   'Baby Care & Diapers', 115, 'product_name'),
            ('nipnap',    'Baby Care & Diapers', 115, 'product_name'),
            ('softcare',  'Baby Care & Diapers', 115, 'product_name'),
            ('mamaearth baby','Baby Care & Diapers', 115, 'product_name'),

            # Baby product types (70-85)
            ('diapers',   'Baby Care & Diapers', 90, 'product_name'),
            ('diaper',    'Baby Care & Diapers', 90, 'product_name'),
            ('nappies',   'Baby Care & Diapers', 90, 'product_name'),
            ('nappy',     'Baby Care & Diapers', 90, 'product_name'),
            ('baby wipes','Baby Care & Diapers', 85, 'product_name'),
            ('baby',      'Baby Care & Diapers', 65, 'product_name'),
            ('wipes',     'Baby Care & Diapers', 65, 'product_name'),

            # ── Sanitary Products brands (115) ────────────────────────────
            ('always',  'Sanitary Products', 115, 'product_name'),
            ('kotex',   'Sanitary Products', 115, 'product_name'),
            ('sofy',    'Sanitary Products', 115, 'product_name'),
            ('velvex conforta', 'Sanitary Products', 115, 'product_name'),

            # Sanitary product types (75-85)
            ('sanitary', 'Sanitary Products', 80, 'product_name'),
            ('panty',    'Sanitary Products', 80, 'product_name'),

            # ── Health & Wellness (75-115) ─────────────────────────────────
            ('condom',    'Health & Wellness', 115, 'product_name'),
            ('condoms',   'Health & Wellness', 115, 'product_name'),
            ('contempo',  'Health & Wellness', 115, 'product_name'),
            ('protein bar','Health & Wellness', 85, 'product_name'),
            ('supplement','Health & Wellness', 75, 'product_name'),

            # ── Pet & Animal Care brands (115) ────────────────────────────
            ('friskies',   'Pet & Animal Care', 115, 'product_name'),
            ('snappy tom', 'Pet & Animal Care', 115, 'product_name'),
            ('tlc',        'Pet & Animal Care', 115, 'product_name'),
            ('go cat',     'Pet & Animal Care', 115, 'product_name'),
            ('gnawlers',   'Pet & Animal Care', 115, 'product_name'),
            ('bchoice',    'Pet & Animal Care', 115, 'product_name'),
            ('bark bite',  'Pet & Animal Care', 115, 'product_name'),

            # Pet product types (80-90)
            ('dog food',  'Pet & Animal Care', 90, 'product_name'),
            ('cat food',  'Pet & Animal Care', 90, 'product_name'),
            ('pet food',  'Pet & Animal Care', 90, 'product_name'),
            ('dog',       'Pet & Animal Care', 85, 'product_name'),
            ('pet',       'Pet & Animal Care', 80, 'product_name'),

            # ── Electronics brands (115) ───────────────────────────────────
            ('mika',    'Electronics & Appliances', 115, 'product_name'),
            ('ramtons', 'Electronics & Appliances', 115, 'product_name'),
            ('samsung', 'Electronics & Appliances', 115, 'product_name'),
            ('oryx',    'Electronics & Appliances', 110, 'product_name'),
            ('sinbo',   'Electronics & Appliances', 110, 'product_name'),
            ('fame',    'Electronics & Appliances', 100, 'product_name'),

            # Electronics subcategory product types
            ('kettle',      'Small Kitchen Appliances', 90, 'product_name'),
            ('blender',     'Small Kitchen Appliances', 90, 'product_name'),
            ('microwave',   'Small Kitchen Appliances', 90, 'product_name'),
            ('mwave',       'Small Kitchen Appliances', 90, 'product_name'),
            ('juicer',      'Small Kitchen Appliances', 90, 'product_name'),
            ('toaster',     'Small Kitchen Appliances', 90, 'product_name'),
            ('dispenser',   'Small Kitchen Appliances', 80, 'product_name'),
            ('wdispenser',  'Small Kitchen Appliances', 85, 'product_name'),
            ('air fryer',   'Small Kitchen Appliances', 90, 'product_name'),
            ('fryer',       'Small Kitchen Appliances', 80, 'product_name'),
            ('fridge',      'Large Appliances',         90, 'product_name'),
            ('freezer',     'Large Appliances',         90, 'product_name'),
            ('washer',      'Large Appliances',         85, 'product_name'),
            ('wmachine',    'Large Appliances',         90, 'product_name'),
            ('washing machine','Large Appliances',      90, 'product_name'),
            ('cooker',      'Cookers & Ovens',          80, 'product_name'),
            ('television',  'TV & Audio',               90, 'product_name'),
            ('subwoofer',   'TV & Audio',               90, 'product_name'),
            ('soundbar',    'TV & Audio',               90, 'product_name'),
            ('sound bar',   'TV & Audio',               90, 'product_name'),
            ('tv',          'TV & Audio',               70, 'product_name'),

            # ── Household & Kitchen (75-115) ───────────────────────────────
            ('luminarc',  'Kitchen & Dining', 115, 'product_name'),
            ('regal',     'Kitchen & Dining',  95, 'product_name'),
            ('flask',     'Kitchen & Dining',  80, 'product_name'),

            # ── Toys & Games (80-115) ──────────────────────────────────────
            ('barbie',    'Toys & Games', 115, 'product_name'),
            ('hot wheels','Toys & Games', 115, 'product_name'),
            ('uno',       'Toys & Games', 110, 'product_name'),
            ('toy',       'Toys & Games',  75, 'product_name'),
            ('doll',      'Toys & Games',  80, 'product_name'),

            # ── Car Care (80-115) ──────────────────────────────────────────
            ('carwash',   'Car Care', 90, 'product_name'),
            ('car wash',  'Car Care', 90, 'product_name'),

            # ── Fashion & Accessories (80-115) ─────────────────────────────
            ('luggage',   'Luggage & Bags', 85, 'product_name'),
        ]

        # ── Create synonyms ─────────────────────────────────────────────────
        created_s = skipped_s = warn_s = 0
        for raw, level, retailer_name, cat_name in SYNONYMS:
            master = cat(cat_name)
            if not master:
                warn_s += 1
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

        # ── Create keyword rules ────────────────────────────────────────────
        created_k = skipped_k = warn_k = 0
        for kw, cat_name, priority, match_field in KEYWORD_RULES:
            master = cat(cat_name)
            if not master:
                warn_k += 1
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
            f'Synonyms:  {created_s} created, {skipped_s} already existed'
            + (f', {warn_s} skipped (cat not found)' if warn_s else '')
        )
        self.stdout.write(
            f'Keywords:  {created_k} created, {skipped_k} already existed'
            + (f', {warn_k} skipped (cat not found)' if warn_k else '')
        )
