# api/app/services/extraction_service.py
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
import json
import re
from typing import Dict, Any, List
from loguru import logger
from ..core.config import settings
from ..models.schemas import EntityExtractionResponse

class EntityExtractionService:
    def __init__(self):
        # Fix for LangChain compatibility - use proper initialization
        try:
            self.llm = ChatOpenAI(
                model=settings.DEFAULT_LLM_MODEL,
                temperature=0.1,
                api_key=settings.OPENAI_API_KEY
            )
        except Exception as e:
            logger.warning(f"Failed to initialize ChatOpenAI with new syntax: {e}")
            # Fallback to old syntax
            try:
                self.llm = ChatOpenAI(
                    model_name=settings.DEFAULT_LLM_MODEL,
                    temperature=0.1,
                    openai_api_key=settings.OPENAI_API_KEY
                )
            except Exception as e2:
                logger.error(f"Failed to initialize ChatOpenAI: {e2}")
                self.llm = None
        
        self.prompt_templates = self._create_prompt_templates()
    
    def _create_prompt_templates(self) -> Dict[str, PromptTemplate]:
        """Create prompt templates for different document types"""
        templates = {}
        
        base_template = """
You are an expert document analyzer. Extract specific information from the given document text.

Document Type: {document_type}
Required Fields: {field_list}

Instructions:
1. Extract ONLY the requested fields from the document
2. Return the information as a valid JSON object
3. Use null for fields that cannot be found or determined
4. Be precise and accurate with the extracted values
5. For dates, use YYYY-MM-DD format
6. For monetary amounts, include currency symbol

Document Text:
{document_text}

Return only the JSON object with no additional text:
"""
        
        # Create specific templates for each document type
        for doc_type in settings.DOCUMENT_TYPES.keys():
            templates[doc_type] = PromptTemplate(
                input_variables=["document_type", "field_list", "document_text"],
                template=base_template
            )
        
        return templates
    
    async def extract_entities(
        self, 
        text: str, 
        document_type: str
    ) -> EntityExtractionResponse:
        """Extract entities from document text using LLM"""
        try:
            if not self.llm:
                logger.error("LLM not initialized - skipping entity extraction")
                return EntityExtractionResponse(entities={})
            
            logger.info(f"Extracting entities for document type: {document_type}")
            
            # Get fields for this document type
            fields = settings.DOCUMENT_TYPES.get(document_type, [])
            if not fields:
                logger.warning(f"No fields defined for document type: {document_type}")
                return EntityExtractionResponse(entities={})
            
            # Create prompt
            prompt = self._create_extraction_prompt(text, document_type, fields)
            
            # Get LLM response
            response = await self._get_llm_response(prompt)
            
            # Parse JSON response
            entities = self._parse_json_response(response)
            
            # Validate and clean entities
            cleaned_entities = self._validate_entities(entities, fields)
            
            return EntityExtractionResponse(
                entities=cleaned_entities,
                confidence_scores=self._calculate_confidence_scores(cleaned_entities)
            )
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            return EntityExtractionResponse(entities={})
    
    def _create_extraction_prompt(
        self, 
        text: str, 
        document_type: str, 
        fields: List[str]
    ) -> str:
        """Create extraction prompt for the given document"""
        template = self.prompt_templates.get(document_type)
        if not template:
            template = self.prompt_templates["invoice"]  # Use default template
        
        return template.format(
            document_type=document_type.title(),
            field_list=", ".join(fields),
            document_text=text[:4000]  # Limit text length for LLM
        )
    
    async def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM"""
        try:
            message = HumanMessage(content=prompt)
            response = await self.llm.agenerate([[message]])
            return response.generations[0][0].text.strip()
        except Exception as e:
            logger.error(f"LLM request failed: {str(e)}")
            raise
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from LLM"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # Try parsing the entire response as JSON
                return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Raw response: {response}")
            return {}
    
    def _validate_entities(
        self, 
        entities: Dict[str, Any], 
        expected_fields: List[str]
    ) -> Dict[str, Any]:
        """Validate and clean extracted entities"""
        validated = {}
        
        for field in expected_fields:
            value = entities.get(field)
            
            # Clean and validate the value
            if value is not None and str(value).strip():
                cleaned_value = str(value).strip()
                if cleaned_value.lower() not in ['null', 'none', 'n/a', '']:
                    validated[field] = self._clean_field_value(field, cleaned_value)
                else:
                    validated[field] = None
            else:
                validated[field] = None
        
        return validated
    
    def _clean_field_value(self, field_name: str, value: str) -> str:
        """Clean specific field values based on field type"""
        # Date fields
        if 'date' in field_name.lower():
            return self._clean_date_value(value)
        
        # Amount fields
        if any(word in field_name.lower() for word in ['amount', 'total', 'balance', 'value']):
            return self._clean_amount_value(value)
        
        # Phone fields
        if 'phone' in field_name.lower():
            return self._clean_phone_value(value)
        
        return value
    
    def _clean_date_value(self, value: str) -> str:
        """Clean date values"""
        # Remove extra whitespace and common prefixes
        value = re.sub(r'^(date:?|on:?)\s*', '', value, flags=re.IGNORECASE)
        return value.strip()
    
    def _clean_amount_value(self, value: str) -> str:
        """Clean monetary amount values"""
        # Remove extra whitespace and common prefixes
        value = re.sub(r'^(total:?|amount:?|sum:?)\s*', '', value, flags=re.IGNORECASE)
        return value.strip()
    
    def _clean_phone_value(self, value: str) -> str:
        """Clean phone number values"""
        # Remove non-numeric characters except + and -
        return re.sub(r'[^\d\+\-\(\)\s]', '', value)
    
    def _calculate_confidence_scores(
        self, 
        entities: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate confidence scores for extracted entities"""
        confidence_scores = {}
        
        for field, value in entities.items():
            if value is None:
                confidence_scores[field] = 0.0
            else:
                # Simple heuristic for confidence scoring
                confidence = 0.8  # Base confidence
                
                # Adjust based on value characteristics
                if len(str(value)) < 3:
                    confidence -= 0.2
                elif len(str(value)) > 50:
                    confidence -= 0.1
                
                confidence_scores[field] = max(0.0, min(1.0, confidence))
        
        return confidence_scores
    
    def _is_valid_date_format(self, value: str) -> bool:
        """Check if value is in a valid date format"""
        import re
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY
            r'\d{1,2}-\d{1,2}-\d{2,4}',  # MM-DD-YYYY
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, value):
                return True
        return False