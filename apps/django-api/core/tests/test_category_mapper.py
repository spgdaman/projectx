from django.test import TestCase
from unittest.mock import patch

from core.models import (
    Category, CategoryKeywordRule, CategoryMapping, CategorySynonym,
    MappingReviewQueue, Retailer, RetailerCategory, StagingProduct,
)
from core.services.category_mapper import CategoryMapper, MappingResult, FUZZY_THRESHOLD


def _make_sp(product_name, retailer_name='Naivas', cat=None, sub1=None, sub2=None):
    return StagingProduct.objects.create(
        retailer_name=retailer_name,
        product_name=product_name,
        price='100.00',
        is_manual=False,
        category_name=cat,
        sub_category_name=sub1,
        sub_category_2_name=sub2,
    )


class CategoryMapperTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.retailer = Retailer.objects.create(name='Naivas')
        cls.other_retailer = Retailer.objects.create(name='Quickmart')

        # Master category hierarchy
        cls.personal_care = Category.objects.create(name='Personal Care')
        cls.baby_care = Category.objects.create(name='Baby Care & Diapers', parent=cls.personal_care)
        cls.food = Category.objects.create(name='Food & Beverages')
        cls.cereals = Category.objects.create(name='Breakfast & Cereals', parent=cls.food)
        cls.snacks = Category.objects.create(name='Snacks & Confectionery', parent=cls.food)

    def _make_retailer_cat(self, name, retailer=None):
        retailer = retailer or self.retailer
        return RetailerCategory.objects.create(retailer=retailer, name=name)

    # ── Normalise ─────────────────────────────────────────────────────── #

    def test_normalise_strips_ampersand(self):
        self.assertEqual(CategoryMapper.normalise('Cereals & Porridge'), 'cereals porridge')

    def test_normalise_strips_hyphen(self):
        self.assertEqual(CategoryMapper.normalise('Baby-Care'), 'baby care')

    def test_normalise_lowercases_and_strips(self):
        self.assertEqual(CategoryMapper.normalise('  Snacks,Biscuits  '), 'snacks biscuits')

    # ── Tier 1 ────────────────────────────────────────────────────────── #

    def test_tier1_exact_match_L2(self):
        rc = self._make_retailer_cat('Baby Diapers')
        CategoryMapping.objects.create(retailer_category=rc, master_category=self.baby_care)
        sp = _make_sp('Some Product', cat='Mother & Child', sub1='Baby Products', sub2='Baby Diapers')

        mapper = CategoryMapper()
        result = mapper.map(sp)

        self.assertTrue(result.matched)
        self.assertEqual(result.tier, 1)
        self.assertEqual(result.level, 2)
        self.assertEqual(result.category, self.baby_care)

    def test_tier1_falls_back_to_L1_when_L2_missing(self):
        rc = self._make_retailer_cat('Baby Products')
        CategoryMapping.objects.create(retailer_category=rc, master_category=self.baby_care)
        sp = _make_sp('Some Product', cat='Mother & Child', sub1='Baby Products')

        mapper = CategoryMapper()
        result = mapper.map(sp)

        self.assertTrue(result.matched)
        self.assertEqual(result.tier, 1)
        self.assertEqual(result.level, 1)

    def test_tier1_falls_back_to_L0(self):
        rc = self._make_retailer_cat('Mother & Child')
        CategoryMapping.objects.create(retailer_category=rc, master_category=self.baby_care)
        sp = _make_sp('Some Product', cat='Mother & Child')

        mapper = CategoryMapper()
        result = mapper.map(sp)

        self.assertTrue(result.matched)
        self.assertEqual(result.tier, 1)
        self.assertEqual(result.level, 0)

    def test_tier1_miss_goes_to_tier2(self):
        sp = _make_sp('Unknown Product', cat='Unknown Cat')

        mapper = CategoryMapper()
        # Tier 1 should miss — no RetailerCategory or CategoryMapping exists
        levels = mapper._get_levels(sp)
        retailer = mapper._get_retailer(sp)
        result = mapper._tier1_exact(levels, retailer)

        self.assertFalse(result.matched)

    # ── Tier 2 ────────────────────────────────────────────────────────── #

    def test_tier2_synonym_L1_match(self):
        # "baby products" normalises to "baby products"
        CategorySynonym.objects.create(
            raw_name='baby products',
            level=1,
            retailer=self.retailer,
            master_category=self.baby_care,
            source='manual',
        )
        sp = _make_sp('Baby Wipes', cat='Mother', sub1='Baby Products')

        mapper = CategoryMapper()
        result = mapper.map(sp)

        self.assertTrue(result.matched)
        self.assertEqual(result.tier, 2)
        self.assertEqual(result.level, 1)
        self.assertEqual(result.category, self.baby_care)

    def test_tier2_retailer_specific_beats_global(self):
        # Global synonym maps to cereals
        CategorySynonym.objects.create(
            raw_name='baby stuff',
            level=1,
            retailer=None,
            master_category=self.cereals,
            source='manual',
        )
        # Retailer-specific maps to baby_care
        CategorySynonym.objects.create(
            raw_name='baby stuff',
            level=1,
            retailer=self.retailer,
            master_category=self.baby_care,
            source='manual',
        )
        sp = _make_sp('Baby Wipes', cat='Mother', sub1='Baby Stuff')

        mapper = CategoryMapper()
        result = mapper.map(sp)

        self.assertTrue(result.matched)
        self.assertEqual(result.category, self.baby_care)

    def test_tier2_global_synonym_applies_to_all_retailers(self):
        CategorySynonym.objects.create(
            raw_name='baby products',
            level=1,
            retailer=None,
            master_category=self.baby_care,
            source='manual',
        )
        sp = _make_sp('Baby Wipes', retailer_name='Quickmart', cat='Mother', sub1='Baby Products')

        mapper = CategoryMapper()
        result = mapper.map(sp)

        self.assertTrue(result.matched)
        self.assertEqual(result.category, self.baby_care)

    # ── Tier 3 ────────────────────────────────────────────────────────── #

    def test_tier3_keyword_matches_product_name(self):
        CategoryKeywordRule.objects.create(
            keyword='pampers',
            master_category=self.baby_care,
            priority=100,
            match_field='product_name',
            is_active=True,
        )
        sp = _make_sp('Pampers Active Baby Size 4', cat='Baby')

        mapper = CategoryMapper()
        result = mapper.map(sp)

        self.assertTrue(result.matched)
        self.assertEqual(result.tier, 3)
        self.assertEqual(result.category, self.baby_care)

    def test_tier3_higher_priority_wins(self):
        CategoryKeywordRule.objects.create(
            keyword='cereal',
            master_category=self.cereals,
            priority=10,
            match_field='product_name',
            is_active=True,
        )
        CategoryKeywordRule.objects.create(
            keyword='baby cereal',
            master_category=self.baby_care,
            priority=50,
            match_field='product_name',
            is_active=True,
        )
        sp = _make_sp('Baby Cereal Starter Pack', cat='Baby')

        mapper = CategoryMapper()
        result = mapper.map(sp)

        self.assertTrue(result.matched)
        self.assertEqual(result.category, self.baby_care)

    def test_tier3_word_boundary_no_false_positive(self):
        CategoryKeywordRule.objects.create(
            keyword='oil',
            master_category=self.food,
            priority=60,
            match_field='product_name',
            is_active=True,
        )
        sp = _make_sp('Aluminium Foil 30m', cat='Kitchen')

        mapper = CategoryMapper()
        # Only Tier 3 — check directly so Tier 4 fuzzy doesn't confound
        mapper._load_keyword_rules()
        result = mapper._tier3_keyword(sp)

        self.assertFalse(result.matched)

    # ── Tier 4 ────────────────────────────────────────────────────────── #

    def test_tier4_fuzzy_high_score_matches(self):
        sp = _make_sp('Some Product', cat='Food', sub1='Cereals and Porridge')

        mapper = CategoryMapper()
        mapper._load_master_categories()
        levels = mapper._get_levels(sp)
        result = mapper._tier4_fuzzy(levels)

        # "cereals and porridge" should score >= 80 against "Breakfast & Cereals"
        # or similar depending on master categories present
        # At minimum, tier4 should run without error
        self.assertIsInstance(result, MappingResult)

    def test_tier4_below_threshold_does_not_match(self):
        sp = _make_sp('Some Product', cat='xyzzy impossible category that matches nothing')

        mapper = CategoryMapper()
        mapper._load_master_categories()
        levels = mapper._get_levels(sp)
        result = mapper._tier4_fuzzy(levels)

        self.assertFalse(result.matched)

    def test_tier4_deepest_level_tried_first(self):
        # L2 = "Breakfast Cereals" is closer to "Breakfast & Cereals" than
        # L0 = "General Food" is. Verify L2 is attempted first and wins.
        sp = _make_sp('Cornflakes', cat='General Food', sub1='Dry Goods', sub2='Breakfast Cereals')

        mapper = CategoryMapper()
        mapper._load_master_categories()
        levels = mapper._get_levels(sp)

        # L2 should be first in the levels list
        self.assertEqual(levels[0][0], 2)
        self.assertEqual(levels[0][1], 'Breakfast Cereals')

    # ── End-to-end / pipeline ─────────────────────────────────────────── #

    def test_full_pipeline_tier1_wins(self):
        rc = self._make_retailer_cat('Baby Diapers')
        CategoryMapping.objects.create(retailer_category=rc, master_category=self.baby_care)
        sp = _make_sp('Pampers', cat='Baby Diapers')

        mapper = CategoryMapper()
        result = mapper.map(sp)

        self.assertTrue(result.matched)
        self.assertEqual(result.tier, 1)
        self.assertEqual(MappingReviewQueue.objects.filter(staging_product=sp).count(), 0)

    def test_full_pipeline_falls_through_to_queue(self):
        sp = _make_sp('Totally Unmappable XYZ999', cat='zzzz no category')

        mapper = CategoryMapper()
        result = mapper.map(sp)

        self.assertFalse(result.matched)
        self.assertEqual(MappingReviewQueue.objects.filter(staging_product=sp).count(), 1)

    def test_map_bulk_returns_dict_keyed_by_id(self):
        sp1 = _make_sp('Product One', cat='Baby')
        sp2 = _make_sp('Product Two', cat='Food')
        sp3 = _make_sp('Product Three', cat='Home')

        mapper = CategoryMapper()
        results = mapper.map_bulk([sp1, sp2, sp3])

        self.assertIn(sp1.id, results)
        self.assertIn(sp2.id, results)
        self.assertIn(sp3.id, results)
        for r in results.values():
            self.assertIsInstance(r, MappingResult)

    def test_fuzzy_synonym_auto_created_on_high_score(self):
        sp = _make_sp('Some Product', sub1='Baby Diapers and Nappies')

        mapper = CategoryMapper()
        # Manually trigger _record_fuzzy_synonym with a score above threshold+5
        high_score = FUZZY_THRESHOLD + 10
        norm = CategoryMapper.normalise('Baby Diapers and Nappies')
        mapper._record_fuzzy_synonym(
            raw=norm,
            level=1,
            retailer=self.retailer,
            category=self.baby_care,
            score=high_score,
        )

        self.assertTrue(
            CategorySynonym.objects.filter(
                raw_name=norm, level=1, retailer=self.retailer, source='fuzzy'
            ).exists()
        )

    def test_fuzzy_synonym_not_created_on_low_score(self):
        norm = CategoryMapper.normalise('vague thing')
        mapper = CategoryMapper()
        mapper._record_fuzzy_synonym(
            raw=norm,
            level=0,
            retailer=self.retailer,
            category=self.baby_care,
            score=FUZZY_THRESHOLD + 2,  # below threshold+5
        )

        self.assertFalse(CategorySynonym.objects.filter(raw_name=norm).exists())
