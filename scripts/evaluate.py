"""Evaluate Sieve on the held-out test sets and write reports/eval_results.json.

    python scripts/evaluate.py

Systems compared (document level):
  * sieve            full pipeline (normalisation + rules + ML + fusion)
  * sieve_no_norm    ablation: same model on raw text (no Unicode/HTML normalisation)
  * ml_only          ablation: learned text model only, no rules (threshold chosen at the same calib FPR)
  * keyword_baseline a typical phrase-list filter
  * protectai_deberta (optional) results from scripts/baseline_deberta.py, merged if present
"""
from __future__ import annotations

import json
import re
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sieve.engine import ALLOW, BLOCK, Scanner  # noqa: E402
from sieve.model import load_default_model  # noqa: E402
from sieve.normalize import normalize  # noqa: E402
from sieve.sanitize import sanitize  # noqa: E402
from sieve.segment import segment  # noqa: E402

KEYWORDS = [
    "ignore previous instructions", "ignore all previous instructions", "ignore the above", "disregard the above",
    "disregard previous", "forget your instructions", "system prompt", "jailbreak", "do anything now",
    "you are now", "new instructions", "ignore your instructions", "developer mode",
]


def load(name):
    return [json.loads(line) for line in open(ROOT / "data" / name, encoding="utf-8")]


def keyword_flag(text: str) -> bool:
    t = re.sub(r"\s+", " ", text.lower())
    return any(k in t for k in KEYWORDS)


def metrics(y, pred):
    y, pred = np.asarray(y), np.asarray(pred)
    tp = int(((y == 1) & pred).sum()); fp = int(((y == 0) & pred).sum())
    fn = int(((y == 1) & ~pred).sum()); tn = int(((y == 0) & ~pred).sum())
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f1 = 2 * p * r / (p + r) if p and r else (0.0 if p is not None and r is not None else None)
    rnd = lambda x: None if x is None else round(x, 4)  # noqa: E731
    return {"n": int(len(y)), "tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": rnd(p), "recall": rnd(r), "f1": rnd(f1),
            "fpr": rnd(fp / (fp + tn)) if fp + tn else None, "fnr": rnd(fn / (fn + tp)) if fn + tp else None}


class MLOnly:
    """Ablation: max over segments of the learned text model, no rules, no fusion.

    Threshold calibrated exactly like Sieve's review threshold: 2% FPR on clean calibration documents.
    """

    def __init__(self, model, calib_rows):
        self.m = model
        doc_max, doc_lab = {}, {}
        for r in calib_rows:
            s = self.m.ml_logit(normalize(r["text"]).text)
            doc_max[r["doc"]] = max(doc_max.get(r["doc"], -1e9), s)
            doc_lab[r["doc"]] = max(doc_lab.get(r["doc"], 0), r["label"])
        neg = np.array([v for d, v in doc_max.items() if doc_lab[d] == 0])
        self.t_review = float(np.quantile(neg, 0.98))

    def flag(self, text):
        n = normalize(text).text
        return any(self.m.ml_logit(s.text) >= self.t_review for s in segment(n))


def main():
    scanner = Scanner()
    model = load_default_model()
    calib = load("calib_segments.jsonl")
    ml_only = MLOnly(model, calib)

    def scan_raw(text):
        return scanner.scan(text, normalize_input=False)

    sets = {
        "indirect": load("test_indirect.jsonl"),
        "obfuscated": load("test_obfuscated.jsonl"),
        "benign_ood": load("test_benign_ood.jsonl"),
        "deepset_external": load("test_deepset.jsonl"),
    }

    report = {"generated_at": time.strftime("%Y-%m-%d %H:%M"), "model_version": model.version,
              "thresholds": model.thresholds, "systems": {}, "breakdowns": {}, "latency_ms": {}, "sanitizer": {}}
    systems = ["sieve_flag", "sieve_block", "sieve_no_norm", "ml_only", "keyword_baseline"]
    for s in systems:
        report["systems"][s] = {}

    lat = []
    per_doc = {}
    for name, rows in sets.items():
        y = [r["label"] for r in rows]
        preds = {s: [] for s in systems}
        res_list = []
        for r in rows:
            t0 = time.perf_counter()
            res = scanner.scan(r["text"])
            lat.append((time.perf_counter() - t0) * 1000)
            res_list.append(res)
            preds["sieve_flag"].append(res.verdict != ALLOW)
            preds["sieve_block"].append(res.verdict == BLOCK)
            preds["sieve_no_norm"].append(scan_raw(r["text"]).verdict != ALLOW)
            preds["ml_only"].append(ml_only.flag(r["text"]))
            preds["keyword_baseline"].append(keyword_flag(r["text"]))
        per_doc[name] = (rows, res_list)
        for s in systems:
            report["systems"][s][name] = metrics(y, preds[s])
        print(f"{name:18s} " + "  ".join(f"{s}: R={report['systems'][s][name]['recall']} FPR={report['systems'][s][name]['fpr']}" for s in systems[:2]))

        # breakdowns
        if name == "indirect":
            bd = {}
            for key in ("subset", "position"):
                for val in sorted({str(r.get(key)) for r in rows if r["label"] == 1}):
                    idx = [i for i, r in enumerate(rows) if r["label"] == 1 and str(r.get(key)) == val]
                    bd[f"{key}={val}"] = {s: round(float(np.mean([preds[s][i] for i in idx])), 4) for s in systems}
            report["breakdowns"]["indirect_recall"] = bd
        if name == "obfuscated":
            bd = {}
            for val in sorted({r["obfuscation"] for r in rows}):
                idx = [i for i, r in enumerate(rows) if r["obfuscation"] == val]
                bd[val] = {s: round(float(np.mean([preds[s][i] for i in idx])), 4) for s in systems}
            report["breakdowns"]["obfuscated_recall"] = bd
        if name == "benign_ood":
            bd = {}
            for val in sorted({r["subset"] for r in rows}):
                idx = [i for i, r in enumerate(rows) if r["subset"] == val]
                bd[val] = {s: round(float(np.mean([preds[s][i] for i in idx])), 4) for s in systems}
            report["breakdowns"]["benign_fpr"] = bd
            report["false_positive_examples"] = [
                {"text": rows[i]["text"][:300], "subset": rows[i]["subset"], "risk": res_list[i].risk}
                for i in range(len(rows)) if preds["sieve_flag"][i]][:15]

    # localisation + sanitiser on the indirect set
    rows, results = per_doc["indirect"]
    loc_hits, loc_n, removed_ok, removed_n, kept_ratio, rescan_clean = 0, 0, 0, 0, [], 0
    for r, res in zip(rows, results):
        if r["label"] == 1 and res.verdict != ALLOW:
            inj = normalize(r["injection"]).text
            top = max(res.segments, key=lambda s: s.prob)
            loc_n += 1
            words = set(re.findall(r"\w+", inj.lower()))
            tw = set(re.findall(r"\w+", top.text.lower()))
            loc_hits += len(words & tw) / max(1, len(words)) >= 0.5
            clean = sanitize(res)
            removed_n += 1
            rescan = scanner.scan(clean.text) if clean.text.strip("[segment removed by Sieve] \n") else None
            residual = rescan is not None and rescan.verdict != ALLOW
            rescan_clean += not residual
            # payload considered removed if <30% of its distinctive words survive and no residual flag
            surv = words & set(re.findall(r"\w+", clean.text.lower()))
            removed_ok += (len(surv) / max(1, len(words)) < 0.3) and not residual
        if r["label"] == 0:
            clean = sanitize(res)
            kept_ratio.append(len(clean.text) / max(1, len(res.normalized_text)))
    report["sanitizer"] = {
        "localisation_top_segment_contains_injection": round(loc_hits / max(1, loc_n), 4),
        "rescan_clean_after_sanitize": round(rescan_clean / max(1, removed_n), 4),
        "injection_text_removed_strict": round(removed_ok / max(1, removed_n), 4),
        "strict_definition": "<30% of the injection's distinct words survive AND the sanitized text re-scans as ALLOW",
        "clean_docs_text_retained": round(float(np.mean(kept_ratio)), 4),
        "n_detected_injected_docs": loc_n,
    }
    report["latency_ms"] = {"mean": round(statistics.mean(lat), 2), "p50": round(float(np.percentile(lat, 50)), 2),
                            "p95": round(float(np.percentile(lat, 95)), 2), "n_docs": len(lat),
                            "hardware": "2 vCPU cloud container, single thread, measured locally"}

    deb = ROOT / "reports" / "baseline_deberta.json"
    if deb.exists():
        report["protectai_deberta"] = json.loads(deb.read_text())

    out = ROOT / "reports" / "eval_results.json"
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("sanitizer", "latency_ms")}, indent=1))
    print(json.dumps(report["breakdowns"], indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
