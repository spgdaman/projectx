from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from core.services.payments import create_payment, expire_stale_payments
from core.integrations.mpesa import stk_push
from core.constants import MONTHLY_SUBSCRIPTION_PRICE
from core.models import Payment
from django.utils.crypto import get_random_string
from django.http import JsonResponse
from datetime import timezone, timedelta

@login_required
def upgrade(request):
    if request.method == "POST":
        phone = request.POST.get("phone")
        payment = create_payment(request.user, MONTHLY_SUBSCRIPTION_PRICE, "mpesa")

        call_and_reference = stk_push(
            phone_number=phone,
            amount=MONTHLY_SUBSCRIPTION_PRICE,
        )

        payment.reference = call_and_reference
        payment.expires_at=timezone.now() + timedelta(minutes=2)
        payment.save()

        return redirect("payment-pending")

    return render(request, "payments/upgrade.html")

@login_required
def initiate_payment(request):
    if request.method == "POST":
        phone = request.POST.get("phone")

        reference = get_random_string(12)

        payment = Payment.objects.create(
            user=request.user,
            amount=MONTHLY_SUBSCRIPTION_PRICE,
            status="pending",
            reference=reference
        )

        call_and_reference = stk_push(
            phone_number=phone,
            amount=payment.amount
        )
        payment.reference = call_and_reference
        payment.save()

        return redirect("payment-pending")

    return render(request, "payments/initiate.html")

@login_required
def payment_status(request):
    expire_stale_payments()

    payment = (
        Payment.objects
        .filter(user=request.user)
        .order_by("-created_at")
        .first()
    )

    if not payment:
        return JsonResponse({"status": "none"})

    return JsonResponse({
        "status": payment.status
    })
