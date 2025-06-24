# api/app/services/classification_service.py
from typing import Dict, Any, List
from loguru import logger
from .vector_service import VectorService
from ..models.schemas import DocumentClassification
from ..core.config import settings

class DocumentClassificationService:
    def __init__(self):
        self.vector_service = VectorService()
        self.document_types = list(settings.DOCUMENT_TYPES.keys())
    
    async def classify_document(self, text: str) -> DocumentClassification:
        """Classify document type based on text content"""
        try:
            logger.info("Starting document classification")
            
            # Search for similar documents in vector database
            similar_docs = await self.vector_service.search_similar_documents(
                query_text=text,
                limit=10,
                score_threshold=0.3
            )
            
            if not similar_docs:
                # Fallback to keyword-based classification
                return await self._keyword_based_classification(text)
            
            # Analyze similar documents to determine type
            type_scores = self._calculate_type_scores(similar_docs)
            
            # Get the most likely document type
            best_type, confidence = self._get_best_classification(type_scores)
            
            return DocumentClassification(
                document_type=best_type,
                confidence=confidence,
                similar_documents=similar_docs[:3]  # Return top 3 similar docs
            )
            
        except Exception as e:
            logger.error(f"Document classification failed: {str(e)}")
            # Return default classification
            return DocumentClassification(
                document_type="unknown",
                confidence=0.0,
                similar_documents=[]
            )
    
    def _calculate_type_scores(self, similar_docs: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate weighted scores for each document type"""
        type_scores = {doc_type: 0.0 for doc_type in self.document_types}
        
        for doc in similar_docs:
            doc_type = doc.get("document_type", "unknown")
            score = doc.get("score", 0.0)
            
            if doc_type in type_scores:
                # Weight the score by similarity
                type_scores[doc_type] += score
        
        # Normalize scores
        total_score = sum(type_scores.values())
        if total_score > 0:
            type_scores = {k: v / total_score for k, v in type_scores.items()}
        
        return type_scores
    
    def _get_best_classification(self, type_scores: Dict[str, float]) -> tuple:
        """Get the best document type and confidence score"""
        if not any(type_scores.values()):
            return "unknown", 0.0
        
        best_type = max(type_scores, key=type_scores.get)
        confidence = type_scores[best_type]
        
        return best_type, confidence
    
    async def _keyword_based_classification(self, text: str) -> DocumentClassification:
        """Fallback keyword-based classification when vector search fails"""
        text_lower = text.lower()
        
        # Define keyword patterns for each document type
        keyword_patterns = {
            "invoice": [
                "invoice", "bill", "amount due", "total", "subtotal", 
                "tax", "payment terms", "vendor", "supplier"
            ],
            "receipt": [
                "receipt", "purchased", "store", "cashier", "thank you",
                "change", "payment method", "card", "cash"
            ],
            "contract": [
                "contract", "agreement", "party", "terms", "conditions",
                "signature", "effective date", "termination"
            ],
            "id_document": [
                "identification", "license", "passport", "id card",
                "date of birth", "expires", "issued by"
            ],
            "bank_statement": [
                "statement", "account", "balance", "transaction",
                "deposit", "withdrawal", "bank", "branch"
            ]
        }
        
        type_scores = {}
        
        for doc_type, keywords in keyword_patterns.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            
            # Normalize by number of keywords
            type_scores[doc_type] = score / len(keywords)
        
        best_type, confidence = self._get_best_classification(type_scores)
        
        # Lower confidence for keyword-based classification
        confidence = confidence * 0.6  # Reduce confidence factor
        
        logger.info(f"Keyword-based classification: {best_type} (confidence: {confidence:.2f})")
        
        return DocumentClassification(
            document_type=best_type if confidence > 0.1 else "unknown",
            confidence=confidence,
            similar_documents=[]
        )
    
    async def get_supported_document_types(self) -> List[str]:
        """Get list of supported document types"""
        return self.document_types
    
    async def get_classification_stats(self) -> Dict[str, Any]:
        """Get classification statistics from vector database"""
        try:
            distribution = await self.vector_service.get_document_type_distribution()
            
            return {
                "total_documents": sum(distribution.values()),
                "document_types": distribution,
                "supported_types": self.document_types
            }
            
        except Exception as e:
            logger.error(f"Error getting classification stats: {str(e)}")
            return {
                "total_documents": 0,
                "document_types": {},
                "supported_types": self.document_types
            }