"""
Tests unitaires — api.py
Teste les endpoints FastAPI via TestClient (sans appel réseau réel).
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ── Helpers de mock ───────────────────────────────────────────────────────────

FAKE_RESULTS = [
    {
        "pertinence":     "82.0%",
        "pertinence_raw": 82.0,
        "l2_distance":    0.4,
        "source_file":    "229__Code_civil.pdf",
        "article_num":    229,
        "text":           "Le divorce peut être prononcé en cas de consentement mutuel.",
        "rerank_score":   85.0,
    }
]


@pytest.fixture
def client():
    """TestClient avec index Code civil simulé comme existant."""
    with patch.object(Path, "exists", return_value=True), \
         patch.object(Path, "glob",   return_value=iter([])):
        from api import app
        return TestClient(app, raise_server_exceptions=True)


# ── GET / ─────────────────────────────────────────────────────────────────────

class TestIndex:
    def test_returns_html(self, tmp_path, monkeypatch):
        html = "<html><body>Assistant Juridique</body></html>"
        html_file = tmp_path / "index.html"
        html_file.write_text(html, encoding="utf-8")

        with patch("api.Path") as MockPath:
            mock_inst = MagicMock()
            mock_inst.exists.return_value = True
            mock_inst.read_text.return_value = html
            MockPath.return_value = mock_inst

            from api import app
            c = TestClient(app)
            resp = c.get("/")
            assert resp.status_code == 200
            assert "Assistant Juridique" in resp.text


# ── GET /api/status ───────────────────────────────────────────────────────────

class TestStatus:
    def test_status_ok(self, client, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        with patch("api.ollama_available", return_value=True):
            resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["api"] == "ok"
        assert data["llm"] == "ollama_ok"
        assert data["provider"] == "ollama"
        assert "model" in data

    def test_status_ollama_unavailable(self, client, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        with patch("api.ollama_available", return_value=False):
            resp = client.get("/api/status")
        assert resp.status_code == 200
        assert resp.json()["llm"] == "ollama_unavailable"


# ── GET /api/codes ────────────────────────────────────────────────────────────

class TestListCodes:
    def test_returns_list(self, client):
        resp = client.get("/api/codes")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_code_civil_in_list(self, client):
        resp = client.get("/api/codes")
        names = [c["name"] for c in resp.json()]
        assert "Code civil" in names

    def test_each_item_has_required_fields(self, client):
        resp = client.get("/api/codes")
        for item in resp.json():
            assert "name"      in item
            assert "indexed"   in item
            assert "pdf_count" in item


# ── POST /api/ask ─────────────────────────────────────────────────────────────

class TestAskEndpoint:
    def _sse_events(self, response) -> list[dict]:
        """Parse les données SSE en liste de dicts JSON."""
        events = []
        for line in response.text.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        return events

    def test_unknown_code_returns_400(self, client):
        resp = client.post("/api/ask", json={
            "question": "test", "code": "Code inexistant"
        })
        assert resp.status_code == 400

    def test_vague_question_returns_clarification(self, client):
        resp = client.post("/api/ask", json={
            "question": "oui", "code": "Code civil"
        })
        assert resp.status_code == 200
        events = self._sse_events(resp)
        types = [e.get("type") for e in events]
        assert "sources" in types
        assert "done"    in types

    def test_valid_question_streams_sources_then_tokens(self, client):
        with patch("rag.query",  return_value=FAKE_RESULTS), \
             patch("rag.rerank", return_value=FAKE_RESULTS), \
             patch("api._gemma_stream", return_value=iter(["Réponse", " LLM"])):
            resp = client.post("/api/ask", json={
                "question": "quelles sont les causes du divorce ?",
                "code":     "Code civil",
                "top_k":    5,
            })
        assert resp.status_code == 200
        events = self._sse_events(resp)
        types = [e.get("type") for e in events]
        assert "sources" in types
        assert "token"   in types
        assert "done"    in types

    def test_sources_event_first(self, client):
        with patch("rag.query",  return_value=FAKE_RESULTS), \
             patch("rag.rerank", return_value=FAKE_RESULTS), \
             patch("api._gemma_stream", return_value=iter(["ok"])):
            resp = client.post("/api/ask", json={
                "question": "droits du locataire en cas de loyer impayé",
                "code":     "Code civil",
            })
        events = self._sse_events(resp)
        assert events[0]["type"] == "sources"

    def test_no_results_returns_token_with_message(self, client):
        with patch("rag.query",  return_value=[]), \
             patch("rag.rerank", return_value=[]), \
             patch("api._gemma_stream", return_value=iter(["reponse generale"])):
            resp = client.post("/api/ask", json={
                "question": "question sur sujet inconnu du tout",
                "code":     "Code civil",
            })
        events = self._sse_events(resp)
        token_events = [e for e in events if e.get("type") == "token"]
        assert any("reponse generale" in e.get("text", "").lower() for e in token_events)


# ── POST /api/build ───────────────────────────────────────────────────────────

class TestBuildEndpoint:
    def test_unknown_code_returns_400(self, client):
        resp = client.post("/api/build", json={"code": "Code inexistant"})
        assert resp.status_code == 400

    def test_missing_pdf_folder_returns_400(self, client):
        with patch.object(Path, "exists", return_value=False):
            resp = client.post("/api/build", json={"code": "Code civil"})
            assert resp.status_code == 400

    def test_build_success(self, client):
        with patch("rag.build_index", return_value=None), \
             patch.object(Path, "exists", return_value=True):
            resp = client.post("/api/build", json={"code": "Code civil"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_build_exception_returns_500(self, client):
        with patch("rag.build_index", side_effect=RuntimeError("erreur test")), \
             patch.object(Path, "exists", return_value=True):
            resp = client.post("/api/build", json={"code": "Code civil"})
        assert resp.status_code == 500


# ── Fonctions internes ────────────────────────────────────────────────────────

class TestIsVague:
    def test_short_question_is_vague(self):
        from api import _is_vague
        assert _is_vague("oui", has_history=False) is True

    def test_two_words_is_vague(self):
        from api import _is_vague
        assert _is_vague("le divorce", has_history=False) is True

    def test_three_words_not_vague(self):
        from api import _is_vague
        assert _is_vague("causes du divorce", has_history=False) is False

    def test_long_question_not_vague(self):
        from api import _is_vague
        assert _is_vague("quelles sont les causes du divorce par consentement mutuel ?", has_history=False) is False

    def test_short_question_not_vague_with_history(self):
        from api import _is_vague
        # Avec historique, même une question courte est acceptée
        assert _is_vague("développe", has_history=True) is False

    def test_empty_question_is_vague(self):
        from api import _is_vague
        assert _is_vague("", has_history=False) is True


class TestBuildSearchQuery:
    def test_returns_string(self):
        from api import _build_search_query
        result = _build_search_query("quelles sont les causes du divorce ?", [])
        assert isinstance(result, str)

    def test_reformulates_interrogative(self):
        from api import _build_search_query
        result = _build_search_query("quelles sont les causes du divorce ?", [])
        assert "quelles" not in result.lower()

    def test_standalone_query_keeps_keywords(self):
        from api import _build_search_query
        result = _build_search_query("droit du travail licenciement procédure", [])
        assert "licenciement" in result.lower() or "travail" in result.lower()

    def test_followup_uses_last_user_question(self):
        from api import _build_search_query
        history = [
            {"role": "user", "content": "quelles sont les causes du divorce ?"},
            {"role": "assistant", "content": "Il y a 4 causes de divorce…"},
        ]
        # "développe" seul = question de suivi → doit réutiliser la question précédente
        result = _build_search_query("développe", history)
        assert "divorce" in result.lower()

    def test_empty_history_uses_question_directly(self):
        from api import _build_search_query
        result = _build_search_query("licenciement préavis délai", [])
        assert "licenciement" in result.lower() or len(result) > 3
