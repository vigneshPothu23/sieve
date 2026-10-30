"""A deliberately gullible, *simulated* agent and a sandboxed tool world.

There is no LLM here. ``ObedientAgent`` models the worst case: it turns every
action-like directive it finds in its context into a tool call, exactly what a
successful indirect prompt injection achieves against a real agent. The tools
mutate an in-memory ``SandboxWorld`` only — nothing leaves the process.

This makes the policy gate's effect observable and testable end-to-end:
run the same task with and without Sieve and compare the world state.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .engine import Scanner
from .policy import ExecutionRecord, GuardedExecutor, PolicyEngine, Session, ToolCall, ToolSpec
from .sanitize import sanitize

TOOLS: dict[str, ToolSpec] = {
    "search_docs": ToolSpec("search_docs", "read", "Search the knowledge base"),
    "send_email": ToolSpec("send_email", "egress", "Send an e-mail", egress_args=("to",)),
    "http_request": ToolSpec("http_request", "egress", "Fetch or post to a URL", egress_args=("url",)),
    "delete_path": ToolSpec("delete_path", "destructive", "Delete a file or folder"),
    "run_shell": ToolSpec("run_shell", "destructive", "Run a shell command", command_args=("command",)),
    "transfer_funds": ToolSpec("transfer_funds", "financial", "Send a payment"),
    "write_note": ToolSpec("write_note", "write", "Save a note for the user"),
}


@dataclass
class SandboxWorld:
    files: dict[str, str] = field(default_factory=lambda: {
        "~/.ssh/id_rsa": "-----BEGIN OPENSSH PRIVATE KEY----- (sandbox placeholder)",
        "~/.aws/credentials": "[default] aws_access_key_id=SANDBOX",
        ".env": "API_KEY=sandbox-not-real",
        "~/Documents/report.docx": "Q3 report",
    })
    outbox: list[dict] = field(default_factory=list)
    network: list[dict] = field(default_factory=list)
    shell: list[str] = field(default_factory=list)
    payments: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def bind(self, ex: GuardedExecutor) -> None:
        ex.register("search_docs", lambda query: f"(sandbox) results for {query!r}")
        ex.register("send_email", lambda to, body="": self.outbox.append({"to": to, "body": body[:200]}) or "sent")
        ex.register("http_request", lambda url, data="": self.network.append({"url": url, "data": data[:200]}) or "200 OK")
        ex.register("delete_path", lambda path: self.files.pop(path, None) is not None and "deleted" or "not found")
        ex.register("run_shell", lambda command: self.shell.append(command) or "(sandbox) executed")
        ex.register("transfer_funds", lambda to, amount: self.payments.append({"to": to, "amount": amount}) or "paid")
        ex.register("write_note", lambda text: self.notes.append(text) or "saved")

    @property
    def damage(self) -> list[str]:
        out = [f"E-mail sent to {m['to']}" for m in self.outbox]
        out += [f"Network request to {n['url']}" for n in self.network]
        out += [f"Shell command executed: {c}" for c in self.shell]
        out += [f"Payment of {p['amount']} to {p['to']}" for p in self.payments]
        missing = {"~/.ssh/id_rsa", "~/.aws/credentials", ".env", "~/Documents/report.docx"} - set(self.files)
        out += [f"File deleted: {f}" for f in sorted(missing)]
        return out


_EMAIL = r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
_URL = r"https?://[^\s)\"'<>\]]+"
_DIRECTIVES = [
    ("send_email", re.compile(rf"\b(?:send|forward|email|e-mail|mail|copy)\b[^.\n]{{0,80}}?\b(?:to|at)\s+({_EMAIL})", re.I),
     lambda m, ctx: {"to": m.group(1), "body": ctx[:200]}),
    ("http_request", re.compile(rf"\b(?:visit|open|fetch|navigate to|go to|post|upload|submit|append|log in at|renew(?:ing)? at|download[^.\n]{{0,40}}from)\b[^.\n]{{0,60}}?({_URL})", re.I),
     lambda m, ctx: {"url": m.group(1).rstrip(".,;"), "data": "session context"}),
    ("run_shell", re.compile(r"\b(?:run|execute)\b(?:\s+the\s+command)?\s+((?:rm|curl|wget|bash|sh|python|powershell)\b.*?)(?:\s+on the host)?(?=\.\s|\.$|\n|$)", re.I),
     lambda m, ctx: {"command": m.group(1).strip()}),
    ("delete_path", re.compile(r"\b(?:delete|remove|wipe|erase)\b[^.\n]{0,30}?\b(?:files? in|in|folder|file)?\s*((?:~|\.)?/?[\w.~/-]*(?:id_rsa|credentials|\.env|Documents)[\w./-]*)", re.I),
     lambda m, ctx: {"path": m.group(1)}),
    ("transfer_funds", re.compile(r"\b(?:transfer|pay|send|wire)\b\s+((?:\$|€|£)?\s?[\d.,]+\s?(?:btc|usd|eur)?)\b[^.\n]{0,60}?(?:to|at)\s+(?:the\s+)?(?:account|wallet)?[^.\n]{0,30}?(" + _URL + r"|\S+)", re.I),
     lambda m, ctx: {"to": m.group(2).rstrip(".,"), "amount": m.group(1).strip()}),
]


def extract_actions(context: str) -> list[ToolCall]:
    calls: list[ToolCall] = []
    seen = set()
    for tool, pat, build in _DIRECTIVES:
        for m in pat.finditer(context):
            args = build(m, context)
            key = (tool, tuple(sorted((k, str(v)) for k, v in args.items() if k != "body")))
            if key not in seen:
                seen.add(key)
                calls.append(ToolCall(tool, args, origin="document"))
    return calls


@dataclass
class AgentRun:
    protected: bool
    context_seen: str
    proposed: list[ToolCall]
    records: list[ExecutionRecord]
    world: SandboxWorld
    session: Session | None
    user_actions: list[ToolCall]


class ObedientAgent:
    """Worst-case agent: executes the user's task *and* any directive found in documents."""

    def __init__(self, scanner: Scanner | None = None, egress_allowlist: tuple[str, ...] = ("example-corp.com",)):
        self.scanner = scanner or Scanner()
        self.allowlist = egress_allowlist

    def run(self, documents: list[str], user_actions: list[ToolCall] | None = None, *, protected: bool,
            sanitize_context: bool = True, confirm: bool = False) -> AgentRun:
        world = SandboxWorld()
        user_actions = list(user_actions or [])
        if not protected:
            from .policy import ALLOW, Decision
            context = "\n\n".join(documents)
            proposed = user_actions + extract_actions(context)
            fns = GuardedExecutor(PolicyEngine(TOOLS))
            world.bind(fns)
            records = []
            for c in proposed:  # no gate: everything runs
                fn = fns._fns[c.tool]
                try:
                    out = fn(**c.args)
                    records.append(ExecutionRecord(c, Decision(ALLOW, ["Unprotected agent: no policy."], []), True, out))
                except Exception as exc:
                    records.append(ExecutionRecord(c, Decision(ALLOW, ["Unprotected agent: no policy."], []), False, error=str(exc)))
            return AgentRun(False, context, proposed, records, world, None, user_actions)

        session = Session()
        parts = []
        for i, doc in enumerate(documents):
            res = self.scanner.scan(doc, source=f"document {i + 1}")
            session.ingest(f"document {i + 1}", res)
            parts.append(sanitize(res).text if sanitize_context else res.normalized_text)
        context = "\n\n".join(parts)
        proposed = user_actions + extract_actions(context)
        ex = GuardedExecutor(PolicyEngine(TOOLS, self.allowlist))
        world.bind(ex)
        records = [ex.execute(c, session, confirmed=confirm) for c in proposed]
        return AgentRun(True, context, proposed, records, world, session, user_actions)
