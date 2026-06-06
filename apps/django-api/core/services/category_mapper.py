"""
core/services/category_mapper.py
----------------------------------
Hierarchy-aware category mapping service.

Attempts Tiers 1-4 in order at each level (L2 → L1 → L0).
The first tier + level combination that produces a confident match wins.
Falls through to MappingReviewQueue if nothing matches.

Usage:
  from core.services.category_mapper import CategoryMapper
  mapper = CategoryMapper()
  result = mapper.map(staging_product)
  # result.category  — resolved Category or None
  # result.tier      — which tier matched (1-4) or None
  # result.level     — which level matched (0-2) or None
  # result.score     — fuzzy score if tier==4, else None
  # result.category_depth — nesting depth (root=0) or None
  # result.category_path  — 'Food > Dairy > Milk' or None
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from django.db.models import F, Q
from django.utils import timezone

logger = logging.getLogger(__name__)

FUZZY_THRESHOLD = 80  # minimum rapidfuzz score to accept


@dataclass
class MappingResult:
    category: Optional[object] = None   # Category instance
    tier: Optional[int] = None          # 1, 2, 3, or 4
    level: Optional[int] = None         # 0=L0, 1=L1, 2=L2
    score: Optional[float] = None       # fuzzy score 0-100
    matched_on: Optional[str] = None    # the string that matched
    category_depth: Optional[int] = None
    category_path: Optional[str] = None

    @property
    def matched(self) -> bool:
        return self.category is not None


class CategoryMapper:

    def __init__(self):
        # Loaded once per instance for fast fuzzy matching.
        # Invalidate by calling invalidate_cache() or creating a new instance.
        self._master_categories = None
        self._keyword_rules = None

    # ── Public API ──────────────────────────────────────────────────────── #

    def map(self, staging_product) -> MappingResult:
        """
        Main entry point. Runs Tiers 1-4 against the staging product's
        category fields.

        Tier order: 1 (exact) → 2 (synonym) → 3 (keyword) → 4 (fuzzy)
        Level order within each tier: L2 → L1 → L0

        On miss: creates a MappingReviewQueue entry and returns
        MappingResult(category=None).
        """
        levels = self._get_levels(staging_product)
        retailer = self._get_retailer(staging_product)

        result = self._tier1_exact(levels, retailer)
        if result.matched:
            return result

        result = self._tier2_synonym(levels, retailer)
        if result.matched:
            return result

        result = self._tier3_keyword(staging_product)
        if result.matched:
            return result

        result = self._tier4_fuzzy(levels)
        if result.matched:
            self._record_fuzzy_synonym(
                raw=result.matched_on,
                level=result.level,
                retailer=retailer,
                category=result.category,
                score=result.score,
            )
            return result

        self._enqueue_review(staging_product, retailer, result)
        return MappingResult()

    def map_bulk(self, staging_products) -> dict:
        """
        Map a queryset or list of StagingProduct instances.
        Returns dict: {staging_product.id: MappingResult}

        Reuses the in-memory category cache across all products — much faster
        than calling map() in a loop from outside this class.
        """
        self._load_master_categories()
        self._load_keyword_rules()
        return {sp.id: self.map(sp) for sp in staging_products}

    # ── Static helpers ───────────────────────────────────────────────────── #

    @staticmethod
    def category_depth(category) -> int:
        """
        Depth in the master hierarchy.
        Root (parent=None) = 0. Each nesting = +1.
        """
        depth = 0
        node = category
        while node.parent_id is not None:
            depth += 1
            node = node.parent
            if depth > 10:  # safety: bad data guard
                break
        return depth

    @staticmethod
    def category_path(category) -> str:
        """Full path string: 'Food > Dairy > Milk'"""
        parts = []
        node = category
        while node is not None:
            parts.append(node.name)
            node = node.parent
        parts.reverse()
        return ' > '.join(parts)

    # ── Helper: extract levels ───────────────────────────────────────────── #

    def _get_levels(self, sp) -> list:
        """
        Returns list of (level_int, raw_string) tuples, deepest first,
        skipping empty/None values.

        Example output:
          [(2, "Instant Porridge"),
           (1, "Cereals & Porridge"),
           (0, "Food Cupboard")]
        """
        levels = []
        l2 = getattr(sp, 'sub_category_2_name', None)
        l1 = getattr(sp, 'sub_category_name', None)
        l0 = getattr(sp, 'category_name', None)
        if l2 and l2.strip():
            levels.append((2, l2.strip()))
        if l1 and l1.strip():
            levels.append((1, l1.strip()))
        if l0 and l0.strip():
            levels.append((0, l0.strip()))
        return levels

    def _get_retailer(self, sp):
        """Resolve the Retailer instance from staging product."""
        from core.models import Retailer
        name = getattr(sp, 'retailer_name', None)
        if not name:
            return None
        try:
            return Retailer.objects.get(name=name)
        except Retailer.DoesNotExist:
            return None

    # ── Normalisation ────────────────────────────────────────────────────── #

    @staticmethod
    def normalise(raw: str) -> str:
        """
        Normalise a raw category string for consistent matching across
        retailers.
        - Lowercase, strip, collapse whitespace
        - Remove punctuation that varies by retailer (&, -, /, etc.)
        - Keep alphanumeric and spaces only

        Examples:
          "Cereals & Porridge"  → "cereals porridge"
          "Baby-Care Products"  → "baby care products"
          "Snacks,Biscuits"     → "snacks biscuits"
        """
        s = raw.lower().strip()
        s = re.sub(r'[&,/\\|]', ' ', s)
        s = re.sub(r'-', ' ', s)
        s = re.sub(r"[^a-z0-9 ']", ' ', s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    # ── Tier 1: Exact match ──────────────────────────────────────────────── #

    def _tier1_exact(self, levels, retailer) -> MappingResult:
        """
        Collect ALL matching CategoryMappings across all levels, then return
        the one pointing to the deepest master_category (not just the first).
        """
        from core.models import RetailerCategory, CategoryMapping

        best_result = MappingResult()
        best_depth = -1

        for level, raw in levels:
            rc_qs = (
                RetailerCategory.objects.filter(retailer=retailer)
                if retailer
                else RetailerCategory.objects.all()
            ).filter(Q(name=raw) | Q(name__iexact=raw))

            for rc in rc_qs:
                try:
                    mapping = CategoryMapping.objects.get(retailer_category=rc)
                    depth = CategoryMapper.category_depth(mapping.master_category)
                    if depth > best_depth:
                        best_depth = depth
                        best_result = MappingResult(
                            category=mapping.master_category,
                            tier=1, level=level, matched_on=raw,
                            category_depth=depth,
                            category_path=CategoryMapper.category_path(
                                mapping.master_category),
                        )
                        logger.debug(
                            '[T1] Matched "%s" (L%d, depth=%d) → %s',
                            raw, level, depth, mapping.master_category)
                except CategoryMapping.DoesNotExist:
                    continue

        return best_result

    # ── Tier 2: Synonym match ────────────────────────────────────────────── #

    def _tier2_synonym(self, levels, retailer) -> MappingResult:
        """
        Collect ALL matching synonyms across all levels, return the one
        pointing to the deepest master_category.
        """
        from core.models import CategorySynonym

        best_result = MappingResult()
        best_depth = -1

        for level, raw in levels:
            norm = self.normalise(raw)

            syns = (
                CategorySynonym.objects
                .filter(raw_name=norm, level=level)
                .filter(Q(retailer=retailer) | Q(retailer__isnull=True))
                .select_related(
                    'master_category',
                    'master_category__parent',
                    'master_category__parent__parent',
                )
                .order_by(F('retailer').asc(nulls_last=True))
            )

            for syn in syns:
                depth = CategoryMapper.category_depth(syn.master_category)
                if depth > best_depth:
                    best_depth = depth
                    best_result = MappingResult(
                        category=syn.master_category,
                        tier=2, level=level, matched_on=norm,
                        category_depth=depth,
                        category_path=CategoryMapper.category_path(
                            syn.master_category),
                    )
                    logger.debug(
                        '[T2] Synonym "%s" (L%d, depth=%d) → %s',
                        norm, level, depth, syn.master_category)

        return best_result

    # ── Tier 3: Keyword rules ────────────────────────────────────────────── #

    def _load_keyword_rules(self):
        if self._keyword_rules is not None:
            return
        from core.models import CategoryKeywordRule
        self._keyword_rules = list(
            CategoryKeywordRule.objects
            .filter(is_active=True)
            .select_related(
                'master_category',
                'master_category__parent',
                'master_category__parent__parent',
            )
            .order_by('-priority')
        )
        logger.debug('[T3] Loaded %d keyword rules', len(self._keyword_rules))

    def _tier3_keyword(self, sp) -> MappingResult:
        """
        Collect ALL matching keyword rules, then pick the one with highest
        priority. Break priority ties by choosing the deeper (more specific)
        category.
        """
        self._load_keyword_rules()

        product_name = getattr(sp, 'product_name', '') or ''
        cat          = getattr(sp, 'category_name', '') or ''
        sub1         = getattr(sp, 'sub_category_name', '') or ''
        sub2         = getattr(sp, 'sub_category_2_name', '') or ''
        any_cat      = f'{cat} {sub1} {sub2}'
        any_all      = f'{product_name} {cat} {sub1} {sub2}'

        matches = []
        for rule in self._keyword_rules:
            kw = rule.keyword.lower()
            pattern = r'\b' + re.escape(kw) + r'\b'

            if rule.match_field == 'product_name':
                haystack = product_name.lower()
            elif rule.match_field == 'any_category':
                haystack = any_cat.lower()
            else:  # 'any'
                haystack = any_all.lower()

            if re.search(pattern, haystack):
                depth = CategoryMapper.category_depth(rule.master_category)
                matches.append((rule, depth))

        if not matches:
            return MappingResult()

        # Highest priority first; break ties by depth (deeper = more specific)
        matches.sort(key=lambda x: (x[0].priority, x[1]), reverse=True)
        best_rule, best_depth = matches[0]

        logger.debug(
            '[T3] Keyword "%s" matched "%s" (depth=%d) → %s',
            best_rule.keyword, product_name, best_depth, best_rule.master_category)
        return MappingResult(
            category=best_rule.master_category,
            tier=3, level=None, matched_on=best_rule.keyword,
            category_depth=best_depth,
            category_path=CategoryMapper.category_path(best_rule.master_category),
        )

    # ── Tier 4: Fuzzy match ──────────────────────────────────────────────── #

    def _load_master_categories(self):
        """
        Load all master category names into memory for fast fuzzy comparison.
        Stored as list of (Category, name, normalised, depth) 4-tuples.
        """
        if self._master_categories is not None:
            return
        from core.models import Category
        cats = Category.objects.all().select_related(
            'parent',
            'parent__parent',
            'parent__parent__parent',
        )
        self._master_categories = [
            (c, c.name, self.normalise(c.name),
             CategoryMapper.category_depth(c))
            for c in cats
        ]
        logger.debug('[T4] Loaded %d master categories for fuzzy', len(self._master_categories))

    def _tier4_fuzzy(self, levels) -> MappingResult:
        """
        For each level (deepest first), run rapidfuzz token_set_ratio against
        all master category names. A small depth bonus (max 3 pts) breaks score
        ties in favour of leaf categories, but the raw score governs the
        threshold check.
        """
        try:
            from rapidfuzz import fuzz
        except ImportError:
            logger.warning('[T4] rapidfuzz not installed — skipping fuzzy tier. Run: pip install rapidfuzz')
            return MappingResult()

        self._load_master_categories()

        best_result = MappingResult()

        for level, raw in levels:
            norm = self.normalise(raw)
            best_score = 0.0
            best_cat = None
            best_effective = 0.0

            for cat, cat_name, cat_norm, cat_depth in self._master_categories:
                score = fuzz.token_set_ratio(norm, cat_norm)
                # Depth bonus: max 3 pts so leaves beat roots on score ties
                effective = score + min(cat_depth, 3)
                if effective > best_effective:
                    best_effective = effective
                    best_score = score  # real score for threshold check
                    best_cat = cat

            if best_score >= FUZZY_THRESHOLD and best_cat:
                depth = CategoryMapper.category_depth(best_cat)
                logger.debug(
                    '[T4] Fuzzy "%s" (L%d) → %s (score %.1f, depth=%d)',
                    norm, level, best_cat, best_score, depth)
                return MappingResult(
                    category=best_cat,
                    tier=4, level=level,
                    score=best_score, matched_on=norm,
                    category_depth=depth,
                    category_path=CategoryMapper.category_path(best_cat),
                )

            if best_score > (best_result.score or 0):
                best_result = MappingResult(
                    category=best_cat,
                    tier=4, level=level,
                    score=best_score, matched_on=norm,
                )

        # Nothing cleared the threshold — return best attempt for the review queue
        return MappingResult(
            category=None,
            tier=4,
            score=best_result.score,
            level=best_result.level,
            matched_on=best_result.matched_on,
        )

    # ── Feedback and review queue ────────────────────────────────────────── #

    def _record_fuzzy_synonym(self, raw, level, retailer, category, score):
        """
        Auto-add a CategorySynonym when a fuzzy match clears FUZZY_THRESHOLD+5
        so Tier 2 catches it next run.
        """
        if score is None or score < FUZZY_THRESHOLD + 5:
            return
        from core.models import CategorySynonym
        CategorySynonym.objects.get_or_create(
            raw_name=raw,
            retailer=retailer,
            level=level,
            defaults={'master_category': category, 'source': 'fuzzy'},
        )

    def _enqueue_review(self, sp, retailer, last_result):
        """Add to MappingReviewQueue if not already queued for this staging product."""
        from core.models import MappingReviewQueue
        MappingReviewQueue.objects.get_or_create(
            staging_product=sp,
            resolved=False,
            defaults={
                'retailer': retailer,
                'tier_reached': last_result.tier or 4,
                'best_fuzzy_suggestion': last_result.category,
                'best_fuzzy_score': last_result.score,
                'best_fuzzy_level': last_result.level,
            },
        )

    # ── Cache invalidation ───────────────────────────────────────────────── #

    def invalidate_cache(self):
        """Force reload of master categories and keyword rules on the next map() call."""
        self._master_categories = None
        self._keyword_rules = None


# Module-level singleton for use in management commands and the normalisation
# pipeline. Re-instantiate (or call invalidate_cache) when the category tree
# changes.
category_mapper = CategoryMapper()
