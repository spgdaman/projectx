from django.db import models
from django.conf import settings

class Category(models.Model):
    """
    Master category hierarchy — what YOU define.
    """
    name = models.CharField(max_length=255, unique=False)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ('name', 'parent')
        verbose_name_plural = "Categories"

    def __str__(self):
        if self.parent:
            return f"{self.parent} > {self.name}"
        return self.name


class Retailer(models.Model):
    """
    A retailer (Jumia, Naivas, Carrefour, etc.)
    """
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name

class RetailerBranch(models.Model):
    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)

    class Meta:
        unique_together = ('retailer', 'name')
        verbose_name_plural = "Retailer Branches"

    def __str__(self):
        return f"{self.retailer.name} - {self.name}"

class RetailerCategory(models.Model):
    """
    Raw categories scraped from different retailers.
    """
    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ('retailer', 'name')
        verbose_name_plural = "Retailer Categories"

    def __str__(self):
        return f"{self.retailer.name}: {self.name}"


class CategoryMapping(models.Model):
    """
    Mapping of RetailerCategory → Master Category.
    """
    retailer_category = models.OneToOneField(
        RetailerCategory,
        on_delete=models.CASCADE,
        related_name="mapping"
    )
    master_category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f"{self.retailer_category} → {self.master_category}"


class Product(models.Model):
    """
    Products scraped from retailers.
    Pull the category from the CategoryMapping model.
    """
    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE)
    retailer_category = models.ForeignKey(
        RetailerCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    sku = models.CharField(max_length=200, null=True, blank=True)
    url = models.URLField(null=True, blank=True)

    master_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name

    def assign_master_category(self):
        if self.retailer_category and hasattr(self.retailer_category, "mapping"):
            self.master_category = self.retailer_category.mapping.master_category
            self.save()


class Deal(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE)

    current_price = models.DecimalField(max_digits=12, decimal_places=2)
    old_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    link = models.URLField(null=True, blank=True)
    scraped_at = models.DateTimeField(auto_now_add=True)


class StagingProduct(models.Model):
    """
    Temporary staging table for raw CSV ingestion from multiple sources.
    """
    retailer_name = models.CharField(max_length=200)
    branch_name = models.CharField(max_length=200, null=True, blank=True)
    category_name = models.CharField(max_length=255, null=True, blank=True)
    sub_category_name = models.CharField(max_length=255, null=True, blank=True)
    sub_category_2_name = models.CharField(max_length=255, null=True, blank=True)

    product_name = models.CharField(max_length=255)
    product_url = models.URLField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    old_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    change_count_7 = models.IntegerField(null=True, blank=True)
    avg_pct_change_7 = models.FloatField(null=True, blank=True)
    last_change_date_7 = models.DateField(null=True, blank=True)

    is_manual = models.BooleanField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.retailer_name} | {self.product_name}"
    
class Subscription(models.Model):
    TARGET_CHOICES = (
        ("product", "Product"),
        ("category", "Category"),
        ("retailer", "Retailer"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    target_type = models.CharField(max_length=20, choices=TARGET_CHOICES)

    product = models.ForeignKey("Product", null=True, blank=True, on_delete=models.CASCADE)
    category = models.ForeignKey("Category", null=True, blank=True, on_delete=models.CASCADE)
    retailer = models.ForeignKey("Retailer", null=True, blank=True, on_delete=models.CASCADE)

    is_paid = models.BooleanField(default=False)
    is_free_tier = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Enforce target rules centrally
        if self.target_type == "product" and self.product:
            self.category = self.product.master_category
            self.retailer = None

        elif self.target_type == "category":
            self.product = None
            self.retailer = None

        elif self.target_type == "retailer":
            self.product = None
            self.category = None

        super().save(*args, **kwargs)

class AlertLog(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    deal = models.ForeignKey("Deal", on_delete=models.CASCADE)
    sent_at = models.DateTimeField(auto_now_add=True)
