from django.db import models


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

    # this gets auto-filled once mapping exists
    master_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name

    def assign_master_category(self):
        """
        Call this after saving product or after updating mappings.
        """
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
    retailer_name = models.CharField(max_length=200)
    retailer_category_name = models.CharField(max_length=255)
    product_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    old_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    product_url = models.URLField(null=True, blank=True)
    scraped_at = models.DateTimeField(auto_now_add=True)
