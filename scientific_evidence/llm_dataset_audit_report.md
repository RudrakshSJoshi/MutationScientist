# LLM SFT dataset audit

Deterministic scientific-trustworthiness screen of every SFT row (prompt + completion). The original dataset is **not modified**; this is a review layer with traceability (`source_file` + `row_index`).

**Checks:** (1) concentration fabrication — a nM/uM/mM/pM value in the completion absent from the prompt (computed fold-changes/% are allowed and not flagged); (2) biochemical/cellular (or IC50/KD) conflation; (3) invented DOI/PMID not in the curated corpus.

- **Rows audited:** 1341
- **Rows with >=1 flag:** 6 (0.4%)
- **Concentration-fabrication flags:** 6
- **Assay-conflation flags:** 0
- **Invented-citation flags:** 0

## By review_status

| review_status | n | flagged | concentration-fab | conflation | invented-cite |
|---|---|---|---|---|---|
| model_generated_grounded | 101 | 0 (0.0%) | 0 | 0 | 0 |
| teacher_generated_unverified_autochecked | 1240 | 6 (0.5%) | 6 | 0 | 0 |

## By task_type

| task_type | n | flagged | concentration-fab | conflation | invented-cite |
|---|---|---|---|---|---|
| assay_distinction | 138 | 2 (1.4%) | 2 | 0 | 0 |
| evidence_limitations | 1 | 0 (0.0%) | 0 | 0 | 0 |
| evidence_qa | 221 | 0 (0.0%) | 0 | 0 | 0 |
| experiment_design | 1 | 0 (0.0%) | 0 | 0 | 0 |
| experimental_interpretation | 499 | 0 (0.0%) | 0 | 0 | 0 |
| hypothesis_generation | 1 | 0 (0.0%) | 0 | 0 | 0 |
| inhibitor_comparison | 322 | 0 (0.0%) | 0 | 0 | 0 |
| mutation_classification | 55 | 0 (0.0%) | 0 | 0 | 0 |
| mutation_mechanism | 54 | 0 (0.0%) | 0 | 0 | 0 |
| resistance_interpretation | 49 | 4 (8.2%) | 4 | 0 | 0 |

## Interpretation

- **Number reviewed:** all 1341 SFT rows (train + validation + test), of which 1240 are teacher-generated/unverified and 101 are hand-grounded.
- **Number passed (no flag):** 1335.
- **Number requiring human review:** 6 (listed in `llm_dataset_audit.csv`).
- **Main error categories:** concentration-fabrication (a value in the answer not traceable to the prompt) is the highest-priority flag because it directly tests the no-fabrication rule; conflation flags indicate assay-type mixing; invented-citation flags indicate a DOI/PMID outside the corpus.
- These flags are **screening signals, not verdicts** — a flagged row may be a correct computed value whose inputs were phrased indirectly in the prompt, or an acceptable paraphrase. Each flagged row should be confirmed by a domain reviewer before any correction is applied, and corrections must be recorded separately from the source dataset.
