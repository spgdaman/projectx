"""
shopping_list/services/optimiser.py
-------------------------------------
Two services:

  BranchResolverService
    Given a user and optional GPS coords, returns branches ranked by:
      1. User's saved preferences (UserBranchPreference, ordered by priority)
      2. Proximity (haversine from user lat/lng or home_lat/home_lng)
      3. All remaining active branches alphabetically

  BasketOptimiserService
    Given a ShoppingList, runs one of three modes:
      single  → find the one branch where total basket cost is lowest
      split   → assign each item to the cheapest available branch
      budget  → greedy fill: highest savings% items first until budget hit

    Saves the result to ListOptimisationResult and updates
    each ShoppingListItem with the resolved deal + branch.
"""

import logging
import math
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


# ── BranchResolverService ──────────────────────────────────────────────────── #

class BranchResolverService:
    """
    Returns an ordered list of RetailerBranch objects for a given user,
    split into two groups: preferred (saved) and nearby (sorted by distance).

    Usage:
      service = BranchResolverService(user)
      preferred, nearby = service.resolve(lat=None, lng=None)
    """

    def __init__(self, user):
        self.user = user

    def resolve(
        self,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        retailer_ids: Optional[list] = None,
    ) -> tuple[list, list]:
        """
        Returns (preferred_branches, nearby_branches).

        preferred_branches : RetailerBranch objects the user has saved,
                             ordered by UserBranchPreference.priority
        nearby_branches    : all remaining active branches, sorted by
                             distance from (lat, lng) if provided,
                             or from the user's saved home_lat/home_lng,
                             or alphabetically if no location available

        retailer_ids       : optional filter — if provided, only return
                             branches belonging to these Retailer IDs
        """
        from core.models import RetailerBranch
        from shopping_list.models import UserBranchPreference

        # Saved preferences for this user
        prefs = (
            UserBranchPreference.objects
            .filter(user=self.user)
            .select_related('branch__retailer')
            .order_by('priority')
        )

        if retailer_ids:
            prefs = prefs.filter(branch__retailer_id__in=retailer_ids)

        preferred_branch_ids = [p.branch_id for p in prefs]
        preferred_branches   = [p.branch for p in prefs]

        # Resolve location — GPS coords take priority over saved home location
        user_lat, user_lng = self._resolve_location(lat, lng, prefs)

        # All other active branches not in preferred set
        remaining_qs = RetailerBranch.objects.filter(
            is_active=True
        ).exclude(
            id__in=preferred_branch_ids
        ).select_related('retailer')

        if retailer_ids:
            remaining_qs = remaining_qs.filter(retailer_id__in=retailer_ids)

        remaining = list(remaining_qs)

        # Sort remaining by distance if we have a location
        if user_lat and user_lng:
            remaining.sort(
                key=lambda b: self._haversine(
                    user_lat, user_lng,
                    float(getattr(b, 'branch_lat', None) or 0),
                    float(getattr(b, 'branch_lng', None) or 0),
                )
            )
        else:
            remaining.sort(key=lambda b: b.name)

        return preferred_branches, remaining

    def _resolve_location(
        self,
        lat: Optional[float],
        lng: Optional[float],
        prefs,
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Priority: GPS coords passed in → saved home_lat/home_lng → None
        """
        if lat and lng:
            return lat, lng

        # Use home location from first saved preference that has one
        for pref in prefs:
            if pref.home_lat and pref.home_lng:
                return float(pref.home_lat), float(pref.home_lng)

        return None, None

    @staticmethod
    def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        if not lat2 and not lng2:
            return float('inf')
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlng / 2) ** 2
        )
        return R * 2 * math.asin(math.sqrt(a))


# ── BasketOptimiserService ─────────────────────────────────────────────────── #

class BasketOptimiserService:
    """
    Computes the best deal plan for a ShoppingList.

    Usage:
      service = BasketOptimiserService(shopping_list)
      result  = service.optimise()
      # result is a ListOptimisationResult instance, saved to DB
    """

    # Minimum KES saving for a split basket to be recommended over single store.
    # If split saves less than this, collapse back to single store.
    MIN_SPLIT_SAVING = Decimal('100.00')

    def __init__(self, shopping_list):
        self.list = shopping_list

    def optimise(self):
        """
        Entry point. Dispatches to the correct mode and saves the result.
        Returns the ListOptimisationResult instance.
        """
        mode = self.list.mode

        if mode == 'single':
            plan = self._optimise_single()
        elif mode == 'split':
            plan = self._optimise_split()
        elif mode == 'budget':
            plan = self._optimise_budget()
        else:
            raise ValueError(f'Unknown mode: {mode}')

        return self._save_result(plan, mode)

    # ── Mode: single store ───────────────────────────────────────────── #

    def _optimise_single(self) -> dict:
        """
        For each preferred branch (and each branchless retailer), compute what
        the full basket would cost. Return the option with the lowest total.
        """
        items = self._get_matched_items()
        if not items:
            return self._empty_plan()

        preferred_branches    = self._get_preferred_branches()
        branchless_retailers  = self._get_branchless_retailers()

        if not preferred_branches and not branchless_retailers:
            return self._empty_plan()

        best_source = None   # branch object OR retailer object
        best_total  = None
        best_deals  = {}
        best_is_branchless = False

        for branch in preferred_branches:
            total, deals = self._basket_total_at_branch(items, branch)
            if best_total is None or total < best_total:
                best_total         = total
                best_source        = branch
                best_deals         = deals
                best_is_branchless = False

        for retailer in branchless_retailers:
            total, deals = self._basket_total_for_retailer(items, retailer)
            if best_total is None or total < best_total:
                best_total         = total
                best_source        = retailer
                best_deals         = deals
                best_is_branchless = True

        if best_source is None:
            return self._empty_plan()

        if best_is_branchless:
            assignment = {item.id: (None, best_deals.get(item.id)) for item in items}
        else:
            assignment = {item.id: (best_source, best_deals.get(item.id)) for item in items}

        return self._build_plan(items=items, assignment=assignment)

    # ── Mode: split basket ───────────────────────────────────────────── #

    def _optimise_split(self) -> dict:
        """
        For each item, find the cheapest deal across all preferred branches
        and branchless retailers. Falls back to single-store if the saving
        from splitting doesn't exceed MIN_SPLIT_SAVING.
        """
        items = self._get_matched_items()
        if not items:
            return self._empty_plan()

        preferred_branches   = self._get_preferred_branches()
        branchless_retailers = self._get_branchless_retailers()

        if not preferred_branches and not branchless_retailers:
            return self._empty_plan()

        # Best deal per item across all sources
        assignment = {}
        for item in items:
            best_deal   = None
            best_branch = None   # None = branchless retailer won
            best_price  = None

            for branch in preferred_branches:
                deal = self._best_deal_at_branch(item, branch)
                if deal is None:
                    continue
                price = deal.current_price
                if best_price is None or price < best_price:
                    best_price  = price
                    best_deal   = deal
                    best_branch = branch

            for retailer in branchless_retailers:
                deal = self._best_deal_for_retailer(item, retailer)
                if deal is None:
                    continue
                price = deal.current_price
                if best_price is None or price < best_price:
                    best_price  = price
                    best_deal   = deal
                    best_branch = None  # no specific branch

            assignment[item.id] = (best_branch, best_deal)

        # Check if split is worth it vs single store
        split_total  = self._assignment_total(assignment)
        single_plan  = self._optimise_single()
        single_total = Decimal(str(single_plan.get('grand_total') or 0))

        if single_total and (single_total - split_total) < self.MIN_SPLIT_SAVING:
            # Not worth the extra trip — return single store plan instead
            logger.debug(
                '[Optimiser] Split saves KES %s — below threshold, using single store',
                single_total - split_total,
            )
            return single_plan

        return self._build_plan(items=items, assignment=assignment)

    # ── Mode: budget fit ─────────────────────────────────────────────── #

    def _optimise_budget(self) -> dict:
        """
        Greedy: sort items by discount % descending, fill basket until
        budget is exhausted. Items that don't fit are marked unmatched.
        """
        items = self._get_matched_items()
        if not items:
            return self._empty_plan()

        budget = self.list.budget or Decimal('0')
        if budget <= 0:
            return self._empty_plan()

        preferred_branches   = self._get_preferred_branches()
        branchless_retailers = self._get_branchless_retailers()

        # Find best deal + source for each item first
        candidates = []
        for item in items:
            best_deal   = None
            best_branch = None
            best_price  = None
            discount    = Decimal('0')

            for branch in preferred_branches:
                deal = self._best_deal_at_branch(item, branch)
                if deal is None:
                    continue
                price = deal.current_price * item.qty
                if best_price is None or price < best_price:
                    best_price  = price
                    best_deal   = deal
                    best_branch = branch
                    if deal.old_price and deal.old_price > deal.current_price:
                        discount = (deal.old_price - deal.current_price) / deal.old_price

            for retailer in branchless_retailers:
                deal = self._best_deal_for_retailer(item, retailer)
                if deal is None:
                    continue
                price = deal.current_price * item.qty
                if best_price is None or price < best_price:
                    best_price  = price
                    best_deal   = deal
                    best_branch = None
                    if deal.old_price and deal.old_price > deal.current_price:
                        discount = (deal.old_price - deal.current_price) / deal.old_price

            candidates.append({
                'item':       item,
                'deal':       best_deal,
                'branch':     best_branch,
                'price':      best_price or Decimal('0'),
                'discount':   discount,
            })

        # Sort by discount % desc — biggest savings first
        candidates.sort(key=lambda c: c['discount'], reverse=True)

        spent      = Decimal('0')
        assignment = {}
        unmatched  = []

        for c in candidates:
            if c['deal'] is None:
                unmatched.append(c['item'].raw_query)
                assignment[c['item'].id] = (None, None)
                continue

            line_total = c['price']
            if spent + line_total <= budget:
                assignment[c['item'].id] = (c['branch'], c['deal'])
                spent += line_total
            else:
                unmatched.append(c['item'].raw_query)
                assignment[c['item'].id] = (None, None)

        return self._build_plan(
            items=items,
            assignment=assignment,
            extra_unmatched=unmatched,
        )

    # ── Helpers ──────────────────────────────────────────────────────── #

    def _get_matched_items(self) -> list:
        return list(
            self.list.items
            .filter(is_matched=True)
            .select_related('product', 'product__retailer')
        )

    def _get_preferred_branches(self) -> list:
        from core.models import RetailerBranch
        from shopping_list.models import UserBranchPreference
        prefs = (
            UserBranchPreference.objects
            .filter(user=self.list.user)
            .select_related('branch__retailer')
            .order_by('priority')
        )
        preferred = [p.branch for p in prefs]
        if preferred:
            return preferred
        # No saved preferences — use all active branches so the optimiser
        # still works for users who haven't selected specific branches
        return list(
            RetailerBranch.objects
            .filter(is_active=True)
            .select_related('retailer')
        )

    def _get_branchless_retailers(self) -> list:
        """
        Returns Retailer objects that have NO entries in RetailerBranch.
        These retailers can never be 'selected' by branch — they're always
        included in the optimiser as retailer-wide deal sources.
        """
        from core.models import Retailer, RetailerBranch
        branched_ids = set(
            RetailerBranch.objects.values_list('retailer_id', flat=True)
        )
        return list(Retailer.objects.exclude(id__in=branched_ids))

    def _best_deal_for_retailer(self, item, retailer):
        """
        Best deal for a retailer that has no branches.
        Fetches any deal for that retailer (branch-specific or retailer-wide).
        """
        from core.models import Deal
        return (
            Deal.objects
            .filter(product=item.product, retailer=retailer)
            .select_related('retailer')
            .order_by('current_price')
            .first()
        )

    def _basket_total_for_retailer(self, items, retailer) -> tuple:
        """Returns (total_Decimal, {item_id: deal}) for a branchless retailer."""
        total = Decimal('0')
        deals = {}
        for item in items:
            deal = self._best_deal_for_retailer(item, retailer)
            if deal:
                total += deal.current_price * item.qty
                deals[item.id] = deal
        return total, deals

    def _best_deal_at_branch(self, item, branch):
        """
        Returns the cheapest Deal for item.product at this branch.
        Includes branch-specific deals AND retailer-wide deals (branch=NULL).
        """
        from core.models import Deal

        return (
            Deal.objects
            .filter(product=item.product, retailer=branch.retailer)
            .filter(models_Q(branch=branch) | models_Q(branch__isnull=True))
            .select_related('retailer')
            .order_by('current_price')
            .first()
        )

    def _basket_total_at_branch(self, items, branch) -> tuple:
        """Returns (total_Decimal, {item_id: deal}) for a branch."""
        total = Decimal('0')
        deals = {}
        for item in items:
            deal = self._best_deal_at_branch(item, branch)
            if deal:
                total += deal.current_price * item.qty
                deals[item.id] = deal
        return total, deals

    def _assignment_total(self, assignment: dict) -> Decimal:
        from shopping_list.models import ShoppingListItem
        total = Decimal('0')
        for item_id, (branch, deal) in assignment.items():
            if deal:
                try:
                    item = self.list.items.get(id=item_id)
                    total += deal.current_price * item.qty
                except Exception:
                    pass
        return total

    def _build_plan(
        self,
        items: list,
        assignment: dict,
        extra_unmatched: list = None,
    ) -> dict:
        """
        Builds the branch_plan JSON structure stored in ListOptimisationResult.
        Also updates ShoppingListItem.deal and .branch for each item.
        """
        from shopping_list.models import ShoppingListItem

        # Group by branch
        branch_groups: dict = {}
        grand_total  = Decimal('0')
        total_saving = Decimal('0')
        unmatched    = list(extra_unmatched or [])

        for item in items:
            branch, deal = assignment.get(item.id, (None, None))

            # branch=None is valid for branchless retailers; only skip when no deal
            if deal is None:
                if item.raw_query not in unmatched:
                    unmatched.append(item.raw_query)
                ShoppingListItem.objects.filter(id=item.id).update(
                    deal=None, branch=None
                )
                continue

            # Update the item row (branch may legitimately be None)
            ShoppingListItem.objects.filter(id=item.id).update(
                deal=deal, branch=branch
            )

            line_total = deal.current_price * item.qty
            grand_total += line_total

            saving = Decimal('0')
            if deal.old_price and deal.old_price > deal.current_price:
                saving = (deal.old_price - deal.current_price) * item.qty
                total_saving += saving

            # Key by branch id when a branch exists; fall back to retailer id
            # (prefixed to avoid collisions between branch ids and retailer ids)
            if branch is not None:
                group_key = f'b{branch.id}'
                if group_key not in branch_groups:
                    branch_groups[group_key] = {
                        'branch_id':    branch.id,
                        'branch_name':  branch.name,
                        'retailer':     branch.retailer.name,
                        'items':        [],
                        'branch_total': Decimal('0'),
                        'branch_saving': Decimal('0'),
                    }
            else:
                # Branchless retailer — group by retailer
                group_key = f'r{deal.retailer_id}'
                if group_key not in branch_groups:
                    branch_groups[group_key] = {
                        'branch_id':    None,
                        'branch_name':  deal.retailer.name,
                        'retailer':     deal.retailer.name,
                        'items':        [],
                        'branch_total': Decimal('0'),
                        'branch_saving': Decimal('0'),
                    }

            branch_groups[group_key]['items'].append({
                'item_id':      item.id,
                'product_name': item.product.name if item.product else item.raw_query,
                'deal_id':      deal.id,
                'price':        str(deal.current_price),
                'old_price':    str(deal.old_price) if deal.old_price else None,
                'qty':          item.qty,
                'line_total':   str(line_total),
                'saving':       str(saving),
            })
            branch_groups[group_key]['branch_total']  += line_total
            branch_groups[group_key]['branch_saving'] += saving

        # Serialise Decimal → str for JSON storage
        branches_list = []
        for bg in branch_groups.values():
            bg['branch_total']  = str(bg['branch_total'])
            bg['branch_saving'] = str(bg['branch_saving'])
            branches_list.append(bg)

        return {
            'branches':        branches_list,
            'grand_total':     str(grand_total),
            'total_saving':    str(total_saving),
            'unmatched_items': unmatched,
        }

    def _empty_plan(self) -> dict:
        return {
            'branches':        [],
            'grand_total':     '0.00',
            'total_saving':    '0.00',
            'unmatched_items': [
                i.raw_query for i in self.list.items.filter(is_matched=False)
            ],
        }

    def _save_result(self, plan: dict, mode: str):
        from shopping_list.models import ListOptimisationResult
        from decimal import Decimal

        result, _ = ListOptimisationResult.objects.update_or_create(
            list=self.list,
            defaults={
                'mode':        mode,
                'grand_total': Decimal(plan.get('grand_total', '0')),
                'total_saving': Decimal(plan.get('total_saving', '0')),
                'branch_plan': plan,
            },
        )

        # Mark list as optimised
        self.list.status = 'optimised'
        self.list.save(update_fields=['status', 'updated_at'])

        return result


# Fix: Q import needed inside _best_deal_at_branch
from django.db.models import Q as models_Q  # noqa: E402
