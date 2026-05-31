from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    # Versioned REST API — consumed by mobile, web, and n8n
    path("api/v1/", include("core.api.urls")),
    # Shopping list feature
    path("api/", include("shopping_list.urls")),
    # Legacy server-side rendered views (kept intact during migration)
    path("", include("core.urls")),
]
