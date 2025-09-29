from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class UploadStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentDomain(str, Enum):
    LEGAL = "legal"
    MEDICAL = "medical"
    FINANCIAL = "financial"
    TECHNICAL = "technical"
    GENERAL = "general"

# Request Models
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: str = Field(..., min_length=1)
    domain: Optional[DocumentDomain] = DocumentDomain.GENERAL

class SessionCreateRequest(BaseModel):
    session_name: Optional[str] = None
    user_id: Optional[str] = None

class DocumentAnalysisRequest(BaseModel):
    query: str = Field(..., min_length=1)
    document_ids: Optional[List[int]] = None
    domain: Optional[DocumentDomain] = DocumentDomain.GENERAL
    session_id: str

# Response Models
class ChatResponse(BaseModel):
    message: str
    message_type: MessageType
    session_id: str
    sources: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime

class SessionResponse(BaseModel):
    session_id: str
    session_name: Optional[str]
    created_at: datetime
    message_count: int = 0

class DocumentUploadResponse(BaseModel):
    id: int
    file_name: str
    file_size: int
    upload_status: UploadStatus
    domain: DocumentDomain
    uploaded_at: datetime
    vector_count: Optional[int] = 0

class DocumentListResponse(BaseModel):
    documents: List[DocumentUploadResponse]
    total_count: int

class HealthResponse(BaseModel):
    status: str
    services: Dict[str, str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Internal Models
class DocumentChunk(BaseModel):
    text: str
    metadata: Dict[str, Any]
    chunk_index: int

class VectorSearchResult(BaseModel):
    chunk_text: str
    score: float
    document_name: str
    chunk_index: int
    metadata: Dict[str, Any]

class LLMResponse(BaseModel):
    content: str
    usage: Optional[Dict[str, Any]] = None
    model: str
    sources: Optional[List[VectorSearchResult]] = None