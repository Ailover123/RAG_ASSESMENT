from typing import Optional
from app.config import settings
from app.embeddings.embedder import Embedder
from app.vectorstore.chroma_client import VectorStore
from app.llm.groq_client import GroqClient

# Module-level singletons (initialized once)
_embedder: Optional[Embedder] = None
_vector_store: Optional[VectorStore] = None
_groq_client: Optional[GroqClient] = None


def get_embedder() -> Embedder:
    """Dependency provider for Embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


def get_vector_store() -> VectorStore:
    """Dependency provider for VectorStore instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(
            persist_directory=settings.CHROMA_PERSIST_DIR,
            collection_name=settings.CHROMA_COLLECTION_NAME,
        )
    return _vector_store


def get_groq_client() -> GroqClient:
    """Dependency provider for GroqClient instance."""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client
