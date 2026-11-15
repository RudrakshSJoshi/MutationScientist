#!/usr/bin/env python3
"""Generate the Molecular Analysis report (Markdown) from real analysis outputs.
Pulls numbers straight from validation.json / delta_tables.csv / meta — no hardcoded results.
"""
import json, csv, pathlib, datetime
OUT = pathlib.Path.home() / "Desktop/EGFR_TRAINING"
val = json.loads((OUT/"validation.json").read_text())
meta = json.loads((OUT/"boltz_predictions.meta.json").read_text())
preds = json.loads((OUT/"boltz_predictions.json").read_text())
def short(v): return v.replace("EGFR_","").replace("_","/")
def f(x,d=2):
    return "n/a" if x is None else (f"{x:.{d}f}" if isinstance(x,(int,float)) else str(x))

L=[]
L.append("# Molecular Analysis — Boltz-2 affinity on EGFR resistance\n")
L.append(f"*Generated {datetime.date.today().isoformat()} · {meta['n_predicted']} real Boltz-2 predictions · "
         "label = log₁₀(IC50 µM), LOWER = STRONGER, NOT pIC50*\n")
L.append("## Method\n")
L.append("- **Model:** Boltz-2 (2.2.1) pretrained affinity head — inference only (no fine-tune of the affinity head).\n"
         "- **Hardware:** Apple M-series, MLX/MPS (Metal), precision float32, fused kernels off.\n"
         f"- **Sampling settings (per complex, recorded in the JSON):** {json.dumps(meta['settings_legend'])}.\n"
         "- **Inputs:** the dataset's ready-made complexes (full-length EGFR P00533 + ColabFold MSA per variant).\n"
         "- **Ground truth:** each complex's curated experimental `affinity_label` (same units).\n")

L.append("## Validation vs experiment\n")
L.append("| Set | n | Spearman ρ | Pearson r | MAE (log₁₀) |\n|---|--:|--:|--:|--:|")
for k in ("overall","curated_panel","bindingdb"):
    s=val.get(k,{})
    if "spearman" in s:
        L.append(f"| {k.replace('_',' ')} | {s['n']} | {f(s.get('spearman'))} | {f(s.get('pearson'))} | {f(s.get('mae'))} |")
L.append("")
L.append("*Spearman (rank) is the headline — BindingDB IC50 are multi-lab/heterogeneous, so rank "
         "agreement matters more than absolute MAE. Curated-panel rows (BLU-945, JBJ-09-063) are the "
         "cleanest ground truth.*\n")

L.append("## Does Boltz capture the C797S resistance shift?\n")
agree=val.get("c797s_direction_agreement")
L.append(f"Direction agreement (predicted Δ sign vs experimental Δ sign across C797S pairs): "
         f"**{f(agree*100,0) if agree is not None else 'n/a'}%**.\n")
L.append("| Compound | Pair | Predicted Δ | Experimental Δ | Agree |\n|---|---|--:|--:|:--:|")
for p in val.get("c797s_resistance_pairs",[]):
    L.append(f"| {p['compound'].replace('CMP_','')} | {short(p['pair'][0])}→{short(p['pair'][1])} | "
             f"{f(p['pred_delta'])} | {f(p['exp_delta'])} | {'✓' if p.get('direction_agree') else '·'} |")
L.append("\n*(Positive Δ = weaker binding = resistance. Osimertinib is covalent → no Boltz complex, so its "
         "C797S resistance stays in the evidence/LLM layer, not here — by design.)*\n")

L.append("## BLU-945 mutant selectivity (predicted, strongest→weakest)\n")
L.append("| Variant | Predicted | Experimental |\n|---|--:|--:|")
for r in val.get("blu945",[]):
    L.append(f"| {short(r['variant'])} | {f(r['pred'])} | {f(r['exp'])} |")
L.append("")

L.append("## Artifacts\n")
L.append("- `boltz_predictions.json` — app-schema array (feeds `BOLTZ_PREDICTIONS_PATH`).\n"
         "- `baseline_predictions.csv` — full per-complex prediction table.\n"
         "- `wt_mutant_comparisons.csv` — per-compound predicted value per variant + Δ vs WT.\n"
         "- `inhibitor_rankings.csv` — per-mutation inhibitor ranking.\n"
         "- `affinity_landscape.csv` — compound × variant predicted-value matrix.\n"
         "- `validation.json` — these stats in machine form.\n"
         "- `comparison_plots/` — predicted-vs-experiment scatter, BLU-945 ladder, C797S resistance, ranking.\n"
         "- `structural_analysis/` — per-complex ligand–pocket contacts + mutated-residue contact flags.\n")

L.append("## Honest limitations\n")
L.append("- **Coverage:** this is a prioritized subset (curated panel + stratified BindingDB), not all "
         "6,843 eligible complexes — full-length structure prediction is ~minutes/complex on MPS, so the "
         "whole set is a GPU-cluster / Kaggle-P100 / Tamarind job (configs provided), not an overnight-Mac job.\n"
         "- **Mixed sampling settings:** the 8 BLU-945 ladder complexes ran at Boltz-2 defaults; the rest at "
         "reduced settings for throughput. Each record carries its `sampling_settings`.\n"
         "- **Pretrained head:** these are the *pretrained* Boltz-2 affinity predictions, not our fine-tuned head.\n"
         "- **BindingDB labels are noisy** (multi-lab, mixed assay conditions); treat absolute values with care, "
         "prefer the rank/relative signal.\n"
         "- Not for clinical decisions.\n")

MA = OUT/"molecular_analysis"; MA.mkdir(exist_ok=True)
(MA/"MOLECULAR_ANALYSIS_REPORT.md").write_text("\n".join(L))
print("wrote", MA/"MOLECULAR_ANALYSIS_REPORT.md")
