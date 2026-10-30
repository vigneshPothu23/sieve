# Sieve — an explainable firewall for untrusted content in LLM apps

LLM applications read text they do not control: web pages, e-mails, shared files, search and tool results. Any of it can carry instructions written for the model rather than the person — **indirect prompt injection**. Sieve sits between that content and the model:

1. **Inspect** — normalises hidden text (zero-width characters, invisible Unicode tags, homoglyphs, HTML comments, CSS-hidden elements, Base64), then scores every sentence with a small, exactly-explainable model and eight interpretable rule families.
2. **Clean** — removes the flagged segments and wraps the rest in data delimiters (spotlighting) before it reaches the LLM.
3. **Enforce** — for agents, a policy gate is the only path to tools: once injected content is seen, outbound, destructive and payment actions are locked, attacker-supplied URLs/e-mails/paths cannot become arguments, and dangerous commands are denied. Denied calls never reach the tool function.

Everything runs on CPU in a few milliseconds per document, with no paid API and a 0.66 MB model file. The Streamlit app has four pages: **Inspect content**, **Agent firewall** (a sandboxed before/after demo), **Evaluation** and **How it works**.

> Sieve reduces risk; it is not a guarantee. It is one layer next to least-privilege tool design and human review.

## Results (held-out test data, measured locally)

| System | Indirect recall | Clean-doc FPR | Obfuscated recall | Other-domain FPR | deepset F1 |
|---|---|---|---|---|---|
| **Sieve (review or block)** | **86.3%** | **0.7%** | **89.7%** | 2.6% | **79.4%** |
| Sieve (block only) | 67.9% | 0.0% | 70.3% | 0.9% | 72.9% |
| Sieve without normalisation | 86.3% | 0.7% | 48.7% | 2.6% | 79.4% |
| Text model only (no rules) | 81.4% | 0.6% | 82.7% | 2.6% | 78.4% |
| Keyword filter | 12.0% | 0.0% | 2.3% | 0.3% | 3.3% |
| ProtectAI DeBERTa v2 (offline baseline) | 48.2% | 0.0% | 34.3% | 4.6% | 53.7% |

- *Indirect*: 672 SQuAD-validation documents with an injection at the head, middle or tail (unseen templates, URLs and e-mails), plus 672 clean documents. Sieve confusion matrix: TP 580, FN 92, FP 5, TN 667 (precision 99.2%, F1 92.3%).
- *Obfuscated*: 300 injections hidden with six techniques. *Other-domain FPR*: 1,000 unseen Dolly-15k responses + 30 hard negatives. *deepset*: the external deepset/prompt-injections test split (direct chat prompts).
- Latency: Sieve median 2.6 ms, p95 6.9 ms per document (one thread, 2 vCPU container). DeBERTa via ONNX: mean 243 ms.
- Cleaning: the injection is in the top-scoring segment for 96.7% of detected documents; 100% of cleaned documents re-scan as clean; 99.9% of clean-document text is preserved.

**Where it struggles** (also shown in the app): subtle, task-plausible injections without trigger words (66.7% caught); benign text that *discusses* prompt injection (30% of 30 hard negatives flagged); benign direct chat prompts (28.6% flagged — Sieve is tuned for content that should contain no instructions). The attack templates were written by the same author as the detector, so treat the benchmark as easier than attacks in the wild. An adaptive attacker who can query Sieve will find phrasings that score low — that is why the policy gate does not depend on detection alone.

The DeBERTa comparison uses the public model as its card describes (whole document, 512 tokens). It was trained for direct injection, so this measures fitness for *this* task, not the model's overall quality.

## What is honestly new here

Not a new algorithm. The contribution is an engineering integration, evaluated on a leakage-controlled benchmark: hidden-text normalisation + segment-level detection with exact explanations + segment removal + an enforcing tool-call gate, small enough for free hosting. Design draws on Chen et al. (ACL 2025) for the benchmark recipe and segment removal, and Hines et al. (2024) for spotlighting. See [THIRD_PARTY.md](THIRD_PARTY.md).

## Run it locally (Windows, macOS, Linux)

Requires Python 3.11–3.13.

```bash
git clone https://github.com/<your-username>/sieve.git
cd sieve
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app opens at http://localhost:8501. If PowerShell refuses to run the activate script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use `.venv\Scripts\activate.bat` from Command Prompt.

### Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

64 tests: normalisation, segmentation, rules, model exactness, engine validation, sanitiser, every policy rule (with spy tools proving denied calls never execute), the agent scenarios end to end, HTML-escaping of hostile input, and the real Streamlit app driven through `streamlit.testing.AppTest`.

### Rebuild the data, retrain and re-evaluate

```bash
pip install -r requirements-dev.txt
python scripts/build_dataset.py      # downloads deepset, SQuAD, Dolly from the Hugging Face Hub
python scripts/train.py              # writes models/sieve_model.json.gz
python scripts/baseline_deberta.py   # optional, downloads ~740 MB, ~15 min on CPU
python scripts/evaluate.py           # writes reports/eval_results.json (read by the app)
python scripts/export_test_sample.py # test cases for the in-app explorer
```

All splits are deterministic (seed 13).

## Deploy free on Streamlit Community Cloud

1. Push this folder to a **public** GitHub repository (the model and reports are committed; `data/` is not needed at runtime).
2. Go to <https://share.streamlit.io>, sign in with GitHub, choose **Create app → Deploy a public app from GitHub**.
3. Repository: `<your-username>/sieve`, branch `main`, main file `streamlit_app.py`. Under **Advanced settings** pick Python 3.13.
4. Deploy. No secrets are required. Optional settings (see `.streamlit/secrets.toml.example`) go in **App settings → Secrets**.

Community Cloud's free tier is CPU-only with limited memory and puts apps to sleep after 12 hours without traffic; Sieve's footprint is small enough for it.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `SIEVE_MAX_CHARS` | 50000 | Largest input accepted per scan |
| `SIEVE_REVIEW_THRESHOLD`, `SIEVE_BLOCK_THRESHOLD` | calibrated | Override the probability thresholds |
| `SIEVE_EGRESS_ALLOWLIST` | example-corp.com | Domains agents may contact without approval |
| `SIEVE_MODEL_PATH` | models/sieve_model.json.gz | Alternative model file |

## Use it in code

```python
from sieve.engine import Scanner
from sieve.sanitize import sanitize

result = Scanner().scan(retrieved_text)
if result.verdict != "ALLOW":
    print([s.text for s in result.flagged])
prompt_block = sanitize(result).llm_context   # cleaned + spotlighted
```

For agents, route every tool call through `sieve.policy.GuardedExecutor` (see `sieve/agent_sim.py` for a complete example).

## Project layout

```
streamlit_app.py      entry point
sieve/                normalize, segment, rules, model, engine, sanitize, policy, agent_sim, config, samples
ui/                   pages and visual system
scripts/              dataset, training, evaluation, baseline, sample export
models/               trained model (JSON, no pickle)
reports/              evaluation results used by the app
tests/                pytest suite
docs/                 ARCHITECTURE.md, THREAT_MODEL.md
```

## Licence

Code: MIT. Data and baseline licences: see [THIRD_PARTY.md](THIRD_PARTY.md).
