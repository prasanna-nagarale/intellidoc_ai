# intellidoc/core/views.py
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic.base import RedirectView
from django.apps import apps
from django.urls import reverse
from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Landing page with features showcase"""
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['demo_stats'] = {
            'documents_processed': '10,000+',
            'queries_answered': '50,000+',
            'active_users': '1,000+',
            'accuracy_rate': '98%'
        }
        return context



class AboutView(TemplateView):
    template_name = 'core/about.html'


class FeaturesView(TemplateView):
    template_name = 'core/features.html'


class PricingView(TemplateView):
    template_name = 'core/pricing.html'


@method_decorator(login_required, name='dispatch')
class DashboardView(TemplateView):
    """
    Dashboard should supply exactly the context your dashboard.html expects:
      - stats.total_documents
      - stats.total_chats
      - stats.total_chunks
      - recent_documents
      - user usage is provided via context processor (user wrapper)
    """
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Try to resolve models dynamically (safe if apps not yet implemented)
        def safe_model(app_label, model_name):
            try:
                return apps.get_model(app_label, model_name)
            except Exception:
                return None

        Document = safe_model('documents', 'Document')
        DocumentChunk = safe_model('documents', 'DocumentChunk')
        ChatSession = safe_model('chat', 'ChatSession') or safe_model('chat', 'Chat')

        user = self.request.user

        # If the models exist, scope them to the current user if owner exists
        def scoped_qs(Model):
            if not Model:
                return None
            # attempt common owner field name
            if hasattr(Model, 'objects'):
                qs = Model.objects.all()
                if hasattr(Model, 'owner') or hasattr(Model, 'user'):
                    # prefer owner, else user foreign key
                    if 'owner' in [f.name for f in Model._meta.fields]:
                        qs = qs.filter(owner=user)
                    elif 'user' in [f.name for f in Model._meta.fields]:
                        qs = qs.filter(user=user)
                return qs
            return None

        docs_qs = scoped_qs(Document) or []
        chats_qs = scoped_qs(ChatSession) or []
        chunks_qs = None
        if DocumentChunk and docs_qs is not None:
            try:
                chunks_qs = DocumentChunk.objects.filter(document__in=docs_qs)
            except Exception:
                chunks_qs = None

        context['stats'] = {
    'total_documents': docs_qs.count() if not isinstance(docs_qs, list) else len(docs_qs),
    'total_chats': chats_qs.count() if not isinstance(chats_qs, list) else len(chats_qs),
    'total_chunks': chunks_qs.count() if hasattr(chunks_qs, 'count') else (len(chunks_qs) if chunks_qs else 0),
}


        # recent documents (limit to 9)
        if hasattr(docs_qs, 'order_by'):
            try:
                context['recent_documents'] = docs_qs.order_by('-created_at')[:9]
            except Exception:
                context['recent_documents'] = docs_qs[:9]
        else:
            context['recent_documents'] = []

        return context


# ---- Small redirect shims so your current templates keep working without changing them ----
# These are temporary and can be removed once chat/documents apps expose matching namespaced routes.

class ChatIndexRedirectView(RedirectView):
    permanent = False
    pattern_name = 'chat:list'  # expects chat app to have name 'chat' and route name 'index'


class ChatCreateRedirectView(RedirectView):
    permanent = False
    pattern_name = 'chat:create'


def chat_message_redirect(request, chat_id):
    """
    Redirect function for older templates that call core:chat_message.
    This forwards to 'chat:message' and preserves chat_id.
    """
    return redirect('chat:message', chat_id=chat_id)


class DocumentUploadRedirectView(RedirectView):
    permanent = False
    pattern_name = 'documents:upload'


class DocumentListRedirectView(RedirectView):
    permanent = False
    pattern_name = 'documents:list'


class DocumentUploadView(TemplateView):
    template_name = "core/document_upload.html"