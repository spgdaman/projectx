from django.contrib import admin
from django.urls import path
from django.template.response import TemplateResponse
from .models import Category, Retailer, RetailerCategory, CategoryMapping, Product, Deal, StagingProduct, RetailerBranch, Subscription, UserProfile, Payment
from django.utils.html import format_html
from difflib import SequenceMatcher
from core.services.subscriptions import update_product_subscription

class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent")
    search_fields = ("name",)
    list_filter = ("parent",)

class RetailerCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "retailer")
    search_fields = ("name",)
    list_filter = ("retailer",)

class MappingStatusFilter(admin.SimpleListFilter):
    title = "Mapping Status"  # Displayed in the admin filter sidebar
    parameter_name = "mapping_status"

    def lookups(self, request, model_admin):
        return (
            ('mapped', 'Mapped'),
            ('unmapped', 'Unmapped'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'mapped':
            return queryset.filter(mapping__isnull=False)
        if self.value() == 'unmapped':
            return queryset.filter(mapping__isnull=True)
        return queryset
    
class RetailerCategoryMappingAdmin(admin.ModelAdmin):
    list_display = ("name", "retailer", "get_master_category", "mapping_status", "map_remap_link")
    search_fields = ("name", "retailer__name")
    list_filter = ("retailer", MappingStatusFilter)

    change_list_template = "admin/categorymapping_change_list.html"

    def get_master_category(self, obj):
        return obj.mapping.master_category.name if hasattr(obj, "mapping") else "-"
    get_master_category.short_description = "Master Category"

    def mapping_status(self, obj):
        return "Mapped" if hasattr(obj, "mapping") else "Unmapped"
    mapping_status.short_description = "Status"

    # Map / Remap link
    def map_remap_link(self, obj):
        url = f"/admin/core/retailercategory/manual-map/?rcat_id={obj.id}"
        if hasattr(obj, "mapping"):
            return format_html(f'<a href="{url}">Remap</a>')
        else:
            return format_html(f'<a href="{url}">Map Now</a>')
    map_remap_link.short_description = "Action"

    # Manual mapping view
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("manual-map/", self.admin_site.admin_view(self.manual_map_view), name="manual-map"),
        ]
        return custom_urls + urls

    def manual_map_view(self, request):
        rcat_id = request.GET.get("rcat_id")
        if rcat_id:
            unmapped = RetailerCategory.objects.filter(id=rcat_id)
        else:
            unmapped = RetailerCategory.objects.filter(mapping__isnull=True).order_by("retailer__name")

        master_categories = Category.objects.all().order_by("name")

        # Preselect existing mapping for remap
        preselect_mapping = None
        if rcat_id:
            rcat = RetailerCategory.objects.get(id=rcat_id)
            if hasattr(rcat, "mapping"):
                preselect_mapping = rcat.mapping.master_category.id

        # Handle POST
        if request.method == "POST":
            rcat_id = request.POST.get("retailer_category")
            cat_id = request.POST.get("master_category")
            if rcat_id and cat_id:
                rcat = RetailerCategory.objects.get(id=rcat_id)
                cat = Category.objects.get(id=cat_id)
                CategoryMapping.objects.update_or_create(
                    retailer_category=rcat,
                    defaults={"master_category": cat}
                )

        context = dict(
            self.admin_site.each_context(request),
            unmapped_categories=unmapped,
            master_categories=master_categories,
            preselect_mapping=preselect_mapping,
            title="Manual Category Mapping",
        )
        return TemplateResponse(request, "admin/manual_category_map.html", context)

class CategoryMappingAdmin(admin.ModelAdmin):
    list_display = ("retailer_category", "master_category")
    search_fields = ("retailer_category__name", "retailer_category__retailer__name")
    list_filter = ("master_category", "retailer_category__retailer")

    # Add a custom button/link in admin
    change_list_template = "admin/categorymapping_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('manual-map/', self.admin_site.admin_view(self.manual_map_view), name='manual-map'),
        ]
        return custom_urls + urls

    def manual_map_view(self, request):
        unmapped = RetailerCategory.objects.filter(mapping__isnull=True).order_by("retailer__name")
        master_categories = Category.objects.all().order_by("name")

        if request.method == "POST":
            rcat_id = request.POST.get("retailer_category")
            cat_id = request.POST.get("master_category")
            if rcat_id and cat_id:
                rcat = RetailerCategory.objects.get(id=rcat_id)
                cat = Category.objects.get(id=cat_id)
                CategoryMapping.objects.update_or_create(
                    retailer_category=rcat,
                    defaults={"master_category": cat}
                )

        context = dict(
            self.admin_site.each_context(request),
            unmapped_categories=unmapped,
            master_categories=master_categories,
            title="Manual Category Mapping"
        )
        return TemplateResponse(request, "admin/unmapped_categories.html", context)

class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "retailer", "master_category", "price")
    search_fields = ("name", "sku")
    list_filter = ("retailer", "master_category")
    autocomplete_fields = ("retailer_category", "master_category")

class DealAdmin(admin.ModelAdmin):
    list_display = ("product", "retailer", "current_price", "old_price", "scraped_at")

class StagingProductAdmin(admin.ModelAdmin):
    list_display = ("retailer_name", "product_name", "price", "branch_name")
    search_fields = ("retailer_name", "product_name")
    list_filter = ("retailer_name",)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "target_type",
        "product",
        "category",
        "retailer",
        "is_paid",
        "is_free_tier",
        "is_active",
        "created_at",
        "last_updated_at",
        "expires_at",
    )

    list_filter = (
        "target_type",
        # "is_paid",
        # "is_free_tier",
        "is_active",
    )

    search_fields = (
        "user__username",
        "product__name",
        "category__name",
        "retailer__name",
    )

    readonly_fields = ("created_at",)

    def save_model(self, request, obj, form, change):
        if change and obj.target_type == "product":
            if "product" in form.changed_data:
                update_product_subscription(obj, form.cleaned_data["product"])
                return
        super().save_model(request, obj, form, change)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("payment_status", "phone_number", "is_free_tier", "is_active", "user_id")

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "amount",
        "provider",
        "status",
        "created_at",
        "completed_at",
        "expires_at",
    )
    list_filter = ("provider", "status")
    search_fields = ("user__username", "reference")

admin.site.register(Category, CategoryAdmin)
admin.site.register(Retailer, admin.ModelAdmin)
admin.site.register(RetailerCategory, RetailerCategoryMappingAdmin)
admin.site.register(CategoryMapping, CategoryMappingAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Deal, DealAdmin)   # ✔ FIXED TYPO
admin.site.register(StagingProduct, StagingProductAdmin)
admin.site.register(RetailerBranch, admin.ModelAdmin)