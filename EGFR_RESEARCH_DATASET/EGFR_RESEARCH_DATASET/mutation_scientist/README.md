# mutation_scientist/ — MutationScientist LLM SFT data

Evidence-grounded instruction data to fine-tune a scientific LLM (target platform: Adaption
AutoScientist, SFT) to explain EGFR mutations, interpret experimental measurements, distinguish
assay types, and reason about resistance — **without inventing numbers or citations**.

## Source datasets (JSONL)
| File | Rows | Content |
|---|---|---|
| `mutation_understanding.jsonl` | 33 | per-variant mechanism/classification/domain explanations (UniProt-grounded). |
| `experimental_evidence_reasoning.jsonl` | 65 | IC50 interpretation from **verified Melis 2026** values: WT-vs-mutant fold-changes, ATP-dependence, KD/Ki/IC50 distinction, covalent caveats. Real numbers only. |
| `research_reasoning.jsonl` | 3 | hypothesis generation / experiment design / evidence-limitation tasks. |

Each record: `prompt, completion, task_type, mutation_id, profile_id, compound_id, evidence_ids, source_ids, evidence_type, annotation_confidence, review_status`. `source_ids` point to `REFERENCES.csv` / `Melis2026` / `UNIPROT_P00533`.

## Consolidated SFT (what you upload)
| File | Rows |
|---|---|
| `sft_train.csv` | 912 |
| `sft_validation.csv` | 214 |
| `sft_test.csv` | 215 |
**1,341 total** = 101 hand-grounded + 1,240 teacher-generated (see below).
Columns: `prompt, completion, task_type, mutation_id, profile_id, compound_id, evidence_ids, source_ids, review_status, annotation_confidence`. **Only `prompt`+`completion` train**; the rest are audit metadata. Every `prompt` is self-contained (all needed numbers/context inline) — AutoScientist does NOT auto-inject metadata columns.

Split = **mutation-held-out** (held-out variants e.g. S768I, L861Q, T790M not in train) to test generalisation to unseen variants.

## Also included
- `eval_questions.jsonl` (3) — independent, human-reviewable Q + reference answer.
- `preference_pairs.jsonl` (2) — realistic chosen/rejected (e.g., IC50≠clinical efficacy; KD≠IC50) for optional DPO.

## Volume & provenance (clears the AutoScientist 1,000-row floor)
- **1,341 unique examples** total, split 912 / 214 / 215 (mutation-held-out: S768I, L861Q → test; T790M → val).
- **101** are hand-grounded (`review_status=model_generated_grounded`).
- **1,240** are **teacher-generated** (`review_status=teacher_generated_unverified_autochecked`), produced by 6 parallel teacher-LLM agents each fed ONLY real fact-packets (real IC50s from Melis/BindingDB, real DOIs, UniProt facts). Stored also in `teacher_generated.jsonl`.
- **Anti-hallucination check:** every `<num> nM` in a completion was verified to trace back to the real source numbers the agent was given; **8 examples were rejected** for ungrounded numbers (1,248 generated → 1,240 kept). Fold-changes are agent-computed from source numbers.
- **Still recommended:** a human expert pass over the teacher set before a production run (status is `…unverified_autochecked`, i.e. machine-grounded but not human-reviewed). DPO via `preference_pairs.jsonl` is optional.

## Upload mapping (Adaption, raw/SFT)
`column_mapping={"prompt":"prompt","completion":"completion"}`, `processing_mode="raw"`. Needs `ADAPTION_API_KEY`. Resolve the model via `recommend_hyperparams` (don't hardcode). Confirm `run.training_method` resolves to `instruction`. Keep `sft_test.csv`/`eval_questions.jsonl` OUT of the training upload.

## Pending downstream (documented, not fabricated)
Boltz-output **interpretation** examples (real WT/mutant `affinity_pred_value` from actual Boltz inference) are **not** generated here — they require running Boltz. The dataset is organised so predictions can be joined later via `mutation_id`+`compound_id`+`complex_id`.
