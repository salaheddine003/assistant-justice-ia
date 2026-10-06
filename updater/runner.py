"""
updater/runner.py
─────────────────
Orchestrateur principal de la mise à jour automatique.

Ordre d'exécution :
  1. tracker   → charge le timestamp de la dernière synchro
  2. fetcher   → télécharge les articles modifiés depuis Légifrance
  3. rebuilder → reconstruit les index FAISS des codes modifiés
  4. tracker   → sauvegarde le nouveau timestamp

Appelé par update.py (entrée principale).
"""
import logging
import time
from pathlib import Path

LOG_FILE = Path(__file__).parent.parent / "update.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
)


def run() -> None:
    from .tracker   import load_last_run_ts, save_last_run_ts, last_run_label
    from .fetcher   import fetch_all
    from .rebuilder import rebuild_selective

    logging.info("=" * 60)
    logging.info("DÉBUT MISE À JOUR AUTOMATIQUE")
    logging.info(f"Dernière synchro : {last_run_label()}")

    t_start     = time.time()
    last_run_ts = load_last_run_ts()

    # ── Étape 1 : Téléchargement ────────────────────────────────────────────
    logging.info("Étape 1/2 — Fetch Légifrance...")
    try:
        total_changes, changed_codes = fetch_all(last_run_ts)
        logging.info(
            f"Fetch terminé : {total_changes} PDF traités, "
            f"{len(changed_codes)} code(s) modifié(s)."
        )
        if changed_codes:
            logging.info(f"Codes modifiés : {', '.join(sorted(changed_codes))}")
    except Exception:
        logging.exception("Fetch échoué — abandon.")
        return

    # ── Étape 2 : Rebuild sélectif ──────────────────────────────────────────
    if changed_codes:
        logging.info("Étape 2/2 — Rebuild des index FAISS modifiés...")
        rebuild_selective(list(changed_codes))
    else:
        logging.info("Étape 2/2 — Aucun changement détecté, aucun rebuild nécessaire.")

    # ── Sauvegarde du timestamp ─────────────────────────────────────────────
    save_last_run_ts(t_start)

    elapsed = round(time.time() - t_start)
    logging.info(f"FIN MISE À JOUR — durée totale : {elapsed}s")
    logging.info("=" * 60)
