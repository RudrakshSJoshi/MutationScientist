#!/usr/bin/env python3
"""
make_figures.py — figures for the Scientific Validation Report (Person 3, follow-up s4).

Pure Python standard library: emits self-contained SVG (renders on GitHub and in
any browser; no matplotlib, no network).  Reads the reports written by
run_benchmark.py (report.*.json) and the EGFR_TRAINING harness
(harness_report.*.json), both already copied next to this file.

Figures produced (only those whose inputs exist):
  fig_fabrication.svg   headline: fabrication-rate + conflation-rate, fine-tuned vs base
                        (218-item harness, closed-book) — lower is better
  fig_by_category.svg   per-task fabrication rate, fine-tuned vs base (harness)
  fig_rag.svg           fine-tune closed-book vs RAG/open-book — citation recall up,
                        invented-citation + fabricated-number items down

Run:
    python -m scientific_evidence.evaluation.make_figures
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
A_COLOR = "#2563eb"   # series A (fine-tuned / with-RAG) — blue
B_COLOR = "#9ca3af"   # series B (base / closed-book) — grey
GOOD = "#16a34a"
BAD = "#dc2626"
INK = "#111827"
MUTE = "#6b7280"
BG = "#ffffff"


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def grouped_bar_svg(title, subtitle, categories, a_vals, b_vals, legend,
                    *, as_pct=True, width=760, colors=(A_COLOR, B_COLOR),
                    value_suffix=""):
    n = len(categories)
    pad_l, pad_r, pad_t, pad_b = 54, 20, 72, 100
    plot_w = width - pad_l - pad_r
    plot_h = 300
    height = pad_t + plot_h + pad_b
    vmax = 1.0 if as_pct else max([*a_vals, *b_vals, 1e-9])
    vmax = vmax * 1.15 if not as_pct else 1.0
    group_w = plot_w / n
    bar_w = min(46, group_w / 2.6)
    gap = 6
    ca, cb = colors

    def y(v):
        return pad_t + plot_h - (v / vmax) * plot_h

    P = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" font-family="Segoe UI,Helvetica,Arial,sans-serif">',
         f'<rect width="{width}" height="{height}" fill="{BG}"/>',
         f'<text x="{pad_l}" y="26" font-size="18" font-weight="700" fill="{INK}">{_esc(title)}</text>',
         f'<text x="{pad_l}" y="46" font-size="12.5" fill="{MUTE}">{_esc(subtitle)}</text>']

    ticks = [0, .25, .5, .75, 1.0] if as_pct else [0, vmax / 2, vmax]
    for t in ticks:
        yy = y(t)
        P.append(f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{width-pad_r}" y2="{yy:.1f}" '
                 f'stroke="#e5e7eb" stroke-width="1"/>')
        lbl = f"{t:.0%}" if as_pct else f"{t:.0f}"
        P.append(f'<text x="{pad_l-8}" y="{yy+4:.1f}" font-size="11" fill="{MUTE}" '
                 f'text-anchor="end">{lbl}</text>')

    def vfmt(v):
        return f"{v:.0%}" if as_pct else f"{v:g}{value_suffix}"

    for i, cat in enumerate(categories):
        gx = pad_l + i * group_w
        cx = gx + group_w / 2
        av, bv = a_vals[i], b_vals[i]
        xa = cx - bar_w - gap / 2
        xb = cx + gap / 2
        P.append(f'<rect x="{xa:.1f}" y="{y(av):.1f}" width="{bar_w:.1f}" '
                 f'height="{pad_t+plot_h-y(av):.1f}" fill="{ca}" rx="2"/>')
        P.append(f'<rect x="{xb:.1f}" y="{y(bv):.1f}" width="{bar_w:.1f}" '
                 f'height="{pad_t+plot_h-y(bv):.1f}" fill="{cb}" rx="2"/>')
        P.append(f'<text x="{xa+bar_w/2:.1f}" y="{y(av)-5:.1f}" font-size="10.5" '
                 f'fill="{ca}" text-anchor="middle" font-weight="600">{vfmt(av)}</text>')
        P.append(f'<text x="{xb+bar_w/2:.1f}" y="{y(bv)-5:.1f}" font-size="10.5" '
                 f'fill="{MUTE}" text-anchor="middle">{vfmt(bv)}</text>')
        words = str(cat).replace("_", " ").split()
        lines, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 > 14:
                lines.append(cur); cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            lines.append(cur)
        for j, ln in enumerate(lines[:3]):
            P.append(f'<text x="{cx:.1f}" y="{pad_t+plot_h+16+j*12:.1f}" font-size="10.5" '
                     f'fill="{INK}" text-anchor="middle">{_esc(ln)}</text>')

    ly = height - 18
    P.append(f'<rect x="{pad_l}" y="{ly-10}" width="12" height="12" fill="{ca}" rx="2"/>')
    P.append(f'<text x="{pad_l+18}" y="{ly}" font-size="12" fill="{INK}">{_esc(legend[0])}</text>')
    off = pad_l + 22 + len(legend[0]) * 7.2
    P.append(f'<rect x="{off:.0f}" y="{ly-10}" width="12" height="12" fill="{cb}" rx="2"/>')
    P.append(f'<text x="{off+18:.0f}" y="{ly}" font-size="12" fill="{INK}">{_esc(legend[1])}</text>')
    P.append("</svg>")
    return "\n".join(P)


def _load(name):
    p = HERE / name
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    wrote = []

    # Figure 1 + 2 — harness (218 items), the unambiguous discipline win.
    hft, hbase = _load("harness_report.finetuned.json"), _load("harness_report.base.json")
    if hft and hbase:
        fo, bo = hft["overall"], hbase["overall"]
        fig1 = grouped_bar_svg(
            "Scientific discipline — fine-tuned vs base (harness, 218 items)",
            "lower is better · number-fabrication and biochemical/cellular conflation rates",
            ["Number\nfabrication rate", "Assay\nconflation rate", "Un-hedged\nrate"],
            [fo["fabrication_rate"], fo["conflation_rate"], 1 - fo["hedged_rate"]],
            [bo["fabrication_rate"], bo["conflation_rate"], 1 - bo["hedged_rate"]],
            ("fine-tuned", "base Qwen3.5-4B"))
        (HERE / "fig_fabrication.svg").write_text(fig1, encoding="utf-8")
        wrote.append("fig_fabrication.svg")

        cats = sorted(set(hft["by_task_type"]) | set(hbase["by_task_type"]))
        fv = [hft["by_task_type"].get(c, {}).get("fabrication_rate", 0.0) for c in cats]
        bv = [hbase["by_task_type"].get(c, {}).get("fabrication_rate", 0.0) for c in cats]
        fig2 = grouped_bar_svg(
            "Number-fabrication rate by task (harness)",
            "lower is better · the fine-tune invents fewer numbers in every scored category",
            cats, fv, bv, ("fine-tuned", "base Qwen3.5-4B"))
        (HERE / "fig_by_category.svg").write_text(fig2, encoding="utf-8")
        wrote.append("fig_by_category.svg")

    # Figure 3 — fine-tune: closed-book vs RAG/open-book (grounding resolves).
    cb = _load("report.finetuned.json")
    rag = _load("report.finetuned_rag.json")
    if cb and rag:
        co, ro = cb["overall"], rag["overall"]
        fig3 = grouped_bar_svg(
            "Why RAG: fine-tune closed-book vs with retrieved evidence",
            "30-item benchmark · supplying the retrieved sources removes invented citations",
            ["Citation recall\n(higher better)", "Items w/ invented\ncitation (lower)",
             "Items w/ fabricated\nnumber (lower)"],
            [ro["citation_recall"], 0.0, 0.0],  # placeholders replaced below
            [co["citation_recall"], 0.0, 0.0],
            ("with RAG evidence", "closed-book"), as_pct=True)
        # citation recall is a fraction; invented/fab are counts -> use a second
        # count-based chart instead for honesty (mixing scales misleads).
        fig3b = grouped_bar_svg(
            "Why RAG: invented citations & fabricated numbers (fine-tune)",
            "30-item benchmark · counts of items flagged · lower is better",
            ["Items w/ invented\ncitation", "Items w/ fabricated\nnumber"],
            [ro["items_with_invented_citation"], ro["items_with_fabrication"]],
            [co["items_with_invented_citation"], co["items_with_fabrication"]],
            ("with RAG evidence", "closed-book"), as_pct=False)
        # recall-only chart (clean, single scale)
        fig3 = grouped_bar_svg(
            "Why RAG: citation recall (fine-tune)",
            "30-item benchmark · fraction of items citing a correct DOI/PMID · higher is better",
            ["Citation recall"],
            [ro["citation_recall"]], [co["citation_recall"]],
            ("with RAG evidence", "closed-book"), as_pct=True)
        (HERE / "fig_rag.svg").write_text(fig3, encoding="utf-8")
        (HERE / "fig_rag_counts.svg").write_text(fig3b, encoding="utf-8")
        wrote += ["fig_rag.svg", "fig_rag_counts.svg"]

    for w in wrote:
        print("Wrote", HERE / w)
    if not wrote:
        print("No figure inputs found (need harness_report.*.json and/or report.finetuned*.json).")


if __name__ == "__main__":
    main()
