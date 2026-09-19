from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Union


@dataclass
class Document:
    """
    Standard normalized document schema for RAG pipeline.

    Attributes:
        text: Extracted text content of the document or document page/slide/block.
        source: Source filename or identifier.
        page: Page number or slide number (1-indexed, Optional).
        metadata: Metadata dictionary containing at minimum 'filename' and 'format'.
    """
    text: str
    source: str
    page: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure default metadata contains at minimum filename and format if derivable."""
        if "filename" not in self.metadata and self.source:
            self.metadata["filename"] = Path(self.source).name
        if "format" not in self.metadata and self.source:
            ext = Path(self.source).suffix.lower().lstrip(".")
            if ext:
                self.metadata["format"] = ext


class BaseAdapter(ABC):
    """Abstract base class for file format adapters."""

    @abstractmethod
    def extract(self, file_path: Union[str, Path]) -> List[Document]:
        """
        Extract text and structure from a source file into a list of Document objects.

        Args:
            file_path: Path to the target document.

        Returns:
            List[Document]: Extracted normalized Document dataclass instances.
        """
        pass
