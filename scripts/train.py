"""Train the segment classifier and the fusion layer; export a pickle-free JSON model.

    python scripts/build_dataset.py   # once
    python scripts/train.py

Training uses data/train_segments.jsonl only. The fusion weights, the
regularisation strength C and the decision thresholds are chosen on
data/calib_segments.jsonl. No test file is read here.
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sieve.model import CHAR_PARAMS, WORD_PARAMS, SieveModel  # noqa: E402
from sieve.normalize import normalize  # noqa: E402
from sieve.rules import RULE_NAMES, rule_vector  # noqa: E402

SEED = 13


def load(name, with_docs=False):
    rows = [json.loads(line) for line in open(ROOT / "data" / name, encoding="utf-8")]
    out = ([normalize(r["text"]).text for r in rows], np.array([r["label"] for r in rows]))
    return out + ([r["doc"] for r in rows],) if with_docs else out


def threshold_at_fpr(scores_neg: np.ndarray, fpr: float) -> float:
    return float(np.quantile(scores_neg, 1 - fpr))


def main():
    t0 = time.time()
    Xtr_txt, ytr = load("train_segments.jsonl")
    Xca_txt, yca, docs = load("calib_segments.jsonl", with_docs=True)
    print(f"train {len(ytr)} (pos {ytr.sum()})  calib {len(yca)} (pos {yca.sum()})")

    wv = TfidfVectorizer(**WORD_PARAMS, sublinear_tf=True, min_df=2, max_features=25000)
    cv = TfidfVectorizer(**CHAR_PARAMS, sublinear_tf=True, min_df=3, max_features=60000)
    Xtr = hstack([wv.fit_transform(Xtr_txt), cv.fit_transform(Xtr_txt)]).tocsr()
    Xca = hstack([wv.transform(Xca_txt), cv.transform(Xca_txt)]).tocsr()

    best = None
    for C in (0.5, 1.0, 2.0, 4.0, 8.0):
        clf = LogisticRegression(C=C, class_weight="balanced", max_iter=4000, random_state=SEED)
        clf.fit(Xtr, ytr)
        f1 = f1_score(yca, clf.predict(Xca))
        print(f"  C={C:<4} calib F1={f1:.4f}")
        if best is None or f1 > best[0]:
            best = (f1, C, clf)
    _, C, clf = best
    print(f"selected C={C}")

    # Fusion layer on calibration split: inputs = [ml_logit, rule indicators...]
    ml_ca = clf.decision_function(Xca)
    R_ca = np.array([rule_vector(t) for t in Xca_txt])
    F = np.column_stack([ml_ca, R_ca])
    fusion = LogisticRegression(C=1.0, max_iter=2000, random_state=SEED).fit(F, yca)

    nw = len(wv.vocabulary_)
    coef = clf.coef_[0]
    w_terms = [None] * nw
    for t, i in wv.vocabulary_.items():
        w_terms[i] = t
    c_terms = [None] * len(cv.vocabulary_)
    for t, i in cv.vocabulary_.items():
        c_terms[i] = t

    spec = {
        "version": "1.0.0",
        "word": {"vocab": w_terms, "idf": wv.idf_.round(6).tolist(), "coef": coef[:nw].round(6).tolist()},
        "char": {"vocab": c_terms, "idf": cv.idf_.round(6).tolist(), "coef": coef[nw:].round(6).tolist()},
        "intercept": float(clf.intercept_[0]),
        "fusion": {"inputs": ["ml_logit"] + RULE_NAMES, "coef": fusion.coef_[0].round(6).tolist(),
                   "intercept": float(fusion.intercept_[0])},
        "thresholds": {},
        "metadata": {
            "trained_at": time.strftime("%Y-%m-%d"), "C": C, "train_segments": int(len(ytr)),
            "calib_segments": int(len(yca)), "word_features": nw, "char_features": len(c_terms),
            "sources": ["deepset/prompt-injections (Apache-2.0)", "rajpurkar/squad (CC BY-SA 4.0)",
                        "databricks/databricks-dolly-15k (CC BY-SA 3.0)", "Sieve injection templates (MIT)"],
        },
    }

    # thresholds from the *exported* model so they match inference exactly
    m = SieveModel(spec)
    probs = np.array([m.score(t, rule_vector(t)).prob for t in Xca_txt])
    # Decisions are made per *document* (flag if any segment crosses the threshold), so thresholds
    # are calibrated on the per-document maximum over clean calibration documents.
    doc_max, doc_lab = {}, {}
    for p, y, d in zip(probs, yca, docs):
        doc_max[d] = max(doc_max.get(d, 0.0), float(p))
        doc_lab[d] = max(doc_lab.get(d, 0), int(y))
    neg = np.array([doc_max[d] for d in doc_max if doc_lab[d] == 0])
    pos = np.array([doc_max[d] for d in doc_max if doc_lab[d] == 1])
    spec["thresholds"] = {"review": round(threshold_at_fpr(neg, 0.02), 6), "block": round(threshold_at_fpr(neg, 0.005), 6)}
    spec["metadata"]["threshold_policy"] = ("Document-level calibration on held-out calibration documents: "
                                            "review = 2% clean-document FPR, block = 0.5% clean-document FPR")
    spec["metadata"]["calib_docs"] = {"clean": int(len(neg)), "injected": int(len(pos))}
    print("thresholds", spec["thresholds"], " calib doc recall review/block",
          round(float((pos >= spec["thresholds"]["review"]).mean()), 4), round(float((pos >= spec["thresholds"]["block"]).mean()), 4))
    print("fusion weights:", dict(zip(spec["fusion"]["inputs"], spec["fusion"]["coef"])))

    out = ROOT / "models" / "sieve_model.json.gz"
    out.parent.mkdir(exist_ok=True)
    with gzip.open(out, "wt", encoding="utf-8") as f:
        json.dump(spec, f, separators=(",", ":"))
    print(f"wrote {out} ({out.stat().st_size/1e6:.2f} MB) in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
