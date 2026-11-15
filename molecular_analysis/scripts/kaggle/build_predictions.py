#!/usr/bin/env python3
"""Aggregate boltz affinity outputs into ~/Desktop/EGFR_TRAINING/boltz_predictions.json.

Reads every affinity_<COMPLEX_ID>.json under the given boltz results dir(s),
joins complex metadata from the EGFR dataset loader, and emits one record per
complex in the app's schema. Also records complexes that FAILED (no affinity
json produced) so the output is honest about coverage.

Usage:
  python build_predictions.py OUT_JSON RESULTS_DIR [RESULTS_DIR ...] \
      --expected COMPLEX_ID,COMPLEX_ID,...
"""
import sys, os, json, argparse, pathlib

HOME = pathlib.Path.home()
sys.path.insert(0, str(HOME / "Desktop"))
from egfr_dataset_loader import EGFRDataset  # noqa: E402

DS_ROOT = pathlib.Path(os.environ.get("EGFR_DS_ROOT", HOME / "Desktop/EGFR_RESEARCH_DATASET"))
BOLTZ_VERSION = "boltz-2.2.1"
SCORE_DEF = ("Boltz-2 pretrained affinity head, raw affinity_pred_value = "
             "log10(IC50 in uM); LOWER = STRONGER (same convention as the "
             "dataset label). affinity_probability_binary = P(binder).")


def build_meta_index():
    ds = EGFRDataset(str(DS_ROOT))
    idx = {}
    for sp in ("train", "validation", "test"):
        for cx in ds.boltz.split(sp):
            idx[cx.complex_id] = cx
    return idx


def find_affinity_jsons(results_dirs):
    found = {}
    for rd in results_dirs:
        for p in pathlib.Path(rd).rglob("affinity_*.json"):
            cid = p.stem.replace("affinity_", "")
            found[cid] = p
    return found


def structure_for(affinity_json: pathlib.Path, cid: str):
    d = affinity_json.parent
    for cand in sorted(d.glob(f"{cid}_model_*.cif")) + sorted(d.glob(f"{cid}_model_*.pdb")):
        return str(cand.resolve())
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_json")
    ap.add_argument("results_dirs", nargs="+")
    ap.add_argument("--expected", default="", help="comma list of complex_ids expected")
    args = ap.parse_args()

    meta = build_meta_index()
    found = find_affinity_jsons(args.results_dirs)
    expected = [c for c in args.expected.split(",") if c] or sorted(found)

    records, failed = [], []
    for cid in expected:
        cx = meta.get(cid)
        aj = found.get(cid)
        if aj is None:
            failed.append({"complex_id": cid,
                           "mutation_id": getattr(cx, "mutation_id", None),
                           "compound_id": getattr(cx, "compound_id", None),
                           "reason": "no affinity output produced"})
            continue
        data = json.loads(aj.read_text())
        rec = {
            "complex_id": cid,
            "mutation_id": getattr(cx, "mutation_id", None),
            "compound_id": getattr(cx, "compound_id", None),
            "model_version": BOLTZ_VERSION,
            "model_checkpoint": "pretrained",
            "affinity_pred_value": data["affinity_pred_value"],
            "affinity_probability_binary": data["affinity_probability_binary"],
            "score_definition": SCORE_DEF,
            "structure_path": structure_for(aj, cid),
        }
        # carry the experimental label for side-by-side context (not a prediction)
        if cx is not None:
            rec["experimental_affinity_label"] = cx.affinity_label
        records.append(rec)

    # Main file: a PLAIN ARRAY of records — exactly what the app's
    # boltz_service._load_real consumes via BOLTZ_PREDICTIONS_PATH.
    out_path = pathlib.Path(args.out_json)
    out_path.write_text(json.dumps(records, indent=2))

    # Sidecar: run metadata + failures (kept out of the app-consumed file so
    # raw.values() in the service only ever sees records).
    meta = {
        "schema_version": "1.0",
        "label_convention": "log10(IC50 in uM); LOWER = STRONGER; NOT pIC50",
        "model_version": BOLTZ_VERSION,
        "model_checkpoint": "pretrained",
        "generated_by": "boltz predict (affinity) on Apple MPS, precision 32-true, no_kernels",
        "score_definition": SCORE_DEF,
        "n_predicted": len(records),
        "n_failed": len(failed),
        "predicted_complex_ids": [r["complex_id"] for r in records],
        "failed": failed,
    }
    meta_path = out_path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"wrote {out_path}: {len(records)} predicted, {len(failed)} failed")
    print(f"wrote {meta_path}: run metadata + failures")
    for r in records:
        print(f"  {r['complex_id']} {r['mutation_id']:<24} {r['compound_id']:<12} "
              f"pred={r['affinity_pred_value']:+.4f}  exp={r.get('experimental_affinity_label')}")
    for f in failed:
        print(f"  FAILED {f['complex_id']} {f.get('mutation_id')} — {f['reason']}")


if __name__ == "__main__":
    main()
