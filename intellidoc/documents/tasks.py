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

@shared_task(bind=True)
def process_document_task(self, document_id: str, user_id: int):
    """Background task to process uploaded document"""
    
    try:
        # Get document and user
        document = Document.objects.get(id=document_id)
        user = User.objects.get(id=user_id)
        
        # Send real-time update
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "document_processing_update",
                "message": {
                    "document_id": document_id,
                    "status": "processing",
                    "progress": 5,
                    "message": "Starting document processing..."
                }
            }
        )
        
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
            
            logger.info(f"Successfully processed document {document_id}")
            
        else:
            # Send error notification  
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
            
            logger.error(f"Failed to process document {document_id}")
    
    except Exception as e:
        logger.error(f"Task error for document {document_id}: {str(e)}")
        
        # Update document status
        try:
            document = Document.objects.get(id=document_id)
            document.status = 'error'
            document.error_message = str(e)
            document.save()
        except:
            pass

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
    
    for doc in failed_docs:
        logger.info(f"Cleaning up failed document: {doc.id}")
        doc.delete()
    
    return f"Cleaned up {failed_docs.count()} failed documents"

@shared_task
def rebuild_faiss_index():
    """Rebuild FAISS index from scratch (maintenance task)"""
    
    try:
        processor = DocumentProcessor()
        
        # Get all ready documents
        documents = Document.objects.filter(status='ready', is_indexed=True)
        
        logger.info(f"Rebuilding FAISS index for {documents.count()} documents")
        
        for document in documents:
            # Reprocess document
            processor.process_document(document)
        
        return f"Successfully rebuilt FAISS index for {documents.count()} documents"
        
    except Exception as e:
        logger.error(f"Error rebuilding FAISS index: {str(e)}")
        return f"Error: {str(e)}"