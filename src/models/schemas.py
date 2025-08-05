"""
Pydantic models for request/response schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class QueryType(str, Enum):
    INSURANCE_CLAIM = "insurance_claim"
    LEGAL_COMPLIANCE = "legal_compliance"
    CONTRACT_REVIEW = "contract_review"
    HR_POLICY = "hr_policy"
    GENERAL = "general"


class EntityType(str, Enum):
    AGE = "age"
    GENDER = "gender"
    PROCEDURE = "procedure"
    LOCATION = "location"
    POLICY_DURATION = "policy_duration"
    AMOUNT = "amount"
    DATE = "date"
    PERSON = "person"
    ORGANIZATION = "organization"


class ExtractedEntity(BaseModel):
    entity_type: EntityType
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    start_pos: Optional[int] = None
    end_pos: Optional[int] = None


class StructuredQuery(BaseModel):
    original_query: str
    query_type: QueryType
    entities: List[ExtractedEntity]
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    metadata: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None


class RetrievedClause(BaseModel):
    clause_id: str
    document_id: str
    content: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = {}
    section: Optional[str] = None


class DecisionType(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"
    PARTIAL = "partial"


class ProcessingRequest(BaseModel):
    query: str
    query_type: Optional[QueryType] = QueryType.GENERAL
    context: Optional[Dict[str, Any]] = {}


class ProcessingResponse(BaseModel):
    decision: DecisionType
    amount: Optional[float] = None
    justification: str
    confidence: float = Field(ge=0.0, le=1.0)
    clauses_used: List[RetrievedClause]
    processing_time: float
    query_analysis: StructuredQuery


class DocumentUploadRequest(BaseModel):
    filename: str
    content_type: str
    metadata: Optional[Dict[str, Any]] = {}


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    chunks_created: int
    processing_time: float


class HealthResponse(BaseModel):
    status: str
    version: str
    components: Dict[str, str]
