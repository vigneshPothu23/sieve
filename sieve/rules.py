"""Interpretable signature rules.

Each rule maps to an attack *tactic* and returns the matched span as evidence.
Rules are features for the fusion model, not verdicts by themselves: their
weights are learned on a calibration split (see scripts/train.py).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_I = re.I

AI = r"(?:ai|a\.i\.|assistant|language model|llm|chat ?bot|gpt|claude|gemini|copilot|agent|model)"

RULES: dict[str, dict] = {
    "override": {
        "label": "Instruction override",
        "desc": "Tries to cancel or replace the instructions the model was given.",
        "patterns": [
            r"\b(?:ignore|disregard|forget|override|bypass|skip|drop|abandon)\b[^.\n]{0,40}\b(?:previous|prior|above|earlier|preceding|original|all|any|your|the system|existing)\b[^.\n]{0,30}\b(?:instructions?|rules?|directions?|prompts?|guidelines?|constraints?|context|tasks?|orders?)\b",
            r"\b(?:new|updated|revised|real|actual|true)\s+(?:instructions?|task|objective|directive|orders?)\s*[:\-]",
            r"\bfrom now on\b[^.\n]{0,40}\b(?:you|your)\b",
            r"\binstead,?\s+(?:you (?:must|should|will)|do the following|respond)",
            r"\b(?:vergiss|ignoriere|vergessen sie)\b[^.\n]{0,40}\b(?:alles|anweisungen|vorherigen|oben)\b",
            r"\b(?:olvida|ignora)\b[^.\n]{0,30}\b(?:instrucciones|anteriores|todo)\b",
        ],
    },
    "role_spoof": {
        "label": "Role / system spoofing",
        "desc": "Impersonates a system, developer or assistant turn inside data.",
        "patterns": [
            r"(?:^|\n)\s*[\[<(#*]*\s*(?:system|developer|admin(?:istrator)?|root|assistant|operator)\s*(?:message|prompt|note|override|instruction)?\s*[\]>)*:?\s*[\]>:]",
            r"[\[<]\s*(?:system|developer|admin|assistant|sys)\s*[\]>]\s*:?",
            r"<\|?(?:im_start|im_end|system|endoftext|start_header_id)\|?>",
            r"###\s*(?:instruction|system|response)\b",
            r"\byou are (?:now|no longer)\b",
            r"\b(?:developer|debug|god|admin|jailbreak|dan) mode\b",
            r"\bact as (?:an?|the) (?:unrestricted|unfiltered|different)\b",
        ],
    },
    "addresses_ai": {
        "label": "Addresses the AI reader",
        "desc": "Speaks directly to an AI processing the content, which normal documents rarely do.",
        "patterns": [
            rf"\b(?:dear|attention|note to|hey|hello)\s+(?:the\s+)?{AI}\b",
            rf"\bif you are an? {AI}\b",
            rf"\b(?:any|the) {AI}s?\s+(?:reading|processing|summari[sz]ing|analy[sz]ing|parsing|browsing)\b",
            rf"\b{AI}s?\s+(?:reading|processing|summari[sz]ing)\s+this\b",
            r"\bwhen (?:you )?(?:summari[sz]e|process|read|answer)\b[^.\n]{0,40}\b(?:this|the) (?:page|document|email|text|content)\b[^.\n]{0,30}\b(?:you must|always|make sure|be sure)\b",
        ],
    },
    "exfiltration": {
        "label": "Data exfiltration",
        "desc": "Asks to send data out or embeds a URL that would leak data when rendered.",
        "patterns": [
            r"!\[[^\]]*\]\(\s*https?://[^)\s]+[?&][^)\s]*=",
            r"\b(?:send|forward|email|e-mail|post|upload|transmit|leak|exfiltrate|copy|submit|share)\b[^.\n]{0,60}\b(?:to|at|into)\b[^.\n]{0,15}(?:[\w.+-]+@[\w-]+\.[\w.]+|https?://\S+)",
            r"\b(?:append|include|encode|attach|embed|insert)\b[^.\n]{0,50}\b(?:conversation|chat history|api[ _-]?keys?|passwords?|credentials?|tokens?|secrets?|personal data|user data|session|cookies?)\b",
            r"https?://\S+[?&](?:q|data|d|c|leak|info|payload|msg|text|secret)=\{?[^\s)]*",
        ],
    },
    "prompt_leak": {
        "label": "System-prompt extraction",
        "desc": "Tries to make the model reveal its hidden instructions.",
        "patterns": [
            r"\b(?:reveal|print|show|output|repeat|display|tell me|leak|dump|recite|disclose)\b[^.\n]{0,30}\b(?:your|the)\s+(?:system prompt|initial (?:prompt|instructions)|hidden (?:prompt|instructions)|original instructions|instructions above|prompt above|configuration)\b",
            r"\bwhat (?:is|are|were) your (?:system prompt|instructions|initial instructions)\b",
        ],
    },
    "tool_coercion": {
        "label": "Tool / action coercion",
        "desc": "Directs an agent to perform an action (call a tool, run code, delete, pay).",
        "patterns": [
            r"\b(?:call|invoke|use|trigger|execute|run)\b[^.\n]{0,20}\b(?:the\s+)?(?:\w+_\w+|tool|function|plugin|api|command|shell|terminal|script)\b[^.\n]{0,40}\b(?:with|to|on|and)\b",
            r"\brm\s+-rf\b|\bcurl\s+[^|\n]+\|\s*(?:ba)?sh\b|\bwget\s+\S+\s*(?:&&|;)|\bpowershell\s+-(?:enc|e)\b",
            r"\b(?:delete|remove|wipe|erase|drop)\b[^.\n]{0,30}\b(?:all|every|the)\b[^.\n]{0,20}\b(?:files?|emails?|records?|database|tables?|repositor(?:y|ies)|backups?)\b",
            r"\b(?:transfer|wire|pay|send)\b[^.\n]{0,25}(?:\$|€|£|usd|eur|btc|bitcoin|funds|money|payment)",
            r"\b(?:visit|open|navigate to|click|browse to|go to)\s+(?:this\s+)?(?:link|url|page|site)?\s*:?\s*https?://",
        ],
    },
    "concealment": {
        "label": "Concealment from user",
        "desc": "Asks the model to hide its behaviour from the human user.",
        "patterns": [
            r"\b(?:do not|don't|never|must not)\s+(?:tell|inform|mention|reveal|disclose|notify|alert|show)\b[^.\n]{0,25}\b(?:the user|anyone|them|this)\b",
            r"\bwithout (?:telling|informing|notifying|alerting|asking) (?:the user|anyone|them)\b",
            r"\b(?:secretly|silently|covertly|quietly)\s+(?:send|add|include|append|call|run|forward|insert|change)\b",
            r"\bthe user (?:must|should) not (?:know|see|find out)\b",
        ],
    },
    "output_hijack": {
        "label": "Output manipulation",
        "desc": "Dictates exact output, injected links or promotional content.",
        "patterns": [
            r"\b(?:respond|reply|answer|output|say|print|write)\s+(?:only|exactly|just)?\s*(?:with\s+)?(?:the\s+(?:word|phrase|text)\s+)?[\"“'][^\"”']{2,80}[\"”']",
            r"\b(?:always|must)\s+(?:recommend|mention|include|promote|say)\b",
            r"\b(?:in your (?:response|answer|summary|reply))\b[^.\n]{0,40}\b(?:include|add|mention|say|recommend|insert|tell)\b",
            r"\b(?:tell|inform|warn|instruct|ask)\s+the user\s+(?:to|that)\b",
        ],
    },
}

_COMPILED = {k: [re.compile(p, _I | re.M) for p in v["patterns"]] for k, v in RULES.items()}
RULE_NAMES: list[str] = list(RULES.keys())


@dataclass(frozen=True)
class RuleHit:
    rule: str
    label: str
    start: int
    end: int
    match: str


def run_rules(text: str) -> list[RuleHit]:
    hits: list[RuleHit] = []
    for name, pats in _COMPILED.items():
        for p in pats:
            for m in p.finditer(text):
                if m.end() > m.start():
                    hits.append(RuleHit(name, RULES[name]["label"], m.start(), m.end(), m.group(0).strip()[:160]))
    return sorted(hits, key=lambda h: h.start)


def rule_vector(text: str, hits: list[RuleHit] | None = None) -> list[float]:
    """Binary indicator per rule family, in RULE_NAMES order."""
    hits = run_rules(text) if hits is None else hits
    present = {h.rule for h in hits}
    return [1.0 if r in present else 0.0 for r in RULE_NAMES]
