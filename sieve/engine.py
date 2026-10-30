"""Scan pipeline: normalise -> segment -> rules + model -> fuse -> verdict."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

from .config import Settings, get_settings
from .model import SieveModel, load_default_model
from .normalize import Finding, NormalizedText, normalize
from .rules import RuleHit, rule_vector, run_rules
from .segment import segment

ALLOW, REVIEW, BLOCK = "ALLOW", "REVIEW", "BLOCK"
_ORDER = {ALLOW: 0, REVIEW: 1, BLOCK: 2}


class InputError(ValueError):
    """Raised for input that cannot be scanned safely (empty, wrong type, too large)."""


@dataclass
class SegmentResult:
    index: int
    text: str
    start: int
    end: int
    prob: float
    risk: float               # 0–100 risk index (monotone rescaling of prob, see risk_index)
    verdict: str
    ml_prob: float
    ml_logit: float
    fusion_terms: dict[str, float]
    rule_hits: list[RuleHit]
    hidden: bool              # segment originates from hidden content (HTML comment, CSS-hidden, tag chars …)


@dataclass
class ScanResult:
    verdict: str
    risk: float
    max_prob: float
    normalized_text: str
    segments: list[SegmentResult]
    findings: list[Finding]
    latency_ms: float
    source: str = "untrusted"
    model_version: str = ""
    thresholds: dict = field(default_factory=dict)

    @property
    def flagged(self) -> list[SegmentResult]:
        return [s for s in self.segments if s.verdict != ALLOW]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["flagged_count"] = len(self.flagged)
        return d


def risk_index(prob: float, review: float, block: float) -> float:
    """Piecewise-linear, monotone map of calibrated probability to 0–100.

    0..review -> 0..40, review..block -> 40..70, block..1 -> 70..100. The two anchor
    points are the calibrated thresholds, so the number is directly interpretable.
    """
    if prob <= review:
        return 40.0 * prob / max(review, 1e-12)
    if prob <= block:
        return 40.0 + 30.0 * (prob - review) / max(block - review, 1e-12)
    return 70.0 + 30.0 * (prob - block) / max(1.0 - block, 1e-12)


class Scanner:
    def __init__(self, model: SieveModel | None = None, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.model = model or load_default_model(self.settings.model_path)
        th = self.model.thresholds
        self.review_t = self.settings.review_threshold or th["review"]
        self.block_t = self.settings.block_threshold or th["block"]

    def _verdict(self, prob: float) -> str:
        if prob >= self.block_t:
            return BLOCK
        if prob >= self.review_t:
            return REVIEW
        return ALLOW

    def scan(self, text: str, source: str = "untrusted", *, normalize_input: bool = True) -> ScanResult:
        if not isinstance(text, str):
            raise InputError("Input must be text.")
        if not text.strip():
            raise InputError("Input is empty.")
        if len(text) > self.settings.max_chars:
            raise InputError(f"Input is {len(text):,} characters; the limit is {self.settings.max_chars:,}.")

        t0 = time.perf_counter()
        norm = normalize(text) if normalize_input else NormalizedText(text, text, [])
        hidden_snips = [f.excerpt.strip()[:60] for f in norm.findings
                        if f.kind in {"html_comment", "hidden_css", "tag_chars", "base64"} and f.excerpt.strip()]
        results: list[SegmentResult] = []
        for seg in segment(norm.text):
            hits = run_rules(seg.text)
            sc = self.model.score(seg.text, rule_vector(seg.text, hits))
            hidden = any(h and (h in seg.text or seg.text in h) for h in hidden_snips)
            verdict = self._verdict(sc.prob)
            # Escalation: instruction-like text that was hidden from human readers is blocked.
            if hidden and verdict == REVIEW:
                verdict = BLOCK
            results.append(SegmentResult(
                seg.index, seg.text, seg.start, seg.end, round(sc.prob, 6),
                round(risk_index(sc.prob, self.review_t, self.block_t), 1), verdict,
                round(sc.ml_prob, 6), round(sc.ml_logit, 4), {k: round(v, 4) for k, v in sc.fusion_terms.items()}, hits, hidden))

        if results:
            top = max(results, key=lambda r: (_ORDER[r.verdict], r.prob))
            verdict, max_prob = top.verdict, top.prob
            risk = max(r.risk for r in results)
        else:
            verdict, max_prob, risk = ALLOW, 0.0, 0.0
        return ScanResult(verdict, risk, max_prob, norm.text, results, norm.findings,
                          round((time.perf_counter() - t0) * 1000, 2), source, self.model.version,
                          {"review": self.review_t, "block": self.block_t})
