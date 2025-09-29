from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://chatbot_user:chatbot_password@postgres:5432/chatbot_db"

    # Redis
    redis_url: str = "redis://redis:6379"

    # ChromaDB
    chroma_host: str = "chromadb"
    chroma_port: int = 8000

    # LLM Settings
    openai_api_key: Optional[str] = None
    openai_api_base: Optional[str] = None  # For GPT-OSS models
    model_name: str = "gpt-3.5-turbo"  # Default, will be overridden for GPT-OSS

    # File Upload
    upload_dir: str = "/app/uploads"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_file_types: list = [".pdf", ".txt", ".docx", ".doc", ".xlsx", ".xls"]

    # Vector Database
    collection_name: str = "document_analysis"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Document Analysis Settings
    analysis_domains: list = ["legal", "medical", "financial", "technical", "general"]
    default_domain: str = "general"

    class Config:
        env_file = ".env"

settings = Settings()