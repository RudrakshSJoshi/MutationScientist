# Molecular Analysis — Boltz-2 affinity on EGFR resistance

*Generated 2026-11-15 · 70 real Boltz-2 predictions · label = log₁₀(IC50 µM), LOWER = STRONGER, NOT pIC50*

## Method

- **Model:** Boltz-2 (2.2.1) pretrained affinity head — inference only (no fine-tune of the affinity head).
- **Hardware:** Apple M-series, MLX/MPS (Metal), precision float32, fused kernels off.
- **Sampling settings (per complex, recorded in the JSON):** {"results": "boltz2-defaults(recycle3,ss200,affens5)", "results_night": "reduced(recycle1,ss50,affens3)"}.
- **Inputs:** the dataset's ready-made complexes (full-length EGFR P00533 + ColabFold MSA per variant).
- **Ground truth:** each complex's curated experimental `affinity_label` (same units).

## Validation vs experiment

| Set | n | Spearman ρ | Pearson r | MAE (log₁₀) |
|---|--:|--:|--:|--:|
| overall | 70 | 0.51 | 0.57 | 1.36 |
| curated panel | 12 | 0.11 | -0.04 | 0.54 |
| bindingdb | 58 | 0.59 | 0.62 | 1.52 |

*Spearman (rank) is the headline — BindingDB IC50 are multi-lab/heterogeneous, so rank agreement matters more than absolute MAE. Curated-panel rows (BLU-945, JBJ-09-063) are the cleanest ground truth.*

## Does Boltz capture the C797S resistance shift?

Direction agreement (predicted Δ sign vs experimental Δ sign across C797S pairs): **38%**.

| Compound | Pair | Predicted Δ | Experimental Δ | Agree |
|---|---|--:|--:|:--:|
| BDB_679698 | ex19del/T790M→ex19del/T790M/C797S | 0.46 | -0.40 | · |
| BDB_717491 | ex19del/T790M→ex19del/T790M/C797S | -0.35 | 0.20 | · |
| BLU945 | L858R→L858R/C797S | -0.24 | -0.10 | ✓ |
| BLU945 | L858R/T790M→L858R/T790M/C797S | -0.12 | 0.72 | · |
| BLU945 | ex19del→ex19del/C797S | 0.46 | 0.01 | ✓ |
| BLU945 | ex19del/T790M→ex19del/T790M/C797S | -0.40 | 0.19 | · |
| JBJ09063 | L858R→L858R/C797S | -0.01 | 0.19 | · |
| JBJ09063 | L858R/T790M→L858R/T790M/C797S | 0.48 | 0.05 | ✓ |

*(Positive Δ = weaker binding = resistance. Osimertinib is covalent → no Boltz complex, so its C797S resistance stays in the evidence/LLM layer, not here — by design.)*

## BLU-945 mutant selectivity (predicted, strongest→weakest)

| Variant | Predicted | Experimental |
|---|--:|--:|
| ex19del/T790M/C797S | -2.55 | -1.62 |
| ex19del | -2.17 | -0.85 |
| ex19del/T790M | -2.15 | -1.81 |
| L858R/T790M/C797S | -2.13 | -0.66 |
| L858R/T790M | -2.01 | -1.38 |
| ex19del/C797S | -1.71 | -0.84 |
| L858R/C797S | -1.46 | -1.36 |
| L858R | -1.22 | -1.25 |

## Artifacts

- `boltz_predictions.json` — app-schema array (feeds `BOLTZ_PREDICTIONS_PATH`).
- `baseline_predictions.csv` — full per-complex prediction table.
- `wt_mutant_comparisons.csv` — per-compound predicted value per variant + Δ vs WT.
- `inhibitor_rankings.csv` — per-mutation inhibitor ranking.
- `affinity_landscape.csv` — compound × variant predicted-value matrix.
- `validation.json` — these stats in machine form.
- `comparison_plots/` — predicted-vs-experiment scatter, BLU-945 ladder, C797S resistance, ranking.
- `structural_analysis/` — per-complex ligand–pocket contacts + mutated-residue contact flags.

## Honest limitations

- **Coverage:** this is a prioritized subset (curated panel + stratified BindingDB), not all 6,843 eligible complexes — full-length structure prediction is ~minutes/complex on MPS, so the whole set is a GPU-cluster / Kaggle-P100 / Tamarind job (configs provided), not an overnight-Mac job.
- **Mixed sampling settings:** the 8 BLU-945 ladder complexes ran at Boltz-2 defaults; the rest at reduced settings for throughput. Each record carries its `sampling_settings`.
- **Pretrained head:** these are the *pretrained* Boltz-2 affinity predictions, not our fine-tuned head.
- **BindingDB labels are noisy** (multi-lab, mixed assay conditions); treat absolute values with care, prefer the rank/relative signal.
- Not for clinical decisions.
