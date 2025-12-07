# documents/tasks.py
import logging
from celery import shared_task
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Document
from .services import DocumentProcessor
from accounts.models import User

logger = logging.getLogger('intellidoc.tasks')
channel_layer = get_channel_layer()

@shared_task(bind=True, max_retries=3)
def process_document_task(self, document_id: str, user_id: int):
    """Background task to process uploaded document"""
    
    try:
        # Get document and user
        document = Document.objects.get(id=document_id)
        user = User.objects.get(id=user_id)
        
        logger.info(f"Starting to process document {document_id}")
        
        # Update document status to processing
        document.status = 'processing'
        document.processing_progress = 10
        document.save()
        
        # Send real-time update if channels are configured
        try:
            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}",
                {
                    "type": "document_processing_update",
                    "message": {
                        "document_id": document_id,
                        "status": "processing",
                        "progress": 10,
                        "message": "Starting document processing..."
                    }
                }
            )
        except Exception as e:
            logger.warning(f"Could not send real-time update: {e}")
        
        # Process document
        processor = DocumentProcessor()
        success = processor.process_document(document)
        
        if success:
            # Update user usage stats
            user.update_usage(
                documents_delta=1,
                storage_delta=document.file_size
            )
            
            # Send success notification
            try:
                async_to_sync(channel_layer.group_send)(
                    f"user_{user_id}",
                    {
                        "type": "document_processing_update", 
                        "message": {
                            "document_id": document_id,
                            "status": "ready",
                            "progress": 100,
                            "message": f"✅ {document.title} is ready for queries!",
                            "chunk_count": document.chunk_count,
                            "word_count": document.word_count
                        }
                    }
                )
            except Exception as e:
                logger.warning(f"Could not send success notification: {e}")
            
            logger.info(f"Successfully processed document {document_id}")
            
        else:
            # Send error notification  
            try:
                async_to_sync(channel_layer.group_send)(
                    f"user_{user_id}",
                    {
                        "type": "document_processing_update",
                        "message": {
                            "document_id": document_id,
                            "status": "error", 
                            "progress": 0,
                            "message": f"❌ Error processing {document.title}",
                            "error": document.error_message
                        }
                    }
                )
            except Exception as e:
                logger.warning(f"Could not send error notification: {e}")
            
            logger.error(f"Failed to process document {document_id}: {document.error_message}")
    
    except Exception as e:
        logger.error(f"Task error for document {document_id}: {str(e)}")
        
        # Update document status
        try:
            document = Document.objects.get(id=document_id)
            document.status = 'error'
            document.error_message = str(e)
            document.save()
        except Exception as save_error:
            logger.error(f"Could not save error status: {save_error}")
        
        # Retry the task
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying document processing for {document_id}, attempt {self.request.retries + 1}")
            raise self.retry(countdown=60 * (self.request.retries + 1), exc=e)

@shared_task
def cleanup_failed_uploads():
    """Clean up documents that failed to process after 24 hours"""
    
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_time = timezone.now() - timedelta(hours=24)
    
    failed_docs = Document.objects.filter(
        status__in=['uploading', 'processing'],
        uploaded_at__lt=cutoff_time
    )
    
    count = failed_docs.count()
    for doc in failed_docs:
        logger.info(f"Cleaning up failed document: {doc.id}")
        doc.status = 'error'
        doc.error_message = "Processing timed out after 24 hours"
        doc.save()
    
    return f"Cleaned up {count} failed documents"