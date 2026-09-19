from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import uuid
import chromadb

from app.chunking.splitter import Chunk
from app.config import settings


class VectorStore:
    """
    Vector storage and retrieval client powered by ChromaDB.

    Architectural Decisions:
        1. PersistentClient vs. In-Memory Client:
           ChromaDB's PersistentClient stores vector indices and metadata directly
           on disk ("data/chroma_db"). This ensures that all embedded documents and
           indices persist across server restarts, without requiring documents to be
           re-parsed and re-embedded every time the backend starts.

        2. Embedded vs. Hosted Vector DB:
           Using an embedded SQLite/DuckDB-backed engine (Chroma PersistentClient)
           avoids the operational complexity and network latency of provisioning and
           maintaining external hosted databases (such as Pinecone, Qdrant, or Weaviate).
           This makes the system self-contained, easy to run locally, and ideal for
           rapid assessment and development cycles.
    """

    def __init__(
        self,
        persist_directory: Optional[Union[str, Path]] = None,
        collection_name: str = "documents",
    ):
        """
        Initialize the persistent Chroma client and collection.

        Args:
            persist_directory: Path to on-disk database storage directory.
                               Defaults to settings.CHROMA_PERSIST_DIR or "data/chroma_db".
            collection_name: Name of the vector collection. Defaults to "documents".
        """
        if persist_directory is not None:
            self.persist_directory = str(persist_directory)
        elif hasattr(settings, "CHROMA_PERSIST_DIR") and settings.CHROMA_PERSIST_DIR:
            self.persist_directory = str(settings.CHROMA_PERSIST_DIR)
        else:
            self.persist_directory = "data/chroma_db"

        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, chunks: List[Chunk], embeddings: List[List[float]]) -> List[str]:
        """
        Add chunked documents and their corresponding vector embeddings to ChromaDB.

        Args:
            chunks: List of Chunk objects containing text and metadata.
            embeddings: List of dense vector embeddings for each chunk.

        Returns:
            List[str]: List of unique chunk IDs added to the collection.
        """
        if not chunks:
            return []

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Union[str, int, float, bool]]] = []

        for chunk in chunks:
            chunk_id = f"{chunk.source}_{chunk.page}_{uuid.uuid4().hex[:8]}"
            ids.append(chunk_id)
            documents.append(chunk.text)

            meta: Dict[str, Union[str, int, float, bool]] = {
                "source": str(chunk.source),
                "chunk_index": int(chunk.chunk_index),
            }

            if chunk.page is not None:
                meta["page"] = int(chunk.page)

            # Add any additional valid primitive metadata fields
            if chunk.metadata:
                for k, v in chunk.metadata.items():
                    if k not in meta and isinstance(v, (str, int, float, bool)):
                        meta[k] = v

            metadatas.append(meta)

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return ids

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Run similarity search against the indexed vector collection.

        Args:
            query_embedding: Dense embedding vector for the search query.
            top_k: Number of nearest neighbors to retrieve (default: 5).

        Returns:
            List[Dict[str, Any]]: List of matching results, each containing:
                - text: Chunk text
                - source: Document source filename
                - page: Page or slide number (if applicable)
                - distance: Vector distance score
                - score: Similarity score
        """
        if not query_embedding:
            return []

        total_count = self.collection.count()
        if total_count == 0:
            return []

        n_results = min(max(1, top_k), total_count)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        output: List[Dict[str, Any]] = []

        if not results or not results.get("documents") or not results["documents"][0]:
            return []

        retrieved_docs = results["documents"][0]
        retrieved_metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(retrieved_docs)
        retrieved_distances = results["distances"][0] if results.get("distances") else [0.0] * len(retrieved_docs)

        for doc_text, meta, dist in zip(retrieved_docs, retrieved_metas, retrieved_distances):
            metadata = meta or {}
            score = round(1.0 - dist, 4) if dist is not None else 1.0

            output.append({
                "text": doc_text,
                "source": metadata.get("source", ""),
                "page": metadata.get("page"),
                "distance": dist,
                "score": score,
                "chunk_index": metadata.get("chunk_index"),
                "metadata": metadata,
            })

        return output

    def list_documents(self) -> List[str]:
        """
        Retrieve unique source filenames currently indexed in the vector store.

        Returns:
            List[str]: Alphabetically sorted list of distinct document filenames.
        """
        if self.collection.count() == 0:
            return []

        data = self.collection.get(include=["metadatas"])
        metadatas = data.get("metadatas", [])
        if not metadatas:
            return []

        unique_sources = set()
        for meta in metadatas:
            if meta and "source" in meta and meta["source"]:
                unique_sources.add(str(meta["source"]))
            elif meta and "filename" in meta and meta["filename"]:
                unique_sources.add(str(meta["filename"]))

        return sorted(list(unique_sources))


# Backwards compatibility alias
ChromaVectorStore = VectorStore
