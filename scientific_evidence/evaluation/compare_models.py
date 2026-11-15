#!/usr/bin/env python3
"""
compare_models.py — base vs fine-tuned, side by side (Person 3, follow-up s1/s4).

Reads the per-model reports written by run_benchmark.py (report.<tag>.json) and
produces the base-vs-finetuned comparison that backs the "Best Use of Adaption"
story: the fine-tune is both more correct AND at least as grounded (fabrication
rate ~0).  Deterministic; reads only what the scorers already recorded.

Run (after both model runs exist):
    python -m scientific_evidence.evaluation.compare_models \
        --finetuned report.finetuned.json --base report.base.json

Outputs: base_vs_finetuned.md and base_vs_finetuned.json (next to this file).
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# metric key -> (label, better_direction)  higher=+1, lower=-1
METRICS = [
    ("pass_rate", "Pass rate", +1),
    ("mean_factual", "Mean factual correctness", +1),
    ("items_with_fabrication", "Items with fabricated numbers", -1),
    ("items_with_invented_citation", "Items with invented DOI/PMID", -1),
    ("citation_recall", "Citation recall", +1),
    ("conflation_items", "Biochem/cellular conflation flags", -1),
    ("hedge_missing", "Hedging missing (of required)", -1),
    ("mean_jaccard", "Mean overlap vs reference (Jaccard)", +1),
]


def _fmt(key, val):
    if key in ("pass_rate", "mean_factual", "citation_recall", "mean_jaccard"):
        return f"{val:.1%}" if key in ("pass_rate", "citation_recall") else f"{val:.3f}"
    return str(val)


def _load(name):
    p = HERE / name if not Path(name).is_absolute() else Path(name)
    return json.loads(p.read_text(encoding="utf-8"))


def _examples(ft, base):
    """Illustrative items: fine-tune fixed a base failure; and honest FT limitations."""
    bi = {i["id"]: i for i in base["items"]}
    fixed, remaining = [], []
    for fi in ft["items"]:
        b = bi.get(fi["id"])
        if not b:
            continue
        fp, bp = fi["scores"]["passed"], b["scores"]["passed"]
        if fp and not bp:
            fixed.append((fi, b))
        elif not fp:
            remaining.append((fi, b))
    return fixed, remaining


def _issue(sc):
    out = []
    g = sc["grounding"]
    if g["n_ungrounded"]:
        out.append("fabricated#: " + ", ".join(g["ungrounded"][:4]))
    c = sc["citation"]
    if c["has_invented_citation"]:
        out.append("invented-cite: " + ", ".join((c["invented_dois"] + c["invented_pmids"])[:3]))
    if c["n_expected"] and not c["expected_satisfied"]:
        out.append("missing expected citation")
    if sc["factual"]["missed"]:
        out.append("missing: " + "; ".join(str(m) for m in sc["factual"]["missed"][:3]))
    if sc["conflation"]["conflation"]:
        out.append("conflation")
    if sc["requires_hedge"] and not sc["hedging"]["hedged"]:
        out.append("no hedging")
    return "; ".join(out) or "ok"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--finetuned", default="report.finetuned.json")
    ap.add_argument("--base", default="report.base.json")
    args = ap.parse_args()

    ft, base = _load(args.finetuned), _load(args.base)
    fo, bo = ft["overall"], base["overall"]

    rows = []
    for key, label, direction in METRICS:
        fv, bv = fo[key], bo[key]
        delta = fv - bv
        winner = "fine-tuned" if delta * direction > 0 else ("base" if delta * direction < 0 else "tie")
        rows.append({"metric": key, "label": label, "finetuned": fv, "base": bv,
                     "delta": round(delta, 4), "better": winner})

    fixed, remaining = _examples(ft, base)

    out_json = {"finetuned_model": ft["model"], "base_model": base["model"],
                "n_items": fo["n"], "metrics": rows,
                "n_fixed_by_finetune": len(fixed),
                "n_remaining_finetune_failures": len(remaining)}
    (HERE / "base_vs_finetuned.json").write_text(
        json.dumps(out_json, indent=2, ensure_ascii=False), encoding="utf-8")

    md = ["# Base vs fine-tuned — independent EGFR benchmark\n",
          f"- **Fine-tuned:** `{ft['model']}`",
          f"- **Base:** `{base['model']}`",
          f"- **Items:** {fo['n']} (identical independent benchmark, identical deterministic scorers, "
          "temperature 0)\n",
          "## Headline metrics\n",
          "| Metric | Fine-tuned | Base | Δ (ft−base) | Better |",
          "|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['label']} | {_fmt(r['metric'], r['finetuned'])} | "
                  f"{_fmt(r['metric'], r['base'])} | {_fmt(r['metric'], r['delta'])} | **{r['better']}** |")

    md += ["", "## Pass rate by task category\n",
           "| Category | Fine-tuned | Base |", "|---|---|---|"]
    for cat in sorted(set(ft["by_task_type"]) | set(base["by_task_type"])):
        f = ft["by_task_type"].get(cat, {})
        b = base["by_task_type"].get(cat, {})
        fp = f"{f.get('passed',0)}/{f.get('n',0)}" if f else "—"
        bp = f"{b.get('passed',0)}/{b.get('n',0)}" if b else "—"
        md.append(f"| {cat} | {fp} | {bp} |")

    md += ["", f"## Where the fine-tune fixed a base failure ({len(fixed)})\n"]
    if fixed:
        md.append("| id | task | base failure | fine-tuned |")
        md.append("|---|---|---|---|")
        for fi, b in fixed[:8]:
            md.append(f"| {fi['id']} | {fi['task_type']} | {_issue(b['scores'])[:120]} | passed |")
    else:
        md.append("_No item where the fine-tune passed and the base failed._")

    md += ["", f"## Honest limitations — items the fine-tune still failed ({len(remaining)})\n"]
    if remaining:
        md.append("| id | task | fine-tuned issue |")
        md.append("|---|---|---|")
        for fi, _b in remaining[:10]:
            md.append(f"| {fi['id']} | {fi['task_type']} | {_issue(fi['scores'])[:140]} |")
    else:
        md.append("_None — the fine-tune passed every item._")
    md.append("")
    (HERE / "base_vs_finetuned.md").write_text("\n".join(md), encoding="utf-8")

    print(f"fine-tuned {ft['model']}  vs  base {base['model']}")
    for r in rows:
        print(f"  {r['label']:38s} ft={_fmt(r['metric'], r['finetuned']):>8s}  "
              f"base={_fmt(r['metric'], r['base']):>8s}  -> {r['better']}")
    print(f"fixed-by-finetune: {len(fixed)}   remaining-ft-failures: {len(remaining)}")
    print(f"Wrote {HERE/'base_vs_finetuned.md'} and base_vs_finetuned.json")


if __name__ == "__main__":
    main()
