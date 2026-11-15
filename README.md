# MutationScientist

MutationScientist is a research tool for investigating how EGFR mutations affect inhibitor interactions in non-small-cell lung cancer. It brings together experimental assay evidence, structural analysis and a Boltz-2 workflow for protein–ligand prediction and affinity-head fine-tuning.

## Run the evidence app

From the repository root, use Python 3.10 or later with SQLite FTS5.

```sh
python3 -m scientific_evidence.retriever.build
python3 -m application.app
```

Open [the local app](http://127.0.0.1:8765/) and try **Why does gefitinib lose potency against T790M?** The report shows the matched EGFR genotype, compound, assay conditions and sources. See the [application guide](application/README.md) for graph search and model endpoint setup.

## Explore the project

| Work | Where to start |
| --- | --- |
| Project objectives and research questions | [Project brief](task_description.md) |
| Curated EGFR measurements, sequences and Boltz inputs | [Dataset](EGFR_RESEARCH_DATASET/) · [Dataset loader](EGFR_LOADER_README.md) |
| Crystal structure comparisons, dataset audit and prediction status | [Molecular analysis report](molecular_analysis/MOLECULAR_ANALYSIS_REPORT.md) |
| Boltz-2 affinity-head training workflow | [Fine-tuning notebook](boltz-finetune.ipynb) |
| Scientific language model training | [Training guide](EGFR_TRAINING/README.md) |
| Source-linked evidence retrieval | [Evidence code](scientific_evidence/) |

The molecular dataset contains **6,843 EGFR–ligand complexes** in predefined training (5,515), validation (684) and test (644) splits. The molecular analysis report records coverage, assay conditions and chemical identities shared across splits. Experimental IC50 measurements, deposited crystal structures and Boltz-2 predictions each have their own provenance.

## Team

| Person | Team member | Responsibility |
| --- | --- | --- |
| 1 | [@RudrakshSJoshi](https://github.com/RudrakshSJoshi) | Model training |
| 2 | [@amdrwn](https://github.com/amdrwn) | Molecular analysis and structural comparisons |
| 3 | [@VictorLimouzi](https://github.com/VictorLimouzi) | Scientific evidence, retrieval and validation |
| 4 | [@yi4nnis](https://github.com/yi4nnis) | Application and system integration |
