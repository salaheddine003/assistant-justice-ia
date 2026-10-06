from unittest.mock import MagicMock, patch


FAKE_RESULTS = [
    {
        "pertinence": "82.0%",
        "pertinence_raw": 82.0,
        "l2_distance": 0.4,
        "source_file": "229__Code_civil.pdf",
        "article_num": 229,
        "text": "Le divorce peut etre prononce en cas de consentement mutuel.",
        "rerank_score": 85.0,
    }
]


class TestAsk:
    def _patch_all(self, llm_response="Reponse LLM simulee."):
        import unittest.mock as um

        return [
            um.patch("rag.generator.query", return_value=FAKE_RESULTS),
            um.patch("rag.generator.rerank", return_value=FAKE_RESULTS),
            um.patch("rag.generator._call_gemma", return_value=llm_response),
        ]

    def test_returns_tuple(self):
        from rag.generator import ask

        patches = self._patch_all()
        for p in patches:
            p.start()
        try:
            response, sources = ask("causes du divorce ?")
            assert isinstance(response, str)
            assert isinstance(sources, list)
        finally:
            for p in patches:
                p.stop()

    def test_response_contains_llm_output(self):
        from rag.generator import ask

        patches = self._patch_all("Reponse specifique du LLM.")
        for p in patches:
            p.start()
        try:
            response, _ = ask("causes du divorce ?")
            assert "Reponse specifique du LLM." in response
        finally:
            for p in patches:
                p.stop()

    def test_sources_returned(self):
        from rag.generator import ask

        patches = self._patch_all()
        for p in patches:
            p.start()
        try:
            _, sources = ask("causes du divorce ?")
            assert len(sources) == 1
            assert sources[0]["source_file"] == "229__Code_civil.pdf"
        finally:
            for p in patches:
                p.stop()

    def test_no_results_returns_error_message(self):
        from rag.generator import ask

        with patch("rag.generator.query", return_value=[]), patch("rag.generator.rerank", return_value=[]):
            response, sources = ask("sujet totalement inconnu")
            assert "Aucun article pertinent" in response
            assert sources == []

    def test_gemma_available_false_when_ollama_unavailable(self, monkeypatch):
        from rag.generator import _gemma_available

        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        with patch("rag.generator.ollama_available", return_value=False):
            assert _gemma_available() is False

    def test_gemma_available_true_when_ollama_available(self, monkeypatch):
        from rag.generator import _gemma_available

        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        with patch("rag.generator.ollama_available", return_value=True):
            assert _gemma_available() is True

    def test_context_truncated_if_too_long(self):
        from rag.generator import ask

        huge_result = [{**FAKE_RESULTS[0], "text": "x" * 10_000}]
        with patch("rag.generator.query", return_value=huge_result), \
             patch("rag.generator.rerank", return_value=huge_result), \
             patch("rag.generator._call_gemma", return_value="ok") as mock_llm:
            ask("test")
            prompt_sent = mock_llm.call_args[0][0]
            assert len(prompt_sent) < 50_000


class TestCallGemma:
    def _mock_response(self, response_text="Reponse LLM."):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": response_text}}
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    def test_returns_stripped_string(self, monkeypatch):
        from rag.generator import _call_gemma

        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        mock_client = MagicMock()
        mock_client.post.return_value = self._mock_response("  Reponse  \n")
        with patch("httpx.Client") as Client:
            Client.return_value.__enter__.return_value = mock_client
            result = _call_gemma("ma question")
        assert result == "Reponse"

    def test_returns_llm_text(self, monkeypatch):
        from rag.generator import _call_gemma

        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        mock_client = MagicMock()
        mock_client.post.return_value = self._mock_response("Divorce prononce en cas de consentement.")
        with patch("httpx.Client") as Client:
            Client.return_value.__enter__.return_value = mock_client
            result = _call_gemma("causes du divorce")
        assert "Divorce" in result

    def test_uses_gemma_model_from_config(self, monkeypatch):
        from rag.config import GEMMA_MODEL
        from rag.generator import _call_gemma

        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        mock_client = MagicMock()
        mock_client.post.return_value = self._mock_response("ok")
        with patch("httpx.Client") as Client:
            Client.return_value.__enter__.return_value = mock_client
            _call_gemma("test question")
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["model"] == GEMMA_MODEL

    def test_passes_prompt_to_llm(self, monkeypatch):
        from rag.generator import _call_gemma

        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        mock_client = MagicMock()
        mock_client.post.return_value = self._mock_response("ok")
        with patch("httpx.Client") as Client:
            Client.return_value.__enter__.return_value = mock_client
            _call_gemma("mon prompt special")
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["messages"][-1]["content"] == "mon prompt special"
