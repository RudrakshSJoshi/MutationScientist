#!/usr/bin/env python3
"""Publication-quality figures from the Boltz analysis outputs.

Reads ~/Desktop/EGFR_TRAINING/{boltz_predictions.json, validation.json, delta_tables.csv}
Writes PNGs (300 dpi) to ~/Desktop/EGFR_TRAINING/figures/.
Palette: Okabe-Ito (colorblind-safe). Diverging blue<->gray<->red for resistance Δ.
Convention: affinity = log10(IC50 uM); LOWER = STRONGER (so a POSITIVE Δ = weaker = resistance).
"""
import json, csv, pathlib, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np

OUT = pathlib.Path.home() / "Desktop/EGFR_TRAINING"
FIG = OUT / "molecular_analysis/comparison_plots"; FIG.mkdir(parents=True, exist_ok=True)
OI = {"blue":"#0072B2","orange":"#E69F00","green":"#009E73","vermillion":"#D55E00",
      "purple":"#CC79A7","sky":"#56B4E9","yellow":"#F0E442","black":"#111111","grey":"#999999"}
plt.rcParams.update({"figure.dpi":120,"font.size":11,"axes.splines.top" if False else "axes.grid":False,
                     "axes.edgecolor":"#444","svg.fonttype":"none"})

preds = json.loads((OUT/"boltz_predictions.json").read_text())
val = json.loads((OUT/"validation.json").read_text())
def short(v): return v.replace("EGFR_","").replace("_","/")

# ---------- Fig 1: predicted vs experimental scatter ----------
def fig_scatter():
    cur=[p for p in preds if p["compound_id"] in ("CMP_BLU945","CMP_JBJ09063") and p["experimental_affinity_label"] is not None]
    bdb=[p for p in preds if p["compound_id"] not in ("CMP_BLU945","CMP_JBJ09063") and p["experimental_affinity_label"] is not None]
    if len(cur)+len(bdb) < 3: return
    fig,ax=plt.subplots(figsize=(6.2,6))
    allx=[p["experimental_affinity_label"] for p in preds if p["experimental_affinity_label"] is not None]
    ally=[p["affinity_pred_value"] for p in preds if p["experimental_affinity_label"] is not None]
    lo=min(allx+ally)-0.5; hi=max(allx+ally)+0.5
    ax.plot([lo,hi],[lo,hi],"--",color=OI["grey"],lw=1.5,zorder=1,label="y = x")
    for grp,col,lab in [(bdb,OI["sky"],"BindingDB (noisier)"),(cur,OI["vermillion"],"Curated panel")]:
        if grp:
            ax.scatter([p["experimental_affinity_label"] for p in grp],
                       [p["affinity_pred_value"] for p in grp],
                       s=46,color=col,edgecolor="white",linewidth=0.6,zorder=3,label=lab)
    s=val["overall"]
    txt=f"Spearman ρ = {s.get('spearman'):.2f}\nPearson r = {s.get('pearson'):.2f}\nMAE = {s.get('mae'):.2f} log₁₀ units\nn = {s['n']}"
    ax.text(0.03,0.97,txt,transform=ax.transAxes,va="top",ha="left",fontsize=10,
            bbox=dict(boxstyle="round",fc="white",ec="#ccc"))
    ax.set_xlabel("Experimental  log₁₀(IC50 / µM)  — lower = stronger")
    ax.set_ylabel("Boltz-2 predicted  log₁₀(IC50 / µM)")
    ax.set_title("Boltz-2 affinity vs experiment (EGFR)")
    ax.set_xlim(lo,hi); ax.set_ylim(lo,hi); ax.set_aspect("equal")
    ax.legend(loc="lower right",frameon=True)
    fig.tight_layout(); fig.savefig(FIG/"fig1_pred_vs_exp.png",dpi=300); plt.close(fig)
    print("wrote fig1_pred_vs_exp.png")

# ---------- Fig 2: BLU-945 resistance ladder (pred vs exp across variants) ----------
def fig_blu():
    blu=val.get("blu945",[])
    if len(blu)<2: return
    blu=sorted(blu,key=lambda r:r["pred"])
    labels=[short(r["variant"]) for r in blu]
    pred=[r["pred"] for r in blu]; exp=[r["exp"] for r in blu]
    x=np.arange(len(blu)); w=0.38
    fig,ax=plt.subplots(figsize=(max(7,len(blu)*1.1),5))
    ax.bar(x-w/2,pred,w,color=OI["blue"],label="Boltz-2 predicted")
    ax.bar(x+w/2,exp,w,color=OI["orange"],label="Experimental")
    ax.set_xticks(x); ax.set_xticklabels(labels,rotation=35,ha="right",fontsize=9)
    ax.set_ylabel("log₁₀(IC50 / µM)  — lower = stronger")
    ax.set_title("BLU-945 across EGFR variants: predicted vs experimental")
    ax.axhline(0,color="#bbb",lw=0.8)
    ax.legend(frameon=True)
    fig.tight_layout(); fig.savefig(FIG/"fig2_blu945_ladder.png",dpi=300); plt.close(fig)
    print("wrote fig2_blu945_ladder.png")

# ---------- Fig 3: C797S resistance Δ (diverging) ----------
def fig_c797():
    pairs=[p for p in val.get("c797s_resistance_pairs",[]) if p.get("pred_delta") is not None]
    if not pairs: return
    pairs=sorted(pairs,key=lambda p:p["pred_delta"])
    labels=[f'{p["compound"].replace("CMP_","")}\n{short(p["pair"][0])}→+C797S' for p in pairs]
    dp=[p["pred_delta"] for p in pairs]
    m=max(abs(min(dp)),abs(max(dp)),0.1)
    norm=TwoSlopeNorm(vmin=-m,vcenter=0,vmax=m)
    cmap=matplotlib.colors.LinearSegmentedColormap.from_list("div",[OI["blue"],"#eeeeee",OI["vermillion"]])
    colors=[cmap(norm(v)) for v in dp]
    fig,ax=plt.subplots(figsize=(7,max(3,len(pairs)*0.5)))
    y=np.arange(len(pairs))
    ax.barh(y,dp,color=colors,edgecolor="white")
    ax.axvline(0,color="#444",lw=1)
    ax.set_yticks(y); ax.set_yticklabels(labels,fontsize=8)
    ax.set_xlabel("Predicted Δ log₁₀(IC50)  (positive → weaker binding = resistance)")
    ax.set_title("Predicted C797S effect on binding")
    fig.tight_layout(); fig.savefig(FIG/"fig3_c797s_resistance.png",dpi=300); plt.close(fig)
    print("wrote fig3_c797s_resistance.png")

# ---------- Fig 4: per-mutation ranking (most populated) ----------
def fig_ranking():
    from collections import defaultdict
    byvar=defaultdict(list)
    for p in preds: byvar[p["mutation_id"]].append(p)
    var=max(byvar,key=lambda v:len(byvar[v]))
    rs=sorted(byvar[var],key=lambda p:p["affinity_pred_value"])
    if len(rs)<3: return
    labels=[r["compound_id"].replace("CMP_","")[:16] for r in rs]
    vals=[r["affinity_pred_value"] for r in rs]
    fig,ax=plt.subplots(figsize=(7,max(3,len(rs)*0.4)))
    y=np.arange(len(rs))[::-1]
    ax.barh(y,vals,color=OI["green"],edgecolor="white")
    ax.set_yticks(y); ax.set_yticklabels(labels,fontsize=8)
    ax.set_xlabel("Boltz-2 predicted log₁₀(IC50 / µM) — lower = stronger")
    ax.set_title(f"Inhibitor ranking for {short(var)} (n={len(rs)})")
    fig.tight_layout(); fig.savefig(FIG/"fig4_ranking.png",dpi=300); plt.close(fig)
    print("wrote fig4_ranking.png")

for fn in (fig_scatter,fig_blu,fig_c797,fig_ranking):
    try: fn()
    except Exception as e: print("skip",fn.__name__,":",e)
print("figures in",FIG)
