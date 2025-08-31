# chat/models.py - CHAT & CONVERSATION MODELS

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from documents.models import Document

class Conversation(models.Model):
    """Chat conversation with documents"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations')
    
    # Conversation details
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Context documents
    documents = models.ManyToManyField(Document, blank=True, related_name='conversations')
    
    # Settings
    is_pinned = models.BooleanField(default=False)
    is_shared = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-last_message_at']
        indexes = [
            models.Index(fields=['user', '-last_message_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.title}"
    
    @property
    def message_count(self):
        return self.messages.count()
    
    def update_activity(self):
        self.last_message_at = timezone.now()
        self.save(update_fields=['last_message_at'])

class Message(models.Model):
    """Individual messages in conversations"""
    
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    
    # Message content
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    
    # AI Response metadata
    model_used = models.CharField(max_length=50, blank=True)
    tokens_used = models.IntegerField(default=0)
    response_time = models.FloatField(default=0.0)  # in seconds
    
    # Source citations
    citations = models.JSONField(default=list, blank=True)  # List of document chunks used
    
    # User feedback
    rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    feedback = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."