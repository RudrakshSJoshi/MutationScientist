#!/usr/bin/env python3
"""Export the REAL Boltz-2 complexes to the React frontend at ~/Desktop/product/.

- data/predictions.json : array of {complex_id, mutation_id, compound_id,
    affinity_pred_value, affinity_probability_binary, experimental_affinity_label,
    structure_path} with structure_path rewritten to relative "structures/<id>.cif".
- structures/<complex_id>.cif : the predicted structure for the browser 3Dmol viewer.
- data/screening.json : WT-vs-mutant delta table per compound.
Only complexes Boltz actually produced (a readable .cif) are included. No fabrication.
label: affinity_pred_value = log10(IC50 µM), LOWER = STRONGER, NOT pIC50.
"""
import json, shutil, pathlib
from collections import defaultdict

SRC = pathlib.Path.home()/"Desktop/EGFR_TRAINING/boltz_predictions.json"
PROD = pathlib.Path.home()/"Desktop/product"
(PROD/"data").mkdir(parents=True, exist_ok=True)
(PROD/"structures").mkdir(parents=True, exist_ok=True)

preds = json.loads(SRC.read_text())
FIELDS = ["complex_id","mutation_id","compound_id","affinity_pred_value",
          "affinity_probability_binary","experimental_affinity_label","structure_path"]

out = []
copied = skipped = 0
for r in preds:
    sp = r.get("structure_path")
    if not sp or not pathlib.Path(sp).exists():
        skipped += 1
        continue   # never emit a complex without a real produced structure
    cid = r["complex_id"]
    dst = PROD/"structures"/f"{cid}.cif"
    shutil.copyfile(sp, dst)
    copied += 1
    out.append({
        "complex_id": cid,
        "mutation_id": r["mutation_id"],
        "compound_id": r["compound_id"],
        "affinity_pred_value": round(r["affinity_pred_value"], 4),
        "affinity_probability_binary": round(r["affinity_probability_binary"], 4),
        "experimental_affinity_label": r.get("experimental_affinity_label"),
        "structure_path": f"structures/{cid}.cif",
    })
out.sort(key=lambda r: (r["compound_id"], r["mutation_id"]))
(PROD/"data"/"predictions.json").write_text(json.dumps(out, indent=2))

# --- screening.json: WT-vs-mutant delta per compound (same ligand across variants) ---
bycomp = defaultdict(dict)
for r in out: bycomp[r["compound_id"]][r["mutation_id"]] = r
screening = []
for comp, vm in sorted(bycomp.items()):
    if len(vm) < 2: continue   # a delta table needs >=2 variants
    ref = vm.get("EGFR_WT") or vm.get("EGFR_L858R") or sorted(vm.values(), key=lambda r:r["affinity_pred_value"])[0]
    refv = ref["mutation_id"]
    rows = []
    for var, r in vm.items():
        dp = round(r["affinity_pred_value"] - ref["affinity_pred_value"], 4)
        de = (round(r["experimental_affinity_label"] - ref["experimental_affinity_label"], 4)
              if (r["experimental_affinity_label"] is not None and ref["experimental_affinity_label"] is not None) else None)
        rows.append({"variant": var, "pred": r["affinity_pred_value"],
                     "exp": r["experimental_affinity_label"],
                     "delta_pred_vs_ref": dp, "delta_exp_vs_ref": de})
    rows.sort(key=lambda x: x["pred"])
    screening.append({"compound_id": comp, "reference_variant": refv,
                      "reference_is_WT": refv == "EGFR_WT", "n_variants": len(vm), "variants": rows})
(PROD/"data"/"screening.json").write_text(json.dumps({
    "label_convention": "affinity_pred_value = log10(IC50 uM); LOWER = STRONGER; NOT pIC50",
    "note": "delta_*_vs_ref relative to reference_variant (WT where available, else mildest predicted variant). Negative delta = stronger than reference.",
    "compounds": screening}, indent=2))

hero = [r for r in out if r["complex_id"] == "COMPLEX_001557"]
print(f"predictions.json: {len(out)} complexes ({copied} cif copied, {skipped} skipped-no-structure)")
print(f"screening.json: {len(screening)} compounds with >=2 variants")
print(f"hero COMPLEX_001557 present: {bool(hero)}", hero[0] if hero else "")
