# MutationScientist
## Mutation-Aware Molecular Discovery and Scientific Reasoning for EGFR-Driven Lung Cancer

**Project category:** AI for Biomedical Research / Computational Drug Discovery  
**Research area:** Oncology, Molecular Modelling, Protein–Ligand Interactions and Scientific Language Models  
**Target disease:** EGFR-driven Non-Small-Cell Lung Cancer (NSCLC)

---

# 1. Project Overview

MutationScientist is a two-model computational research system designed to investigate mutation-dependent drug interactions and acquired resistance in EGFR-driven non-small-cell lung cancer.

The project combines two specialised AI models:

1. **Boltz-2:** A biomolecular foundation model used to predict protein–ligand structures and binding-affinity-related properties. We will use an existing affinity fine-tuning implementation to specialise its affinity prediction heads on experimentally characterised EGFR–inhibitor interactions.
2. **MutationScientist LLM:** A language model fine-tuned through Adaption AutoScientist to understand EGFR mutations, interpret experimental evidence, reason about inhibitor resistance and explain molecular predictions.

The two models serve different purposes. Boltz-2 performs molecular prediction, while the language model provides biological interpretation and evidence-grounded scientific reasoning.

The overall objective is to build a system that can investigate an EGFR mutation–inhibitor combination, compare predicted molecular interactions, retrieve supporting scientific evidence and produce a structured research report identifying potentially interesting inhibitors and experiments for further investigation.

## 1.1 Research question

**Can mutation-specialised molecular affinity modelling, combined with an evidence-grounded scientific language model, improve the interpretation and prioritisation of inhibitors for acquired EGFR resistance in NSCLC?**

Rather than treating molecular prediction and scientific interpretation as separate problems, we aim to combine them into a single research workflow.

# 2. Biological Problem

EGFR (Epidermal Growth Factor Receptor) is a receptor tyrosine kinase involved in cellular signalling. Specific EGFR mutations can drive tumour growth and influence sensitivity to targeted inhibitors.

Although EGFR inhibitors can initially be effective, acquired resistance can emerge through additional mutations and other molecular mechanisms.

We will investigate mutation-dependent changes in EGFR–inhibitor interactions, focusing on variants including:

| Mutation | Research relevance |
|---|---|
| Wild-type EGFR | Reference protein for comparisons |
| L858R | Activating mutation |
| Exon 19 deletions | Important activating mutation class |
| T790M | Established resistance-associated gatekeeper mutation |
| C797S | Alters the cysteine-dependent covalent binding mechanism of osimertinib |
| G719X | Less common activating mutation class |
| L861Q | Activating mutation |
| S768I | Uncommon EGFR mutation |
| L858R/T790M/C797S | Compound resistance-associated mutation profile |

We will also investigate other experimentally characterised mutation combinations where suitable data are available.

The compound library includes established and investigational EGFR inhibitors:

- Gefitinib
- Erlotinib
- Afatinib
- Dacomitinib
- Osimertinib
- BLU-945
- JBJ-09-063
- Other experimentally characterised EGFR inhibitors discovered through the dataset.

An important distinction is that not all mutations have the same biological significance, and not every inhibitor has experimental measurements against every mutation. The analysis will be restricted to combinations supported by the available data.

# 3. Models and Technologies

## 3.1 Model 1 — Boltz-2: Molecular Structure and Affinity Prediction

**Model:** Boltz-2

**Official model website:**  
https://www.boltz.com/boltz2

**Official GitHub repository:**  
https://github.com/jwohlwend/boltz

**Research paper:**  
https://doi.org/10.1101/2025.06.14.659707

### What Boltz-2 does

Boltz-2 is an open-source biomolecular foundation model that jointly models molecular structures and protein–ligand binding-affinity-related properties.

It accepts biomolecular inputs such as protein sequences and small-molecule ligands and can produce:

- Predicted protein–ligand complex structures.
- Binding-affinity-related predictions.
- Predicted binder probabilities.
- Structural information useful for molecular analysis.

Its affinity outputs include:

- `affinity_pred_value`: a predicted affinity-related value.
- `affinity_probability_binary`: a predicted probability that the ligand is a binder.

These outputs have different purposes and must not be conflated.

The documented `affinity_pred_value` convention is log10(IC50 in μM), where lower predicted values indicate stronger binding. The binary probability is a separate binder-likelihood prediction.

### How we will specialise Boltz-2

We will use the following community fine-tuning implementation:

**Boltz-2 affinity fine-tuning repository:**  
https://github.com/molecularinformatics/Boltz2_affinity

**Fine-tuning documentation:**  
https://github.com/molecularinformatics/Boltz2_affinity/blob/main/docs/affinity_finetuning.md

This implementation provides an affinity-head fine-tuning workflow.

An important technical distinction: this is not full end-to-end retraining of Boltz-2. The documented approach freezes the structure-prediction modules and trains the affinity prediction heads using embeddings generated from pretrained Boltz-2.

### Our specialisation objective

We will use experimentally labelled EGFR–inhibitor complexes to adapt the affinity prediction component to the EGFR research domain.

The process is:

1. Provide EGFR protein sequences containing the relevant mutations.
2. Provide inhibitor SMILES representations.
3. Associate the protein–ligand complex with an experimentally supported affinity label.
4. Generate pretrained Boltz-2 embeddings.
5. Fine-tune the affinity heads using the supplied experimental data.
6. Compare predictions from pretrained and specialised checkpoints.

The intended outcome is an EGFR-specialised affinity prediction model that can be evaluated on held-out mutation–ligand combinations.

**Scientific caveat:** predicted binding affinity is not equivalent to enzyme inhibition, cancer-cell killing or clinical efficacy. Covalent inhibitors also present additional challenges because irreversible binding kinetics are not fully represented by conventional affinity measurements.

---

## 3.2 Model 2 — MutationScientist LLM: Scientific Interpretation and Reasoning

**Training platform:** Adaption Labs  
**Platform:** https://adaptionlabs.ai/

**AutoScientist application:**  
https://adaptionlabs.ai/app/autoscientist

**Documentation:**  
https://docs.adaptionlabs.ai/

**AutoScientist overview:**  
https://docs.adaptionlabs.ai/autoscientist/overview

**API documentation:**  
https://docs.adaptionlabs.ai/api/

Unlike Boltz-2, this component is a language model. We will select a base language model from the models currently supported by Adaption AutoScientist.

The exact base-model identifier will be selected from Adaption's live supported-model catalogue rather than assumed in advance:

https://docs.adaptionlabs.ai/api/resources/autoscientist

### What the LLM will do

MutationScientist will be specialised to:

- Explain EGFR mutations and their molecular changes.
- Explain established resistance mechanisms.
- Understand EGFR inhibitor classes and mechanisms.
- Interpret experimental affinity and inhibition measurements.
- Compare mutation-specific experimental findings.
- Interpret actual Boltz prediction outputs when supplied.
- Retrieve and summarise relevant scientific evidence.
- Generate testable molecular hypotheses.
- Suggest appropriate biochemical and cellular validation experiments.
- Clearly communicate uncertainty and limitations.

### How we will fine-tune it

The model will be trained using curated scientific instruction/completion examples from the EGFR dataset.

Three primary categories of data will be used:

**A. Mutation understanding**

Examples teaching the LLM about amino-acid substitutions, EGFR domains, activating mutations, compound mutations and resistance mechanisms.

**B. Experimental evidence reasoning**

Examples involving real biochemical measurements, inhibitor sensitivity, assay interpretation, experimental comparisons and published research findings.

**C. Scientific reasoning and experiment design**

Examples asking the model to formulate evidence-backed hypotheses, identify missing information, evaluate alternative explanations and propose validation experiments.

The training format will use:

`prompt → completion`

Only the `prompt` and `completion` fields provide the essential supervised training signal. Other fields retain provenance and auditing information.

### Adaption training workflow

We intend to use AutoScientist's instruction-training workflow for supervised fine-tuning (SFT).

The platform can optimise the training recipe, train a model and evaluate it iteratively.

Preference alignment using chosen/rejected responses may be investigated as a subsequent step, subject to suitable data and platform requirements.

### How it connects to Boltz-2

The LLM will not directly replace the molecular model or be expected to independently calculate binding affinity.

Instead, it will receive:

- Mutation information.
- Compound information.
- Actual Boltz prediction outputs.
- Relevant experimental measurements.
- Retrieved scientific literature.

It will then interpret these results and generate a structured explanation.

This is output-conditioned scientific interpretation: the LLM learns to reason over supplied molecular predictions, rather than sharing Boltz-2's internal weights or representations.

---

# 4. Shared EGFR Research Dataset

Both model-training pipelines use a common curated research dataset.

The dataset is organised into linked biological, molecular, experimental and language-model components.

**Dataset directory:** `EGFR_RESEARCH_DATASET/`

**Dataset loader:** `egfr_dataset_loader.py`

The loader exposes the two model-training inputs through:

- `EGFRDataset.boltz`
- `EGFRDataset.llm`

It also provides shared mutation and compound identifiers, metadata and basic integrity checks.

## 4.1 Data sources

| Database | Role in the project | URL |
|---|---|---|
| ChEMBL | EGFR inhibitor activity and experimental assays | https://www.ebi.ac.uk/chembl/ |
| BindingDB | Protein–ligand affinity measurements | https://www.bindingdb.org/ |
| RCSB PDB | Experimental protein and ligand structures | https://www.rcsb.org/ |
| UniProt | EGFR sequence and reference isoform | https://www.uniprot.org/ |
| COSMIC | Somatic cancer mutation information | https://cancer.sanger.ac.uk/cosmic |
| PubMed | Primary scientific literature | https://pubmed.ncbi.nlm.nih.gov/ |
| Europe PMC | Literature records and metadata | https://europepmc.org/ |
| PubChem | Compound identity and SMILES | https://pubchem.ncbi.nlm.nih.gov/ |

## 4.2 Current dataset summary

According to the supplied dataset loader:

<text> </text>

| Component | Current size |
|---|---:|
| Boltz protein–ligand complexes | 6,843 |
| Eligible experimental measurement rows | 18,189 |
| EGFR mutation variants in Boltz component | 16 |
| Compounds shared across components | Approximately 354 |
| LLM SFT examples | 1,341 |
| Hand-grounded LLM examples | 101 |
| Teacher-generated, machine-checked examples | 1,240 |

### Boltz dataset splits

| Split | Complexes |
|---|---:|
| Training | 5,515 |
| Validation | 684 |
| Test | 644 |
| **Total** | **6,843** |

The supplied loader describes these splits as ligand-disjoint, so a ligand is assigned to only one split.

There are 18,189 compatible measurement rows before replicate deduplication. These are not 18,189 independent complexes.

### LLM dataset splits

| Split | Examples |
|---|---:|
| Training | 912 |
| Validation | 214 |
| Test | 215 |
| **Total** | **1,341** |

The LLM split is mutation-held-out.

S768I and L861Q are allocated to test, while T790M is allocated to validation according to the supplied loader documentation.

### Data-quality consideration

Of the LLM examples:

- 101 are hand-grounded.
- 1,240 are teacher-generated and machine-checked, but not human-reviewed.

We will therefore conduct an additional scientific audit rather than treating all generated examples as equally verified.

The loader also reports that the training split alone contains fewer than its stated 1,000-row minimum for a 4B SFT workflow. This platform requirement must be checked against the selected live Adaption model before deciding how to prepare the upload. The validation set should not be silently absorbed into training.

---

# 5. Overall System Architecture

The system consists of three connected information layers.

### Layer 1 — Molecular prediction

Boltz-2 receives EGFR protein sequences and inhibitor molecular representations.

It generates protein–ligand structural predictions and affinity-related outputs.

### Layer 2 — Scientific evidence

The evidence retrieval system indexes the curated mutation annotations, experimental measurements and scientific literature.

It retrieves relevant information using mutation IDs, compound IDs and biological context.

### Layer 3 — Scientific interpretation

MutationScientist receives the molecular predictions and retrieved evidence.

It generates a scientific report that separates:

- Established biological mechanisms.
- Experimental observations.
- Computational predictions.
- Hypotheses requiring validation.

### End-to-end architecture

```text
                EGFR RESEARCH DATASET
                         |
             +-----------+-----------+
             |                       |
             v                       v
       PRETRAINED BOLTZ-2       BIOLOGICAL EVIDENCE
             |                       |
      EGFR protein + ligand     Literature retrieval
             |                  Experimental findings
             v                  Mutation annotations
       STRUCTURE AND                 |
       AFFINITY OUTPUTS              |
             |                       |
             +-----------+-----------+
                         |
                         v
              MUTATIONSCIENTIST LLM
                 (Adaption SFT)
                         |
                         v
              EVIDENCE-GROUNDED
               SCIENTIFIC REPORT
                         |
                         v
              MUTATION EXPLORER
              INHIBITOR COMPARISON
              STRUCTURAL ANALYSIS
              EXPERIMENTAL HYPOTHESES
```

The application will provide the interface for selecting mutations and inhibitors, viewing molecular predictions, inspecting references and generating reports.

---

# 6. Team Responsibilities

The project is divided into four independently owned workstreams.

## Person 1 — Model Training Lead

**Responsible models:** Boltz-2 and MutationScientist LLM.

Responsibilities:

- Fine-tune the Boltz-2 affinity prediction heads.
- Fine-tune the selected Adaption-supported LLM.
- Manage training configurations and checkpoints.
- Compare pretrained versus specialised models.
- Perform model-level evaluation.
- Provide the inference interfaces and checkpoints to the application developer.

Main deliverables:

- Fine-tuned Boltz-2 affinity checkpoint.
- Fine-tuned MutationScientist checkpoint.
- Training logs and evaluation results.
- Baseline-versus-fine-tuned model comparisons.

## Person 2 — Molecular Inference and Structural Analysis

**Responsible model:** Pretrained and subsequently fine-tuned Boltz-2 inference.

Responsibilities:

- Validate and process supplied Boltz complex inputs.
- Generate pretrained Boltz-2 predictions.
- Generate embeddings required by affinity-head fine-tuning.
- Provide the processed inference outputs to Person 1.
- Perform mutation-specific molecular screening.
- Compare WT and mutant EGFR predictions.
- Analyse inhibitor rankings.
- Generate structural visualisations.
- Compare pretrained and fine-tuned outputs once Person 1 provides the checkpoint.

Main deliverables:

- Baseline molecular predictions.
- Embeddings.
- Screening results.
- WT-versus-mutant comparisons.
- Structural visualisations.
- Molecular analysis report.

## Person 3 — Scientific Evidence, RAG and Validation

**Responsible system:** Biological evidence retrieval and independent scientific evaluation.

Responsibilities:

- Build the evidence retrieval system.
- Index mutation annotations, inhibitor information and literature.
- Return traceable references for mutation–inhibitor queries.
- Audit teacher-generated language-model examples.
- Build an independent scientific evaluation benchmark.
- Establish criteria for assessing evidence grounding and scientific correctness.
- Validate the final model's explanations against experimental findings.

Main deliverables:

- Evidence retrieval system.
- Structured evidence API.
- Scientific evaluation benchmark.
- Dataset audit.
- Scientific validation report.

## Person 4 — Application and System Integration

**Responsible system:** MutationScientist application.

Responsibilities:

- Build the research interface.
- Implement mutation and inhibitor selection.
- Display Boltz molecular predictions.
- Display WT-versus-mutant comparisons.
- Implement protein structure visualisation.
- Integrate the evidence retrieval service.
- Integrate the fine-tuned language model.
- Generate structured research reports.

Main deliverables:

- Working application.
- Molecular viewer.
- Screening visualisations.
- Evidence explorer.
- LLM report interface.
- Integrated demonstration.

---

# 7. Parallel Execution and Integration

The workstreams can start independently.

| Team member | Initial independent work | Later integration |
|---|---|---|
| Person 1 | Prepare both training workflows and launch LLM SFT / Boltz training when inputs are ready | Provide model checkpoints and evaluation |
| Person 2 | Pretrained Boltz inference, embeddings and molecular analysis | Evaluate the specialised checkpoint |
| Person 3 | Evidence indexing, retrieval and evaluation benchmark | Audit outputs from both models |
| Person 4 | Application interface using mock data | Integrate real predictions, evidence and model checkpoints |

### Important dependencies

- Person 2 supplies pretrained Boltz embeddings and baseline predictions for Person 1's molecular training workflow.
- Person 3 provides the evidence API to Person 4.
- Person 1 provides the fine-tuned LLM and Boltz inference interfaces.
- Person 2 provides real molecular predictions and structures to Person 4.
- Person 3 independently evaluates the scientific correctness of the generated reports.

The application should begin using mock data immediately, and the molecular analysis should begin using pretrained Boltz outputs. Neither workstream should wait for both checkpoints.

---

# 8. Evaluation Strategy

The project must demonstrate measurable improvements and meaningful scientific analysis.

## 8.1 Boltz-2 evaluation

Compare pretrained Boltz-2 against the EGFR-specialised affinity-head checkpoint.

Metrics:

- Mean Absolute Error (MAE).
- Root Mean Squared Error (RMSE).
- Spearman rank correlation.
- Pearson correlation where appropriate.
- Inhibitor ranking performance.
- Mutation-specific performance.
- Ligand-scaffold-held-out performance.

Evaluate only on appropriate held-out experimental labels.

## 8.2 Language model evaluation

Compare the base LLM against the Adaption fine-tuned LLM.

Evaluate:

- Mutation explanation accuracy.
- Biological mechanism correctness.
- Experimental measurement interpretation.
- Evidence retrieval and citation correctness.
- Ability to distinguish biochemical and cellular measurements.
- Uncertainty calibration.
- Scientific hypothesis quality.
- Experiment-design quality.

Use an independently reviewed benchmark, not merely the training examples.

## 8.3 Integrated-system evaluation

Test the full application using mutation–inhibitor queries.

For each query, evaluate whether the system:

1. Identifies the correct EGFR mutation.
2. Retrieves the correct inhibitor information.
3. Obtains the correct Boltz prediction.
4. Interprets the score convention correctly.
5. Retrieves relevant experimental evidence.
6. Produces a traceable scientific explanation.
7. Separates established findings from computational hypotheses.
8. Suggests appropriate validation experiments.

---

# 9. Expected Final Demonstration

The final demonstration should revolve around a concrete research question.

For example:

**How does EGFR C797S affect the predicted interaction with osimertinib, and what evidence supports the proposed resistance mechanism?**

The system should:

1. Load the C797S mutation information.
2. Retrieve the osimertinib compound information.
3. Obtain WT and mutant Boltz predictions where available.
4. Display their molecular structures.
5. Compare the predicted affinity-related outputs.
6. Retrieve relevant experimental literature.
7. Pass the evidence and predictions to MutationScientist.
8. Produce a structured research explanation.
9. Identify uncertainties and propose follow-up experiments.

The report must distinguish the established biochemical rationale for the mutation from any new computational prediction made by our model.

The intended scientific outcome is a set of mutation–inhibitor interactions and hypotheses that warrant further experimental investigation, not a claim of proven clinical treatment effectiveness.

---

# 10. Important Scientific Limitations

The project is computational and evidence-driven.

We do not claim that:

- Predicted binding affinity proves inhibition in a biological system.
- Binding predictions establish tumour response.
- A computationally identified compound is clinically effective.
- An LLM-generated mechanism is experimentally verified.
- The model replaces biochemical or cellular experiments.

In particular:

- KD, Ki and IC50 must remain distinct.
- Cellular viability measurements must remain separate from biochemical affinity.
- Covalent inhibitor kinetics require additional consideration.
- Literature-derived claims must retain source references.
- Teacher-generated examples require scientific review.
- Predictions on unseen mutations must be evaluated rather than assumed to generalise.

The ultimate validation of a promising molecular hypothesis requires appropriate biochemical and cellular experiments.

---

# 11. Key Project Links and Resources

## Molecular foundation model

| Resource | URL |
|---|---|
| Boltz-2 official website | https://www.boltz.com/boltz2 |
| Official Boltz GitHub | https://github.com/jwohlwend/boltz |
| Boltz-2 research paper | https://doi.org/10.1101/2025.06.14.659707 |
| Boltz-2 affinity fine-tuning implementation | https://github.com/molecularinformatics/Boltz2_affinity |
| Affinity fine-tuning documentation | https://github.com/molecularinformatics/Boltz2_affinity/blob/main/docs/affinity_finetuning.md |

## Language-model fine-tuning

| Resource | URL |
|---|---|
| Adaption Labs | https://adaptionlabs.ai/ |
| AutoScientist application | https://adaptionlabs.ai/app/autoscientist |
| Adaption documentation | https://docs.adaptionlabs.ai/ |
| AutoScientist overview | https://docs.adaptionlabs.ai/autoscientist/overview |
| AutoScientist quickstart | https://docs.adaptionlabs.ai/autoscientist-quickstart/ |
| Adaption API reference | https://docs.adaptionlabs.ai/api/ |

The precise LLM base model will be selected from the live AutoScientist model catalogue when training is configured.

## Scientific databases

| Resource | URL |
|---|---|
| ChEMBL | https://www.ebi.ac.uk/chembl/ |
| BindingDB | https://www.bindingdb.org/ |
| RCSB PDB | https://www.rcsb.org/ |
| UniProt | https://www.uniprot.org/ |
| COSMIC | https://cancer.sanger.ac.uk/cosmic |
| PubMed | https://pubmed.ncbi.nlm.nih.gov/ |
| Europe PMC | https://europepmc.org/ |
| PubChem | https://pubchem.ncbi.nlm.nih.gov/ |

## Project data

| Resource | Location |
|---|---|
| Curated EGFR dataset | `EGFR_RESEARCH_DATASET/` |
| Dataset documentation | `EGFR_RESEARCH_DATASET/README.md` |
| Dataset loader | `egfr_dataset_loader.py` |
| Boltz training input | `ds.boltz` |
| LLM SFT input | `ds.llm` |

---

# 12. Final Project Goal

MutationScientist aims to demonstrate how molecular foundation models and specialised scientific language models can work together to support computational oncology research.

Boltz-2 will provide mutation-aware protein–ligand predictions.

The fine-tuned LLM will interpret these results using curated biological knowledge and experimental evidence.

The retrieval and application layers will make the complete workflow traceable, inspectable and accessible.

**The central contribution is the integration of mutation-specialised molecular prediction with evidence-grounded scientific reasoning, producing a research system for investigating EGFR inhibitor resistance in lung cancer.**