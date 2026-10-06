"""
updater/rebuilder.py
─────────────────────
Reconstruit les index FAISS après une mise à jour des PDFs.

Deux modes :
- rebuild_selective(code_names) : uniquement les codes qui ont changé (rapide).
- rebuild_all()                 : tous les codes du registre (premier run / forcé).
"""
import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))  # garantit les imports root (api, rag)


def _normalize(name: str) -> str:
    """Normalise un nom de code pour la comparaison (accents, espaces, apostrophes)."""
    return (
        name.lower()
        .replace(" ", "")
        .replace("'", "")
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("î", "i")
        .replace("ô", "o")
        .replace("û", "u")
        .replace("ç", "c")
    )


def _match_registry(fetch_name: str, registry: dict) -> str | None:
    """
    Trouve la clé du CODE_REGISTRY correspondant au nom de dossier fetch_name.
    Les noms de dossiers (ex: "Code penal") diffèrent parfois des clés du registre
    (ex: "Code pénal") — on compare sans accents.
    """
    n1 = _normalize(fetch_name)
    for reg_name in registry:
        n2 = _normalize(reg_name)
        if n1 == n2 or n1 in n2 or n2 in n1:
            return reg_name
    return None


def _build_one(reg_name: str, cfg: dict, index: int, total: int) -> bool:
    """Construit l'index FAISS pour un code. Retourne True si succès."""
    from rag import build_index

    pdf_path = Path(cfg["pdf"])
    if not pdf_path.exists():
        logging.warning(f"[{index}/{total}] Dossier PDF absent : {cfg['pdf']}")
        return False

    pdf_count = len(list(pdf_path.glob("*.pdf")))
    if pdf_count == 0:
        logging.warning(f"[{index}/{total}] Dossier vide : {cfg['pdf']}")
        return False

    logging.info(f"[{index}/{total}] Rebuild : {reg_name} ({pdf_count} PDFs)")
    try:
        build_index(pdf_folder=cfg["pdf"], index_path=cfg["index"], code_name=reg_name)
        logging.info(f"[{index}/{total}] OK : {reg_name}")
        return True
    except Exception:
        logging.exception(f"[{index}/{total}] ERREUR : {reg_name}")
        return False


def rebuild_selective(code_names: list[str]) -> int:
    """
    Reconstruit uniquement les index des codes listés.
    Retourne le nombre d'index reconstruits avec succès.
    """
    from api import CODE_REGISTRY

    matched: dict[str, str] = {}
    for fetch_name in code_names:
        reg_name = _match_registry(fetch_name, CODE_REGISTRY)
        if reg_name:
            matched[fetch_name] = reg_name
        else:
            logging.warning(f"Code non trouvé dans le registre : '{fetch_name}'")

    total   = len(matched)
    success = sum(
        _build_one(reg_name, CODE_REGISTRY[reg_name], i, total)
        for i, (_, reg_name) in enumerate(matched.items(), 1)
    )
    logging.info(f"Rebuild sélectif terminé : {success}/{total} reconstruits.")
    return success


def rebuild_all() -> int:
    """
    Reconstruit TOUS les index FAISS.
    Utilisé au premier run ou lors d'une mise à jour forcée.
    Retourne le nombre d'index reconstruits avec succès.
    """
    from api import CODE_REGISTRY

    total   = len(CODE_REGISTRY)
    success = sum(
        _build_one(name, cfg, i, total)
        for i, (name, cfg) in enumerate(CODE_REGISTRY.items(), 1)
    )
    logging.info(f"Rebuild complet terminé : {success}/{total} reconstruits.")
    return success
