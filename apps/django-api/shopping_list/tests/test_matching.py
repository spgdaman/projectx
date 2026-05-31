"""
shopping_list/tests/test_matching.py
--------------------------------------
Unit tests for ProductMatchingService (layers 1 + 2).
Run with: python manage.py test shopping_list.tests.test_matching

Uses Django's TestCase with a small set of fixture products.
No external services required — rapidfuzz runs in-process.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User

from core.models import Retailer, Category, RetailerCategory, CategoryMapping, Product, Deal
from shopping_list.services.matching import ProductMatchingService


class ProductMatchingServiceTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Retailer
        cls.naivas = Retailer.objects.create(name='Naivas')

        # Master categories
        cls.dairy    = Category.objects.create(name='Dairy', parent=None)
        cls.cereals  = Category.objects.create(name='Cereals', parent=None)
        cls.baby     = Category.objects.create(name='Baby Care', parent=None)
        cls.nappies  = Category.objects.create(name='Nappies', parent=cls.baby)

        # Retailer categories + mappings
        def make_product(name, category, price='100.00', old_price=None, sku=None):
            rc, _ = RetailerCategory.objects.get_or_create(
                retailer=cls.naivas, name=category.name
            )
            CategoryMapping.objects.get_or_create(
                retailer_category=rc, defaults={'master_category': category}
            )
            p = Product.objects.create(
                retailer=cls.naivas,
                retailer_category=rc,
                master_category=category,
                name=name,
                price=Decimal(price),
                sku=sku or name[:20],
            )
            Deal.objects.create(
                product=p,
                retailer=cls.naivas,
                current_price=Decimal(price),
                old_price=Decimal(old_price) if old_price else None,
            )
            return p

        cls.milk1 = make_product('Brookside Fresh Whole Milk 1L', cls.dairy,  '78.00', '95.00')
        cls.milk2 = make_product('Tuzo Fresh Milk 500ml',          cls.dairy,  '55.00', '65.00')
        cls.milk3 = make_product('KCC UHT Milk 1L',                cls.dairy,  '92.00')
        cls.uji   = make_product('Uji wa Dhahabu Porridge 500g',   cls.cereals,'120.00', '150.00')
        cls.pamp  = make_product('Pampers Active Baby Size 3 42pcs', cls.nappies,'1240.00','1450.00')

        cls.service = ProductMatchingService()

    def setUp(self):
        # Invalidate cache before each test so fixture data is freshly loaded
        self.service.invalidate_cache()

    # ── Layer 1: Fuzzy matching ──────────────────────────────────────── #

    def test_exact_match_scores_1(self):
        results = self.service.search('Brookside Fresh Whole Milk 1L', limit=5)
        self.assertTrue(len(results) > 0)
        top = results[0]
        self.assertEqual(top.product_id, self.milk1.id)
        self.assertAlmostEqual(top.score, 1.0, places=1)

    def test_partial_name_match(self):
        results = self.service.search('fresh milk', limit=5)
        self.assertTrue(len(results) > 0)
        ids = [r.product_id for r in results]
        # Both milk products should appear
        self.assertIn(self.milk1.id, ids)
        self.assertIn(self.milk2.id, ids)

    def test_abbreviated_query(self):
        results = self.service.search('uji', limit=5)
        self.assertTrue(len(results) > 0)
        ids = [r.product_id for r in results]
        self.assertIn(self.uji.id, ids)

    def test_brand_name_only(self):
        results = self.service.search('pampers', limit=5)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0].product_id, self.pamp.id)

    def test_empty_query_returns_empty(self):
        results = self.service.search('', limit=5)
        self.assertEqual(results, [])

    def test_short_query_returns_empty(self):
        results = self.service.search('a', limit=5)
        self.assertEqual(results, [])

    def test_no_match_gibberish(self):
        results = self.service.search('xyzxyzxyz', limit=5)
        # May return 0 results or very low-score results
        for r in results:
            self.assertLess(r.score, 0.65)

    # ── Layer 2: Category fallback ───────────────────────────────────── #

    def test_category_keyword_milk(self):
        results = self.service.search('milk', limit=10)
        ids = [r.product_id for r in results]
        # All three dairy products should be found via category or fuzzy
        self.assertIn(self.milk1.id, ids)
        self.assertIn(self.milk2.id, ids)
        self.assertIn(self.milk3.id, ids)

    def test_category_keyword_diaper(self):
        results = self.service.search('diapers', limit=5)
        ids = [r.product_id for r in results]
        self.assertIn(self.pamp.id, ids)

    def test_category_match_type_label(self):
        # A word that only matches by category (not fuzzy name)
        results = self.service.search('nappy', limit=5)
        ids = [r.product_id for r in results]
        self.assertIn(self.pamp.id, ids)

    # ── Enrichment ───────────────────────────────────────────────────── #

    def test_enrichment_attaches_price(self):
        results = self.service.search('brookside', limit=3)
        top = next((r for r in results if r.product_id == self.milk1.id), None)
        self.assertIsNotNone(top)
        self.assertEqual(top.best_price, 78.0)
        self.assertEqual(top.old_price,  95.0)
        self.assertEqual(top.discount_pct, 17)   # (95-78)/95 * 100 = 17%

    def test_enrichment_attaches_retailer(self):
        results = self.service.search('fresh milk', limit=5)
        self.assertTrue(len(results) > 0)
        for r in results:
            self.assertIn('Naivas', r.retailers)

    # ── Resolve ──────────────────────────────────────────────────────── #

    def test_resolve_returns_best_match(self):
        match = self.service.resolve('Fresh whole milk 1L')
        self.assertIsNotNone(match)
        self.assertEqual(match.product_id, self.milk1.id)

    def test_resolve_returns_none_for_gibberish(self):
        match = self.service.resolve('xyzxyzxyz_not_a_product')
        self.assertIsNone(match)

    # ── Deduplication ────────────────────────────────────────────────── #

    def test_no_duplicate_product_ids(self):
        results = self.service.search('milk', limit=20)
        ids = [r.product_id for r in results]
        self.assertEqual(len(ids), len(set(ids)), 'Duplicate product IDs in results')

    # ── Cache ────────────────────────────────────────────────────────── #

    def test_cache_invalidation_rebuilds(self):
        self.service.search('milk', limit=3)   # build cache
        self.assertTrue(self.service._cache_built)
        self.service.invalidate_cache()
        self.assertFalse(self.service._cache_built)
        results = self.service.search('milk', limit=3)   # rebuild
        self.assertTrue(self.service._cache_built)
        self.assertTrue(len(results) > 0)
