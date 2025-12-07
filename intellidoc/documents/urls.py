from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
    path('', views.DocumentListView.as_view(), name='list'),  # canonical
    path('upload/', views.document_upload_view, name='upload'),
    path('search/', views.document_search_view, name='search'),
    path('<uuid:document_id>/', views.document_detail_view, name='detail'),
    path('<uuid:document_id>/delete/', views.document_delete_view, name='delete'),
    path('collections/create/', views.collection_create_view, name='collection_create'),
    path('<uuid:document_id>/status/', views.document_processing_status, name='processing_status'),
    path('validate/title/', views.validate_title, name='validate_title'),
    path('validate/file/', views.validate_file, name='validate_file'),
    path('bulk/delete/', views.bulk_delete_documents, name='bulk_delete'),
    path('bulk/add-to-collection/', views.bulk_add_to_collection, name='bulk_add_to_collection'),
]
