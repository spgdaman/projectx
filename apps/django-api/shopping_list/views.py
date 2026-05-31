"""
shopping_list/views.py
-----------------------
All API views for the shopping list feature.

Endpoints:
  GET    /api/products/search/               → autocomplete
  GET    /api/branches/nearby/               → branches sorted by proximity
  PATCH  /api/user/branches/                 → save preferred branches

  GET    /api/shopping-lists/                → list user's lists
  POST   /api/shopping-lists/                → create a list
  GET    /api/shopping-lists/{id}/           → retrieve a list + items
  PATCH  /api/shopping-lists/{id}/           → update name/mode/budget
  DELETE /api/shopping-lists/{id}/           → delete a list

  POST   /api/shopping-lists/{id}/items/     → add item (triggers matching)
  DELETE /api/shopping-lists/{id}/items/{item_id}/ → remove item
  PATCH  /api/shopping-lists/{id}/items/{item_id}/ → update qty / confirm match

  POST   /api/shopping-lists/{id}/optimise/  → run optimiser, return result
  GET    /api/shopping-lists/{id}/result/    → get cached result

Wire into core urls.py:
  from django.urls import path, include
  urlpatterns += [
      path('api/', include('shopping_list.urls')),
  ]
"""

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from shopping_list.models import (
    ShoppingList,
    ShoppingListItem,
    UserBranchPreference,
    ListOptimisationResult,
)
from shopping_list.serializers import (
    ProductSearchResultSerializer,
    BranchSerializer,
    UserBranchPreferenceSerializer,
    ShoppingListSerializer,
    ShoppingListItemSerializer,
    AddItemSerializer,
    OptimisationResultSerializer,
)
from shopping_list.services.matching import matching_service
from shopping_list.services.optimiser import BranchResolverService, BasketOptimiserService

logger = logging.getLogger(__name__)


# ── Product search autocomplete ────────────────────────────────────────────── #

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_search(request):
    """
    GET /api/products/search/?q=fresh+mil&limit=8

    Returns up to `limit` product suggestions. Called on every keystroke
    after a 300ms debounce. Typical response: < 80ms.
    """
    q     = request.query_params.get('q', '').strip()
    limit = min(int(request.query_params.get('limit', 10)), 20)

    if not q or len(q) < 2:
        return Response([])

    results = matching_service.search(q, limit=limit)
    return Response(
        ProductSearchResultSerializer(results, many=True).data
    )


# ── Branches nearby ────────────────────────────────────────────────────────── #

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def branches_nearby(request):
    """
    GET /api/branches/nearby/?lat=-1.2921&lng=36.8219&retailer_ids=1,2,3

    Returns preferred branches first, then remaining sorted by distance.
    lat/lng are optional — if omitted, uses saved home_lat/home_lng.
    """
    lat  = request.query_params.get('lat')
    lng  = request.query_params.get('lng')
    rids = request.query_params.get('retailer_ids')

    try:
        lat = float(lat) if lat else None
        lng = float(lng) if lng else None
    except ValueError:
        lat, lng = None, None

    retailer_ids = None
    if rids:
        try:
            retailer_ids = [int(x) for x in rids.split(',')]
        except ValueError:
            pass

    resolver = BranchResolverService(request.user)
    preferred, nearby = resolver.resolve(lat=lat, lng=lng, retailer_ids=retailer_ids)

    def _serialise(branch, is_preferred, user_lat, user_lng):
        dist = None
        if user_lat and user_lng:
            dist = BranchResolverService._haversine(
                user_lat, user_lng,
                float(getattr(branch, 'branch_lat', None) or 0),
                float(getattr(branch, 'branch_lng', None) or 0),
            )
            if dist == float('inf'):
                dist = None
            else:
                dist = round(dist, 2)
        return {
            'branch': branch,
            'is_preferred': is_preferred,
            'distance_km': dist,
        }

    data = (
        [_serialise(b, True, lat, lng)  for b in preferred] +
        [_serialise(b, False, lat, lng) for b in nearby]
    )

    return Response(BranchSerializer(data, many=True).data)


# ── User branch preferences ────────────────────────────────────────────────── #

class UserBranchPreferencesView(APIView):
    """
    GET  /api/user/branches/   → list saved branch preferences
    POST /api/user/branches/   → add a branch preference
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prefs = UserBranchPreference.objects.filter(
            user=request.user
        ).select_related('branch__retailer').order_by('priority')
        return Response(
            UserBranchPreferenceSerializer(prefs, many=True).data
        )

    def post(self, request):
        serializer = UserBranchPreferenceSerializer(
            data=request.data,
            context={'request': request},
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_branch_preference(request, branch_id):
    """DELETE /api/user/branches/{branch_id}/"""
    deleted, _ = UserBranchPreference.objects.filter(
        user=request.user,
        branch_id=branch_id,
    ).delete()
    if deleted:
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(
        {'detail': 'Branch preference not found.'},
        status=status.HTTP_404_NOT_FOUND,
    )


# ── ShoppingList CRUD ──────────────────────────────────────────────────────── #

class ShoppingListListCreateView(ListCreateAPIView):
    """
    GET  /api/shopping-lists/   → user's lists, most recently updated first
    POST /api/shopping-lists/   → create a new list
    """
    serializer_class   = ShoppingListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            ShoppingList.objects
            .filter(user=self.request.user)
            .prefetch_related('items__product', 'items__deal', 'items__branch')
            .order_by('-updated_at')
        )


class ShoppingListDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET    /api/shopping-lists/{id}/   → full list + items
    PATCH  /api/shopping-lists/{id}/   → update name/mode/budget
    DELETE /api/shopping-lists/{id}/   → delete list + all items
    """
    serializer_class   = ShoppingListSerializer
    permission_classes = [IsAuthenticated]
    http_method_names  = ['get', 'patch', 'delete']

    def get_queryset(self):
        return ShoppingList.objects.filter(user=self.request.user)


# ── ShoppingListItem ───────────────────────────────────────────────────────── #

class ShoppingListItemView(APIView):
    """
    POST   /api/shopping-lists/{list_id}/items/            → add item
    PATCH  /api/shopping-lists/{list_id}/items/{item_id}/  → update qty or confirm match
    DELETE /api/shopping-lists/{list_id}/items/{item_id}/  → remove item
    """
    permission_classes = [IsAuthenticated]

    def _get_list(self, list_id, user):
        try:
            return ShoppingList.objects.get(id=list_id, user=user)
        except ShoppingList.DoesNotExist:
            return None

    def post(self, request, list_id):
        """
        Add an item. Accepts raw_query and optional product_id.

        If product_id is provided (user selected from autocomplete):
          → resolve immediately, mark is_matched=True

        If only raw_query (user typed and hit enter without selecting):
          → attempt auto-resolve via matching service
          → if match found: mark is_matched=True
          → if not: save with is_matched=False, frontend prompts user to confirm
        """
        shopping_list = self._get_list(list_id, request.user)
        if not shopping_list:
            return Response(
                {'detail': 'List not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AddItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        raw_query  = serializer.validated_data['raw_query']
        product_id = serializer.validated_data.get('product_id')
        qty        = serializer.validated_data['qty']
        position   = shopping_list.items.count()

        product     = None
        is_matched  = False
        match_score = None

        if product_id:
            # User explicitly selected from autocomplete — direct resolve
            from core.models import Product
            try:
                product    = Product.objects.get(id=product_id)
                is_matched = True
                match_score = 1.0
            except Product.DoesNotExist:
                pass

        if not product:
            # Auto-resolve via matching service
            match = matching_service.resolve(raw_query)
            if match and match.score >= 0.75:
                from core.models import Product
                try:
                    product    = Product.objects.get(id=match.product_id)
                    is_matched = True
                    match_score = match.score
                except Product.DoesNotExist:
                    pass

        item = ShoppingListItem.objects.create(
            list=shopping_list,
            raw_query=raw_query,
            product=product,
            qty=qty,
            is_matched=is_matched,
            match_score=match_score,
            position=position,
        )

        # Mark list as draft again (needs re-optimisation)
        shopping_list.status = 'draft'
        shopping_list.save(update_fields=['status', 'updated_at'])

        return Response(
            ShoppingListItemSerializer(item).data,
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request, list_id, item_id):
        """
        Update qty or confirm a product match.

        To update qty:         {"qty": 3}
        To confirm a match:    {"product_id": 42}
        """
        shopping_list = self._get_list(list_id, request.user)
        if not shopping_list:
            return Response({'detail': 'List not found.'}, status=404)

        try:
            item = shopping_list.items.get(id=item_id)
        except ShoppingListItem.DoesNotExist:
            return Response({'detail': 'Item not found.'}, status=404)

        if 'qty' in request.data:
            item.qty = max(1, int(request.data['qty']))

        if 'product_id' in request.data:
            from core.models import Product
            try:
                item.product    = Product.objects.get(id=request.data['product_id'])
                item.is_matched = True
                item.match_score = 1.0
            except Product.DoesNotExist:
                return Response({'detail': 'Product not found.'}, status=404)

        item.save()
        shopping_list.status = 'draft'
        shopping_list.save(update_fields=['status', 'updated_at'])

        return Response(ShoppingListItemSerializer(item).data)

    def delete(self, request, list_id, item_id):
        shopping_list = self._get_list(list_id, request.user)
        if not shopping_list:
            return Response({'detail': 'List not found.'}, status=404)

        deleted, _ = shopping_list.items.filter(id=item_id).delete()
        if deleted:
            shopping_list.status = 'draft'
            shopping_list.save(update_fields=['status', 'updated_at'])
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'detail': 'Item not found.'}, status=404)


# ── Optimiser ─────────────────────────────────────────────────────────────── #

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def optimise_list(request, list_id):
    """
    POST /api/shopping-lists/{id}/optimise/

    Runs the basket optimiser and returns the result.
    Accepts optional body: {"mode": "single"} to override list.mode for this run.
    """
    try:
        shopping_list = ShoppingList.objects.get(id=list_id, user=request.user)
    except ShoppingList.DoesNotExist:
        return Response({'detail': 'List not found.'}, status=404)

    # Allow one-off mode override without changing the list's saved mode
    override_mode = request.data.get('mode')
    if override_mode and override_mode in ('single', 'split', 'budget'):
        shopping_list.mode = override_mode

    if not shopping_list.items.filter(is_matched=True).exists():
        return Response(
            {'detail': 'None of your items were matched to products. '
                       'Try searching and selecting a product from the dropdown instead of typing freely.'},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    if shopping_list.mode == 'budget' and not shopping_list.budget:
        return Response(
            {'detail': 'Set a budget amount before running budget mode.'},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        result = BasketOptimiserService(shopping_list).optimise()
    except Exception as e:
        logger.exception('[Optimiser] Failed for list %s', list_id)
        return Response(
            {'detail': f'Optimisation failed: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(OptimisationResultSerializer(result).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_optimisation_result(request, list_id):
    """GET /api/shopping-lists/{id}/result/"""
    try:
        shopping_list = ShoppingList.objects.get(id=list_id, user=request.user)
        result = shopping_list.optimisation_result
    except ShoppingList.DoesNotExist:
        return Response({'detail': 'List not found.'}, status=404)
    except ListOptimisationResult.DoesNotExist:
        return Response(
            {'detail': 'No optimisation result yet — run /optimise/ first.'},
            status=404,
        )

    return Response(OptimisationResultSerializer(result).data)
