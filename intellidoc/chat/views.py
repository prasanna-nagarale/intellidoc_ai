from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, CreateView, DetailView
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone

from .models import Conversation, Message
from .forms import ConversationForm
from documents.models import Document

class ConversationListView(LoginRequiredMixin, ListView):
    """List user's chat conversations"""
    
    model = Conversation
    template_name = 'chat/conversation_list.html'
    context_object_name = 'conversations'
    paginate_by = 20
    
    def get_queryset(self):
        return Conversation.objects.filter(
            user=self.request.user
        ).prefetch_related('documents')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        context['stats'] = {
            'total_conversations': self.get_queryset().count(),
            'pinned_conversations': self.get_queryset().filter(is_pinned=True).count(),
            'total_messages': Message.objects.filter(
                conversation__user=self.request.user
            ).count()
        }
        
        return context

class ConversationCreateView(LoginRequiredMixin, CreateView):
    """Create new conversation"""
    
    model = Conversation
    form_class = ConversationForm
    template_name = 'chat/conversation_form.html'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        
        # Auto-generate title if not provided
        if not form.instance.title:
            form.instance.title = f"Chat {timezone.now().strftime('%Y-%m-%d %H:%M')}"
        
        response = super().form_valid(form)
        
        messages.success(self.request, 'New conversation started! 💬')
        return response
    
    def get_success_url(self):
        return reverse_lazy('chat:conversation_detail', kwargs={'pk': self.object.pk})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class ConversationDetailView(LoginRequiredMixin, DetailView):
    """Chat conversation interface"""
    
    model = Conversation
    template_name = 'chat/conversation_detail.html'
    context_object_name = 'conversation'
    
    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get messages with pagination
        messages = self.object.messages.all().order_by('created_at')
        context['messages'] = messages
        
        # Available documents for context
        context['available_documents'] = Document.objects.filter(
            owner=self.request.user,
            status='ready'
        )
        
        return context

@login_required
def conversation_toggle_pin(request, pk):
    """Toggle conversation pin status"""
    conversation = get_object_or_404(Conversation, pk=pk, user=request.user)
    
    conversation.is_pinned = not conversation.is_pinned
    conversation.save(update_fields=['is_pinned'])
    
    return JsonResponse({
        'success': True,
        'is_pinned': conversation.is_pinned,
        'message': '📌 Pinned' if conversation.is_pinned else '📌 Unpinned'
    })

@login_required  
def add_document_to_conversation(request, pk):
    """Add document to conversation context"""
    conversation = get_object_or_404(Conversation, pk=pk, user=request.user)
    
    if request.method == 'POST':
        document_id = request.POST.get('document_id')
        
        try:
            document = Document.objects.get(
                id=document_id,
                owner=request.user,
                status='ready'
            )
            
            conversation.documents.add(document)
            
            return JsonResponse({
                'success': True,
                'message': f'Added {document.title} to conversation'
            })
            
        except Document.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Document not found'
            }, status=404)
    
    return JsonResponse({'success': False}, status=405)
