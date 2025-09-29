from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import logging
from datetime import datetime

from database import get_db, ChatSession, ChatMessage
from models import ChatRequest, ChatResponse, MessageType, DocumentAnalysisRequest
from services.llm_service import LLMService
from services.vector_service import VectorService

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize services (will be injected in main.py)
llm_service = None
vector_service = None

def set_services(llm_svc: LLMService, vec_service: VectorService):
    global llm_service, vector_service
    llm_service = llm_svc
    vector_service = vec_service

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Main chat endpoint with RAG"""
    try:
        # Verify session exists
        session_result = await db.execute(
            select(ChatSession).where(ChatSession.session_id == request.session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Save user message
        user_message = ChatMessage(
            session_id=request.session_id,
            message_type=MessageType.USER,
            content=request.message,
            metadata={"domain": request.domain}
        )
        db.add(user_message)

        # Get recent chat history for context
        history_result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == request.session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
        history_messages = history_result.scalars().all()

        # Convert to chat history format
        chat_history = []
        for msg in reversed(history_messages):  # Reverse to get chronological order
            role = "user" if msg.message_type == MessageType.USER else "assistant"
            chat_history.append({"role": role, "content": msg.content})

        # Search for relevant documents
        search_results = await vector_service.search_similar(
            query=request.message,
            top_k=5,
            domain=request.domain if request.domain != "general" else None
        )

        # Generate response using LLM
        llm_response = await llm_service.generate_response(
            query=request.message,
            context_chunks=search_results,
            domain=request.domain,
            chat_history=chat_history[:-1]  # Exclude the current message
        )

        # Save assistant message
        assistant_message = ChatMessage(
            session_id=request.session_id,
            message_type=MessageType.ASSISTANT,
            content=llm_response.content,
            metadata={
                "domain": request.domain,
                "model": llm_response.model,
                "usage": llm_response.usage,
                "source_count": len(search_results)
            }
        )
        db.add(assistant_message)

        # Update session timestamp
        session.updated_at = datetime.now()

        await db.commit()

        # Prepare sources for response
        sources = []
        if search_results:
            sources = [
                {
                    "document_name": result.document_name,
                    "chunk_index": result.chunk_index,
                    "score": result.score,
                    "content_preview": result.chunk_text[:200] + "..." if len(result.chunk_text) > 200 else result.chunk_text
                }
                for result in search_results
            ]

        return ChatResponse(
            message=llm_response.content,
            message_type=MessageType.ASSISTANT,
            session_id=request.session_id,
            sources=sources,
            metadata={
                "model": llm_response.model,
                "usage": llm_response.usage,
                "domain": request.domain
            },
            timestamp=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@router.post("/analyze", response_model=ChatResponse)
async def analyze_documents(
    request: DocumentAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """Analyze specific documents with a query"""
    try:
        # Verify session exists
        session_result = await db.execute(
            select(ChatSession).where(ChatSession.session_id == request.session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Search in specific documents if provided
        search_results = await vector_service.search_similar(
            query=request.query,
            top_k=10,  # More results for analysis
            document_ids=request.document_ids,
            domain=request.domain if request.domain != "general" else None
        )

        if not search_results:
            return ChatResponse(
                message="죄송합니다. 요청하신 문서에서 관련 내용을 찾을 수 없습니다.",
                message_type=MessageType.ASSISTANT,
                session_id=request.session_id,
                sources=[],
                metadata={"domain": request.domain},
                timestamp=datetime.now()
            )

        # Generate analysis response
        llm_response = await llm_service.generate_response(
            query=f"다음 문서들을 상세히 분석해주세요: {request.query}",
            context_chunks=search_results,
            domain=request.domain
        )

        # Save messages
        user_message = ChatMessage(
            session_id=request.session_id,
            message_type=MessageType.USER,
            content=f"[문서 분석] {request.query}",
            metadata={"domain": request.domain, "document_ids": request.document_ids}
        )
        db.add(user_message)

        assistant_message = ChatMessage(
            session_id=request.session_id,
            message_type=MessageType.ASSISTANT,
            content=llm_response.content,
            metadata={
                "domain": request.domain,
                "model": llm_response.model,
                "usage": llm_response.usage,
                "source_count": len(search_results),
                "analysis_type": "document_analysis"
            }
        )
        db.add(assistant_message)

        session.updated_at = datetime.now()
        await db.commit()

        # Prepare detailed sources for analysis
        sources = [
            {
                "document_name": result.document_name,
                "chunk_index": result.chunk_index,
                "score": result.score,
                "content_preview": result.chunk_text[:300] + "..." if len(result.chunk_text) > 300 else result.chunk_text,
                "metadata": result.metadata
            }
            for result in search_results
        ]

        return ChatResponse(
            message=llm_response.content,
            message_type=MessageType.ASSISTANT,
            session_id=request.session_id,
            sources=sources,
            metadata={
                "model": llm_response.model,
                "usage": llm_response.usage,
                "domain": request.domain,
                "analysis_type": "document_analysis"
            },
            timestamp=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Document analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Document analysis failed: {str(e)}")

@router.get("/search")
async def search_documents(
    query: str,
    session_id: str,
    domain: Optional[str] = None,
    document_ids: Optional[str] = None,  # Comma-separated IDs
    top_k: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """Search documents without generating a chat response"""
    try:
        # Verify session exists
        session_result = await db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        if not session_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Session not found")

        # Parse document IDs if provided
        doc_ids = None
        if document_ids:
            try:
                doc_ids = [int(id.strip()) for id in document_ids.split(",")]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid document IDs format")

        # Search for documents
        search_results = await vector_service.search_similar(
            query=query,
            top_k=top_k,
            document_ids=doc_ids,
            domain=domain if domain != "general" else None
        )

        return {
            "query": query,
            "results": [
                {
                    "document_name": result.document_name,
                    "chunk_index": result.chunk_index,
                    "score": result.score,
                    "content": result.chunk_text,
                    "metadata": result.metadata
                }
                for result in search_results
            ],
            "total_results": len(search_results)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/suggestions")
async def get_chat_suggestions(
    session_id: str,
    domain: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get suggested questions based on uploaded documents"""
    try:
        # Verify session exists
        session_result = await db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        if not session_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Session not found")

        # Domain-specific suggestions
        domain_suggestions = {
            "legal": [
                "이 계약서의 주요 조항은 무엇인가요?",
                "법적 리스크가 있는 부분을 찾아주세요",
                "계약 해지 조건을 설명해주세요",
                "의무사항과 책임 범위를 정리해주세요"
            ],
            "medical": [
                "환자의 주요 증상과 진단을 요약해주세요",
                "처방된 치료법의 효과와 부작용은?",
                "검사 결과를 해석해주세요",
                "추천되는 후속 조치는 무엇인가요?"
            ],
            "financial": [
                "재무 상태의 주요 지표를 분석해주세요",
                "수익성과 성장성을 평가해주세요",
                "리스크 요인들을 식별해주세요",
                "투자 관점에서의 권고사항은?"
            ],
            "technical": [
                "시스템 아키텍처를 설명해주세요",
                "보안 취약점이 있는지 확인해주세요",
                "성능 최적화 방안을 제안해주세요",
                "기술적 개선사항을 정리해주세요"
            ],
            "general": [
                "문서의 핵심 내용을 요약해주세요",
                "중요한 포인트들을 정리해주세요",
                "개선이 필요한 부분은 무엇인가요?",
                "추가로 확인이 필요한 사항은?"
            ]
        }

        suggestions = domain_suggestions.get(domain or "general", domain_suggestions["general"])

        return {
            "suggestions": suggestions,
            "domain": domain or "general"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")