from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

class HomeView(TemplateView):
    """Landing page with features showcase"""
    
    template_name = 'core/home.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Redirect authenticated users to dashboard
        if request.user.is_authenticated:
            return redirect('documents:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Demo statistics (you can make these dynamic later)
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