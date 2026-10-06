"""
api.py — Backend FastAPI — Assistant Juridique IA
==================================================
Usage : uvicorn api:app --host 0.0.0.0 --port 8000 --reload

Endpoints :
  GET  /                    → SPA (static/index.html)
  GET  /api/codes           → liste des codes + statut index
  GET  /api/status          → santé de l'API et du LLM
  POST /api/ask             → stream SSE (sources puis tokens)
  POST /api/build           → construit l'index d'un code
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel

load_dotenv()

from spellchecker import SpellChecker
from rag.llm import call_gemma, model_name, ollama_available, provider, stream_gemma
from rag.retrieval import reformulate_query

# ── Correcteur orthographique français (chargé une fois) ──────────────────────
_spell = SpellChecker(language='fr', distance=1)

def _correct_typos(text: str) -> str:
    """
    Corrige les fautes de frappe évidentes dans une question en français.
    Préserve : chiffres, abréviations majuscules, références légales (L123-4),
    mots très courts (< 3 chars), et tout mot déjà correct.
    """
    words = text.split()
    corrected = []
    for word in words:
        # Garder les références légales (ex: L123-4, R45, D122-2)
        if re.match(r'^[A-Z]\d', word):
            corrected.append(word)
            continue
        # Garder les mots tout en majuscules (abréviations: SNCF, TVA...)
        stripped = re.sub(r'[^\w]', '', word)
        if stripped.isupper() and len(stripped) > 1:
            corrected.append(word)
            continue
        # Garder les mots courts ou avec des chiffres
        if len(stripped) <= 2 or any(c.isdigit() for c in stripped):
            corrected.append(word)
            continue
        # Extraire le mot sans ponctuation pour la correction
        prefix = re.match(r'^([^\w]*)', word).group(1)
        suffix = re.search(r'([^\w]*)$', word).group(1)
        core = stripped.lower()
        if _spell.unknown([core]):
            fix = _spell.correction(core)
            if fix and fix != core:
                corrected.append(prefix + fix + suffix)
                continue
        corrected.append(word)
    return ' '.join(corrected)

# ── Constantes LLM ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "Tu es un assistant juridique expert en droit français. "
    "Tu réponds en français, de façon claire, précise et bien structurée.\n\n"

    "STRUCTURE OBLIGATOIRE DE CHAQUE RÉPONSE :\n"
    "1. **Réponse directe** (1-2 phrases en gras) : réponds immédiatement et concrètement à la question.\n"
    "2. **Développement** structuré avec les informations des extraits :\n"
    "   - Si la question porte sur des types / cas / formes / conditions → "
    "liste-les TOUS en liste numérotée, sans en omettre aucun.\n"
    "   - Pour chaque point important, cite l'article de loi avec son numéro "
    "entre parenthèses ex : (art. 229 C. civ.) et explique-le concrètement.\n"
    "   - Utilise des titres ### si la réponse couvre plusieurs thèmes distincts.\n"
    "3. Termine TOUJOURS par : "
    "'⚠️ *Ces informations sont générales et ne remplacent pas l\\'avis d\\'un avocat.*'\n\n"

    "RÈGLES ABSOLUES :\n"
    "- Base-toi UNIQUEMENT sur les extraits fournis. N'invente aucun article.\n"
    "- Si les extraits donnent une information partielle, valorise ce qui est disponible "
    "sans inventer le reste.\n"
    "- Ne commence JAMAIS par une phrase négative du type "
    "'Les documents ne mentionnent pas...' ou 'Les extraits ne listent pas...' : "
    "commence toujours par la réponse positive et directe.\n"
    "- Si la question fait référence à la conversation précédente "
    "(résume, développe, explique autrement...), utilise l'historique des échanges.\n"
    "- Évite les formules de politesse inutiles et les intro génériques.\n"
)

MODE_INSTRUCTION: dict[str, str] = {
    "avocat": (
        "Tu réponds à un juriste / avocat. Sois technique et précis : "
        "cite les numéros d'articles exacts, les alinéas, la jurisprudence disponible, "
        "les conditions légales strictes. Utilise le vocabulaire juridique professionnel."
    ),
    "citoyen": (
        "Tu réponds à un citoyen non-juriste. Explique simplement, évite le jargon, "
        "donne des exemples concrets, et dis clairement ce que la personne peut/doit faire."
    ),
    "etudiant": (
        "Tu réponds à un étudiant en droit. Structure la réponse en plan clair, "
        "définis les notions, cite les textes, puis ajoute les points à retenir."
    ),
    "resume": (
        "Tu réponds en format résumé rapide. Donne l'essentiel en quelques points courts, "
        "avec les articles clés et une limite claire si les sources sont partielles."
    ),
}

SYSTEM_PROMPT_LLM_ONLY = (
    SYSTEM_PROMPT
    + "\n\nATTENTION — MODE CONNAISSANCE GÉNÉRALE :\n"
    "Aucun extrait de code juridique n'a été trouvé dans la base de données.\n"
    "Réponds en te basant sur ta connaissance approfondie du droit français "
    "(codes, lois, jurisprudence, doctrine). "
    "Précise toujours les articles ou textes dont tu parles en indiquant '(de mémoire)' "
    "après chaque référence. "
    "COMMENCE ta réponse par la ligne : "
    "'📚 *Réponse basée sur la connaissance générale du droit français (aucun article indexé trouvé pour ce sujet).*'\n"
)


def _search_all_codes(question: str, top_k: int = 5) -> list[dict]:
    """
    Fallback universel : cherche dans TOUS les codes indexés en parallèle.
    Retourne les meilleurs résultats toutes sources confondues.
    """
    import concurrent.futures
    from rag import query as rag_query, rerank
    from rag.retrieval import reformulate_query as _reformulate

    indexed_codes = [
        (name, cfg) for name, cfg in CODE_REGISTRY.items()
        if Path(cfg["index"]).exists()
    ]
    if not indexed_codes:
        return []

    search_q = _reformulate(question)

    def _search_one(args):
        name, cfg = args
        try:
            res = rag_query(search_q, top_k=3, index_path=cfg["index"])
            for r in res:
                if not r.get("code_name"):
                    r["code_name"] = name
            return res
        except Exception:
            return []

    all_results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for chunk in ex.map(_search_one, indexed_codes):
            all_results.extend(chunk)

    all_results = rerank(all_results, question)
    all_results.sort(key=lambda r: r.get("pertinence_raw", 0), reverse=True)
    return all_results[:top_k * 2]


def _is_vague(question: str, has_history: bool) -> bool:
    """Retourne True si la question est trop courte/vague sans contexte conversationnel."""
    if has_history:
        return False
    return len(question.strip().split()) < 3


def _build_search_query(question: str, history: list) -> str:
    """
    Construit la requête de recherche vectorielle en tenant compte de l'historique.

    Problème : les questions de suivi ("explique moi", "développe", "donne plus de détails")
    ne contiennent aucun mot-clé juridique → FAISS retourne des articles hors-sujet.

    Solution : si la question courante est une question de suivi (< 4 mots significatifs)
    ET qu'il y a un historique, on réutilise la dernière question utilisateur non-vague
    comme base de recherche.
    """
    meaningful_words = [w for w in question.strip().split() if len(w) > 2]
    is_followup = len(meaningful_words) < 5

    if is_followup and history:
        last_user_q = next(
            (m["content"] for m in reversed(history) if m.get("role") == "user"),
            None,
        )
        if last_user_q and len(last_user_q.split()) >= 3:
            return reformulate_query(last_user_q)

    return reformulate_query(question)


app = FastAPI(title="Assistant Juridique IA", docs_url="/docs", redoc_url=None)

# CORS_ORIGINS="*" par defaut (usage local); restreindre en production via .env
_cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Registre des codes (pdfs/ et pdfs2/) ─────────────────────────────────────
CODE_REGISTRY: dict[str, dict] = {
    # ── pdfs/ (Code civil uniquement) ────────────────────────────────────────
    "Code civil":                               {"pdf": "pdfs/Code civil",                                        "index": "faiss_index_code_civil"},
    # ── pdfs2/ — codes classiques ────────────────────────────────────────────
    "Code pénal":                               {"pdf": "pdfs2/Code penal",                                       "index": "faiss_index_code_penal"},
    "Code du travail":                          {"pdf": "pdfs2/Code du travail",                                  "index": "faiss_index_code_travail"},
    "Code de procédure pénale":                 {"pdf": "pdfs2/Code de procedure penale",                        "index": "faiss_index_code_proc_penale"},
    "Code de commerce":                         {"pdf": "pdfs2/Code de commerce",                                 "index": "faiss_index_code_commerce"},
    "Code général des impôts":                  {"pdf": "pdfs2/Code general des impots",                         "index": "faiss_index_code_impots"},
    "Code de la santé publique":                {"pdf": "pdfs2/Code de la sante publique",                       "index": "faiss_index_code_sante"},
    "Code de la sécurité sociale":              {"pdf": "pdfs2/Code de la securite sociale",                     "index": "faiss_index_code_secu"},
    "Code de l'environnement":                  {"pdf": "pdfs2/Code de l environnement",                         "index": "faiss_index_code_environnement"},
    "Code de l'urbanisme":                      {"pdf": "pdfs2/Code de l urbanisme",                             "index": "faiss_index_code_urbanisme"},
    "Code de l'éducation":                      {"pdf": "pdfs2/Code de l education",                             "index": "faiss_index_code_education"},
    "Code de la consommation":                  {"pdf": "pdfs2/Code de la consommation",                         "index": "faiss_index_code_conso"},
    "Code des transports":                      {"pdf": "pdfs2/Code des transports",                             "index": "faiss_index_code_transports"},
    "Code de la défense":                       {"pdf": "pdfs2/Code de la defense",                              "index": "faiss_index_code_defense"},
    "Code rural":                               {"pdf": "pdfs2/Code rural",                                      "index": "faiss_index_code_rural"},
    "Code monétaire et financier":              {"pdf": "pdfs2/Code monetaire et financier",                     "index": "faiss_index_code_monetaire"},
    "Code de la construction":                  {"pdf": "pdfs2/Code de la construction",                         "index": "faiss_index_code_construction"},
    "Code des assurances":                      {"pdf": "pdfs2/Code des assurances",                             "index": "faiss_index_code_assurances"},
    "Code de la propriété intellectuelle":      {"pdf": "pdfs2/Code de la propriete intellectuelle",             "index": "faiss_index_code_pi"},
    "Code des douanes":                         {"pdf": "pdfs2/Code des douanes",                                "index": "faiss_index_code_douanes"},
    # ── pdfs2/ — nouveaux codes ───────────────────────────────────────────────
    "Code de justice administrative":           {"pdf": "pdfs2/Code de justice administrative",                  "index": "faiss_index_code_justice_admin"},
    "Code de justice militaire":                {"pdf": "pdfs2/Code de justice militaire",                       "index": "faiss_index_code_justice_militaire"},
    "Code de justice militaire (nouveau)":      {"pdf": "pdfs2/Code de justice militaire nouveau",              "index": "faiss_index_code_justice_mil_new"},
    "Code des juridictions financières":        {"pdf": "pdfs2/Code des juridictions financières",              "index": "faiss_index_code_juridictions_fin"},
    "Code général des collectivités territoriales": {"pdf": "pdfs2/Code général des collectivités territoriales", "index": "faiss_index_code_coll_terr"},
    # ── nouveaux codes ────────────────────────────────────────────────────────
    "Code de procédure civile":                 {"pdf": "pdfs2/Code de procedure civile",                       "index": "faiss_index_code_proc_civile"},
    "Code des procédures civiles d'exécution":  {"pdf": "pdfs2/Code des procedures civiles d execution",        "index": "faiss_index_code_proc_exec"},
    "Code de la route":                         {"pdf": "pdfs2/Code de la route",                               "index": "faiss_index_code_route"},
    "Code de l'action sociale et des familles": {"pdf": "pdfs2/Code de l action sociale et des familles",       "index": "faiss_index_code_action_sociale"},
    "Code de la sécurité intérieure":           {"pdf": "pdfs2/Code de la securite interieure",                 "index": "faiss_index_code_secu_int"},
    "Code du sport":                            {"pdf": "pdfs2/Code du sport",                                  "index": "faiss_index_code_sport"},
    "Code du patrimoine":                       {"pdf": "pdfs2/Code du patrimoine",                             "index": "faiss_index_code_patrimoine"},
    "Code électoral":                           {"pdf": "pdfs2/Code electoral",                                 "index": "faiss_index_code_electoral"},
    "Code forestier":                           {"pdf": "pdfs2/Code forestier",                                 "index": "faiss_index_code_forestier"},
    "Code de la commande publique":             {"pdf": "pdfs2/Code de la commande publique",                   "index": "faiss_index_code_commande_pub"},
    "Code de la fonction publique":             {"pdf": "pdfs2/Code de la fonction publique",                   "index": "faiss_index_code_fonction_pub"},
    "Code pénitentiaire":                       {"pdf": "pdfs2/Code penitentiaire",                             "index": "faiss_index_code_penitentiaire"},
    "Code de la mutualité":                     {"pdf": "pdfs2/Code de la mutualite",                           "index": "faiss_index_code_mutualite"},
    "Code de la voirie routière":               {"pdf": "pdfs2/Code de la voirie routiere",                     "index": "faiss_index_code_voirie"},
    "Code de l'entrée et du séjour des étrangers": {"pdf": "pdfs2/Code de l entree et du sejour des etrangers", "index": "faiss_index_code_ceseda"},
    "Code du tourisme":                         {"pdf": "pdfs2/Code du tourisme",                               "index": "faiss_index_code_tourisme"},
    "Code de l'énergie":                        {"pdf": "pdfs2/Code de l energie",                              "index": "faiss_index_code_energie"},
    "Code minier":                              {"pdf": "pdfs2/Code minier",                                    "index": "faiss_index_code_minier"},
    "Code de la recherche":                     {"pdf": "pdfs2/Code de la recherche",                           "index": "faiss_index_code_recherche"},
    "Code du cinéma et de l'image animée":      {"pdf": "pdfs2/Code du cinema et de l image animee",            "index": "faiss_index_code_cinema"},
    "Code des pensions civiles et militaires":  {"pdf": "pdfs2/Code des pensions civiles et militaires",        "index": "faiss_index_code_pensions"},
    "Code des postes et communications électroniques": {"pdf": "pdfs2/Code des postes et des communications electroniques", "index": "faiss_index_code_postes"},
    "Livre des procédures fiscales":            {"pdf": "pdfs2/Livre des procedures fiscales",                  "index": "faiss_index_lpf"},
    "Code des relations public-administration": {"pdf": "pdfs2/Code des relations entre le public et l administration", "index": "faiss_index_code_crpa"},
    "Code de l'organisation judiciaire":        {"pdf": "pdfs2/Code de l organisation judiciaire",               "index": "faiss_index_code_org_judiciaire"},
    "Code général de la propriété des personnes publiques": {"pdf": "pdfs2/Code general de la propriete des personnes publiques", "index": "faiss_index_code_cg3p"},
    "Code de l'expropriation":                  {"pdf": "pdfs2/Code de l expropriation",                        "index": "faiss_index_code_expropriation"},
    # ── pdfs2/ — jurisprudence ────────────────────────────────────────────────
    "Conseil d'État (jurisprudence)":           {"pdf": "pdfs2/Conseil d Etat",                                  "index": "faiss_index_jurisprudence_ce"},
    "Cour Administrative d'Appel (jurisprudence)": {"pdf": "pdfs2/Cour Administrative d Appel",                 "index": "faiss_index_jurisprudence_caa"},
    "Lois et Ordonnances":                      {"pdf": "pdfs2/Lois et Ordonnances",                             "index": "faiss_index_lois_ordonnances"},
    "Tribunal Administratif (jurisprudence)":   {"pdf": "pdfs2/Tribunal Administratif",                         "index": "faiss_index_jurisprudence_ta"},
}


_PDF_COUNT_CACHE: dict[str, int] = {}


def _pdf_count(pdf_path: Path) -> int:
    key = str(pdf_path)
    if key not in _PDF_COUNT_CACHE:
        _PDF_COUNT_CACHE[key] = sum(1 for _ in pdf_path.glob("*.pdf")) if pdf_path.exists() else 0
    return _PDF_COUNT_CACHE[key]


def _code_info(name: str) -> dict:
    cfg      = CODE_REGISTRY[name]
    pdf_path = Path(cfg["pdf"])
    return {
        "name":      name,
        "indexed":   Path(cfg["index"]).exists(),
        "pdf_count": _pdf_count(pdf_path),
    }


def _confidence(results: list[dict]) -> dict:
    """Retourne un niveau de confiance lisible à partir des scores de recherche."""
    if not results:
        return {
            "level": "none",
            "label": "Aucune source fiable trouvée",
            "score": 0,
            "detail": "La réponse doit être considérée comme générale ou incomplète.",
        }

    scores = [float(r.get("pertinence_raw", 0) or 0) for r in results]
    best = max(scores)
    avg_top3 = sum(scores[:3]) / min(len(scores), 3)
    if best >= 70 and avg_top3 >= 60:
        level = "high"
        label = "Réponse bien appuyée par les sources"
        detail = "Plusieurs extraits pertinents soutiennent la réponse."
    elif best >= 55:
        level = "medium"
        label = "Sources partielles"
        detail = "Les extraits aident, mais la réponse doit rester prudente."
    else:
        level = "low"
        label = "Confiance faible"
        detail = "Les extraits retrouvés semblent peu proches de la question."
    return {"level": level, "label": label, "score": round(best, 1), "detail": detail}


def _safe_sources(results: list[dict], default_code: str = "") -> list[dict]:
    return [
        {
            "source_file": r.get("source_file", ""),
            "pertinence": r.get("pertinence", "?"),
            "pertinence_raw": r.get("pertinence_raw", 0),
            "hybrid_score": r.get("hybrid_score"),
            "lexical_score": r.get("lexical_score"),
            "article_num": r.get("article_num"),
            "article_ref": r.get("article_ref"),
            "source_url": r.get("source_url", ""),
            "text": r.get("text", "")[:800],
            "code": r.get("code_name", "") or default_code,
        }
        for r in results
    ]


def _gemma_stream(user_message: str, history: list[dict] | None = None, system_override: str | None = None):
    """Stream les tokens via le provider LLM configure, Ollama/Gemma par defaut."""
    system = system_override if system_override is not None else SYSTEM_PROMPT
    yield from stream_gemma(user_message, history=history, system=system, temperature=0.2, max_tokens=4096)


# ── Routes ────────────────────────────────────────────────────────────────────

# Bump this version to force all browsers to reload the new HTML
_UI_VERSION = "5"

@app.get("/", response_class=HTMLResponse)
def index(v: str = Query(default=None)):
    # Cache-bust: redirect to versioned URL so stale browser caches are bypassed
    if v != _UI_VERSION:
        r = RedirectResponse(url=f"/?v={_UI_VERSION}", status_code=302)
        r.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        r.headers["Pragma"] = "no-cache"
        return r
    html_file = Path("static/index.html")
    if not html_file.exists():
        raise HTTPException(404, "Interface introuvable. Vérifiez static/index.html")
    content = html_file.read_text(encoding="utf-8")
    return HTMLResponse(content=content, headers={
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    })


@app.get("/api/codes")
def list_codes():
    return [_code_info(n) for n in CODE_REGISTRY if Path(CODE_REGISTRY[n]["pdf"]).exists() or Path(CODE_REGISTRY[n]["index"]).exists()]


@app.get("/api/status")
def api_status():
    """Vérifie la disponibilité de l'API et du LLM local."""
    llm_provider = provider()
    has_key = bool(os.environ.get("GOOGLE_API_KEY", ""))
    model = model_name()
    codes = [_code_info(n) for n in CODE_REGISTRY]
    indexed_count = sum(1 for c in codes if c["indexed"])
    pdf_count = sum(c["pdf_count"] for c in codes)
    if llm_provider == "ollama":
        llm_status = "ollama_ok" if ollama_available() else "ollama_unavailable"
    elif has_key:
        llm_status = "gemini_ok"
    else:
        llm_status = "missing_key"
    return {
        "api":     "ok",
        "llm":     llm_status,
        "model":   model,
        "provider": llm_provider,
        "ollama_available": ollama_available() if llm_provider == "ollama" else None,
        "has_key": has_key,
        "codes_total": len(CODE_REGISTRY),
        "codes_indexed": indexed_count,
        "pdf_count": pdf_count,
    }


@app.get("/api/admin")
def admin_status():
    """Résumé d'administration pour l'interface locale."""
    update_file = Path("last_update.json")
    update_info = None
    if update_file.exists():
        try:
            update_info = json.loads(update_file.read_text(encoding="utf-8"))
        except Exception:
            update_info = {"error": "last_update.json illisible"}

    feedback_file = Path("feedback.jsonl")
    feedback_count = 0
    if feedback_file.exists():
        try:
            feedback_count = sum(1 for line in feedback_file.read_text(encoding="utf-8").splitlines() if line.strip())
        except Exception:
            feedback_count = None

    codes = [_code_info(n) for n in CODE_REGISTRY]
    return {
        "status": api_status(),
        "last_update": update_info,
        "feedback_count": feedback_count,
        "codes": codes,
    }


class AskBody(BaseModel):
    question: str
    code:     str
    top_k:    int = 5
    history:  list[dict] = []
    mode:     str = "citoyen"


@app.post("/api/ask")
def ask_endpoint(body: AskBody):
    if body.code not in CODE_REGISTRY:
        raise HTTPException(400, f"Code inconnu : {body.code}")
    cfg = CODE_REGISTRY[body.code]
    if not Path(cfg["index"]).exists():
        raise HTTPException(400, f"Index non construit pour '{body.code}'.")

    from rag import query, rerank

    def generate():
        t0  = time.perf_counter()
        ms  = lambda: round((time.perf_counter() - t0) * 1000)
        timing = {"retrieval_ms": 0, "first_token_ms": 0, "total_ms": 0, "tokens": 0}

        def emit(obj):
            return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

        try:
            question = _correct_typos(body.question)

            # Détecter les questions trop vagues sans contexte
            if _is_vague(question, bool(body.history)):
                yield emit({'type': 'sources', 'data': []})
                clarif = (
                    "Pourriez-vous préciser votre question ?\n\n"
                    "Indiquez le sujet juridique qui vous intéresse, par exemple :\n"
                    "- *Quel est le délai de préavis pour un licenciement ?*\n"
                    "- *Quelles sont les conditions du divorce par consentement mutuel ?*\n"
                    "- *Quels sont les droits du locataire en cas de loyer impayé ?*"
                )
                yield emit({'type': 'token', 'text': clarif})
                timing["total_ms"] = ms()
                yield emit({'type': 'timing', **timing})
                yield emit({'type': 'done'})
                return

            # ① Retrieval : reformulation + recherche vectorielle + reranking
            search_query = _build_search_query(question, body.history)
            results      = query(search_query, top_k=body.top_k, index_path=cfg["index"])
            results      = rerank(results, question)
            timing["retrieval_ms"] = ms()

            fallback_mode = None  # None | "all_codes" | "llm_only"

            # ━━ FALLBACK 1 : si le code sélectionné ne donne rien, on cherche partout ━━
            if not results:
                yield emit({'type': 'fallback', 'level': 'all_codes'})
                results = _search_all_codes(question, top_k=body.top_k)
                if results:
                    fallback_mode = "all_codes"

            # ② Envoyer les sources au client (800 chars pour plus de contexte visible)
            yield emit({
                'type': 'sources',
                'data': _safe_sources(results, body.code),
                'confidence': _confidence(results),
            })

            if not results:
                # ━━ FALLBACK 2 : zéro résultat même en cherchant partout → LLM pur ━━
                fallback_mode = "llm_only"
                yield emit({'type': 'fallback', 'level': 'llm_only'})
                mode_instr = MODE_INSTRUCTION.get(body.mode, MODE_INSTRUCTION["citoyen"])
                user_message = (
                    f"Instruction : {mode_instr}\n\n"
                    f"── QUESTION JURIDIQUE ──\n{question}\n\n"
                    "── RÉPONSE (cite les articles de loi pertinents, liste tous les cas) ──\n"
                )
                system = SYSTEM_PROMPT_LLM_ONLY
                first_token = True
                for token in _gemma_stream(user_message, history=body.history, system_override=system):
                    if first_token:
                        timing["first_token_ms"] = ms()
                        first_token = False
                    timing["tokens"] += 1
                    yield emit({'type': 'token', 'text': token})
            else:
                # ③ Construire le contexte RAG enrichi (code + extraits + question)
                codes_used = body.code if fallback_mode != "all_codes" else "tous les codes indexés"
                context = "\n\n".join(
                    f"[Art. {i} — {r.get('code_name', body.code)} | {r['source_file']} | Pertinence: {r['pertinence']}]\n{r['text']}"
                    for i, r in enumerate(results, 1)
                )
                mode_instr = MODE_INSTRUCTION.get(body.mode, MODE_INSTRUCTION["citoyen"])
                user_message = (
                    f"Code(s) juridique(s) consulté(s) : **{codes_used}**\n\n"
                    f"Mode de réponse : {body.mode}\n"
                    f"Instruction spécifique : {mode_instr}\n\n"
                    f"── EXTRAITS ({len(results)} articles) ──\n{context}\n\n"
                    f"── QUESTION ──\n{question}\n\n"
                    "── RÉPONSE (sois précis, cite les articles, liste tous les cas) ──\n"
                )
                if len(user_message) > 12000:
                    user_message = user_message[:12000] + "\n[...contexte tronqué...]"

                # ④ Streamer les tokens LLM
                first_token = True
                for token in _gemma_stream(user_message, history=body.history):
                    if first_token:
                        timing["first_token_ms"] = ms()
                        first_token = False
                    timing["tokens"] += 1
                    yield emit({'type': 'token', 'text': token})

        except Exception as e:
            yield emit({'type': 'error', 'text': str(e)[:200]})

        timing["total_ms"] = ms()
        yield emit({'type': 'timing', **timing})
        yield emit({'type': 'done'})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class BuildBody(BaseModel):
    code: str


@app.post("/api/build")
def build_endpoint(body: BuildBody):
    if body.code not in CODE_REGISTRY:
        raise HTTPException(400, f"Code inconnu : {body.code}")
    cfg = CODE_REGISTRY[body.code]
    if not Path(cfg["pdf"]).exists():
        raise HTTPException(400, f"Dossier PDF introuvable : {cfg['pdf']}")
    from rag import build_index
    try:
        build_index(pdf_folder=cfg["pdf"], index_path=cfg["index"], code_name=body.code)
        return {"status": "ok", "code": body.code}
    except Exception as e:
        raise HTTPException(500, str(e))


class FeedbackBody(BaseModel):
    question: str = ""
    answer: str = ""
    rating: str
    sources_ok: bool | None = None
    comment: str = ""
    mode: str = ""
    codes: list[str] = []


@app.post("/api/feedback")
def save_feedback(body: FeedbackBody):
    """Enregistre un retour utilisateur localement, au format JSON Lines."""
    if body.rating not in {"useful", "not_useful", "bad_sources"}:
        raise HTTPException(400, "rating invalide")

    row = body.dict()
    row["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    row["question"] = row["question"][:1000]
    row["answer"] = row["answer"][:4000]
    row["comment"] = row["comment"][:1000]

    with Path("feedback.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"status": "ok"}


# ── Détection automatique du code juridique ───────────────────────────────────
_CODE_KEYWORDS: dict[str, list[str]] = {
    "Code civil":                                   ["mariage","divorce","succession","héritier","contrat","responsabilité civile","propriété","donation","testament","tutelle","adoption","filiation","locataire","bail","loyer"],
    "Code pénal":                                   ["peine","infraction","crime","délit","contravention","emprisonnement","amende","viol","meurtre","vol","escroquerie","fraude","harcèlement","agression"],
    "Code du travail":                              ["licenciement","contrat travail","cdi","cdd","salaire","heures supplémentaires","congé","syndicat","grève","employeur","salarié","rupture conventionnelle","chômage","discrimination","heures travail"],
    "Code de procédure pénale":                     ["garde à vue","perquisition","instruction","juge","jugement","appel","cassation","mise en examen","détention provisoire","témoin","audition"],
    "Code de procédure civile":                     ["assignation","tribunal","procédure civile","huissier","saisie","référé","compétence","juridiction","délai","requête","citation","exploit"],
    "Code de commerce":                             ["société","sarl","sas","actionnaire","faillite","liquidation","redressement judiciaire","fonds de commerce","bail commercial","concurrence","marque"],
    "Code général des impôts":                      ["impôt","taxe","tva","revenu","fiscalité","déclaration","crédit d'impôt","plus-value","contribution","exonération","défiscalisation"],
    "Code de la santé publique":                    ["médecin","patient","hôpital","médicament","vaccination","consentement médical","urgence","pharmacie","établissement de santé","soins"],
    "Code de la sécurité sociale":                  ["retraite","pension","cotisation","maladie","accident travail","invalidité","allocations","caf","cpam","indemnités journalières"],
    "Code de l'environnement":                      ["pollution","environnement","déchets","eau","air","nuisance","espèce protégée","natura 2000","éolien","installation classée"],
    "Code de l'urbanisme":                          ["permis de construire","plan local","urbanisme","lotissement","zone","servitude","plu","construction","démolition","aménagement"],
    "Code de la consommation":                      ["consommateur","garantie","vice caché","remboursement","démarchage","crédit consommation","pratique commerciale","publicité","livraison"],
    "Code des assurances":                          ["assurance","sinistre","franchise","prime","indemnisation","résiliation","assureur","contrat assurance","couverture"],
    "Code de la propriété intellectuelle":          ["brevet","droit auteur","copyright","plagiat","propriété intellectuelle","oeuvre","licence","contrefaçon","logiciel","invention"],
    "Code monétaire et financier":                  ["banque","crédit","prêt","taux","virement","chèque","bourse","action","obligation","investissement","blanchiment"],
    "Code de la route":                             ["permis de conduire","infraction routière","radar","retrait de points","alcool volant","vitesse","accident route","stationnement","véhicule","circulation"],
    "Code de l'action sociale et des familles":     ["aide sociale","handicap","personne âgée","famille","protection enfance","allocations familiales","apad","aah","apa","maison retraite"],
    "Code de la sécurité intérieure":               ["police","gendarmerie","sécurité publique","maintien ordre","arme","manifestation","surveillance","renseignement","csi"],
    "Code du sport":                                ["sport","sportif","fédération sportive","dopage","club sportif","licence sportive","entraîneur","compétition","arbitrage sportif"],
    "Code du patrimoine":                           ["monument historique","patrimoine culturel","archéologie","musée","archive","classement monument","bien culturel","fouille"],
    "Code électoral":                               ["élection","vote","candidature","scrutin","liste électorale","propagande","financement campagne","fraude électorale","mandat"],
    "Code forestier":                               ["forêt","coupe arbre","déboisement","reboisement","propriété forestière","exploitation forestière","incendie forêt"],
    "Code de la commande publique":                 ["marché public","appel d'offres","contrat public","soumissionnaire","délégation service public","concession","achats publics"],
    "Code de la fonction publique":                 ["fonctionnaire","agent public","mutation","notation","discipline","grève fonction publique","statut fonctionnaire","concours","détachement"],
    "Code pénitentiaire":                           ["prison","détenu","incarcération","liberté conditionnelle","remise peine","établissement pénitentiaire","sursis","bracelet électronique"],
    "Code de la mutualité":                         ["mutuelle","complémentaire santé","cotisation mutuelle","remboursement mutuelle","adhésion mutuelle"],
    "Code de la voirie routière":                   ["voie publique","route nationale","autoroute","domaine public routier","travaux voirie","alignement","riverain"],
    "Code de l'entrée et du séjour des étrangers":  ["visa","titre de séjour","expulsion","immigration","naturalisation","asile","réfugié","étranger","carte de résident","oqtf"],
    "Code de justice administrative":               ["recours administratif","tribunal administratif","conseil état","excès pouvoir","annulation acte","fonction publique contentieux"],
    "Code général des collectivités territoriales": ["mairie","commune","prefecture","conseil municipal","budget communal","intercommunalité","département","région"],
    "Code des transports":                          ["transport","compagnie aérienne","train","sncf","billet","retard transport","marchandise","conducteur","responsabilité transporteur"],
    "Code rural":                                   ["agriculture","fermage","bail rural","exploitation agricole","subvention agricole","élevage","pesticide","parcelle"],
    "Code de la défense":                           ["armée","militaire","service national","réserve militaire","secret défense","équipement militaire"],
    "Code de la construction":                      ["maîtrise d'ouvrage","garantie décennale","constructeur","permis construire","réception travaux","vices construction","dommage ouvrage"],
    "Code du tourisme":                             ["tourisme","hôtel","agence voyage","hébergement touristique","camping","location vacances","guide touristique"],
    "Code de l'énergie":                            ["électricité","gaz","énergie","fournisseur énergie","réseau électrique","tarif énergie","nucléaire","énergies renouvelables"],
    "Code minier":                                  ["mine","extraction","concession minière","géothermie","hydrocarbure","sous-sol","carrière"],
    "Code de la recherche":                         ["recherche scientifique","université","laboratoire","publication scientifique","brevet recherche","doctorat"],
    "Code du cinéma et de l'image animée":          ["cinéma","film","audiovisuel","csa","arcom","production audiovisuelle","diffusion","streaming"],
    "Code des pensions civiles et militaires":      ["pension retraite fonctionnaire","pension militaire","réversion fonctionnaire","retraite civil"],
    "Code des postes et communications électroniques": ["télécommunication","sfr","orange","free","opérateur mobile","internet","fréquence","arcep","courrier postal"],
    "Livre des procédures fiscales":                ["contrôle fiscal","vérification comptabilité","redressement fiscal","prescription fiscale","contentieux fiscal","avis imposition"],
    "Code des relations public-administration":     ["droit accès document administratif","motivation décision","silence administration","crpa","droits usagers"],
    "Code de l'organisation judiciaire":            ["tribunal judiciaire","cour appel","compétence territoriale","ressort","organisation tribunal","greffe"],
    "Code général de la propriété des personnes publiques": ["domaine public","domaine privé état","propriété publique","bien public","domanialité","cession bien public"],
    "Code de l'expropriation":                      ["expropriation","utilité publique","indemnité expropriation","enquête publique","dépossession","emprise"],
    "Code des procédures civiles d'exécution":      ["saisie","huissier","saisie salaire","saisie bancaire","expulsion locataire","contrainte","voie exécution","astreinte"],
}

class DetectBody(BaseModel):
    question: str

@app.post("/api/detect-codes")
def detect_codes(body: DetectBody):
    """Détecte automatiquement les codes juridiques pertinents pour une question."""
    q_lower = _correct_typos(body.question).lower()
    scored: list[tuple[int, str]] = []
    for code, keywords in _CODE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in q_lower)
        if score > 0:
            scored.append((score, code))
    scored.sort(key=lambda x: -x[0])
    # Retourner max 3 codes, seulement ceux qui ont un index
    result = [
        {"code": c, "score": s, "indexed": Path(CODE_REGISTRY[c]["index"]).exists()}
        for s, c in scored[:3]
        if c in CODE_REGISTRY
    ]
    # Fallback : Code civil si rien détecté
    if not result:
        result = [{"code": "Code civil", "score": 0, "indexed": Path(CODE_REGISTRY["Code civil"]["index"]).exists()}]
    return {"codes": result}


# ── Multi-codes : recherche dans plusieurs codes simultanément ────────────────
class MultiAskBody(BaseModel):
    question: str
    codes:    list[str]
    top_k:    int = 5
    history:  list[dict] = []
    mode:     str = "citoyen"   # "citoyen" | "avocat"

@app.post("/api/ask-multi")
def ask_multi_endpoint(body: MultiAskBody):
    """Recherche dans plusieurs codes en parallèle, fusionne et stream."""
    import concurrent.futures

    for code in body.codes:
        if code not in CODE_REGISTRY:
            raise HTTPException(400, f"Code inconnu : {code}")
        if not Path(CODE_REGISTRY[code]["index"]).exists():
            raise HTTPException(400, f"Index non construit pour '{code}'.")

    from rag import query, rerank

    mode_instr = MODE_INSTRUCTION.get(body.mode, MODE_INSTRUCTION["citoyen"])

    def search_one(code: str, question: str):
        cfg = CODE_REGISTRY[code]
        search_q = _build_search_query(question, body.history)
        res = query(search_q, top_k=body.top_k, index_path=cfg["index"])
        res = rerank(res, question)
        for r in res:
            # code_name vient de la metadata si l'index a été buildé avec code_name,
            # sinon on utilise le nom passé par l'appelant
            if not r.get("code_name"):
                r["code_name"] = code
        return res

    def generate():
        t0  = time.perf_counter()
        ms  = lambda: round((time.perf_counter() - t0) * 1000)
        timing = {"retrieval_ms": 0, "first_token_ms": 0, "total_ms": 0, "tokens": 0}

        def emit(obj):
            return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

        try:
            question = _correct_typos(body.question)

            if _is_vague(question, bool(body.history)):
                yield emit({'type': 'sources', 'data': []})
                yield emit({'type': 'token', 'text': "Veuillez préciser votre question juridique."})
                yield emit({'type': 'done'})
                return

            # Recherche parallèle dans tous les codes
            all_results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(body.codes)) as ex:
                futures = {ex.submit(search_one, c, question): c for c in body.codes}
                for fut in concurrent.futures.as_completed(futures):
                    try:
                        all_results.extend(fut.result())
                    except Exception:
                        pass

            # Trier global par pertinence_raw décroissant, garder top top_k*len(codes)
            all_results.sort(key=lambda r: r.get("pertinence_raw", 0), reverse=True)
            all_results = all_results[:body.top_k * len(body.codes)]
            timing["retrieval_ms"] = ms()

            yield emit({
                'type': 'sources',
                'data': _safe_sources(all_results),
                'confidence': _confidence(all_results),
            })

            if not all_results:
                # ━━ FALLBACK LLM pur ━━
                yield emit({'type': 'fallback', 'level': 'llm_only'})
                user_message = (
                    f"Instruction : {mode_instr}\n\n"
                    f"── QUESTION JURIDIQUE ──\n{question}\n\n"
                    "── RÉPONSE (cite les articles de loi pertinents, liste tous les cas) ──\n"
                )
                first_token = True
                for token in _gemma_stream(user_message, history=body.history, system_override=SYSTEM_PROMPT_LLM_ONLY):
                    if first_token:
                        timing["first_token_ms"] = ms()
                        first_token = False
                    timing["tokens"] += 1
                    yield emit({'type': 'token', 'text': token})
            else:
                codes_str = ", ".join(body.codes)
                context = "\n\n".join(
                    f"[{r.get('code_name','?')} — {r['source_file']} | {r['pertinence']}]\n{r['text']}"
                    for i, r in enumerate(all_results, 1)
                )
                user_message = (
                    f"Codes juridiques consultés : **{codes_str}**\n\n"
                    f"Mode de réponse : {body.mode}\n"
                    f"Instruction spécifique : {mode_instr}\n\n"
                    f"── EXTRAITS ({len(all_results)} articles) ──\n{context}\n\n"
                    f"── QUESTION ──\n{question}\n\n"
                    "── RÉPONSE (cite les articles et leur code d'origine, liste tous les cas, "
                    "signale si des codes se complètent ou se contredisent) ──\n"
                )
                if len(user_message) > 14000:
                    user_message = user_message[:14000] + "\n[...contexte tronqué...]"

                first_token = True
                for token in _gemma_stream(user_message, history=body.history):
                    if first_token:
                        timing["first_token_ms"] = ms()
                        first_token = False
                    timing["tokens"] += 1
                    yield emit({'type': 'token', 'text': token})

        except Exception as e:
            yield emit({'type': 'error', 'text': str(e)[:200]})

        timing["total_ms"] = ms()
        yield emit({'type': 'timing', **timing})
        yield emit({'type': 'done'})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Suggestions de questions de suivi ─────────────────────────────────────────
class SuggestBody(BaseModel):
    question: str
    answer:   str
    code:     str

@app.post("/api/suggestions")
def get_suggestions(body: SuggestBody):
    """Génère 3 questions de suivi pertinentes basées sur la réponse."""
    prompt = (
        f"Voici une question juridique et sa réponse. "
        f"Génère exactement 3 questions de suivi courtes et pertinentes "
        f"qu'un utilisateur pourrait poser ensuite. "
        f"Réponds UNIQUEMENT avec les 3 questions, une par ligne, sans numérotation.\n\n"
        f"Question initiale : {body.question}\n"
        f"Réponse : {body.answer[:1000]}\n"
        f"Code : {body.code}\n\n"
        f"3 questions de suivi :"
    )
    try:
        raw = _call_gemma_simple(prompt)
        lines = [l.strip().lstrip("•-123.").strip() for l in raw.strip().split("\n") if l.strip()]
        questions = [l for l in lines if len(l) > 10][:3]
        return {"suggestions": questions}
    except Exception as e:
        return {"suggestions": []}


def _call_gemma_simple(prompt: str) -> str:
    """Appel non-streame pour les taches courtes via Ollama/Gemma par defaut."""
    return call_gemma(prompt, temperature=0.4, max_tokens=300)

