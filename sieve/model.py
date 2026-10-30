"""Lightweight, exactly-explainable segment classifier.

Two TF-IDF blocks (word 1–2-grams, character 3–5-grams within word boundaries)
feed an L2-regularised logistic regression, followed by a small *fusion*
logistic regression over [ML logit, rule-family indicators].

The trained model is exported to plain JSON (no pickle), so loading the model
never executes code, and inference needs only scikit-learn's analyzers + numpy.
Because every stage is linear, per-feature contributions are exact: the
explanation shown in the UI is the actual arithmetic behind the score.
"""
from __future__ import annotations

import gzip
import json
import math
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .rules import RULE_NAMES, RULES

WORD_PARAMS = dict(analyzer="word", ngram_range=(1, 2), lowercase=True, token_pattern=r"(?u)\b\w+\b|[<>\[\]|#!:]+")
CHAR_PARAMS = dict(analyzer="char_wb", ngram_range=(3, 5), lowercase=True)


@dataclass
class Contribution:
    feature: str
    weight: float      # contribution to the ML logit
    block: str         # "word" | "char"


@dataclass
class SegmentScore:
    ml_logit: float
    ml_prob: float
    fused_logit: float
    prob: float
    fusion_terms: dict[str, float]   # contribution of each fusion input to the fused logit


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-50.0, min(50.0, x))))


class _Block:
    def __init__(self, name: str, params: dict, vocab: list[str], idf: list[float], coef: list[float]):
        self.name = name
        self.analyzer = TfidfVectorizer(**params).build_analyzer()
        self.vocab = {t: i for i, t in enumerate(vocab)}
        self.terms = vocab
        self.idf = np.asarray(idf, dtype=np.float64)
        self.coef = np.asarray(coef, dtype=np.float64)

    def vector(self, text: str) -> dict[int, float]:
        counts = Counter(t for t in self.analyzer(text) if t in self.vocab)
        if not counts:
            return {}
        vals = {self.vocab[t]: (1.0 + math.log(c)) * self.idf[self.vocab[t]] for t, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vals.values())) or 1.0
        return {i: v / norm for i, v in vals.items()}

    def logit_part(self, vec: dict[int, float]) -> float:
        return float(sum(v * self.coef[i] for i, v in vec.items()))


class SieveModel:
    """Loads the exported JSON model and scores text segments."""

    def __init__(self, spec: dict):
        self.spec = spec
        self.version = spec.get("version", "unknown")
        self.blocks = [
            _Block("word", WORD_PARAMS, spec["word"]["vocab"], spec["word"]["idf"], spec["word"]["coef"]),
            _Block("char", CHAR_PARAMS, spec["char"]["vocab"], spec["char"]["idf"], spec["char"]["coef"]),
        ]
        self.intercept = float(spec["intercept"])
        f = spec["fusion"]
        self.fusion_names: list[str] = f["inputs"]
        self.fusion_coef = np.asarray(f["coef"], dtype=np.float64)
        self.fusion_intercept = float(f["intercept"])
        self.thresholds: dict[str, float] = spec["thresholds"]
        self.metadata: dict = spec.get("metadata", {})

    # -- loading -----------------------------------------------------------------------
    @classmethod
    def load(cls, path: str | Path) -> "SieveModel":
        path = Path(path)
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as f:
            spec = json.load(f)
        for key in ("word", "char", "intercept", "fusion", "thresholds"):
            if key not in spec:
                raise ValueError(f"model file is missing '{key}'")
        return cls(spec)

    # -- inference ---------------------------------------------------------------------
    def ml_logit(self, text: str) -> float:
        return self.intercept + sum(b.logit_part(b.vector(text)) for b in self.blocks)

    def score(self, text: str, rule_vec: list[float]) -> SegmentScore:
        ml = self.ml_logit(text)
        inputs = [ml] + list(rule_vec)
        terms = {name: float(c * x) for name, c, x in zip(self.fusion_names, self.fusion_coef, inputs)}
        fused = self.fusion_intercept + sum(terms.values())
        return SegmentScore(ml, _sigmoid(ml), fused, _sigmoid(fused), terms)

    def explain(self, text: str, k: int = 8) -> list[Contribution]:
        """Top-k n-grams by absolute contribution to the ML logit (exact)."""
        contribs: list[Contribution] = []
        for b in self.blocks:
            for i, v in b.vector(text).items():
                w = v * b.coef[i]
                if abs(w) > 1e-6:
                    contribs.append(Contribution(b.terms[i], float(w), b.name))
        # merge char n-grams into readable groups is lossy; we show raw features, strongest first
        contribs.sort(key=lambda c: -abs(c.weight))
        return contribs[:k]

    @staticmethod
    def fusion_label(name: str) -> str:
        if name == "ml_logit":
            return "Learned text model"
        return RULES.get(name, {}).get("label", name)

    @property
    def n_features(self) -> int:
        return sum(len(b.terms) for b in self.blocks)


DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "sieve_model.json.gz"


@lru_cache(maxsize=2)
def load_default_model(path: str | None = None) -> SieveModel:
    return SieveModel.load(path or DEFAULT_MODEL_PATH)


__all__ = ["SieveModel", "SegmentScore", "Contribution", "load_default_model", "DEFAULT_MODEL_PATH",
           "WORD_PARAMS", "CHAR_PARAMS", "RULE_NAMES"]
