from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, MessageViewSet

router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    path('', include(router.urls)),
]
