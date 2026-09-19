import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.config import settings
from app.ingestion.base import Document


@dataclass
class Chunk:
    """A chunk of source text ready for embedding and retrieval."""

    text: str
    source: str
    page: Optional[int]
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _split_words(text: str, chunk_size: int, chunk_overlap: int = 0) -> List[str]:
    words = text.split()
    if not words:
        return []

    step = max(1, chunk_size - max(0, chunk_overlap))
    chunks = []
    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size]
        if chunk_words:
            chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):
            break
    return chunks


def _split_sentences(text: str) -> List[str]:
    pieces = re.split(r"(?<=[.!?])\s+", text.strip())
    return [piece.strip() for piece in pieces if piece.strip()]


def _recursive_units(text: str, chunk_size: int) -> List[str]:
    text = text.strip()
    if not text:
        return []
    if _word_count(text) <= chunk_size:
        return [text]

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n+", text)
        if paragraph.strip()
    ]
    if len(paragraphs) > 1:
        units: List[str] = []
        for paragraph in paragraphs:
            units.extend(_recursive_units(paragraph, chunk_size))
        return units

    sentences = _split_sentences(text)
    if len(sentences) > 1:
        units = []
        for sentence in sentences:
            if _word_count(sentence) <= chunk_size:
                units.append(sentence)
            else:
                units.extend(_split_words(sentence, chunk_size))
        return units

    return _split_words(text, chunk_size)


def _join_units(units: List[str]) -> str:
    return "\n\n".join(unit for unit in units if unit.strip()).strip()


def _overlap_from_text(text: str, max_words: int) -> str:
    if max_words <= 0:
        return ""

    sentences = _split_sentences(text)
    selected: List[str] = []
    selected_words = 0

    for sentence in reversed(sentences):
        sentence_words = _word_count(sentence)
        if sentence_words > max_words:
            break
        if selected_words + sentence_words > max_words:
            break
        selected.insert(0, sentence)
        selected_words += sentence_words

    if selected:
        return " ".join(selected)

    words = text.split()
    return " ".join(words[-max_words:])


def split_text(
    text: str,
    chunk_size: int = 600,
    chunk_overlap: int = 80,
) -> List[str]:
    """
    Split text into retrieval chunks while preserving semantic boundaries.

    Recursive splitting is used instead of fixed-size character chunking because
    paragraphs and sentences usually map to complete ideas. Keeping those ideas
    intact gives embeddings better context and avoids brittle chunks that start
    or stop halfway through a sentence. Word-boundary splitting is only used as
    the final fallback, so chunks are never cut mid-word.

    PPT slides are treated as atomic units by default in split_documents because
    each slide is already a natural semantic boundary: its title, bullets, and
    notes normally belong together. Oversized slides are still sub-split so they
    fit the configured chunk size.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be greater than or equal to 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    units = _recursive_units(text, chunk_size)
    if not units:
        return []

    chunks: List[str] = []
    current_units: List[str] = []
    current_words = 0

    for unit in units:
        unit_words = _word_count(unit)
        if not current_units:
            current_units = [unit]
            current_words = unit_words
            continue

        if current_words + unit_words <= chunk_size:
            current_units.append(unit)
            current_words += unit_words
            continue

        previous_chunk = _join_units(current_units)
        chunks.append(previous_chunk)

        overlap_budget = min(chunk_overlap, max(0, chunk_size - unit_words))
        overlap = _overlap_from_text(previous_chunk, overlap_budget)
        current_units = [overlap, unit] if overlap else [unit]
        current_words = _word_count(_join_units(current_units))

    if current_units:
        chunks.append(_join_units(current_units))

    return chunks


def _split_documents(
    documents: List[Document],
    chunk_size: int,
    chunk_overlap: int,
) -> List[Chunk]:
    """Split ingested documents into chunks while preserving source metadata."""
    chunks: List[Chunk] = []

    for document in documents:
        metadata = dict(document.metadata or {})
        document_format = str(metadata.get("format", "")).lower()
        text = document.text or ""

        if document_format == "pptx" and _word_count(text) <= chunk_size:
            document_chunks = [text.strip()] if text.strip() else []
        else:
            document_chunks = split_text(
                text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

        for chunk_index, chunk_text in enumerate(document_chunks):
            chunk_metadata = {**metadata, "chunk_index": chunk_index}
            chunks.append(
                Chunk(
                    text=chunk_text,
                    source=document.source,
                    page=document.page,
                    chunk_index=chunk_index,
                    metadata=chunk_metadata,
                )
            )

    return chunks


def split_documents(documents: List[Document]) -> List[Chunk]:
    """Split ingested documents into chunks using the configured chunk settings."""
    return _split_documents(
        documents,
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )


class TextSplitter:
    """Compatibility wrapper around the module-level chunking functions."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        separators: Optional[List[str]] = None,
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.separators = separators or ["\n\n", ".", " ", ""]

    def split_text(self, text: str) -> List[str]:
        return split_text(text, self.chunk_size, self.chunk_overlap)

    def split_documents(self, documents: List[Document]) -> List[Chunk]:
        return _split_documents(documents, self.chunk_size, self.chunk_overlap)
