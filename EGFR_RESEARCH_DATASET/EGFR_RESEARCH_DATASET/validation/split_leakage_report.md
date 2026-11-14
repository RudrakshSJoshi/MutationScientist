# Split leakage report

## Boltz complexes (ligand-disjoint splits)
- train ligands: 3320 | validation ligands: 432 | test ligands: 408
- ligands shared between train and (val or test): **0** (none — PASS)
- Splits are LIGAND-DISJOINT (scaffold-held-out): every complex of a given ligand sits in one split.
- For a MUTATION-held-out evaluation, hold out all complexes of a chosen variant at train time
  (e.g., EGFR_S768I = 53 complexes, or EGFR_L861Q/G719C/G719S) — these are small, distinct variants
  suitable as a mutation-generalisation probe.

## LLM SFT (mutation-held-out)
- train mutation_ids: ['', 'EGFR_C797S', 'EGFR_G719A', 'EGFR_G719C', 'EGFR_G719S', 'EGFR_L858R', 'EGFR_L858R_C797S', 'EGFR_L858R_T790M', 'EGFR_L858R_T790M_C797S', 'EGFR_T790M_C797S', 'EGFR_WT', 'EGFR_ex19del', 'EGFR_ex19del_C797S', 'EGFR_ex19del_T790M', 'EGFR_ex19del_T790M_C797S']
- test mutation_ids:  ['', 'EGFR_C797S', 'EGFR_G719A', 'EGFR_G719C', 'EGFR_G719S', 'EGFR_L858R', 'EGFR_L858R_C797S', 'EGFR_L858R_T790M', 'EGFR_L858R_T790M_C797S', 'EGFR_L861Q', 'EGFR_S768I', 'EGFR_T790M_C797S', 'EGFR_WT', 'EGFR_ex19del', 'EGFR_ex19del_C797S', 'EGFR_ex19del_T790M', 'EGFR_ex19del_T790M_C797S']
- held-out test variants (EGFR_S768I, EGFR_L861Q) absent from train: True
