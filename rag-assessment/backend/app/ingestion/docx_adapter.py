from pathlib import Path
from typing import List, Union
from docx import Document as DocxReader

from app.ingestion.base import BaseAdapter, Document


class DocxAdapter(BaseAdapter):
    """Adapter for extracting text and metadata from DOCX files using python-docx."""

    def __init__(self, paragraphs_per_block: int = 5, max_chars_per_block: int = 1500):
        """
        Initialize DocxAdapter with grouping thresholds.

        Args:
            paragraphs_per_block: Target number of non-empty paragraphs per text block.
            max_chars_per_block: Target maximum characters per block before creating a new Document.
        """
        self.paragraphs_per_block = paragraphs_per_block
        self.max_chars_per_block = max_chars_per_block

    def extract(self, file_path: Union[str, Path]) -> List[Document]:
        """
        Extract text from a DOCX file grouped into paragraph blocks.

        Args:
            file_path: Path to the DOCX file.

        Returns:
            List[Document]: List of Document objects grouped by paragraph blocks, page=None.

        Raises:
            FileNotFoundError: If the file does not exist.
            RuntimeError: If the DOCX file is corrupted or cannot be parsed.
        """
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"DOCX file not found: {file_path}")

        try:
            doc = DocxReader(str(path))
            raw_paragraphs: List[str] = []

            # Extract text from paragraphs
            for p in doc.paragraphs:
                cleaned = p.text.strip()
                if cleaned:
                    raw_paragraphs.append(cleaned)

            # Also extract text from tables if present
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        raw_paragraphs.append(row_text)

            if not raw_paragraphs:
                return []

            # Group paragraphs into reasonably sized blocks
            blocks: List[str] = []
            current_block: List[str] = []
            current_length = 0

            for para in raw_paragraphs:
                current_block.append(para)
                current_length += len(para) + 1  # newline length

                if (
                    len(current_block) >= self.paragraphs_per_block
                    or current_length >= self.max_chars_per_block
                ):
                    blocks.append("\n\n".join(current_block))
                    current_block = []
                    current_length = 0

            if current_block:
                blocks.append("\n\n".join(current_block))

            total_blocks = len(blocks)
            documents: List[Document] = [
                Document(
                    text=block_text,
                    source=path.name,
                    page=None,
                    metadata={
                        "filename": path.name,
                        "format": "docx",
                        "block_index": idx + 1,
                        "total_blocks": total_blocks,
                    },
                )
                for idx, block_text in enumerate(blocks)
            ]

            return documents

        except Exception as e:
            raise RuntimeError(f"Failed to read or parse DOCX file '{path.name}': {e}") from e
