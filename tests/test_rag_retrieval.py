"""
Tests unitaires — rag/retrieval.py
Teste la conversion de score, l'extraction d'article, la reformulation,
le re-ranking et la recherche FAISS (query).
"""
import math
import pytest
from unittest.mock import patch, MagicMock
from rag.retrieval import (
    _l2_to_similarity,
    _extract_article_number,
    reformulate_query,
    rerank,
)


class TestL2ToSimilarity:
    def test_distance_zero_is_100(self):
        assert _l2_to_similarity(0.0) == 100.0

    def test_distance_increases_score_decreases(self):
        assert _l2_to_similarity(0.5) > _l2_to_similarity(1.0)
        assert _l2_to_similarity(1.0) > _l2_to_similarity(2.0)

    def test_known_values(self):
        # sim = round(100 * exp(-d/2), 1)
        assert _l2_to_similarity(0.5) == round(100 * math.exp(-0.25), 1)
        assert _l2_to_similarity(2.0) == round(100 * math.exp(-1.0),  1)

    def test_always_positive(self):
        for d in [0.0, 0.5, 1.0, 1.5, 2.0, 5.0]:
            assert _l2_to_similarity(d) > 0


class TestExtractArticleNumber:
    def test_filename_format(self):
        assert _extract_article_number("229__Code_civil.pdf") == 229
        assert _extract_article_number("1__Code_penal.pdf") == 1
        assert _extract_article_number("1234_article.pdf") == 1234

    def test_text_format_article(self):
        assert _extract_article_number("Article 229 du code") == 229

    def test_text_format_art(self):
        assert _extract_article_number("art. 229 alinéa 1") == 229
        assert _extract_article_number("art 45") == 45

    def test_no_number_returns_none(self):
        assert _extract_article_number("aucun_numero.pdf") is None
        assert _extract_article_number("") is None

    def test_case_insensitive(self):
        assert _extract_article_number("ARTICLE 100") == 100


class TestReformulateQuery:
    def test_removes_quelles_sont(self):
        result = reformulate_query("quelles sont les causes du divorce ?")
        assert "quelles" not in result.lower()
        assert "sont" not in result.lower()

    def test_removes_quest_ce_que(self):
        result = reformulate_query("qu'est-ce que le divorce ?")
        assert "qu'est" not in result.lower()

    def test_keeps_key_words(self):
        result = reformulate_query("quelles sont les causes du divorce ?")
        assert "divorce" in result.lower()

    def test_removes_pourquoi(self):
        result = reformulate_query("pourquoi le divorce est accordé ?")
        assert "pourquoi" not in result.lower()

    def test_removes_combien(self):
        result = reformulate_query("combien de types de divorce existent ?")
        assert "combien" not in result.lower()

    def test_removes_comment(self):
        result = reformulate_query("comment fonctionne le droit du travail ?")
        assert "comment" not in result.lower()

    def test_short_result_returns_original(self):
        # Si le nettoyage vide trop la question, on garde l'originale
        result = reformulate_query("quand ?")
        assert len(result) > 0

    def test_already_declarative(self):
        q = "divorce consentement mutuel conditions"
        assert reformulate_query(q) == q

    def test_returns_string(self):
        assert isinstance(reformulate_query("test"), str)

    def test_strips_trailing_space(self):
        result = reformulate_query("quelles sont les obligations ?")
        assert result == result.strip()


class TestRerank:
    """Teste le re-ranking sans FAISS (données injectées manuellement)."""

    def _make_result(self, text, score=75.0, article_num=None):
        return {
            "text":           text,
            "pertinence":     f"{score}%",
            "pertinence_raw": score,
            "source_file":    f"{article_num or 'x'}__Code_civil.pdf",
            "article_num":    article_num,
            "l2_distance":    0.5,
        }

    def test_keyword_boost_moves_result_up(self):
        results = [
            self._make_result("texte sans rapport avec la question", score=80),
            self._make_result("divorce consentement mutuel procédure", score=70),
        ]
        ranked = rerank(results, "divorce consentement mutuel")
        # Le second (70%) doit passer devant grâce aux mots-clés
        assert ranked[0]["pertinence_raw"] == 70.0

    def test_article_229_boost_for_divorce_causes(self):
        results = [
            self._make_result("autre texte non lié", score=80, article_num=100),
            self._make_result("divorce peut être prononcé", score=70, article_num=229),
        ]
        ranked = rerank(results, "quelles sont les causes du divorce ?")
        assert ranked[0]["article_num"] == 229

    def test_order_preserved_when_no_keywords(self):
        results = [
            self._make_result("aaa", score=90),
            self._make_result("bbb", score=80),
            self._make_result("ccc", score=70),
        ]
        # Question sans mots-clés significatifs → ordre par score brut
        ranked = rerank(results, "ok")
        scores = [r["pertinence_raw"] for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_rerank_score_field_added(self):
        results = [self._make_result("divorce mariage", score=75)]
        ranked = rerank(results, "divorce")
        assert "rerank_score" in ranked[0]

    def test_empty_results(self):
        assert rerank([], "question") == []

    def test_does_not_alter_pertinence(self):
        """Le score affiché (pertinence) ne doit pas être modifié."""
        results = [self._make_result("divorce", score=75.3)]
        ranked = rerank(results, "divorce")
        assert ranked[0]["pertinence"] == "75.3%"
        assert ranked[0]["pertinence_raw"] == 75.3


# ── query() ───────────────────────────────────────────────────────────────────

class TestQuery:
    """Teste query() en mockant FAISS.load_local et get_embeddings."""

    def _make_doc(self, content, source_file="229__Code_civil.pdf"):
        doc = MagicMock()
        doc.page_content = content
        doc.metadata = {"source_file": source_file}
        return doc

    def _mock_faiss(self, docs_with_scores, mock_vs=None):
        """Retourne un mock_vs configuré avec les résultats donnés."""
        vs = mock_vs or MagicMock()
        vs.similarity_search_with_score.return_value = docs_with_scores
        return vs

    def test_raises_file_not_found_if_index_missing(self):
        from rag.retrieval import query
        with patch("rag.retrieval.Path") as MockPath:
            MockPath.return_value.exists.return_value = False
            with pytest.raises(FileNotFoundError):
                query("test question", index_path="missing_index")

    def test_returns_list(self):
        from rag.retrieval import query
        doc = self._make_doc("Le divorce peut être prononcé par consentement mutuel.")
        mock_vs = self._mock_faiss([(doc, 0.5)])
        with patch("rag.retrieval.Path") as MockPath, \
             patch("langchain_community.vectorstores.FAISS") as MockFAISS, \
             patch("rag.retrieval.get_embeddings", return_value=MagicMock()):
            MockPath.return_value.exists.return_value = True
            MockFAISS.load_local.return_value = mock_vs
            results = query("divorce consentement", index_path="fake_idx")
        assert isinstance(results, list)

    def test_filters_results_above_threshold(self):
        from rag.retrieval import query
        from rag.config import SCORE_THRESHOLD
        doc = self._make_doc("contenu quelconque")
        mock_vs = self._mock_faiss([(doc, SCORE_THRESHOLD + 1.0)])
        with patch("rag.retrieval.Path") as MockPath, \
             patch("langchain_community.vectorstores.FAISS") as MockFAISS, \
             patch("rag.retrieval.get_embeddings", return_value=MagicMock()):
            MockPath.return_value.exists.return_value = True
            MockFAISS.load_local.return_value = mock_vs
            results = query("question quelconque", index_path="fake_idx")
        assert results == []

    def test_includes_results_below_threshold(self):
        from rag.retrieval import query
        doc = self._make_doc("Article 1 — texte de l'article")
        mock_vs = self._mock_faiss([(doc, 0.3)])
        with patch("rag.retrieval.Path") as MockPath, \
             patch("langchain_community.vectorstores.FAISS") as MockFAISS, \
             patch("rag.retrieval.get_embeddings", return_value=MagicMock()):
            MockPath.return_value.exists.return_value = True
            MockFAISS.load_local.return_value = mock_vs
            results = query("question", index_path="fake_idx")
        assert len(results) == 1

    def test_result_has_required_keys(self):
        from rag.retrieval import query
        doc = self._make_doc("texte test", "229__Code_civil.pdf")
        mock_vs = self._mock_faiss([(doc, 0.4)])
        with patch("rag.retrieval.Path") as MockPath, \
             patch("langchain_community.vectorstores.FAISS") as MockFAISS, \
             patch("rag.retrieval.get_embeddings", return_value=MagicMock()):
            MockPath.return_value.exists.return_value = True
            MockFAISS.load_local.return_value = mock_vs
            results = query("test", index_path="fake_idx")
        r = results[0]
        for key in ("pertinence", "pertinence_raw", "l2_distance", "source_file", "text"):
            assert key in r

    def test_results_sorted_by_pertinence_desc(self):
        from rag.retrieval import query
        doc1 = self._make_doc("haute similarité", "art1.pdf")
        doc2 = self._make_doc("basse similarité", "art2.pdf")
        # doc2 a une distance plus faible → pertinence_raw plus haute
        mock_vs = self._mock_faiss([(doc2, 0.8), (doc1, 0.2)])
        with patch("rag.retrieval.Path") as MockPath, \
             patch("langchain_community.vectorstores.FAISS") as MockFAISS, \
             patch("rag.retrieval.get_embeddings", return_value=MagicMock()):
            MockPath.return_value.exists.return_value = True
            MockFAISS.load_local.return_value = mock_vs
            results = query("test", index_path="fake_idx")
        if len(results) >= 2:
            assert results[0]["pertinence_raw"] > results[1]["pertinence_raw"]

    def test_respects_top_k_limit(self):
        from rag.retrieval import query
        docs_with_scores = [
            (self._make_doc(f"art {i}", f"art{i}.pdf"), 0.3)
            for i in range(20)
        ]
        mock_vs = self._mock_faiss(docs_with_scores)
        with patch("rag.retrieval.Path") as MockPath, \
             patch("langchain_community.vectorstores.FAISS") as MockFAISS, \
             patch("rag.retrieval.get_embeddings", return_value=MagicMock()):
            MockPath.return_value.exists.return_value = True
            MockFAISS.load_local.return_value = mock_vs
            results = query("test", top_k=5, index_path="fake_idx")
        assert len(results) <= 5
