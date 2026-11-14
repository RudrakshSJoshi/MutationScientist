# EGFR dataset loader — `egfr_dataset_loader.py`

A single, dependency-free Python module that **exposes the two training inputs** inside the
`EGFR_RESEARCH_DATASET` and sanity-checks them. It does not train anything — it loads, parses and
documents exactly what each downstream trainer consumes, so you can be certain of the format.

## Setup
Extract the zip so you have a folder `EGFR_RESEARCH_DATASET/` next to this script.
```bash
python egfr_dataset_loader.py                      # uses ./EGFR_RESEARCH_DATASET
python egfr_dataset_loader.py /path/to/EGFR_RESEARCH_DATASET --validate
python egfr_dataset_loader.py --describe           # print the exact input formats and exit
```
Only the Python standard library is used (`csv, json, re, pathlib`). Python 3.9+.

As a library:
```python
from egfr_dataset_loader import EGFRDataset
ds = EGFRDataset("EGFR_RESEARCH_DATASET")
ds.validate()          # [] means all good
ds.boltz               # Component 1
ds.llm                 # Component 2
```

---

## What the script contains (and what each piece means)

### `EGFRDataset` (top level)
Loads both components plus the **shared reference tables** that link them:
`mutations`, `compounds`, `measurements`, `references`. Methods:
- `.validate()` → list of problems (missing YAML/MSA files, unknown ids, empty fields). Empty = healthy.
- `.shared_keys()` → the `mutation_id` / `compound_id` overlap between the two components (the join).
- `.manifest` → the dataset's `DATASET_MANIFEST.json` (version + counts + caveats).

---

### Component 1 — `BoltzDataset` (Boltz-2 affinity fine-tuning)

**What it exposes.** One `BoltzComplex` per training example. The YAML it points to is *exactly*
what you feed to `boltz predict` in the `molecularinformatics/Boltz2_affinity` pipeline.

**Input format (per complex YAML):**
```yaml
version: 1
sequences:
  - protein: {id: A, sequence: <mutant EGFR amino-acid sequence>, msa: <path to .a3m>}
  - ligand:  {id: B, smiles: '<ligand SMILES>'}
properties:
  - affinity: {binder: B, value: <LABEL>}
```

**`BoltzComplex` fields:**
| field | meaning |
|---|---|
| `complex_id` | `COMPLEX_000001` … unique id |
| `split` | `train` / `validation` / `test` — **ligand-disjoint** (a ligand lives in one split only → scaffold-held-out) |
| `mutation_id` | `EGFR_*` → links to `mutations.csv` and to Component 2 |
| `compound_id` | `CMP_*` (named panel) or `BDB_*` (BindingDB ligand) → `compounds.csv` / `bindingdb_ligands.csv` |
| `sequence_id` | FASTA record id (== `mutation_id`) |
| `affinity_label` | **the training target** = `log10(IC50 in µM)` = `log10(IC50_nM) − 3`; **lower = stronger**. **NOT pIC50.** |
| `affinity_label_unit` | `log10(IC50_uM)` |
| `n_replicates` | how many raw measurements were averaged (in log space) into this one label |
| `measurement_ids` | source `MEAS_*` ids (provenance) |
| `yaml_path` | the Boltz input file to feed |
| `msa_path` | the precomputed MSA (`.a3m`) this complex uses (ColabFold/MMseqs2) |
| `protein_sequence`, `ligand_smiles` | parsed out of the YAML for convenience |

**Methods:** `.split("train"|"validation"|"test")`, `.all()`, iteration, `.counts()`.
Also: `.eligible_rows` = the full `boltz_compatible_dataset.csv` (18,189 eligible measurement rows
*before* replicate de-duplication — the 6,843 complexes are the de-duplicated version you train on);
`.val_names` = the validation complex names for the repo's `split_file` (also in `boltz2/val_names.txt`).

**Label helpers (module level):** `ic50_nM_to_label(nM)` and `label_to_ic50_nM(label)`.

**Why some data is excluded:** covalent inhibitors (osimertinib, silevertinib, afatinib, dacomitinib)
give time-dependent IC50 (not equilibrium) and are *not* in the eligible set — they're in the LLM
interpretation data instead. KD/Ki/EC50 and censored values are likewise excluded from this target.

---

### Component 2 — `LLMDataset` (MutationScientist LLM, SFT)

**What it exposes.** One `LLMExample` per SFT row. The model learns **INPUT = `prompt` → OUTPUT = `completion`**.

**Input format (upload CSV columns):**
`prompt, completion, task_type, mutation_id, profile_id, compound_id, evidence_ids, source_ids, review_status, annotation_confidence`
→ map **only** `prompt` (input) and `completion` (output); everything else is audit metadata.
The module exposes `AUTOSCIENTIST_COLUMN_MAPPING = {"prompt":"prompt","completion":"completion"}`.

**`LLMExample` fields:**
| field | meaning |
|---|---|
| `prompt` | the INPUT — self-contained (all numbers/context inline; the platform does not auto-inject metadata) |
| `completion` | the OUTPUT — the target answer |
| `task_type` | e.g. `experimental_interpretation`, `inhibitor_comparison`, `mutation_mechanism`, `assay_distinction`, `evidence_qa` |
| `mutation_id`, `compound_id` | link back to Component 1 / reference tables |
| `source_ids` | provenance → `REFERENCES.csv` / `Melis2026` / `UNIPROT_P00533` |
| `review_status` | `model_generated_grounded` (hand-built) **or** `teacher_generated_unverified_autochecked` (made by teacher-LLMs from real facts; every number machine-verified against source, but **not** human-reviewed) |
| `annotation_confidence` | qualitative confidence tag |
| `split` | `train` / `validation` / `test` — **mutation-held-out** (S768I, L861Q → test; T790M → validation) |

**Methods:** `.split(name)`, `.all()`, `.pairs(name)` (just `(prompt, completion)` tuples),
`.counts()`, `.meets_4b_floor()`. Extra assets: `.source_jsonl` (the 3 source sets + `teacher_generated`),
`.eval_questions` (independent eval), `.preference_pairs` (optional DPO).

**⚠️ 4B minimum-rows check (`.meets_4b_floor()`):** a 4B model (`gemma-3-4b-it`, `Qwen3.5-4B`) needs
**≥ 1,000 rows** in the uploaded SFT set. `sft_train` alone is **912 (short by 88)**. The loader's
recommendation: **upload `sft_train` + `sft_validation` (1,126 rows)** and keep `sft_test` (215) as an
external held-out eval. (Or re-split so train ≥ 1,000.)

---

## How the two components link
Both carry the **same stable ids**: `mutation_id` (`EGFR_*`) and `compound_id` (`CMP_*`/`BDB_*`).
`boltz2/complex_metadata.csv` is the join table: `complex_id → mutation_id + compound_id + affinity_label`.
Overlap in this build: **16 variants and ~354 compounds** appear in *both* components (`ds.shared_keys()`).

**Intended end-to-end flow:**
1. Fine-tune Boltz-2 on the 6,843 complexes → run it → get `affinity_pred_value` per `complex_id`.
2. Join that prediction by `(mutation_id, compound_id)` to the LLM, which was trained to *interpret*
   IC50-scale values.
3. At runtime the LLM reads the predicted value + evidence and writes the interpretation.
   (The explicit "interpret a real Boltz prediction" examples are the one piece that can only be
   generated *after* Boltz is trained and run — the join keys are already in place.)

## Counts in this build (printed by the CLI)
- **Boltz:** 6,843 complexes (train 5,515 / val 684 / test 644); 18,189 eligible rows; 16 variants.
- **LLM:** 1,341 examples (train 912 / val 214 / test 215); 101 hand-grounded + 1,240 teacher-generated.

## Caveats (carried from the dataset docs)
BindingDB IC50 are multi-lab/heterogeneous; covalency flagged by a SMILES heuristic; the 1,240
teacher-generated LLM rows are number-grounded but not human-reviewed (expert pass recommended);
not for clinical decisions.
