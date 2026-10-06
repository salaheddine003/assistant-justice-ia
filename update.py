"""
update.py — Point d'entrée de la mise à jour automatique.
Toute la logique est dans le package updater/.

Usage :
  python update.py             → mise à jour normale (fetch + rebuild sélectif)
  run_update.bat               → idem, lancé via Windows Task Scheduler
"""
import logging
import subprocess
import sys
from pathlib import Path

from updater import run as run_update_pipeline


def run(script: str) -> bool:
    """Exécute un ancien script de maintenance (compatibilité CLI/tests)."""
    result = subprocess.run([sys.executable, script], capture_output=True, text=True)
    if result.returncode != 0:
        logging.error("Échec de %s : %s", script, result.stderr)
        return False
    return True


def rebuild_all_indexes() -> int:
    """Reconstruit les index présents, sans interrompre la série sur erreur."""
    from api import CODE_REGISTRY
    import rag

    successes = 0
    for cfg in CODE_REGISTRY.values():
        pdf_path = Path(cfg["pdf"])
        if not pdf_path.exists() or not any(pdf_path.glob("*.pdf")):
            continue
        try:
            rag.build_index(pdf_folder=str(pdf_path), index_path=cfg["index"])
            successes += 1
        except Exception:
            logging.exception("Échec de reconstruction pour %s", pdf_path)
    return successes

if __name__ == "__main__":
    run_update_pipeline()

