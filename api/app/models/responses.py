from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List
from datetime import datetime

from .schemas import (
    DocumentUploadResponse,
    DocumentClassification,
    EntityExtractionResponse,
    EntityExtractionRequest,
    ErrorResponse,
    ProcessingStats,
)

class SuccessResponse(BaseModel):
    success: bool = Field(True, description="Indicates if the request was successful")
    message: Optional[str] = Field(None, description="Optional success message")
    data: Optional[Any] = Field(None, description="Payload data")

class APIErrorResponse(BaseModel):
    success: bool = Field(False, description="Indicates if the request failed")
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now)

# Utility functions for standardized responses
from fastapi.responses import JSONResponse

def success_response(data: Any = None, message: Optional[str] = None) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content=SuccessResponse(data=data, message=message).dict()
    )

def error_response(error: str, detail: Optional[str] = None, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=APIErrorResponse(error=error, detail=detail).dict()
    )

# Re-export main response models for convenience
__all__ = [
    "DocumentUploadResponse",
    "DocumentClassification",
    "EntityExtractionResponse",
    "EntityExtractionRequest",
    "ErrorResponse",
    "ProcessingStats",
    "SuccessResponse",
    "APIErrorResponse",
    "success_response",
    "error_response",
]
