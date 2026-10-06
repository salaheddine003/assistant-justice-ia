"""
Tests unitaires — update.py
Teste run() et rebuild_all_indexes().

Note : update.py exécute du code au niveau module (run + rebuild).
On mocke subprocess.run pour retourner un échec (returncode=1) lors de
l'import → ok1=False → rebuild_all_indexes() n'est PAS appelé automatiquement.
"""
import sys
import pytest
from unittest.mock import patch, MagicMock


def _load_update():
    """
    Importe (ou réimporte) update.py en isolation.
    subprocess.run mocké pour retourner un échec → le corps du module
    ne déclenche pas rebuild_all_indexes().
    """
    if "update" in sys.modules:
        del sys.modules["update"]

    fail_result = MagicMock(returncode=1, stdout="", stderr="test isolation")
    with patch("subprocess.run", return_value=fail_result):
        import update as _update
    return _update


# ── run() ─────────────────────────────────────────────────────────────────────

class TestRun:
    def test_returns_true_on_success(self):
        update = _load_update()
        ok_result = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("subprocess.run", return_value=ok_result):
            assert update.run("fetch_codes_complets.py") is True

    def test_returns_false_on_failure(self):
        update = _load_update()
        fail_result = MagicMock(returncode=1, stdout="", stderr="error")
        with patch("subprocess.run", return_value=fail_result):
            assert update.run("fetch_codes_complets.py") is False

    def test_cmd_contains_python_executable(self):
        update = _load_update()
        ok_result = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("subprocess.run", return_value=ok_result) as mock_sp:
            update.run("script.py")
        cmd = mock_sp.call_args[0][0]
        assert sys.executable in cmd

    def test_cmd_contains_script_name(self):
        update = _load_update()
        ok_result = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("subprocess.run", return_value=ok_result) as mock_sp:
            update.run("fetch_codes_complets.py")
        cmd = mock_sp.call_args[0][0]
        assert any("fetch_codes_complets.py" in part for part in cmd)

    def test_capture_output_enabled(self):
        update = _load_update()
        ok_result = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("subprocess.run", return_value=ok_result) as mock_sp:
            update.run("script.py")
        kwargs = mock_sp.call_args[1]
        assert kwargs.get("capture_output") is True

    def test_text_mode_enabled(self):
        update = _load_update()
        ok_result = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("subprocess.run", return_value=ok_result) as mock_sp:
            update.run("script.py")
        kwargs = mock_sp.call_args[1]
        assert kwargs.get("text") is True

    def test_logs_error_on_failure(self):
        update = _load_update()
        fail_result = MagicMock(returncode=1, stdout="", stderr="oh noes")
        with patch("subprocess.run", return_value=fail_result), \
             patch("logging.error") as mock_log:
            update.run("script.py")
        mock_log.assert_called_once()


# ── rebuild_all_indexes() ─────────────────────────────────────────────────────

class TestRebuildAllIndexes:
    def test_skips_missing_pdf_folder(self):
        update = _load_update()
        mock_api = MagicMock()
        mock_api.CODE_REGISTRY = {
            "Code manquant": {"pdf": "nonexistent_xyz_path", "index": "idx_test"}
        }
        mock_rag = MagicMock()
        with patch.dict("sys.modules", {"api": mock_api, "rag": mock_rag}):
            update.rebuild_all_indexes()
        mock_rag.build_index.assert_not_called()

    def test_skips_empty_pdf_folder(self, tmp_path):
        update = _load_update()
        empty = tmp_path / "empty_code"
        empty.mkdir()

        mock_api = MagicMock()
        mock_api.CODE_REGISTRY = {
            "Code vide": {"pdf": str(empty), "index": "idx_vide"}
        }
        mock_rag = MagicMock()
        with patch.dict("sys.modules", {"api": mock_api, "rag": mock_rag}):
            update.rebuild_all_indexes()
        mock_rag.build_index.assert_not_called()

    def test_calls_build_index_for_nonempty_folder(self, tmp_path):
        update = _load_update()
        pdf_dir = tmp_path / "Code civil"
        pdf_dir.mkdir()
        (pdf_dir / "art1.pdf").touch()

        mock_api = MagicMock()
        mock_api.CODE_REGISTRY = {
            "Code civil": {"pdf": str(pdf_dir), "index": "idx_civil"}
        }
        mock_rag = MagicMock()
        with patch.dict("sys.modules", {"api": mock_api, "rag": mock_rag}):
            update.rebuild_all_indexes()

        mock_rag.build_index.assert_called_once_with(
            pdf_folder=str(pdf_dir), index_path="idx_civil"
        )

    def test_processes_all_codes(self, tmp_path):
        """rebuild_all_indexes itère sur tous les codes avec PDFs."""
        update = _load_update()
        codes = {}
        for name in ("Code A", "Code B", "Code C"):
            d = tmp_path / name
            d.mkdir()
            (d / "art.pdf").touch()
            codes[name] = {"pdf": str(d), "index": f"idx_{name}"}

        mock_api = MagicMock()
        mock_api.CODE_REGISTRY = codes
        mock_rag = MagicMock()
        with patch.dict("sys.modules", {"api": mock_api, "rag": mock_rag}):
            update.rebuild_all_indexes()

        assert mock_rag.build_index.call_count == 3

    def test_continues_after_build_index_exception(self, tmp_path):
        """Une exception sur un code n'arrête pas les autres."""
        update = _load_update()
        for name in ("Code A", "Code B"):
            d = tmp_path / name
            d.mkdir()
            (d / "art.pdf").touch()

        mock_api = MagicMock()
        mock_api.CODE_REGISTRY = {
            "Code A": {"pdf": str(tmp_path / "Code A"), "index": "idx_a"},
            "Code B": {"pdf": str(tmp_path / "Code B"), "index": "idx_b"},
        }
        mock_rag = MagicMock()
        call_count = [0]
        def side_effect(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("index failed")
        mock_rag.build_index.side_effect = side_effect

        with patch.dict("sys.modules", {"api": mock_api, "rag": mock_rag}):
            update.rebuild_all_indexes()  # should not raise

        assert mock_rag.build_index.call_count == 2
