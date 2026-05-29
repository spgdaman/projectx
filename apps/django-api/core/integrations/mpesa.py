import base64
import requests
from datetime import datetime
from django.conf import settings

def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(
        url,
        auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET)
    )
    return response.json()["access_token"]

def stk_push(phone_number, amount):
    token=get_access_token()
    timestamp=datetime.now().strftime("YmdHMS")

    password = base64.b64encode(
        # f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode()
        f"{settings.MPESA_CONSUMER_KEY}{settings.MPESA_CONSUMER_SECRET}{timestamp}".encode()
    ).decode()

    # payload = { 
    #     "BusinessShortCode": 174379,
    #     "Password": password,
    #     "Timestamp": "20210628092408",
    #     "TransactionType": "BuyGoods",
    #     "Amount": amount,
    #     "PartyA": phone_number,
    #     "PartyB": "174379",
    #     "PhoneNumber": phone_number,
    #     "CallBackURL": "127.0.0.1/8000/webhooks/mpesa/",
    #     "AccountReference": reference,
    #     "TransactionDesc": "txndesc"
    # } 

    payload = {
        "Password": "MTc0Mzc5YmZiMjc5ZjlhYTliZGJjZjE1OGU5N2RkNzFhNDY3Y2QyZTBjODkzMDU5YjEwZjc4ZTZiNzJhZGExZWQyYzkxOTIwMjUxMjE2MTUxMDMw",
        "BusinessShortCode": "174379",
        "Timestamp": "20251216151030",
        "Amount": 1,
        # "PartyA": "254708374149",
        "PartyA": phone_number,
        "PartyB": "174379",
        "TransactionType": "CustomerPayBillOnline",
        # "PhoneNumber": "254708374149",
        "PhoneNumber": phone_number,
        "TransactionDesc": "Test",
        "AccountReference": "Test",
        "CallBackURL": "https://excuseless-atmospherically-delcie.ngrok-free.dev/webhooks/mpesa/"
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"        
    }

    response = requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers=headers        
    )

    response_data = response.json()
    reference = response_data.get("CheckoutRequestID")
    print(reference)

    return reference

