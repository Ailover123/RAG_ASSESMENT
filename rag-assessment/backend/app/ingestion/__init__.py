"""Document ingestion and parsing package."""
from app.ingestion.base import Document, BaseAdapter
from app.ingestion.pdf_adapter import PDFAdapter
from app.ingestion.docx_adapter import DocxAdapter
from app.ingestion.pptx_adapter import PptxAdapter
from app.ingestion.router import IngestionRouter, get_adapter, extract_documents

__all__ = [
    "Document",
    "BaseAdapter",
    "PDFAdapter",
    "DocxAdapter",
    "PptxAdapter",
    "IngestionRouter",
    "get_adapter",
    "extract_documents",
]
