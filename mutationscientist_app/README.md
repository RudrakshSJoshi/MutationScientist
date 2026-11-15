# MutationScientist — EGFR Molecular Discovery (Person 4: Application & Integration)

The integrated research application for the **MutationScientist** project. It ties
the shared `EGFR_RESEARCH_DATASET`, Boltz-2 molecular predictions (Person 2),
scientific evidence retrieval (Person 3) and the fine-tuned MutationScientist LLM
(Person 1) into one Streamlit interface — usable, interpretable and demonstrable.

> Not for clinical decisions. Predicted binding affinity ≠ enzyme inhibition ≠
> cell killing ≠ clinical efficacy.

---

## Quick start

```bash
cd application

# Option A — uv (recommended; handles Python + deps)
uv venv --python 3.13 .venv
uv pip install -r requirements.txt
uv run streamlit run app.py

# Option B — plain pip (needs Python 3.11–3.13)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501.

The app finds `EGFR_RESEARCH_DATASET/` and `egfr_dataset_loader.py` automatically
by searching upward from `application/`. Override with `EGFR_DATASET_ROOT` /
`EGFR_LOADER_PATH` if they live elsewhere.

---

## 1. Application architecture

```
          EGFR_RESEARCH_DATASET  +  egfr_dataset_loader.py
                              │
                   services/dataset_service.py        (single source of truth)
                              │
        ┌──────────────┬──────┴───────┬────────────────┐
  boltz_service   evidence_service  llm_service     (dataset tables)
   (Person 2)       (Person 3)      (Person 1)
        │               │               │
        └──────────────┬┴───────────────┘
                       │
        pages/*  (render(ctx))  ◀── app.py (sidebar nav, shared ctx, cache)
                       │
         components/ui.py · visualisations/charts.py
```

- **`app.py`** — entry point. Builds the services once (`st.cache_resource`),
  owns the sidebar navigation and the shared `ctx`, shows dataset + service status.
- **`services/`** — one module per external interface, each with a REAL and a
  MOCK mode decided at runtime (see §4).
- **`pages/`** — six `render(ctx)` modules (Streamlit auto-nav is disabled in
  `.streamlit/config.toml`; the sidebar radio is the single navigation).
- **`components/ui.py`** — provenance badges (experimental / pretrained /
  fine-tuned / mock / real), banners, key-value tables.
- **`visualisations/charts.py`** — WT-vs-mutant bars, ranking tables.

## 2. Pages and functionality

| Page | What it does | Data source |
|---|---|---|
| **Overview** | Counts, live service status, the demo question | dataset (real) |
| **Mutation Explorer** | Variant → residues, domain, mechanism, profile, linked evidence | real |
| **Inhibitor Explorer** | Panel browse/search, covalent flagging, SMILES, measurements | real |
| **Molecular Screening** | Inhibitor ranking, WT-vs-mutant, single-pair prediction *vs* experiment | Boltz = mock/real |
| **Structure Viewer** | Real RCSB PDB entries rendered via 3Dmol.js | real (experimental) |
| **Evidence Explorer** | Cited evidence retrieval by mutation/compound | real |
| **MutationScientist Report** | Assembles context → structured research report | LLM = template/real |

## 3. Backend interfaces (agreed shapes)

**Boltz prediction (Person 2)** — `services/boltz_service.py`:
```json
{"complex_id":"COMPLEX_000001","mutation_id":"EGFR_C797S","compound_id":"...",
 "model_version":"boltz-2.2.1","model_checkpoint":"pretrained|finetuned",
 "affinity_pred_value":null,"affinity_probability_binary":null,
 "score_definition":"log10(IC50 uM); lower=stronger; NOT pIC50","structure_path":null}
```
Supply a JSON file (list or `{complex_id: record}`) via `BOLTZ_PREDICTIONS_PATH`.
Null = unavailable, not zero. Schema sample: `mock_data/boltz_predictions.sample.json`.

**Evidence (Person 3)** — `services/evidence_service.py`:
`retrieve(mutation_id, compound_id, match)` → `{mutation_id, compound_id, count,
evidence:[{evidence_id, claim, evidence_type, assay_type, pmid, doi, source_url, ...}]}`.

**LLM (Person 1)** — `services/llm_service.py`:
`generate(mutation, compound, boltz_predictions, experimental_evidence,
measurements, data)` → `{is_mock, model, context, report_markdown, sections}`.
`build_context()` is the exact structured payload handed to the model (includes the
score definition, because prediction-interpretation is not yet in the training set).

## 4. Mock vs real components

| Component | Default | Becomes real when |
|---|---|---|
| Dataset / mutations / compounds / measurements | **REAL** | always |
| Evidence retrieval | **REAL** (curated + cited) | always |
| Structures | **REAL** (RCSB experimental) | always |
| Boltz predictions | **MOCK** placeholder | `BOLTZ_PREDICTIONS_PATH` set |
| MutationScientist report | **MOCK** grounded template | `ADAPTION_API_KEY` + `ADAPTION_MODEL_ID` set |

Switching modes needs **no UI change**. Mock output is always badged/bannered and
never presented as a real result. The mock Boltz value is a deterministic
placeholder (loosely anchored to the experimental label only so WT/mutant ordering
is illustrative); it is not a scientific prediction.

## 5. Integration status (per teammate)

- **Person 1 (LLM):** interface ready; real call is an OpenAI-compatible
  `chat/completions` request with graceful fallback to the template. Pending the
  served checkpoint + `ADAPTION_API_KEY`/`ADAPTION_MODEL_ID`.
- **Person 2 (Boltz):** interface + schema ready; drop a predictions JSON at
  `BOLTZ_PREDICTIONS_PATH`. Pending real predictions/embeddings and predicted
  structure files (`structure_path`).
- **Person 3 (Evidence):** already serving the real curated evidence; can be
  repointed at a live retrieval API by swapping `EvidenceService`.

## 6. Known issues / limitations

- Boltz predictions and the LLM report are mock/template until teammates deliver.
- The RCSB structure index is EGFR-wide and not reliably mutation-tagged, so
  entries are **not** auto-mapped to a specific variant (stated in the UI).
- Covalent inhibitors (osimertinib etc.) are flagged; their time-dependent
  kinetics are not represented by equilibrium affinity and they are excluded from
  the Boltz regression *target*.
- Not every mutation×compound pair has data — the app shows "no data" rather than
  inventing a row.

## 7. Demo workflow

1. **Overview** → confirm dataset loaded + service modes.
2. **MutationScientist Report** → it defaults to **EGFR_C797S × osimertinib**.
3. Expand *Assembled context* to see predictions / measurements / evidence counts.
4. **Generate research report** → structured report separating established
   mechanism from (mock) computational prediction, with cited references.
5. Cross-check in **Molecular Screening** (WT vs mutant), **Evidence Explorer**
   (the C797S↔osimertinib resistance citations) and **Structure Viewer**.

Every displayed result keeps its IDs (`complex_id`, `mutation_id`, `compound_id`,
`evidence_id`, `pmid`/`doi`) so it is traceable back to the dataset.
