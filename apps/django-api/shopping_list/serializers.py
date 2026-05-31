"""
shopping_list/serializers.py
------------------------------
DRF serializers for all shopping list endpoints.

Covers:
  - Product search autocomplete (read-only)
  - ShoppingList CRUD
  - ShoppingListItem CRUD + resolution
  - UserBranchPreference save/update
  - Branch nearby list (read-only)
  - ListOptimisationResult (read-only)
"""

from decimal import Decimal
from rest_framework import serializers

from shopping_list.models import (
    ShoppingList,
    ShoppingListItem,
    UserBranchPreference,
    ListOptimisationResult,
)


# ── Product search ─────────────────────────────────────────────────────────── #

class ProductSearchResultSerializer(serializers.Serializer):
    """
    Read-only. Returned by GET /api/products/search/?q=...
    Serialises a MatchResult dataclass from ProductMatchingService.
    """
    product_id    = serializers.IntegerField()
    product_name  = serializers.CharField()
    score         = serializers.FloatField()
    match_type    = serializers.CharField()
    master_category = serializers.CharField(allow_null=True)
    retailers     = serializers.ListField(child=serializers.CharField())
    best_price    = serializers.FloatField(allow_null=True)
    old_price     = serializers.FloatField(allow_null=True)
    discount_pct  = serializers.IntegerField(allow_null=True)
    image_url     = serializers.URLField(allow_null=True)
    product_url   = serializers.URLField(allow_null=True)


# ── Branch nearby ──────────────────────────────────────────────────────────── #

class BranchSerializer(serializers.Serializer):
    """
    Read-only. Returned by GET /api/branches/nearby/
    Includes distance_km if coords were provided.
    """
    id           = serializers.IntegerField(source='branch.id')
    name         = serializers.CharField(source='branch.name')
    retailer     = serializers.CharField(source='branch.retailer.name')
    is_preferred = serializers.BooleanField()
    distance_km  = serializers.FloatField(allow_null=True)


# ── UserBranchPreference ───────────────────────────────────────────────────── #

class UserBranchPreferenceSerializer(serializers.ModelSerializer):
    branch_name   = serializers.CharField(source='branch.name', read_only=True)
    retailer_name = serializers.CharField(source='branch.retailer.name', read_only=True)

    class Meta:
        model  = UserBranchPreference
        fields = [
            'id', 'branch', 'branch_name', 'retailer_name',
            'priority', 'home_lat', 'home_lng',
        ]
        read_only_fields = ['id']

    def validate(self, data):
        # Ensure user doesn't save the same branch twice
        user   = self.context['request'].user
        branch = data.get('branch')
        qs = UserBranchPreference.objects.filter(user=user, branch=branch)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'You have already saved this branch.'
            )
        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


# ── ShoppingListItem ───────────────────────────────────────────────────────── #

class ShoppingListItemSerializer(serializers.ModelSerializer):
    product_name  = serializers.CharField(source='product.name', read_only=True)
    retailer_name = serializers.CharField(
        source='product.retailer.name', read_only=True
    )
    branch_name   = serializers.CharField(source='branch.name', read_only=True)
    best_price    = serializers.SerializerMethodField()
    old_price     = serializers.SerializerMethodField()
    discount_pct  = serializers.SerializerMethodField()
    line_total    = serializers.SerializerMethodField()
    saving        = serializers.SerializerMethodField()

    class Meta:
        model  = ShoppingListItem
        fields = [
            'id', 'raw_query', 'qty', 'position',
            'product', 'product_name', 'retailer_name',
            'deal', 'branch', 'branch_name',
            'is_matched', 'match_score',
            'best_price', 'old_price', 'discount_pct',
            'line_total', 'saving',
        ]
        read_only_fields = [
            'id', 'is_matched', 'match_score',
            'product_name', 'retailer_name', 'branch_name',
            'best_price', 'old_price', 'discount_pct',
            'line_total', 'saving',
        ]

    def get_best_price(self, obj):
        return float(obj.deal.current_price) if obj.deal else None

    def get_old_price(self, obj):
        if obj.deal and obj.deal.old_price:
            return float(obj.deal.old_price)
        return None

    def get_discount_pct(self, obj):
        if obj.deal and obj.deal.old_price and obj.deal.current_price:
            if obj.deal.old_price > obj.deal.current_price:
                return int(
                    (obj.deal.old_price - obj.deal.current_price)
                    / obj.deal.old_price * 100
                )
        return None

    def get_line_total(self, obj):
        return float(obj.line_total) if obj.line_total else None

    def get_saving(self, obj):
        return float(obj.saving) if obj.saving else None


class AddItemSerializer(serializers.Serializer):
    """
    Used by POST /api/shopping-lists/{id}/items/
    Accepts either a raw_query (user typed) or a confirmed product_id.
    """
    raw_query  = serializers.CharField(max_length=500)
    product_id = serializers.IntegerField(required=False, allow_null=True)
    qty        = serializers.IntegerField(min_value=1, default=1)

    def validate_raw_query(self, value):
        return value.strip()


# ── ShoppingList ───────────────────────────────────────────────────────────── #

class ShoppingListSerializer(serializers.ModelSerializer):
    items            = ShoppingListItemSerializer(many=True, read_only=True)
    item_count       = serializers.IntegerField(read_only=True)
    matched_count    = serializers.IntegerField(
        source='matched_item_count', read_only=True
    )

    class Meta:
        model  = ShoppingList
        fields = [
            'id', 'name', 'mode', 'budget', 'status',
            'item_count', 'matched_count',
            'items', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    def validate_budget(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError('Budget must be greater than 0.')
        return value

    def validate(self, data):
        mode   = data.get('mode', getattr(self.instance, 'mode', 'split'))
        budget = data.get('budget', getattr(self.instance, 'budget', None))
        if mode == 'budget' and not budget:
            raise serializers.ValidationError(
                {'budget': 'A budget amount is required when mode is "budget".'}
            )
        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


# ── ListOptimisationResult ─────────────────────────────────────────────────── #

class OptimisationResultSerializer(serializers.ModelSerializer):
    is_stale = serializers.SerializerMethodField()

    class Meta:
        model  = ListOptimisationResult
        fields = [
            'id', 'mode', 'grand_total', 'total_saving',
            'branch_plan', 'computed_at', 'is_stale',
        ]
        read_only_fields = fields

    def get_is_stale(self, obj):
        return obj.is_stale()
