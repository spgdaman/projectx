"""
shopping_list/urls.py
----------------------
Wire into your main urls.py:

  from django.urls import path, include
  urlpatterns += [
      path('api/', include('shopping_list.urls')),
  ]

All endpoints then become:
  /api/products/search/
  /api/branches/nearby/
  /api/user/branches/
  /api/user/branches/<branch_id>/
  /api/shopping-lists/
  /api/shopping-lists/<list_id>/
  /api/shopping-lists/<list_id>/items/
  /api/shopping-lists/<list_id>/items/<item_id>/
  /api/shopping-lists/<list_id>/optimise/
  /api/shopping-lists/<list_id>/result/
"""

from django.urls import path
from shopping_list import views

urlpatterns = [

    # ── Product search ──────────────────────────────────────────────
    path(
        'products/search/',
        views.product_search,
        name='product-search',
    ),

    # ── Branches ────────────────────────────────────────────────────
    path(
        'branches/nearby/',
        views.branches_nearby,
        name='branches-nearby',
    ),
    path(
        'user/branches/',
        views.UserBranchPreferencesView.as_view(),
        name='user-branches',
    ),
    path(
        'user/branches/<int:branch_id>/',
        views.remove_branch_preference,
        name='user-branch-remove',
    ),

    # ── Shopping lists ───────────────────────────────────────────────
    path(
        'shopping-lists/',
        views.ShoppingListListCreateView.as_view(),
        name='shopping-list-list',
    ),
    path(
        'shopping-lists/<int:pk>/',
        views.ShoppingListDetailView.as_view(),
        name='shopping-list-detail',
    ),

    # ── Items ────────────────────────────────────────────────────────
    path(
        'shopping-lists/<int:list_id>/items/',
        views.ShoppingListItemView.as_view(),
        name='shopping-list-items',
    ),
    path(
        'shopping-lists/<int:list_id>/items/<int:item_id>/',
        views.ShoppingListItemView.as_view(),
        name='shopping-list-item-detail',
    ),

    # ── Optimiser ────────────────────────────────────────────────────
    path(
        'shopping-lists/<int:list_id>/optimise/',
        views.optimise_list,
        name='shopping-list-optimise',
    ),
    path(
        'shopping-lists/<int:list_id>/result/',
        views.get_optimisation_result,
        name='shopping-list-result',
    ),
]
