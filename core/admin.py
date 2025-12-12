from django.contrib import admin
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
    list_filter = ("master_category", "retailer_category__retailer")
    search_fields = ("retailer_category__name",)


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