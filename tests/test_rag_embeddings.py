"""
Tests unitaires — rag/embeddings.py
Teste le singleton get_embeddings() : chargement unique, réutilisation, paramètres.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestGetEmbeddings:
    def setup_method(self):
        """Réinitialise le singleton avant chaque test."""
        import rag.embeddings as emb_mod
        emb_mod._embeddings_instance = None

    def test_returns_non_none(self):
        mock_emb = MagicMock()
        with patch("langchain_huggingface.HuggingFaceEmbeddings", return_value=mock_emb):
            from rag.embeddings import get_embeddings
            result = get_embeddings()
        assert result is not None

    def test_returns_same_instance_on_second_call(self):
        mock_emb = MagicMock()
        with patch("langchain_huggingface.HuggingFaceEmbeddings", return_value=mock_emb) as MockHF:
            from rag.embeddings import get_embeddings
            r1 = get_embeddings()
            r2 = get_embeddings()
        assert r1 is r2
        assert MockHF.call_count == 1  # constructeur appelé une seule fois

    def test_model_name_passed_to_constructor(self):
        mock_emb = MagicMock()
        with patch("langchain_huggingface.HuggingFaceEmbeddings", return_value=mock_emb) as MockHF:
            from rag.embeddings import get_embeddings
            from rag.config import MODEL_NAME
            get_embeddings()
        call_kwargs = MockHF.call_args[1]
        model_arg = call_kwargs.get("model_name", "")
        assert model_arg == MODEL_NAME or MODEL_NAME.replace("/", "--") in model_arg

    def test_cpu_device_used(self):
        mock_emb = MagicMock()
        with patch("langchain_huggingface.HuggingFaceEmbeddings", return_value=mock_emb) as MockHF:
            from rag.embeddings import get_embeddings
            get_embeddings()
        call_kwargs = MockHF.call_args[1]
        assert call_kwargs.get("model_kwargs", {}).get("device") == "cpu"

    def test_normalize_embeddings_enabled(self):
        mock_emb = MagicMock()
        with patch("langchain_huggingface.HuggingFaceEmbeddings", return_value=mock_emb) as MockHF:
            from rag.embeddings import get_embeddings
            get_embeddings()
        call_kwargs = MockHF.call_args[1]
        assert call_kwargs.get("encode_kwargs", {}).get("normalize_embeddings") is True

    def test_multiple_calls_do_not_reload_model(self):
        mock_emb = MagicMock()
        with patch("langchain_huggingface.HuggingFaceEmbeddings", return_value=mock_emb) as MockHF:
            from rag.embeddings import get_embeddings
            for _ in range(5):
                get_embeddings()
        assert MockHF.call_count == 1
