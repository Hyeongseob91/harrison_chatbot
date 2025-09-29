from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from datetime import datetime
from config import settings

# Convert postgres:// to postgresql+asyncpg://
DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    future=True
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(String(255))
    session_name = Column(String(255))

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), ForeignKey("chat_sessions.session_id"), nullable=False)
    message_type = Column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class DocumentUpload(Base):
    __tablename__ = "document_uploads"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    upload_status = Column(String(50), default="pending")
    vector_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    session_id = Column(String(255), ForeignKey("chat_sessions.session_id"))
    domain = Column(String(100), default="general")  # Document domain/category

class VectorChunk(Base):
    __tablename__ = "vector_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("document_uploads.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    vector_id = Column(String(255), nullable=False)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Dependency to get database session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()