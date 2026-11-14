# EGFR Acquired-Resistance Research Dataset (NSCLC)

**Version:** 1.0.0 · **Date:** 2026-11-14 · **Status:** COMPLETE (data-and-documentation deliverable)

A scientifically defensible, fully-traceable dataset for mutation-aware EGFR–inhibitor modelling in
non-small-cell lung cancer, feeding two downstream fine-tuning efforts (**training is not part of
this package**):
1. **Boltz-2 affinity-head fine-tuning** — experimentally labelled EGFR–inhibitor IC50 data (`boltz2/`).
2. **MutationScientist LLM (Adaption AutoScientist)** — evidence-grounded EGFR reasoning (`mutation_scientist/`).

> **No fabrication.** Every measurement traces to BindingDB or Melis 2026; every sequence is validated
> against UniProt P00533; every compound identifier is from PubChem; every evidence claim and structure
> carries a real DOI/PMID or PDB id. Where data could not be obtained it is documented, not invented.

---

## 1. Scientific scope
EGFR mutation-dependent inhibitor interactions and acquired resistance in NSCLC: WT vs mutant potency,
T790M (gatekeeper) and C797S (covalent-anchor-loss) resistance, exon-19 deletions, atypical activating
mutations, and the covalent-vs-reversible / generational inhibitor landscape.

## 2. Reference protein & numbering
UniProt **P00533**, canonical **P00533-1 (1210 aa precursor, Met=1)**, sha256 `dbb4583267ad40a7…`.
Clinical numbering (L858R, T790M, C797S, G719x, L861Q, S768I, ex19del=E746_A750) is defined on this
sequence; WT residues verified at every panel position.

## 3. ★ Boltz-2 affinity label convention (verified in source)
```
boltz_target_value = log10(IC50_nM) - 3   ==  log10(IC50 in µM);   LOWER = STRONGER   (NOT pIC50)
```
`molecularinformatics/Boltz2_affinity` @ `bc06a0b`: YAML `value` → Huber loss directly, no transform.

## 4. Directory structure
```
EGFR_RESEARCH_DATASET/
├── README.md                      this file
├── DATASET_MANIFEST.json          inventory + actual counts + blockers
├── REFERENCES.csv                 29 sources (DOI/PMID/DB ids, licences)
├── curated/
│   ├── mutations.csv              19 variants (17 sequenced + OTHER/UNSPECIFIED)
│   ├── mutation_profiles.csv      19 profiles (component mutation ids)
│   ├── compounds.csv              13 curated inhibitors (PubChem-verified)
│   ├── affinity_measurements.csv  31,655 measurements (all types, provenance, eligibility)
│   ├── cellular_assays.csv        header + CELLULAR_ASSAYS_NOTE.txt (numeric data in Melis Suppl.; not fabricated)
│   ├── biological_evidence.csv    40 literature claims (real DOIs)
│   ├── bindingdb_ligands.csv      16,393 BindingDB ligand SMILES
│   ├── protein_sequences.fasta    17 validated, checksummed sequences
│   ├── protein_sequence_metadata.csv
│   └── protein_structures/structures_index.csv   60 EGFR PDB entries (RCSB)
├── boltz2/                        see boltz2/README.md
│   ├── boltz_compatible_dataset.csv   18,189 eligible rows
│   ├── complexes/{train,validation,test}/COMPLEX_*.yaml   6,843 YAMLs
│   ├── complex_metadata.csv · val_names.txt · msa/<variant>.a3m (17)
├── mutation_scientist/            see mutation_scientist/README.md
│   ├── mutation_understanding.jsonl / experimental_evidence_reasoning.jsonl / research_reasoning.jsonl
│   ├── sft_train.csv / sft_validation.csv / sft_test.csv
│   ├── eval_questions.jsonl · preference_pairs.jsonl
├── validation/                    8 computed QC reports (see §9)
└── raw/                           source snapshots (UniProt FASTA, PubChem JSON)
```

## 5. Data dictionary (key columns)
**affinity_measurements.csv** (one original measurement per row): `measurement_id, mutation_id→mutations.csv,
profile_id→mutation_profiles.csv, compound_id→compounds.csv|bindingdb_ligands.csv, protein_construct,
measurement_type {IC50|Ki|KD|EC50}, original_value, original_unit(nM), measurement_relation {=,>,<},
boltz_target_value (log10 IC50 µM; blank if not applicable/censored), boltz_target_unit, source_database,
source_record_id, doi, pmid, source_url, quality_flag, boltz_eligibility, exclusion_reason`.
**boltz_eligibility**: `eligible` (→ training) | `requires_review` (covalent/censored/out-of-panel) |
`incompatible_target_scale` (KD/Ki) | `ineligible_assay_type` (EC50) | `insufficient_provenance` (n.d.).
**mutations.csv**: `mutation_id, mutation_notation, mutation_type, position, wt_residue, mutant_residue,
protein_domain, mutation_classification, known_mechanism, resistance_association, …`.
**compounds.csv**: `compound_id, compound_name, canonical/isomeric_smiles, inchi, inchikey, pubchem_cid,
chembl_id(blank—ChEMBL outage), drug_class, inhibitor_generation, binding_mechanism, covalent_status, warhead_type, …`.
Full per-file dictionaries: `boltz2/README.md`, `mutation_scientist/README.md`; JSONL schemas therein.

## 6. Coverage (actual counts from delivered files)
- **Mutations:** 19 (17 sequenced); classes: reference/activating/resistance/activating+resistance.
- **Compounds:** 13 curated (gen 1→4 + allosteric; covalent vs non-covalent recorded) + 16,393 BindingDB assay ligands.
- **Affinity:** 31,655 measurements (72 Melis gold biochemical IC50 + 31,583 BindingDB). Types: IC50 29,302 · KD 1,707 · Ki 370 · EC50 276.
- **Boltz-eligible:** 18,189 across 16 variants, 10,509 distinct compounds (per-variant counts in `boltz2/README.md`).
- **Structures:** 60 EGFR PDB entries. **Evidence:** 40 claims / 29 sources. **LLM:** 1,341 examples (101 hand-grounded + 1,240 teacher-generated, number-grounding verified; split 912/214/215).

## 7. Structural data
`curated/protein_structures/structures_index.csv`: PDB id, title, method, resolution, bound ligands, UniProt,
source_url (RCSB experimental). Sequences (`protein_sequences.fasta`) are the mutant kinase sequences for Boltz
(which predicts structure); no experimental mutant structures are mislabelled, none fabricated.

## 8. Sources & provenance (`REFERENCES.csv`)
UniProt P00533 (sequences), PubChem (compound identities), BindingDB_All_202611 (bulk affinities, mutation
construct parsed from Target Name), Melis et al. 2026 Front Oncol (DOI 10.3389/fonc.2026.1952701, PMC13634975;
verified Table 2), Europe PMC (literature evidence), RCSB PDB (structures). Licences/usage per row. **ChEMBL
was unreachable at build (EBI HTTP 500)** → no ChEMBL rows; `chembl_id` blank.

## 9. Data quality (`validation/`)
`data_quality_report.md` (counts + QC), `mutation_coverage.csv`, `compound_coverage.csv`, `assay_distribution.csv`,
`source_coverage.csv`, `duplicate_records.csv` (2,421 replicate groups — expected for aggregated BindingDB;
handled by mean-aggregation in YAMLs), `conflicting_measurements.csv` (232 same-pair IC50 spreads >2 log10 —
preserved + flagged), `missing_fields_report.csv`, `split_leakage_report.md` (**0 ligand leakage; splits ligand-disjoint**).
Referential integrity verified: every affinity `mutation_id`/`compound_id`/`profile_id` resolves.

## 10. Limitations
- BindingDB IC50 heterogeneous (multi-lab, mixed ATP/assay conditions, no uniform assay_id) → noisier labels.
- BindingDB covalency flagged by **acrylamide-SMILES heuristic**, not per-compound curation.
- ChEMBL outage → no ChEMBL assays; `chembl_id` blank; would add volume on recovery.
- Cellular IC50/GI50 (Melis Suppl. Tables 3/4) not numerically extracted → `cellular_assays.csv` headed/documented only.
- LLM set is 1,341 (clears AutoScientist's 1,000 floor): 1,240 are **teacher-LLM-generated**, machine-verified for number-grounding (8 rejected) but **not human-reviewed** — a domain-expert pass is recommended before a production run.
- **Not for clinical decisions.** Biochemical/predicted affinity ≠ cellular or clinical response.

## 11. Downstream use
- **Boltz-2:** train from `boltz2/complexes/` (labels in YAML `value` = log10 IC50 µM) or index via
  `boltz_compatible_dataset.csv`; `val_names.txt` = validation split. GPU/P100 notes in `boltz2/README.md`.
  Covalent inhibitors are intentionally excluded from the regression target.
- **LLM:** upload `mutation_scientist/sft_train.csv` (map `prompt`,`completion`; raw/SFT); hold out `sft_test.csv`
  + `eval_questions.jsonl`; needs `ADAPTION_API_KEY`. See `mutation_scientist/README.md`.
- **Join point for later Boltz-interpretation LLM data:** `mutation_id` + `compound_id` + `complex_id`.
