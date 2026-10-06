from .config import CODES, CODES2, PDF_FOLDER, PDF_FOLDER2, WORKERS
from .auth import get_token
from .client import get_table_matieres, collect_article_ids, get_article_content
from .pdf_writer import traiter_article

__all__ = [
    "CODES", "CODES2", "PDF_FOLDER", "PDF_FOLDER2", "WORKERS",
    "get_token",
    "get_table_matieres", "collect_article_ids", "get_article_content",
    "traiter_article",
]
