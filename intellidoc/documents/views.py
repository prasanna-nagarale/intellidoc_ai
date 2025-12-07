import json
import logging
from typing import Dict, Any
from .tasks import process_document_task
from .services import DocumentProcessor, FAISSSearchService  # Add this line

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView, CreateView
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone

from .models import Document, DocumentCollection, DocumentChunk
from .forms import DocumentUploadForm, CollectionForm
from .tasks import process_document_task
from .services import FAISSSearchService

logger = logging.getLogger('intellidoc.documents')

class DocumentListView(LoginRequiredMixin, ListView):
    """Document dashboard with advanced filtering"""
    
    model = Document
    template_name = 'documents/list.html'
    context_object_name = 'documents'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Document.objects.filter(
            owner=self.request.user
        ).exclude(status='deleted').order_by('-uploaded_at')
        
        # Search filter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search)
            )
        
        # Status filter
        status = self.request.GET.get('status')
        if status and status != 'all':
            queryset = queryset.filter(status=status)
        
        # Collection filter
        collection_id = self.request.GET.get('collection')
        if collection_id:
            queryset = queryset.filter(collections__id=collection_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add collections
        context['collections'] = DocumentCollection.objects.filter(
            owner=self.request.user
        ).annotate(doc_count=Count('documents'))
        
        # Add statistics
        user_docs = Document.objects.filter(owner=self.request.user).exclude(status='deleted')
        context['stats'] = {
            'total_documents': user_docs.count(),
            'ready_documents': user_docs.filter(status='ready').count(),
            'processing_documents': user_docs.filter(status='processing').count(),
            'total_storage': sum(doc.file_size for doc in user_docs),
            'total_queries': sum(doc.query_count for doc in user_docs),
        }
        
        # Add current filters for template
        context['current_search'] = self.request.GET.get('search', '')
        context['current_status'] = self.request.GET.get('status', 'all')
        context['current_collection'] = self.request.GET.get('collection', '')
        
        return context

@login_required
@require_http_methods(["GET", "POST"])
def document_upload_view(request):
    """HTMX-powered document upload with real-time feedback"""
    
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES, user=request.user)
        
        if form.is_valid():
            if not request.user.can_upload_document():
                return JsonResponse(
                    {"error": "Upgrade your plan to upload more documents"}, status=403
                )

            document = form.save(commit=False)
            document.owner = request.user
            
            # Determine file type
            file_ext = document.file.name.split('.')[-1].lower()
            type_mapping = {
                'pdf': 'pdf',
                'docx': 'docx', 
                'doc': 'docx',
                'txt': 'txt',
                'md': 'md'
            }
            document.file_type = type_mapping.get(file_ext, 'txt')
            document.file_size = document.file.size
            
            document.save()
            
            # Add to default collection if exists
            default_collection, created = DocumentCollection.objects.get_or_create(
                owner=request.user,
                name="My Documents",
                defaults={"is_default": True}
            )
            document.collections.add(default_collection)
            
            # Start background processing
            process_document_task.delay(str(document.id), request.user.id)
            
            # HTMX response
            if request.headers.get('HX-Request'):
                return render(request, 'documents/upload_success.html', {
        'document': document
    })
            else:
                messages.success(request, f'Document "{document.title}" uploaded successfully!')
                return redirect('documents:list')
        
        else:
            # HTMX error response
            if request.headers.get('HX-Request'):
                return render(request, 'documents/upload_form.html', {
                    'form': form
                })
    
    else:
        form = DocumentUploadForm(user=request.user)
    
    # ✅ Always send recent uploads to the template
    recent_uploads = Document.objects.filter(owner=request.user)\
        .exclude(status='deleted')\
        .order_by('-uploaded_at')[:5]

    return render(request, 'documents/upload.html', {
        'form': form,
        'recent_uploads': recent_uploads
    })


@login_required
@require_http_methods(["GET"])
def document_search_view(request):
    """Real-time document search with HTMX"""
    
    query = request.GET.get('q', '').strip()
    
    if not query:
        documents = Document.objects.filter(
            owner=request.user,
            status='ready'
        ).order_by('-last_accessed')[:6]
        
        return render(request, 'documents/search_results.html', {
            'documents': documents,
            'query': query
        })
    
    # Semantic search using FAISS
    search_service = FAISSSearchService()
    user_document_ids = list(
        Document.objects.filter(owner=request.user, status='ready')
        .values_list('id', flat=True)
    )
    
    search_results = search_service.search_documents(
        query=query,
        k=10,
        user_documents=[str(doc_id) for doc_id in user_document_ids]
    )
    
    # Group results by document
    documents_dict = {}
    for result in search_results:
        doc_id = str(result["document"].id)
        if doc_id not in documents_dict:
            documents_dict[doc_id] = {
                "document": result["document"],
                "chunks": [],
                "max_score": result["score"]
            }
        documents_dict[doc_id]["chunks"].append(result)
    
    return render(request, 'documents/search_results.html', {
        'search_results': list(documents_dict.values()),
        'query': query,
        'total_results': len(search_results)
    })

@login_required
def document_detail_view(request, document_id):
    """Document detail view with chunk exploration"""
    
    document = get_object_or_404(
        Document,
        id=document_id,
        owner=request.user
    )
    
    # Increment view count
    document.increment_view_count()
    
    # Get document chunks
    chunks = DocumentChunk.objects.filter(document=document).order_by('chunk_index')
    
    # Pagination for chunks
    paginator = Paginator(chunks, 10)
    page_number = request.GET.get('page')
    chunks_page = paginator.get_page(page_number)
    
    context = {
        'document': document,
        'chunks': chunks_page,
        'total_chunks': chunks.count(),
    }
    
    return render(request, 'documents/detail.html', context)

@login_required
@require_http_methods(["DELETE"])
def document_delete_view(request, document_id):
    """Delete document with HTMX"""
    
    document = get_object_or_404(
        Document,
        id=document_id,
        owner=request.user
    )
    
    # Update user storage
    request.user.update_usage(storage_delta=-document.file_size)
    
    # Soft delete
    document.status = 'deleted'
    document.save()
    
    if request.headers.get('HX-Request'):
        return HttpResponse('')  # HTMX will remove the element
    
    messages.success(request, f'Document "{document.title}" deleted successfully!')
    return redirect('documents:list')

@login_required
def collection_create_view(request):
    """Create new document collection"""
    
    if request.method == 'POST':
        form = CollectionForm(request.POST, user=request.user)
        
        if form.is_valid():
            collection = form.save(commit=False)
            collection.owner = request.user
            collection.save()
            
            if request.headers.get('HX-Request'):
                return render(request, 'documents/collection_item.html', {
                    'collection': collection
                })
            
            messages.success(request, f'Collection "{collection.name}" created!')
            return redirect('documents:list')
    
    else:
        form = CollectionForm(user=request.user)
    
    return render(request, 'documents/collection_form.html', {'form': form})

@login_required
def document_processing_status(request, document_id):
    """Get real-time processing status"""
    
    document = get_object_or_404(
        Document,
        id=document_id,
        owner=request.user
    )
    
    return JsonResponse({
        'status': document.status,
        'progress': document.processing_progress,
        'error_message': document.error_message,
        'chunk_count': document.chunk_count,
        'word_count': document.word_count,
        'is_indexed': document.is_indexed
    })

@login_required
@require_http_methods(["POST"])
def validate_title(request):
    """HTMX endpoint for real-time title validation"""
    title = request.POST.get('title', '').strip()
    
    if not title:
        return HttpResponse('')
    
    # Check for duplicate titles
    if Document.objects.filter(owner=request.user, title=title).exists():
        return HttpResponse(
            '<div class="text-red-500 text-sm mt-1">A document with this title already exists</div>'
        )
    
    return HttpResponse(
        '<div class="text-green-500 text-sm mt-1">✓ Title is available</div>'
    )

@login_required
@require_http_methods(["POST"])
def validate_file(request):
    """HTMX endpoint for file validation"""
    file = request.FILES.get('file')
    
    if not file:
        return HttpResponse('')
    
    # File size check
    max_size = 50 * 1024 * 1024  # 50MB
    if file.size > max_size:
        return HttpResponse(
            f'<div class="text-red-500 text-sm mt-1">❌ File too large. Maximum size is {max_size // (1024*1024)}MB</div>'
        )
    
    # User limits check
    can_upload, message = request.user.can_upload_document(file.size)
    if not can_upload:
        return HttpResponse(
            f'<div class="text-red-500 text-sm mt-1">❌ {message}</div>'
        )
    
    return HttpResponse(
        f'<div class="text-green-500 text-sm mt-1">✓ File is valid ({file.size // 1024} KB)</div>'
    )

@login_required
@require_http_methods(["POST"])
def bulk_delete_documents(request):
    """Bulk delete documents with HTMX"""
    document_ids = request.POST.getlist('document_ids')
    
    if not document_ids:
        return JsonResponse({'error': 'No documents selected'}, status=400)
    
    # Get user documents
    documents = Document.objects.filter(
        id__in=document_ids,
        owner=request.user
    ).exclude(status='deleted')
    
    # Calculate storage to free up
    total_storage = sum(doc.file_size for doc in documents)
    
    # Soft delete documents
    documents.update(status='deleted')
    
    # Update user storage
    request.user.update_usage(storage_delta=-total_storage)
    
    return JsonResponse({
        'success': True,
        'deleted_count': documents.count(),
        'message': f'Successfully deleted {documents.count()} documents'
    })

@login_required
@require_http_methods(["POST"])
def bulk_add_to_collection(request):
    """Bulk add documents to collection"""
    document_ids = request.POST.getlist('document_ids')
    collection_id = request.POST.get('collection_id')
    
    if not document_ids or not collection_id:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        collection = DocumentCollection.objects.get(
            id=collection_id,
            owner=request.user
        )
        
        documents = Document.objects.filter(
            id__in=document_ids,
            owner=request.user
        ).exclude(status='deleted')
        
        # Add documents to collection
        collection.documents.add(*documents)
        
        return JsonResponse({
            'success': True,
            'added_count': documents.count(),
            'message': f'Added {documents.count()} documents to {collection.name}'
        })
        
    except DocumentCollection.DoesNotExist:
        return JsonResponse({'error': 'Collection not found'}, status=404)