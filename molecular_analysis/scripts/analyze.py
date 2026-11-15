#!/usr/bin/env python3
"""Aggregate ALL Boltz affinity outputs + build the full analysis.

Sources:
  results/        -> the 8 BLU-945 ladder at Boltz-2 DEFAULTS (recycle3/ss200/dsa5)
  results_night/  -> the overnight queue at REDUCED settings (recycle1/ss50/dsa3)

Outputs (to ~/Desktop/EGFR_TRAINING/):
  boltz_predictions.json        app-schema array (feeds BOLTZ_PREDICTIONS_PATH)
  boltz_predictions.meta.json   run metadata, settings per complex, failures
  delta_tables.csv              per-compound predicted value per variant + Δ vs WT
  rankings.csv                  per-mutation inhibitor ranking (pred, lower=stronger)
  validation.json               Spearman + MAE (overall/curated/bindingdb) + C797S + BLU945
Label convention: affinity = log10(IC50 uM); LOWER = STRONGER; NOT pIC50.
"""
import sys, os, json, csv, math, pathlib
HOME = pathlib.Path.home()
sys.path.insert(0, str(HOME / "Desktop"))
from egfr_dataset_loader import EGFRDataset

RUN = HOME / "Desktop/EGFR_TRAINING/boltz_run"
OUT = HOME / "Desktop/EGFR_TRAINING"
DS = HOME / "Desktop/EGFR_RESEARCH_DATASET"
SETTINGS = {"results": "boltz2-defaults(recycle3,ss200,affens5)",
            "results_night": "reduced(recycle1,ss50,affens3)"}
SCORE_DEF = ("Boltz-2 pretrained affinity head, affinity_pred_value = log10(IC50 uM); "
             "LOWER = STRONGER. affinity_probability_binary = P(binder).")

def spearman(xs, ys):
    n = len(xs)
    if n < 3: return None
    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0]*n; i = 0
        while i < n:
            j = i
            while j+1 < n and v[order[j+1]] == v[order[i]]: j += 1
            avg = (i+j)/2.0 + 1
            for k in range(i, j+1): r[order[k]] = avg
            i = j+1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx)/n, sum(ry)/n
    cov = sum((rx[i]-mx)*(ry[i]-my) for i in range(n))
    vx = math.sqrt(sum((rx[i]-mx)**2 for i in range(n)))
    vy = math.sqrt(sum((ry[i]-my)**2 for i in range(n)))
    return cov/(vx*vy) if vx and vy else None

def pearson(xs, ys):
    n=len(xs)
    if n<3: return None
    mx,my=sum(xs)/n,sum(ys)/n
    cov=sum((xs[i]-mx)*(ys[i]-my) for i in range(n))
    vx=math.sqrt(sum((x-mx)**2 for x in xs)); vy=math.sqrt(sum((y-my)**2 for y in ys))
    return cov/(vx*vy) if vx and vy else None

def main():
    ds = EGFRDataset(str(DS))
    meta = {c.complex_id: c for sp in ("train","validation","test") for c in ds.boltz.split(sp)}

    recs = {}
    for sub, label in SETTINGS.items():
        base = RUN / sub
        if not base.exists(): continue
        for aj in base.rglob("affinity_*.json"):
            cid = aj.stem.replace("affinity_", "")
            cx = meta.get(cid)
            if cx is None: continue
            d = json.loads(aj.read_text())
            struct = None
            for cand in sorted(aj.parent.glob(f"{cid}_model_*.cif")):
                struct = str(cand.resolve()); break
            recs[cid] = {   # later dir (results_night) does NOT override defaults: prefer defaults
                "complex_id": cid, "mutation_id": cx.mutation_id, "compound_id": cx.compound_id,
                "model_version": "boltz-2.2.1", "model_checkpoint": "pretrained",
                "affinity_pred_value": d["affinity_pred_value"],
                "affinity_probability_binary": d["affinity_probability_binary"],
                "score_definition": SCORE_DEF, "structure_path": struct,
                "experimental_affinity_label": cx.affinity_label,
                "sampling_settings": label,
            } if (cid not in recs or sub == "results") else recs[cid]

    records = list(recs.values())
    records.sort(key=lambda r: (r["compound_id"], r["mutation_id"]))

    MA = OUT / "molecular_analysis"; MA.mkdir(exist_ok=True)

    # --- app-schema array (root, feeds BOLTZ_PREDICTIONS_PATH) + meta ---
    (OUT / "boltz_predictions.json").write_text(json.dumps(records, indent=2))
    (OUT / "boltz_predictions.meta.json").write_text(json.dumps({
        "label_convention": "log10(IC50 uM); LOWER=STRONGER; NOT pIC50",
        "generated_by": "boltz predict (affinity) on Apple MPS, precision 32-true, no_kernels",
        "n_predicted": len(records),
        "settings_legend": SETTINGS, "score_definition": SCORE_DEF,
    }, indent=2))

    # --- baseline_predictions.csv (person2 spec) ---
    cols=["complex_id","mutation_id","compound_id","model_version","model_checkpoint",
          "affinity_pred_value","affinity_probability_binary","experimental_affinity_label",
          "sampling_settings","structure_path"]
    with open(MA/"baseline_predictions.csv","w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
        for r in records: w.writerow({k:r.get(k) for k in cols})

    from collections import defaultdict
    bycomp = defaultdict(dict)
    for r in records: bycomp[r["compound_id"]][r["mutation_id"]] = r

    # --- wt_mutant_comparisons.csv (Δ vs WT) ---
    with open(MA/"wt_mutant_comparisons.csv","w",newline="") as f:
        w=csv.writer(f); w.writerow(["compound_id","variant","pred","exp","pred_delta_vs_WT","exp_delta_vs_WT"])
        for comp, vmap in sorted(bycomp.items()):
            wt = vmap.get("EGFR_WT")
            for var,r in sorted(vmap.items()):
                pdw = (r["affinity_pred_value"]-wt["affinity_pred_value"]) if wt else ""
                edw = (r["experimental_affinity_label"]-wt["experimental_affinity_label"]) if (wt and r["experimental_affinity_label"] is not None and wt["experimental_affinity_label"] is not None) else ""
                w.writerow([comp,var,round(r["affinity_pred_value"],4),r["experimental_affinity_label"],
                            round(pdw,4) if pdw!="" else "", round(edw,4) if edw!="" else ""])

    # --- inhibitor_rankings.csv (per mutation) ---
    byvar = defaultdict(list)
    for r in records: byvar[r["mutation_id"]].append(r)
    with open(MA/"inhibitor_rankings.csv","w",newline="") as f:
        w=csv.writer(f); w.writerow(["mutation_id","rank","compound_id","pred","exp"])
        for var,rs in sorted(byvar.items()):
            for i,r in enumerate(sorted(rs,key=lambda x:x["affinity_pred_value"]),1):
                w.writerow([var,i,r["compound_id"],round(r["affinity_pred_value"],4),r["experimental_affinity_label"]])

    # --- affinity_landscape.csv (compound x variant matrix of predicted value) ---
    variants=sorted({r["mutation_id"] for r in records})
    with open(MA/"affinity_landscape.csv","w",newline="") as f:
        w=csv.writer(f); w.writerow(["compound_id"]+[v.replace("EGFR_","") for v in variants])
        for comp,vmap in sorted(bycomp.items()):
            w.writerow([comp]+[round(vmap[v]["affinity_pred_value"],4) if v in vmap else "" for v in variants])

    # --- screening_results.csv (long form with Δ) ---
    with open(MA/"screening_results.csv","w",newline="") as f:
        w=csv.writer(f); w.writerow(["complex_id","compound_id","mutation_id","pred","prob_binder","exp","pred_minus_exp","sampling_settings"])
        for r in records:
            e=r["experimental_affinity_label"]
            w.writerow([r["complex_id"],r["compound_id"],r["mutation_id"],round(r["affinity_pred_value"],4),
                        round(r["affinity_probability_binary"],4),e,
                        round(r["affinity_pred_value"]-e,4) if e is not None else "",r["sampling_settings"]])

    # --- validation: predicted vs experimental ---
    def stats(rs):
        pair=[(r["affinity_pred_value"],r["experimental_affinity_label"]) for r in rs
              if r["experimental_affinity_label"] is not None]
        if len(pair)<3: return {"n":len(pair)}
        p=[a for a,b in pair]; e=[b for a,b in pair]
        mae=sum(abs(a-b) for a,b in pair)/len(pair)
        return {"n":len(pair),"spearman":spearman(p,e),"pearson":pearson(p,e),
                "mae":mae,"pred_range":[min(p),max(p)],"exp_range":[min(e),max(e)]}
    curated={"CMP_BLU945","CMP_JBJ09063"}
    val={"overall":stats(records),
         "curated_panel":stats([r for r in records if r["compound_id"] in curated]),
         "bindingdb":stats([r for r in records if r["compound_id"] not in curated])}

    # --- C797S resistance direction check ---
    c797=[]
    for comp,vmap in bycomp.items():
        for var,r in vmap.items():
            if var.endswith("_C797S"):
                base=var[:-len("_C797S")]
                br=vmap.get(base) or vmap.get("EGFR_"+base.replace("EGFR_",""))
                if base=="EGFR": br=vmap.get("EGFR_WT")
                if br:
                    dp=r["affinity_pred_value"]-br["affinity_pred_value"]
                    de=(r["experimental_affinity_label"]-br["experimental_affinity_label"]) if (r["experimental_affinity_label"] is not None and br["experimental_affinity_label"] is not None) else None
                    c797.append({"compound":comp,"pair":[base,var],
                                 "pred_delta":round(dp,4),
                                 "exp_delta":round(de,4) if de is not None else None,
                                 "direction_agree":(de is not None and (dp>0)==(de>0))})
    val["c797s_resistance_pairs"]=c797
    agree=[x for x in c797 if x["exp_delta"] is not None]
    val["c797s_direction_agreement"]=(sum(x["direction_agree"] for x in agree)/len(agree)) if agree else None

    # --- BLU-945 selectivity ---
    blu=bycomp.get("CMP_BLU945",{})
    val["blu945"]=[{"variant":v,"pred":round(r["affinity_pred_value"],4),"exp":r["experimental_affinity_label"]}
                   for v,r in sorted(blu.items(),key=lambda kv:kv[1]["affinity_pred_value"])]

    (OUT/"validation.json").write_text(json.dumps(val,indent=2,default=str))

    print(f"predictions: {len(records)}")
    for k,s in val.items():
        if isinstance(s,dict) and "spearman" in s:
            print(f"  {k:14} n={s['n']} spearman={s.get('spearman')} mae={s.get('mae')}")
    print("c797s direction agreement:", val["c797s_direction_agreement"])
    print("wrote boltz_predictions.json, delta_tables.csv, rankings.csv, validation.json")

if __name__=="__main__":
    main()
