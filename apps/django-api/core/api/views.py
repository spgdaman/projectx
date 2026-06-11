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
from rest_framework import generics, viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import (
    AlertLog,
    Category,
    CategoryMapping,
    Retailer,
    RetailerCategory,
    Product,
    Deal,
    Subscription,
    Payment,
    UserProfile,
)
from core.serializers import (
    AlertLogSerializer,
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
            UserProfile.objects.create(
                user=user,
                phone_number=d["phone"],
                date_of_birth=d.get("date_of_birth"),
            )
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
    """GET/PATCH the authenticated user's profile."""

    def get(self, request):
        try:
            profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "Profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(UserProfileSerializer(profile).data)

    def patch(self, request):
        try:
            profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

        email = request.data.get("email")
        dob = request.data.get("date_of_birth")

        if email is not None:
            request.user.email = email
            request.user.save(update_fields=["email"])

        if dob is not None:
            profile.date_of_birth = dob or None
            profile.save(update_fields=["date_of_birth"])

        return Response(UserProfileSerializer(profile).data)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    search_fields = ["name"]

    def get_queryset(self):
        # The deals filter dropdown only needs top-level categories.
        # Descendants are included automatically when deals are filtered (see DealViewSet).
        # Showing leaf categories in a flat <select> is confusing and under-counts results.
        qs = Category.objects.filter(parent__isnull=True).order_by("name")
        if retailer_id := self.request.query_params.get("retailer"):
            from core.services.alert_resolver import get_category_descendants
            # Include a root if it OR any of its descendants has a product from this retailer
            roots_with_products = set()
            for root in qs:
                desc_ids = get_category_descendants(root)
                if Product.objects.filter(
                    retailer_id=retailer_id,
                    master_category_id__in=desc_ids,
                ).exists():
                    roots_with_products.add(root.id)
            # If no categorized products exist yet for this retailer, fall back to all roots
            # so the dropdown is never empty (data quality issue, not a user-facing error)
            if roots_with_products:
                qs = qs.filter(id__in=roots_with_products)
        return qs

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
            .order_by("-discount_pct_db", "-scraped_at")
        )
        params = self.request.query_params
        if retailer_id := params.get("retailer"):
            qs = qs.filter(retailer_id=retailer_id)
        if category_id := params.get("category"):
            from core.models import Category as Cat
            from core.services.alert_resolver import get_category_descendants
            try:
                cat = Cat.objects.get(pk=category_id)
                cat_ids = get_category_descendants(cat)
            except Cat.DoesNotExist:
                cat_ids = {int(category_id)}
            qs = qs.filter(product__master_category_id__in=cat_ids)
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
        ordering = params.get("ordering")
        if ordering == "newest":
            qs = qs.order_by("-scraped_at")
        elif ordering == "price_asc":
            qs = qs.order_by("current_price", "-discount_pct_db")
        elif ordering == "price_desc":
            qs = qs.order_by("-current_price", "-discount_pct_db")
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


# ── Admin-only views ──────────────────────────────────────────────────────────

class AdminStatsView(APIView):
    """Dashboard stats — staff only."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response({
            "total_users": User.objects.count(),
            "paid_users": UserProfile.objects.filter(payment_status=True).count(),
            "free_users": UserProfile.objects.filter(is_free_tier=True).count(),
            "total_products": Product.objects.count(),
            "total_deals": Deal.objects.count(),
            "active_subscriptions": Subscription.objects.filter(is_active=True).count(),
            "total_retailers": Retailer.objects.count(),
            "unmapped_categories": RetailerCategory.objects.filter(mapping__isnull=True).count(),
            "total_categories": Category.objects.count(),
        })


class AdminUsersViewSet(viewsets.ReadOnlyModelViewSet):
    """Paginated user list — staff only."""
    permission_classes = [permissions.IsAdminUser]
    serializer_class = UserProfileSerializer

    def get_queryset(self):
        qs = UserProfile.objects.select_related("user").order_by("-user__date_joined")
        if q := self.request.query_params.get("search"):
            from django.db.models import Q
            qs = qs.filter(
                Q(user__username__icontains=q) |
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(phone_number__icontains=q)
            )
        if plan := self.request.query_params.get("plan"):
            if plan == "paid":
                qs = qs.filter(payment_status=True)
            elif plan == "free":
                qs = qs.filter(is_free_tier=True)
        return qs

    @action(detail=True, methods=["post"])
    def toggle_admin(self, request, pk=None):
        """Toggle is_staff on the underlying User — cannot demote yourself."""
        profile = self.get_object()
        if profile.user == request.user:
            return Response(
                {"detail": "You cannot change your own admin status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile.user.is_staff = not profile.user.is_staff
        profile.user.save(update_fields=["is_staff"])
        return Response({"is_staff": profile.user.is_staff})

    @action(detail=True, methods=["post"], url_path="set-plan")
    def set_plan(self, request, pk=None):
        """Manually set a user's plan to premium or free — staff only."""
        profile = self.get_object()
        plan = request.data.get("plan")
        if plan not in ("premium", "free"):
            return Response(
                {"detail": "plan must be 'premium' or 'free'"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if plan == "premium":
            profile.payment_status = True
            profile.is_free_tier = False
            profile.grace_until = None
            profile.save(update_fields=["payment_status", "is_free_tier", "grace_until"])
            profile.user.subscription_set.update(is_active=True)
        else:
            profile.payment_status = False
            profile.is_free_tier = True
            profile.save(update_fields=["payment_status", "is_free_tier"])
        return Response({"payment_status": profile.payment_status, "is_free_tier": profile.is_free_tier})


class AdminTriggerScraperView(APIView):
    """Manually queue a scraper task — staff only."""
    permission_classes = [permissions.IsAdminUser]

    _TASKS = {
        'naivas':     'scrapers.tasks.scrape_naivas',
        'quickmart':  'scrapers.tasks.scrape_quickmart_all',
        'chandarana': 'scrapers.tasks.scrape_chandarana',
        'carrefour':  'scrapers.tasks.scrape_carrefour',
        'normalize':  'scrapers.tasks.normalize_staging',
    }

    def post(self, request, retailer):
        key = retailer.lower()
        task_name = self._TASKS.get(key)
        if not task_name:
            return Response(
                {'detail': f'Unknown retailer: {retailer}. Valid: {list(self._TASKS)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from celery import current_app
        result = current_app.send_task(task_name)
        return Response({'task_id': result.id, 'retailer': retailer, 'queued': True})


class AdminMapCategoriesView(APIView):
    """
    Run category mapping on production data — staff only.
    Runs map_categories (staging-based) then categorize_products (keyword-based
    direct pass) so products without staging rows also get categorized.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        from django.core.management import call_command
        from io import StringIO
        retailer = request.data.get('retailer')
        out = StringIO()
        kwargs = {'stdout': out, 'stderr': out}
        if retailer:
            kwargs['retailer'] = retailer
        try:
            call_command('map_categories', **kwargs)
            out.write('\n--- direct keyword pass ---\n')
            call_command('categorize_products', **kwargs)
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'output': out.getvalue()})


class AdminUncategorizedProductsView(APIView):
    """Paginated list of products with no master_category — staff only."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from core.models import Product
        from django.core.paginator import Paginator

        qs = (
            Product.objects
            .filter(master_category__isnull=True)
            .select_related('retailer')
            .order_by('retailer__name', 'name')
        )
        if search := request.query_params.get('search', '').strip():
            qs = qs.filter(name__icontains=search)
        if retailer_id := request.query_params.get('retailer', '').strip():
            qs = qs.filter(retailer_id=retailer_id)

        paginator = Paginator(qs, 50)
        page = paginator.get_page(int(request.query_params.get('page', 1)))
        return Response({
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'results': [
                {
                    'id': p.id,
                    'name': p.name,
                    'image_url': p.image_url,
                    'retailer': {'id': p.retailer_id, 'name': p.retailer.name},
                }
                for p in page
            ],
        })


class AdminSetProductCategoryView(APIView):
    """Set master_category on a single Product — staff only."""
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk):
        from core.models import Category, Product
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        category_id = request.data.get('master_category_id')
        if not category_id:
            return Response({'detail': 'master_category_id required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            category = Category.objects.get(pk=category_id)
        except Category.DoesNotExist:
            return Response({'detail': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
        product.master_category = category
        product.save(update_fields=['master_category'])
        return Response({'id': product.id, 'master_category': {'id': category.id, 'name': category.name}})


class AdminBulkSetProductCategoryView(APIView):
    """
    Map multiple products to a category in one request — staff only.
    Optionally creates a CategoryKeywordRule so future products with
    similar names are auto-categorized.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        from core.models import Category, CategoryKeywordRule, Product

        product_ids = request.data.get('product_ids', [])
        category_id = request.data.get('master_category_id')
        keyword = (request.data.get('keyword') or '').strip().lower()

        if not product_ids or not category_id:
            return Response(
                {'detail': 'product_ids and master_category_id are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            category = Category.objects.get(pk=category_id)
        except Category.DoesNotExist:
            return Response({'detail': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)

        updated = Product.objects.filter(pk__in=product_ids).update(master_category=category)

        rule_created = False
        if keyword:
            _, rule_created = CategoryKeywordRule.objects.get_or_create(
                keyword=keyword,
                master_category=category,
                defaults={
                    'priority': 150,
                    'match_field': 'product_name',
                    'is_active': True,
                },
            )

        return Response({
            'updated': updated,
            'category': {'id': category.id, 'name': category.name},
            'keyword_rule_created': rule_created,
            'keyword': keyword or None,
        })


class AdminImportKeywordRulesView(APIView):
    """
    Bulk-import CategoryKeywordRule records — staff only.
    Accepts a JSON array of rule dicts (Django fixture format or plain dicts).
    Idempotent: existing rules with the same PK are skipped.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        from core.models import Category, CategoryKeywordRule
        rules = request.data if isinstance(request.data, list) else request.data.get('rules', [])
        if not rules:
            return Response({'error': 'POST a JSON array of rule objects'}, status=status.HTTP_400_BAD_REQUEST)

        created = skipped = errors = 0
        for entry in rules:
            fields = entry.get('fields', entry)
            try:
                cat_id = fields['master_category']
                cat = Category.objects.get(pk=cat_id)
                _, was_created = CategoryKeywordRule.objects.get_or_create(
                    keyword=fields['keyword'],
                    master_category=cat,
                    defaults={
                        'priority': fields.get('priority', 100),
                        'match_field': fields.get('match_field', 'product_name'),
                        'is_active': fields.get('is_active', True),
                    },
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1
            except Exception as exc:
                errors += 1
        return Response({'created': created, 'skipped': skipped, 'errors': errors})


class AdminScraperRunsView(APIView):
    """Paginated scraper run history — staff only."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from core.models import ScraperRun
        from django.core.paginator import Paginator

        qs = ScraperRun.objects.select_related('retailer', 'branch').order_by('-started_at')

        if retailer := request.query_params.get('retailer'):
            qs = qs.filter(retailer__name__icontains=retailer)
        if status_filter := request.query_params.get('status'):
            qs = qs.filter(status=status_filter)

        page_num = max(1, int(request.query_params.get('page', 1)))
        paginator = Paginator(qs, 50)
        page = paginator.get_page(page_num)

        return Response({
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'results': [
                {
                    'id':               r.id,
                    'retailer':         r.retailer.name,
                    'branch':           r.branch.name if r.branch else None,
                    'strategy':         r.strategy,
                    'status':           r.status,
                    'deals_found':      r.deals_found,
                    'deals_changed':    r.deals_changed,
                    'products_new':     r.products_new,
                    'products_skipped': r.products_skipped,
                    'pages_scraped':    r.pages_scraped,
                    'http_errors':      r.http_errors,
                    'duration_seconds': r.duration_seconds,
                    'started_at':       r.started_at,
                    'error':            r.error[:400] if r.error else '',
                }
                for r in page
            ],
        })


class AdminCategoryMappingViewSet(viewsets.ModelViewSet):
    """Category mapping CRUD — staff only."""
    permission_classes = [permissions.IsAdminUser]

    def list(self, request):
        """Returns both mapped and unmapped retailer categories."""
        from core.serializers import RetailerSerializer
        unmapped = RetailerCategory.objects.filter(
            mapping__isnull=True
        ).select_related("retailer").order_by("retailer__name", "name")
        mapped = CategoryMapping.objects.select_related(
            "retailer_category", "retailer_category__retailer", "master_category"
        ).order_by("retailer_category__retailer__name", "retailer_category__name")

        return Response({
            "unmapped": [
                {
                    "id": rc.id,
                    "name": rc.name,
                    "retailer": rc.retailer.name,
                }
                for rc in unmapped
            ],
            "mapped": [
                {
                    "id": m.id,
                    "retailer_category_id": m.retailer_category_id,
                    "retailer_category": m.retailer_category.name,
                    "retailer": m.retailer_category.retailer.name,
                    "master_category_id": m.master_category_id,
                    "master_category": m.master_category.name,
                }
                for m in mapped
            ],
        })

    def create(self, request):
        retailer_category_id = request.data.get("retailer_category_id")
        master_category_id = request.data.get("master_category_id")
        if not retailer_category_id or not master_category_id:
            return Response(
                {"detail": "retailer_category_id and master_category_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        mapping, created = CategoryMapping.objects.update_or_create(
            retailer_category_id=retailer_category_id,
            defaults={"master_category_id": master_category_id},
        )
        return Response(
            {"id": mapping.id, "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def destroy(self, request, pk=None):
        try:
            CategoryMapping.objects.get(pk=pk).delete()
        except CategoryMapping.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Alert views ───────────────────────────────────────────────────────────────

class AlertLogView(generics.ListAPIView):
    """
    GET /api/alerts/
    Returns the logged-in user's alert history, most recent first.
    Supports ?limit=N (default 50, max 200).
    """
    serializer_class = AlertLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = AlertLog.objects.filter(
            subscription__user=self.request.user,
        ).select_related(
            'deal', 'deal__product',
            'deal__retailer',
            'deal__product__master_category',
            'subscription',
        ).order_by('-sent_at')

        limit = min(
            int(self.request.query_params.get('limit', 50)),
            200)
        return qs[:limit]


class AlertMarkReadView(generics.UpdateAPIView):
    """
    PATCH /api/alerts/<id>/read/
    Marks a specific alert as read.
    """
    serializer_class = AlertLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['patch']

    def get_queryset(self):
        return AlertLog.objects.filter(
            subscription__user=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        alert = self.get_object()
        alert.is_read = True
        alert.save(update_fields=['is_read'])
        return Response(self.get_serializer(alert).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_alerts_read(request):
    """POST /api/alerts/read-all/"""
    AlertLog.objects.filter(
        subscription__user=request.user,
        is_read=False,
    ).update(is_read=True)
    return Response({'status': 'ok'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def alert_unread_count(request):
    """GET /api/alerts/unread-count/"""
    count = AlertLog.objects.filter(
        subscription__user=request.user,
        is_read=False,
    ).count()
    return Response({'unread': count})


# ── Email config admin views ──────────────────────────────────────────────────

class AdminEmailConfigView(APIView):
    """
    GET  /admin/email-config/   — return current SMTP config (password masked)
    PUT  /admin/email-config/   — update SMTP config
    """
    permission_classes = [permissions.IsAdminUser]

    def _serialize(self, cfg):
        return {
            'smtp_host': cfg.smtp_host,
            'smtp_port': cfg.smtp_port,
            'smtp_username': cfg.smtp_username,
            'smtp_password': '••••••••' if cfg.smtp_password else '',
            'use_tls': cfg.use_tls,
            'use_ssl': cfg.use_ssl,
            'from_email': cfg.from_email,
            'from_name': cfg.from_name,
            'is_active': cfg.is_active,
            'updated_at': cfg.updated_at,
        }

    def get(self, request):
        from core.models import EmailConfig
        cfg = EmailConfig.get()
        return Response(self._serialize(cfg))

    def put(self, request):
        from core.models import EmailConfig
        cfg = EmailConfig.get()
        fields = [
            'smtp_host', 'smtp_port', 'smtp_username',
            'use_tls', 'use_ssl', 'from_email', 'from_name', 'is_active',
        ]
        for field in fields:
            if field in request.data:
                setattr(cfg, field, request.data[field])
        # Only update password if a real value (not the masked placeholder) is sent
        password = request.data.get('smtp_password', '')
        if password and password != '••••••••':
            cfg.smtp_password = password
        cfg.save()
        return Response(self._serialize(cfg))


class AdminEmailTestView(APIView):
    """POST /admin/email-config/test/ — send a test email to the given address."""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        from core.services.email import send_test_email
        to = request.data.get('to') or request.user.email
        if not to:
            return Response(
                {'detail': 'Provide a "to" email address'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        success = send_test_email(to)
        if success:
            return Response({'detail': f'Test email sent to {to}'})
        return Response(
            {'detail': 'Failed to send — check SMTP settings and server logs'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class AdminSendTestAlertView(APIView):
    """
    POST /admin/users/<pk>/send-test-alert/
    Collects the best deal from each active subscription and sends ONE
    batched alert email listing all of them.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk=None):
        from core.models import UserProfile, Subscription, Deal
        from core.services.alert_resolver import resolve_alert_products
        from core.services.email import _send
        from django.conf import settings
        from django.db.models import F

        try:
            profile = UserProfile.objects.select_related('user').get(pk=pk)
        except UserProfile.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        user = profile.user
        if not user.email:
            return Response(
                {'detail': f'User {user.username} has no email address on their account'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subs = Subscription.objects.filter(user=user, is_active=True).select_related(
            'product', 'category', 'retailer'
        )
        if not subs.exists():
            return Response(
                {'detail': 'User has no active subscriptions to send alerts for'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Collect one best deal per subscription, dedup by product id
        deals_data = []
        seen_products = set()

        for sub in subs:
            products = resolve_alert_products(sub)
            for product in products[:1]:
                if product.id in seen_products:
                    continue
                deal = (
                    Deal.objects
                    .filter(product=product)
                    .select_related('product', 'retailer', 'branch')
                    .order_by(F('old_price') - F('current_price'))
                    .last()
                )
                if not deal:
                    continue
                seen_products.add(product.id)
                old = deal.old_price
                cur = deal.current_price
                deals_data.append({
                    'name': deal.product.name,
                    'retailer': deal.retailer.name,
                    'price': cur,
                    'old_price': old,
                    'discount_pct': int((old - cur) / old * 100) if old and old > cur else None,
                    'image_url': getattr(deal.product, 'image_url', None),
                    'branch': deal.branch.name if getattr(deal, 'branch', None) else None,
                })

        if not deals_data:
            return Response(
                {'detail': 'No active deals found for this user\'s subscriptions right now'},
                status=status.HTTP_200_OK,
            )

        name = user.first_name or user.username
        subject = (
            f"Price drop: {deals_data[0]['name']}"
            if len(deals_data) == 1
            else f"{len(deals_data)} deals matched your alerts"
        )

        _send(
            subject=subject,
            template='emails/deal_alert.html',
            context={
                'name': name,
                'deals': deals_data,
                'site_url': getattr(settings, 'SITE_URL', 'https://www.bargainhunters.co.ke'),
            },
            to=user.email,
        )

        return Response({
            'email': user.email,
            'deals_included': [d['name'] for d in deals_data],
        })


class AdminEmailDigestStatsView(APIView):
    """GET /admin/email-config/digest-stats/ — opt-in counts and breakdown."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from core.models import UserProfile
        total = UserProfile.objects.count()
        opted_in = UserProfile.objects.filter(email_digest_opt_in=True).count()
        daily = UserProfile.objects.filter(email_digest_opt_in=True, email_digest_frequency='daily').count()
        weekly = UserProfile.objects.filter(email_digest_opt_in=True, email_digest_frequency='weekly').count()
        with_email = UserProfile.objects.filter(email_digest_opt_in=True, user__email__gt='').count()
        return Response({
            'total_users': total,
            'opted_in': opted_in,
            'opted_out': total - opted_in,
            'daily_subscribers': daily,
            'weekly_subscribers': weekly,
            'with_email_address': with_email,
        })
