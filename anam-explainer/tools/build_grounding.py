#!/usr/bin/env python3
"""
build_grounding.py — regenerate the Anam avatar's grounded context packs from the
REAL EGFR dataset + REAL Boltz-2 predictions, reusing the MutationScientist app's
own services so the avatar receives EXACTLY the context the research app uses.

Outputs (committed, self-contained — the running app needs neither this script nor
the dataset at demo time):
  ../data/contexts.json         one grounded context per hero pair (real numbers only)
And, as a side effect, the consolidated real predictions file:
  ~/Desktop/EGFR_TRAINING/boltz_predictions.json   (agreed Person-2 schema, REAL)

Run:  python3 tools/build_grounding.py
Requires the local research app at ~/Desktop/application and the EGFR dataset.
Nothing here fabricates data: every value traces to the dataset or the Boltz run.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path

APP = Path(os.environ.get("MS_APP_DIR", "~/Desktop/application")).expanduser()
TRAIN = Path("~/Desktop/EGFR_TRAINING").expanduser()
BOLTZ_RUN = TRAIN / "boltz_run"
HERE = Path(__file__).resolve().parent
DATA_OUT = HERE.parent / "data" / "contexts.json"
PRED_OUT = TRAIN / "boltz_predictions.json"

# The two hero pairs (user-chosen). Pair A is covalent (no Boltz complex -> honest
# "no prediction"); pair B has a real Boltz prediction on screen.
HERO_A = {"key": "osimertinib_resistance", "mutation": "EGFR_L858R_C797S", "compound": "CMP_OSIMERTINIB",
          "title": "C797S resistance to osimertinib",
          "question": "How does the C797S mutation affect osimertinib binding, and what does the evidence say about resistance?",
          # Sensitising baseline (C797S absent) so the resistance fold-change is grounded in-context.
          "comparison": {"mutation": "EGFR_L858R", "compound": "CMP_OSIMERTINIB",
                         "label": "sensitising baseline: L858R without C797S"}}
HERO_B = {"key": "blu945_prediction", "mutation": "EGFR_L858R_C797S", "compound": "CMP_BLU945",
          "title": "BLU-945 vs L858R/C797S (real Boltz prediction)",
          "question": "What does the Boltz-2 prediction say about BLU-945 against L858R/C797S, and how does it compare to the measured potency?"}


def find_real_affinity():
    """Locate every real Boltz affinity_*.json in the run and map complex_id -> (aff, conf)."""
    out = {}
    for aff in BOLTZ_RUN.rglob("affinity_COMPLEX_*.json"):
        cid = aff.stem.replace("affinity_", "")
        try:
            a = json.loads(aff.read_text())
        except Exception:
            continue
        conf = {}
        cdir = aff.parent
        cfile = cdir / f"confidence_{cid}_model_0.json"
        if cfile.exists():
            try: conf = json.loads(cfile.read_text())
            except Exception: conf = {}
        cif = next(iter(cdir.glob(f"{cid}_model_0.cif")), None) or next(iter(cdir.glob("*.cif")), None)
        out[cid] = (a, conf, str(cif) if cif else None)
    return out


def main():
    sys.path.insert(0, str(APP))
    os.chdir(APP)
    import config.settings as S
    from services.dataset_service import DatasetService
    from services.evidence_service import EvidenceService
    from services.boltz_service import BoltzService
    from services.llm_service import LLMService

    data = DatasetService()
    real_aff = find_real_affinity()
    print(f"[boltz] real affinity predictions found: {list(real_aff)}")

    # ---- 1) consolidate REAL predictions into the agreed schema -------------
    preds_file = []
    for cid, (a, conf, cif) in real_aff.items():
        cx = data.get_complex(cid)
        if cx is None:
            print(f"[warn] complex {cid} not in dataset loader; skipping"); continue
        rec = {
            "complex_id": cid,
            "mutation_id": cx.mutation_id,
            "compound_id": cx.compound_id,
            "model_version": "boltz-2",
            "model_checkpoint": "pretrained",  # affinity head not fine-tuned (open item #1)
            "affinity_pred_value": a.get("affinity_pred_value"),
            # Pre-computed IC50 (nM) equivalents from score_definition (10**(value+3)) so the model
            # states correct potencies instead of re-deriving the log scale. Deterministic, not fabricated.
            "affinity_pred_ic50_nM_equiv": round(10 ** (a.get("affinity_pred_value") + 3), 2) if a.get("affinity_pred_value") is not None else None,
            "experimental_ic50_nM_equiv": round(10 ** (cx.affinity_label + 3), 2) if cx.affinity_label is not None else None,
            "affinity_probability_binary": a.get("affinity_probability_binary"),
            "affinity_pred_ensemble": [a.get("affinity_pred_value1"), a.get("affinity_pred_value2")],
            "confidence_score": conf.get("confidence_score"),
            "ligand_iptm": conf.get("ligand_iptm"),
            "complex_plddt": conf.get("complex_plddt"),
            "experimental_affinity_label": cx.affinity_label,  # ground truth for compare
            "score_definition": S.SCORE_DEFINITION,
            "structure_path": cif,
            "is_mock": False,
        }
        preds_file.append(rec)
        print(f"[boltz] {cid}: {cx.mutation_id} x {cx.compound_id}  pred={rec['affinity_pred_value']:.3f}  exp={cx.affinity_label}")
    PRED_OUT.write_text(json.dumps(preds_file, indent=2))
    print(f"[write] {PRED_OUT}  ({len(preds_file)} real prediction(s))")

    # ---- 2) build grounded hero contexts (REAL boltz now loaded) -----------
    boltz = BoltzService(data, predictions_path=PRED_OUT)
    evsvc = EvidenceService(data)
    llm = LLMService()
    print(f"[boltz] real_mode={boltz.real_mode}  [llm] {llm.mode_label()}")

    packs = {}
    for hero in (HERO_A, HERO_B):
        mid, cid = hero["mutation"], hero["compound"]
        mutation = data.get_mutation(mid)
        compound = data.get_compound(cid)
        if mutation is None or compound is None:
            print(f"[warn] {mid} x {cid}: mutation/compound missing (mut={mutation is not None}, cmp={compound is not None})")
        complexes = data.complexes_for(mutation_id=mid, compound_id=cid)
        preds = [boltz.get_prediction(c.complex_id) for c in complexes]
        preds = [p for p in preds if p]
        meas = data.measurements_for(mutation_id=mid, compound_id=cid)
        ev = evsvc.retrieve(mutation_id=mid, compound_id=cid, match="any")["evidence"]
        ctx = llm.build_context(mutation, compound, preds, ev, meas, data)
        # Optional grounded comparison (e.g. the sensitising baseline for a resistance story).
        cmpspec = hero.get("comparison")
        if cmpspec:
            cmeas = data.measurements_for(mutation_id=cmpspec["mutation"], compound_id=cmpspec["compound"])
            ctx["comparison_measurements"] = {
                "label": cmpspec["label"],
                "mutation_id": cmpspec["mutation"], "compound_id": cmpspec["compound"],
                "measurements": [{
                    "measurement_type": m.get("measurement_type"), "value": m.get("original_value"),
                    "unit": m.get("original_unit"), "relation": m.get("measurement_relation"),
                    "source": m.get("publication") or m.get("source_database"),
                } for m in (cmeas or [])],
            }
        # compact on-screen card (only real values)
        realpred = next((p for p in preds if not p.get("is_mock")), None)
        card = {
            "mutation": (mutation or {}).get("mutation_notation") or mid,
            "compound": (compound or {}).get("compound_name") or cid,
            "drug_class": (compound or {}).get("drug_class"),
            "covalent": (compound or {}).get("covalent_status"),
            "has_real_prediction": bool(realpred),
            "affinity_pred_value": realpred.get("affinity_pred_value") if realpred else None,
            "affinity_probability_binary": realpred.get("affinity_probability_binary") if realpred else None,
            "confidence_score": realpred.get("confidence_score") if realpred else None,
            "experimental_affinity_label": realpred.get("experimental_affinity_label") if realpred else None,
            "measurements": [
                {"type": m.get("measurement_type"), "value": m.get("original_value"),
                 "unit": m.get("original_unit"), "relation": m.get("measurement_relation"),
                 "source": (m.get("publication") or m.get("source_database") or "").split(",")[0]}
                for m in (meas or [])
            ],
            "headline_claim": (ev[0]["claim"] if ev else None),
            "n_evidence": len(ev),
            "score_definition": S.SCORE_DEFINITION,
        }
        packs[hero["key"]] = {
            "title": hero["title"], "question": hero["question"],
            "mutation_id": mid, "compound_id": cid,
            "card": card, "context": ctx,
        }
        print(f"[pack] {hero['key']}: preds={len(preds)} meas={len(meas)} ev={len(ev)} real_pred={bool(realpred)}")

    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    DATA_OUT.write_text(json.dumps(packs, indent=2))
    print(f"[write] {DATA_OUT}")


if __name__ == "__main__":
    main()
