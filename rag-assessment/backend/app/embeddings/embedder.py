from typing import List, Optional
from sentence_transformers import SentenceTransformer

from app.chunking.splitter import Chunk
from app.config import settings


class Embedder:
    """
    Dense vector embedding generator using sentence-transformers.

    Architectural Decision:
        The SentenceTransformer model is loaded once during class instantiation
        (__init__) rather than per method call. Loading a transformer model into
        memory requires reading weights from disk, initializing neural network layers,
        and allocating GPU/RAM resources, which can take several seconds. By loading
        once at initialization, subsequent inference calls (embed_documents, embed_query)
        execute rapidly with minimal latency overhead.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the embedding model.

        Args:
            model_name: Sentence-transformers model name or HuggingFace path.
                        Defaults to settings.EMBEDDING_MODEL_NAME ("all-MiniLM-L6-v2").
        """
        self.model_name: str = model_name or settings.EMBEDDING_MODEL_NAME or "all-MiniLM-L6-v2"
        self.model: SentenceTransformer = SentenceTransformer(self.model_name)

    def embed_documents(self, chunks: List[Chunk]) -> List[List[float]]:
        """
        Generate embedding vectors for a list of document chunks.

        Args:
            chunks: List of Chunk objects from the chunking module.

        Returns:
            List[List[float]]: List of float embedding vectors in the same order as chunks.
        """
        if not chunks:
            return []

        texts = [chunk.text for chunk in chunks]
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        """
        Generate a single embedding vector for a user query.

        Args:
            text: Query string.

        Returns:
            List[float]: Float embedding vector representing the query.
        """
        if not text:
            return []

        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
