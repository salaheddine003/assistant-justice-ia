"""Audit reproductible du corpus juridique local et des index FAISS."""
from pathlib import Path
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib, json, time

import fitz

ROOT = Path(__file__).parent
OUT = ROOT / "audit_data_corpus.json"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return str(path), path.stat().st_size, h.hexdigest()


def inspect_pdf(item):
    path, size, digest = item
    try:
        document = fitz.open(path)
        pages = document.page_count
        chars = None
        document.close()
        return {"path": path, "size": size, "sha256": digest, "pages": pages,
                "text_chars": chars, "corrupt": False}
    except Exception as exc:
        return {"path": path, "size": size, "sha256": digest, "pages": 0,
                "text_chars": 0, "corrupt": True, "error": type(exc).__name__}


started = time.perf_counter()
files = sorted([*ROOT.joinpath("pdfs").rglob("*.pdf"), *ROOT.joinpath("pdfs2").rglob("*.pdf")])
with ThreadPoolExecutor(max_workers=12) as pool:
    hashed = list(pool.map(sha256, files, chunksize=128))
hash_groups = defaultdict(list)
for path, size, digest in hashed:
    hash_groups[digest].append(path)
unique_items = []
for digest, paths in hash_groups.items():
    p = Path(paths[0]); unique_items.append((str(p), p.stat().st_size, digest))
with ThreadPoolExecutor(max_workers=8) as pool:
    inspected = list(pool.map(inspect_pdf, unique_items, chunksize=32))

indexes=[]; total_vectors=0; dimensions=set(); index_bytes=0
try:
    import faiss
    for folder in sorted(ROOT.glob("faiss_index*")):
        ix=faiss.read_index(str(folder/"index.faiss")); size=(folder/"index.faiss").stat().st_size+(folder/"index.pkl").stat().st_size
        indexes.append({"name":folder.name,"vectors":ix.ntotal,"dimension":ix.d,"bytes":size})
        total_vectors += ix.ntotal; dimensions.add(ix.d); index_bytes += size
except Exception as exc:
    indexes=[{"error":type(exc).__name__}]

elapsed=time.perf_counter()-started
result={
    "audit_date":"2026-08-20", "duration_seconds":round(elapsed,3),
    "physical_pdf_count":len(files), "physical_bytes":sum(x[1] for x in hashed),
    "unique_sha256_count":len(hash_groups),
    "duplicate_physical_files":len(files)-len(hash_groups),
    "duplicate_hash_groups":sum(len(v)>1 for v in hash_groups.values()),
    "empty_files":sum(x[1]==0 for x in hashed),
    "unique_pdfs_inspected":len(inspected),
    "corrupt_unique_pdfs":sum(x["corrupt"] for x in inspected),
    "unique_pdfs_without_text":None,
    "total_pages_unique_pdfs":sum(x["pages"] for x in inspected),
    "total_text_characters_unique_pdfs":None,
    "faiss_index_count":len([x for x in indexes if "vectors" in x]),
    "total_vectors":total_vectors, "dimensions":sorted(dimensions),
    "index_bytes":index_bytes, "indexes":indexes,
    "limits":["Les chunks correspondent aux vecteurs enregistrés, mais un même document peut produire plusieurs chunks.","Le contrôle exhaustif du texte a dépassé vingt minutes : documents sans texte et total de caractères restent MESURE À EXÉCUTER."],
}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False,indent=2))
