# MutationScientist API

A thin **FastAPI** REST layer over the **existing** MutationScientist service
classes (`~/Desktop/application/services`). Nothing is re-implemented — the API
imports and reuses `DatasetService`, `BoltzService`, `EvidenceService` and
`LLMService`, so the science, the **provenance rules** and the honesty guarantees
are identical to the Streamlit app. This is what the React frontend calls.

## Run

```bash
cd ~/Desktop/product/backend
./run.sh                 # uv + Python 3.13 → uvicorn on http://127.0.0.1:8080
# PORT=9000 ./run.sh     # custom port
```

`run.sh` loads the app's gitignored `.env` (`MUTATIONSCIENTIST_APP_DIR`, default
`~/Desktop/application`) so the API serves **REAL** data when available:
`BOLTZ_PREDICTIONS_PATH` (the real Boltz run) and `OPENAI_*` (the model at
`http://localhost:8000/v1`). Anything unset falls back to the clearly-labelled
mock/template — exactly like the app. No secrets are committed.

Interactive docs: `http://127.0.0.1:8080/docs`.

## Provenance — the Truth Ladder (returned on every value)

| tier | meaning | where |
|---|---|---|
| `measured` | observed / published truth | experimental IC50, cited evidence |
| `predicted` | Boltz-2 affinity model | `affinity_pred_value` |
| `reasoned` | the MutationScientist LLM | `/interpret` report |
| `placeholder` | interface stand-in — **not real** | mock Boltz / template report (`is_mock:true`) |

Measured and predicted values are returned in **separate fields** and never
conflated. A **covalent** inhibitor (osimertinib, silevertinib…) has no Boltz
complex, so `/predict` returns `prediction: null` with an honest reason — never a
fabricated number.

## Endpoints & contracts

### `GET /health`
Liveness + service modes (REAL/MOCK), the live Boltz complex count, the score
definition and the provenance tiers.

### `GET /predict?mutation=&compound=`
`mutation` = id or notation (`EGFR_C797S` / `C797S`). `compound` = id or name
(`CMP_BLU945` / `BLU-945` / `osimertinib`). Returns Boltz-2 prediction(s) for the
pair, each with its experimental reference kept distinct. `prediction` is `null`
(with `reason`, `covalent`) when there is no complex.

**Example — non-covalent pair with a real prediction**
`GET /predict?mutation=EGFR_L858R_C797S&compound=BLU-945`
```json
{
  "mutation_id": "EGFR_L858R_C797S",
  "compound_id": "CMP_BLU945",
  "compound_name": "BLU-945",
  "covalent": false,
  "score_definition": "affinity_pred_value is log10(IC50 in micromolar): log10(IC50_nM) - 3. LOWER = STRONGER binding. This is NOT pIC50. ...",
  "prediction": {
    "complex_id": "COMPLEX_001557",
    "provenance": "predicted",
    "is_mock": false,
    "model_checkpoint": "pretrained",
    "model_version": "boltz-2.2.1",
    "sampling_settings": "boltz2-defaults(recycle3,ss200,affens5)",
    "affinity_pred_value": -1.4600205421447754,
    "affinity_pred_ic50_nM_equiv": 34.672045017477544,
    "affinity_probability_binary": 0.5816891193389893,
    "experimental": {
      "provenance": "measured",
      "affinity_label_log10uM": -1.3568,
      "ic50_nM_equiv": 43.97440784473687
    }
  },
  "predictions": ["… same shape, one per complex …"],
  "provenance": "predicted",
  "count": 1
}
```

**Example — covalent inhibitor, honest no-prediction**
`GET /predict?mutation=C797S&compound=osimertinib`
```json
{
  "mutation_id": "EGFR_C797S",
  "compound_id": "CMP_OSIMERTINIB",
  "compound_name": "osimertinib",
  "covalent": true,
  "prediction": null,
  "predictions": [],
  "provenance": "none",
  "reason": "covalent inhibitor (acrylamide → Cys797): excluded from the Boltz-2 regression target — no complex, no prediction (by design)."
}
```

### `GET /evidence?mutation=&compound=&match=`
`match` = `any` (default, mutation OR compound) | `pair` | `exact`. Returns cited
evidence rows (`claim`, `mechanism`, `assay_type`, `pmid`/`doi`, `source_url`, …),
`provenance: "measured"`, and the `source` (curated or live retrieval API).

**Example** — `GET /evidence?mutation=C797S&compound=osimertinib&match=pair`
```json
{
  "mutation_id": "EGFR_C797S",
  "compound_id": "CMP_OSIMERTINIB",
  "match": "pair",
  "count": 10,
  "provenance": "measured",
  "source": "REAL (curated + cited)",
  "evidence": [
    {
      "evidence_id": "…",
      "claim": "Literature reports EGFR C797S as an acquired on-target resistance mechanism to osimertinib",
      "mechanism": "…",
      "assay_type": "…",
      "pmid": "43021317",
      "doi": "",
      "source_title": "…",
      "source_url": "…",
      "is_mock": false
    }
  ]
}
```

### `POST /interpret`
Body `{ "mutation": "...", "compound": "...", "match": "any" }`. Assembles the
structured record (mutation + compound + Boltz prediction + measurements +
evidence) and calls the served model at `:8000` to interpret it — falling back to
the grounded template (`is_mock:true`, `provenance:"placeholder"`) if the endpoint
is unreachable. The model is instructed to use **only** the supplied context.

```json
{
  "mutation_id": "EGFR_L858R_C797S",
  "compound_id": "CMP_BLU945",
  "provenance": "reasoned",
  "is_mock": false,
  "model": "mutationscientist",
  "served_by": "http://localhost:8000/v1",
  "report_markdown": "# Research Report: BLU-945 Activity Against EGFR L858R/C797S\n\n## 1. Mutation (established mechanism)\n…",
  "context_used": {
    "boltz_predictions": 1,
    "experimental_measurements": 2,
    "evidence_items": 5,
    "any_mock_prediction": false
  }
}
```

## CORS
Enabled for the React dev server. Defaults to `*`; pin with
`CORS_ORIGINS="http://localhost:3000,http://localhost:5173"`.
