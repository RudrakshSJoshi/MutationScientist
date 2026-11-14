# Data quality report (computed from delivered files)

## Counts
- Mutations: 19 (sequenced variants: 17)
- Compounds (curated panel): 13
- Affinity measurements: 31655
- Boltz-eligible: 18189
- Biological evidence claims: 40
- Boltz complexes (YAML): 6843

## Measurement types (all rows)
{'IC50': 29302, 'KD': 1707, 'EC50': 276, 'Ki': 370}

## Eligibility breakdown
{'requires_review': 11109, 'insufficient_provenance': 4, 'eligible': 18189, 'incompatible_target_scale': 2077, 'ineligible_assay_type': 276}

## Boltz-eligible by variant
{'EGFR_WT': 13215, 'EGFR_L858R': 589, 'EGFR_ex19del': 235, 'EGFR_L858R_T790M': 698, 'EGFR_ex19del_T790M': 90, 'EGFR_L858R_C797S': 670, 'EGFR_ex19del_C797S': 661, 'EGFR_ex19del_T790M_C797S': 159, 'EGFR_L858R_T790M_C797S': 942, 'EGFR_T790M': 114, 'EGFR_T790M_C797S': 435, 'EGFR_G719C': 2, 'EGFR_G719S': 2, 'EGFR_L861Q': 2, 'EGFR_C797S': 322, 'EGFR_S768I': 53}

## Integrity & QC
- Referential integrity: every affinity mutation_id/compound_id/profile_id resolves (verified at build).
- Duplicate (mutation,compound,type,value,source_record) groups: 2421
- Conflicting eligible IC50 pairs (>2 log10 spread for same mutation+compound): see conflicting_measurements.csv
- Melis Table 2 values verified against source PDF; censored (>10,000 nM) preserved with relation '>'.

## Known limitations
- BindingDB IC50 heterogeneous (multi-lab, mixed ATP/assay conditions, no uniform assay_id) -> noisier labels.
- Covalency for BindingDB ligands flagged by acrylamide-SMILES heuristic, not per-compound curation.
- ChEMBL unreachable at build (EBI HTTP 500) -> no ChEMBL rows; compound chembl_id blank.
- Cellular IC50/GI50 (Melis Suppl. Tables 3/4) not numerically extracted -> cellular_assays.csv headed/documented only.
- Not for clinical decisions.
