from django.db import models

# Create your models here.
def can_upload_document(self):
    if self.is_premium:
        return True
    return self.documents.count() < 5
