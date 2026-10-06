"""
Tests unitaires — legifrance/config.py
Vérifie que les constantes et dictionnaires sont correctement définis.
"""
import pytest
from legifrance.config import (
    CODES, CODES2, PDF_FOLDER, PDF_FOLDER2, WORKERS, DATE_REF,
    OAUTH_URL, API_BASE, LEGIFRANCE,
)


class TestCodes:
    def test_codes_not_empty(self):
        assert len(CODES) > 0

    def test_codes2_not_empty(self):
        assert len(CODES2) > 0

    def test_code_civil_present(self):
        assert "Code civil" in CODES

    def test_code_civil_id(self):
        assert CODES["Code civil"] == "LEGITEXT000006070721"

    def test_all_ids_are_strings(self):
        for name, tid in {**CODES, **CODES2}.items():
            assert isinstance(tid, str), f"{name}: id devrait être une str"

    def test_all_ids_start_with_LEGITEXT(self):
        for name, tid in {**CODES, **CODES2}.items():
            assert tid.startswith("LEGITEXT"), f"{name}: id invalide '{tid}'"

    def test_no_duplicate_ids(self):
        all_ids = list(CODES.values()) + list(CODES2.values())
        assert len(all_ids) == len(set(all_ids)), "Des IDs Legifrance sont dupliqués"

    def test_no_duplicate_names(self):
        all_names = list(CODES.keys()) + list(CODES2.keys())
        assert len(all_names) == len(set(all_names)), "Des noms de codes sont dupliqués"


class TestConstants:
    def test_pdf_folders(self):
        assert PDF_FOLDER == "pdfs"
        assert PDF_FOLDER2 == "pdfs2"

    def test_workers_positive(self):
        assert WORKERS > 0

    def test_date_ref_format(self):
        import re
        assert re.match(r"\d{4}-\d{2}-\d{2}", DATE_REF)

    def test_urls(self):
        assert OAUTH_URL.startswith("https://")
        assert API_BASE.startswith("https://")
        assert LEGIFRANCE.startswith("https://")
