from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from pathlib import Path

from database import get_db, init_db
from models import ChatSession, ChatMessage, DocumentUpload
from services.vector_service import VectorService
from services.llm_service import LLMService
from services.document_service import DocumentService
from config import settings

# Initialize services
vector_service = VectorService()
llm_service = LLMService()
document_service = DocumentService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await vector_service.initialize()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Document Analysis Chatbot API",
    description="전문 분야 문서 분석을 위한 RAG 기반 챗봇 시스템",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Document Analysis Chatbot API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_status = await check_db_connection()

        # Check vector database connection
        vector_status = await vector_service.health_check()

        # Check LLM service
        llm_status = await llm_service.health_check()

        return {
            "status": "healthy",
            "services": {
                "database": db_status,
                "vector_db": vector_status,
                "llm": llm_status
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

async def check_db_connection():
    """Check database connection"""
    try:
        from database import engine
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        return "connected"
    except Exception:
        return "disconnected"

# Initialize API routers and inject services
from api import chat, documents, sessions

# Inject services into API modules
chat.set_services(llm_service, vector_service)
documents.set_services(document_service, vector_service)

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)