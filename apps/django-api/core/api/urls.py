from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView,
    RegisterView,
    MeView,
    CategoryViewSet,
    RetailerViewSet,
    ProductViewSet,
    DealViewSet,
    SubscriptionViewSet,
    PaymentViewSet,
    MpesaWebhookView,
    AdminStatsView,
    AdminUsersViewSet,
    AdminCategoryMappingViewSet,
    AdminScraperRunsView,
    AdminTriggerScraperView,
)

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"retailers", RetailerViewSet, basename="retailer")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"deals", DealViewSet, basename="deal")
router.register(r"subscriptions", SubscriptionViewSet, basename="subscription")
router.register(r"payments", PaymentViewSet, basename="payment")

admin_router = DefaultRouter()
admin_router.register(r"users", AdminUsersViewSet, basename="admin-users")
admin_router.register(r"mappings", AdminCategoryMappingViewSet, basename="admin-mappings")

urlpatterns = [
    # Auth
    path("auth/login/", LoginView.as_view(), name="api-login"),
    path("auth/register/", RegisterView.as_view(), name="api-register"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="api-token-refresh"),
    path("auth/me/", MeView.as_view(), name="api-me"),

    # Webhooks (no JWT, CSRF-exempt)
    path("webhooks/mpesa/", MpesaWebhookView.as_view(), name="api-mpesa-webhook"),

    # Admin (staff only)
    path("admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("admin/scraper-runs/", AdminScraperRunsView.as_view(), name="admin-scraper-runs"),
    path("admin/trigger-scrape/<str:retailer>/", AdminTriggerScraperView.as_view(), name="admin-trigger-scrape"),
    path("admin/", include(admin_router.urls)),

    # Resource router
    path("", include(router.urls)),
]
