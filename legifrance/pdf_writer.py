import os
import re
import threading
import time

from fpdf import FPDF

from .auth import get_token
from .client import get_article_content
from .config import LEGIFRANCE

# ── Verrou thread-safe pour le renouvellement de token ───────────────────────
_token_lock    = threading.Lock()
_current_token = {"value": None}


def refresh_token_if_needed() -> str:
    """Renouvelle le token de façon thread-safe."""
    with _token_lock:
        _current_token["value"] = get_token()
    return _current_token["value"]


# ── Utilitaires texte ─────────────────────────────────────────────────────────

def clean(txt) -> str:
    if not txt:
        return ""
    txt = re.sub(r"<[^>]+>", "", str(txt))
    txt = txt.replace("[...]", "...").strip()
    txt = re.sub(r"\s+", " ", txt)
    return txt


def safe(txt) -> str:
    if not txt:
        return ""
    return clean(str(txt)).encode("latin-1", errors="replace").decode("latin-1")


def nom_fichier(num, code) -> str:
    num_clean  = re.sub(r"[^\w\-]", "_", clean(str(num  or "article")))[:60]
    code_clean = re.sub(r"[^\w\-]", "_", clean(str(code or "code"   )))[:50]
    return f"{num_clean}__{code_clean}.pdf"[:180]


# ── Génération PDF ────────────────────────────────────────────────────────────

def generer_pdf(chemin, num, code_name, section, texte, etat, date_debut, date_fin, url):
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # En-tête
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(20, 50, 120)
    pdf.multi_cell(0, 8, safe(f"Article {num}"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(0, 6, safe(code_name), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Méta-données
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(240, 242, 248)
    for label, val in [
        ("Section", section),
        ("Etat",    etat),
        ("Debut",   date_debut),
        ("Fin",     date_fin),
        ("URL",     url),
    ]:
        if val:
            pdf.set_font("Helvetica", "B", 9)
            pdf.multi_cell(0, 5, safe(f"{label} : {val}"), fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)

    # Contenu
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 6, safe(texte or "(contenu non disponible)"), new_x="LMARGIN", new_y="NEXT")

    pdf.output(chemin)


# ── Traitement d'un article (appelé par ThreadPoolExecutor) ─────────────────

def traiter_article(
    token, art_id, art_num, section_path, code_name, dossier,
    date_debut_ms: int = 0, last_run_ts: float | None = None,
) -> str:
    """
    Télécharge un article et génère son PDF.
    Retourne 'ok' (nouveau), 'updated' (modifié), 'skip' (inchangé) ou 'err'.

    date_debut_ms : timestamp milliseconde de l'entrée en vigueur de l'article
                    (issu de la table des matières Legifrance).
    last_run_ts   : timestamp UNIX (secondes) de la dernière mise à jour réussie.
                    Si None, on ne force jamais le re-téléchargement.
    """
    fname       = nom_fichier(art_num, code_name)
    chemin      = os.path.join(dossier, fname)
    was_existing = os.path.exists(chemin)

    if was_existing:
        # Sauter si pas de détection de MAJ, ou si l'article est plus ancien que la dernière synchro
        if last_run_ts is None or date_debut_ms is None or date_debut_ms <= 0:
            return "skip"
        if (date_debut_ms / 1000) <= last_run_ts:  # ms → s
            return "skip"
        # article plus récent que la dernière synchro → re-télécharger

    try:
        art = get_article_content(token, art_id)
        if art is None:
            token = refresh_token_if_needed()
            art   = get_article_content(token, art_id)
            if art is None:
                return "err"

        texte     = art.get("texte", "") or art.get("texteHtml", "") or ""
        etat      = art.get("etat", "")
        raw_debut = art.get("dateDebut", "")
        raw_fin   = art.get("dateFin",   "")

        def _parse_date(raw) -> str:
            if isinstance(raw, int):
                try:
                    return time.strftime("%Y-%m-%d", time.gmtime(raw / 1000))
                except Exception:
                    return ""
            return str(raw)[:10] if isinstance(raw, str) else ""

        url = f"{LEGIFRANCE}/codes/article_lc/{art_id}"
        generer_pdf(chemin, art_num, code_name, section_path, texte, etat,
                    _parse_date(raw_debut), _parse_date(raw_fin), url)
        return "updated" if was_existing else "ok"
    except Exception:
        return "err"
