from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
import uuid
from datetime import datetime

from database import get_db, ChatSession, ChatMessage
from models import SessionCreateRequest, SessionResponse

router = APIRouter()

@router.post("/", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat session"""
    try:
        session_id = str(uuid.uuid4())
        session_name = request.session_name or f"Chat Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        new_session = ChatSession(
            session_id=session_id,
            session_name=session_name,
            user_id=request.user_id
        )

        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)

        return SessionResponse(
            session_id=session_id,
            session_name=session_name,
            created_at=new_session.created_at,
            message_count=0
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    user_id: str = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List chat sessions"""
    try:
        # Build query
        query = select(
            ChatSession,
            func.count(ChatMessage.id).label('message_count')
        ).outerjoin(
            ChatMessage, ChatSession.session_id == ChatMessage.session_id
        ).group_by(ChatSession.id)

        if user_id:
            query = query.where(ChatSession.user_id == user_id)

        query = query.order_by(ChatSession.updated_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        sessions = result.all()

        return [
            SessionResponse(
                session_id=session.ChatSession.session_id,
                session_name=session.ChatSession.session_name,
                created_at=session.ChatSession.created_at,
                message_count=session.message_count or 0
            )
            for session in sessions
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get session details"""
    try:
        # Get session with message count
        query = select(
            ChatSession,
            func.count(ChatMessage.id).label('message_count')
        ).outerjoin(
            ChatMessage, ChatSession.session_id == ChatMessage.session_id
        ).where(
            ChatSession.session_id == session_id
        ).group_by(ChatSession.id)

        result = await db.execute(query)
        session_data = result.first()

        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")

        return SessionResponse(
            session_id=session_data.ChatSession.session_id,
            session_name=session_data.ChatSession.session_name,
            created_at=session_data.ChatSession.created_at,
            message_count=session_data.message_count or 0
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")

@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a chat session"""
    try:
        # Get session
        result = await db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Delete session (cascade will delete messages)
        await db.delete(session)
        await db.commit()

        return {"message": "Session deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get messages for a session"""
    try:
        # Check if session exists
        session_result = await db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        if not session_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Session not found")

        # Get messages
        messages_result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        messages = messages_result.scalars().all()

        return {
            "messages": [
                {
                    "id": msg.id,
                    "message_type": msg.message_type,
                    "content": msg.content,
                    "metadata": msg.metadata,
                    "created_at": msg.created_at
                }
                for msg in messages
            ],
            "session_id": session_id,
            "total_count": len(messages)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")