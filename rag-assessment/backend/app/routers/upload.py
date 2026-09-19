from pathlib import Path
from typing import Any, Dict
import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.chunking.splitter import split_documents
from app.config import settings
from app.dependencies import get_embedder, get_vector_store
from app.embeddings.embedder import Embedder
from app.ingestion.router import extract_documents
from app.vectorstore.chroma_client import VectorStore

router = APIRouter()

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx"}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    embedder: Embedder = Depends(get_embedder),
    vector_store: VectorStore = Depends(get_vector_store),
) -> Dict[str, Any]:
    """
    POST /upload endpoint.
    
    Accepts a document file (.pdf, .docx, .pptx), saves it asynchronously using aiofiles,
    and runs the full ingestion -> chunking -> embedding -> vector store indexing pipeline.
    
    Args:
        file: Uploaded file object from multipart/form-data.
        embedder: Injected Embedder instance.
        vector_store: Injected VectorStore instance.
        
    Returns:
        JSON response with upload status and chunk count.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported_str = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported formats: {supported_str}",
        )

    try:
        # Ensure upload directory exists
        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        save_path = settings.UPLOAD_DIR / file.filename

        # Save file asynchronously
        async with aiofiles.open(save_path, "wb") as out_file:
            while chunk_data := await file.read(1024 * 1024):
                await out_file.write(chunk_data)

        # Run ingestion pipeline
        documents = extract_documents(save_path)
        chunks = split_documents(documents)

        # Generate embeddings and store in ChromaDB
        if chunks:
            embeddings = embedder.embed_documents(chunks)
            vector_store.add(chunks, embeddings)

        return {
            "filename": file.filename,
            "chunks_added": len(chunks),
            "status": "success",
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process and index document '{file.filename}': {str(exc)}",
        ) from exc
