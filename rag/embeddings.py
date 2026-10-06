import os
from pathlib import Path

from .config import MODEL_NAME

_embeddings_instance = None


def _local_snapshot(model_name: str) -> str:
    cache_name = "models--" + model_name.replace("/", "--")
    snapshots = Path.home() / ".cache" / "huggingface" / "hub" / cache_name / "snapshots"
    if snapshots.exists():
        candidates = [p for p in snapshots.iterdir() if (p / "modules.json").exists()]
        if candidates:
            return str(sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0])
    return model_name


def get_embeddings():
    """Singleton: charge le modele d'embedding une seule fois, en priorite locale."""
    global _embeddings_instance
    if _embeddings_instance is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        local_only = os.environ.get("HF_LOCAL_ONLY", "1").strip() != "0"
        model_path = _local_snapshot(MODEL_NAME) if local_only else MODEL_NAME
        print(f"      [Embedding] Chargement du modele : {MODEL_NAME}")
        try:
            _embeddings_instance = HuggingFaceEmbeddings(
                model_name=model_path,
                model_kwargs={"device": "cpu", "local_files_only": local_only},
                encode_kwargs={"normalize_embeddings": True},
            )
        except TypeError:
            _embeddings_instance = HuggingFaceEmbeddings(
                model_name=model_path,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        except Exception as exc:
            raise RuntimeError(
                "Modele d'embedding introuvable en local. "
                "Connectez internet une fois pour le telecharger, ou lancez avec HF_LOCAL_ONLY=0."
            ) from exc
        print("      [Embedding] Modele charge")
    return _embeddings_instance
