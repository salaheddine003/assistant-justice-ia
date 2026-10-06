"""
Tests unitaires — rag/config.py
Vérifie la cohérence et les types des constantes de configuration RAG.
"""
import pytest
from pathlib import Path

from rag.config import (
    MODEL_NAME,
    PDF_FOLDER,
    INDEX_PATH,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TOP_K,
    SCORE_THRESHOLD,
    GEMMA_MODEL,
)


class TestModelConfig:
    def test_model_name_is_string(self):
        assert isinstance(MODEL_NAME, str)

    def test_model_name_not_empty(self):
        assert len(MODEL_NAME.strip()) > 0

    def test_model_name_is_multilingual(self):
        assert "multilingual" in MODEL_NAME.lower()

    def test_gemma_model_is_string(self):
        assert isinstance(GEMMA_MODEL, str)

    def test_gemma_model_not_empty(self):
        assert len(GEMMA_MODEL.strip()) > 0


class TestIndexConfig:
    def test_pdf_folder_is_path(self):
        assert isinstance(PDF_FOLDER, Path)

    def test_index_path_is_string(self):
        assert isinstance(INDEX_PATH, str)

    def test_index_path_not_empty(self):
        assert len(INDEX_PATH.strip()) > 0


class TestChunkingConfig:
    def test_chunk_size_positive(self):
        assert CHUNK_SIZE > 0

    def test_chunk_overlap_non_negative(self):
        assert CHUNK_OVERLAP >= 0

    def test_overlap_strictly_less_than_chunk_size(self):
        assert CHUNK_OVERLAP < CHUNK_SIZE

    def test_chunk_size_reasonable_range(self):
        # Between 200 and 10000 chars
        assert 200 <= CHUNK_SIZE <= 10000


class TestQueryConfig:
    def test_top_k_positive(self):
        assert TOP_K > 0

    def test_top_k_reasonable(self):
        assert 1 <= TOP_K <= 200

    def test_score_threshold_positive(self):
        assert SCORE_THRESHOLD > 0

    def test_score_threshold_in_l2_range(self):
        # L2 distance thresholds for FAISS are typically 0.5–3.0
        assert 0.3 <= SCORE_THRESHOLD <= 5.0
