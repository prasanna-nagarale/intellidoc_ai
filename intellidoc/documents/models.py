import os
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

def validate_file_type(value):
    """Validate uploaded file type"""
    allowed_types = ['.pdf', '.docx', '.doc', '.txt', '.md']
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in allowed_types:
        raise ValidationError(f'File type {ext} not allowed. Allowed types: {", ".join(allowed_types)}')

def document_upload_path(instance, filename):
    """Generate upload path for documents"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return f"documents/{instance.owner.id}/{filename}"

class Document(models.Model):
    """Document model for uploaded files"""
    
    STATUS_CHOICES = [
        ('uploading', 'Uploading'),
        ('processing', 'Processing'),
        ('ready', 'Ready'),
        ('error', 'Error'),
        ('deleted', 'Deleted'),
    ]
    
    TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('docx', 'Word Document'),
        ('txt', 'Text File'),
        ('md', 'Markdown'),
        ('web', 'Web Page'),
    ]
    
    # Basic Info
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to=document_upload_path, validators=[validate_file_type])
    
    # Metadata
    file_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    file_size = models.BigIntegerField()  # in bytes
    page_count = models.IntegerField(default=0)
    word_count = models.IntegerField(default=0)
    
    # Processing Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploading')
    processing_progress = models.IntegerField(default=0)  # 0-100
    error_message = models.TextField(blank=True)
    
    # Ownership & Access
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    is_public = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='shared_documents')
    
    # AI Processing
    is_indexed = models.BooleanField(default=False)
    embedding_model = models.CharField(max_length=100, blank=True)
    chunk_count = models.IntegerField(default=0)
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Analytics
    view_count = models.IntegerField(default=0)
    query_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'documents_document'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['is_indexed']),
            models.Index(fields=['file_type']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def file_size_mb(self):
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def processing_status_display(self):
        if self.status == 'processing':
            return f"Processing... {self.processing_progress}%"
        return self.get_status_display()
    
    def mark_as_processed(self):
        self.status = 'ready'
        self.processed_at = timezone.now()
        self.processing_progress = 100
        self.save(update_fields=['status', 'processed_at', 'processing_progress'])
    
    def increment_view_count(self):
        self.view_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['view_count', 'last_accessed'])
    
    def increment_query_count(self):
        self.query_count += 1
        self.save(update_fields=['query_count'])

class DocumentChunk(models.Model):
    """Text chunks from processed documents for RAG"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    
    # Content
    content = models.TextField()
    chunk_index = models.IntegerField()
    chunk_size = models.IntegerField()
    
    # Metadata
    page_number = models.IntegerField(null=True, blank=True)
    section_title = models.CharField(max_length=255, blank=True)
    
    # Vector Storage Info
    faiss_index = models.IntegerField(null=True, blank=True)  # Index in FAISS vector store
    embedding_model = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'documents_chunk'
        ordering = ['document', 'chunk_index']
        indexes = [
            models.Index(fields=['document', 'chunk_index']),
            models.Index(fields=['faiss_index']),
        ]
    
    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"

class DocumentCollection(models.Model):
    """Collections/folders for organizing documents"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='collections')
    documents = models.ManyToManyField(Document, blank=True, related_name='collections')
    
    # Settings
    is_default = models.BooleanField(default=False)
    color = models.CharField(max_length=7, default='#3B82F6')  # Hex color
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'documents_collection'
        ordering = ['name']
        unique_together = ['owner', 'name']
    
    def __str__(self):
        return f"{self.owner.username} - {self.name}"
    
    @property
    def document_count(self):
        return self.documents.count()

class DocumentAccess(models.Model):
    """Track document access for analytics"""
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='access_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    action = models.CharField(max_length=20, choices=[
        ('view', 'View'),
        ('download', 'Download'), 
        ('query', 'Query'),
        ('share', 'Share'),
    ])
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'documents_access'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['document', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]


# documents/models.py
from django.db.models.signals import pre_save
from django.dispatch import receiver

@receiver(pre_save, sender=Document)
def set_file_metadata(sender, instance, **kwargs):
    if instance.file:
        # File type from extension
        _, ext = os.path.splitext(instance.file.name)
        instance.file_type = ext.lower().replace(".", "")

        # File size (bytes → KB)
        instance.file_size = instance.file.size // 1024