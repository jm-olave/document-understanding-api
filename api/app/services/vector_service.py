# api/app/services/vector_service.py
import marqo
from typing import List, Dict, Any
from loguru import logger
import uuid
import time
from ..core.config import settings
import asyncio

class VectorService:
    def __init__(self):
        self.client = marqo.Client(url=settings.MARQO_URL)
        self.index_name = settings.MARQO_INDEX_NAME
        self._index_ready = False
        # Don't block startup - initialize index asynchronously
        self._ensure_index_exists()
    
    def _ensure_index_exists(self):
        """Create index if it doesn't exist - non-blocking"""
        try:
            # Quick check if Marqo is available
            self.client.get_indexes()
            self._index_ready = True
            logger.info(f"Marqo connection successful, index {self.index_name} ready")
        except Exception as e:
            logger.warning(f"Marqo not ready during startup: {str(e)}")
            logger.info("API will continue without vector database functionality")
            self._index_ready = False
    
    async def _ensure_index_exists_async(self) -> bool:
        """Ensure the vector index exists, creating it if necessary."""
        try:
            if not self._index_ready:
                # Check if index exists
                try:
                    indexes = self.client.get_indexes()
                    if self.index_name not in [idx["indexName"] for idx in indexes.get("results", [])]:
                        # Create index with a smaller model that requires less memory
                        self.client.create_index(
                            self.index_name, 
                            model="hf/all_datasets_v4_MiniLM-L6"
                        )
                        logger.info(f"Created vector index: {self.index_name}")
                    else:
                        logger.info(f"Vector index already exists: {self.index_name}")
                    self._index_ready = True
                    return True
                except Exception as e:
                    logger.error(f"Error checking/creating vector index: {str(e)}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error in _ensure_index_exists_async: {str(e)}")
            return False
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Add documents to the vector database"""
        try:
            if not documents:
                logger.warning("No documents provided to add.")
                return False

            # Ensure index is ready
            if not await self._ensure_index_exists_async():
                logger.warning("Vector database not available - skipping document storage")
                return False

            logger.info(f"Preparing to add {len(documents)} documents to index")

            # Prepare documents for indexing, ensuring stable and unique IDs
            prepared_docs = []
            for doc in documents:
                # If an _id is provided in the doc, use it. Otherwise, generate one.
                # This makes the operation idempotent if the caller provides stable IDs.
                doc_id = doc.get("_id") or f"doc_{uuid.uuid4()}"

                prepared_doc = {
                    "_id": doc_id,
                    "content": doc.get("text", ""),
                    "document_type": doc.get("document_type", "unknown"),
                    "filename": doc.get("filename", "unknown_file"),
                    "metadata": doc.get("metadata", {})
                }
                prepared_docs.append(prepared_doc)

            # Add documents to Marqo
            response = self.client.index(self.index_name).add_documents(
                prepared_docs,
                tensor_fields=["content"],
                device="cpu" # Specify device for broader compatibility
            )

            if response.get("errors"):
                logger.error(f"Errors occurred during indexing: {response['errors']}")
                # Optionally raise an exception here
                # raise Exception("Failed to index some documents")

            logger.info(f"Successfully requested indexing for {len(documents)} documents")
            return not response.get("errors", False)

        except Exception as e:
            logger.error(f"Error adding documents to vector DB: {str(e)}")
            # Don't raise the exception, just log it and return False
            return False
    
    async def search_similar_documents(
        self, 
        query_text: str, 
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar documents in the vector database"""
        try:
            # Ensure index is ready
            if not await self._ensure_index_exists_async():
                logger.warning("Vector database not available - returning empty results")
                return []
                
            logger.info(f"Searching for similar documents with query length: {len(query_text)}")
            
            # Perform semantic search
            results = self.client.index(self.index_name).search(
                q=query_text,
                limit=limit,
                searchable_attributes=["content"]
            )
            
            # Filter and format results
            filtered_results = []
            for hit in results['hits']:
                score = hit.get('_score', 0)
                if score >= score_threshold:
                    filtered_results.append({
                        "document_type": hit.get("document_type", "unknown"),
                        "score": score,
                        "filename": hit.get("filename", ""),
                        "content_preview": hit.get("content", "")[:200] + "...",
                        "metadata": hit.get("metadata", {})
                    })
            
            logger.info(f"Found {len(filtered_results)} relevant documents")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error searching vector DB: {str(e)}")
            return []
    
    async def get_document_type_distribution(self) -> Dict[str, int]:
        """Get distribution of document types in the database"""
        try:
            # Ensure index is ready
            if not await self._ensure_index_exists_async():
                logger.warning("Vector database not available - returning empty distribution")
                return {}
                
            # Search all documents
            results = self.client.index(self.index_name).search(
                q="*",
                limit=1000,
                searchable_attributes=["content"]
            )
            
            # Count document types
            type_counts = {}
            for hit in results['hits']:
                doc_type = hit.get("document_type", "unknown")
                type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            
            return type_counts
            
        except Exception as e:
            logger.error(f"Error getting document type distribution: {str(e)}")
            return {}
    
    async def delete_index(self):
        """Delete the entire index (for testing/reset purposes)"""
        try:
            self.client.delete_index(self.index_name)
            logger.info(f"Index {self.index_name} deleted successfully")
        except Exception as e:
            logger.error(f"Error deleting index: {str(e)}")
            raise
