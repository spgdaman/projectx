from django.contrib import admin
from django.urls import path
from django.template.response import TemplateResponse
from .models import Category, Retailer, RetailerCategory, CategoryMapping, Product, Deal, StagingProduct, RetailerBranch


class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent")
    search_fields = ("name",)
    list_filter = ("parent",)


class RetailerCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "retailer")
    search_fields = ("name",)
    list_filter = ("retailer",)


class CategoryMappingAdmin(admin.ModelAdmin):
    list_display = ("retailer_category", "master_category")
    search_fields = ("retailer_category__name", "retailer_category__retailer__name")
    list_filter = ("master_category", "retailer_category__retailer")

    change_list_template = "admin/unmapped_categories.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('manual-map/', self.admin_site.admin_view(self.manual_map_view), name='manual-map'),
        ]
        return custom_urls + urls

    def manual_map_view(self, request):
        unmapped = RetailerCategory.objects.filter(mapping__isnull=True).order_by("retailer__name")
        categories = Category.objects.all().order_by("name")

        if request.method == "POST":
            rcat_id = request.POST.get("retailer_category")
            cat_id = request.POST.get("master_category")
            if rcat_id and cat_id:
                rcat = RetailerCategory.objects.get(id=rcat_id)
                cat = Category.objects.get(id=cat_id)
                CategoryMapping.objects.get_or_create(retailer_category=rcat, defaults={"master_category": cat})

        context = dict(
            self.admin_site.each_context(request),
            unmapped_categories=unmapped,
            master_categories=categories,
            title="Manual Category Mapping",
        )
        return TemplateResponse(request, "admin/manual_category_map.html", context)

class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "retailer", "master_category", "price")
    search_fields = ("name", "sku")
    list_filter = ("retailer", "master_category")
    autocomplete_fields = ("retailer_category", "master_category")


class DealAdmin(admin.ModelAdmin):
    list_display = ("product", "retailer", "current_price", "old_price", "scraped_at")


class StagingProductAdmin(admin.ModelAdmin):
    list_display = ("retailer_name", "product_name", "price", "branch_name")


admin.site.register(Category, CategoryAdmin)
admin.site.register(Retailer, admin.ModelAdmin)
admin.site.register(RetailerCategory, RetailerCategoryAdmin)
admin.site.register(CategoryMapping, CategoryMappingAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Deal, DealAdmin)   # ✔ FIXED TYPO
admin.site.register(StagingProduct, StagingProductAdmin)
admin.site.register(RetailerBranch, admin.ModelAdmin)