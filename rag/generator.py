import os

from .config import GEMMA_MODEL, TOP_K
from .llm import call_gemma, ollama_available, provider
from .retrieval import query, rerank, reformulate_query


def _gemma_available() -> bool:
    if provider() == "google":
        return bool(os.environ.get("GOOGLE_API_KEY", ""))
    return ollama_available()


def _call_gemma(prompt: str) -> str:
    return call_gemma(prompt, temperature=0.2, max_tokens=4096)


def ask(question: str, top_k: int = TOP_K, index_path: str = None) -> tuple[str, list[dict]]:
    """
    RAG complet : reformulation → recherche → re-ranking → génération LLM.
    Retourne (réponse_str, résultats_list).
    """
    search_query = reformulate_query(question)
    results      = query(search_query, top_k=top_k, index_path=index_path)
    results      = rerank(results, question)

    if not results:
        return (
            "## ⚖️ Réponse juridique\n\n"
            f"**Question** : {question}\n\n"
            "---\n\n"
            "❌ Aucun article pertinent trouvé dans l'index pour cette question.\n"
            "Vérifiez que l'index est bien construit avec `--build`.",
            [],
        )

    context = "\n\n".join(
        f"[Source {i} — {r['source_file']} | Score: {r['pertinence']}]\n{r['text']}"
        for i, r in enumerate(results, 1)
    )

    prompt = (
        "Tu es un assistant juridique expert en droit français.\n"
        "Réponds de façon claire, directe et pratique, comme un avocat qui explique à son client.\n\n"
        "RÈGLES :\n"
        "- Commence TOUJOURS par une réponse directe à la question (1-2 phrases).\n"
        "- Ensuite explique les points importants en langage simple.\n"
        "- Liste les articles pertinents avec leur numéro et ce qu'ils disent concrètement.\n"
        "- Si plusieurs cas existent (ex: 4 types de divorce), mentionne-les tous brièvement.\n"
        "- Base-toi UNIQUEMENT sur les extraits fournis. N'invente aucun article.\n"
        "- Écris en français courant, évite le jargon inutile.\n\n"
        f"── EXTRAITS ──\n{context}\n\n"
        f"── QUESTION ──\n{question}\n\n"
        "── RÉPONSE ──\n"
    )

    raw = _call_gemma(prompt)

    if "⚖️" not in raw:
        sep = "─" * 60
        formatted = (
            f"## ⚖️ Réponse juridique\n\n"
            f"**Question** : {question}\n\n"
            f"---\n\n{raw}\n\n"
            f"{sep}\n"
            "*Source : Code civil français (analyse RAG)*"
        )
    else:
        formatted = raw

    return formatted, results
