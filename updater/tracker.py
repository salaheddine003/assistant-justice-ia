"""
updater/tracker.py
──────────────────
Gestion du fichier last_update.json.

Ce fichier enregistre le timestamp de la dernière synchronisation réussie.
Il sert de référence pour savoir quels articles ont été modifiés depuis.
"""
import json
from datetime import datetime
from pathlib import Path

LAST_UPDATE_FILE = Path(__file__).parent.parent / "last_update.json"


def load_last_run_ts() -> float | None:
    """
    Charge le timestamp (secondes UNIX) de la dernière exécution réussie.
    Retourne None si c'est le premier run ou si le fichier est corrompu.
    """
    if not LAST_UPDATE_FILE.exists():
        return None
    try:
        data = json.loads(LAST_UPDATE_FILE.read_text(encoding="utf-8"))
        ts = float(data.get("last_run_ts", 0))
        return ts if ts > 0 else None
    except Exception:
        return None


def save_last_run_ts(ts: float) -> None:
    """Sauvegarde le timestamp de fin d'exécution avec une date lisible."""
    LAST_UPDATE_FILE.write_text(
        json.dumps(
            {
                "last_run_ts":   ts,
                "last_run_date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def last_run_label() -> str:
    """Retourne une chaîne lisible de la dernière synchro, ou 'jamais'."""
    ts = load_last_run_ts()
    if ts is None:
        return "jamais (premier téléchargement)"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
