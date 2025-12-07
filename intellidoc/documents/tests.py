from django.test import TestCase

# Create your tests here.
# documents/tasks.py

from .services import DocumentProcessor, FAISSSearchService

def process_document_task(content):
    processor = DocumentProcessor(content)
    processed_content = processor.process()
    return processed_content
