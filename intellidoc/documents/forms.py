from django import forms
from django.core.exceptions import ValidationError
from .models import Document, DocumentCollection, validate_file_type


class DocumentUploadForm(forms.ModelForm):
    """Form for uploading and validating documents"""
    
    class Meta:
        model = Document
        fields = ['title', 'description', 'file']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter document title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Add an optional description',
                'rows': 3
            }),
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-file-input'
            })
        }

    # In DocumentUploadForm.__init__:
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add proper CSS classes
        self.fields['title'].widget.attrs.update({
            'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Enter document title'
        })
        self.fields['description'].widget.attrs.update({
            'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Brief description of the document content...',
            'rows': 3
        })

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if self.user and Document.objects.filter(owner=self.user, title=title, status__in=['uploading','processing','ready']).exists():
            raise ValidationError("You already have a document with this title.")
        return title

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            raise ValidationError("No file selected.")

        # File type validation
        validate_file_type(file)

        # Size validation (50 MB limit)
        max_size = 50 * 1024 * 1024
        if file.size > max_size:
            raise ValidationError(f"File too large. Maximum size is {max_size // (1024*1024)} MB.")

        # User quota check
        if self.user:
            can_upload, message = self.user.can_upload_document(file.size)
            if not can_upload:
                raise ValidationError(message)

        return file


class CollectionForm(forms.ModelForm):
    """Form for creating new document collections"""

    class Meta:
        model = DocumentCollection
        fields = ['name', 'description', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Collection name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Optional description',
                'rows': 2
            }),
            'color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-color-input'
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if self.user and DocumentCollection.objects.filter(owner=self.user, name=name).exists():
            raise ValidationError("You already have a collection with this name.")
        return name
