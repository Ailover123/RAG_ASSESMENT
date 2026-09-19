from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_vector_store
from app.vectorstore.chroma_client import VectorStore

router = APIRouter()


@router.get("/documents")
async def list_documents_endpoint(
    vector_store: VectorStore = Depends(get_vector_store),
) -> Dict[str, Any]:
    """
    GET /documents endpoint.
    
    Retrieves the unique source filenames currently indexed in the vector store.
    
    Args:
        vector_store: Injected VectorStore instance.
        
    Returns:
        JSON response with list of indexed document names: {"documents": [...]}
    """
    try:
        documents = vector_store.list_documents()
        return {"documents": documents}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch indexed documents: {str(exc)}",
        ) from exc
