# api/app/core/config.py
from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # API Settings
    API_TITLE: str = "Intelligent Document Understanding API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Extract structured information from unstructured documents"
    
    # Marqo Settings
    MARQO_URL: str = "http://localhost:8882"
    MARQO_INDEX_NAME: str = "document-types"
    
    # OCR Settings
    TESSERACT_CMD: str = "tesseract"  # Will be overridden in Docker
    OCR_CONFIG: str = "--oem 3 --psm 6"
    
    # LLM Settings
    OPENAI_API_KEY: str = ""
    DEFAULT_LLM_MODEL: str = "gpt-3.5-turbo"
    
    # File Settings
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"]
    UPLOAD_DIR: str = "uploads"
    
    # Document Types and Fields
    DOCUMENT_TYPES: dict = {
        "invoice": [
            "invoice_number", "date", "due_date", "total_amount", 
            "vendor_name", "vendor_address", "customer_name", "customer_address"
        ],
        "receipt": [
            "store_name", "date", "total_amount", "items", "payment_method"
        ],
        "contract": [
            "contract_number", "parties", "start_date", "end_date", 
            "contract_value", "terms"
        ],
        "id_document": [
            "full_name", "id_number", "date_of_birth", "expiry_date", 
            "issuing_authority"
        ],
        "bank_statement": [
            "account_number", "statement_period", "opening_balance", 
            "closing_balance", "bank_name"
        ]
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()