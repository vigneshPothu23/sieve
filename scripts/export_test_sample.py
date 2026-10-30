"""Export a small, fixed sample of held-out test cases for the app's test-case explorer.

Derived from SQuAD (CC BY-SA 4.0) and databricks-dolly-15k (CC BY-SA 3.0); the
exported file carries the same share-alike licence (see THIRD_PARTY.md).
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rng = random.Random(7)


def load(n):
    return [json.loads(line) for line in open(ROOT / "data" / n, encoding="utf-8")]


ind, obf, ood = load("test_indirect.jsonl"), load("test_obfuscated.jsonl"), load("test_benign_ood.jsonl")
groups = {
    "Injected documents": [r for r in ind if r["subset"] == "indirect"],
    "Subtle injections": [r for r in ind if r["subset"] == "subtle"],
    "Clean documents": [r for r in ind if r["subset"] == "clean"],
    "Obfuscated injections": obf,
    "Hard negatives (benign)": [r for r in ood if r["subset"] == "hard_negative"],
}
out = ROOT / "reports" / "test_case_sample.jsonl"
with open(out, "w", encoding="utf-8") as f:
    for g, rows in groups.items():
        for r in rng.sample(rows, min(15, len(rows))):
            f.write(json.dumps({"group": g, "text": r["text"], "label": r["label"]}, ensure_ascii=False) + "\n")
print("wrote", out)
