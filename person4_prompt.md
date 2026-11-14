# PERSON 4 — MUTATIONSCIENTIST APPLICATION AND SYSTEM INTEGRATION

## Objective

Build the working research application for the EGFR project.

Your responsibility is to turn the dataset, molecular predictions, biological evidence and language model into one usable interface.

You are NOT responsible for training either model or collecting the underlying scientific dataset.

Start with mock data and integrate the real outputs as they become available.

## 1. Understand the dataset and loader

Inspect:

- `README.md`
- `egfr_dataset_loader.py`
- `boltz2/complex_metadata.csv`
- `mutation_scientist/sft_train.csv`
- `mutation_scientist/sft_validation.csv`
- `mutation_scientist/sft_test.csv`
- `curated/mutations.csv`
- `curated/compounds.csv`
- `curated/biological_evidence.csv`
- `REFERENCES.csv`

Load the dataset:

```python
from egfr_dataset_loader import EGFRDataset

ds = EGFRDataset("EGFR_RESEARCH_DATASET")

print(ds.validate())
print(ds.shared_keys())
```

Understand that:

- Boltz records represent protein–ligand complexes.
- LLM records represent prompt/completion examples.
- Both components use common mutation and compound identifiers.
- `complex_id` is the primary identifier for a specific Boltz complex.
- A mutation–compound pair may have multiple experimental measurements or complex records.

Never assume that every mutation can be paired with every compound.

Do not invent missing combinations or predictions.

## 2. Design the application

Build a professional, research-oriented application.

Streamlit is acceptable for the hackathon MVP.

Suggested name:

**MutationScientist — EGFR Molecular Discovery**

The application should contain the following sections.

### A. Mutation Explorer

Allow users to:
- Browse available EGFR variants.
- Select an individual mutation or mutation profile.
- View the reference and mutant residues.
- View the protein domain.
- Read the known biological mechanism.
- See evidence classification and references.

### B. Inhibitor Explorer

Allow users to:
- Browse available EGFR inhibitors.
- Search by name.
- View molecular identifiers and SMILES.
- View inhibitor class.
- Identify covalent versus non-covalent inhibitors.
- View the available experimental measurements.

### C. Molecular Screening

Display Person 2's actual Boltz outputs.

Include:
- WT versus mutant comparisons.
- Predicted affinity values.
- Predicted binder probabilities.
- Mutation-specific inhibitor rankings.
- Confidence metadata where available.
- Model version and checkpoint identity.

Distinguish clearly between:
- Experimental measurements.
- Pretrained Boltz predictions.
- Fine-tuned Boltz predictions.

Never display an experimental affinity measurement as though it were a model prediction or vice versa.

Use `complex_id` to retrieve the exact prediction record. Keep source measurement IDs accessible.

### D. Molecular Structure Viewer

Display actual protein–ligand structures supplied by Person 2.

Provide:
- Protein structure.
- Ligand structure.
- Mutation location.
- Binding-pocket view where feasible.
- Relevant structural annotations.

PyMOL-generated images, a browser-based molecular viewer or another appropriate viewer can be used.

Clearly identify whether a structure is experimental or computationally predicted.

### E. Evidence Explorer

Integrate Person 3's retrieval service.

Display:
- Relevant biological claims.
- Experimental findings.
- Assay types.
- PMID and DOI.
- Source links.
- Evidence classifications.
- Uncertainties and conflicting evidence.

A user should be able to inspect the evidence supporting a generated explanation.

### F. MutationScientist Report

Integrate the fine-tuned LLM supplied by the model-training owner.

For a selected mutation–inhibitor pair, assemble:

1. Mutation information.
2. Compound information.
3. Actual Boltz prediction outputs.
4. Retrieved experimental evidence.
5. Relevant literature references.

Pass this structured context to the LLM.

Display a structured report containing:

- Mutation explanation.
- Molecular prediction interpretation.
- Experimental evidence.
- Potential resistance implications.
- Confidence and uncertainties.
- Suggested validation experiments.
- References.

**Important:** the current LLM training dataset does not contain actual post-training Boltz prediction interpretation examples. Until those examples are generated and appropriately incorporated, ensure the LLM receives the complete actual prediction and score definition in its inference-time context. Do not assume the model has learned this task merely from mutation-understanding examples.

## 3. Establish common interfaces

Coordinate with the other team members before implementing the backend.

### Molecular prediction interface — Person 2

Expect records containing:

```json
{
  "complex_id": "COMPLEX_000001",
  "mutation_id": "EGFR_C797S",
  "compound_id": "CMP_OSIMERTINIB",
  "model_version": "VERIFIED_VERSION",
  "model_checkpoint": "pretrained_or_finetuned",
  "affinity_pred_value": null,
  "affinity_probability_binary": null,
  "score_definition": "verified score convention",
  "structure_path": null
}
```

Use actual outputs. Null values mean unavailable, not zero.

### Evidence retrieval interface — Person 3

Expect a structured response containing:

```json
{
  "mutation_id": "EGFR_C797S",
  "compound_id": "CMP_OSIMERTINIB",
  "evidence": [
    {
      "evidence_id": "EVIDENCE_000001",
      "claim": "Verified scientific claim",
      "evidence_type": "experimental",
      "source_id": "SOURCE_000001",
      "pmid": "PMID",
      "doi": "DOI",
      "source_url": "URL"
    }
  ]
}
```

### Language model interface — model-training owner

Agree on an inference interface that receives structured context and returns a report.

For example:

```python
report = mutation_scientist.generate(
    mutation=mutation_record,
    compound=compound_record,
    boltz_predictions=prediction_records,
    experimental_evidence=evidence_records
)
```

The exact implementation can be agreed with the model owner.

## 4. Build using mock data first

Do not wait for model checkpoints.

Start by:

1. Building the page structure.
2. Loading mutation and compound metadata from the provided dataset.
3. Creating representative mock prediction records.
4. Creating mock evidence responses.
5. Building the visualisations.
6. Implementing the report layout.
7. Defining the backend interfaces.

Keep mock data clearly marked and separate from real results.

When the other team members deliver real outputs, replace the mock services without rebuilding the interface.

## 5. Implement the final integrated workflow

The expected user journey is:

1. User selects an EGFR mutation.
2. User selects an inhibitor.
3. Application finds the relevant available complex record.
4. Application retrieves its Boltz prediction.
5. Application retrieves relevant experimental evidence.
6. Application sends the structured context to MutationScientist.
7. LLM generates a grounded research explanation.
8. Application displays predictions, structures, findings and references together.
9. User can inspect the underlying evidence and experimental measurements.

Ensure the application preserves all IDs so every displayed result is traceable to the underlying dataset.

## 6. Required deliverables

```text
application/
│
├── app.py
├── config/
│
├── pages/
│   ├── mutation_explorer.py
│   ├── inhibitor_explorer.py
│   ├── molecular_screening.py
│   ├── structure_viewer.py
│   ├── evidence_explorer.py
│   └── mutation_scientist.py
│
├── components/
├── services/
│   ├── dataset_service.py
│   ├── boltz_service.py
│   ├── evidence_service.py
│   └── llm_service.py
│
├── visualisations/
├── mock_data/
├── assets/
│
├── requirements.txt
└── README.md
```

## 7. Final acceptance criteria

The application should:

- Load the provided dataset successfully.
- Display real mutation and compound information.
- Demonstrate the interface using mock data before model integration.
- Display actual Boltz predictions when supplied.
- Distinguish pretrained and fine-tuned model outputs.
- Display molecular structures.
- Retrieve cited biological evidence.
- Invoke MutationScientist using structured context.
- Generate a traceable scientific report.
- Never invent a missing prediction or experimental result.

### Final report

Document:
- Application architecture.
- Pages and functionality.
- Backend interfaces.
- Mock versus real components.
- Integration status with each team member.
- Known issues.
- Demo workflow.

Your main responsibility is to make the two-model research system usable, interpretable and demonstrable as one integrated application.