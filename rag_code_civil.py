"""
Point d'entrée CLI pour le RAG juridique.

Usage:
    python rag_code_civil.py --build
    python rag_code_civil.py --query "divorce par consentement mutuel"
    python rag_code_civil.py --ask "quelles sont les causes de divorce ?"
    python rag_code_civil.py --ask "autorité parentale" --top_k 10
"""

import argparse
import os

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from rag import _gemma_available, ask, build_index, query, rerank
from rag.config import TOP_K


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG juridique")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", action="store_true", help="Construire l'index FAISS")
    group.add_argument("--query", type=str, help="Recherche sémantique (extraits bruts)")
    group.add_argument("--ask", type=str, help="Question avec réponse rédigée par LLM")
    parser.add_argument("--top_k", type=int, default=TOP_K, help=f"Nb résultats (défaut={TOP_K})")
    args = parser.parse_args()

    sep = "-" * 60

    if args.build:
        build_index()

    elif args.query:
        results = rerank(query(args.query, top_k=args.top_k), args.query)
        print(f"\nRésultats pour : « {args.query} »\n{sep}")
        if not results:
            print("Aucun résultat au-dessus du seuil de pertinence.")
        for i, r in enumerate(results, 1):
            print(f"\n[{i}] Score: {r['pertinence']} (L2={r['l2_distance']}) | {r['source_file']}")
            print(r["text"])
            print(sep)

    elif args.ask:
        if not _gemma_available():
            print(
                "\nClé API Google manquante.\n"
                "  Windows PowerShell : $env:GOOGLE_API_KEY='AIza...'\n"
                "  Linux/Mac          : export GOOGLE_API_KEY='AIza...'\n"
                "\nAffichage des extraits bruts :\n"
            )
            results = rerank(query(args.ask, top_k=args.top_k), args.ask)
            for i, r in enumerate(results, 1):
                print(f"[{i}] {r['pertinence']} | {r['source_file']}")
                print(r["text"])
                print(sep)
        else:
            print(f"\n{sep}")
            print(f"Question : {args.ask}")
            print("\nGénération de la réponse...\n")

            answer, results = ask(args.ask, top_k=args.top_k)

            print(f"Sources : {', '.join(r['source_file'] for r in results[:5])}")
            print(sep)
            print(answer)
            print(f"\n{sep}")
            print("Sources utilisées :")
            for i, r in enumerate(results[:5], 1):
                print(f"  [{i}] {r['source_file']} ({r['pertinence']})")
