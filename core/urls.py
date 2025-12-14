from django.urls import path
from core.views.subscriptions import unsubscribe

urlpatterns = [
    path("subscriptions/<int:subscription_id>/unsubscribe/", unsubscribe),
]
