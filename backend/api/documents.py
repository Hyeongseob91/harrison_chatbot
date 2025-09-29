from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import logging
from datetime import datetime

from database import get_db, DocumentUpload, VectorChunk
from models import DocumentUploadResponse, DocumentListResponse, DocumentDomain
from services.document_service import DocumentService
from services.vector_service import VectorService

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize services (will be injected in main.py)
document_service = None
vector_service = None

def set_services(doc_service: DocumentService, vec_service: VectorService):
    global document_service, vector_service
    document_service = doc_service
    vector_service = vec_service
    document_service.set_vector_service(vec_service)

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    domain: DocumentDomain = Form(DocumentDomain.GENERAL),
    db: AsyncSession = Depends(get_db)
):
    """Upload and process a document"""
    try:
        # Validate file
        is_valid, error_msg = document_service.validate_file(file.filename, file.size)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Save file
        file_path = await document_service.save_upload_file(file, session_id)

        # Create database record
        doc_upload = DocumentUpload(
            file_name=file.filename,
            file_path=file_path,
            file_type=file.content_type or "unknown",
            file_size=file.size or 0,
            session_id=session_id,
            domain=domain,
            upload_status="processing"
        )

        db.add(doc_upload)
        await db.commit()
        await db.refresh(doc_upload)

        try:
            # Process document
            chunks = await document_service.process_document(file_path, domain)

            # Add to vector database
            vector_ids = await vector_service.add_documents(chunks, doc_upload.id)

            # Save chunk metadata to database
            for i, (chunk, vector_id) in enumerate(zip(chunks, vector_ids)):
                vector_chunk = VectorChunk(
                    document_id=doc_upload.id,
                    chunk_index=i,
                    chunk_text=chunk.text,
                    vector_id=vector_id,
                    metadata=chunk.metadata
                )
                db.add(vector_chunk)

            # Update document status
            doc_upload.upload_status = "completed"
            doc_upload.vector_count = len(chunks)
            doc_upload.processed_at = datetime.now()

            await db.commit()
            await db.refresh(doc_upload)

            logger.info(f"Successfully processed document {doc_upload.id} with {len(chunks)} chunks")

        except Exception as e:
            # Update status to failed
            doc_upload.upload_status = "failed"
            await db.commit()
            logger.error(f"Failed to process document {doc_upload.id}: {e}")
            raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")

        return DocumentUploadResponse(
            id=doc_upload.id,
            file_name=doc_upload.file_name,
            file_size=doc_upload.file_size,
            upload_status=doc_upload.upload_status,
            domain=doc_upload.domain,
            uploaded_at=doc_upload.uploaded_at,
            vector_count=doc_upload.vector_count
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    session_id: Optional[str] = None,
    domain: Optional[DocumentDomain] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List uploaded documents"""
    try:
        query = select(DocumentUpload)

        # Apply filters
        if session_id:
            query = query.where(DocumentUpload.session_id == session_id)
        if domain:
            query = query.where(DocumentUpload.domain == domain)
        if status:
            query = query.where(DocumentUpload.upload_status == status)

        query = query.order_by(DocumentUpload.uploaded_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        documents = result.scalars().all()

        # Get total count
        count_query = select(DocumentUpload)
        if session_id:
            count_query = count_query.where(DocumentUpload.session_id == session_id)
        if domain:
            count_query = count_query.where(DocumentUpload.domain == domain)
        if status:
            count_query = count_query.where(DocumentUpload.upload_status == status)

        count_result = await db.execute(count_query)
        total_count = len(count_result.scalars().all())

        document_responses = [
            DocumentUploadResponse(
                id=doc.id,
                file_name=doc.file_name,
                file_size=doc.file_size,
                upload_status=doc.upload_status,
                domain=doc.domain,
                uploaded_at=doc.uploaded_at,
                vector_count=doc.vector_count
            )
            for doc in documents
        ]

        return DocumentListResponse(
            documents=document_responses,
            total_count=total_count
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@router.get("/{document_id}", response_model=DocumentUploadResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get document details"""
    try:
        result = await db.execute(
            select(DocumentUpload).where(DocumentUpload.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return DocumentUploadResponse(
            id=document.id,
            file_name=document.file_name,
            file_size=document.file_size,
            upload_status=document.upload_status,
            domain=document.domain,
            uploaded_at=document.uploaded_at,
            vector_count=document.vector_count
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a document"""
    try:
        # Get document
        result = await db.execute(
            select(DocumentUpload).where(DocumentUpload.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete from vector database
        await vector_service.delete_document(document_id)

        # Delete file from filesystem
        await document_service.delete_file(document.file_path)

        # Delete from database (cascade will delete vector chunks)
        await db.delete(document)
        await db.commit()

        logger.info(f"Deleted document {document_id}")
        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Reprocess a document"""
    try:
        # Get document
        result = await db.execute(
            select(DocumentUpload).where(DocumentUpload.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete existing vectors
        await vector_service.delete_document(document_id)

        # Delete existing chunks from database
        await db.execute(
            select(VectorChunk).where(VectorChunk.document_id == document_id)
        )

        # Reprocess document
        document.upload_status = "processing"
        document.vector_count = 0
        await db.commit()

        # Process document
        chunks = await document_service.process_document(document.file_path, document.domain)

        # Add to vector database
        vector_ids = await vector_service.add_documents(chunks, document.id)

        # Save chunk metadata
        for i, (chunk, vector_id) in enumerate(zip(chunks, vector_ids)):
            vector_chunk = VectorChunk(
                document_id=document.id,
                chunk_index=i,
                chunk_text=chunk.text,
                vector_id=vector_id,
                metadata=chunk.metadata
            )
            db.add(vector_chunk)

        # Update status
        document.upload_status = "completed"
        document.vector_count = len(chunks)
        document.processed_at = datetime.now()
        await db.commit()

        logger.info(f"Reprocessed document {document_id} with {len(chunks)} chunks")
        return {"message": "Document reprocessed successfully", "chunk_count": len(chunks)}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to reprocess document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reprocess document: {str(e)}")

@router.get("/domains/list")
async def list_supported_domains():
    """Get list of supported document domains"""
    return {
        "domains": document_service.get_supported_domains(),
        "default": "general"
    }