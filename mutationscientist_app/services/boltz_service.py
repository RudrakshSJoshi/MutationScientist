"""
boltz_service.py — the molecular-prediction interface (Person 2's outputs).

Two modes, decided per request:
  * REAL  — if a predictions file (JSON) is supplied via BOLTZ_PREDICTIONS_PATH
            (or passed in), records are read straight from it.
  * MOCK  — otherwise a clearly-labelled placeholder record is produced so the
            interface can be demonstrated before checkpoints exist.

HARD RULE: a MOCK record is never presented as a real prediction. Every mock
carries is_mock=True and model_checkpoint="MOCK_PLACEHOLDER"; the UI shows a
banner. A mock value is a deterministic placeholder, NOT a scientific result.

The record schema matches the agreed Person 2 interface:
  complex_id, mutation_id, compound_id, model_version, model_checkpoint,
  affinity_pred_value, affinity_probability_binary, score_definition,
  structure_path  (+ is_mock, note)
"""
from __future__ import annotations
import json, hashlib
from pathlib import Path

import config.settings as S


def _mock_jitter(seed: str, lo: float, hi: float) -> float:
    h = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)
    return lo + (h % 10_000) / 10_000.0 * (hi - lo)


class BoltzService:
    def __init__(self, dataset_service, predictions_path: str | Path | None = None):
        self.data = dataset_service
        self._real: dict[str, dict] = {}
        path = predictions_path or S.env(S.ENV_BOLTZ_PREDICTIONS)
        self.predictions_path = Path(path).expanduser().resolve() if path else None
        self.real_mode = False
        if self.predictions_path and self.predictions_path.exists():
            self._load_real(self.predictions_path)

    def _load_real(self, path: Path):
        raw = json.loads(path.read_text())
        records = raw.values() if isinstance(raw, dict) else raw
        for r in records:
            if r.get("complex_id"):
                r.setdefault("is_mock", False)
                self._real[r["complex_id"]] = r
        self.real_mode = len(self._real) > 0

    # ------------------------------------------------------------------ core
    def get_prediction(self, complex_id: str) -> dict | None:
        cx = self.data.get_complex(complex_id)
        if cx is None:
            return None
        if complex_id in self._real:
            rec = dict(self._real[complex_id])
            rec.setdefault("score_definition", S.SCORE_DEFINITION)
            return rec
        return self._mock_record(cx)

    def _mock_record(self, cx) -> dict:
        # Deterministic placeholder. Loosely anchored on the experimental label
        # ONLY so WT/mutant ordering is illustrative in the demo — explicitly
        # flagged as a placeholder, never a scientific prediction.
        anchor = cx.affinity_label if cx.affinity_label is not None else 0.0
        val = round(anchor + _mock_jitter(cx.complex_id, -0.6, 0.6), 3)
        prob = round(_mock_jitter(cx.complex_id + "p", 0.45, 0.95), 3)
        return {
            "complex_id": cx.complex_id,
            "mutation_id": cx.mutation_id,
            "compound_id": cx.compound_id,
            "model_version": "boltz2 (interface placeholder)",
            "model_checkpoint": "MOCK_PLACEHOLDER",
            "affinity_pred_value": val,
            "affinity_probability_binary": prob,
            "score_definition": S.SCORE_DEFINITION,
            "structure_path": None,
            "is_mock": True,
            "note": "MOCK placeholder for interface demo only — NOT a real Boltz-2 prediction.",
        }

    def predictions_for(self, mutation_id: str | None = None, compound_id: str | None = None) -> list[dict]:
        out = []
        for cx in self.data.complexes_for(mutation_id, compound_id):
            rec = self.get_prediction(cx.complex_id)
            if rec:
                out.append(rec)
        return out

    def compare_wt_mutant(self, compound_id: str) -> dict:
        """WT-vs-mutant predicted values for one compound, across mutations that
        actually have a complex for it. Empty lists where there is no data."""
        preds = self.predictions_for(compound_id=compound_id)
        wt = [p for p in preds if p["mutation_id"] == "EGFR_WT"]
        mut = [p for p in preds if p["mutation_id"] != "EGFR_WT"]
        return {"compound_id": compound_id, "wt": wt, "mutant": mut,
                "any_mock": any(p.get("is_mock") for p in preds)}

    def ranking_for(self, mutation_id: str) -> list[dict]:
        """Inhibitors ranked by predicted value (lower = stronger) for a mutation."""
        preds = self.predictions_for(mutation_id=mutation_id)
        return sorted(preds, key=lambda p: (p["affinity_pred_value"] is None, p["affinity_pred_value"]))

    def mode_label(self) -> str:
        return "REAL (file)" if self.real_mode else "MOCK (placeholder)"
