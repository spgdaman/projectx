from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from core.models import Subscription, Product, Category, Retailer
from core.services.subscriptions import can_create_subscription


@login_required
def create_subscription(request):
    user = request.user

    if not can_create_subscription(user):
        return JsonResponse(
            {"error": "Free tier limit reached"},
            status=403
        )

    target_type = request.POST.get("target_type")
    target_id = request.POST.get("target_id")

    data = {
        "user": user,
        "target_type": target_type,
        "is_free_tier": True,
        "is_paid": False,
        "is_active": True,
    }

    if target_type == "product":
        data["product"] = Product.objects.get(id=target_id)

    elif target_type == "category":
        data["category"] = Category.objects.get(id=target_id)

    elif target_type == "retailer":
        data["retailer"] = Retailer.objects.get(id=target_id)

    Subscription.objects.create(**data)

    return JsonResponse({"status": "subscribed"})
