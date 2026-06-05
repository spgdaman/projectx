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
        Look up each level in CategoryMapping (the existing table).
        Tries the retailer's RetailerCategory → CategoryMapping chain.
        """
        from core.models import RetailerCategory, CategoryMapping

        for level, raw in levels:
            rc_qs = (
                RetailerCategory.objects.filter(retailer=retailer)
                if retailer
                else RetailerCategory.objects.all()
            ).filter(Q(name=raw) | Q(name__iexact=raw))

            for rc in rc_qs:
                try:
                    mapping = CategoryMapping.objects.get(retailer_category=rc)
                    logger.debug('[T1] Matched "%s" (L%d) → %s', raw, level, mapping.master_category)
                    return MappingResult(
                        category=mapping.master_category,
                        tier=1, level=level, matched_on=raw,
                    )
                except CategoryMapping.DoesNotExist:
                    continue

        return MappingResult()

    # ── Tier 2: Synonym match ────────────────────────────────────────────── #

    def _tier2_synonym(self, levels, retailer) -> MappingResult:
        """
        Look up each level's normalised string in CategorySynonym.
        Retailer-specific synonyms take priority over global ones.
        """
        from core.models import CategorySynonym

        for level, raw in levels:
            norm = self.normalise(raw)

            syn = (
                CategorySynonym.objects
                .filter(raw_name=norm, level=level)
                .filter(Q(retailer=retailer) | Q(retailer__isnull=True))
                .select_related('master_category')
                .order_by(F('retailer').asc(nulls_last=True))  # retailer-specific before global
                .first()
            )

            if syn:
                logger.debug('[T2] Synonym "%s" (L%d) → %s', norm, level, syn.master_category)
                return MappingResult(
                    category=syn.master_category,
                    tier=2, level=level, matched_on=norm,
                )

        return MappingResult()

    # ── Tier 3: Keyword rules ────────────────────────────────────────────── #

    def _load_keyword_rules(self):
        if self._keyword_rules is not None:
            return
        from core.models import CategoryKeywordRule
        self._keyword_rules = list(
            CategoryKeywordRule.objects
            .filter(is_active=True)
            .select_related('master_category')
            .order_by('-priority')
        )
        logger.debug('[T3] Loaded %d keyword rules', len(self._keyword_rules))

    def _tier3_keyword(self, sp) -> MappingResult:
        """
        Test active keyword rules against the product's name and/or category
        fields. Rules checked in priority order (highest first). First match
        wins. Keyword matching is word-boundary aware: "oil" matches
        "Cooking Oil" but not "Foil".
        """
        self._load_keyword_rules()

        product_name = getattr(sp, 'product_name', '') or ''
        cat          = getattr(sp, 'category_name', '') or ''
        sub1         = getattr(sp, 'sub_category_name', '') or ''
        sub2         = getattr(sp, 'sub_category_2_name', '') or ''
        any_cat      = f'{cat} {sub1} {sub2}'
        any_all      = f'{product_name} {cat} {sub1} {sub2}'

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
                logger.debug('[T3] Keyword "%s" matched "%s" → %s', kw, product_name, rule.master_category)
                return MappingResult(
                    category=rule.master_category,
                    tier=3, level=None, matched_on=kw,
                )

        return MappingResult()

    # ── Tier 4: Fuzzy match ──────────────────────────────────────────────── #

    def _load_master_categories(self):
        """
        Load all master category names into memory for fast fuzzy comparison.
        Stored as list of (Category instance, name string, normalised string).
        """
        if self._master_categories is not None:
            return
        from core.models import Category
        cats = Category.objects.all().select_related('parent')
        self._master_categories = [
            (c, c.name, self.normalise(c.name))
            for c in cats
        ]
        logger.debug('[T4] Loaded %d master categories for fuzzy', len(self._master_categories))

    def _tier4_fuzzy(self, levels) -> MappingResult:
        """
        For each level (deepest first), run rapidfuzz token_set_ratio against
        all master category names. Returns the first match above
        FUZZY_THRESHOLD.

        If rapidfuzz is not installed, logs a warning and returns empty result.
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

            for cat, cat_name, cat_norm in self._master_categories:
                score = fuzz.token_set_ratio(norm, cat_norm)
                if score > best_score:
                    best_score = score
                    best_cat = cat

            if best_score >= FUZZY_THRESHOLD and best_cat:
                logger.debug('[T4] Fuzzy "%s" (L%d) → %s (score %.1f)', norm, level, best_cat, best_score)
                return MappingResult(
                    category=best_cat,
                    tier=4, level=level,
                    score=best_score, matched_on=norm,
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
