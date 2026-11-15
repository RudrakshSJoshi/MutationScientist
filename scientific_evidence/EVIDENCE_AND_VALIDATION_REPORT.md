# EGFR MutationScientist — Evidence & Validation Report (Person 3)

**Scope:** the scientific-evidence / RAG layer and the *independent* scientific
evaluation of the MutationScientist LLM. This report documents what evidence is
indexed, how retrieval and provenance work, how assay types are kept distinct,
what the audit found in the teacher-generated SFT data, what the independent
benchmark covers, and how the service is called by the application.

**Guiding rule throughout:** never fabricate measurements, structures,
identifiers or citations; keep biochemical, cellular and clinical evidence
strictly distinct; when a value is not in the source, say so rather than invent it.

---

## 0. What was added in this contribution

Built on the existing `scientific_evidence/` package (retriever + evidence API from
PR #1) — extended, not duplicated:

```
scientific_evidence/
├── retriever/                         (existing: build/search/question — verified)
├── evidence_api.py                    (existing: retrieve_evidence interface)
├── retrieval_results_examples.jsonl   (NEW — worked retrieval outputs)
├── llm_dataset_audit.csv              (NEW — flagged SFT rows, traceable)
├── llm_dataset_audit_report.md        (NEW — audit summary)
├── EVIDENCE_AND_VALIDATION_REPORT.md  (NEW — this file)
└── evaluation/                        (NEW — independent benchmark + scorers)
    ├── build_benchmark.py             (authors the benchmark; single source of truth)
    ├── scientific_benchmark.jsonl     (30 questions + machine-checkable gold)
    ├── reference_answers.jsonl        (cited gold prose for human review / dry-run)
    ├── evaluation_rubric.md           (scoring rubric)
    ├── scorers.py                     (deterministic scorers; ported + extended)
    ├── run_benchmark.py               (endpoint-agnostic runner: dry-run/openai/adaption)
    ├── audit_llm_dataset.py           (the SFT audit generator)
    ├── valid_citations.json           (corpus DOIs/PMIDs for invented-citation checks)
    ├── evaluation_report.md           (current result: dry-run self-test)
    └── report.json                    (full machine-readable results)
```

Environment: `uv` + Python 3.13, fully local, **no paid/external APIs** for
embedding or scoring. Reproduce with:

```bash
uv venv --python 3.13 .venv
.venv/bin/python -m scientific_evidence.retriever.build --dataset ~/Desktop/EGFR_RESEARCH_DATASET
.venv/bin/python -m scientific_evidence.evaluation.build_benchmark
.venv/bin/python -m scientific_evidence.evaluation.run_benchmark --dry-run
.venv/bin/python -m scientific_evidence.evaluation.audit_llm_dataset
```

---

## 1. What evidence is indexed

The build (`scientific_evidence.retriever.build`) compiles **31,867 evidence
records** from the curated dataset into a packaged SQLite index. Records span:

- **Mutation annotations** (`curated/mutations.csv`) — residue change, position,
  domain, mechanism, resistance association, for the 17 sequenced EGFR variants
  (e.g. C797S = Cys→Ser at 797, loss of covalent anchor).
- **Mutation profiles** (`curated/mutation_profiles.csv`) — single and compound
  variants (L858R/C797S, L858R/T790M/C797S, …) with component linkage.
- **Compound annotations** (`curated/compounds.csv`) — generation, covalent status,
  binding mechanism, warhead, resistance context (gefitinib 1st-gen non-covalent …
  osimertinib 3rd-gen covalent-Cys797 … BLU-945 4th-gen reversible).
- **Affinity measurements** (`curated/affinity_measurements.csv`) — 31,655 rows:
  72 Melis gold biochemical IC50 + 31,583 BindingDB (IC50/KD/Ki/EC50), each with
  assay type, relation, value/unit, ATP condition and provenance.
- **Biological evidence claims** (`curated/biological_evidence.csv`) — 40
  literature-reported mutation×compound associations, each tied to a PMID/DOI.
- **Primary-source cellular points** (`evidence_database/primary_evidence.jsonl`) —
  individually curated Melis Table 4 cellular viability values (e.g. osimertinib
  11.7 nM parental vs 2950 nM clone-1 NCI-H1975).
- **Structures** (`protein_structures/structures_index.csv`) — RCSB PDB entries.
- **References** (`REFERENCES.csv`) — 29 sources with DOI/PMID/URL.

## 2. How retrieval works

Retrieval is deliberately lightweight and fully traceable — appropriate to a small
curated corpus — rather than an opaque vector store:

- **Exact metadata filters** on mutation_id / profile_id / compound_id /
  evidence_category / assay_type / measurement_type / PMID / DOI, with an **alias
  layer** that resolves clinical notation (`L858R`, `C797S`, `ex19del`), profile
  notation (`L858R/C797S`), compound names/synonyms and BDB↔CMP equivalents to
  canonical IDs.
- **BM25 full-text ranking** (SQLite FTS5) over claim text, titles, mechanisms and
  resistance context for free-text and mechanism queries.
- **Priority ordering** so primary-table measurements rank above database records
  above literature associations.
- A **natural-language planner** (`retriever/question.py`) that resolves questions
  like "EGFR C797S + osimertinib" to bounded, typed lookups and rejects
  unrecognised IDs rather than guessing.

Worked outputs are in `retrieval_results_examples.jsonl`. Verified live:

| Query | Direct hits | Context | Traceable IDs returned |
|---|---|---|---|
| C797S + osimertinib | 6 | 6 | PMID/DOI on every literature hit |
| T790M + gefitinib | 4 | 11 | Yun KD (PMID 18227510) + BindingDB IC50s |
| L858R/C797S + BLU-945 | 2 | 3 | Melis biochemical IC50 6.32 nM, Boltz-eligible |
| L858R/T790M/C797S + osimertinib | 6 | 8 | triple-mutant rows incl. n.d. |

## 3. How references are preserved

Every retrieval result carries structured provenance — `evidence_id`,
`evidence_type`, `assay_type`, `source_id`, `pmid`, `doi`, `source_url`,
`evidence_strength` — exactly as in the Person 3 schema. The retriever **never
invents references and never merges unrelated evidence into one claim**: each
record maps to a single source row and keeps its own citation. Conflicting
same-pair measurements are preserved and surfaced (`pair_variability`) rather than
silently reconciled.

## 4. How assay types are distinguished

Assay layers are first-class and never conflated:

- **Biochemical binding** (KD/Ki, equilibrium) vs **enzyme inhibition** (IC50,
  ATP- and assay-dependent) vs **cellular viability** (GI50/viability) vs
  **cellular pathway** vs **structural** vs **clinical** vs **computational
  prediction** — each tagged on the record and filterable.
- **Covalent time-dependence** is flagged: covalent osimertinib IC50s carry
  `covalent_time_dependent_IC50` and are routed to `requires_review`, excluded from
  the Boltz regression target (which is log10(IC50 µM), lower = stronger, **not**
  pIC50; covalent/KD/Ki/cellular rows excluded).
- A **predicted Boltz affinity is never presented as experimental**, and a
  **cellular IC50 is never presented as a protein–ligand KD**. The evaluation
  scorers enforce the same separation on model output.

## 5. Problems discovered in teacher-generated examples

Audit (`llm_dataset_audit_report.md`, generator `audit_llm_dataset.py`) over **all
1,341 SFT rows**:

- **Reviewed:** 1,341 (1,240 teacher-generated/unverified + 101 hand-grounded).
- **Passed (no flag):** 1,335.
- **Requiring human review:** **6** (0.4%) — all concentration-fabrication, all in
  teacher-generated rows (0.5%), none in hand-grounded rows (0.0%). No conflation
  or invented-citation flags.
- **Concentration:** resistance_interpretation carried the most (4/49 = 8.2%).

**Representative confirmed issue** — `sft_train.csv #92` (silevertinib,
resistance_interpretation): the prompt gives only "IC50 = 2.97 nM against L858R/C797S
at 1 mM ATP", but the completion introduces "10.7 nM" (the wild-type value, not in
the prompt) **and** mis-states the interpretation — it calls 2.97 nM "markedly
reduced biochemical potency" when a 2.97 nM IC50 is in fact *more* potent than the
10.7 nM wild-type (lower IC50 = stronger). This is a genuine reasoning error in
unreviewed teacher data, not just an un-sourced number.

Flags are **screening signals, not verdicts**: some are correct values computed
from — or adjacent to — the prompt. The original dataset is **not modified**; each
flag is recorded with `source_file` + `row_index` for a domain reviewer, and any
correction must be stored separately with traceability.

## 6. What the independent evaluation benchmark covers

`evaluation/scientific_benchmark.jsonl` — **30 questions, 6 per category**, with
cited gold in `reference_answers.jsonl` and a deterministic rubric
(`evaluation_rubric.md`):

- **mutation_mechanism** — residue change, domain, functional class (incl. the
  held-out S768I and L861Q).
- **resistance_interpretation** — fold-changes and what they do/don't prove
  (e.g. osimertinib L858R 2.82 nM → L858R/C797S 574 nM ≈ 204-fold; cellular/clinical
  not implied; covalent IC50 is time-dependent).
- **inhibitor_comparison** — osimertinib vs BLU-945 vs JBJ-09-063 vs silevertinib
  potency/selectivity across variants and ATP conditions.
- **assay_distinction** — KD vs Ki vs IC50; biochemical vs cellular; covalent
  time-dependence; Boltz label convention.
- **evidence_qa** — produce the correct DOI/PMID/evidence_id and, crucially, refuse
  to invent a citation when none exists.

Scored on six deterministic dimensions: factual correctness, evidence
grounding/citation (with **invented-DOI/PMID detection** against the 928-DOI /
1171-PMID corpus), biochemical-vs-cellular distinction, uncertainty calibration,
plus the cardinal number-grounding and hedging checks.

**Harness validation (both directions):**

- **Dry-run self-test** (reference answers fed back as predictions):
  **30/30 pass, mean factual 1.000, 0 fabricated numbers, 0 invented citations,
  100% citation recall, 0 conflation** — gold and scorers are mutually consistent.
- **Adversarial negative controls** confirm the scorers *catch* a fabricated
  number, an invented DOI, an invented PMID, an assay conflation, a missing
  required fact, and a missing expected citation.

**Model status:** the fine-tuned endpoint is not yet wired. The runner is
endpoint-agnostic and ready:

```bash
# local OpenAI-compatible server (e.g. vLLM on :8000)
OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=sk-x OPENAI_MODEL=<name> \
  python -m scientific_evidence.evaluation.run_benchmark --backend openai

# Adaption hosted fine-tune (Responses API; slug provided once the stack exists)
ADAPTION_API_KEY=... ADAPTION_STACK=<slug> \
  python -m scientific_evidence.evaluation.run_benchmark --backend adaption
```

When the endpoint is up, the same 30 held-out questions can grade the fine-tune
against the base model with identical scoring.

## 7. How the evidence service is called by the application

Person 4's app calls one stable in-process function; it does not need to know the
retrieval internals:

```python
from scientific_evidence.evidence_api import retrieve_evidence

result = retrieve_evidence(mutation_id="EGFR_C797S", compound_id="CMP_OSIMERTINIB")
# -> {"mutation_id", "profile_id", "compound_id",
#     "evidence": [ {evidence_id, claim, evidence_type, assay_type,
#                    source_id, pmid, doi, source_url, evidence_strength, ...}, ... ],
#     "context": [...], "pair_variability": [...], "total_matches": N}
```

Accepts mutation_id / profile / compound_id / compound_name / free-text `query`
("C797S + osimertinib") / resistance_mechanism / assay_type / PMID / DOI. Output is
structured, source-linked evidence — never an unreferenced paragraph.

---

## Scientific-trustworthiness summary

The system can state **where each claim comes from** (structured PMID/DOI/evidence_id
provenance on every record), **what the evidence actually demonstrates** (assay
layers kept distinct; covalent/cellular/predicted never conflated), and **when it
does not know** (n.d. values and the header-only cellular table are reported as
gaps, not filled in). The independent benchmark tests exactly these properties on
model output, with fabricated numbers and invented citations always surfaced and
always failing.
