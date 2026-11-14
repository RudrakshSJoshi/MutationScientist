# boltz2/ — Boltz-2 affinity-head fine-tuning data

This folder is the input for **affinity-head fine-tuning** of Boltz-2 (structure modules frozen).
Target implementation: `molecularinformatics/Boltz2_affinity` @ commit `bc06a0b` (boltz v2.2.1).

## ★ Affinity label convention (verified against source code)
```
value (YAML property) = boltz_target_value = log10(IC50_nM) - 3  ==  log10(IC50 in µM);  LOWER = STRONGER
```
NOT pIC50. Verified: `docs/prediction.md:244-249`; the YAML `value` is fed directly into the Huber loss (`loss/affinity.py`) with no transform. Anchors: 1 nM→−3, 1 µM→0, 100 µM→+2.

## Files
| File | Contents |
|---|---|
| `boltz_compatible_dataset.csv` | 18,189 **eligible** measurement rows (biochemical IC50, relation `=`, non-covalent, in-panel/WT construct) — the full eligible index. |
| `complexes/{train,validation,test}/COMPLEX_*.yaml` | 6,843 ready-to-run Boltz complexes (unique (variant, ligand); replicate IC50 aggregated by mean in log10 µM space). WT capped at 2,000 for balance. |
| `complex_metadata.csv` | one row per complex: complex_id → mutation_id/profile_id/compound_id/sequence_id/measurement_ids, msa_path, affinity_label (log10 IC50 µM), split, n_replicates. |
| `msa/<variant>.a3m` | ColabFold (MMseqs2, `env` mode) MSAs; WT depth ~9,087. Point-mutant MSAs derived from the WT/ex19del base by query-residue swap (substitutions don't shift columns). |
| `val_names.txt` | validation complex names (one per line) for the repo's `split_file`. |

## Splits
- **Ligand-disjoint (scaffold-held-out):** all complexes of a given ligand are in ONE split (train 80 / val 10 / test 10 by ligand hash). Verified 0 ligand leakage (`validation/split_leakage_report.md`).
- **Mutation-held-out (optional eval):** hold out all complexes of a small distinct variant (e.g., `EGFR_S768I`, 53) at train time.

## Eligible coverage (16 variants, 10,509 distinct compounds)
WT 13,215* · L858R/T790M/C797S 942 · L858R/T790M 698 · L858R/C797S 670 · ex19del/C797S 661 · L858R 589 · T790M/C797S 435 · C797S 322 · ex19del 235 · ex19del/T790M/C797S 159 · T790M 114 · ex19del/T790M 90 · S768I 53 · G719C/G719S/L861Q 2 each.
*WT is capped to 2,000 in the YAML complexes; the CSV retains all.

## Covalent exclusion (important)
Osimertinib, silevertinib (and afatinib/dacomitinib) are covalent (acrylamide/Cys797) → time-dependent IC50 → `requires_review`, **excluded** from this eligible set. BindingDB covalency flagged via an acrylamide-SMILES **heuristic** (`quality_flag`). The osimertinib×C797S resistance signal lives in the LLM interpretation data, not this regression target.

## How to train (not included; see Boltz2_affinity repo)
1. Env: Python 3.10–3.12 + CUDA GPU (compute ≥8.0 ideal). On **Kaggle P100** set `precision: 16-mixed` (no bf16 on Pascal) and `use_trifast: false`.
2. `boltz predict complexes/<split> --write_embeddings …` → `data_collector.py` → `trainv2.py config_aff/config.yaml` with `paths/local.yaml` (pretrained `boltz2_aff.ckpt`, `split_file=val_names.txt`).
3. Only `affinity_module{,1,2}` train; init from `boltz2_aff.ckpt`; monitor `val/affinity_pearson`.

## Limitations
BindingDB IC50 are multi-lab/heterogeneous (mixed ATP/assay conditions, no uniform assay_id) → noisier labels; treat absolute values with care, prefer within-assay/relative signal where possible.
