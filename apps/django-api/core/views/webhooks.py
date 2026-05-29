import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Payment, User, UserProfile
from core.services.payments import mark_payment_success
from django.utils import timezone
from datetime import timedelta
from core.services.subscriptions import extend_user_subscription

@csrf_exempt
def mpesa_callback(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    print("M-PESA CALLBACK:")
    print(json.dumps(data, indent=2))

    callback = data.get("Body", {}).get("stkCallback")
    if not callback:
        return JsonResponse({"error": "Invalid callback payload"}, status=400)

    result_code = callback.get("ResultCode")
    checkout_id = callback.get("CheckoutRequestID")

    try:
        payment = Payment.objects.get(reference=checkout_id)
    except Payment.DoesNotExist:
        return JsonResponse({"error": "Payment not found"}, status=404)

    # 🔒 Idempotency
    if payment.status == "success":
        return JsonResponse({"status": "already processed"})

    if result_code == 0:
        metadata = callback.get("CallbackMetadata", {}).get("Item", [])
        meta = {item["Name"]: item.get("Value") for item in metadata}

        mark_payment_success(payment, provider_reference=None)
        # new_expiry = extend_user_subscription(payment.user)
        payment.user.subscription_set.update(is_active=True)
        payment.status = "success"
        payment.provider_reference = meta.get("MpesaReceiptNumber")
        payment.completed_at = timezone.now()
        payment.expires_at = extend_user_subscription(payment.user)
        payment.provider = "mpesa"
        payment.save()

        # Upgrade user
        profile = payment.user.userprofile
        profile.payment_status = True
        profile.is_free_tier = False
        profile.grace_until = None
        profile.save()

        # payment.user.subscription_set.update(is_active=True)
        extend_user_subscription(payment.user)

    else:
        payment.status = "failed"
        payment.completed_at = timezone.now()
        payment.save()

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

# @csrf_exempt
# def mpesa_callback(request):
#     print("🔥 CALLBACK VIEW ENTERED")
#     print("METHOD:", request.method)
#     print("RAW BODY:", request.body)

#     return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
