"""
shopping_list/services/matching.py
------------------------------------
ProductMatchingService — layers 1 and 2 only (layer 3 semantic search parked).

Layer 1: Fuzzy string matching via rapidfuzz
  - Runs token_set_ratio against all product names in the DB
  - Handles: abbreviations, word reordering, partial brand names
  - Threshold: 65 (configurable via FUZZY_MATCH_THRESHOLD in settings)
  - Returns top N results ranked by score

Layer 2: Category fallback via core.Category hierarchy
  - Fires when query matches a known category keyword
  - Returns all products in that master category + children
  - Ranked by current deal discount percentage

Both layers merge results, deduplicate by product ID,
and return a unified list of MatchResult objects.

REQUIREMENTS (add to requirements.txt):
  rapidfuzz>=3.6.0

USAGE:
  from shopping_list.services.matching import ProductMatchingService

  service = ProductMatchingService()

  # Autocomplete: returns top matches for a partial query
  results = service.search('fresh mil', limit=8)

  # Resolve: returns single best match for a confirmed query
  match = service.resolve('fresh whole milk 1L')
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from django.conf import settings
from django.db.models import Q, Prefetch

logger = logging.getLogger(__name__)

# Minimum score (0–100) for a fuzzy match to be included in results.
# Raise this to get fewer but more precise results.
# Lower it if users complain about missing obvious matches.
FUZZY_THRESHOLD = getattr(settings, 'FUZZY_MATCH_THRESHOLD', 65)

# Maximum results returned by search()
DEFAULT_LIMIT = 10

# Category keyword map — maps common user terms to master category names.
# Add more entries as you discover what users type.
# Keys are lowercase, values must match Category.name in your DB exactly.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    'milk':        ['Dairy', 'Beverages'],
    'uji':         ['Cereals', 'Breakfast'],
    'flour':       ['Baking', 'Cereals'],
    'sugar':       ['Baking', 'Sweeteners'],
    'rice':        ['Grains', 'Dry Foods'],
    'oil':         ['Cooking Oils', 'Fats'],
    'diaper':      ['Baby Care', 'Nappies'],
    'nappy':       ['Baby Care', 'Nappies'],
    'soap':        ['Personal Care', 'Cleaning'],
    'bread':       ['Bakery', 'Bread'],
    'egg':         ['Dairy', 'Eggs'],
    'chicken':     ['Meat & Poultry'],
    'beef':        ['Meat & Poultry'],
    'fish':        ['Seafood', 'Fish'],
    'tea':         ['Beverages', 'Hot Drinks'],
    'coffee':      ['Beverages', 'Hot Drinks'],
    'water':       ['Beverages', 'Water'],
    'juice':       ['Beverages', 'Juices'],
    'pasta':       ['Dry Foods', 'Pasta'],
    'tomato':      ['Vegetables', 'Canned Goods'],
    'shampoo':     ['Personal Care', 'Hair Care'],
    'toothpaste':  ['Personal Care', 'Dental'],
    'tissue':      ['Household', 'Paper Products'],
    'detergent':   ['Household', 'Cleaning'],
}


@dataclass
class MatchResult:
    """
    A single product match result returned by ProductMatchingService.

    score       : 0.0–1.0 match confidence (1.0 = perfect)
    match_type  : 'fuzzy' | 'category' | 'exact'
    retailers   : list of retailer names that carry this product
    best_price  : lowest current_price across all active deals
    old_price   : corresponding old_price (if discounted)
    discount_pct: percentage off, or None
    """
    product_id:   int
    product_name: str
    score:        float
    match_type:   str
    master_category: Optional[str] = None
    retailers:    list = field(default_factory=list)
    best_price:   Optional[float] = None
    old_price:    Optional[float] = None
    discount_pct: Optional[int]  = None
    image_url:    Optional[str]  = None
    product_url:  Optional[str]  = None

    def to_dict(self) -> dict:
        return {
            'product_id':    self.product_id,
            'product_name':  self.product_name,
            'score':         round(self.score, 3),
            'match_type':    self.match_type,
            'master_category': self.master_category,
            'retailers':     self.retailers,
            'best_price':    self.best_price,
            'old_price':     self.old_price,
            'discount_pct':  self.discount_pct,
            'image_url':     self.image_url,
            'product_url':   self.product_url,
        }


class ProductMatchingService:
    """
    Two-layer product matching service.

    Instantiate once and reuse — the product name cache is built on
    first call and held for the lifetime of the instance.
    In production, use a module-level singleton or cache it in Redis.
    """

    def __init__(self):
        self._name_cache: list[tuple[int, str]] = []   # [(product_id, name), ...]
        self._cache_built = False

    # ── Public API ───────────────────────────────────────────────────── #

    def search(self, query: str, limit: int = DEFAULT_LIMIT) -> list[MatchResult]:
        """
        Returns up to `limit` MatchResult objects for an autocomplete query.
        Combines fuzzy + category results, deduplicates, and sorts by score desc.

        Called on every keystroke (after a 300ms debounce on the frontend).
        Typical response time: 20–80ms for 10k products.
        """
        if not query or not query.strip():
            return []

        query = query.strip()

        # Layer 1: fuzzy name matching
        fuzzy_results = self._fuzzy_search(query, limit=limit * 2)

        # Layer 2: category fallback
        cat_results = self._category_search(query, limit=limit * 2)

        # Layer 3: direct icontains fallback — guaranteed to find products when
        # fuzzy/category return nothing (e.g. empty cache, no category mappings)
        db_results = []
        if len(fuzzy_results) + len(cat_results) < limit:
            db_results = self._name_search(query, limit=limit * 2)

        # Merge + deduplicate (fuzzy wins over category or db for same product)
        merged = self._merge(self._merge(fuzzy_results, cat_results), db_results)

        # Enrich with retailer + pricing data
        enriched = self._enrich(merged)

        return enriched[:limit]

    def resolve(self, query: str) -> Optional[MatchResult]:
        """
        Returns the single best match for a confirmed search query.
        Used when the user selects a suggestion or hits Enter.
        Returns None if nothing matches above the threshold.
        """
        results = self.search(query, limit=1)
        return results[0] if results else None

    # ── Layer 1: Fuzzy matching ──────────────────────────────────────── #

    def _build_cache(self):
        """
        Load all product names into memory for fast fuzzy matching.
        10k products = ~1MB of strings. Acceptable for a single VPS.

        If the product table grows beyond ~100k rows, switch to:
          - PostgreSQL trigram index (pg_trgm extension)
          - Query: Product.objects.filter(name__trigram_similar=query)
        """
        from core.models import Product
        self._name_cache = list(
            Product.objects.values_list('id', 'name')
        )
        self._cache_built = True
        logger.debug('[Matching] Cache built: %d products', len(self._name_cache))

    def _fuzzy_search(self, query: str, limit: int) -> list[MatchResult]:
        try:
            from rapidfuzz import process, fuzz
        except ImportError:
            logger.error(
                '[Matching] rapidfuzz not installed — run: pip install rapidfuzz'
            )
            return []

        if not self._cache_built:
            self._build_cache()

        if not self._name_cache:
            return []

        # token_set_ratio handles word reordering and partial matches well
        # e.g. "fresh milk" matches "Brookside Fresh Whole Milk 1L"
        names = [name for _, name in self._name_cache]
        id_map = {name: pid for pid, name in self._name_cache}

        hits = process.extract(
            query,
            names,
            scorer=fuzz.token_set_ratio,
            limit=limit,
            score_cutoff=FUZZY_THRESHOLD,
        )

        results = []
        for matched_name, score, _ in hits:
            pid = id_map.get(matched_name)
            if pid:
                results.append(MatchResult(
                    product_id=pid,
                    product_name=matched_name,
                    score=round(score / 100, 3),
                    match_type='fuzzy' if score < 100 else 'exact',
                ))

        return results

    # ── Layer 2: Category fallback ───────────────────────────────────── #

    def _category_search(self, query: str, limit: int) -> list[MatchResult]:
        """
        If the query contains a known category keyword, fetch all products
        in that master category (and its children) and return them.

        This handles:
          "milk"        → all Dairy products
          "cooking oil" → all Cooking Oils products
          "diapers"     → all Baby Care / Nappies products
        """
        from core.models import Category, Product

        query_lower = query.lower()
        target_category_names: list[str] = []

        for keyword, categories in CATEGORY_KEYWORDS.items():
            if keyword in query_lower:
                target_category_names.extend(categories)

        if not target_category_names:
            return []

        # Find matching master categories
        categories = Category.objects.filter(
            name__in=target_category_names,
            parent__isnull=True,   # top-level only; children fetched below
        )

        if not categories.exists():
            # Try partial match if exact names not found
            categories = Category.objects.filter(
                name__icontains=target_category_names[0]
            )

        if not categories.exists():
            return []

        # Collect category IDs including all children (one level deep)
        category_ids = list(categories.values_list('id', flat=True))
        child_ids = list(
            Category.objects
            .filter(parent_id__in=category_ids)
            .values_list('id', flat=True)
        )
        all_category_ids = category_ids + child_ids

        products = (
            Product.objects
            .filter(master_category_id__in=all_category_ids)
            .select_related('master_category')
            [:limit]
        )

        results = []
        for p in products:
            results.append(MatchResult(
                product_id=p.id,
                product_name=p.name,
                score=0.70,   # fixed score for category matches
                match_type='category',
                master_category=p.master_category.name if p.master_category else None,
                image_url=p.image_url or None,
                product_url=p.url or None,
            ))

        return results

    # ── Layer 3: Direct DB name search ──────────────────────────────── #

    def _name_search(self, query: str, limit: int) -> list[MatchResult]:
        """
        Direct icontains DB query — runs when fuzzy + category together return
        fewer results than needed. Ensures products are always findable even
        when the in-memory cache is empty or categories aren't mapped.
        """
        from core.models import Product
        products = (
            Product.objects
            .filter(name__icontains=query)
            .select_related('master_category')
            [:limit]
        )
        return [
            MatchResult(
                product_id=p.id,
                product_name=p.name,
                score=0.60,
                match_type='fuzzy',
                master_category=p.master_category.name if p.master_category else None,
                image_url=p.image_url or None,
                product_url=p.url or None,
            )
            for p in products
        ]

    # ── Merge + dedup ────────────────────────────────────────────────── #

    def _merge(
        self,
        fuzzy: list[MatchResult],
        category: list[MatchResult],
    ) -> list[MatchResult]:
        """
        Merge two result lists. If the same product appears in both,
        the fuzzy match wins (higher score). Sorted by score desc.
        """
        seen: dict[int, MatchResult] = {}

        for r in fuzzy:
            seen[r.product_id] = r

        for r in category:
            if r.product_id not in seen:
                seen[r.product_id] = r
            # else: fuzzy match already there, keep it

        return sorted(seen.values(), key=lambda r: r.score, reverse=True)

    # ── Enrich with pricing + retailer data ──────────────────────────── #

    def _enrich(self, results: list[MatchResult]) -> list[MatchResult]:
        """
        For each matched product, attach:
          - Best current deal price (lowest current_price across all deals)
          - Corresponding old_price and discount_pct
          - List of retailer names that carry the product
          - image_url and product_url from core.Product

        Batches into a single DB query for all products at once.
        """
        if not results:
            return results

        from core.models import Product, Deal

        product_ids = [r.product_id for r in results]

        # Fetch products with their deals in one query
        products = {
            p.id: p
            for p in Product.objects
            .filter(id__in=product_ids)
            .select_related('retailer', 'master_category')
        }

        # Best deal per product: lowest current_price
        deals = (
            Deal.objects
            .filter(product_id__in=product_ids)
            .select_related('retailer', 'branch')
            .order_by('product_id', 'current_price')
        )

        # Build: product_id → [deals]
        deals_by_product: dict[int, list] = {}
        for d in deals:
            deals_by_product.setdefault(d.product_id, []).append(d)

        for result in results:
            product = products.get(result.product_id)
            if not product:
                continue

            result.image_url = product.image_url or None
            result.product_url = product.url or None
            if product.master_category:
                result.master_category = product.master_category.name

            product_deals = deals_by_product.get(result.product_id, [])
            if product_deals:
                # Best = lowest current_price
                best = product_deals[0]
                result.best_price = float(best.current_price)
                result.old_price  = float(best.old_price) if best.old_price else None
                if result.old_price and result.old_price > result.best_price:
                    result.discount_pct = int(
                        (result.old_price - result.best_price)
                        / result.old_price * 100
                    )

            # Unique retailer names across all deals for this product
            result.retailers = list({
                d.retailer.name for d in product_deals if d.retailer
            })

        return results

    # ── Cache invalidation ───────────────────────────────────────────── #

    def invalidate_cache(self):
        """
        Call this after a bulk scraper run completes to force a cache rebuild
        on the next search request. Hook into BaseScraper.run() post-success.
        """
        self._cache_built = False
        self._name_cache = []
        logger.debug('[Matching] Name cache invalidated')


# Module-level singleton — import this in views and serializers
matching_service = ProductMatchingService()
