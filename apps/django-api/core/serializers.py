import re
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    UserProfile,
    Category,
    Retailer,
    RetailerBranch,
    Product,
    Deal,
    Subscription,
    Payment,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    has_access = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "user",
            "phone_number",
            "payment_status",
            "is_free_tier",
            "is_active",
            "grace_until",
            "has_access",
        ]

    def get_has_access(self, obj):
        return obj.has_access()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "parent"]


class CategoryTreeSerializer(serializers.ModelSerializer):
    """Recursive serializer — used only for tree endpoints (depth-limited by design)."""
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "parent", "children"]

    def get_children(self, obj):
        return CategoryTreeSerializer(obj.children.all(), many=True).data


class RetailerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Retailer
        fields = ["id", "name"]


class RetailerBranchSerializer(serializers.ModelSerializer):
    retailer = RetailerSerializer(read_only=True)

    class Meta:
        model = RetailerBranch
        fields = ["id", "retailer", "name"]


class ProductSerializer(serializers.ModelSerializer):
    retailer = RetailerSerializer(read_only=True)
    master_category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "price", "sku", "url", "retailer", "master_category"]


class DealSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    retailer = RetailerSerializer(read_only=True)
    discount_pct = serializers.SerializerMethodField()

    class Meta:
        model = Deal
        fields = [
            "id",
            "product",
            "retailer",
            "current_price",
            "old_price",
            "link",
            "scraped_at",
            "discount_pct",
        ]

    def get_discount_pct(self, obj):
        if obj.old_price and obj.old_price > 0:
            return round(
                float((obj.old_price - obj.current_price) / obj.old_price * 100), 1
            )
        return None


class SubscriptionSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    retailer = RetailerSerializer(read_only=True)
    is_paid = serializers.BooleanField(read_only=True)
    is_free_tier = serializers.BooleanField(read_only=True)
    is_valid = serializers.SerializerMethodField()

    # Write-only FK fields so clients can set targets by ID
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source="product",
        write_only=True,
        required=False,
        allow_null=True,
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )
    retailer_id = serializers.PrimaryKeyRelatedField(
        queryset=Retailer.objects.all(),
        source="retailer",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Subscription
        fields = [
            "id",
            "target_type",
            "product",
            "category",
            "retailer",
            "product_id",
            "category_id",
            "retailer_id",
            "is_active",
            "is_paid",
            "is_free_tier",
            "is_valid",
            "created_at",
            "last_updated_at",
            "expires_at",
        ]
        read_only_fields = ["created_at", "last_updated_at", "expires_at"]

    def get_is_valid(self, obj):
        return obj.is_valid()

    def validate(self, data):
        target_type = data.get("target_type")
        if target_type == "product" and not data.get("product"):
            raise serializers.ValidationError("product_id is required for product subscriptions.")
        if target_type == "category" and not data.get("category"):
            raise serializers.ValidationError("category_id is required for category subscriptions.")
        if target_type == "retailer" and not data.get("retailer"):
            raise serializers.ValidationError("retailer_id is required for retailer subscriptions.")
        return data


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "amount",
            "currency",
            "provider",
            "status",
            "reference",
            "created_at",
            "completed_at",
            "expires_at",
        ]
        read_only_fields = [
            "reference",
            "status",
            "created_at",
            "completed_at",
            "expires_at",
        ]


class InitiatePaymentSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class RegisterSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(min_length=6, write_only=True, style={"input_type": "password"})
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")

    def validate_phone(self, value):
        import phonenumbers
        value = value.strip()

        # Validate phone number format (default region KE for local numbers)
        try:
            parsed = phonenumbers.parse(value, "KE")
            if not phonenumbers.is_valid_number(parsed):
                raise serializers.ValidationError("Enter a valid phone number (e.g. +254712345678 or 0712345678).")
            # Normalise to E.164 so the uniqueness check matches stored values
            value = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            raise serializers.ValidationError("Enter a valid phone number (e.g. +254712345678 or 0712345678).")

        if UserProfile.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("An account with this phone number already exists.")
        return value
