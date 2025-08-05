"""
Query parsing and entity extraction service
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
# import spacy  # Optional - will be loaded if available

from src.models.schemas import (
    StructuredQuery, ExtractedEntity, EntityType, QueryType
)
from src.core.config import settings
from src.services.llm_client import LLMClientFactory

logger = logging.getLogger(__name__)


class QueryParser:
    """Handles natural language query parsing and entity extraction"""
    
    def __init__(self):
        self.llm_client = LLMClientFactory.create_client()
        self.nlp = None
        self._load_spacy_model()
        
        # Enhanced regex patterns for common entities
        self.patterns = {
            EntityType.AGE: [
                r'(\d{1,3})\s*(?:year|yr|y)(?:s)?(?:\s*old)?',
                r'(\d{1,3})\s*(?:M|F|male|female)',
                r'age\s*(?:of\s*)?(\d{1,3})',
                r'(\d{1,3})-year-old',
                r'(\d{1,3})M\b',
                r'(\d{1,3})F\b',
            ],
            EntityType.GENDER: [
                r'\b(male|female|M|F|man|woman)\b',
                r'(\d+)M\b',  # Will extract as male
                r'(\d+)F\b',  # Will extract as female
            ],
            EntityType.PROCEDURE: [
                r'\b(surgery|operation|procedure|treatment)\b',
                r'\b(knee|hip|heart|brain|liver|kidney|dental|eye|spine)\s+(surgery|operation|procedure|treatment)',
                r'\b(knee|hip|heart|cardiac|orthopedic|dental)\s+(surgery|operation)',
                r'\b(chemotherapy|radiation|dialysis|physiotherapy)\b',
                r'\b(bypass|angioplasty|transplant|replacement)\b',
            ],
            EntityType.LOCATION: [
                r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'\bat\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'\b(Mumbai|Delhi|Bangalore|Chennai|Pune|Hyderabad|Kolkata|Ahmedabad)\b',
                r'\b([A-Z][a-z]+)\s+(?:city|hospital|clinic)\b',
            ],
            EntityType.POLICY_DURATION: [
                r'(\d+)\s*(?:month|yr|year)(?:s)?\s*(?:old\s*)?policy',
                r'policy\s*(?:of\s*)?(\d+)\s*(?:month|yr|year)(?:s)?',
                r'(\d+)-(?:month|year)(?:s)?\s*(?:old\s*)?policy',
                r'(\d+)\s*(?:month|yr|year)(?:s)?\s*insurance',
            ],
            EntityType.AMOUNT: [
                r'(?:₹|Rs\.?|INR)\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
                r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:₹|Rs\.?|INR|rupees)',
                r'(?:amount|cost|price|fee)\s*(?:of\s*)?(?:₹|Rs\.?|INR)?\s*(\d+(?:,\d{3})*)',
                r'(\d+)\s*(?:lakh|crore)',
            ]
        }
    
    def _load_spacy_model(self):
        """Load spaCy model for NLP processing"""
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
        except (ImportError, OSError):
            logger.warning("spaCy not available. Install with: pip install spacy && python -m spacy download en_core_web_sm")
            self.nlp = None
    
    def parse_query(self, query: str) -> StructuredQuery:
        """
        Parse natural language query and extract structured information
        
        Args:
            query: Natural language query string
            
        Returns:
            StructuredQuery object with extracted entities and metadata
        """
        logger.info(f"Parsing query: {query}")
        
        # Extract entities using regex patterns
        entities = self._extract_entities_regex(query)
        
        # Extract entities using spaCy if available
        if self.nlp:
            spacy_entities = self._extract_entities_spacy(query)
            entities.extend(spacy_entities)
        
        # Determine query type and intent using LLM
        query_type, intent, confidence = self._classify_query(query)
        
        structured_query = StructuredQuery(
            original_query=query,
            query_type=query_type,
            entities=entities,
            intent=intent,
            confidence=confidence
        )
        
        logger.info(f"Extracted {len(entities)} entities, type: {query_type}, intent: {intent}")
        return structured_query
    
    def _extract_entities_regex(self, query: str) -> List[ExtractedEntity]:
        """Extract entities using regex patterns"""
        entities = []
        query_lower = query.lower()
        
        for entity_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, query_lower, re.IGNORECASE)
                for match in matches:
                    value = match.group(1) if match.groups() else match.group(0)
                    
                    entity = ExtractedEntity(
                        entity_type=entity_type,
                        value=value.strip(),
                        confidence=0.8,  # High confidence for regex matches
                        start_pos=match.start(),
                        end_pos=match.end()
                    )
                    entities.append(entity)
        
        return entities
    
    def _extract_entities_spacy(self, query: str) -> List[ExtractedEntity]:
        """Extract entities using spaCy NER"""
        entities = []
        doc = self.nlp(query)
        
        for ent in doc.ents:
            entity_type = self._map_spacy_label(ent.label_)
            if entity_type:
                entity = ExtractedEntity(
                    entity_type=entity_type,
                    value=ent.text,
                    confidence=0.7,  # Medium confidence for spaCy
                    start_pos=ent.start_char,
                    end_pos=ent.end_char
                )
                entities.append(entity)
        
        return entities
    
    def _map_spacy_label(self, label: str) -> Optional[EntityType]:
        """Map spaCy entity labels to our EntityType enum"""
        mapping = {
            'PERSON': EntityType.PERSON,
            'ORG': EntityType.ORGANIZATION,
            'GPE': EntityType.LOCATION,
            'MONEY': EntityType.AMOUNT,
            'DATE': EntityType.DATE,
        }
        return mapping.get(label)
    
    def _classify_query(self, query: str) -> Tuple[QueryType, str, float]:
        """Classify query type and extract intent using LLM or fallback"""

        try:
            # Try LLM classification first
            return self._classify_query_llm(query)
        except Exception as e:
            logger.warning(f"LLM classification failed: {str(e)}")
            # Use rule-based fallback
            return self._classify_query_fallback(query)

    def _classify_query_llm(self, query: str) -> Tuple[QueryType, str, float]:
        """Classify query using LLM"""

        prompt = f"""
        Analyze the following query and determine:
        1. Query type (insurance_claim, legal_compliance, contract_review, hr_policy, or general)
        2. Intent (what the user wants to know)
        3. Confidence score (0.0 to 1.0)

        Query: "{query}"

        Respond in this exact format:
        Type: [query_type]
        Intent: [brief description of what user wants]
        Confidence: [0.0-1.0]
        """

        content = self.llm_client.generate_text(prompt)

        # Parse the response
        lines = content.split('\n')
        query_type = QueryType.GENERAL
        intent = "General query"
        confidence = 0.5

        for line in lines:
            if line.startswith('Type:'):
                type_str = line.split(':', 1)[1].strip().lower()
                try:
                    query_type = QueryType(type_str)
                except ValueError:
                    query_type = QueryType.GENERAL
            elif line.startswith('Intent:'):
                intent = line.split(':', 1)[1].strip()
            elif line.startswith('Confidence:'):
                try:
                    confidence = float(line.split(':', 1)[1].strip())
                except ValueError:
                    confidence = 0.5

        return query_type, intent, confidence

    def _classify_query_fallback(self, query: str) -> Tuple[QueryType, str, float]:
        """Classify query using rule-based approach"""

        query_lower = query.lower()

        # Insurance-related keywords
        insurance_keywords = [
            'surgery', 'claim', 'coverage', 'policy', 'insurance', 'medical',
            'treatment', 'hospital', 'procedure', 'knee', 'hip', 'heart'
        ]

        # HR-related keywords
        hr_keywords = [
            'leave', 'maternity', 'paternity', 'salary', 'employee', 'working hours',
            'notice period', 'resignation', 'bonus', 'benefits', 'vacation'
        ]

        # Legal/compliance keywords
        legal_keywords = [
            'contract', 'legal', 'compliance', 'regulation', 'law', 'agreement',
            'terms', 'conditions', 'violation', 'breach'
        ]

        # Count keyword matches
        insurance_score = sum(1 for keyword in insurance_keywords if keyword in query_lower)
        hr_score = sum(1 for keyword in hr_keywords if keyword in query_lower)
        legal_score = sum(1 for keyword in legal_keywords if keyword in query_lower)

        # Determine query type based on highest score
        max_score = max(insurance_score, hr_score, legal_score)

        if max_score == 0:
            return QueryType.GENERAL, "General information request", 0.3

        confidence = min(0.8, 0.4 + (max_score * 0.1))  # Cap at 0.8 for rule-based

        if insurance_score == max_score:
            intent = "Insurance claim or coverage inquiry"
            return QueryType.INSURANCE_CLAIM, intent, confidence
        elif hr_score == max_score:
            intent = "HR policy or employee benefits inquiry"
            return QueryType.HR_POLICY, intent, confidence
        elif legal_score == max_score:
            intent = "Legal compliance or contract inquiry"
            return QueryType.LEGAL_COMPLIANCE, intent, confidence
        else:
            return QueryType.GENERAL, "General information request", confidence
