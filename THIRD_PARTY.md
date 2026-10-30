# Third-party components and data

Sieve's own source code is MIT-licensed (see `LICENSE`). It builds on the following.

## Libraries (runtime)

| Component | Use | Licence |
|---|---|---|
| Streamlit | Web UI | Apache-2.0 |
| scikit-learn | TF-IDF analyzers, logistic regression (training) | BSD-3-Clause |
| NumPy, SciPy | Numerics | BSD-3-Clause |
| pandas | Tables | BSD-3-Clause |
| Plotly | Charts | MIT |

Development only: pytest (MIT), Hugging Face `datasets` (Apache-2.0), onnxruntime (MIT), tokenizers (Apache-2.0), huggingface_hub (Apache-2.0).

## Datasets (downloaded by `scripts/build_dataset.py`, not redistributed)

| Dataset | Use | Licence |
|---|---|---|
| [deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections) | Direct-injection examples (train/calibration); external test split | Apache-2.0 |
| [rajpurkar/squad](https://huggingface.co/datasets/rajpurkar/squad) (SQuAD v1.1) | Benign host documents for injected and clean examples | CC BY-SA 4.0 |
| [databricks/databricks-dolly-15k](https://huggingface.co/datasets/databricks/databricks-dolly-15k) | Benign, imperative-rich responses (false-positive control) | CC BY-SA 3.0 |

`reports/test_case_sample.jsonl` contains 75 short excerpts derived from SQuAD and Dolly-15k (with injections written for this project) for the in-app test explorer. That file is distributed under **CC BY-SA 4.0**, with attribution to the SQuAD authors (Rajpurkar et al., 2016) and Databricks.

The trained model file `models/sieve_model.json.gz` contains learned weights and an n-gram vocabulary derived from the datasets above.

## Baseline model (evaluation only, not shipped)

[protectai/deberta-v3-base-prompt-injection-v2](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2), Apache-2.0, run via its published ONNX export in `scripts/baseline_deberta.py`.

## Research the design draws on

- Y. Chen et al., *Can Indirect Prompt Injection Attacks Be Detected and Removed?* ACL 2025 (arXiv:2502.16580). Benchmark construction (QA documents, head/middle/tail injection) and the segmentation-removal strategy. Their data has no stated licence and is **not** used.
- K. Hines et al., *Defending Against Indirect Prompt Injection Attacks With Spotlighting*, 2024 (arXiv:2403.14720). Delimiting and datamarking of untrusted text.
- K. Greshake et al., *Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection*, AISec 2023. Threat model for indirect injection.

All injection templates, rules, hard negatives and samples were written for this project.
