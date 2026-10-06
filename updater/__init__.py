"""
updater/
─────────
Package de mise à jour automatique des lois et des index FAISS.

Structure :
  tracker.py   → gestion de last_update.json (timestamp dernière synchro)
  fetcher.py   → téléchargement des articles modifiés depuis Légifrance
  rebuilder.py → reconstruction sélective ou complète des index FAISS
  runner.py    → orchestrateur (appelé par update.py)
"""
from .tracker   import load_last_run_ts, save_last_run_ts, last_run_label
from .fetcher   import fetch_all
from .rebuilder import rebuild_selective, rebuild_all
from .runner    import run

__all__ = [
    "load_last_run_ts",
    "save_last_run_ts",
    "last_run_label",
    "fetch_all",
    "rebuild_selective",
    "rebuild_all",
    "run",
]
