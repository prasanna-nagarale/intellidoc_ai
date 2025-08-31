from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.ConversationListView.as_view(), name='chat_list'),
    path('new/', views.ConversationCreateView.as_view(), name='conversation_create'),
    path('<uuid:pk>/', views.ConversationDetailView.as_view(), name='conversation_detail'),
    path('<uuid:pk>/pin/', views.conversation_toggle_pin, name='conversation_pin'),
    path('<uuid:pk>/add-document/', views.add_document_to_conversation, name='add_document'),
]