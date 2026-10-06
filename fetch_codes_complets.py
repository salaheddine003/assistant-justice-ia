"""
fetch_codes_complets.py — Point d'entrée pour le fetch seul.
Toute la logique est dans updater/fetcher.py.

Usage : python fetch_codes_complets.py
"""
import time
import os
from concurrent.futures import ThreadPoolExecutor

from updater.tracker import load_last_run_ts, save_last_run_ts, last_run_label
from updater.fetcher import fetch_all
from legifrance import get_token, get_table_matieres, collect_article_ids, traiter_article


def fetch_codes(codes: dict, folder: str) -> int:
    """API historique conservée pour les scripts et tests existants.

    Télécharge les articles de ``codes`` dans ``folder`` et retourne le nombre
    de nouveaux PDF. La mise à jour normale continue d'utiliser ``fetch_all``.
    """
    total = 0
    for code_name, text_id in codes.items():
        try:
            token = get_token()
            articles = collect_article_ids(get_table_matieres(token, text_id))
        except Exception:
            continue
        dossier = os.path.join(folder, code_name)
        os.makedirs(dossier, exist_ok=True)
        with ThreadPoolExecutor() as pool:
            results = list(pool.map(
                lambda a: traiter_article(token, a[0], a[1], a[2], code_name, dossier),
                articles,
            ))
        total += sum(result == "ok" for result in results)
    return total

if __name__ == "__main__":
    print(f"[INFO] Dernière synchronisation : {last_run_label()}")
    t_start = time.time()
    total, changed = fetch_all(load_last_run_ts())
    save_last_run_ts(t_start)
    print(f"\n[TERMINÉ] {total} PDFs traités | {len(changed)} code(s) modifié(s)")
    if changed:
        print(f"  Codes mis à jour : {', '.join(sorted(changed))}")

