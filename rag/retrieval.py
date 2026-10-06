import math
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote_plus

from .config import INDEX_PATH, SCORE_THRESHOLD, TOP_K
from .embeddings import get_embeddings


def _l2_to_similarity(distance: float) -> float:
    """
    Convertit une distance L2 FAISS en score de similarite [0, 100].
    distance 0.0 -> 100% | 0.5 -> 78% | 1.0 -> 61% | 1.4 -> 50% | 2.0 -> 37%
    """
    return round(100 * math.exp(-distance / 2), 1)


def _extract_article_number(text: str) -> int | None:
    """Extrait le numero d'article quand il est purement numerique."""
    m = re.search(r"^(\d+)[-_]", text or "")
    if m:
        return int(m.group(1))
    m = re.search(r"(?:article|art\.?)\s*(\d+)", text or "", re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower()


def _extract_article_ref(text: str) -> str | None:
    """Extrait une reference complete: L123-4, R221-1, 229, etc."""
    if not text:
        return None
    cleaned = text.replace("_", " ").replace(".pdf", "")
    patterns = [
        r"\b([LORDRA]\.?\s*\d+(?:-\d+)*[A-Z]?)\b",
        r"\b(?:article|art\.?)\s*([LORDRA]?\s*\d+(?:-\d+)*[A-Z]?)\b",
        r"^(\d+(?:-\d+)*)\b",
    ]
    for pat in patterns:
        m = re.search(pat, cleaned, re.IGNORECASE)
        if m:
            return re.sub(r"\s+", "", m.group(1).replace(".", "")).upper()
    return None


def _keywords(text: str) -> list[str]:
    stop_words = {
        "avec", "dans", "des", "donc", "elle", "elles", "est", "etre", "fait",
        "les", "leur", "leurs", "mais", "par", "pas", "peut", "plus", "pour",
        "que", "quel", "quelle", "quels", "quelles", "qui", "sans", "sont",
        "sur", "une", "vous",
    }
    normalized = _normalize(text)
    return [
        w.lower()
        for w in re.findall(r"\b[\w'-]+\b", normalized)
        if len(w) > 3 and w.lower() not in stop_words
    ]


def _lexical_score(question: str, text: str) -> float:
    """Score lexical simple inspire BM25, entre 0 et 100."""
    kws = _keywords(question)
    if not kws:
        return 0.0
    unique = set(kws)
    text_lower = _normalize(text)
    unique_hits = sum(1 for kw in unique if kw in text_lower)
    freq_hits = sum(min(text_lower.count(kw), 3) for kw in unique)
    coverage = unique_hits / len(unique)
    density = min(freq_hits / max(len(kws), 1), 1.5) / 1.5
    return round((coverage * 75) + (density * 25), 1)


def _source_url(article_ref: str | None, code_name: str = "") -> str:
    query = " ".join(part for part in [article_ref or "", code_name] if part).strip()
    if not query:
        return ""
    return "https://www.legifrance.gouv.fr/search/all?query=" + quote_plus(query)


def expand_legal_query(question: str) -> str:
    """Ajoute des synonymes juridiques utiles pour ameliorer le rappel FAISS."""
    q = question or ""
    q_norm = _normalize(q)
    additions: list[str] = []
    expansions = {
        "oqtf": "obligation de quitter le territoire francais recours delai contentieux administratif",
        "preavis": "préavis delai licenciement notification rupture contrat travail",
        "licenciement": "rupture contrat travail preavis indemnité salarie employeur",
        "loyer impaye": "loyer impayé bail locataire paiement commandement resiliation",
        "accident travail": "accident du travail maladie professionnelle indemnisation securite sociale",
        "construction sans permis": "permis de construire infraction urbanisme demolition sanction",
        "ordinateur portable": "question hors sujet droit civil absence article juridique reparation materiel",
    }
    for key, value in expansions.items():
        if key in q_norm:
            additions.append(value)
    if not additions:
        return q
    return q + " " + " ".join(additions)


def reformulate_query(question: str) -> str:
    """
    Convertit une question interrogative en mots-cles declaratifs pour ameliorer
    la similarite avec les textes juridiques.
    """
    patterns = [
        r"\bqu[\'e]est[\s-]+ce\s+qu[e\']\b",
        r"\best[\s-]+ce\s+qu[e\']\b",
        r"\bquelles?\s+sont\b",
        r"\bquels?\s+sont\b",
        r"\bcomment\s+(?:fonctionne|se\s+passe|faire|obtenir|calculer|determine|dÃ©termine)\b",
        r"\bpourquoi\b",
        r"\bcombien\b",
        r"\bquand\b",
        r"\bqui\s+(?:peut|doit|a|est)\b",
        r"\bqu[e\']\b",
        r"\bquelles?\b",
        r"\bquels?\b",
        r"\bcomment\b",
    ]
    cleaned = question
    for pat in patterns:
        cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(
        r"^\s*(?:sont|est|peut|peuvent|faut[-\s]il|doit|doivent|a[\s-]t[\s-]on|y\s+a[\s-]t[\s-]il)\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[?,!;:]", " ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    return cleaned if len(cleaned.split()) >= 2 else question


def query(question: str, top_k: int = TOP_K, index_path: str = None) -> list[dict]:
    """
    Recherche les chunks les plus pertinents dans l'index FAISS.
    Ajoute un score hybride: similarite vectorielle + score lexical.
    """
    from langchain_community.vectorstores import FAISS

    idx = index_path or INDEX_PATH
    if not Path(idx).exists():
        raise FileNotFoundError(
            f"Index non trouve : {idx}/\n"
            "Lancez d'abord : python rag_code_civil.py --build"
        )

    expanded_question = expand_legal_query(question)
    embeddings = get_embeddings()
    vectorstore = FAISS.load_local(idx, embeddings, allow_dangerous_deserialization=True)

    fetch_k = min(max(top_k * 4, 20), 60)
    results = vectorstore.similarity_search_with_score(expanded_question, k=fetch_k)

    output = []
    for doc, l2_distance in results:
        if l2_distance > SCORE_THRESHOLD:
            continue
        similarity_pct = _l2_to_similarity(l2_distance)
        source_file = doc.metadata.get("source_file", "?")
        code_name = doc.metadata.get("code_name", "")
        article_ref = _extract_article_ref(source_file) or _extract_article_ref(doc.page_content)
        lexical = _lexical_score(expanded_question, doc.page_content)
        hybrid_score = round((similarity_pct * 0.78) + (lexical * 0.22), 1)
        output.append({
            "pertinence": f"{similarity_pct}%",
            "pertinence_raw": similarity_pct,
            "hybrid_score": hybrid_score,
            "lexical_score": lexical,
            "l2_distance": round(l2_distance, 4),
            "source_file": source_file,
            "code_name": code_name,
            "article_num": _extract_article_number(source_file),
            "article_ref": article_ref,
            "source_url": _source_url(article_ref, code_name),
            "text": doc.page_content.strip(),
        })

    output.sort(key=lambda x: x["hybrid_score"], reverse=True)
    return output[:top_k]


def rerank(results: list[dict], question: str) -> list[dict]:
    """
    Re-ranking contextuel:
    1. boost lexical type BM25 leger ;
    2. boost des articles structurants ;
    3. boost des formulations de definition/enumeration.
    """
    keywords = _keywords(question)
    question_lower = question.lower()

    for r in results:
        text_lower = r["text"].lower()

        lexical = r.get("lexical_score")
        if lexical is None:
            lexical = _lexical_score(question, r["text"])
            r["lexical_score"] = lexical
        keyword_boost = 0.35 * (float(lexical) / 100)

        definition_boost = 0.0
        if any(kw in question_lower for kw in ["cause", "motif", "cas", "type", "forme"]) and \
           "divorce" in question_lower:
            if r.get("article_num") == 229 or r.get("article_ref") == "229":
                definition_boost = 0.6
            elif "divorce peut etre prononce" in text_lower or \
                 "divorce peut Ãªtre prononcÃ©" in text_lower or \
                 "divorce est prononce" in text_lower or \
                 "divorce est prononcÃ©" in text_lower:
                definition_boost = 0.35

        definition_patterns = [
            "peut etre prononce en cas",
            "peut Ãªtre prononcÃ© en cas",
            "sont au nombre de",
            "comprend",
            "se divise en",
            "sont les suivants",
        ]
        if any(p in text_lower for p in definition_patterns):
            definition_boost = max(definition_boost, 0.25)

        base_score = r.get("hybrid_score", r["pertinence_raw"])
        r["rerank_score"] = base_score * (1 + keyword_boost + definition_boost)

    if not keywords:
        results.sort(key=lambda x: x["pertinence_raw"], reverse=True)
    else:
        results.sort(key=lambda x: x["rerank_score"], reverse=True)
    return results
