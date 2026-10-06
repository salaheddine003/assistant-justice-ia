"""
Tests unitaires — legifrance/client.py
Teste la traversée récursive de la table des matières et les appels HTTP (mockés).
"""
import pytest
from unittest.mock import MagicMock, patch
from legifrance.client import collect_article_ids, get_table_matieres, get_article_content


# ── Fixtures JSON réalistes ───────────────────────────────────────────────────

SIMPLE_NODE = {
    "title": "Titre I",
    "articles": [
        {"id": "ART001", "num": "1", "etat": "VIGUEUR"},
        {"id": "ART002", "num": "2", "etat": "ABROGE"},   # doit être ignoré
        {"id": "",       "num": "3", "etat": "VIGUEUR"},   # id vide → ignoré
    ],
    "sections": [],
}

NESTED_NODE = {
    "title": "Livre I",
    "articles": [],
    "sections": [
        {
            "title": "Titre I",
            "articles": [
                {"id": "ART010", "num": "10", "etat": "VIGUEUR"},
            ],
            "sections": [
                {
                    "title": "Chapitre I",
                    "articles": [
                        {"id": "ART011", "num": "11", "etat": "VIGUEUR"},
                    ],
                    "sections": [],
                }
            ],
        }
    ],
}

EMPTY_NODE = {"title": "", "articles": [], "sections": []}


class TestCollectArticleIds:
    def test_simple_vigueur_only(self):
        result = collect_article_ids(SIMPLE_NODE)
        ids = [r[0] for r in result]
        assert "ART001" in ids
        assert "ART002" not in ids   # ABROGE
        assert "" not in ids          # id vide

    def test_returns_tuple3(self):
        result = collect_article_ids(SIMPLE_NODE)
        assert len(result) == 1
        art_id, num, path = result[0]
        assert art_id == "ART001"
        assert num == "1"
        assert "Titre I" in path

    def test_nested_recursion(self):
        result = collect_article_ids(NESTED_NODE)
        ids = [r[0] for r in result]
        assert "ART010" in ids
        assert "ART011" in ids
        assert len(result) == 2

    def test_section_path_propagates(self):
        result = collect_article_ids(NESTED_NODE)
        # ART011 est dans Livre I > Titre I > Chapitre I
        art11 = next(r for r in result if r[0] == "ART011")
        assert "Livre I" in art11[2]
        assert "Titre I" in art11[2]
        assert "Chapitre I" in art11[2]

    def test_empty_node(self):
        assert collect_article_ids(EMPTY_NODE) == []

    def test_no_title_section(self):
        node = {
            "title": "",
            "articles": [{"id": "ART999", "num": "999", "etat": "VIGUEUR"}],
            "sections": [],
        }
        result = collect_article_ids(node)
        assert len(result) == 1
        assert result[0][2] == ""   # chemin vide si pas de titre


class TestGetTableMatieres:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"title": "Code civil", "sections": []}
        mock_resp.raise_for_status = MagicMock()

        with patch("legifrance.client.requests.post", return_value=mock_resp):
            result = get_table_matieres("fake_token", "LEGITEXT000006070721")

        assert result["title"] == "Code civil"

    def test_http_error_raises(self):
        from requests.exceptions import HTTPError
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = HTTPError("404")

        with patch("legifrance.client.requests.post", return_value=mock_resp):
            with pytest.raises(HTTPError):
                get_table_matieres("fake_token", "INVALIDE")


class TestGetArticleContent:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "article": {"id": "ART001", "texte": "Le mariage est...", "etat": "VIGUEUR"}
        }

        with patch("legifrance.client.requests.post", return_value=mock_resp):
            result = get_article_content("fake_token", "ART001")

        assert result["texte"] == "Le mariage est..."

    def test_http_failure_returns_none(self):
        mock_resp = MagicMock()
        mock_resp.ok = False

        with patch("legifrance.client.requests.post", return_value=mock_resp):
            result = get_article_content("fake_token", "ART_INVALIDE")

        assert result is None
