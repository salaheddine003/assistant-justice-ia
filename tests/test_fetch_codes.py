"""
Tests unitaires — fetch_codes_complets.py
Teste fetch_codes() : comptage, erreurs réseau, gestion des cas limites.
"""
import os
import pytest
from unittest.mock import patch, MagicMock


# ── Helpers ───────────────────────────────────────────────────────────────────

ARTS_1 = [("ART001", "1", "Section I"), ("ART002", "2", "Section I")]
ARTS_2 = [("ART003", "3", "Section II")]


class TestFetchCodes:
    def test_returns_zero_for_empty_codes_dict(self, tmp_path):
        from fetch_codes_complets import fetch_codes
        assert fetch_codes({}, str(tmp_path)) == 0

    def test_returns_zero_when_no_articles(self, tmp_path):
        """collect_article_ids retourne [] → aucun PDF généré."""
        from fetch_codes_complets import fetch_codes
        with patch("fetch_codes_complets.get_token", return_value="tok"), \
             patch("fetch_codes_complets.get_table_matieres", return_value={}), \
             patch("fetch_codes_complets.collect_article_ids", return_value=[]):
            result = fetch_codes({"Code test": "LEGITEXT001"}, str(tmp_path))
        assert result == 0

    def test_counts_ok_results(self, tmp_path):
        """Chaque résultat 'ok' de traiter_article est compté."""
        from fetch_codes_complets import fetch_codes
        with patch("fetch_codes_complets.get_token", return_value="tok"), \
             patch("fetch_codes_complets.get_table_matieres", return_value={}), \
             patch("fetch_codes_complets.collect_article_ids", return_value=ARTS_1), \
             patch("fetch_codes_complets.traiter_article", return_value="ok"):
            result = fetch_codes({"Code test": "LEGITEXT001"}, str(tmp_path))
        assert result == 2

    def test_skip_results_not_counted(self, tmp_path):
        """Les résultats 'skip' (fichier existant) ne s'ajoutent pas au total."""
        from fetch_codes_complets import fetch_codes
        with patch("fetch_codes_complets.get_token", return_value="tok"), \
             patch("fetch_codes_complets.get_table_matieres", return_value={}), \
             patch("fetch_codes_complets.collect_article_ids", return_value=ARTS_1), \
             patch("fetch_codes_complets.traiter_article", return_value="skip"):
            result = fetch_codes({"Code test": "LEGITEXT001"}, str(tmp_path))
        assert result == 0

    def test_err_results_not_counted(self, tmp_path):
        """Les résultats 'err' ne s'ajoutent pas au total."""
        from fetch_codes_complets import fetch_codes
        with patch("fetch_codes_complets.get_token", return_value="tok"), \
             patch("fetch_codes_complets.get_table_matieres", return_value={}), \
             patch("fetch_codes_complets.collect_article_ids", return_value=ARTS_2), \
             patch("fetch_codes_complets.traiter_article", return_value="err"):
            result = fetch_codes({"Code test": "LEGITEXT001"}, str(tmp_path))
        assert result == 0

    def test_mixed_results_counted_correctly(self, tmp_path):
        """ok=2, skip=1, err=1 → total = 2."""
        from fetch_codes_complets import fetch_codes
        arts = [("A1", "1", "S"), ("A2", "2", "S"), ("A3", "3", "S"), ("A4", "4", "S")]
        responses = iter(["ok", "ok", "skip", "err"])
        with patch("fetch_codes_complets.get_token", return_value="tok"), \
             patch("fetch_codes_complets.get_table_matieres", return_value={}), \
             patch("fetch_codes_complets.collect_article_ids", return_value=arts), \
             patch("fetch_codes_complets.traiter_article", side_effect=responses):
            result = fetch_codes({"Code test": "LEGITEXT001"}, str(tmp_path))
        assert result == 2

    def test_continues_after_tdm_exception(self, tmp_path):
        """Une exception sur get_table_matieres n'interrompt pas les autres codes."""
        from fetch_codes_complets import fetch_codes
        with patch("fetch_codes_complets.get_token", return_value="tok"), \
             patch("fetch_codes_complets.get_table_matieres", side_effect=Exception("API down")), \
             patch("fetch_codes_complets.collect_article_ids") as mock_collect:
            result = fetch_codes(
                {"Code A": "LEGITEXT001", "Code B": "LEGITEXT002"}, str(tmp_path)
            )
        mock_collect.assert_not_called()
        assert result == 0

    def test_accumulates_across_multiple_codes(self, tmp_path):
        """Totalise les PDFs sur tous les codes du dictionnaire."""
        from fetch_codes_complets import fetch_codes
        with patch("fetch_codes_complets.get_token", return_value="tok"), \
             patch("fetch_codes_complets.get_table_matieres", return_value={}), \
             patch("fetch_codes_complets.collect_article_ids", return_value=ARTS_2), \
             patch("fetch_codes_complets.traiter_article", return_value="ok"):
            result = fetch_codes(
                {"Code A": "LEGITEXT001", "Code B": "LEGITEXT002"}, str(tmp_path)
            )
        assert result == 2  # 1 article × 2 codes

    def test_creates_output_directory(self, tmp_path):
        """os.makedirs est appelé pour créer le dossier du code."""
        from fetch_codes_complets import fetch_codes
        with patch("fetch_codes_complets.get_token", return_value="tok"), \
             patch("fetch_codes_complets.get_table_matieres", return_value={}), \
             patch("fetch_codes_complets.collect_article_ids", return_value=ARTS_1), \
             patch("fetch_codes_complets.traiter_article", return_value="ok"):
            fetch_codes({"Code civil": "LEGITEXT001"}, str(tmp_path))
        # The directory should have been created
        expected = os.path.join(str(tmp_path), "Code civil")
        assert os.path.isdir(expected)
