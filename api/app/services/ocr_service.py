# api/app/services/ocr_service.py
import pytesseract
from PIL import Image
import pdf2image
import io
import os
from typing import Union, List
from loguru import logger
from ..core.config import settings

class OCRService:
    def __init__(self):
        # Set tesseract command path if in Docker
        if os.getenv('TESSERACT_CMD'):
            pytesseract.pytesseract.tesseract_cmd = os.getenv('TESSERACT_CMD')
    
    async def extract_text_from_file(self, file_content: bytes, filename: str) -> str:
        """Extract text from uploaded file (PDF or image)"""
        try:
            file_extension = os.path.splitext(filename.lower())[1]
            
            if file_extension == '.pdf':
                return await self._extract_from_pdf(file_content)
            elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                return await self._extract_from_image(file_content)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
                
        except Exception as e:
            logger.error(f"OCR extraction failed for {filename}: {str(e)}")
            raise
    
    async def _extract_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF file"""
        try:
            # Convert PDF to images
            images = pdf2image.convert_from_bytes(
                pdf_content,
                dpi=300,
                first_page=1,
                last_page=5  # Limit to first 5 pages for performance
            )
            
            extracted_texts = []
            for i, image in enumerate(images):
                logger.info(f"Processing PDF page {i+1}")
                text = pytesseract.image_to_string(
                    image, 
                    config=settings.OCR_CONFIG
                )
                if text.strip():
                    extracted_texts.append(text)
            
            return "\n\n".join(extracted_texts)
            
        except Exception as e:
            logger.error(f"PDF OCR failed: {str(e)}")
            raise
    
    async def _extract_from_image(self, image_content: bytes) -> str:
        """Extract text from image file"""
        try:
            # Open image from bytes
            image = Image.open(io.BytesIO(image_content))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(
                image, 
                config=settings.OCR_CONFIG
            )
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Image OCR failed: {str(e)}")
            raise
    
    def preprocess_text(self, text: str) -> str:
        """Clean and preprocess extracted text"""
        if not text:
            return ""
        
        # Basic text cleaning
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if len(line) > 2:  # Filter out very short lines
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    async def get_text_confidence(self, image_content: bytes) -> dict:
        """Get OCR confidence scores"""
        try:
            image = Image.open(io.BytesIO(image_content))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Get detailed OCR data
            data = pytesseract.image_to_data(
                image, 
                output_type=pytesseract.Output.DICT,
                config=settings.OCR_CONFIG
            )
            
            # Calculate confidence metrics
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "average_confidence": avg_confidence,
                "word_count": len(confidences),
                "low_confidence_words": len([c for c in confidences if c < 60])
            }
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {str(e)}")
            return {"average_confidence": 0, "word_count": 0, "low_confidence_words": 0}