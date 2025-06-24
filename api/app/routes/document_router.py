from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
import time
from typing import List
from loguru import logger

from ..services.ocr_service import OCRService
from ..services.classification_service import DocumentClassificationService
from ..services.extraction_service import EntityExtractionService
from ..services.vector_service import VectorService
from ..models.schemas import (
    DocumentUploadResponse, 
    DocumentClassification,
    EntityExtractionRequest,
    EntityExtractionResponse,
    ProcessingStats
)
from ..core.config import settings
from ..core.exceptions import DocumentProcessingException

router = APIRouter()

# Initialize services
ocr_service = OCRService()
classification_service = DocumentClassificationService()
extraction_service = EntityExtractionService()
vector_service = VectorService()

@router.post("/extract_entities", response_model=DocumentUploadResponse)
async def extract_entities_from_document(
    file: UploadFile = File(...),
    include_raw_text: bool = False
):
    """
    Extract entities from an uploaded document (full pipeline: OCR, classification, entity extraction, storage).
    
    - **file**: Document file (PDF, PNG, JPG, JPEG, TIFF, BMP)
    - **include_raw_text**: Whether to include raw OCR text in response
    """
    try:
        start_time = time.time()
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        file_extension = file.filename.lower().split('.')[-1]
        if f".{file_extension}" not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"File type not supported. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )
        
        # Read file content
        file_content = await file.read()
        if len(file_content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Max size: {settings.MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Step 1: OCR Processing
        ocr_start = time.time()
        logger.info(f"Starting OCR for file: {file.filename}")
        raw_text = await ocr_service.extract_text_from_file(file_content, file.filename)
        ocr_time = time.time() - ocr_start
        
        if not raw_text.strip():
            raise DocumentProcessingException("No text could be extracted from the document")
        
        # Step 2: Document Classification
        classification_start = time.time()
        logger.info("Starting document classification")
        classification = await classification_service.classify_document(raw_text)
        classification_time = time.time() - classification_start
        
        # Step 3: Entity Extraction
        extraction_start = time.time()
        logger.info(f"Starting entity extraction for type: {classification.document_type}")
        extraction_result = await extraction_service.extract_entities(
            raw_text, 
            classification.document_type
        )
        extraction_time = time.time() - extraction_start
        
        # Step 4: Store in vector database (optional)
        try:
            await vector_service.add_documents([{
                "text": raw_text,
                "document_type": classification.document_type,
                "filename": file.filename,
                "metadata": {
                    "confidence": classification.confidence,
                    "entities": extraction_result.entities
                }
            }])
        except Exception as e:
            logger.warning(f"Failed to store document in vector DB: {str(e)}")
        
        total_time = time.time() - start_time
        
        # Prepare response
        response_data = {
            "document_type": classification.document_type,
            "confidence": classification.confidence,
            "entities": extraction_result.entities,
            "processing_time": f"{total_time:.2f}s",
            "processing_stats": ProcessingStats(
                ocr_time=ocr_time,
                classification_time=classification_time,
                extraction_time=extraction_time,
                total_time=total_time
            ).dict()
        }
        
        if include_raw_text:
            response_data["raw_text"] = raw_text
        
        if classification.similar_documents:
            response_data["similar_documents"] = classification.similar_documents
        
        logger.info(f"Document processing completed in {total_time:.2f}s")
        
        return DocumentUploadResponse(**response_data)
        
    except DocumentProcessingException as e:
        logger.error(f"Document processing error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/classify", response_model=DocumentClassification)
async def classify_document_text(text: str = Form(...)):
    """
    Classify document type from text content
    """
    try:
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text content is required")
        
        classification = await classification_service.classify_document(text)
        return classification
        
    except Exception as e:
        logger.error(f"Classification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Classification failed")

@router.post("/extract", response_model=EntityExtractionResponse)
async def extract_entities(request: EntityExtractionRequest):
    """
    Extract entities from text for a specific document type
    """
    try:
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text content is required")
        
        if not request.document_type:
            raise HTTPException(status_code=400, detail="Document type is required")
        
        result = await extraction_service.extract_entities(
            request.text, 
            request.document_type
        )
        return result
        
    except Exception as e:
        logger.error(f"Entity extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail="Entity extraction failed")

@router.get("/types")
async def get_supported_document_types():
    """
    Get list of supported document types and their fields
    """
    try:
        return {
            "document_types": settings.DOCUMENT_TYPES,
            "supported_types": list(settings.DOCUMENT_TYPES.keys())
        }
    except Exception as e:
        logger.error(f"Error getting document types: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get document types")

@router.get("/stats")
async def get_processing_stats():
    """
    Get processing statistics and document type distribution
    """
    try:
        stats = await classification_service.get_classification_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")

@router.delete("/vector-db")
async def clear_vector_database():
    """
    Clear the vector database (for testing/reset purposes)
    """
    try:
        await vector_service.delete_index()
        return {"message": "Vector database cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing vector DB: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear vector database")

@router.get("/vector-db-status")
async def check_vector_db_status():
    """
    Check the status of the vector database connection
    """
    try:
        # Try to connect to Marqo and get indexes
        is_connected = await vector_service._ensure_index_exists_async()
        if is_connected:
            indexes = vector_service.client.get_indexes()
            return {
                "status": "connected",
                "indexes": indexes,
                "index_name": vector_service.index_name,
                "index_ready": vector_service._index_ready
            }
        else:
            return {
                "status": "disconnected",
                "reason": "Failed to connect to Marqo after retries"
            }
    except Exception as e:
        logger.error(f"Error checking vector DB status: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
