"""
updater/fetcher.py
──────────────────
Télécharge les articles juridiques depuis l'API Légifrance (PISTE).

Logique smart :
- Compare le dateDebut de chaque article (fourni par la table des matières)
  avec le timestamp de la dernière exécution (last_run_ts).
- Télécharge uniquement les articles nouveaux ou modifiés.
- Retourne l'ensemble des codes ayant eu au moins un changement.
"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from legifrance import (
    CODES,
    CODES2,
    PDF_FOLDER,
    PDF_FOLDER2,
    WORKERS,
    collect_article_ids,
    get_table_matieres,
    get_token,
    traiter_article,
)


def _fetch_one_code(
    code_name: str,
    text_id: str,
    folder: str,
    last_run_ts: float | None,
) -> tuple[int, int, int, int]:
    """
    Télécharge un seul code juridique.
    Retourne (nouveaux, mis_a_jour, inchanges, erreurs).
    """
    token = get_token()
    try:
        tdm = get_table_matieres(token, text_id)
    except Exception as e:
        print(f"  [ERR] Table des matières ({code_name}) : {e}")
        return 0, 0, 0, 1

    articles_info = collect_article_ids(tdm, include_dates=True)
    nb = len(articles_info)
    print(f"  {nb} articles en vigueur")
    if nb == 0:
        return 0, 0, 0, 0

    dossier = os.path.join(folder, code_name)
    os.makedirs(dossier, exist_ok=True)

    nouveaux = mises_a_jour = erreurs = inchanges = traites = 0

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {
            pool.submit(
                traiter_article,
                token, aid, anum, sec, code_name, dossier,
                date_ms, last_run_ts,
            ): anum
            for aid, anum, sec, date_ms in articles_info
        }
        for fut in as_completed(futures):
            res = fut.result()
            traites += 1
            if res == "ok":        nouveaux += 1
            elif res == "updated": mises_a_jour += 1
            elif res == "skip":    inchanges += 1
            else:                  erreurs += 1
            if traites % 500 == 0:
                print(f"  {traites}/{nb}  ({nouveaux} new, {mises_a_jour} MAJ, {erreurs} err, {inchanges} exist)")

    return nouveaux, mises_a_jour, inchanges, erreurs


def fetch_all(last_run_ts: float | None) -> tuple[int, set[str]]:
    """
    Télécharge tous les codes (pdfs/ et pdfs2/).
    Retourne (total_changes, set_des_codes_modifies).
    """
    total_changes = 0
    changed_codes: set[str] = set()

    all_sources = [
        (CODES,  PDF_FOLDER),
        (CODES2, PDF_FOLDER2),
    ]

    for codes_dict, folder in all_sources:
        for code_name, text_id in codes_dict.items():
            print(f"\n{'='*65}")
            print(f"[>>] {code_name}  ({text_id})")

            nouveaux, mises_a_jour, inchanges, erreurs = _fetch_one_code(
                code_name, text_id, folder, last_run_ts
            )

            nb_changes = nouveaux + mises_a_jour
            if nb_changes > 0:
                changed_codes.add(code_name)
            total_changes += nb_changes

            print(
                f"  [OK] {nouveaux} nouveaux, {mises_a_jour} mis à jour, "
                f"{inchanges} inchangés, {erreurs} erreurs"
            )

    return total_changes, changed_codes
