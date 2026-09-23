import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.dependencies import get_embedder, get_vector_store, get_groq_client
from app.embeddings.embedder import Embedder
from app.llm.groq_client import GroqClient
from app.vectorstore.chroma_client import VectorStore
from app.security import get_session_id

router = APIRouter()


class QueryRequest(BaseModel):
    """Request payload for RAG query endpoint."""
    question: str = Field(..., min_length=1, description="User question or query.")
    top_k: int = Field(default=4, ge=1, le=20, description="Number of context chunks to retrieve.")


@router.post("/query")
async def query_endpoint(
    request: QueryRequest,
    session_id: str = Depends(get_session_id),
    embedder: Embedder = Depends(get_embedder),
    vector_store: VectorStore = Depends(get_vector_store),
    groq_client: GroqClient = Depends(get_groq_client),
):
    """
    POST /query endpoint.
    
    Embeds the user question, queries ChromaDB for top-k matching context chunks,
    and streams LLM-generated answers via Server-Sent Events (SSE).
    
    Args:
        request: QueryRequest containing the question and optional top_k.
        embedder: Injected Embedder instance.
        vector_store: Injected VectorStore instance.
        groq_client: Injected GroqClient instance.
        
    Returns:
        StreamingResponse (media_type="text/event-stream") emitting "data: {...}\n\n"
    """
    clean_question = request.question.strip()
    if not clean_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or whitespace only.",
        )

    try:
        # Generate query embedding
        query_embedding = embedder.embed_query(clean_question)

        # Retrieve matching chunks from vector store
        retrieved_chunks = vector_store.query(
            query_embedding=query_embedding,
            top_k=request.top_k,
            session_id=session_id,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The document search could not be completed.",
        )

    def sse_generator():
        citations = []
        for chunk in retrieved_chunks:
            metadata = chunk.get("metadata") or {}
            source = chunk.get("source") or metadata.get("filename") or metadata.get("source")
            if source:
                citations.append({
                    "source": str(source),
                    "page": chunk.get("page") or metadata.get("page") or metadata.get("slide"),
                    "score": chunk.get("score"),
                })

        yield f"data: {json.dumps({'type': 'metadata', 'model': groq_client.model, 'citations': citations})}\n\n"

        # If no documents exist in vector store, stream back informative notice
        if not retrieved_chunks:
            yield f"data: {json.dumps({'type': 'token', 'token': 'No documents are available in the system yet. Please upload a document first.'})}\n\n"
            return

        try:
            for token in groq_client.generate_stream(clean_question, retrieved_chunks):
                yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
        except Exception:
            yield f"data: {json.dumps({'type': 'error', 'message': 'The answer could not be completed.'})}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
