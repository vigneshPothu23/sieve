"""Build the training, calibration and test sets (deterministic, seed=13).

Sources (downloaded from the Hugging Face Hub; not redistributed in this repo):
  * deepset/prompt-injections           Apache-2.0
  * rajpurkar/squad                     CC BY-SA 4.0
  * databricks/databricks-dolly-15k     CC BY-SA 3.0

Split discipline (no train/test leakage):
  * SQuAD *train* contexts  -> train / calib documents (split by article title)
  * SQuAD *validation*      -> test documents
  * Dolly responses         -> 70/15/15 by record index
  * deepset train           -> train / calib ; deepset test -> external test (deduplicated against train)
  * Injection templates & entities: TRAIN_* pools for train/calib, disjoint TEST_* pools for test

Usage:  python scripts/build_dataset.py
"""
from __future__ import annotations

import base64
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from datasets import load_dataset  # noqa: E402

import attack_templates as T  # noqa: E402
from sieve.segment import segment  # noqa: E402

SEED = 13
DATA = ROOT / "data"
rng = random.Random(SEED)


def fill(template: str, ents: dict) -> str:
    out = template
    for k, vals in ents.items():
        while "{" + k + "}" in out:
            out = out.replace("{" + k + "}", rng.choice(vals), 1)
    return out.replace("{{", "{").replace("}}", "}")


def make_injection(payloads, wrappers, ents) -> str:
    p = fill(rng.choice(payloads), ents)
    w = rng.choice(wrappers)
    if rng.random() < 0.15:  # light surface variation
        p = p.upper() if rng.random() < 0.3 else p
    return w.replace("{P}", p[:1].upper() + p[1:]).replace("{p}", p)


def sentences(text: str) -> list[str]:
    return [s.text for s in segment(text)]


def inject(doc: str, inj: str, position: str) -> tuple[str, int, int]:
    sents = sentences(doc)
    if position == "head" or len(sents) < 2:
        pre = ""
        post = doc
    elif position == "tail":
        pre, post = doc, ""
    else:
        k = len(sents) // 2
        cut = doc.find(sents[k])
        pre, post = doc[:cut].rstrip(), doc[cut:]
    sep_pre = "\n" if pre and rng.random() < 0.4 else (" " if pre else "")
    sep_post = "\n" if post and rng.random() < 0.4 else (" " if post else "")
    text = pre + sep_pre + inj + sep_post + post
    start = len(pre) + len(sep_pre)
    return text, start, start + len(inj)


def label_segments(text: str, spans: list[tuple[int, int]]) -> list[tuple[str, int]]:
    out = []
    for s in segment(text):
        lab = 0
        for a, b in spans:
            ov = max(0, min(s.end, b) - max(s.start, a))
            if ov and (ov >= 0.5 * (s.end - s.start) or ov >= 0.5 * (b - a)):
                lab = 1
        out.append((s.text, lab))
    return out


# --- obfuscation transforms (test only) -------------------------------------------------
_HG = {"a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "i": "і"}


def obf_zero_width(s):
    return re.sub(r"(\w{3,})", lambda m: m.group(1)[:2] + "​" + m.group(1)[2:], s)


def obf_homoglyph(s):
    return "".join(_HG.get(ch, ch) if rng.random() < 0.6 else ch for ch in s)


def obf_html_comment(s):
    return f"<!-- {s} -->"


def obf_hidden_css(s):
    return f'<span style="display:none">{s}</span>'


def obf_base64(s):
    return "Reference data: " + base64.b64encode(s.encode()).decode()


def obf_tag_chars(s):
    return "".join(chr(0xE0000 + ord(c)) for c in s if 0x20 <= ord(c) <= 0x7E)


OBFUSCATIONS = {
    "zero_width": obf_zero_width, "homoglyph": obf_homoglyph, "html_comment": obf_html_comment,
    "hidden_css": obf_hidden_css, "base64": obf_base64, "tag_chars": obf_tag_chars,
}


def write_jsonl(name, rows):
    DATA.mkdir(exist_ok=True)
    with open(DATA / name, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  {name:28s} {len(rows):6d} rows")


def norm_key(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()


def main():
    print("Loading datasets from the Hugging Face Hub ...")
    squad = load_dataset("rajpurkar/squad")
    dolly = load_dataset("databricks/databricks-dolly-15k")["train"]
    deep = load_dataset("deepset/prompt-injections")

    # unique contexts
    def uniq_contexts(split):
        seen, out = set(), []
        for r in split:
            if r["context"] not in seen:
                seen.add(r["context"])
                out.append((r["title"], r["context"]))
        return out

    tr_ctx = uniq_contexts(squad["train"])
    titles = sorted({t for t, _ in tr_ctx})
    rng.shuffle(titles)
    calib_titles = set(titles[: len(titles) // 6])
    train_docs = [c for t, c in tr_ctx if t not in calib_titles]
    calib_docs = [c for t, c in tr_ctx if t in calib_titles]
    test_docs = [c for _, c in uniq_contexts(squad["validation"])]
    rng.shuffle(train_docs); rng.shuffle(calib_docs); rng.shuffle(test_docs)

    # dolly responses with >= 2 sentences, split by index
    dolly_resp = [r["response"] for r in dolly if len(r["response"]) > 80 and r["category"] in
                  {"open_qa", "general_qa", "brainstorming", "creative_writing", "summarization", "information_extraction", "closed_qa", "classification"}]
    rng.shuffle(dolly_resp)
    n = len(dolly_resp)
    d_train, d_calib, d_test = dolly_resp[: int(.7 * n)], dolly_resp[int(.7 * n): int(.85 * n)], dolly_resp[int(.85 * n):]

    deep_tr = [(r["text"], r["label"]) for r in deep["train"]]
    rng.shuffle(deep_tr)
    cut = int(0.8 * len(deep_tr))
    deep_train, deep_calib = deep_tr[:cut], deep_tr[cut:]
    train_keys = {norm_key(t) for t, _ in deep_tr}
    deep_test = [(r["text"], r["label"]) for r in deep["test"] if norm_key(r["text"]) not in train_keys]
    print(f"  deepset test: {len(deep['test'])} -> {len(deep_test)} after removing train duplicates")

    def segment_set(docs, dolly_part, deep_part, n_inj, n_clean, payloads, wrappers, ents, tag):
        rows = []
        for i in range(n_inj):
            inj = make_injection(payloads, wrappers, ents)
            pos = ["head", "middle", "tail"][i % 3]
            text, a, b = inject(docs[i], inj, pos)
            rows += [{"text": t, "label": l, "src": "squad_injected", "doc": f"{tag}-inj-{i}"} for t, l in label_segments(text, [(a, b)])]
        for j, d in enumerate(docs[n_inj: n_inj + n_clean]):
            rows += [{"text": t, "label": 0, "src": "squad_clean", "doc": f"{tag}-sq-{j}"} for t in sentences(d)]
        for j, d in enumerate(dolly_part):
            rows += [{"text": t, "label": 0, "src": "dolly", "doc": f"{tag}-do-{j}"} for t in sentences(d)]
        for j, (t, l) in enumerate(deep_part):
            rows.append({"text": t, "label": int(l), "src": "deepset", "doc": f"{tag}-dp-{j}"})
        return rows

    # Disjoint template halves: the text model trains on half A; calibration (fusion weights +
    # thresholds) sees half B, i.e. phrasings the text model has never seen. This teaches the
    # fusion layer how much to rely on rules when the text model is uncertain.
    pay_a, pay_b = T.TRAIN_PAYLOADS[0::2], T.TRAIN_PAYLOADS[1::2]
    wr_a, wr_b = T.TRAIN_WRAPPERS[0::2], T.TRAIN_WRAPPERS[1::2]
    print("Writing splits:")
    train = segment_set(train_docs, d_train, deep_train, 3500, 3000, pay_a, wr_a, T.TRAIN_ENTITIES, "tr")
    calib = segment_set(calib_docs, d_calib, deep_calib, 900, 1200, pay_b, wr_b, T.TRAIN_ENTITIES, "ca")
    write_jsonl("train_segments.jsonl", train)
    write_jsonl("calib_segments.jsonl", calib)

    # --- document-level test sets (unseen templates + unseen documents) ---------------
    test_rows, k = [], 0
    for i in range(600):
        inj = make_injection(T.TEST_PAYLOADS, T.TEST_WRAPPERS, T.TEST_ENTITIES)
        pos = ["head", "middle", "tail"][i % 3]
        text, a, b = inject(test_docs[k], inj, pos); k += 1
        test_rows.append({"text": text, "label": 1, "subset": "indirect", "position": pos, "span": [a, b], "injection": inj})
    for tmpl in T.TEST_SUBTLE:
        for pos in ("head", "middle", "tail"):
            for _ in range(4):
                inj = fill(tmpl, T.TEST_ENTITIES)
                text, a, b = inject(test_docs[k], inj, pos); k += 1
                test_rows.append({"text": text, "label": 1, "subset": "subtle", "position": pos, "span": [a, b], "injection": inj})
    for _ in range(672):
        test_rows.append({"text": test_docs[k], "label": 0, "subset": "clean", "position": None, "span": None}); k += 1
    write_jsonl("test_indirect.jsonl", test_rows)

    obf_rows = []
    names = list(OBFUSCATIONS)
    for i in range(300):
        kind = names[i % len(names)]
        inj = make_injection(T.TEST_PAYLOADS, T.TEST_WRAPPERS, T.TEST_ENTITIES)
        text, _, _ = inject(test_docs[k], OBFUSCATIONS[kind](inj), ["head", "middle", "tail"][i % 3]); k += 1
        obf_rows.append({"text": text, "label": 1, "subset": "obfuscated", "obfuscation": kind, "injection": inj})
    write_jsonl("test_obfuscated.jsonl", obf_rows)

    ood = [{"text": t, "label": 0, "subset": "dolly_benign"} for t in d_test[:1000]]
    ood += [{"text": t, "label": 0, "subset": "hard_negative"} for t in T.HARD_NEGATIVES]
    write_jsonl("test_benign_ood.jsonl", ood)

    write_jsonl("test_deepset.jsonl", [{"text": t, "label": int(l), "subset": "deepset"} for t, l in deep_test])


if __name__ == "__main__":
    main()
