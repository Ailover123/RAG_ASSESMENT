import asyncio
import logging
import zipfile
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.chunking.splitter import split_documents
from app.config import settings
from app.dependencies import get_embedder, get_vector_store
from app.embeddings.embedder import Embedder
from app.ingestion.router import extract_documents
from app.security import get_session_id, sanitize_filename
from app.vectorstore.chroma_client import VectorStore

router = APIRouter()
logger = logging.getLogger(__name__)
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx"}
ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


def validate_signature(path: Path, extension: str) -> None:
    with path.open("rb") as source:
        signature = source.read(8)
    if extension == ".pdf":
        valid = signature.startswith(b"%PDF-")
    else:
        valid = signature.startswith(ZIP_SIGNATURES)
        if valid:
            try:
                with zipfile.ZipFile(path) as archive:
                    names = set(archive.namelist())
                    expected_prefix = "word/" if extension == ".docx" else "ppt/"
                    valid = "[Content_Types].xml" in names and any(name.startswith(expected_prefix) for name in names)
            except (zipfile.BadZipFile, OSError):
                valid = False
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File content does not match its extension.")


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Depends(get_session_id),
    embedder: Embedder = Depends(get_embedder),
    vector_store: VectorStore = Depends(get_vector_store),
) -> Dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a valid filename.")
    safe_name = sanitize_filename(file.filename)
    extension = Path(safe_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file format. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

    session_dir = settings.UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    save_path = session_dir / f"{uuid4().hex}{extension}"
    bytes_written = 0
    try:
        async with aiofiles.open(save_path, "xb") as output:
            while chunk := await file.read(1024 * 1024):
                bytes_written += len(chunk)
                if bytes_written > settings.MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail=f"File exceeds the {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit.")
                await output.write(chunk)
        validate_signature(save_path, extension)
        documents = await asyncio.to_thread(extract_documents, save_path)
        for document in documents:
            document.source = safe_name
            document.metadata["filename"] = safe_name
        chunks = split_documents(documents)
        if chunks:
            embeddings = await asyncio.to_thread(embedder.embed_documents, chunks)
            await asyncio.to_thread(vector_store.add, chunks, embeddings, session_id)
        return {"filename": safe_name, "chunks_added": len(chunks), "status": "success"}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Document ingestion failed", extra={"session_id": session_id})
        raise HTTPException(status_code=500, detail="The document could not be processed. Check that it is a valid, readable file.")
    finally:
        await file.close()
        save_path.unlink(missing_ok=True)
        try:
            session_dir.rmdir()
        except OSError:
            pass
