# api/app/models/schemas.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

class DocumentUploadResponse(BaseModel):
    document_type: str = Field(..., description="Detected document type")
    confidence: float = Field(..., ge=0, le=1, description="Classification confidence score")
    entities: Dict[str, Any] = Field(..., description="Extracted entities")
    processing_time: str = Field(..., description="Total processing time")
    raw_text: Optional[str] = Field(None, description="Raw OCR text")

class DocumentClassification(BaseModel):
    document_type: str
    confidence: float
    similar_documents: List[Dict[str, Any]] = []

class EntityExtractionRequest(BaseModel):
    text: str
    document_type: str
    fields: List[str]

class EntityExtractionResponse(BaseModel):
    entities: Dict[str, Any]
    confidence_scores: Optional[Dict[str, float]] = None

class ErrorResponse(BaseModel):
    error: str
    detail: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ProcessingStats(BaseModel):
    ocr_time: float
    classification_time: float
    extraction_time: float
    total_time: float