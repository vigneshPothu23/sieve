"""Runtime configuration from environment variables (or Streamlit secrets, mirrored into env).

All settings are optional; defaults are safe. No secret is required to run Sieve.

SIEVE_MAX_CHARS          maximum characters per scan (default 50 000)
SIEVE_REVIEW_THRESHOLD   override the calibrated review threshold (probability, 0–1)
SIEVE_BLOCK_THRESHOLD    override the calibrated block threshold (probability, 0–1)
SIEVE_EGRESS_ALLOWLIST   comma-separated domains the agent may contact (default: example-corp.com)
SIEVE_MODEL_PATH         alternative model JSON(.gz) file
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _float(name: str) -> float | None:
    v = os.environ.get(name, "").strip()
    if not v:
        return None
    x = float(v)
    if not 0.0 < x < 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    return x


@dataclass(frozen=True)
class Settings:
    max_chars: int = 50_000
    review_threshold: float | None = None
    block_threshold: float | None = None
    egress_allowlist: tuple[str, ...] = field(default_factory=lambda: ("example-corp.com",))
    model_path: str | None = None


def get_settings() -> Settings:
    allow = os.environ.get("SIEVE_EGRESS_ALLOWLIST", "example-corp.com")
    return Settings(
        max_chars=int(os.environ.get("SIEVE_MAX_CHARS", "50000")),
        review_threshold=_float("SIEVE_REVIEW_THRESHOLD"),
        block_threshold=_float("SIEVE_BLOCK_THRESHOLD"),
        egress_allowlist=tuple(d.strip().lower() for d in allow.split(",") if d.strip()),
        model_path=os.environ.get("SIEVE_MODEL_PATH") or None,
    )
