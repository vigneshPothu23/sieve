"""Tool-call policy gate for LLM agents that read untrusted content.

Detection alone only *warns*. The gate *enforces*: a tool function registered
with :class:`GuardedExecutor` is invoked only when the policy returns ALLOW
(or CONFIRM plus an explicit human confirmation). The policy combines:

  P1  Session taint lock      — after a BLOCK-level injection is ingested, egress,
                                destructive and financial tools are locked for the session.
  P2  Argument provenance     — an argument value (URL, domain, e-mail, path, command)
                                that appears in flagged untrusted content is denied: the
                                attacker chose it.
  P3  Egress allowlist        — network/e-mail destinations outside the allowlist need
                                confirmation, and are denied once the session is tainted.
  P4  Dangerous commands      — shell payloads such as `rm -rf`, `curl … | sh` are denied.
  P5  Human-in-the-loop       — destructive and financial actions always need confirmation.

The design follows the "least privilege after untrusted input" idea discussed in
work on agent security (e.g. taint tracking / capability control); it is a
practical policy layer, not a formal guarantee.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urlparse

from .engine import ALLOW as V_ALLOW, BLOCK as V_BLOCK, REVIEW as V_REVIEW, ScanResult

ALLOW, DENY, CONFIRM = "ALLOW", "DENY", "CONFIRM"
RISK_LEVELS = ("read", "write", "egress", "destructive", "financial")
LOCKED_WHEN_TAINTED = ("egress", "destructive", "financial")
_V_ORDER = {V_ALLOW: 0, V_REVIEW: 1, V_BLOCK: 2}

_URL = re.compile(r"https?://[^\s)\"'<>\]]+", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PATH = re.compile(r"(?:~|\.{0,2})/[\w./-]+|\b[\w-]+\.(?:json|env|pem|key|txt|csv|db|sqlite|ya?ml)\b|\bid_(?:rsa|ed25519)\b")
_DANGEROUS_CMD = re.compile(r"\brm\s+-[a-z]*r[a-z]*f|\bcurl\b[^|]*\|\s*(?:ba|z)?sh\b|\bwget\b[^;&|]*(?:;|&&|\|)|\bmkfs\b|\bdd\s+if=|"
                            r":\(\)\s*\{|\bchmod\s+777\b|\bpowershell\b.*-enc", re.I)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    risk: str
    description: str = ""
    egress_args: tuple[str, ...] = ()     # args holding URLs / e-mail addresses
    command_args: tuple[str, ...] = ()    # args holding shell commands

    def __post_init__(self):
        if self.risk not in RISK_LEVELS:
            raise ValueError(f"unknown risk level {self.risk!r}")


@dataclass
class ToolCall:
    tool: str
    args: dict[str, Any]
    origin: str = "agent"


@dataclass
class Decision:
    action: str
    reasons: list[str]
    rule_ids: list[str]


@dataclass
class ExecutionRecord:
    call: ToolCall
    decision: Decision
    executed: bool
    output: Any = None
    error: str | None = None


def _domain(value: str) -> str | None:
    value = value.strip()
    if _EMAIL.fullmatch(value):
        return value.split("@", 1)[1].lower()
    if value.lower().startswith(("http://", "https://")):
        return (urlparse(value).hostname or "").lower() or None
    return None


def _indicators(text: str) -> set[str]:
    out: set[str] = set()
    for u in _URL.findall(text):
        u = u.rstrip(".,;:")
        out.add(u.lower())
        d = _domain(u)
        if d:
            out.add(d)
    for e in _EMAIL.findall(text):
        out.add(e.lower())
        out.add(e.split("@", 1)[1].lower())
    for p in _PATH.findall(text):
        if len(p) > 3:
            out.add(p.lower())
    return out


@dataclass
class Session:
    """Tracks the untrusted content an agent has ingested in one task."""
    scans: list[tuple[str, ScanResult]] = field(default_factory=list)
    flagged_indicators: set[str] = field(default_factory=set)

    def ingest(self, source: str, result: ScanResult) -> None:
        self.scans.append((source, result))
        for seg in result.segments:
            if seg.verdict != V_ALLOW:
                self.flagged_indicators |= _indicators(seg.text)

    @property
    def taint(self) -> str:
        if not self.scans:
            return V_ALLOW
        return max((r.verdict for _, r in self.scans), key=lambda v: _V_ORDER[v])


class PolicyEngine:
    def __init__(self, tools: dict[str, ToolSpec], egress_allowlist: tuple[str, ...] = ()):
        self.tools = tools
        self.allow = tuple(d.lower() for d in egress_allowlist)

    def _allowed_domain(self, d: str) -> bool:
        return any(d == a or d.endswith("." + a) for a in self.allow)

    def evaluate(self, call: ToolCall, session: Session) -> Decision:
        spec = self.tools.get(call.tool)
        if spec is None:
            return Decision(DENY, [f"Unknown tool '{call.tool}' — default deny."], ["P0"])
        reasons, rules, action = [], [], ALLOW

        def escalate(a, reason, rid):
            nonlocal action
            reasons.append(reason); rules.append(rid)
            if a == DENY or (a == CONFIRM and action == ALLOW):
                action = a

        taint = session.taint
        if taint == V_BLOCK and spec.risk in LOCKED_WHEN_TAINTED:
            escalate(DENY, "Session ingested content with a likely prompt injection; "
                           f"'{spec.risk}' tools are locked until a human reviews it.", "P1")

        for k, v in call.args.items():
            sv = str(v).lower()
            hit = next((ind for ind in session.flagged_indicators if ind and ind in sv), None)
            if hit:
                escalate(DENY, f"Argument '{k}' contains '{hit}', which came from flagged untrusted content.", "P2")

        for k in spec.egress_args:
            if k in call.args:
                d = _domain(str(call.args[k]))
                if d is None:
                    escalate(DENY, f"Argument '{k}' is not a valid URL or e-mail address.", "P3")
                elif not self._allowed_domain(d):
                    if taint != V_ALLOW:
                        escalate(DENY, f"Destination '{d}' is outside the egress allowlist and the session is tainted.", "P3")
                    else:
                        escalate(CONFIRM, f"Destination '{d}' is outside the egress allowlist.", "P3")

        for k in spec.command_args:
            if k in call.args and _DANGEROUS_CMD.search(str(call.args[k])):
                escalate(DENY, f"Command in '{k}' matches a dangerous pattern.", "P4")

        if spec.risk in ("destructive", "financial"):
            escalate(CONFIRM, f"'{spec.risk}' actions always require human confirmation.", "P5")

        if not reasons:
            reasons.append("No policy objection.")
        return Decision(action, reasons, rules)


class GuardedExecutor:
    """The only path through which tools run. Denied calls never reach the tool function."""

    def __init__(self, policy: PolicyEngine):
        self.policy = policy
        self._fns: dict[str, Callable[..., Any]] = {}
        self.log: list[ExecutionRecord] = []

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        if name not in self.policy.tools:
            raise KeyError(f"tool {name!r} has no ToolSpec")
        self._fns[name] = fn

    def execute(self, call: ToolCall, session: Session, *, confirmed: bool = False) -> ExecutionRecord:
        decision = self.policy.evaluate(call, session)
        run = decision.action == ALLOW or (decision.action == CONFIRM and confirmed)
        rec = ExecutionRecord(call, decision, executed=False)
        if run:
            fn = self._fns.get(call.tool)
            if fn is None:
                rec.error = "tool not registered"
            else:
                try:
                    rec.output = fn(**call.args)
                    rec.executed = True
                except Exception as exc:  # tool failures are recorded, never propagated into the agent loop
                    rec.error = f"{type(exc).__name__}: {exc}"
        self.log.append(rec)
        return rec
