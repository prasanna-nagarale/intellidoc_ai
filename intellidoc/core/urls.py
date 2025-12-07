from django.urls import path
from . import views
from .views import (
    HomeView, AboutView, FeaturesView, PricingView,
    DashboardView,DocumentListRedirectView
)

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('features/', FeaturesView.as_view(), name='features'),
    path('pricing/', PricingView.as_view(), name='pricing'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
]