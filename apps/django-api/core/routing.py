from django.urls import path
from .consumers import DealConsumer

websocket_urlpatterns = [
    path("ws/deals/", DealConsumer.as_asgi()),
]
