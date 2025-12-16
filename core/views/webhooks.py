import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Payment
from core.services.payments import mark_payment_success


@csrf_exempt
def mpesa_callback(request):
    data = json.loads(request.body)

    stk = data.get("Body", {}).get("stkCallback", {})
    result_code = stk.get("ResultCode")
    reference = stk.get("CheckoutRequestID")

    if result_code == 0:
        payment = Payment.objects.filter(reference=reference).first()
        if payment:
            mark_payment_success(payment)

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
