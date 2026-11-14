# PERSON 3 — BIOLOGICAL EVIDENCE, RAG AND SCIENTIFIC VALIDATION

## Objective

Build the scientific evidence and retrieval layer for MutationScientist.

Your responsibility is to make sure that the final system can retrieve relevant, traceable biomedical evidence for EGFR mutations and inhibitors, and that its scientific explanations can be independently evaluated.

You are NOT responsible for fine-tuning the LLM or Boltz-2.

Your work should proceed independently of both training pipelines.

## 1. Understand the provided dataset

Inspect:

- `README.md`
- `egfr_dataset_loader.py`
- `curated/mutations.csv`
- `curated/mutation_profiles.csv`
- `curated/compounds.csv`
- `curated/affinity_measurements.csv`
- `curated/cellular_assays.csv`
- `curated/biological_evidence.csv`
- `REFERENCES.csv`
- `mutation_scientist/`
- `validation/`

Load the dataset:

```python
from egfr_dataset_loader import EGFRDataset

ds = EGFRDataset("EGFR_RESEARCH_DATASET")

print(ds.validate())
print(ds.llm.counts())
```

Understand the actual LLM dataset composition:

- 1,341 SFT examples.
- 912 training examples.
- 214 validation examples.
- 215 test examples.
- 101 hand-grounded examples.
- 1,240 teacher-generated examples that are machine-checked but not human-reviewed.

The last point is particularly important. Do not assume all existing examples have equal scientific reliability.

## 2. Build the evidence retrieval system

Create a searchable evidence database from the provided curated records.

It should support queries using:

- Mutation ID.
- Mutation profile.
- Compound ID.
- Compound name.
- Resistance mechanism.
- Cancer context.
- Evidence category.
- Assay type.
- Publication title.
- PMID.
- DOI.

For example:

`EGFR_C797S + CMP_OSIMERTINIB`

should retrieve relevant mutation annotations, resistance mechanisms, experimental observations and literature references.

Another query:

`EGFR_T790M + gefitinib`

should return the relevant experimental findings and distinguish them from unrelated inhibitor evidence.

Implement a retrieval approach suitable for the actual dataset size. You may use keyword/BM25 retrieval, metadata filtering and semantic search where useful.

Do not spend time building an unnecessarily complex vector database if a simpler indexed retrieval system provides better reliability.

## 3. Build a structured evidence response

Every retrieval result must preserve its scientific provenance.

Use a consistent output format:

```json
{
  "mutation_id": "EGFR_C797S",
  "compound_id": "CMP_OSIMERTINIB",
  "evidence": [
    {
      "evidence_id": "EVIDENCE_000001",
      "claim": "Verified scientific claim",
      "evidence_type": "experimental",
      "assay_type": "biochemical",
      "source_id": "SOURCE_000001",
      "pmid": "PMID",
      "doi": "DOI",
      "source_url": "URL",
      "evidence_strength": "high"
    }
  ]
}
```

The values are illustrative. Use actual identifiers and evidence from the dataset.

The retrieval system must never invent references or merge unrelated evidence into a single claim.

## 4. Distinguish evidence types

This is a major responsibility.

Build filtering and interpretation logic that distinguishes:

- Biochemical binding affinity.
- Enzyme inhibition.
- Cellular viability.
- Cellular pathway inhibition.
- Structural experimental observations.
- Clinical observations.
- Computational predictions.
- Literature-derived hypotheses.

For example, a cellular viability IC50 must not be presented as a measured protein–ligand KD.

Likewise, a predicted Boltz affinity must not be presented as experimental evidence.

Preserve conflicting measurements and identify differences in assay conditions rather than silently choosing one result.

## 5. Audit the existing LLM dataset

The teacher-generated examples are not human-reviewed, even though their numerical values have been automatically checked.

Review a representative sample, prioritising:

1. Mutation mechanism correctness.
2. Amino-acid substitutions and residue numbering.
3. Inhibitor mechanisms.
4. Numerical measurement interpretation.
5. Assay-type distinctions.
6. Citation correctness.
7. Unsupported biological or clinical claims.

Flag incorrect or questionable examples.

Produce:
- Number reviewed.
- Number passed.
- Number requiring correction.
- Number rejected.
- Main error categories.

Do not silently modify the original dataset. Record corrections separately and maintain traceability to the original example.

## 6. Prepare an independent scientific evaluation benchmark

Use:

- `mutation_scientist/eval_questions.jsonl`
- `sft_test.csv`
- Relevant independent literature and experimental measurements.

Create an evaluation benchmark that tests whether a language model can:

- Explain mutations accurately.
- Identify established resistance mechanisms.
- Interpret experimental measurements.
- Distinguish KD, Ki and IC50.
- Identify whether evidence is biochemical, cellular or clinical.
- Cite the supplied evidence correctly.
- Avoid unsupported claims.
- Suggest appropriate validation experiments.

The test set is mutation-held-out:
- S768I and L861Q are in the test split.
- T790M is in validation.

Keep these splits independent. Do not move test examples into training or use held-out answers to construct training examples.

Create a scoring rubric and sample answer references for human review.

When the fine-tuned LLM becomes available, evaluate it against the original base model using the same held-out questions.

## 7. Define the RAG interface for Person 4

Expose a simple interface that the application can call.

Conceptually:

```python
evidence = retrieve_evidence(
    mutation_id="EGFR_C797S",
    compound_id="CMP_OSIMERTINIB"
)
```

The output must be structured, source-linked evidence rather than an unreferenced paragraph.

The application developer should not need to understand your internal retrieval implementation.

## 8. Required deliverables

```text
scientific_evidence/
│
├── evidence_index/
├── evidence_database/
├── retriever/
│
├── retrieval_results_examples.jsonl
├── evidence_api.py
├── evidence_schema.json
│
├── llm_dataset_audit.csv
├── llm_dataset_audit_report.md
│
├── evaluation/
│   ├── scientific_benchmark.jsonl
│   ├── evaluation_rubric.md
│   ├── reference_answers.jsonl
│   └── evaluation_report.md
│
└── EVIDENCE_AND_VALIDATION_REPORT.md
```

### Final report

Explain:
- What evidence has been indexed.
- How retrieval works.
- How references are preserved.
- How different assay types are distinguished.
- What problems were discovered in teacher-generated examples.
- What the independent evaluation benchmark covers.
- How the evidence service can be called by the application.

Your main responsibility is scientific trustworthiness: the final research assistant must be able to explain where its claims came from and what the evidence actually demonstrates.