"""
shopping_list/models.py
------------------------
Four new models for the smart shopping list feature.

All FK references use string form ('core.Product' etc.) so this app
can live as a separate Django app alongside core/.

INSTALLATION:
  1. Create a new Django app:  python manage.py startapp shopping_list
  2. Replace shopping_list/models.py with this file
  3. Add 'shopping_list' to INSTALLED_APPS in settings.py
  4. Apply the migration (see migrations/0001_initial.py)
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
import math


# ── 1. ShoppingList ────────────────────────────────────────────────────────── #

class ShoppingList(models.Model):
    """
    A user's named shopping list.

    mode controls how the optimiser picks deals:
      single   → cheapest total at one branch
      split    → best price per item regardless of branch
      budget   → fit as many items as possible within budget (greedy by savings %)
    """
    MODE_CHOICES = [
        ('single', 'Cheapest single store'),
        ('split',  'Best price per item (split basket)'),
        ('budget', 'Budget fit'),
    ]
    STATUS_CHOICES = [
        ('draft',      'Draft'),
        ('optimised',  'Optimised'),
        ('completed',  'Completed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shopping_lists',
    )
    name = models.CharField(
        max_length=200,
        default='My shopping list',
    )
    mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default='split',
    )
    budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Maximum spend in KES — used only when mode=budget',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shopping_list'
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.user.username} — {self.name}'

    @property
    def item_count(self):
        return self.items.count()

    @property
    def matched_item_count(self):
        return self.items.filter(is_matched=True).count()


# ── 2. ShoppingListItem ────────────────────────────────────────────────────── #

class ShoppingListItem(models.Model):
    """
    One line in a shopping list.

    raw_query  → exactly what the user typed ("fresh milk", "uji", "size 3 diapers")
    product    → resolved core.Product after matching (null until matched)
    deal       → best core.Deal found for this product at the user's preferred branches
    branch     → which core.RetailerBranch the deal was found at
    qty        → quantity the user wants
    is_matched → True once product FK is resolved
    match_score→ 0.0–1.0 confidence of the fuzzy/category match (for UI display)
    """
    list = models.ForeignKey(
        ShoppingList,
        on_delete=models.CASCADE,
        related_name='items',
    )
    raw_query = models.CharField(
        max_length=500,
        help_text='Exactly what the user typed into the search box',
    )
    product = models.ForeignKey(
        'core.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shopping_list_items',
    )
    deal = models.ForeignKey(
        'core.Deal',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shopping_list_items',
    )
    branch = models.ForeignKey(
        'core.RetailerBranch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shopping_list_items',
        help_text='Branch where this deal was found',
    )
    qty = models.PositiveIntegerField(default=1)
    is_matched = models.BooleanField(
        default=False,
        help_text='True once product FK has been resolved from raw_query',
    )
    match_score = models.FloatField(
        null=True,
        blank=True,
        help_text='0.0–1.0 — fuzzy/category match confidence shown in the UI',
    )
    position = models.PositiveIntegerField(
        default=0,
        help_text='Display order within the list',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shopping_list_item'
        ordering = ['position', 'created_at']

    def __str__(self):
        matched = self.product.name if self.product else f'"{self.raw_query}" (unmatched)'
        return f'{self.list.name} → {matched} × {self.qty}'

    @property
    def line_total(self):
        """Deal price × qty, or None if no deal resolved yet."""
        if self.deal and self.deal.current_price:
            return self.deal.current_price * self.qty
        return None

    @property
    def saving(self):
        """Saving vs old_price × qty, or None."""
        if self.deal and self.deal.old_price and self.deal.current_price:
            return (self.deal.old_price - self.deal.current_price) * self.qty
        return None


# ── 3. UserBranchPreference ────────────────────────────────────────────────── #

class UserBranchPreference(models.Model):
    """
    Stores a user's saved branch choices and home location.

    priority controls the order branches appear in the selector (lower = first).
    home_lat / home_lng are set once from GPS (mobile) or a typed suburb (web)
    and used to sort unselected nearby branches.

    Only one row per user/branch combination is allowed (unique_together).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='branch_preferences',
    )
    branch = models.ForeignKey(
        'core.RetailerBranch',
        on_delete=models.CASCADE,
        related_name='user_preferences',
    )
    priority = models.PositiveIntegerField(
        default=0,
        help_text='Lower number = shown first in branch selector',
    )
    home_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='User home/work latitude — used to sort nearby branches',
    )
    home_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shopping_user_branch_preference'
        unique_together = ('user', 'branch')
        ordering = ['priority']

    def __str__(self):
        return f'{self.user.username} → {self.branch}'

    def distance_km(self, lat: float, lng: float) -> float:
        """
        Haversine distance in km from (lat, lng) to the branch.
        Returns float('inf') if branch has no coordinates.

        Used by BranchResolverService to sort unselected branches
        by proximity when the user hasn't set a home location.
        Note: core.RetailerBranch does not yet have lat/lng fields.
        Add them to RetailerBranch when you seed branch data:
          branch_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
          branch_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
        """
        try:
            b_lat = float(getattr(self.branch, 'branch_lat', None) or 0)
            b_lng = float(getattr(self.branch, 'branch_lng', None) or 0)
            if not b_lat and not b_lng:
                return float('inf')
            R = 6371
            dlat = math.radians(b_lat - lat)
            dlng = math.radians(b_lng - lng)
            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(math.radians(lat))
                * math.cos(math.radians(b_lat))
                * math.sin(dlng / 2) ** 2
            )
            return R * 2 * math.asin(math.sqrt(a))
        except Exception:
            return float('inf')


# ── 4. ListOptimisationResult ──────────────────────────────────────────────── #

class ListOptimisationResult(models.Model):
    """
    Cached result of running BasketOptimiserService on a ShoppingList.

    branch_plan is a JSON snapshot of the optimisation result:
    {
      "branches": [
        {
          "branch_id": 3,
          "branch_name": "Naivas Westlands",
          "retailer": "Naivas",
          "items": [
            {
              "item_id": 12,
              "product_name": "Fresh whole milk 1L",
              "deal_id": 45,
              "price": "78.00",
              "old_price": "95.00",
              "qty": 2,
              "line_total": "156.00",
              "saving": "34.00"
            }
          ],
          "branch_total": "345.00",
          "branch_saving": "68.00"
        }
      ],
      "grand_total": "1920.00",
      "total_saving": "243.00",
      "unmatched_items": ["hand soap", "vinegar"]
    }

    Re-run the optimiser whenever the list changes (items added/removed,
    user changes preferred branches). The result is cached here so the
    API can return it instantly without re-computing on every request.
    """
    list = models.OneToOneField(
        ShoppingList,
        on_delete=models.CASCADE,
        related_name='optimisation_result',
    )
    mode = models.CharField(
        max_length=20,
        help_text='The mode that was used when this result was computed',
    )
    grand_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    total_saving = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    branch_plan = models.JSONField(
        default=dict,
        help_text='Full optimisation result — see docstring above for shape',
    )
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shopping_list_optimisation_result'

    def __str__(self):
        return (
            f'{self.list.name} — {self.mode} — '
            f'KES {self.grand_total} (saved {self.total_saving})'
        )

    def is_stale(self) -> bool:
        """
        Returns True if the list was updated after this result was computed.
        Callers should re-run the optimiser and refresh when stale.
        """
        return self.list.updated_at > self.computed_at
