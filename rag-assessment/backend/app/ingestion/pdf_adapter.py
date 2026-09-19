from pathlib import Path
from typing import List, Union
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.ingestion.base import BaseAdapter, Document


class PDFAdapter(BaseAdapter):
    """Adapter for extracting text and metadata from PDF files using pypdf."""

    def extract(self, file_path: Union[str, Path]) -> List[Document]:
        """
        Extract text per page from a PDF file.

        Args:
            file_path: Path to the PDF file.

        Returns:
            List[Document]: One Document per page with 1-indexed page number and metadata.

        Raises:
            FileNotFoundError: If the file does not exist.
            RuntimeError: If the PDF file is corrupted or cannot be parsed.
        """
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        try:
            reader = PdfReader(str(path))
            total_pages = len(reader.pages)
            documents: List[Document] = []

            for page_idx, page in enumerate(reader.pages):
                page_number = page_idx + 1
                try:
                    text = page.extract_text() or ""
                except Exception as extract_err:
                    raise RuntimeError(
                        f"Error extracting text from page {page_number} of PDF '{path.name}': {extract_err}"
                    ) from extract_err

                documents.append(
                    Document(
                        text=text.strip(),
                        source=path.name,
                        page=page_number,
                        metadata={
                            "filename": path.name,
                            "format": "pdf",
                            "page": page_number,
                            "total_pages": total_pages,
                        },
                    )
                )

            return documents

        except (PdfReadError, Exception) as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Failed to read or parse PDF file '{path.name}': {e}") from e
