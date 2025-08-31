import os
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain.schema import Document as LangchainDocument

from django.conf import settings
from django.core.files.base import ContentFile
from .models import Document, DocumentChunk

logger = logging.getLogger('intellidoc.documents')

class DocumentProcessor:
    """Advanced document processing service with FAISS integration"""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""]
        )
        self.faiss_index_path = settings.FAISS_INDEX_PATH
        self.ensure_faiss_directory()
    
    def ensure_faiss_directory(self):
        """Ensure FAISS index directory exists"""
        os.makedirs(self.faiss_index_path, exist_ok=True)
    
    def extract_text_from_file(self, file_path: str, file_type: str) -> tuple[str, dict]:
        """Extract text from uploaded file with metadata"""
        
        try:
            metadata = {"source": file_path}
            
            if file_type == 'pdf':
                loader = PyPDFLoader(file_path)
                documents = loader.load()
                text = "\n".join([doc.page_content for doc in documents])
                metadata.update({
                    "page_count": len(documents),
                    "word_count": len(text.split())
                })
                
            elif file_type in ['docx', 'doc']:
                loader = Docx2txtLoader(file_path)
                documents = loader.load()
                text = documents[0].page_content if documents else ""
                metadata.update({
                    "page_count": 1,
                    "word_count": len(text.split())
                })
                
            elif file_type in ['txt', 'md']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                metadata.update({
                    "page_count": 1,
                    "word_count": len(text.split())
                })
            
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            return text, metadata
            
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            raise Exception(f"Failed to extract text: {str(e)}")
    
    def create_chunks(self, text: str, document_id: str) -> List[Dict[str, Any]]:
        """Split text into chunks for RAG processing"""
        
        # Create LangChain document
        langchain_doc = LangchainDocument(
            page_content=text,
            metadata={"document_id": document_id}
        )
        
        # Split into chunks
        chunks = self.text_splitter.split_documents([langchain_doc])
        
        # Convert to our format
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            processed_chunks.append({
                "content": chunk.page_content,
                "chunk_index": i,
                "chunk_size": len(chunk.page_content),
                "metadata": chunk.metadata
            })
        
        logger.info(f"Created {len(processed_chunks)} chunks for document {document_id}")
        return processed_chunks
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for text chunks"""
        try:
            embeddings = self.embedding_model.encode(
                texts,
                show_progress_bar=True,
                batch_size=32,
                convert_to_numpy=True
            )
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    def save_to_faiss(self, embeddings: np.ndarray, document_id: str) -> Dict[str, int]:
        """Save embeddings to FAISS index"""
        
        # Create or load FAISS index
        index_file = os.path.join(self.faiss_index_path, 'document_index.faiss')
        metadata_file = os.path.join(self.faiss_index_path, 'metadata.json')
        
        if os.path.exists(index_file):
            # Load existing index
            index = faiss.read_index(index_file)
            
            # Load metadata
            import json
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            # Create new index
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            metadata = {"id_to_chunk": {}, "next_id": 0}
        
        # Add embeddings to index
        start_id = metadata["next_id"]
        index.add(embeddings)
        
        # Update metadata
        for i, embedding_id in enumerate(range(start_id, start_id + len(embeddings))):
            metadata["id_to_chunk"][str(embedding_id)] = {
                "document_id": document_id,
                "chunk_index": i
            }
        
        metadata["next_id"] = start_id + len(embeddings)
        
        # Save index and metadata
        faiss.write_index(index, index_file)
        import json
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)
        
        logger.info(f"Saved {len(embeddings)} embeddings to FAISS for document {document_id}")
        
        return {"start_id": start_id, "end_id": start_id + len(embeddings) - 1}
    
    def process_document(self, document: Document) -> bool:
        """Complete document processing pipeline"""
        
        try:
            # Update status
            document.status = 'processing'
            document.processing_progress = 10
            document.save()
            
            # Extract text
            file_path = document.file.path
            text, metadata = self.extract_text_from_file(file_path, document.file_type)
            
            # Update document metadata
            document.page_count = metadata.get('page_count', 0)
            document.word_count = metadata.get('word_count', 0)
            document.processing_progress = 30
            document.save()
            
            # Create chunks
            chunks_data = self.create_chunks(text, str(document.id))
            document.processing_progress = 50
            document.save()
            
            # Generate embeddings
            chunk_texts = [chunk["content"] for chunk in chunks_data]
            embeddings = self.generate_embeddings(chunk_texts)
            document.processing_progress = 70
            document.save()
            
            # Save to FAISS
            faiss_info = self.save_to_faiss(embeddings, str(document.id))
            document.processing_progress = 90
            document.save()
            
            # Save chunks to database
            chunk_objects = []
            for i, chunk_data in enumerate(chunks_data):
                chunk_objects.append(DocumentChunk(
                    document=document,
                    content=chunk_data["content"],
                    chunk_index=chunk_data["chunk_index"],
                    chunk_size=chunk_data["chunk_size"],
                    faiss_index=faiss_info["start_id"] + i,
                    embedding_model=settings.EMBEDDING_MODEL
                ))
            
            DocumentChunk.objects.bulk_create(chunk_objects)
            document.chunk_count = len(chunk_objects)
            
            # Mark as processed
            document.mark_as_processed()
            document.is_indexed = True
            document.embedding_model = settings.EMBEDDING_MODEL
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

class FAISSSearchService:
    """FAISS-powered semantic search service"""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.faiss_index_path = settings.FAISS_INDEX_PATH
    
    def search_documents(self, query: str, k: int = 5, user_documents: List[str] = None) -> List[Dict[str, Any]]:
        """Search documents using FAISS semantic search"""
        
        try:
            # Load FAISS index
            index_file = os.path.join(self.faiss_index_path, 'document_index.faiss')
            metadata_file = os.path.join(self.faiss_index_path, 'metadata.json')
            
            if not os.path.exists(index_file):
                logger.warning("No FAISS index found")
                return []
            
            index = faiss.read_index(index_file)
            
            import json
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])
            
            # Search FAISS index
            scores, indices = index.search(query_embedding, k * 2)  # Get more results to filter
            
            # Process results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # No more results
                    break
                
                chunk_meta = metadata["id_to_chunk"].get(str(idx))
                if not chunk_meta:
                    continue
                
                # Filter by user documents if specified
                if user_documents and chunk_meta["document_id"] not in user_documents:
                    continue
                
                try:
                    # Get document chunk
                    chunk = DocumentChunk.objects.get(
                        document_id=chunk_meta["document_id"],
                        chunk_index=chunk_meta["chunk_index"]
                    )
                    
                    results.append({
                        "chunk": chunk,
                        "document": chunk.document,
                        "score": float(score),
                        "content": chunk.content,
                        "page_number": chunk.page_number,
                        "chunk_index": chunk.chunk_index
                    })
                    
                except DocumentChunk.DoesNotExist:
                    continue
            
            # Sort by relevance score and limit results
            results = sorted(results, key=lambda x: x["score"], reverse=True)[:k]
            
            logger.info(f"Found {len(results)} relevant chunks for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return []
    
    def get_document_stats(self) -> Dict[str, Any]:
        """Get FAISS index statistics"""
        try:
            index_file = os.path.join(self.faiss_index_path, 'document_index.faiss')
            if os.path.exists(index_file):
                index = faiss.read_index(index_file)
                return {
                    "total_vectors": index.ntotal,
                    "dimension": index.d,
                    "index_type": type(index).__name__
                }
            return {"total_vectors": 0, "dimension": 0, "index_type": "None"}
        except Exception as e:
            logger.error(f"Error getting FAISS stats: {str(e)}")
            return {"total_vectors": 0, "dimension": 0, "index_type": "Error"}