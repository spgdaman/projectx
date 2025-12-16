from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
import random
from django.utils import timezone
from datetime import timedelta
from phonenumber_field.modelfields import PhoneNumberField

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # phone_number = models.CharField(max_length=15, unique=True)
    phone_number = PhoneNumberField()
    payment_status = models.BooleanField(default=False)  # Paid subscription
    is_free_tier = models.BooleanField(default=True)     # Free tier
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} profile"

class LoginOTP(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)

    @staticmethod
    def generate_code():
        return str(random.randint(100000, 999999))

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

    # is_paid = models.BooleanField(default=False)
    # is_free_tier = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    
    @property
    def is_paid(self):
        return self.user.userprofile.payment_status

    @property
    def is_free_tier(self):
        return self.user.userprofile.is_free_tier

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

class Payment(models.Model):
    PAYMENT_PROVIDER_CHOICES = (
        ("mpesa", "M-Pesa"),
        ("card", "Card"),
        ("bank", "Bank"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("expired", "Expired"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="KES")

    provider = models.CharField(max_length=20, choices=PAYMENT_PROVIDER_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    reference = models.CharField(max_length=100, unique=True)
    provider_reference = models.CharField(max_length=100, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} | {self.amount} | {self.status}"


