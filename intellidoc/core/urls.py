from django.urls import path
from .views import HomeView, AboutView, FeaturesView, PricingView

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('features/', FeaturesView.as_view(), name='features'),
    path('pricing/', PricingView.as_view(), name='pricing'),
]