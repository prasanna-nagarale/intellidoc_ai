# documents/services.py
import os
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import Document, DocumentChunk

logger = logging.getLogger('intellidoc.documents')

class SimpleDocumentProcessor:
    """Simplified document processor that works without external dependencies"""
    
    def __init__(self):
        self.setup_directories()
    
    def setup_directories(self):
        """Ensure required directories exist"""
        try:
            faiss_path = getattr(settings, 'FAISS_INDEX_PATH', settings.BASE_DIR / 'data' / 'faiss_index')
            os.makedirs(faiss_path, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create FAISS directory: {e}")
    
    def extract_text_from_file(self, file_path: str, file_type: str) -> tuple[str, dict]:
        """Extract text from uploaded file"""
        
        try:
            metadata = {"source": file_path}
            
            if file_type == 'pdf':
                # For now, we'll use a simple approach
                # You can install PyPDF2 or pdfplumber later
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + "\n"
                        metadata.update({
                            "page_count": len(reader.pages),
                            "word_count": len(text.split())
                        })
                except ImportError:
                    # Fallback: create placeholder text
                    text = f"PDF file uploaded: {os.path.basename(file_path)}\nContent extraction requires PyPDF2 installation."
                    metadata.update({"page_count": 1, "word_count": len(text.split())})
                
            elif file_type in ['docx', 'doc']:
                try:
                    import docx
                    doc = docx.Document(file_path)
                    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                    metadata.update({
                        "page_count": 1,
                        "word_count": len(text.split())
                    })
                except ImportError:
                    text = f"Word document uploaded: {os.path.basename(file_path)}\nContent extraction requires python-docx installation."
                    metadata.update({"page_count": 1, "word_count": len(text.split())})
                
            elif file_type in ['txt', 'md']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                metadata.update({
                    "page_count": 1,
                    "word_count": len(text.split())
                })
            
            else:
                text = f"File uploaded: {os.path.basename(file_path)}\nUnsupported file type: {file_type}"
                metadata.update({"page_count": 1, "word_count": len(text.split())})
            
            return text, metadata
            
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            # Return fallback text instead of raising exception
            fallback_text = f"File uploaded: {os.path.basename(file_path)}\nText extraction failed: {str(e)}"
            return fallback_text, {"page_count": 1, "word_count": len(fallback_text.split())}
    
    def create_chunks(self, text: str, document_id: str) -> List[Dict[str, Any]]:
        """Split text into chunks for processing"""
        
        # Simple chunking - split by paragraphs and limit size
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            # If adding this paragraph would make chunk too large, save current chunk
            if len(current_chunk) + len(paragraph) > 1000 and current_chunk:
                chunks.append({
                    "content": current_chunk.strip(),
                    "chunk_index": chunk_index,
                    "chunk_size": len(current_chunk),
                    "metadata": {"document_id": document_id}
                })
                chunk_index += 1
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        # Add the last chunk
        if current_chunk:
            chunks.append({
                "content": current_chunk.strip(),
                "chunk_index": chunk_index,
                "chunk_size": len(current_chunk),
                "metadata": {"document_id": document_id}
            })
        
        logger.info(f"Created {len(chunks)} chunks for document {document_id}")
        return chunks
    
    def process_document(self, document: Document) -> bool:
        """Complete document processing pipeline"""
        
        try:
            logger.info(f"Starting to process document {document.id}")
            
            # Update status
            document.status = 'processing'
            document.processing_progress = 20
            document.save()
            
            # Extract text
            file_path = document.file.path
            text, metadata = self.extract_text_from_file(file_path, document.file_type)
            
            # Update document metadata
            document.page_count = metadata.get('page_count', 0)
            document.word_count = metadata.get('word_count', 0)
            document.processing_progress = 50
            document.save()
            
            # Create chunks
            chunks_data = self.create_chunks(text, str(document.id))
            document.processing_progress = 70
            document.save()
            
            # Save chunks to database
            chunk_objects = []
            for i, chunk_data in enumerate(chunks_data):
                chunk_objects.append(DocumentChunk(
                    document=document,
                    content=chunk_data["content"],
                    chunk_index=chunk_data["chunk_index"],
                    chunk_size=chunk_data["chunk_size"],
                    faiss_index=i,  # Simple indexing
                    embedding_model="simple"
                ))
            
            DocumentChunk.objects.bulk_create(chunk_objects)
            document.chunk_count = len(chunk_objects)
            
            # Mark as processed
            document.status = 'ready'
            document.processed_at = timezone.now() if hasattr(timezone, 'now') else None
            document.processing_progress = 100
            document.is_indexed = True
            document.embedding_model = "simple"
            document.save()
            
            logger.info(f"Successfully processed document {document.id}")
            return True
            
        except Exception as e:
            # Mark as error
            document.status = 'error'
            document.error_message = str(e)
            document.save()
            
            logger.error(f"Error processing document {document.id}: {str(e)}")
            return False

# Maintain the original class name for backward compatibility
class DocumentProcessor(SimpleDocumentProcessor):
    pass

class SimpleFAISSSearchService:
    """Simple search service that works without FAISS"""
    
    def search_documents(self, query: str, k: int = 5, user_documents: List[str] = None) -> List[Dict[str, Any]]:
        """Search documents using simple text matching"""
        
        try:
            from django.db.models import Q
            
            # Simple text search in chunks
            chunks_query = DocumentChunk.objects.all()
            
            # Filter by user documents if specified
            if user_documents:
                chunks_query = chunks_query.filter(document_id__in=user_documents)
            
            # Search in content
            chunks_query = chunks_query.filter(
                Q(content__icontains=query)
            ).select_related('document')[:k]
            
            results = []
            for chunk in chunks_query:
                results.append({
                    "chunk": chunk,
                    "document": chunk.document,
                    "score": 1.0,  # Simple scoring
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index
                })
            
            logger.info(f"Found {len(results)} relevant chunks for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return []
    
    def get_document_stats(self) -> Dict[str, Any]:
        """Get simple statistics"""
        try:
            total_chunks = DocumentChunk.objects.count()
            return {
                "total_vectors": total_chunks,
                "dimension": 0,
                "index_type": "Simple"
            }
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {"total_vectors": 0, "dimension": 0, "index_type": "Error"}

# Maintain original class name for backward compatibility  
class FAISSSearchService(SimpleFAISSSearchService):
    pass