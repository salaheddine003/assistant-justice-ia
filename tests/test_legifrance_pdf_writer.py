"""
Tests unitaires — legifrance/pdf_writer.py
Teste les utilitaires texte, le nommage des fichiers et la génération PDF.
"""
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from legifrance.pdf_writer import clean, safe, nom_fichier, generer_pdf


class TestClean:
    def test_strips_html(self):
        assert clean("<b>Bonjour</b>") == "Bonjour"

    def test_replaces_ellipsis(self):
        assert "[...]" not in clean("texte [...] suite")
        assert "..." in clean("texte [...] suite")

    def test_collapses_whitespace(self):
        result = clean("a   b\n\nc")
        assert "  " not in result
        assert result == "a b c"

    def test_empty_input(self):
        assert clean("") == ""
        assert clean(None) == ""

    def test_none_input(self):
        assert clean(None) == ""

    def test_nested_html(self):
        assert clean("<p><span>texte</span></p>") == "texte"


class TestSafe:
    def test_returns_latin1_safe_string(self):
        result = safe("café résumé")
        assert isinstance(result, str)

    def test_empty(self):
        assert safe("") == ""
        assert safe(None) == ""

    def test_strips_html_too(self):
        assert safe("<b>texte</b>") == "texte"


class TestNomFichier:
    def test_ends_with_pdf(self):
        assert nom_fichier("229", "Code civil").endswith(".pdf")

    def test_contains_num_and_code(self):
        name = nom_fichier("229", "Code civil")
        assert "229" in name
        assert "Code_civil" in name or "civil" in name.lower()

    def test_separator_double_underscore(self):
        name = nom_fichier("1", "Code penal")
        assert "__" in name

    def test_max_length(self):
        long_num  = "A" * 200
        long_code = "B" * 200
        assert len(nom_fichier(long_num, long_code)) <= 180

    def test_special_chars_replaced(self):
        name = nom_fichier("1-bis", "Code de l'environnement")
        # L'apostrophe doit être remplacée
        assert "'" not in name

    def test_none_num(self):
        name = nom_fichier(None, "Code civil")
        assert "article" in name

    def test_none_code(self):
        name = nom_fichier("1", None)
        assert "code" in name


class TestGenererPdf:
    def test_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            chemin = os.path.join(tmpdir, "test_article.pdf")
            generer_pdf(
                chemin=chemin,
                num="229",
                code_name="Code civil",
                section="Titre VI — Du divorce",
                texte="Le divorce peut être prononcé en cas de consentement mutuel.",
                etat="VIGUEUR",
                date_debut="1975-07-11",
                date_fin="",
                url="https://www.legifrance.gouv.fr/codes/article_lc/ART001",
            )
            assert os.path.exists(chemin)
            assert os.path.getsize(chemin) > 0

    def test_pdf_magic_bytes(self):
        """Vérifie que le fichier créé est bien un PDF (commence par %PDF)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            chemin = os.path.join(tmpdir, "magic.pdf")
            generer_pdf(chemin, "1", "Code civil", "", "Texte.", "VIGUEUR", "", "", "")
            with open(chemin, "rb") as f:
                assert f.read(4) == b"%PDF"

    def test_empty_texte(self):
        """Ne doit pas lever d'exception si texte est vide."""
        with tempfile.TemporaryDirectory() as tmpdir:
            chemin = os.path.join(tmpdir, "empty.pdf")
            generer_pdf(chemin, "1", "Code civil", "", "", "VIGUEUR", "", "", "")
            assert os.path.exists(chemin)


# ── refresh_token_if_needed() ─────────────────────────────────────────────────

class TestRefreshTokenIfNeeded:
    def test_returns_new_token(self):
        from legifrance.pdf_writer import refresh_token_if_needed
        with patch("legifrance.pdf_writer.get_token", return_value="new_tok"):
            result = refresh_token_if_needed()
        assert result == "new_tok"

    def test_updates_global_current_token(self):
        from legifrance.pdf_writer import refresh_token_if_needed, _current_token
        with patch("legifrance.pdf_writer.get_token", return_value="tok_xyz"):
            refresh_token_if_needed()
        assert _current_token["value"] == "tok_xyz"

    def test_returns_string(self):
        from legifrance.pdf_writer import refresh_token_if_needed
        with patch("legifrance.pdf_writer.get_token", return_value="abc"):
            result = refresh_token_if_needed()
        assert isinstance(result, str)


# ── traiter_article() ─────────────────────────────────────────────────────────

class TestTraiterArticle:
    def test_returns_skip_if_file_exists(self, tmp_path):
        """Si le PDF existe déjà, retourne 'skip' sans appel réseau."""
        from legifrance.pdf_writer import traiter_article, nom_fichier
        fname = nom_fichier("229", "Code civil")
        (tmp_path / fname).touch()
        result = traiter_article("token", "ART001", "229", "Section I", "Code civil", str(tmp_path))
        assert result == "skip"

    def test_returns_ok_on_success(self, tmp_path):
        """Retourne 'ok' quand le contenu est obtenu et le PDF généré."""
        from legifrance.pdf_writer import traiter_article
        fake_art = {
            "texte":      "Contenu de l'article.",
            "etat":       "VIGUEUR",
            "dateDebut":  "2024-01-01",
            "dateFin":    "",
        }
        with patch("legifrance.pdf_writer.get_article_content", return_value=fake_art), \
             patch("legifrance.pdf_writer.generer_pdf"):
            result = traiter_article("token", "ART001", "1", "Section I", "Code test", str(tmp_path))
        assert result == "ok"

    def test_returns_err_after_two_none_responses(self, tmp_path):
        """Si get_article_content retourne None deux fois → 'err'."""
        from legifrance.pdf_writer import traiter_article
        with patch("legifrance.pdf_writer.get_article_content", return_value=None), \
             patch("legifrance.pdf_writer.refresh_token_if_needed", return_value="new_tok"):
            result = traiter_article("token", "ART001", "229", "Section I", "Code civil", str(tmp_path))
        assert result == "err"

    def test_returns_err_on_exception(self, tmp_path):
        """Une exception réseau → 'err'."""
        from legifrance.pdf_writer import traiter_article
        with patch("legifrance.pdf_writer.get_article_content", side_effect=Exception("réseau coupé")):
            result = traiter_article("token", "ART001", "229", "Section I", "Code civil", str(tmp_path))
        assert result == "err"

    def test_parses_int_timestamp_to_iso_date(self, tmp_path):
        """Un timestamp int (millisecondes) doit être converti en date ISO."""
        from legifrance.pdf_writer import traiter_article
        ts_ms = 1136073600000  # 2006-01-01 00:00:00 UTC
        fake_art = {
            "texte":      "texte",
            "etat":       "VIGUEUR",
            "dateDebut":  ts_ms,
            "dateFin":    "",
        }
        captured = {}
        def mock_generer(chemin, num, code_name, section, texte, etat, date_debut, date_fin, url):
            captured["date_debut"] = date_debut

        with patch("legifrance.pdf_writer.get_article_content", return_value=fake_art), \
             patch("legifrance.pdf_writer.generer_pdf", side_effect=mock_generer):
            traiter_article("token", "ART_DATE", "1", "Section", "Code test", str(tmp_path))
        assert "-" in captured.get("date_debut", ""), "La date doit être au format ISO YYYY-MM-DD"

    def test_retries_with_refreshed_token(self, tmp_path):
        """Si le premier appel retourne None, tente avec un token rafraîchi."""
        from legifrance.pdf_writer import traiter_article
        fake_art = {"texte": "contenu", "etat": "VIGUEUR", "dateDebut": "", "dateFin": ""}
        call_count = [0]
        def get_art(token, art_id):
            call_count[0] += 1
            if call_count[0] == 1:
                return None  # premier appel échoue
            return fake_art

        with patch("legifrance.pdf_writer.get_article_content", side_effect=get_art), \
             patch("legifrance.pdf_writer.refresh_token_if_needed", return_value="new_tok"), \
             patch("legifrance.pdf_writer.generer_pdf"):
            result = traiter_article("old_tok", "ART001", "1", "Section", "Code test", str(tmp_path))
        assert result == "ok"
        assert call_count[0] == 2
