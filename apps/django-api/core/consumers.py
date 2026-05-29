import json
from channels.generic.websocket import AsyncWebsocketConsumer


class DealConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time deal push notifications.

    Clients connect to ws/deals/ and join the "deals" group.
    When a new Deal is created, broadcast_deal() is called from the
    save signal / Celery task to push it to all connected clients.
    """

    GROUP_NAME = "deals"

    async def connect(self):
        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    # Receive is unused — clients only listen, not send
    async def receive(self, text_data=None, bytes_data=None):
        pass

    async def deal_message(self, event):
        """Handler called by channel layer group_send."""
        await self.send(text_data=json.dumps(event["data"]))
