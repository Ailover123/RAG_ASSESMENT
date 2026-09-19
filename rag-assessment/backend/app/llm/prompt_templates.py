from typing import Any, Dict, List


SYSTEM_PROMPT = (
    "You are a retrieval-augmented assistant. Answer ONLY using the provided "
    "context. If the answer is not present in the context, say explicitly that "
    "the provided context does not contain enough information to answer. Do not "
    "guess or use outside knowledge. Cite the source filename and page or slide "
    "number when possible. Format the answer as clean Markdown. Use short "
    "paragraphs and headings when useful. For comparisons, use a valid Markdown "
    "table with a blank line before it, one row per line, and this exact shape: "
    "| Column A | Column B |\\n| --- | --- |\\n| Value | Value |. Never put table pipes "
    "inside a normal paragraph. For processes or relationships, use a fenced "
    "Mermaid diagram with a blank line before and after it, for example "
    "```mermaid\\nflowchart TD\\n A[Start] --> B[End]\\n```. Keep prose outside "
    "tables and diagrams."
)


def _chunk_text(chunk: Dict[str, Any]) -> str:
    return str(
        chunk.get("text")
        or chunk.get("document")
        or chunk.get("content")
        or ""
    ).strip()


def _chunk_metadata(chunk: Dict[str, Any]) -> Dict[str, Any]:
    metadata = chunk.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _chunk_source(chunk: Dict[str, Any]) -> str:
    metadata = _chunk_metadata(chunk)
    return str(
        chunk.get("source")
        or metadata.get("source")
        or metadata.get("filename")
        or "unknown source"
    )


def _chunk_page(chunk: Dict[str, Any]) -> Any:
    metadata = _chunk_metadata(chunk)
    return chunk.get("page") or metadata.get("page") or metadata.get("slide")


def _format_context(retrieved_chunks: List[Dict[str, Any]]) -> str:
    blocks = []
    for index, chunk in enumerate(retrieved_chunks, start=1):
        text = _chunk_text(chunk)
        if not text:
            continue

        source = _chunk_source(chunk)
        page = _chunk_page(chunk)
        label = f"Source: {source}"
        if page is not None:
            label += f", page/slide: {page}"

        blocks.append(f"[{index}] {label}\n{text}")

    return "\n\n".join(blocks) if blocks else "No context was retrieved."


def build_rag_prompt(query: str, retrieved_chunks: List[dict]) -> List[Dict[str, str]]:
    """Build chat messages for a grounded RAG answer with source citations."""
    context = _format_context(retrieved_chunks)
    user_prompt = (
        "Context:\n"
        f"{context}\n\n"
        "Question:\n"
        f"{query}\n\n"
        "Answer using only the context above. Include source/page citations when "
        "the context provides them. Return only the answer content in Markdown; "
        "do not describe the formatting rules."
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


class RAGPromptTemplate:
    """Prompt templates for RAG context injection and system instructions."""

    SYSTEM_PROMPT: str = SYSTEM_PROMPT

    @classmethod
    def format_rag_messages(
        cls,
        query: str,
        retrieved_contexts: List[Dict[str, Any]],
        system_prompt: str = SYSTEM_PROMPT,
    ) -> List[Dict[str, str]]:
        """
        Format retrieved context chunks and user question into chat messages.

        Args:
            query: The user question.
            retrieved_contexts: List of retrieved chunks with 'text', 'source', 'page'.
            system_prompt: System instruction prompt.

        Returns:
            List[Dict[str, str]]: Messages payload formatted for LLM completion.
        """
        messages = build_rag_prompt(query, retrieved_contexts)
        if system_prompt != SYSTEM_PROMPT:
            messages[0] = {"role": "system", "content": system_prompt}
        return messages
