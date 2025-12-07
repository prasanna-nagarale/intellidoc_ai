# chat/urls.py
from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.ConversationListView.as_view(), name='list'),
    path('create/', views.ConversationCreateView.as_view(), name='create'),   # used by template to create a new chat
    path('<uuid:pk>/', views.ConversationDetailView.as_view(), name='detail'),
    path('<uuid:pk>/pin/', views.conversation_toggle_pin, name='pin'),
    path('<uuid:pk>/add-document/', views.add_document_to_conversation, name='add_document'),
    path("<int:pk>/message/", views.chat_message, name="chat_message"), # HTMX -> returns rendered snippet
]
