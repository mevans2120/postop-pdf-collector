"""PostOp PDF Collector - A system for collecting and analyzing post-operative instruction PDFs."""

__version__ = "0.1.0"
__author__ = "Your Name"

from .core.collector import PostOpPDFCollector
from .core.models import PDFMetadata, CollectionResult

__all__ = [
    "PostOpPDFCollector",
    "PDFMetadata",
    "CollectionResult",
]