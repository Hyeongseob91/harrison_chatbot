import aiofiles
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import asyncio
from datetime import datetime

# Document processing imports
import PyPDF2
from docx import Document as DocxDocument
import pandas as pd
import tiktoken

from config import settings
from models import DocumentChunk, DocumentDomain
from services.vector_service import VectorService

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        self.upload_dir = Path(settings.upload_dir)
        self.upload_dir.mkdir(exist_ok=True, parents=True)
        self.vector_service = None

        # Initialize tokenizer for chunk size calculation
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except:
            self.tokenizer = None

    def set_vector_service(self, vector_service: VectorService):
        """Set vector service instance"""
        self.vector_service = vector_service

    async def save_upload_file(self, file, session_id: str) -> str:
        """Save uploaded file and return file path"""
        try:
            # Create session directory
            session_dir = self.upload_dir / session_id
            session_dir.mkdir(exist_ok=True, parents=True)

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = Path(file.filename).suffix
            safe_filename = f"{timestamp}_{file.filename}"
            file_path = session_dir / safe_filename

            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)

            logger.info(f"Saved file: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            raise

    async def process_document(
        self,
        file_path: str,
        domain: DocumentDomain = DocumentDomain.GENERAL
    ) -> List[DocumentChunk]:
        """Process document and return chunks"""
        try:
            file_extension = Path(file_path).suffix.lower()

            if file_extension == '.pdf':
                text = await self._extract_pdf_text(file_path)
            elif file_extension == '.txt':
                text = await self._extract_text_file(file_path)
            elif file_extension in ['.docx', '.doc']:
                text = await self._extract_docx_text(file_path)
            elif file_extension in ['.xlsx', '.xls']:
                text = await self._extract_excel_text(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")

            # Create chunks
            chunks = await self._create_chunks(text, file_path, domain)
            logger.info(f"Created {len(chunks)} chunks from {file_path}")
            return chunks

        except Exception as e:
            logger.error(f"Failed to process document {file_path}: {e}")
            raise

    async def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF file"""
        def extract_text():
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text

        return await asyncio.to_thread(extract_text)

    async def _extract_text_file(self, file_path: str) -> str:
        """Extract text from text file"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()

    async def _extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        def extract_text():
            doc = DocxDocument(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text

        return await asyncio.to_thread(extract_text)

    async def _extract_excel_text(self, file_path: str) -> str:
        """Extract text from Excel file"""
        def extract_text():
            df = pd.read_excel(file_path)
            # Convert DataFrame to text representation
            text = df.to_string(index=False)
            return text

        return await asyncio.to_thread(extract_text)

    async def _create_chunks(
        self,
        text: str,
        file_path: str,
        domain: DocumentDomain
    ) -> List[DocumentChunk]:
        """Create document chunks with metadata"""
        chunks = []

        # Clean and prepare text
        text = text.strip()
        if not text:
            return chunks

        # Calculate chunk size in tokens if tokenizer is available
        if self.tokenizer:
            chunk_size = settings.chunk_size
            overlap = settings.chunk_overlap
        else:
            # Fallback to character-based chunking
            chunk_size = settings.chunk_size * 4  # Approximate characters per token
            overlap = settings.chunk_overlap * 4

        # Simple text chunking strategy
        sentences = text.split('. ')
        current_chunk = ""
        chunk_index = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if adding this sentence exceeds chunk size
            potential_chunk = current_chunk + ". " + sentence if current_chunk else sentence

            if self.tokenizer:
                token_count = len(self.tokenizer.encode(potential_chunk))
                should_split = token_count > chunk_size
            else:
                should_split = len(potential_chunk) > chunk_size

            if should_split and current_chunk:
                # Create chunk
                chunk = DocumentChunk(
                    text=current_chunk.strip(),
                    chunk_index=chunk_index,
                    metadata={
                        "file_name": Path(file_path).name,
                        "file_path": file_path,
                        "domain": domain,
                        "chunk_index": chunk_index,
                        "token_count": len(self.tokenizer.encode(current_chunk)) if self.tokenizer else len(current_chunk) // 4,
                        "created_at": datetime.now().isoformat()
                    }
                )
                chunks.append(chunk)

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk, overlap)
                current_chunk = overlap_text + ". " + sentence if overlap_text else sentence
                chunk_index += 1
            else:
                current_chunk = potential_chunk

        # Add final chunk
        if current_chunk.strip():
            chunk = DocumentChunk(
                text=current_chunk.strip(),
                chunk_index=chunk_index,
                metadata={
                    "file_name": Path(file_path).name,
                    "file_path": file_path,
                    "domain": domain,
                    "chunk_index": chunk_index,
                    "token_count": len(self.tokenizer.encode(current_chunk)) if self.tokenizer else len(current_chunk) // 4,
                    "created_at": datetime.now().isoformat()
                }
            )
            chunks.append(chunk)

        return chunks

    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get overlap text from the end of current chunk"""
        if self.tokenizer:
            tokens = self.tokenizer.encode(text)
            if len(tokens) <= overlap_size:
                return text
            overlap_tokens = tokens[-overlap_size:]
            return self.tokenizer.decode(overlap_tokens)
        else:
            # Character-based overlap
            if len(text) <= overlap_size:
                return text
            return text[-overlap_size:]

    async def delete_file(self, file_path: str) -> bool:
        """Delete file from filesystem"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False

    def validate_file(self, filename: str, file_size: int) -> tuple[bool, str]:
        """Validate uploaded file"""
        # Check file extension
        file_extension = Path(filename).suffix.lower()
        if file_extension not in settings.allowed_file_types:
            return False, f"File type {file_extension} not allowed"

        # Check file size
        if file_size > settings.max_file_size:
            return False, f"File size {file_size} exceeds maximum {settings.max_file_size}"

        return True, "Valid"

    def get_supported_domains(self) -> List[str]:
        """Get list of supported document domains"""
        return settings.analysis_domains