"""
Tests unitaires — rag/indexer.py
Teste build_index() : erreurs, chargement PDF, chunks, sauvegarde FAISS.
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call


class _FakePage:
    """Simule un objet Document LangChain minimal."""
    def __init__(self, content="texte test", source="art.pdf"):
        self.page_content = content
        self.metadata = {"source": source}


class TestBuildIndex:
    def test_raises_if_folder_is_empty(self, tmp_path):
        """Dossier vide → FileNotFoundError."""
        from rag.indexer import build_index
        with pytest.raises(FileNotFoundError):
            build_index(pdf_folder=str(tmp_path), index_path=str(tmp_path / "idx"))

    def test_raises_if_folder_does_not_exist(self, tmp_path):
        """Dossier inexistant → glob retourne rien → FileNotFoundError."""
        from rag.indexer import build_index
        missing = str(tmp_path / "does_not_exist")
        with pytest.raises(FileNotFoundError):
            build_index(pdf_folder=missing, index_path=str(tmp_path / "idx"))

    def test_calls_save_local_with_custom_index_path(self, tmp_path):
        """save_local est appelé avec le chemin d'index fourni."""
        fake_pdf = tmp_path / "001__Code_civil.pdf"
        fake_pdf.touch()

        page = _FakePage("Article 1 — texte de test", "001__Code_civil.pdf")
        mock_loader = MagicMock()
        mock_loader.load.return_value = [page]
        mock_vs = MagicMock()
        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = [page]

        idx_path = str(tmp_path / "my_index")
        with patch("langchain_community.document_loaders.PyPDFLoader", return_value=mock_loader), \
             patch("langchain_community.vectorstores.FAISS") as MockFAISS, \
             patch("langchain_text_splitters.RecursiveCharacterTextSplitter", return_value=mock_splitter), \
             patch("rag.indexer.get_embeddings", return_value=MagicMock()):
            MockFAISS.from_documents.return_value = mock_vs
            from rag.indexer import build_index
            build_index(pdf_folder=str(tmp_path), index_path=idx_path)

        mock_vs.save_local.assert_called_once_with(idx_path)

    def test_loads_every_pdf_in_folder(self, tmp_path):
        """PyPDFLoader est instancié une fois par PDF."""
        for i in range(3):
            (tmp_path / f"art_{i}.pdf").touch()

        page = _FakePage()
        mock_loader = MagicMock()
        mock_loader.load.return_value = [page]
        mock_vs = MagicMock()
        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = [page]

        with patch("langchain_community.document_loaders.PyPDFLoader", return_value=mock_loader) as MockLoader, \
             patch("langchain_community.vectorstores.FAISS") as MockFAISS, \
             patch("langchain_text_splitters.RecursiveCharacterTextSplitter", return_value=mock_splitter), \
             patch("rag.indexer.get_embeddings", return_value=MagicMock()):
            MockFAISS.from_documents.return_value = mock_vs
            from rag.indexer import build_index
            build_index(pdf_folder=str(tmp_path), index_path=str(tmp_path / "idx"))

        assert MockLoader.call_count == 3

    def test_source_file_metadata_added_to_pages(self, tmp_path):
        """source_file est injecté dans page.metadata après chargement."""
        pdf_file = tmp_path / "229__Code_civil.pdf"
        pdf_file.touch()

        page = _FakePage("contenu de test")
        mock_loader = MagicMock()
        mock_loader.load.return_value = [page]
        mock_vs = MagicMock()
        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = [page]

        with patch("langchain_community.document_loaders.PyPDFLoader", return_value=mock_loader), \
             patch("langchain_community.vectorstores.FAISS") as MockFAISS, \
             patch("langchain_text_splitters.RecursiveCharacterTextSplitter", return_value=mock_splitter), \
             patch("rag.indexer.get_embeddings", return_value=MagicMock()):
            MockFAISS.from_documents.return_value = mock_vs
            from rag.indexer import build_index
            build_index(pdf_folder=str(tmp_path), index_path=str(tmp_path / "idx"))

        assert page.metadata.get("source_file") == "229__Code_civil.pdf"

    def test_uses_default_index_path_when_none(self, tmp_path):
        """Avec index_path=None, utilise INDEX_PATH de la config."""
        (tmp_path / "art_1.pdf").touch()

        page = _FakePage()
        mock_loader = MagicMock()
        mock_loader.load.return_value = [page]
        mock_vs = MagicMock()
        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = [page]

        with patch("langchain_community.document_loaders.PyPDFLoader", return_value=mock_loader), \
             patch("langchain_community.vectorstores.FAISS") as MockFAISS, \
             patch("langchain_text_splitters.RecursiveCharacterTextSplitter", return_value=mock_splitter), \
             patch("rag.indexer.get_embeddings", return_value=MagicMock()):
            MockFAISS.from_documents.return_value = mock_vs
            from rag.indexer import build_index
            from rag.config import INDEX_PATH
            build_index(pdf_folder=str(tmp_path))  # index_path implicite

        mock_vs.save_local.assert_called_once_with(INDEX_PATH)

    def test_pdf_load_error_is_caught_and_skipped(self, tmp_path):
        """Une erreur de chargement d'un PDF n'arrête pas les autres."""
        for name in ["ok.pdf", "bad.pdf"]:
            (tmp_path / name).touch()

        ok_page = _FakePage("texte ok")
        mock_ok_loader = MagicMock()
        mock_ok_loader.load.return_value = [ok_page]
        mock_bad_loader = MagicMock()
        mock_bad_loader.load.side_effect = Exception("PDF corrompu")
        mock_vs = MagicMock()
        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = [ok_page]

        # Return different loaders based on which PDF is being loaded
        call_count = [0]
        loaders = [mock_ok_loader, mock_bad_loader]
        def loader_factory(path):
            idx = call_count[0] % 2
            call_count[0] += 1
            return loaders[idx]

        with patch("langchain_community.document_loaders.PyPDFLoader", side_effect=loader_factory), \
             patch("langchain_community.vectorstores.FAISS") as MockFAISS, \
             patch("langchain_text_splitters.RecursiveCharacterTextSplitter", return_value=mock_splitter), \
             patch("rag.indexer.get_embeddings", return_value=MagicMock()):
            MockFAISS.from_documents.return_value = mock_vs
            from rag.indexer import build_index
            # Should not raise even though one PDF fails
            build_index(pdf_folder=str(tmp_path), index_path=str(tmp_path / "idx"))

        mock_vs.save_local.assert_called_once()
