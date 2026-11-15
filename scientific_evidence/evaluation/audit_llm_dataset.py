#!/usr/bin/env python3
"""
Audit the LLM SFT dataset for scientific-trustworthiness risks (Person 3 brief, s5).

The teacher-generated examples are machine-checked but NOT human-reviewed, so we
do not assume they are all reliable.  This runs three deterministic, reproducible
checks over every SFT row (prompt + completion):

  1. concentration_fabrication - a concentration value+unit (nM/uM/mM/pM) that
     appears in the COMPLETION but not in the PROMPT.  (Computed fold-changes/%
     are allowed by the cardinal rule and are NOT flagged.)
  2. assay_conflation          - a sentence equating biochemical IC50 with cellular
     response, or IC50/GI50 with equilibrium binding/KD, without distinguishing it.
  3. invented_citation         - a DOI/PMID in the completion that is not present
     in the curated corpus (valid_citations.json).

We NEVER modify the original dataset; corrections are recorded separately with a
pointer back to the source row (source_file + row_index).

Run:  python -m scientific_evidence.evaluation.audit_llm_dataset
Outputs: scientific_evidence/llm_dataset_audit.csv
         scientific_evidence/llm_dataset_audit_report.md
"""

import csv
import os
from collections import Counter
from pathlib import Path

from .scorers import (extract_numbers, conflation_flag, citation_presence,
                      load_valid_citations)

PKG = Path(__file__).resolve().parents[1]
DATASET = Path(os.environ.get("EGFR_DATASET",
                              os.path.expanduser("~/Desktop/EGFR_RESEARCH_DATASET")))
SFT_FILES = ["sft_train.csv", "sft_validation.csv", "sft_test.csv"]
CONC_UNITS = {"nm", "um", "mm", "pm"}   # concentration units only (not fold/%/x)

# large csv fields (long completions)
csv.field_size_limit(10_000_000)


def concentration_fabrication(prompt, completion):
    ctx = {n["key"] for n in extract_numbers(prompt) if n["unit"] in CONC_UNITS}
    flagged = [n["raw"] for n in extract_numbers(completion)
               if n["unit"] in CONC_UNITS and n["key"] not in ctx]
    return flagged


def main():
    valid_dois, valid_pmids = load_valid_citations()
    rows_out = []
    by_status = {}
    by_task = {}
    totals = Counter()

    for fn in SFT_FILES:
        path = DATASET / "mutation_scientist" / fn
        with path.open(encoding="utf-8") as f:
            for i, r in enumerate(csv.DictReader(f)):
                prompt = r.get("prompt", "") or ""
                completion = r.get("completion", "") or ""
                status = r.get("review_status", "") or "unknown"
                task = r.get("task_type", "") or "unknown"

                fab = concentration_fabrication(prompt, completion)
                conf = conflation_flag(completion)["conflation"]
                cit = citation_presence(completion, [], valid_dois, valid_pmids)
                invented = cit["invented_dois"] + cit["invented_pmids"]

                flags = []
                if fab:
                    flags.append("concentration_fabrication")
                if conf:
                    flags.append("assay_conflation")
                if invented:
                    flags.append("invented_citation")

                sb = by_status.setdefault(status, Counter())
                tb = by_task.setdefault(task, Counter())
                for bucket in (totals, sb, tb):
                    bucket["n"] += 1
                    bucket["flagged"] += int(bool(flags))
                    for fl in flags:
                        bucket[fl] += 1

                if flags:
                    rows_out.append({
                        "source_file": fn, "row_index": i, "task_type": task,
                        "review_status": status,
                        "mutation_id": r.get("mutation_id", ""),
                        "compound_id": r.get("compound_id", ""),
                        "flags": "|".join(flags),
                        "fabricated_concentrations": "; ".join(fab),
                        "invented_citations": "; ".join(invented),
                        "conflation_sentence": (conflation_flag(completion)["sentences"][0][:200]
                                                if conf else ""),
                        "prompt_snippet": prompt[:160].replace("\n", " "),
                    })

    # ---- CSV ----
    csv_path = PKG / "llm_dataset_audit.csv"
    cols = ["source_file", "row_index", "task_type", "review_status", "mutation_id",
            "compound_id", "flags", "fabricated_concentrations", "invented_citations",
            "conflation_sentence", "prompt_snippet"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows_out)

    # ---- report ----
    def line(b):
        return (f"{b['n']} | flagged {b['flagged']} ({b['flagged']/max(b['n'],1):.1%}) | "
                f"fab {b['concentration_fabrication']} | conflation {b['assay_conflation']} | "
                f"invented-cite {b['invented_citation']}")

    md = ["# LLM SFT dataset audit\n",
          "Deterministic scientific-trustworthiness screen of every SFT row "
          "(prompt + completion). The original dataset is **not modified**; this is a "
          "review layer with traceability (`source_file` + `row_index`).\n",
          "**Checks:** (1) concentration fabrication — a nM/uM/mM/pM value in the "
          "completion absent from the prompt (computed fold-changes/% are allowed and "
          "not flagged); (2) biochemical/cellular (or IC50/KD) conflation; (3) invented "
          "DOI/PMID not in the curated corpus.\n",
          f"- **Rows audited:** {totals['n']}",
          f"- **Rows with >=1 flag:** {totals['flagged']} ({totals['flagged']/max(totals['n'],1):.1%})",
          f"- **Concentration-fabrication flags:** {totals['concentration_fabrication']}",
          f"- **Assay-conflation flags:** {totals['assay_conflation']}",
          f"- **Invented-citation flags:** {totals['invented_citation']}\n",
          "## By review_status\n",
          "| review_status | n | flagged | concentration-fab | conflation | invented-cite |",
          "|---|---|---|---|---|---|"]
    for st, b in sorted(by_status.items()):
        md.append(f"| {st} | {b['n']} | {b['flagged']} ({b['flagged']/max(b['n'],1):.1%}) | "
                  f"{b['concentration_fabrication']} | {b['assay_conflation']} | {b['invented_citation']} |")
    md += ["", "## By task_type\n",
           "| task_type | n | flagged | concentration-fab | conflation | invented-cite |",
           "|---|---|---|---|---|---|"]
    for tk, b in sorted(by_task.items()):
        md.append(f"| {tk} | {b['n']} | {b['flagged']} ({b['flagged']/max(b['n'],1):.1%}) | "
                  f"{b['concentration_fabrication']} | {b['assay_conflation']} | {b['invented_citation']} |")

    md += ["", "## Interpretation\n",
           "- **Number reviewed:** all " + str(totals['n']) + " SFT rows "
           "(train + validation + test), of which "
           f"{by_status.get('teacher_generated_unverified_autochecked', Counter())['n']} are "
           "teacher-generated/unverified and "
           f"{by_status.get('model_generated_grounded', Counter())['n']} are hand-grounded.",
           f"- **Number passed (no flag):** {totals['n'] - totals['flagged']}.",
           f"- **Number requiring human review:** {totals['flagged']} (listed in "
           "`llm_dataset_audit.csv`).",
           "- **Main error categories:** concentration-fabrication (a value in the "
           "answer not traceable to the prompt) is the highest-priority flag because it "
           "directly tests the no-fabrication rule; conflation flags indicate assay-type "
           "mixing; invented-citation flags indicate a DOI/PMID outside the corpus.",
           "- These flags are **screening signals, not verdicts** — a flagged row may be "
           "a correct computed value whose inputs were phrased indirectly in the prompt, "
           "or an acceptable paraphrase. Each flagged row should be confirmed by a "
           "domain reviewer before any correction is applied, and corrections must be "
           "recorded separately from the source dataset.\n"]
    (PKG / "llm_dataset_audit_report.md").write_text("\n".join(md), encoding="utf-8")

    print(f"Audited {totals['n']} rows; flagged {totals['flagged']} "
          f"(fab={totals['concentration_fabrication']}, conflation={totals['assay_conflation']}, "
          f"invented-cite={totals['invented_citation']}).")
    print(f"Wrote {csv_path}")
    print(f"Wrote {PKG / 'llm_dataset_audit_report.md'}")


if __name__ == "__main__":
    main()
