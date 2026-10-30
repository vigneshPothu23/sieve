# Architecture

Sieve is a single Python package (`sieve/`) plus a Streamlit front end (`ui/`, `streamlit_app.py`). There is no server-side storage, no external API and no network call at inference time.

```
                     untrusted text (web page, e-mail, file, tool result)
                                         │
 ┌───────────────────────────────────────▼──────────────────────────────────────┐
 │ normalize.py   NFKC · zero-width removal · Unicode-tag decoding · homoglyphs  │
 │                HTML comments & CSS-hidden text surfaced · Base64 decoded      │──► findings
 ├──────────────────────────────────────────────────────────────────────────────┤
 │ segment.py     sentences/lines with exact character offsets                  │
 ├──────────────────────────────────────────────────────────────────────────────┤
 │ rules.py       8 rule families → binary features + evidence spans            │
 │ model.py       TF-IDF word(1-2) + char_wb(3-5) → logistic regression logit   │
 │                fusion LR over [logit, 8 rule features] → probability          │
 ├──────────────────────────────────────────────────────────────────────────────┤
 │ engine.py      per-segment verdict (ALLOW / REVIEW / BLOCK), hidden-text      │
 │                escalation, document verdict = worst segment                   │
 └───────────────┬───────────────────────────────────────┬──────────────────────┘
                 ▼                                       ▼
 sanitize.py  remove flagged segments,           policy.py  Session (taint + flagged indicators)
              spotlight remaining text                      PolicyEngine (P1–P5)
                 │                                          GuardedExecutor ── only path to tools
                 ▼                                       ▼
          cleaned LLM context                     agent_sim.py  simulated worst-case agent + sandbox
```

## Components

| Module | Responsibility |
|---|---|
| `sieve/config.py` | Environment-variable settings (limits, threshold overrides, egress allowlist). |
| `sieve/normalize.py` | Makes hidden text visible to the detectors and records what was hidden. Never deletes attacker text. |
| `sieve/segment.py` | Offset-exact segmentation; short fragments merge with neighbours (`New task:` merges forward). |
| `sieve/rules.py` | Interpretable regex families: override, role spoofing, addressing the AI, exfiltration, prompt extraction, tool coercion, concealment, output manipulation. |
| `sieve/model.py` | Pickle-free JSON model. Inference reimplements TF-IDF with scikit-learn's analyzers, so explanations are exact. |
| `sieve/engine.py` | `Scanner.scan()` – validation, pipeline orchestration, verdicts, risk index. |
| `sieve/sanitize.py` | Segment removal + spotlighting/datamarking. |
| `sieve/policy.py` | Tool-call policy and the `GuardedExecutor` enforcement point. |
| `sieve/agent_sim.py` | Rule-based "obedient" agent and in-memory sandbox for demonstrating enforcement. |
| `ui/` | Streamlit pages and the visual system; every user-supplied string is HTML-escaped. |
| `scripts/` | Dataset construction, training, evaluation, external baseline, test-sample export. |

## Model choice

A transformer (e.g. the ProtectAI DeBERTa model, ~740 MB) would strain Streamlit Community Cloud's memory limit and is not exactly explainable. The linear model is 0.66 MB compressed, scans a typical document in a few milliseconds on one CPU thread, and every score decomposes into feature contributions. The evaluation compares both on the same held-out data.

Training procedure (`scripts/train.py`):
1. Fit the text model on training segments (templates half A).
2. Choose `C` and fit the fusion layer on calibration segments built from *unseen* templates (half B), so fusion learns how much rules help when the text model meets new phrasing.
3. Calibrate thresholds at the **document** level on clean calibration documents: review = 2% FPR, block = 0.5% FPR.
4. Export vocabulary, IDF, coefficients and thresholds to gzip-compressed JSON.

## Decision logic

- Segment probability ≥ block threshold → BLOCK; ≥ review threshold → REVIEW.
- A REVIEW segment that came from hidden content (HTML comment, CSS-hidden, Unicode tags, Base64) is escalated to BLOCK.
- Document verdict = the most severe segment verdict.
- Risk index 0–100 is a monotone, piecewise-linear rescaling of probability with the review threshold at 40 and block at 70.

## Failure behaviour

- Invalid input (empty, non-text, larger than `SIEVE_MAX_CHARS`) raises `InputError`; the UI shows a fix-it message.
- A missing or malformed model file fails loudly at load time (`ValueError`); the app does not fall back to "allow".
- Unknown tools are denied by default; tool exceptions are captured in the execution record and never propagate.
- `CONFIRM` decisions never run without explicit confirmation; confirmation never overrides `DENY`.

## Deployment

Streamlit Community Cloud runs `streamlit_app.py` from a public GitHub repository with `requirements.txt`. The model file is committed (0.66 MB); training data is not, and is not needed at runtime. Memory use is dominated by Streamlit and pandas/plotly imports; the model adds tens of MB.
