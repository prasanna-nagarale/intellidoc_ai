# chat/consumers.py - WEBSOCKET CONSUMER

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

logger = logging.getLogger('intellidoc.chat')


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""

    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.group_name = f"user_{self.user_id}"

        user = self.scope.get("user")
        if not user or not user.is_authenticated or str(user.id) != str(self.user_id):
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"WebSocket connected for user {self.user_id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"WebSocket disconnected for user {self.user_id}")

    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            data = json.loads(text_data)
            if data.get("type") == "ping":
                await self.send(
                    text_data=json.dumps(
                        {"type": "pong", "timestamp": data.get("timestamp")}
                    )
                )
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from user {self.user_id}")

    async def document_processing_update(self, event):
        await self.send(
            text_data=json.dumps(
                {"type": "document_processing_update", "message": event["message"]}
            )
        )

    async def chat_response(self, event):
        await self.send(
            text_data=json.dumps({"type": "chat_response", "message": event["message"]})
        )

    async def system_notification(self, event):
        await self.send(
            text_data=json.dumps(
                {"type": "system_notification", "message": event["message"]}
            )
        )


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat"""

    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.group_name = f"chat_{self.conversation_id}"

        allowed = await self.can_access_conversation()
        if not allowed:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"Chat WebSocket connected for conversation {self.conversation_id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle chat messages"""
        try:
            data = json.loads(text_data)
            if data.get("type") == "chat_message":
                await self.handle_chat_message(data)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received for conversation {self.conversation_id}")

    async def handle_chat_message(self, data):
        """Process incoming chat message"""
        message_content = (data.get("message") or "").strip()
        if not message_content:
            return

        # Save user message
        user_msg = await self.save_message(role="user", content=message_content)
        if user_msg:
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "chat_message_broadcast", "message": user_msg},
            )

        # Placeholder AI response (Phase 2: replace with actual LLM call)
        ai_response = (
            "I'm processing your question about the documents. "
            "Full AI integration coming in Phase 2! 🤖"
        )
        ai_msg = await self.save_message(role="assistant", content=ai_response)
        if ai_msg:
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "chat_message_broadcast", "message": ai_msg},
            )

    async def chat_message_broadcast(self, event):
        """Broadcast chat message to WebSocket"""
        await self.send(
            text_data=json.dumps({"type": "chat_message", "message": event["message"]})
        )

    @database_sync_to_async
    def can_access_conversation(self):
        """Check if user can access conversation"""
        from .models import Conversation

        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.user == self.scope["user"]
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, role, content):
        """Save message to database and return dict"""
        from .models import Conversation, Message

        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            message = Message.objects.create(
                conversation=conversation, role=role, content=content
            )
            conversation.update_activity()
            return {
                "id": str(message.id),
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            }
        except Conversation.DoesNotExist:
            logger.error(f"Conversation {self.conversation_id} not found")
            return None
