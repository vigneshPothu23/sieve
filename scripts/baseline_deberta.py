"""External baseline: ProtectAI deberta-v3-base-prompt-injection-v2 (Apache-2.0).

Run locally only (≈740 MB ONNX weights via onnxruntime; not part of the
deployed app). Documents are classified whole, truncated to 512 tokens, which
is how the model card recommends using it. Writes reports/baseline_deberta.json.

    pip install onnxruntime tokenizers huggingface_hub
    python scripts/baseline_deberta.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate import metrics  # noqa: E402

MODEL = "protectai/deberta-v3-base-prompt-injection-v2"


def main():
    import onnxruntime as ort
    from huggingface_hub import hf_hub_download
    from tokenizers import Tokenizer

    onnx_path = hf_hub_download(MODEL, "onnx/model.onnx")
    tok = Tokenizer.from_file(hf_hub_download(MODEL, "onnx/tokenizer.json"))
    tok.enable_truncation(512)
    cfg = json.load(open(hf_hub_download(MODEL, "onnx/config.json")))
    inj_idx = int({v: k for k, v in cfg["id2label"].items()}["INJECTION"])
    so = ort.SessionOptions(); so.intra_op_num_threads = 2
    sess = ort.InferenceSession(onnx_path, so, providers=["CPUExecutionProvider"])
    names = {i.name for i in sess.get_inputs()}

    def clf(text):
        enc = tok.encode(text)
        feed = {"input_ids": np.array([enc.ids], dtype=np.int64), "attention_mask": np.array([enc.attention_mask], dtype=np.int64)}
        if "token_type_ids" in names:
            feed["token_type_ids"] = np.zeros_like(feed["input_ids"])
        logits = sess.run(None, {k: v for k, v in feed.items() if k in names})[0][0]
        return [{"label": "INJECTION" if int(np.argmax(logits)) == inj_idx else "SAFE"}]

    out = {"model": MODEL, "license": "Apache-2.0", "note": "whole-document classification, truncated to 512 tokens; label INJECTION = flagged",
           "sets": {}, "breakdowns": {}}
    lat = []
    for name in ("indirect", "obfuscated", "benign_ood", "deepset"):
        fn = f"test_{name}.jsonl"
        rows = [json.loads(line) for line in open(ROOT / "data" / fn, encoding="utf-8")]
        preds = []
        for r in rows:
            t0 = time.perf_counter()
            res = clf(r["text"])[0]
            lat.append((time.perf_counter() - t0) * 1000)
            preds.append(res["label"] == "INJECTION")
        key = "deepset_external" if name == "deepset" else name
        out["sets"][key] = metrics([r["label"] for r in rows], preds)
        for field in ("subset", "position", "obfuscation"):
            vals = sorted({str(r.get(field)) for r in rows if r["label"] == 1 and r.get(field) is not None})
            for v in vals:
                idx = [i for i, r in enumerate(rows) if r["label"] == 1 and str(r.get(field)) == v]
                if idx:
                    out["breakdowns"][f"{key}:{field}={v}"] = round(float(np.mean([preds[i] for i in idx])), 4)
        if name == "benign_ood":
            for v in ("dolly_benign", "hard_negative"):
                idx = [i for i, r in enumerate(rows) if r["subset"] == v]
                out["breakdowns"][f"benign_fpr:{v}"] = round(float(np.mean([preds[i] for i in idx])), 4)
        print(name, out["sets"][key], flush=True)
    out["latency_ms"] = {"mean": round(float(np.mean(lat)), 1), "p95": round(float(np.percentile(lat, 95)), 1),
                         "hardware": "2 vCPU cloud container, CPU only, measured locally"}
    (ROOT / "reports" / "baseline_deberta.json").write_text(json.dumps(out, indent=2))
    print("done", out["latency_ms"])


if __name__ == "__main__":
    main()
