from rest_framework import serializers
from documents.models import Document
from chat.models import Message

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'title', 'file', 'file_type', 'file_size', 'uploaded_at']

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'sender', 'room', 'content', 'timestamp']
