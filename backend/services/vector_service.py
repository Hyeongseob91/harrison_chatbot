import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
import logging
from sentence_transformers import SentenceTransformer
import asyncio
from config import settings
from models import VectorSearchResult, DocumentChunk

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        self.client = None
        self.collection = None
        self.embedding_model = None

    async def initialize(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Initialize ChromaDB client
            self.client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
                settings=ChromaSettings(
                    allow_reset=True,
                    anonymized_telemetry=False
                )
            )

            # Initialize embedding model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name=settings.collection_name
                )
                logger.info(f"Retrieved existing collection: {settings.collection_name}")
            except:
                self.collection = self.client.create_collection(
                    name=settings.collection_name,
                    metadata={"description": "Document analysis chatbot collection"}
                )
                logger.info(f"Created new collection: {settings.collection_name}")

        except Exception as e:
            logger.error(f"Failed to initialize vector service: {e}")
            raise

    async def health_check(self) -> str:
        """Check if vector service is healthy"""
        try:
            if self.client is None:
                return "not_initialized"

            # Try to list collections
            collections = self.client.list_collections()
            return "connected"
        except Exception as e:
            logger.error(f"Vector service health check failed: {e}")
            return "disconnected"

    async def add_documents(self, chunks: List[DocumentChunk], document_id: int) -> List[str]:
        """Add document chunks to vector database"""
        try:
            if not chunks:
                return []

            # Prepare data for ChromaDB
            texts = [chunk.text for chunk in chunks]
            metadatas = []
            ids = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"doc_{document_id}_chunk_{i}"
                metadata = {
                    **chunk.metadata,
                    "document_id": document_id,
                    "chunk_index": i
                }
                metadatas.append(metadata)
                ids.append(chunk_id)

            # Generate embeddings
            embeddings = await asyncio.to_thread(
                self.embedding_model.encode,
                texts,
                convert_to_numpy=True
            )

            # Add to ChromaDB
            self.collection.add(
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"Added {len(chunks)} chunks for document {document_id}")
            return ids

        except Exception as e:
            logger.error(f"Failed to add documents to vector DB: {e}")
            raise

    async def search_similar(
        self,
        query: str,
        top_k: int = 5,
        document_ids: Optional[List[int]] = None,
        domain: Optional[str] = None
    ) -> List[VectorSearchResult]:
        """Search for similar documents"""
        try:
            # Generate query embedding
            query_embedding = await asyncio.to_thread(
                self.embedding_model.encode,
                [query],
                convert_to_numpy=True
            )

            # Build where clause for filtering
            where_clause = {}
            if document_ids:
                where_clause["document_id"] = {"$in": document_ids}
            if domain and domain != "general":
                where_clause["domain"] = domain

            # Search in ChromaDB
            search_kwargs = {
                "query_embeddings": query_embedding.tolist(),
                "n_results": top_k
            }

            if where_clause:
                search_kwargs["where"] = where_clause

            results = self.collection.query(**search_kwargs)

            # Convert to VectorSearchResult objects
            search_results = []
            if results['documents'][0]:  # Check if results exist
                for i in range(len(results['documents'][0])):
                    result = VectorSearchResult(
                        chunk_text=results['documents'][0][i],
                        score=1.0 - results['distances'][0][i],  # Convert distance to similarity
                        document_name=results['metadatas'][0][i].get('file_name', 'Unknown'),
                        chunk_index=results['metadatas'][0][i].get('chunk_index', 0),
                        metadata=results['metadatas'][0][i]
                    )
                    search_results.append(result)

            logger.info(f"Found {len(search_results)} similar chunks for query")
            return search_results

        except Exception as e:
            logger.error(f"Failed to search similar documents: {e}")
            return []

    async def delete_document(self, document_id: int) -> bool:
        """Delete all chunks for a document"""
        try:
            # Find all chunks for this document
            results = self.collection.get(
                where={"document_id": document_id}
            )

            if results['ids']:
                # Delete the chunks
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "collection_name": settings.collection_name
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"total_chunks": 0, "collection_name": settings.collection_name}