# api/app/core/exceptions.py

class DocumentProcessingException(Exception):
    """Custom exception for document processing errors"""
    pass

class OCRException(Exception):
    """Custom exception for OCR processing errors"""
    pass

class ClassificationException(Exception):
    """Custom exception for document classification errors"""
    pass

class ExtractionException(Exception):
    """Custom exception for entity extraction errors"""
    pass

class VectorDBException(Exception):
    """Custom exception for vector database errors"""
    pass
