import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Channel, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.channel_id = self.scope["url_route"]["kwargs"]["channel_id"]
        self.group_name = f"chat_{self.channel_id}"
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        allowed = await self.user_can_access()
        if not allowed:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "presence", "username": self.user.username, "status": "online"},
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "presence", "username": self.user.username, "status": "offline"},
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        kind = data.get("type")

        if kind == "message":
            content = (data.get("content") or "").strip()
            if not content:
                return
            saved = await self.save_message(content)
            await self.channel_layer.group_send(
                self.group_name, {"type": "chat_message", "message": saved}
            )

        elif kind == "typing":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "typing_indicator",
                    "username": self.user.username,
                    "is_typing": bool(data.get("is_typing")),
                },
            )

        elif kind == "reaction":
            message_id = data.get("message_id")
            emoji = data.get("emoji")
            if not message_id or not emoji:
                return
            reactions = await self.add_reaction(message_id, emoji)
            if reactions is not None:
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type": "reaction_update", "message_id": message_id, "reactions": reactions},
                )

    # ---- group event handlers (broadcast -> individual socket) ----
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"type": "message", "message": event["message"]}))

    async def typing_indicator(self, event):
        await self.send(
            text_data=json.dumps(
                {"type": "typing", "username": event["username"], "is_typing": event["is_typing"]}
            )
        )

    async def presence(self, event):
        await self.send(
            text_data=json.dumps(
                {"type": "presence", "username": event["username"], "status": event["status"]}
            )
        )

    async def reaction_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "reaction",
                    "message_id": event["message_id"],
                    "reactions": event["reactions"],
                }
            )
        )

    # ---- db helpers ----
    @database_sync_to_async
    def user_can_access(self):
        try:
            channel = Channel.objects.get(pk=self.channel_id)
        except Channel.DoesNotExist:
            return False
        return channel.is_member(self.user)

    @database_sync_to_async
    def save_message(self, content):
        channel = Channel.objects.get(pk=self.channel_id)
        msg = Message.objects.create(channel=channel, user=self.user, content=content)
        return msg.to_dict()

    @database_sync_to_async
    def add_reaction(self, message_id, emoji):
        try:
            msg = Message.objects.get(pk=message_id, channel_id=self.channel_id)
        except Message.DoesNotExist:
            return None
        reactions = msg.reactions or {}
        reactions[emoji] = reactions.get(emoji, 0) + 1
        msg.reactions = reactions
        msg.save(update_fields=["reactions"])
        return reactions
