import requests

from .config import API_BASE, DATE_REF
from .auth import hdrs


def get_table_matieres(token: str, text_id: str) -> dict:
    """Retourne la table des matières d'un code Legifrance."""
    r = requests.post(
        f"{API_BASE}/consult/code/tableMatieres",
        headers=hdrs(token),
        json={"textId": text_id, "date": DATE_REF},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def collect_article_ids(node: dict, path: str = "", include_dates: bool = False) -> list[tuple]:
    """Parcourt la table des matières.

    Par compatibilité, retourne des triplets ``(id, num, section)``. Le mode
    ``include_dates=True`` ajoute le timestamp d'entrée en vigueur utilisé par
    la mise à jour incrémentale.
    """
    result = []
    section = node.get("title", "")
    current_path = (path + " > " + section).strip(" > ") if section else path

    for art in node.get("articles", []):
        aid        = art.get("id", "")
        num        = art.get("num", "")
        etat       = art.get("etat", "")
        date_debut = art.get("dateDebut", 0)  # timestamp ms
        if aid and etat == "VIGUEUR":
            base = (aid, num, current_path)
            result.append(base + (date_debut,) if include_dates else base)

    for sec in node.get("sections", []):
        result.extend(collect_article_ids(sec, current_path, include_dates))

    return result


def get_article_content(token: str, article_id: str) -> dict | None:
    """Retourne le contenu complet d'un article."""
    r = requests.post(
        f"{API_BASE}/consult/getArticle",
        headers=hdrs(token),
        json={"id": article_id},
        timeout=20,
    )
    if not r.ok:
        return None
    return r.json().get("article", {})
