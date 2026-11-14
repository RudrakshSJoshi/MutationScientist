# PERSON 2 — BOLTZ-2 INFERENCE, MOLECULAR SCREENING AND STRUCTURAL ANALYSIS

## Objective

Own the molecular inference and analysis pipeline for the EGFR research project.

Your responsibility is to use the provided EGFR dataset and pretrained Boltz-2 model to establish baseline molecular predictions, analyse EGFR mutation–inhibitor interactions, and prepare the outputs required for the final research application.

You are NOT responsible for fine-tuning Boltz-2. That is being handled separately.

Your work must directly support the Boltz-2 fine-tuning process and produce independent scientific findings.

## 1. Understand the dataset

First, inspect:

- `README.md`
- `egfr_dataset_loader.py`
- `boltz2/complex_metadata.csv`
- `boltz2/boltz_compatible_dataset.csv`
- `boltz2/complexes/`
- `boltz2/msa/`
- `curated/mutations.csv`
- `curated/compounds.csv`
- `curated/protein_sequences.fasta`

Load the dataset using:

```python
from egfr_dataset_loader import EGFRDataset

ds = EGFRDataset("EGFR_RESEARCH_DATASET")

print(ds.validate())
print(ds.boltz.counts())
```

Understand the following:

- There are 6,843 de-duplicated Boltz complexes.
- The splits contain 5,515 training, 684 validation and 644 test complexes.
- There are 18,189 eligible measurement rows before replicate deduplication.
- The split is ligand-disjoint.
- Every complex has a corresponding YAML input and precomputed MSA.

Do not assume every possible mutation–compound combination exists. Work from the actual complex metadata.

## 2. Establish pretrained Boltz-2 baseline predictions

Run pretrained Boltz-2 inference using the provided YAML files.

Your first goal is to obtain baseline predictions for the available EGFR complexes.

Where computational resources permit, process all 6,843 complexes.

Use the existing YAML inputs and their corresponding MSA files. Do not recreate or modify the experimental labels.

Generate and preserve:

- `affinity_pred_value`
- `affinity_probability_binary`
- Predicted protein–ligand structures.
- Relevant confidence metadata.
- Any other useful output exposed by the installed Boltz version.

Every prediction must be associated with its original `complex_id`.

**Important:** these are pretrained model predictions, not experimental measurements. Never overwrite the experimental affinity labels.

## 3. Generate the molecular embedding outputs

Generate Boltz embeddings for the complexes using the documented `--write_embeddings` functionality.

These embeddings and associated prediction outputs are needed by the person responsible for affinity-head fine-tuning.

Organise them with an unambiguous mapping:

`complex_id → YAML → inference output → embedding → experimental label`

Coordinate the expected output directory with the model-training owner before running the full dataset.

Do not train the affinity heads yourself.

Verify that:
- Every expected complex has an output.
- Embeddings are present and readable.
- No outputs have been assigned to the wrong complex.
- Failed complexes are explicitly recorded.

## 4. Perform molecular screening and comparisons

Use the pretrained predictions to produce the initial molecular analysis.

Investigate:

- WT EGFR versus mutant EGFR.
- Mutation-specific changes in predicted inhibitor interactions.
- Differences between inhibitor classes.
- Inhibitor ranking within each mutation profile.
- Predicted binding-related changes across resistance-associated mutations.

Focus particularly on:

- L858R.
- Exon 19 deletions.
- T790M.
- C797S.
- L858R/T790M/C797S.

Include compound comparisons involving osimertinib, gefitinib, erlotinib and other available inhibitors.

Do not fabricate missing combinations.

Use the documented Boltz score convention when interpreting predictions. Lower `affinity_pred_value` represents stronger predicted affinity under the documented log10(IC50 in μM) convention.

Keep `affinity_probability_binary` separate from the affinity value.

For every comparison, retain:
- Complex IDs.
- Mutation IDs.
- Compound IDs.
- Model version.
- Score values.
- Relevant experimental reference measurements.

## 5. Structural analysis

Analyse the available predicted and experimentally determined structures.

Investigate:

- EGFR kinase-domain binding pockets.
- Locations of resistance-associated mutations.
- Potential steric or local structural changes.
- Differences between WT and mutant structures.
- Ligand positioning and relevant protein–ligand contacts.
- Structural observations that may help explain differences in predicted affinity.

Use appropriate molecular visualisation tools such as PyMOL or ChimeraX.

Distinguish experimentally determined structures from computational predictions.

Do not present a predicted structural interaction as experimentally established.

## 6. Integrate the fine-tuned Boltz checkpoint later

Once the fine-tuned affinity checkpoint is provided by the model-training owner:

1. Run inference on the held-out validation and test complexes.
2. Compare specialised-model outputs with pretrained Boltz outputs.
3. Save predictions using the same complex identifiers.
4. Produce baseline-versus-specialised comparisons.
5. Identify improvements, regressions and mutation-specific limitations.

Do not change the dataset splits or use test labels to tune your analysis.

## 7. Required deliverables

```text
molecular_analysis/
│
├── baseline_predictions.csv
├── baseline_predictions/
│
├── embeddings/
│
├── screening_results.csv
├── wt_mutant_comparisons.csv
├── inhibitor_rankings.csv
├── affinity_landscape.csv
│
├── structural_analysis/
│   ├── pdb_files/
│   ├── visualisations/
│   └── structural_findings.md
│
├── specialised_predictions.csv
├── baseline_vs_finetuned.csv
├── comparison_plots/
│
└── MOLECULAR_ANALYSIS_REPORT.md
```

### Final report

Explain:
- What predictions were generated.
- How many complexes were successfully processed.
- Which mutations and compounds were covered.
- Which inhibitor interactions are potentially interesting.
- What structural patterns were observed.
- How pretrained and fine-tuned Boltz compare.
- What experimental validation remains necessary.

Your main responsibility is to produce trustworthy molecular predictions, structural observations and quantitative comparisons that the other team members can use.