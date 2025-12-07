# accounts/views.py - COMPLETE AUTHENTICATION VIEWS

from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from .models import User
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from documents.models import Document, DocumentCollection
from django.conf import settings
from django.shortcuts import resolve_url

class RegisterView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = "accounts/register.html"

    def form_valid(self, form):
        user = form.save()
        raw_password = form.cleaned_data.get("password1")

        # authenticate directly with email
        user = authenticate(self.request, email=user.email, password=raw_password)
        if user:
            login(self.request, user)
            messages.success(self.request, "Welcome to IntelliDoc AI 🎉")
            return redirect("accounts:dashboard")

        return super().form_valid(form)


class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = "accounts/login.html"

    def get_success_url(self):
        return self.get_redirect_url() or resolve_url(settings.LOGIN_REDIRECT_URL)


class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile view with stats"""
    
    template_name = 'accounts/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # User statistics
        context['stats'] = {
            'documents_count': Document.objects.filter(owner=user).exclude(status='deleted').count(),
            'ready_documents': Document.objects.filter(owner=user, status='ready').count(),
            'total_storage': Document.objects.filter(owner=user).exclude(status='deleted').aggregate(
                total=Sum('file_size'))['total'] or 0,
            'total_queries': user.queries_made,
            'collections_count': DocumentCollection.objects.filter(owner=user).count(),
        }
        
        # Recent activity
        context['recent_documents'] = Document.objects.filter(
            owner=user
        ).exclude(status='deleted').order_by('-uploaded_at')[:5]
        
        # Plan limits
        context['plan_limits'] = user.get_plan_limits()
        
        return context

class DashboardView(LoginRequiredMixin, TemplateView):
    """Main user dashboard with analytics"""
    
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Time-based stats
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Document stats over time
        context['weekly_uploads'] = Document.objects.filter(
            owner=user,
            uploaded_at__gte=week_ago
        ).exclude(status='deleted').count()
        
        context['monthly_uploads'] = Document.objects.filter(
            owner=user,
            uploaded_at__gte=month_ago
        ).exclude(status='deleted').count()
        
        # Processing status breakdown
        context['status_breakdown'] = {
            'ready': Document.objects.filter(owner=user, status='ready').count(),
            'processing': Document.objects.filter(owner=user, status='processing').count(),
            'error': Document.objects.filter(owner=user, status='error').count(),
        }
        
        # Most accessed documents
        context['popular_documents'] = Document.objects.filter(
            owner=user,
            status='ready'
        ).order_by('-query_count', '-view_count')[:5]
        
        # Storage usage by file type
        from django.db.models import Sum, Case, When, CharField
        context['storage_by_type'] = Document.objects.filter(
            owner=user
        ).exclude(status='deleted').values('file_type').annotate(
            total_size=Sum('file_size'),
            count=Count('id')
        ).order_by('-total_size')
        
        return context

class UserSettingsView(LoginRequiredMixin, TemplateView):
    """User settings and preferences"""
    
    template_name = 'accounts/settings.html'
    
    def post(self, request, *args, **kwargs):
        # Handle settings updates via HTMX
        setting = request.POST.get('setting')
        value = request.POST.get('value')
        
        if setting == 'email_notifications':
            request.user.email_notifications = value.lower() == 'true'
            request.user.save(update_fields=['email_notifications'])
            
        elif setting == 'dark_mode':
            request.user.dark_mode = value.lower() == 'true'
            request.user.save(update_fields=['dark_mode'])
        
        return JsonResponse({'success': True})

class UpgradePlanView(LoginRequiredMixin, TemplateView):
    """Plan upgrade page"""
    
    template_name = 'accounts/upgrade.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Plan comparison
        context['plans'] = {
            'free': {
                'name': 'Free',
                'price': '$0',
                'features': [
                    '10 documents',
                    '100MB storage', 
                    '100 AI queries/month',
                    'Basic support'
                ]
            },
            'pro': {
                'name': 'Pro',
                'price': '$19',
                'features': [
                    '100 documents',
                    '1GB storage',
                    '1000 AI queries/month',
                    'Priority support',
                    'API access',
                    'Advanced analytics'
                ]
            },
            'enterprise': {
                'name': 'Enterprise',
                'price': '$99',
                'features': [
                    'Unlimited documents',
                    'Unlimited storage',
                    'Unlimited AI queries',
                    '24/7 dedicated support',
                    'Custom integrations',
                    'White-label option',
                    'On-premise deployment'
                ]
            }
        }
        
        context['current_plan'] = self.request.user.plan
        
        return context