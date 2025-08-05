"""
LLM-powered decision engine for processing queries and making decisions
"""

import json
import logging
from typing import List, Dict, Any, Tuple, Optional

from src.models.schemas import (
    StructuredQuery, RetrievedClause, DecisionType, ProcessingResponse
)
from src.core.config import settings
from src.services.llm_client import LLMClientFactory

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Handles decision making based on retrieved clauses and query analysis"""
    
    def __init__(self):
        self.llm_client = LLMClientFactory.create_client()
    
    def make_decision(
        self, 
        query: StructuredQuery, 
        clauses: List[RetrievedClause]
    ) -> Tuple[DecisionType, Optional[float], str, float]:
        """
        Make a decision based on the query and retrieved clauses
        
        Args:
            query: Structured query object
            clauses: List of relevant clauses
            
        Returns:
            Tuple of (decision, amount, justification, confidence)
        """
        logger.info(f"Making decision for query: {query.original_query}")
        
        if not clauses:
            return (
                DecisionType.REJECTED,
                None,
                "No relevant clauses found to support the request",
                0.1
            )
        
        # Prepare context for LLM
        context = self._prepare_context(query, clauses)
        
        # Generate decision using LLM
        decision_result = self._generate_decision(context)
        
        return decision_result
    
    def _prepare_context(self, query: StructuredQuery, clauses: List[RetrievedClause]) -> Dict[str, Any]:
        """Prepare context for LLM decision making"""
        
        # Extract entities for context
        entities_dict = {}
        for entity in query.entities:
            if entity.entity_type.value not in entities_dict:
                entities_dict[entity.entity_type.value] = []
            entities_dict[entity.entity_type.value].append(entity.value)
        
        # Prepare clauses information
        clauses_info = []
        for clause in clauses:
            clause_info = {
                "id": clause.clause_id,
                "content": clause.content,
                "similarity_score": clause.similarity_score,
                "section": clause.section or "Unknown",
                "document_id": clause.document_id
            }
            clauses_info.append(clause_info)
        
        context = {
            "original_query": query.original_query,
            "query_type": query.query_type.value,
            "intent": query.intent,
            "extracted_entities": entities_dict,
            "relevant_clauses": clauses_info,
            "total_clauses": len(clauses)
        }
        
        return context
    
    def _generate_decision(self, context: Dict[str, Any]) -> Tuple[DecisionType, Optional[float], str, float]:
        """Generate decision using LLM or fallback logic"""

        try:
            # Try LLM-based decision first
            return self._generate_llm_decision(context)

        except Exception as e:
            logger.warning(f"LLM decision failed: {str(e)}")
            logger.info("🔄 Using fallback decision logic...")
            return self._generate_fallback_decision(context)

    def _generate_llm_decision(self, context: Dict[str, Any]) -> Tuple[DecisionType, Optional[float], str, float]:
        """Generate decision using LLM"""

        prompt = self._create_decision_prompt(context)
        system_prompt = ("You are an expert decision-making AI for document analysis. "
                        "Analyze the provided context and make accurate decisions based on the relevant clauses.")

        content = self.llm_client.generate_text(prompt, system_prompt)
        return self._parse_decision_response(content)

    def _generate_fallback_decision(self, context: Dict[str, Any]) -> Tuple[DecisionType, Optional[float], str, float]:
        """Generate decision using rule-based fallback logic"""

        clauses = context.get('relevant_clauses', [])
        entities = context.get('extracted_entities', {})
        query_type = context.get('query_type', 'general')

        if not clauses:
            return (
                DecisionType.REJECTED,
                None,
                "No relevant policy clauses found to support this request.",
                0.2
            )

        # Simple rule-based decision logic
        decision = DecisionType.PENDING
        amount = None
        justification = "Based on available policy information: "
        confidence = 0.6

        # Check for insurance claims
        if query_type == 'insurance_claim':
            # Look for coverage indicators
            coverage_found = False
            exclusion_found = False

            for clause in clauses:
                content = clause['content'].lower()

                # Check for procedure coverage
                if any(proc in entities.get('procedure', []) for proc in ['surgery', 'knee', 'hip']):
                    if 'covered' in content or 'coverage' in content:
                        coverage_found = True
                        # Extract amount if mentioned
                        import re
                        amount_match = re.search(r'₹([\d,]+)', clause['content'])
                        if amount_match:
                            amount_str = amount_match.group(1).replace(',', '')
                            amount = float(amount_str)

                # Check for exclusions
                if 'excluded' in content or 'not covered' in content:
                    exclusion_found = True

            if coverage_found and not exclusion_found:
                decision = DecisionType.APPROVED
                justification += "Procedure appears to be covered under the policy terms."
                confidence = 0.7
            elif exclusion_found:
                decision = DecisionType.REJECTED
                justification += "Procedure appears to be excluded from coverage."
                confidence = 0.7
            else:
                decision = DecisionType.PENDING
                justification += "Coverage status unclear, requires manual review."

        # Check for HR policy queries
        elif query_type == 'hr_policy':
            if clauses:
                decision = DecisionType.APPROVED
                justification += f"Found relevant policy information in {len(clauses)} sections."
                confidence = 0.6

        # Add clause references
        if clauses:
            justification += f" Referenced {len(clauses)} relevant policy sections."

        return decision, amount, justification, confidence
    
    def _create_decision_prompt(self, context: Dict[str, Any]) -> str:
        """Create a detailed prompt for decision making"""
        
        prompt = f"""
        Analyze the following query and relevant document clauses to make a decision.

        QUERY INFORMATION:
        - Original Query: "{context['original_query']}"
        - Query Type: {context['query_type']}
        - Intent: {context['intent']}
        - Extracted Entities: {json.dumps(context['extracted_entities'], indent=2)}

        RELEVANT CLAUSES:
        """
        
        for i, clause in enumerate(context['relevant_clauses'], 1):
            prompt += f"""
        Clause {i} (Similarity: {clause['similarity_score']:.2f}):
        Section: {clause['section']}
        Content: {clause['content']}
        ---
        """
        
        prompt += """
        DECISION REQUIREMENTS:
        Based on the query and relevant clauses, provide your decision in the following JSON format:

        {
            "decision": "approved|rejected|pending|partial",
            "amount": null or numeric value,
            "justification": "Detailed explanation of the decision",
            "confidence": 0.0-1.0,
            "reasoning": "Step-by-step reasoning process",
            "applicable_clauses": ["clause_id1", "clause_id2"]
        }

        DECISION GUIDELINES:
        1. "approved": All requirements are met according to the clauses
        2. "rejected": Requirements are not met or explicitly excluded
        3. "pending": Insufficient information or requires additional verification
        4. "partial": Some requirements are met, but not all

        For insurance claims:
        - Check coverage eligibility based on policy terms
        - Verify procedure/treatment is covered
        - Consider waiting periods, exclusions, and limits
        - Calculate coverage amount if applicable

        For legal/compliance queries:
        - Check if the scenario complies with stated rules
        - Identify any violations or requirements
        - Provide clear compliance status

        Provide your response as valid JSON only:
        """
        
        return prompt
    
    def _parse_decision_response(self, response: str) -> Tuple[DecisionType, Optional[float], str, float]:
        """Parse the LLM response and extract decision components"""
        
        try:
            # Try to extract JSON from the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                decision_data = json.loads(json_str)
                
                # Extract decision components
                decision_str = decision_data.get('decision', 'pending').lower()
                try:
                    decision = DecisionType(decision_str)
                except ValueError:
                    decision = DecisionType.PENDING
                
                amount = decision_data.get('amount')
                if amount is not None:
                    try:
                        amount = float(amount)
                    except (ValueError, TypeError):
                        amount = None
                
                justification = decision_data.get('justification', 'No justification provided')
                confidence = float(decision_data.get('confidence', 0.5))
                
                # Ensure confidence is within valid range
                confidence = max(0.0, min(1.0, confidence))
                
                return decision, amount, justification, confidence
            
            else:
                # Fallback parsing if JSON is not found
                return self._fallback_parse(response)
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            return self._fallback_parse(response)
        except Exception as e:
            logger.error(f"Error parsing decision response: {str(e)}")
            return (
                DecisionType.PENDING,
                None,
                "Error parsing decision response",
                0.1
            )
    
    def _fallback_parse(self, response: str) -> Tuple[DecisionType, Optional[float], str, float]:
        """Fallback parsing when JSON parsing fails"""
        
        response_lower = response.lower()
        
        # Determine decision based on keywords
        if any(word in response_lower for word in ['approved', 'accept', 'covered', 'eligible']):
            decision = DecisionType.APPROVED
        elif any(word in response_lower for word in ['rejected', 'denied', 'not covered', 'excluded']):
            decision = DecisionType.REJECTED
        elif any(word in response_lower for word in ['partial', 'partially']):
            decision = DecisionType.PARTIAL
        else:
            decision = DecisionType.PENDING
        
        return decision, None, response[:500], 0.5
