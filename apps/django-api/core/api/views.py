import json
import logging
import re
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import ExpressionWrapper, F, FloatField, Case, When, Value
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import (
    Category,
    Retailer,
    Product,
    Deal,
    Subscription,
    Payment,
    UserProfile,
)
from core.serializers import (
    CategorySerializer,
    CategoryTreeSerializer,
    RetailerSerializer,
    ProductSerializer,
    DealSerializer,
    SubscriptionSerializer,
    PaymentSerializer,
    UserProfileSerializer,
    LoginSerializer,
    InitiatePaymentSerializer,
    RegisterSerializer,
)
from core.services.subscriptions import can_create_subscription, extend_user_subscription
from core.services.payments import expire_stale_payments, mark_payment_success
from core.integrations.mpesa import stk_push
from core.constants import MONTHLY_SUBSCRIPTION_PRICE

logger = logging.getLogger(__name__)


class LoginView(APIView):
    """Phone + password → JWT access + refresh tokens."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            phone=serializer.validated_data["phone"],
            password=serializer.validated_data["password"],
        )

        if not user:
            return Response(
                {"detail": "Invalid phone number or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )


class RegisterView(APIView):
    """Phone + password → create account → JWT tokens."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        username = re.sub(r"[^\w]", "", d["phone"])[:150]
        if User.objects.filter(username=username).exists():
            username = f"{username}_{get_random_string(6)}"

        try:
            user = User.objects.create_user(
                username=username,
                password=d["password"],
                first_name=d.get("first_name", ""),
                last_name=d.get("last_name", ""),
                email=d.get("email", ""),
            )
            UserProfile.objects.create(user=user, phone_number=d["phone"])
        except Exception as exc:
            # Catch IntegrityError (duplicate phone after normalisation) or
            # ValueError from PhoneNumberField rejecting an invalid number.
            logger.warning("Registration failed for phone %s: %s", d["phone"], exc)
            return Response(
                {"detail": str(exc) or "Registration failed. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh)},
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    """Return the authenticated user's full profile."""

    def get(self, request):
        try:
            profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "Profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(UserProfileSerializer(profile).data)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    search_fields = ["name"]

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """Return top-level categories with nested children."""
        roots = Category.objects.filter(parent=None).order_by("name")
        return Response(CategoryTreeSerializer(roots, many=True).data)


class RetailerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Retailer.objects.all().order_by("name")
    serializer_class = RetailerSerializer
    permission_classes = [permissions.AllowAny]


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.select_related("retailer", "master_category").order_by("name")
    serializer_class = ProductSerializer
    search_fields = ["name"]

    def get_queryset(self):
        qs = super().get_queryset()
        if retailer_id := self.request.query_params.get("retailer"):
            qs = qs.filter(retailer_id=retailer_id)
        if category_id := self.request.query_params.get("category"):
            qs = qs.filter(master_category_id=category_id)
        return qs


class DealViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DealSerializer
    search_fields = ["product__name", "retailer__name"]

    def get_queryset(self):
        qs = (
            Deal.objects
            .select_related("product", "product__master_category", "retailer")
            .annotate(
                discount_pct_db=Case(
                    When(
                        old_price__isnull=False,
                        old_price__gt=0,
                        then=ExpressionWrapper(
                            (F("old_price") - F("current_price")) / F("old_price") * Value(100.0),
                            output_field=FloatField(),
                        ),
                    ),
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            )
            .order_by("-scraped_at")
        )
        params = self.request.query_params
        if retailer_id := params.get("retailer"):
            qs = qs.filter(retailer_id=retailer_id)
        if category_id := params.get("category"):
            qs = qs.filter(product__master_category_id=category_id)
        if search := params.get("search"):
            from django.db.models import Q
            qs = qs.filter(
                Q(product__name__icontains=search) | Q(retailer__name__icontains=search)
            )
        if min_discount := params.get("min_discount"):
            try:
                qs = qs.filter(discount_pct_db__gte=float(min_discount))
            except (ValueError, TypeError):
                pass
        return qs


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer

    def get_queryset(self):
        return (
            Subscription.objects
            .filter(user=self.request.user)
            .select_related("product", "product__master_category", "category", "retailer")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        if not can_create_subscription(self.request.user):
            raise PermissionDenied(
                "Free tier limit reached. Upgrade to create more subscriptions."
            )
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        sub = self.get_object()
        sub.is_active = True
        sub.save(update_fields=["is_active", "last_updated_at"])
        return Response(SubscriptionSerializer(sub).data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        sub = self.get_object()
        sub.is_active = False
        sub.save(update_fields=["is_active", "last_updated_at"])
        return Response(SubscriptionSerializer(sub).data)


class PaymentViewSet(viewsets.GenericViewSet):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).order_by("-created_at")

    @action(detail=False, methods=["post"])
    def initiate(self, request):
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        reference = get_random_string(12)

        payment = Payment.objects.create(
            user=request.user,
            amount=MONTHLY_SUBSCRIPTION_PRICE,
            status="pending",
            provider="mpesa",
            reference=reference,
        )

        call_reference = stk_push(phone_number=phone, amount=payment.amount)
        if call_reference:
            payment.reference = call_reference
            payment.save(update_fields=["reference"])

        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def status(self, request):
        expire_stale_payments()
        payment = (
            Payment.objects
            .filter(user=request.user)
            .order_by("-created_at")
            .first()
        )
        if not payment:
            return Response({"status": "none"})
        return Response({"status": payment.status, "reference": payment.reference})


@method_decorator(csrf_exempt, name="dispatch")
class MpesaWebhookView(APIView):
    """M-Pesa STK push callback — no auth, no CSRF."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, AttributeError):
            return Response({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info("M-Pesa callback: %s", json.dumps(data))

        callback = data.get("Body", {}).get("stkCallback")
        if not callback:
            return Response(
                {"error": "Invalid callback payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result_code = callback.get("ResultCode")
        checkout_id = callback.get("CheckoutRequestID")

        try:
            payment = Payment.objects.get(reference=checkout_id)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        if payment.status == "success":
            return Response({"status": "already processed"})

        if result_code == 0:
            metadata = callback.get("CallbackMetadata", {}).get("Item", [])
            meta = {item["Name"]: item.get("Value") for item in metadata}

            mark_payment_success(payment, provider_reference=meta.get("MpesaReceiptNumber"))
            extend_user_subscription(payment.user)

            profile = payment.user.userprofile
            profile.payment_status = True
            profile.is_free_tier = False
            profile.grace_until = None
            profile.save(update_fields=["payment_status", "is_free_tier", "grace_until"])

            payment.user.subscription_set.update(is_active=True)
        else:
            payment.status = "failed"
            payment.completed_at = timezone.now()
            payment.save(update_fields=["status", "completed_at"])

        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})
