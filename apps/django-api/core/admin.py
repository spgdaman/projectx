from django.contrib import admin
from django.urls import path
from django.template.response import TemplateResponse
from .models import (
    Category, Retailer, RetailerCategory, CategoryMapping, Product, Deal,
    StagingProduct, RetailerBranch, Subscription, UserProfile, Payment,
    ScraperRun, CategorySynonym, CategoryKeywordRule, MappingReviewQueue,
)
from django.utils.html import format_html
from difflib import SequenceMatcher
from django.utils import timezone
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

@admin.register(ScraperRun)
class ScraperRunAdmin(admin.ModelAdmin):
    list_display = (
        'started_at', 'retailer', 'branch', 'strategy',
        'status_badge', 'deals_found', 'deals_changed',
        'products_new', 'products_skipped', 'pages_scraped',
        'http_errors', 'duration_seconds',
    )
    list_filter  = ('retailer', 'strategy', 'status')
    search_fields = ('retailer__name', 'branch__name', 'celery_task_id')
    readonly_fields = (
        'retailer', 'branch', 'strategy', 'status', 'started_at', 'finished_at',
        'deals_found', 'deals_changed', 'products_new', 'products_skipped',
        'pages_scraped', 'http_errors', 'celery_task_id', 'error',
    )
    ordering = ('-started_at',)
    date_hierarchy = 'started_at'

    _STATUS_COLORS = {
        'success': '#16a34a',
        'failed':  '#dc2626',
        'partial': '#d97706',
        'running': '#2563eb',
    }

    def status_badge(self, obj):
        color = self._STATUS_COLORS.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600">{}</span>',
            color, obj.status.upper(),
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class RetailerAdmin(admin.ModelAdmin):
    list_display  = ['id', 'name', 'product_count', 'deal_count', 'last_scraped']
    search_fields = ['name']

    def product_count(self, obj):
        return obj.product_set.count()
    product_count.short_description = 'Products'

    def deal_count(self, obj):
        return obj.deal_set.count()
    deal_count.short_description = 'Deals'

    def last_scraped(self, obj):
        run = ScraperRun.objects.filter(retailer=obj).order_by('-started_at').first()
        return run.started_at if run else '—'
    last_scraped.short_description = 'Last scraped'


admin.site.register(Category, CategoryAdmin)
admin.site.register(Retailer, RetailerAdmin)
admin.site.register(RetailerCategory, RetailerCategoryMappingAdmin)
admin.site.register(CategoryMapping, CategoryMappingAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Deal, DealAdmin)   # ✔ FIXED TYPO
admin.site.register(StagingProduct, StagingProductAdmin)
admin.site.register(RetailerBranch, admin.ModelAdmin)


@admin.register(CategorySynonym)
class CategorySynonymAdmin(admin.ModelAdmin):
    list_display  = ('raw_name', 'level', 'retailer', 'master_category', 'source', 'created_at')
    list_filter   = ('level', 'retailer', 'source')
    search_fields = ('raw_name', 'master_category__name')
    ordering      = ('level', 'raw_name')


@admin.register(CategoryKeywordRule)
class CategoryKeywordRuleAdmin(admin.ModelAdmin):
    list_display  = ('keyword', 'master_category', 'priority', 'match_field', 'is_active')
    list_filter   = ('is_active', 'match_field', 'master_category')
    search_fields = ('keyword',)
    ordering      = ('-priority', 'keyword')


@admin.register(MappingReviewQueue)
class MappingReviewQueueAdmin(admin.ModelAdmin):
    list_display  = (
        'product_name_display', 'retailer', 'all_category_levels',
        'tier_reached', 'fuzzy_suggestion_display', 'resolved', 'created_at',
    )
    list_filter   = ('resolved', 'tier_reached', 'retailer')
    search_fields = ('staging_product__product_name', 'staging_product__category_name')
    readonly_fields = (
        'staging_product', 'retailer', 'tier_reached', 'best_fuzzy_score',
        'best_fuzzy_level', 'created_at', 'all_category_levels_detail',
    )
    actions = ['confirm_fuzzy_suggestion', 'mark_no_mapping']

    def product_name_display(self, obj):
        return obj.staging_product.product_name
    product_name_display.short_description = 'Product'

    def all_category_levels(self, obj):
        sp = obj.staging_product
        parts = [p for p in [sp.category_name, sp.sub_category_name, sp.sub_category_2_name] if p]
        return ' > '.join(parts)
    all_category_levels.short_description = 'Retailer cats'

    def all_category_levels_detail(self, obj):
        return self.all_category_levels(obj)
    all_category_levels_detail.short_description = 'Retailer category path'

    def fuzzy_suggestion_display(self, obj):
        if obj.best_fuzzy_suggestion:
            score = obj.best_fuzzy_score or 0
            return f'{obj.best_fuzzy_suggestion} ({score:.0f}%)'
        return '—'
    fuzzy_suggestion_display.short_description = 'Best fuzzy match'

    @admin.action(description='Confirm fuzzy suggestion as mapping')
    def confirm_fuzzy_suggestion(self, request, queryset):
        from core.models import CategoryMapping, CategorySynonym, Product, RetailerCategory

        confirmed = 0
        for entry in queryset.select_related(
            'staging_product', 'best_fuzzy_suggestion', 'retailer'
        ):
            if not entry.best_fuzzy_suggestion:
                continue

            sp = entry.staging_product
            master = entry.best_fuzzy_suggestion
            level = entry.best_fuzzy_level

            # Record synonym at the matched level
            if level is not None:
                from core.services.category_mapper import CategoryMapper
                level_field_map = {
                    2: sp.sub_category_2_name,
                    1: sp.sub_category_name,
                    0: sp.category_name,
                }
                raw_name = level_field_map.get(level)
                if raw_name:
                    norm = CategoryMapper.normalise(raw_name)
                    CategorySynonym.objects.get_or_create(
                        raw_name=norm,
                        level=level,
                        retailer=entry.retailer,
                        defaults={'master_category': master, 'source': 'human'},
                    )

            # Create CategoryMapping for top-level category if possible
            if sp.category_name and entry.retailer:
                rc, _ = RetailerCategory.objects.get_or_create(
                    retailer=entry.retailer,
                    name=sp.category_name,
                )
                CategoryMapping.objects.get_or_create(
                    retailer_category=rc,
                    defaults={'master_category': master},
                )

            # Update linked Product
            Product.objects.filter(
                retailer=entry.retailer,
                name=sp.product_name,
                master_category__isnull=True,
            ).update(master_category=master)

            # Resolve the queue entry
            entry.resolved = True
            entry.resolved_category = master
            entry.resolved_at = timezone.now()
            entry.save(update_fields=['resolved', 'resolved_category', 'resolved_at'])
            confirmed += 1

        self.message_user(request, f'{confirmed} entries confirmed and resolved.')

    @admin.action(description='Mark as reviewed (no mapping)')
    def mark_no_mapping(self, request, queryset):
        updated = queryset.update(resolved=True, resolved_category=None, resolved_at=timezone.now())
        self.message_user(request, f'{updated} entries marked as reviewed (no mapping).')