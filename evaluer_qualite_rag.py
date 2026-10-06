import json
import unicodedata
from pathlib import Path

from rag import query, rerank
from api import CODE_REGISTRY, _build_search_query


DATASET = Path("evaluation_questions.json")
REPORT = Path("evaluation_rag_report.json")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower()


def evaluate_case(case: dict) -> dict:
    question = case["question"]
    expected_terms = [normalize(t) for t in case.get("expected_terms", [])]
    all_results = []

    for code in case.get("codes", []):
        cfg = CODE_REGISTRY.get(code)
        if not cfg or not Path(cfg["index"]).exists():
            continue
        search_query = _build_search_query(question, [])
        try:
            results = query(search_query, top_k=5, index_path=cfg["index"])
            results = rerank(results, question)
            for r in results:
                r["code_name"] = r.get("code_name") or code
            all_results.extend(results)
        except Exception as exc:
            return {"id": case["id"], "status": "error", "error": str(exc)}

    all_results.sort(key=lambda r: r.get("rerank_score", r.get("hybrid_score", 0)), reverse=True)
    joined = normalize(" ".join(r.get("text", "") for r in all_results[:5]))
    hits = [term for term in expected_terms if term in joined]
    best_score = max([r.get("pertinence_raw", 0) for r in all_results], default=0)
    best_lexical = max([r.get("lexical_score", 0) for r in all_results], default=0)
    source_count = len(all_results)
    if case.get("type") == "piege":
        pass_terms = best_lexical < 45 or len(hits) >= 1
    else:
        pass_terms = len(hits) >= max(1, min(2, len(expected_terms)))
    pass_sources = source_count > 0 and best_score >= 45

    return {
        "id": case["id"],
        "type": case.get("type", ""),
        "question": question,
        "codes": case.get("codes", []),
        "status": "pass" if pass_terms and pass_sources else "review",
        "best_score": best_score,
        "best_lexical_score": best_lexical,
        "source_count": source_count,
        "expected_hits": hits,
        "top_sources": [
            {
                "code": r.get("code_name", ""),
                "article_ref": r.get("article_ref"),
                "source_file": r.get("source_file"),
                "score": r.get("pertinence"),
                "hybrid_score": r.get("hybrid_score"),
            }
            for r in all_results[:3]
        ],
    }


def main():
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    results = [evaluate_case(case) for case in cases]
    summary = {
        "total": len(results),
        "pass": sum(1 for r in results if r["status"] == "pass"),
        "review": sum(1 for r in results if r["status"] == "review"),
        "error": sum(1 for r in results if r["status"] == "error"),
    }
    payload = {"summary": summary, "results": results}
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
