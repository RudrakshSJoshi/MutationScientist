"""
MutationScientist REST API — a thin FastAPI layer over the EXISTING Streamlit
service classes (dataset / boltz / evidence / llm). Nothing is re-implemented:
the same `services.*` that power the Streamlit app are imported and reused, so
the science, the provenance rules and the honesty guarantees are identical.

Endpoints (for the React frontend):
  GET  /health                         — liveness + service modes
  GET  /predict?mutation=&compound=    — Boltz-2 prediction(s) for a pair
  GET  /evidence?mutation=&compound=   — curated/live cited evidence
  POST /interpret                      — calls the :8000 model on the structured record

HARD RULES (carried over from the app, enforced here too):
  * Provenance is explicit on every value: MEASURED vs PREDICTED vs REASONED vs
    PLACEHOLDER. Experimental measurements are never conflated with predictions.
  * A covalent inhibitor (osimertinib etc.) has NO Boltz complex — /predict then
    returns prediction:null with an honest reason, never a fabricated number.
  * MOCK/placeholder values are flagged is_mock:true and tiered PLACEHOLDER.

Run:  see README.md  (./run.sh  →  uvicorn on :8080)
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Optional

# --- reuse the Streamlit app's services (do NOT re-create them) --------------
APP_DIR = Path(os.environ.get("MUTATIONSCIENTIST_APP_DIR",
                              str(Path.home() / "Desktop" / "application"))).expanduser().resolve()
if not (APP_DIR / "services").is_dir():
    raise RuntimeError(
        f"Could not find the Streamlit app's services at {APP_DIR}. "
        "Set MUTATIONSCIENTIST_APP_DIR to the application/ directory.")
sys.path.insert(0, str(APP_DIR))

import config.settings as S                       # noqa: E402
from services.dataset_service import DatasetService   # noqa: E402
from services.boltz_service import BoltzService       # noqa: E402
from services.evidence_service import EvidenceService # noqa: E402
from services.llm_service import LLMService           # noqa: E402

from fastapi import FastAPI, HTTPException, Query     # noqa: E402
from fastapi.middleware.cors import CORSMiddleware    # noqa: E402
from pydantic import BaseModel                        # noqa: E402

# ---------------------------------------------------------------------------
# Provenance — the Truth Ladder, expressed as data (no Streamlit/UI import).
#   measured    observed / published truth        (experimental)
#   predicted   Boltz-2 affinity model            (pretrained / fine-tuned)
#   reasoned    the MutationScientist LLM          (interpretation)
#   placeholder interface stand-in — NOT real      (mock / template)
# ---------------------------------------------------------------------------
def _pred_provenance(rec: dict) -> str:
    if rec.get("is_mock"):
        return "placeholder"
    return "predicted"


def _log10uM_to_nM(v):
    if v is None:
        return None
    try:
        return 10.0 ** (float(v) + 3.0)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
app = FastAPI(
    title="MutationScientist API",
    version="1.0.0",
    description="Thin REST layer over the MutationScientist dataset/boltz/evidence/llm services.",
)

# CORS — the React dev server calls this cross-origin. Configurable; defaults to
# the common local dev origins plus '*' for a hackathon frontend.
_origins = os.environ.get("CORS_ORIGINS")
allow_origins = [o.strip() for o in _origins.split(",")] if _origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Services are built ONCE and shared (the dataset load is a few seconds).
_data = DatasetService()
_boltz = BoltzService(_data)
_evidence = EvidenceService(_data)
_llm = LLMService()


# --------------------------------------------------------------- id resolution
def resolve_mutation(q: Optional[str]) -> Optional[str]:
    """Accept a mutation_id (EGFR_C797S) or a notation (C797S), case-insensitive."""
    if not q:
        return None
    q = q.strip()
    if _data.get_mutation(q):
        return q
    cand = q if q.upper().startswith("EGFR_") else f"EGFR_{q}"
    if _data.get_mutation(cand):
        return cand
    ql = q.lower()
    for m in _data.list_mutations():
        if (m.get("mutation_notation") or "").lower() == ql or \
           (m.get("mutation_id") or "").lower() == ql:
            return m["mutation_id"]
    return None


def resolve_compound(q: Optional[str]) -> Optional[str]:
    """Accept a compound_id (CMP_BLU945 / BDB_...) or a name (osimertinib, BLU-945)."""
    if not q:
        return None
    q = q.strip()
    if _data.get_compound(q):
        return q
    ql = q.lower().replace("-", "").replace(" ", "")
    for c in _data.list_compounds():
        name = (c.get("compound_name") or "").lower().replace("-", "").replace(" ", "")
        if name == ql or (c.get("compound_id") or "").lower() == q.lower():
            return c["compound_id"]
    return None


def _compound_is_covalent(compound_id: str) -> bool:
    c = _data.get_compound(compound_id) or {}
    return S.is_covalent(c.get("covalent_status"))


# ----------------------------------------------------------------- endpoints
@app.get("/health")
def health():
    return {
        "status": "ok",
        "dataset_version": _data.manifest.get("dataset_version", "?"),
        "services": {
            "boltz": _boltz.mode_label(),
            "boltz_real_complexes": _boltz.n_real,
            "evidence": _evidence.mode_label(),
            "llm": _llm.mode_label(),
            "llm_endpoint": S.MODEL_ENDPOINT,
        },
        "score_definition": S.SCORE_DEFINITION,
        "provenance_tiers": ["measured", "predicted", "reasoned", "placeholder"],
    }


@app.get("/predict")
def predict(mutation: str = Query(..., description="mutation id or notation, e.g. EGFR_C797S or C797S"),
            compound: str = Query(..., description="compound id or name, e.g. CMP_BLU945 or osimertinib")):
    mid = resolve_mutation(mutation)
    cid = resolve_compound(compound)
    if not mid:
        raise HTTPException(404, f"unknown mutation: {mutation!r}")
    if not cid:
        raise HTTPException(404, f"unknown compound: {compound!r}")

    covalent = _compound_is_covalent(cid)
    complexes = _data.complexes_for(mutation_id=mid, compound_id=cid)

    base = {
        "mutation_id": mid,
        "compound_id": cid,
        "compound_name": _data.compound_display_name(cid),
        "covalent": covalent,
        "score_definition": S.SCORE_DEFINITION,
    }

    if not complexes:
        # HARD RULE: covalent inhibitors are excluded from the Boltz regression
        # target — return an honest 'no prediction', never a fabricated value.
        reason = ("covalent inhibitor (acrylamide → Cys797): excluded from the Boltz-2 "
                  "regression target — no complex, no prediction (by design)."
                  if covalent else
                  "no Boltz-2 complex exists for this mutation–inhibitor pair "
                  "(nothing fabricated).")
        return {**base, "prediction": None, "predictions": [], "provenance": "none", "reason": reason}

    preds = []
    for cx in complexes:
        rec = _boltz.get_prediction(cx.complex_id)
        if not rec:
            continue
        prov = _pred_provenance(rec)
        pv = rec.get("affinity_pred_value")
        ev = rec.get("experimental_affinity_label")
        preds.append({
            "complex_id": rec.get("complex_id"),
            "provenance": prov,                       # 'predicted' or 'placeholder' (mock)
            "is_mock": bool(rec.get("is_mock")),
            "model_checkpoint": rec.get("model_checkpoint"),
            "model_version": rec.get("model_version"),
            "sampling_settings": rec.get("sampling_settings"),
            # PREDICTED (Boltz-2) — log10(IC50 µM), lower = stronger
            "affinity_pred_value": pv,
            "affinity_pred_ic50_nM_equiv": _log10uM_to_nM(pv),
            "affinity_probability_binary": rec.get("affinity_probability_binary"),
            # MEASURED (experimental reference) — kept DISTINCT from the prediction
            "experimental": {
                "provenance": "measured",
                "affinity_label_log10uM": ev,
                "ic50_nM_equiv": _log10uM_to_nM(ev),
            } if ev is not None else None,
        })

    return {**base, "prediction": preds[0] if preds else None, "predictions": preds,
            "provenance": preds[0]["provenance"] if preds else "none",
            "count": len(preds)}


@app.get("/evidence")
def evidence(mutation: Optional[str] = Query(None, description="mutation id or notation"),
             compound: Optional[str] = Query(None, description="compound id or name"),
             match: str = Query("any", pattern="^(any|pair|exact)$")):
    mid = resolve_mutation(mutation) if mutation else None
    cid = resolve_compound(compound) if compound else None
    if mutation and not mid:
        raise HTTPException(404, f"unknown mutation: {mutation!r}")
    if compound and not cid:
        raise HTTPException(404, f"unknown compound: {compound!r}")
    res = _evidence.retrieve(mutation_id=mid, compound_id=cid, match=match)
    # Evidence is MEASURED/cited truth — label it so the frontend styles it right.
    return {**res, "provenance": "measured", "source": _evidence.mode_label()}


class InterpretBody(BaseModel):
    mutation: str
    compound: str
    match: str = "any"


@app.post("/interpret")
def interpret(body: InterpretBody):
    mid = resolve_mutation(body.mutation)
    cid = resolve_compound(body.compound)
    if not mid:
        raise HTTPException(404, f"unknown mutation: {body.mutation!r}")
    if not cid:
        raise HTTPException(404, f"unknown compound: {body.compound!r}")

    mutation = _data.get_mutation(mid)
    compound = _data.get_compound(cid)
    preds = _boltz.predictions_for(mutation_id=mid, compound_id=cid)
    meas = _data.measurements_for(mutation_id=mid, compound_id=cid)
    ev = _evidence.retrieve(mutation_id=mid, compound_id=cid, match=body.match).get("evidence", [])

    # Calls the served model at :8000 with the structured record (or the grounded
    # template on fallback). The service enforces 'use only the supplied context'.
    report = _llm.generate(mutation, compound, preds, ev, meas, _data)
    provenance = "placeholder" if report.get("is_mock") else "reasoned"
    return {
        "mutation_id": mid,
        "compound_id": cid,
        "provenance": provenance,                 # 'reasoned' (real) or 'placeholder' (template)
        "is_mock": bool(report.get("is_mock")),
        "model": report.get("model"),
        "served_by": S.MODEL_ENDPOINT,
        "report_markdown": report.get("report_markdown"),
        "context_used": {
            "boltz_predictions": len(preds),
            "experimental_measurements": len(meas),
            "evidence_items": len(ev),
            "any_mock_prediction": any(p.get("is_mock") for p in preds),
        },
    }
