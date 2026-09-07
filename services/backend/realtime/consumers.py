import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class ChatPingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return
        await self.accept()

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})
        else:
            await self.send_json({"type": "error", "message": "unsupported"})
