from pathlib import Path
from typing import Dict, List, Union

from app.ingestion.base import BaseAdapter, Document
from app.ingestion.pdf_adapter import PDFAdapter
from app.ingestion.docx_adapter import DocxAdapter
from app.ingestion.pptx_adapter import PptxAdapter

# Supported adapters registry mapping file extension to adapter instance
ADAPTER_MAP: Dict[str, BaseAdapter] = {
    ".pdf": PDFAdapter(),
    ".docx": DocxAdapter(),
    ".pptx": PptxAdapter(),
}


def get_adapter(file_path: Union[str, Path]) -> BaseAdapter:
    """
    Inspect the file extension (.pdf, .docx, .pptx) and return the matching BaseAdapter.

    Args:
        file_path: Path to the document.

    Returns:
        BaseAdapter: Instance of the adapter suited for the given file extension.

    Raises:
        ValueError: If the file format is unsupported or has no extension.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if not ext:
        raise ValueError(f"File '{path.name}' has no extension. Supported formats: {', '.join(ADAPTER_MAP.keys())}")

    adapter = ADAPTER_MAP.get(ext)
    if adapter is None:
        supported = ", ".join(ADAPTER_MAP.keys())
        raise ValueError(
            f"Unsupported file format '{ext}' for file '{path.name}'. Supported formats: {supported}"
        )

    return adapter


def extract_documents(file_path: Union[str, Path]) -> List[Document]:
    """
    Route a file to its appropriate format adapter and extract Document objects.

    Args:
        file_path: Path to the file to ingest.

    Returns:
        List[Document]: List of extracted Document dataclass objects.

    Raises:
        ValueError: If the file format is unsupported.
        FileNotFoundError: If the target file does not exist.
        RuntimeError: If file parsing fails or the file is corrupted.
    """
    adapter = get_adapter(file_path)
    return adapter.extract(file_path)


class IngestionRouter:
    """Router helper class providing instance-based access and custom adapter registration."""

    def __init__(self):
        self._adapters: Dict[str, BaseAdapter] = {
            ".pdf": PDFAdapter(),
            ".docx": DocxAdapter(),
            ".pptx": PptxAdapter(),
        }

    def register_adapter(self, extension: str, adapter: BaseAdapter) -> None:
        """
        Register a custom adapter for a file extension.

        Args:
            extension: File extension including leading dot (e.g. '.txt').
            adapter: Instance of BaseAdapter.
        """
        self._adapters[extension.lower()] = adapter

    def get_adapter(self, file_path: Union[str, Path]) -> BaseAdapter:
        """
        Determine and return the correct adapter for a given file path.

        Args:
            file_path: Path to the target file.

        Returns:
            BaseAdapter: Matching format adapter.

        Raises:
            ValueError: If file format is unsupported.
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        if ext not in self._adapters:
            supported = ", ".join(self._adapters.keys())
            raise ValueError(f"Unsupported file format '{ext}'. Supported formats: {supported}")
        return self._adapters[ext]

    def parse_file(self, file_path: Union[str, Path]) -> List[Document]:
        """
        Parse a file by dynamically selecting the appropriate adapter.

        Args:
            file_path: Path to the document.

        Returns:
            List[Document]: List of extracted Document objects.
        """
        adapter = self.get_adapter(file_path)
        return adapter.extract(file_path)
