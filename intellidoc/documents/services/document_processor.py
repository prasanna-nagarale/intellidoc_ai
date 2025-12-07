# documents/services/document_processor.py

class DocumentProcessor:
    def __init__(self, content):
        self.content = content

    def process(self):
        # Your document processing logic
        return self.content.lower()
