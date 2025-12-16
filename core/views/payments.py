from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from core.services.payments import create_payment
from core.integrations.mpesa import stk_push
from core.constants import MONTHLY_SUBSCRIPTION_PRICE

@login_required
def upgrade(request):
    if request.method == "POST":
        phone = request.POST.get("phone")
        payment = create_payment(request.user, MONTHLY_SUBSCRIPTION_PRICE)

        stk_push(
            phone_number=phone,
            amount=MONTHLY_SUBSCRIPTION_PRICE,
            reference=payment.reference
        )

        return redirect("payment-pending")

    return render(request, "payments/upgrade.html")