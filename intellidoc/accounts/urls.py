from django.urls import path
from django.contrib.auth.views import LogoutView

from .views import (
    RegisterView,
    CustomLoginView,
    ProfileView,
    ProfileEditView,
    DashboardView,
    UserSettingsView,
    UpgradePlanView,
)

app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/edit/', ProfileEditView.as_view(), name='profile_edit'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('settings/', UserSettingsView.as_view(), name='settings'),
    path('upgrade/', UpgradePlanView.as_view(), name='upgrade'),
]