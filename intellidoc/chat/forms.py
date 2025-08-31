from django import forms
from .models import Conversation
from documents.models import Document

class ConversationForm(forms.ModelForm):
    """Create/edit conversation form"""
    
    class Meta:
        model = Conversation
        fields = ['title', 'description', 'documents']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Conversation title (optional)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Optional description...',
                'rows': 3
            }),
            'documents': forms.CheckboxSelectMultiple(attrs={
                'class': 'space-y-2'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter documents to user's ready documents
        if self.user:
            self.fields['documents'].queryset = Document.objects.filter(
                owner=self.user,
                status='ready'
            )