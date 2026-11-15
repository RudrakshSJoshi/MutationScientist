# MutationScientist

**Mutation-Aware Molecular Discovery and Evidence-Grounded Scientific Reasoning for EGFR-Driven Lung Cancer**

MutationScientist is a dual-model computational research system that combines EGFR-specialised protein–ligand prediction with a fine-tuned scientific language model. It investigates how cancer-associated mutations affect inhibitor interactions, connects predictions to experimental evidence, and generates traceable hypotheses for further validation.

**Research focus:** Computational oncology · EGFR inhibitor resistance · Molecular modelling · Scientific language models

**Models:** Boltz-2 (molecular structure and affinity) · Qwen3.5-4B (mutation-aware scientific reasoning)

---

## The problem

### A drug can work against a cancer-driving protein—and stop working after the protein mutates.

**EGFR** (epidermal growth factor receptor) is a receptor tyrosine kinase. Certain EGFR mutations drive a subset of **non-small-cell lung cancers (NSCLC)**. Targeted inhibitors can suppress EGFR signalling, but tumours may acquire additional mutations that change drug sensitivity and create resistance.

Consider **osimertinib**, a covalent EGFR inhibitor. Its mechanism involves the **C797** residue. A **C797S** substitution can disrupt the expected covalent interaction, providing a biologically established route to resistance. Understanding that mechanism is only the beginning: researchers also need to investigate which inhibitors remain promising, how predicted molecular interactions change, what experiments have actually been performed, and what remains uncertain.

Three problems make this difficult:

1. **Mutation-dependent molecular behaviour.** An inhibitor's predicted interaction with wild-type EGFR may not carry over to L858R, T790M, C797S, or compound mutants.
2. **Fragmented evidence.** Compound structures, protein sequences, biochemical measurements, cellular assays, and research papers are distributed across separate resources and use different measurement conventions.
3. **A gap between prediction and explanation.** Molecular models can estimate structures or affinity-related values, but do not automatically explain experimental discrepancies, resistance mechanisms, or which validation experiment to run next. General-purpose language models can produce fluent explanations without reliably grounding them in the relevant mutation, assay, or source.

> **Research question:** Can EGFR-specialised molecular prediction and mutation-aware scientific language modelling, connected through a shared evidence dataset, improve the investigation and prioritisation of inhibitors for acquired EGFR resistance?

**Scope:** MutationScientist is a computational *research and hypothesis-generation* tool. It does **not** establish clinical drug efficacy or recommend treatments.

## Our solution

MutationScientist connects two complementary models to a common, traceable EGFR research dataset:

| Component | Receives | Produces | Scientific role |
|---|---|---|---|
| **Boltz-2 molecular model** | Mutant EGFR protein sequence, ligand representation, and relevant molecular context | Predicted complex structure and affinity-related outputs | Investigate **how a mutation may affect protein–ligand interactions** |
| **MutationScientist LLM** | Mutation and compound context, experimental evidence, retrieved literature, and **actual** molecular predictions | Evidence-grounded interpretation, comparisons, caveats, and experimental hypotheses | Investigate **what the prediction means, why it might happen, and what should be tested** |
| **Evidence / retrieval layer** | Mutation IDs, compound IDs, queries, and provenance | Relevant measurements, annotations, and source records | Make interpretations **traceable and auditable** |

The models are **trained separately**, not as a single end-to-end differentiable network. Their integration occurs through **shared mutation and compound identifiers**, retrieved evidence, and molecular model outputs. The language model does not predict atomic coordinates or binding affinities on its own.

### Example research workflow

**Question:** *How might EGFR C797S affect osimertinib interactions, and which experiments would test the proposed resistance mechanism?*

1. Resolve the mutation and compound against curated records.
2. Retrieve available biochemical measurements, literature, and mutation annotations.
3. Obtain Boltz-2 predictions for appropriate wild-type and mutant protein–ligand inputs, **where available**.
4. Compare predicted structures and affinity-related values, preserving their score conventions.
5. Supply the **actual predictions and evidence** to MutationScientist.
6. Generate a structured report separating **established mechanisms**, **measured observations**, **model predictions**, and **unverified hypotheses**.
7. Suggest follow-up biochemical and cellular experiments rather than presenting a computational prediction as a clinical conclusion.

## What makes MutationScientist different

The contribution is **not** a new protein-folding architecture or a claim that an LLM can replace molecular simulation. It is a **mutation-centred research workflow** combining specialised modelling, shared scientific supervision, and evidence-aware interpretation.

**1. One research domain, two complementary representations.** The same EGFR mutation–inhibitor research space is represented as both **structured molecular examples** (protein sequences, ligand SMILES, measured activity) and **natural-language scientific tasks** (mechanism interpretation, assay distinctions, inhibitor comparison, evidence questions). This lets the system study molecular behaviour and communicate its scientific meaning without conflating the models' capabilities.

**2. Explicit cross-model provenance.** `mutation_id` and `compound_id` connect the molecular complexes to scientific examples and references. This makes it possible to inspect which biological context underlies an answer and which molecular prediction was actually used.

**3. Mutation-specialised language adaptation.** Rather than asking a generic LLM to improvise oncology expertise, we adapt a 4B language model on curated EGFR-specific question–answer examples, including resistance mechanisms, evidence interpretation, and experimental reasoning.

**4. Semantic, claim-level evaluation.** We evaluate generated scientific explanations by extracting **atomic scientific facts and claims**, rather than requiring exact token overlap with a reference response. This is useful because two scientifically equivalent explanations may use different wording.

**5. Resource-aware execution.** Data collection, parallel inference on constrained GPUs, affinity-head adaptation, and external molecular evaluation are organised as independent stages, allowing progress without a single large end-to-end training run.

These are **system-design and adaptation contributions**. Novel molecular discoveries or superior generalisation to unseen drug scaffolds require separate experimental evidence.

---

## System architecture

```text
ChEMBL / BindingDB / UniProt / PDB / PubMed
                    |
           Curate and reconcile
                    |
         Shared EGFR research data
           /        |         \
          /         |          \
   Boltz-2 input  LLM SFT input   Evidence index
          |         |                 |
   Affinity-head  Qwen3.5-4B         Retrieval
    adaptation      SFT               |
          |         |                 |
    Structures +    +-----------------+
   affinity scores            |
          +-------------------+
                    |
       MutationScientist analysis
                    |
       Evidence-grounded report
                    |
       Inhibitor comparison and
       experimental hypotheses
```

### What is actually shared?

The models do **not** train on an identical number of examples or share weights. The **Boltz-2 component has 6,843 protein–ligand complexes**, while the **LLM component has 1,341 instruction examples**. They share a curated biological domain and linking identifiers, not a one-to-one training sample mapping.

## The research dataset

We assembled EGFR-focused records from public scientific resources and associated literature. The curation process brings together mutation annotations, protein sequences, compounds, experimental measurements, molecular input files, and scientific instruction examples.

| Source | Contribution |
|---|---|
| [ChEMBL](https://www.ebi.ac.uk/chembl/) | Compound bioactivity and assay records |
| [BindingDB](https://www.bindingdb.org/) | Protein–ligand binding and inhibition measurements |
| [UniProt](https://www.uniprot.org/) | Reference EGFR sequence and protein annotations |
| [RCSB PDB](https://www.rcsb.org/) | Experimental biomolecular structures |
| [PubChem](https://pubchem.ncbi.nlm.nih.gov/) | Compound identifiers and molecular representations |
| [COSMIC](https://cancer.sanger.ac.uk/cosmic) | Cancer mutation context |
| [PubMed](https://pubmed.ncbi.nlm.nih.gov/) / [Europe PMC](https://europepmc.org/) | Primary literature and evidence metadata |

### Dataset at a glance

| Dataset component | Count |
|---|---:|
| Boltz-2 protein–ligand complexes | **6,843** |
| Eligible experimental measurement records (before replicate deduplication) | **18,189** |
| EGFR variants in Boltz component | **16** |
| Shared compounds | **~354** |
| MutationScientist SFT examples | **1,341** |
| Hand-grounded LLM examples | **101** |
| Teacher-generated, machine-checked LLM examples | **1,240** |

**Important:** The 18,189 measurements are not 18,189 independent complexes. Teacher-generated, automatically checked examples should not be treated as equivalent to independently human-verified scientific annotations.

#### Molecular split

| Training | Validation | Test | Total |
|---:|---:|---:|---:|
| 5,515 | 684 | 644 | **6,843** |

The dataset loader describes these as **ligand-disjoint** splits. Ligand-disjointness should not automatically be described as *scaffold-disjointness* without verifying scaffold grouping.

#### Language-model split

| Training | Validation | Test | Total |
|---:|---:|---:|---:|
| 912 | 214 | 215 | **1,341** |

The supplied split design is **mutation-held-out**: S768I and L861Q are assigned to test, and T790M to validation. This is a more demanding setting than randomly splitting near-duplicate scientific questions, although a complete leakage audit is still necessary.

### Data format and cross-model joins

The repository loader is [`egfr_dataset_loader.py`](egfr_dataset_loader.py), exposing `EGFRDataset.boltz` and `EGFRDataset.llm` alongside shared mutation, compound, measurement, and reference tables.

```python
from egfr_dataset_loader import EGFRDataset

ds = EGFRDataset("EGFR_RESEARCH_DATASET/EGFR_RESEARCH_DATASET")
print(ds.boltz.counts())
print(ds.llm.counts())
print(ds.shared_keys())
print(ds.validate())
```

For the LLM, **only** `prompt` and `completion` form the supervised training pair. Fields such as `mutation_id`, `compound_id`, `source_ids`, `review_status`, and `annotation_confidence` support provenance, dataset auditing, and evaluation; they are not automatically extra model inputs.

---

## Model 1: Boltz-2 molecular prediction

[Boltz-2](https://www.boltz.com/boltz2) is an open biomolecular foundation model for joint structure and affinity-related prediction. We use the community [Boltz-2 affinity fine-tuning implementation](https://github.com/molecularinformatics/Boltz2_affinity) to adapt the **affinity heads** to EGFR–inhibitor examples. This approach is distinct from retraining the entire structure-prediction network.

### Molecular input

Each complex encodes a mutant EGFR protein sequence, a ligand molecular representation, and an experimental label. A simplified example is:

```yaml
version: 1
sequences:
  - protein:
      id: A
      sequence: "<mutant EGFR amino-acid sequence>"
      msa: "<path to alignment.a3m>"
  - ligand:
      id: B
      smiles: "<ligand SMILES>"
properties:
  - affinity:
      binder: B
      value: <experimental label>
```

The dataset's documented affinity label is:

\[
 y = \log_{10}(IC_{50}\;[\mu\mathrm{M}])
   = \log_{10}(IC_{50}\;[\mathrm{nM}]) - 3
\]

**Lower values indicate lower IC50 (greater apparent inhibitory potency in the corresponding assay).** This is **not** pIC50. `affinity_pred_value` and `affinity_probability_binary` are different outputs: one is a continuous affinity-related prediction, the other a binder-probability prediction.

### Molecular adaptation and validation

The intended comparison is between pretrained and EGFR-adapted affinity heads on **held-out experimental labels**, using MAE, RMSE, Spearman correlation, and mutation-/compound-level ranking analyses. Structural visualisation helps inspect predictions, but **an affinity-head loss improvement alone does not prove better protein folding**.

**Molecular evaluation status:** The project reports a loss change of **0.3412 → 0.0595**, equivalent to an **82.56% decrease** or approximately **5.73× lower numeric loss**. The precise loss function, split, and checkpoint provenance have not yet been supplied, so this result is shown as a **reported optimisation metric**, *not* a verified test-set affinity MAE or proof of a 5.73× physical affinity improvement. A log-transformed target does not make the loss itself a base-10 logarithm.

## Model 2: MutationScientist language model

**Base model:** Qwen3.5-4B. **Adaptation:** supervised fine-tuning (QLoRA-based workflow). **Domain:** EGFR mutations, inhibitor resistance, experimental evidence, and scientific reasoning.

### Why a language model belongs in a molecular discovery system

Molecular predictions answer questions such as *“What structure or affinity-related value does the model predict for this protein–ligand pair?”* A scientist needs additional answers:

- **Mechanism:** Why might C797S interfere with an inhibitor's known binding mechanism?
- **Evidence:** Which observations support the explanation, and from which assay or publication?
- **Comparison:** Does a measured IC50 change support the same interpretation as the structural prediction?
- **Uncertainty:** Is a statement experimentally established, predicted, or merely a hypothesis?
- **Next experiment:** Which biochemical or cellular experiment would distinguish competing explanations?

These are **scientific interpretation tasks**. Language modelling is useful because much of the relevant knowledge exists as research prose, assay descriptions, tables, and contextual explanations—not solely as 3D coordinates.

### How the training works

Each training example is a self-contained **instruction → scientific answer** pair:

```text
INPUT / prompt
  EGFR mutation + inhibitor + available measurements/context
  → Ask for a resistance explanation, evidence comparison,
    assay interpretation, or validation experiment.

TARGET / completion
  A structured scientific explanation grounded in the supplied
  context, with appropriate distinctions and uncertainty.
```

The fine-tuning objective is **next-token supervised cross-entropy**, encouraging the model to generate domain-appropriate target explanations given the prompt. This is **not reinforcement learning** and does not directly optimise a molecular affinity score.

The scientific tasks include:

| Task | What the LLM learns to do |
|---|---|
| Mutation classification | Distinguish activating, resistance-associated, and compound variants |
| Mutation mechanism | Explain mutation-dependent biochemical mechanisms |
| Inhibitor comparison | Compare evidence across candidate EGFR inhibitors |
| Experimental interpretation | Interpret experimental observations and limitations |
| Assay distinction | Avoid conflating biochemical, cellular, and binding measurements |
| Evidence QA | Recover specific facts from scientific context |
| Resistance interpretation | Relate mutations and inhibitor mechanisms to resistance hypotheses |

### Why this is not merely autoregressive text generation

The model **is** an autoregressive language model, but the *research task* is not open-ended prose generation. It is **domain-conditioned interpretation**: the system provides mutation-specific context, retrieved evidence, and actual Boltz outputs, and the model is trained to respond with scientifically meaningful distinctions. The benefit comes from the **supervised task distribution and evidence context**, not from assuming the LLM has learned the physics of protein folding.

At inference, a report should explicitly distinguish:

> **Established:** C797S changes a residue involved in osimertinib's covalent binding mechanism.  
> **Observed:** A particular experiment reports a particular assay result (with source and units).  
> **Predicted:** Boltz-2 returns a structure or affinity-related value for the specified input.  
> **Hypothesis:** An alternative inhibitor may merit testing against the mutant.  
> **Validation:** Test the hypothesis with suitable biochemical and cellular assays.

**Cross-model boundary:** We do not claim that natural-language supervision directly changes Boltz-2 folding or affinity-head weights. Demonstrating such an effect would require an explicit coupling mechanism and controlled ablation.

### Semantic evaluation: scientific facts rather than token overlap

A correct answer can be phrased many ways. BLEU-style exact word overlap can penalise valid paraphrases and overlook confidently incorrect scientific claims. Our teacher-model evaluation instead decomposes answers into **atomic reference facts** and **generated scientific claims**, classifying whether facts were recovered, omitted, or contradicted and whether generated claims were supported, unsupported, or contradictory.

The teacher provides a **semantic scoring rubric**, analogous to a reward signal for evaluation; it is **not** evidence that reinforcement learning was used. The project reports **Cohen's κ = 0.83** for evaluator agreement; the compared annotators, sample size, and agreement protocol must be documented before interpreting that figure as validated scientific accuracy.

---

## Experimental results

### Language-model evaluation

The current Claude evaluation compares **pretrained Qwen3.5-4B outputs against fine-tuned model outputs used as the reference** on **215 test prompts**. This measures **agreement with the selected fine-tuned reference**, not independent clinical or factual correctness of the fine-tuned model.

| Metric | Pretrained vs fine-tuned reference | Gap to reference self-match |
|---|---:|---:|
| **Macro factual precision** | **55.61%** | 44.39 percentage points |
| **Macro factual recall** | **46.95%** | 53.05 percentage points |
| **Macro factual F1** | **48.05%** | 51.95 percentage points |
| Micro factual precision | 55.68% | — |
| Micro factual recall | 46.81% | — |
| Micro factual F1 | 50.86% | — |
| Mean unsupported-claim rate | 38.76% | — |
| Mean contradiction rate | 5.63% | — |

**Interpretation:** The pretrained model misses a substantial portion of the atomic content in the selected fine-tuned reference answers. The gaps above are **distances to self-agreement**, not independently established percentage-point gains in scientific accuracy.

#### Atomic fact audit (215 prompts)

| Reference facts | Count | Generated claims | Count |
|---|---:|---|---:|
| Total reference facts | 1,175 | Total generated claims | 977 |
| Correctly recalled | 550 | Supported | 544 |
| Missing | 602 | Unsupported | 382 |
| Contradicted | 23 | Contradicted | 51 |

**Unsupported** means not supported by the selected reference; it does not necessarily mean false in the broader scientific literature.

#### Performance by scientific task

| Task | Test prompts | Macro precision | Macro recall | Macro F1 |
|---|---:|---:|---:|---:|
| Inhibitor comparison | 59 | 79.69% | 53.40% | **61.25%** |
| Experimental interpretation | 82 | 54.80% | 49.88% | 50.05% |
| Assay distinction | 31 | 50.41% | 44.91% | 45.09% |
| Mutation mechanism | 11 | 41.26% | 54.05% | 43.70% |
| Resistance interpretation | 9 | 33.89% | 33.44% | 29.52% |
| Mutation classification | 8 | 20.42% | 24.58% | 21.58% |
| Evidence QA | 15 | 18.33% | 24.56% | **19.80%** |

The largest pretrained-to-reference disagreements occur in **evidence QA** and **mutation classification**, suggesting these are useful priorities for independent scientific validation. Task sample sizes differ substantially; the eight-example mutation-classification result should not be treated as a precise population estimate.

### Language-model held-out loss

| Model | Reported test loss |
|---|---:|
| Pretrained Qwen3.5-4B | **2.23768** |
| Fine-tuned Qwen3.5-4B | **0.19399** |
| **Relative reduction** | **91.33%** |

This is a **teacher-forced, token-weighted next-token prediction loss** comparison on the supplied test completions. It supports improved modelling of the reference text distribution, but is **not** a direct measurement of binding affinity, mutation classification accuracy, or independent factual correctness. Test-set independence and provenance should be audited before making broader generalisation claims.

### Molecular optimisation result

| Metric | Before | After | Relative reduction |
|---|---:|---:|---:|
| Reported Boltz-2 loss (definition pending) | 0.3412 | 0.0595 | **82.56%** |

**Pending verification:** Please supply the exact loss function, whether this is training/validation/test, and corresponding baseline/fine-tuned checkpoints. Until then, the README does **not** claim improved held-out molecular accuracy, protein folding, or inhibitor ranking from this number alone.

---

## Engineering under resource constraints

The project was developed with limited compute and an unusually fragmented domain dataset:

- **Data scarcity and assembly:** Approximately **five hours** spent collecting, joining, and checking task-specific public measurements and literature-derived information.
- **GPU constraints:** Parallel scripts and distributed inference were used to make progress on limited GPU resources, including **dual NVIDIA T4** inference workflows.
- **Molecular training:** **NVIDIA A30** shell access was used for the Boltz-2 fine-tuning workflow, including the practical challenge of preparing sequences, ligands, alignments, and embeddings under resource limits.
- **External molecular tooling:** **Tamarind Bio** was used for molecular modelling/evaluation workflows. The exact completed jobs and verified comparative outcomes should be linked before claiming a particular downstream improvement.
- **Independent modules:** Data curation, model training, evidence retrieval, molecular inference, and the frontend were developed as separable workstreams so one blocked dependency did not halt the entire system.

The engineering lesson is central to the project: **domain specialisation can be approached through curated data, selective adaptation, and staged evaluation rather than unrestricted compute**.

## Repository structure

The following is a **condensed representation of the uploaded repository tree**. Thousands of generated complex YAMLs and alignment files are intentionally omitted.

```text
.
├── README.md
├── requirements.txt
├── egfr_dataset_loader.py             # Shared data loader and integrity checks
├── EGFR_LOADER_README.md
├── boltz-finetune.ipynb               # Molecular fine-tuning notebook
├── task_description.md
├── anam-explainer/                   # Voice-based explainer service
│   ├── server.js
│   ├── model.js
│   ├── persona.js
│   ├── public/
│   └── tools/
├── application/                      # Application and service integration
│   ├── app.py
│   ├── pages/mutation_scientist.py
│   ├── services/evidence_service.py
│   ├── services/llm_service.py
│   └── tests/
├── EGFR_RESEARCH_DATASET/
│   └── EGFR_RESEARCH_DATASET/
│       ├── DATASET_MANIFEST.json
│       ├── REFERENCES.csv
│       ├── boltz2/
│       │   ├── complex_metadata.csv
│       │   ├── boltz_compatible_dataset.csv
│       │   ├── val_names.txt
│       │   └── complexes/{train,validation,test}/
│       ├── curated/
│       │   ├── mutations.csv
│       │   ├── mutation_profiles.csv
│       │   ├── compounds.csv
│       │   ├── affinity_measurements.csv
│       │   ├── biological_evidence.csv
│       │   └── cellular_assays.csv
│       └── mutation_scientist/
│           ├── sft_train.csv
│           ├── sft_validation.csv
│           ├── sft_test.csv
│           ├── mutation_understanding.jsonl
│           ├── experimental_evidence_reasoning.jsonl
│           ├── research_reasoning.jsonl
│           ├── teacher_generated.jsonl
│           ├── eval_questions.jsonl
│           └── preference_pairs.jsonl
├── scientific_evidence/              # Evidence schema, retrieval, graph benchmark
│   ├── evidence_api.py
│   ├── evidence_schema.json
│   ├── evidence_database/
│   ├── evidence_index/
│   ├── retriever/
│   └── evaluation/
├── product/backend/                  # Product backend
│   ├── main.py
│   ├── requirements.txt
│   └── run.sh
└── WIN/                              # Demo assets and experiment evidence
    ├── deck/index.html
    ├── demo-script.md
    ├── run-of-show.md
    ├── evidence/
    └── visuals/hero.png
```

The uploaded tree also contains additional application pages, service modules, and molecular assets. Consult the corresponding subdirectory READMEs for component-specific details.

## Getting started

### Requirements

- Python environment compatible with the repository's `requirements.txt`
- Additional dependencies for Boltz-2 and the relevant model checkpoints where molecular inference is required
- Node.js for the optional `anam-explainer` service
- Access to model/API credentials for externally hosted services, configured privately (never committed)

```bash
# From repository root
python -m venv .venv
source .venv/bin/activate       # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Inspect dataset input formats
python egfr_dataset_loader.py --describe

# Check the linked research dataset
python egfr_dataset_loader.py EGFR_RESEARCH_DATASET/EGFR_RESEARCH_DATASET --validate
```

### Application and supporting services

The repository contains a Python application at [`application/app.py`](application/app.py), a backend at [`product/backend/main.py`](product/backend/main.py), and a Node service at [`anam-explainer/server.js`](anam-explainer/server.js). Their precise runtime commands and environment variables should be taken from their respective local READMEs and configuration files; the directory listing alone does not establish which service is the canonical entry point.

### Interactive demo

The repository includes [`WIN/deck/index.html`](WIN/deck/index.html) and supporting demo documentation under [`WIN/`](WIN/). Open the deck in a browser or serve the repository locally if its assets require HTTP access.

## Evaluation and reproducibility checklist

Before interpreting a new model comparison, verify:

- **Split integrity:** Mutation-held-out language tests and ligand-held-out molecular tests remain untouched by training or model selection.
- **Molecular targets:** IC50, Ki, Kd, and cellular viability measurements are never silently merged into interchangeable targets.
- **Molecular metrics:** Compare models on the **same held-out examples** and report MAE, RMSE, rank correlation, and uncertainty.
- **Teacher evaluation:** Report the reference source, prompt rubric, teacher model, atomic-fact extraction procedure, and any human agreement audit.
- **Reference dependence:** If fine-tuned answers are used as reference, call the result **reference alignment**, not independently verified factual accuracy.
- **Covalent inhibitors:** Interpret osimertinib and other irreversible inhibitors with appropriate kinetic caveats.
- **Scientific provenance:** Trace claims back to measurement IDs, mutation IDs, compound IDs, and primary sources.

## Limitations and next steps

MutationScientist does **not** equate predicted affinity with clinical response. Protein–ligand models may be sensitive to protein construct, protonation, assay conditions, and covalent binding mechanisms. Language-model explanations can remain unsupported even when fluent; synthetic SFT examples require independent review. Ligand-disjoint evaluation is valuable but does not automatically establish performance on unseen chemical scaffolds or unseen resistance mechanisms.

The most important next experiments are: **(i)** complete a controlled Boltz-2 baseline-vs-adapted test-set comparison, **(ii)** score both language models against **independently reviewed** EGFR answers, **(iii)** evaluate retrieval grounding and citation fidelity, and **(iv)** test mutation–inhibitor hypotheses against appropriately matched biochemical and cellular evidence.

## References and acknowledgements

- [Boltz-2 official implementation](https://github.com/jwohlwend/boltz) · [Boltz-2 research preprint](https://doi.org/10.1101/2025.06.14.659707)
- [Boltz-2 affinity-head fine-tuning](https://github.com/molecularinformatics/Boltz2_affinity)
- [Adaption Labs / AutoScientist](https://adaptionlabs.ai/) · [Documentation](https://docs.adaptionlabs.ai/)
- [ChEMBL](https://www.ebi.ac.uk/chembl/) · [BindingDB](https://www.bindingdb.org/) · [RCSB PDB](https://www.rcsb.org/) · [UniProt](https://www.uniprot.org/) · [PubMed](https://pubmed.ncbi.nlm.nih.gov/)

See [`EGFR_RESEARCH_DATASET/EGFR_RESEARCH_DATASET/REFERENCES.csv`](EGFR_RESEARCH_DATASET/EGFR_RESEARCH_DATASET/REFERENCES.csv) for dataset-level provenance.

