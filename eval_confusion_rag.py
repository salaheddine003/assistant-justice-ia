"""Évalue le routage question traitable / hors périmètre du prototype RAG.

La vérité terrain provient du champ `type` du mini-jeu existant : le cas
`piege` est hors périmètre, les six autres questions sont juridiquement
traitables. La prédiction est positive lorsque le meilleur score hybride
des sources retournées atteint le seuil documenté ci-dessous.
"""
from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).parent
INPUT = ROOT / "evaluation_rag_report.json"
OUTPUT_JSON = ROOT / "evaluation_confusion_report.json"
OUTPUT_PNG = ROOT / "tmp" / "report_assets" / "matrice_confusion_reelle.png"
THRESHOLD = 60.0


def safe_div(a, b):
    return a / b if b else 0.0


report = json.loads(INPUT.read_text(encoding="utf-8"))
rows = []
for case in report["results"]:
    best_hybrid = max(float(s["hybrid_score"]) for s in case["top_sources"])
    expected = 0 if case["type"] == "piege" else 1
    predicted = int(best_hybrid >= THRESHOLD)
    rows.append({
        "id": case["id"],
        "expected_answerable": expected,
        "predicted_answerable": predicted,
        "best_hybrid_score": best_hybrid,
    })

tp = sum(r["expected_answerable"] == 1 and r["predicted_answerable"] == 1 for r in rows)
fn = sum(r["expected_answerable"] == 1 and r["predicted_answerable"] == 0 for r in rows)
fp = sum(r["expected_answerable"] == 0 and r["predicted_answerable"] == 1 for r in rows)
tn = sum(r["expected_answerable"] == 0 and r["predicted_answerable"] == 0 for r in rows)

precision = safe_div(tp, tp + fp)
recall = safe_div(tp, tp + fn)
specificity = safe_div(tn, tn + fp)
accuracy = safe_div(tp + tn, len(rows))
f1 = safe_div(2 * precision * recall, precision + recall)

result = {
    "task": "routage question traitable par le corpus / hors perimetre",
    "threshold_hybrid_pct": THRESHOLD,
    "sample_size": len(rows),
    "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    "metrics": {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "specificity": round(specificity, 4),
        "f1": round(f1, 4),
    },
    "cases": rows,
    "limitation": (
        f"Evaluation exploratoire sur {len(rows)} questions; "
        "elle ne mesure pas la correction juridique des reponses."
    ),
}
OUTPUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

matrix = np.array([[tn, fp], [fn, tp]])
fig, ax = plt.subplots(figsize=(7.6, 6.2))
heatmap = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=max(1, matrix.max()))
fig.colorbar(heatmap, ax=ax)
ax.set_xticks([0, 1], ["Hors périmètre", "Traitable"])
ax.set_yticks([0, 1], ["Hors périmètre", "Traitable"])
ax.set_xlabel("Prédit")
ax.set_ylabel("Réel")
ax.set_title(f"Matrice de confusion — n = {len(rows)}")
for i in range(2):
    for j in range(2):
        ax.text(
            j, i, str(matrix[i, j]),
            ha="center", va="center", fontsize=18,
            color="white" if matrix[i, j] > matrix.max() / 2 else "#263238",
        )
fig.tight_layout()
OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUTPUT_PNG, dpi=220, bbox_inches="tight")
plt.close(fig)

print(json.dumps(result, ensure_ascii=False, indent=2))
