from django.urls import path
from core.views.auth import login_view
from core.views.subscriptions import (
    subscription_list,
    subscription_create,
    subscription_update,
    subscription_deactivate
)
from core.views.webhooks import mpesa_callback

urlpatterns = [
    path("login/", login_view, name="login"),
    path("subscriptions/", subscription_list, name="subscription_list"),
    path("subscriptions/add/", subscription_create, name="subscription_create"),
    path("subscriptions/<int:pk>/edit/", subscription_update, name="subscription_update"),
    path("subscriptions/<int:pk>/deactivate/", subscription_deactivate, name="subscription_deactivate"),

    # MPesa callback
    path("webhooks/mpesa/", mpesa_callback, name="mpesa-callback"),
]
