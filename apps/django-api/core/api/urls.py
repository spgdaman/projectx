from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from core.views import extension as extension_views
from .views import (
    AlertLogView,
    AlertMarkReadView,
    alert_unread_count,
    mark_all_alerts_read,
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
    AdminMapCategoriesView,
    AdminImportKeywordRulesView,
    AdminUncategorizedProductsView,
    AdminSetProductCategoryView,
    AdminBulkSetProductCategoryView,
    AdminEmailConfigView,
    AdminEmailTestView,
    AdminEmailDigestStatsView,
    AdminSendTestAlertView,
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
    # Alerts
    path("alerts/", AlertLogView.as_view(), name="alert-log"),
    path("alerts/unread-count/", alert_unread_count, name="alert-unread-count"),
    path("alerts/read-all/", mark_all_alerts_read, name="alert-read-all"),
    path("alerts/<int:pk>/read/", AlertMarkReadView.as_view(), name="alert-mark-read"),

    # Auth
    path("auth/login/", LoginView.as_view(), name="api-login"),
    path("auth/register/", RegisterView.as_view(), name="api-register"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="api-token-refresh"),
    path("auth/me/", MeView.as_view(), name="api-me"),

    # Chrome Extension — anonymous, rate-limited
    path("extension/compare/", extension_views.extension_compare, name="extension-compare"),

    # Webhooks (no JWT, CSRF-exempt)
    path("webhooks/mpesa/", MpesaWebhookView.as_view(), name="api-mpesa-webhook"),

    # Admin (staff only)
    path("admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("admin/scraper-runs/", AdminScraperRunsView.as_view(), name="admin-scraper-runs"),
    path("admin/trigger-scrape/<str:retailer>/", AdminTriggerScraperView.as_view(), name="admin-trigger-scrape"),
    path("admin/map-categories/", AdminMapCategoriesView.as_view(), name="admin-map-categories"),
    path("admin/import-keyword-rules/", AdminImportKeywordRulesView.as_view(), name="admin-import-keyword-rules"),
    path("admin/uncategorized-products/", AdminUncategorizedProductsView.as_view(), name="admin-uncategorized-products"),
    path("admin/products/<int:pk>/set-category/", AdminSetProductCategoryView.as_view(), name="admin-set-product-category"),
    path("admin/products/bulk-set-category/", AdminBulkSetProductCategoryView.as_view(), name="admin-bulk-set-product-category"),
    path("admin/users/<int:pk>/send-test-alert/", AdminSendTestAlertView.as_view(), name="admin-send-test-alert"),
    path("admin/email-config/", AdminEmailConfigView.as_view(), name="admin-email-config"),
    path("admin/email-config/test/", AdminEmailTestView.as_view(), name="admin-email-test"),
    path("admin/email-config/digest-stats/", AdminEmailDigestStatsView.as_view(), name="admin-email-digest-stats"),
    path("admin/", include(admin_router.urls)),

    # Resource router
    path("", include(router.urls)),
]
