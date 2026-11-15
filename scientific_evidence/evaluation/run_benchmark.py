#!/usr/bin/env python3
"""
Run the independent EGFR scientific-evaluation benchmark against a model.

Standard library only. Endpoint-agnostic: build/self-test now, wire a model later.

MODES
-----
Self-test the scorers with NO network (prediction == reference answer):
    python -m scientific_evidence.evaluation.run_benchmark --dry-run

Grade a local OpenAI-compatible server (e.g. vLLM on http://localhost:8000/v1):
    OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=sk-... OPENAI_MODEL=mutation-scientist \
        python -m scientific_evidence.evaluation.run_benchmark --backend openai

Grade the Adaption hosted fine-tune (Responses API, stack slug):
    ADAPTION_API_KEY=... ADAPTION_STACK=<slug> \
        python -m scientific_evidence.evaluation.run_benchmark --backend adaption

Outputs (next to this file):
    evaluation_report.md    human-readable validation report
    report.json             full machine-readable results incl. every flag

Hard rule: a fabricated number or an invented DOI/PMID is always surfaced and
always fails the item; nothing is silently smoothed over.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

from .scorers import load_valid_citations, score_item

HERE = Path(__file__).resolve().parent

SYSTEM_PROMPT = (
    "You are MutationScientist, an evidence-grounded assistant that explains EGFR "
    "mutations, interprets experimental measurements, distinguishes assay types, and "
    "reasons about resistance.\n"
    "CARDINAL RULES you must never break:\n"
    "1. NEVER invent or fabricate numbers. Do not state any IC50, Ki, KD, affinity, "
    "fold-change or percentage unless it is given to you in the prompt or can be "
    "computed directly from numbers given in the prompt. If a number is not provided, "
    "say it is not available / requires measurement.\n"
    "2. NEVER invent mutations, compounds, citations or DOIs.\n"
    "3. Keep biochemical (isolated-enzyme / binding) affinity, cellular assays "
    "(GI50 / viability) and clinical response STRICTLY distinct.\n"
    "4. Hedge appropriately: a biochemical IC50 does not prove cellular or clinical "
    "outcome. Cite supplied evidence by its DOI/PMID/evidence_id where possible.\n"
    "Answer concisely and factually."
)


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def load_benchmark(bench_path, ref_path):
    refs = {}
    with open(ref_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                r = json.loads(line)
                refs[r["id"]] = r["reference_answer"]
    items = []
    with open(bench_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            it = json.loads(line)
            it["reference_answer"] = refs.get(it["id"], "")
            items.append(it)
    return items


# --------------------------------------------------------------------------- #
# Model backends
# --------------------------------------------------------------------------- #
def _http_post_json(url, payload, headers, timeout):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def predict_dry_run(item, _cfg):
    return item["reference_answer"]


def predict_openai(item, cfg):
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": item["question"]},
        ],
        "temperature": 0,
        "max_tokens": cfg["max_tokens"],
    }
    headers = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = "Bearer " + cfg["api_key"]
    body = _http_post_json(url, payload, headers, cfg["timeout"])
    return body["choices"][0]["message"]["content"]


def _extract_output_text(body):
    txt = body.get("output_text")
    if isinstance(txt, str) and txt:
        return txt
    parts = []
    for block in body.get("output", []) or []:
        for c in block.get("content", []) or []:
            if isinstance(c, dict) and isinstance(c.get("text"), str):
                parts.append(c["text"])
            elif isinstance(c, str):
                parts.append(c)
    return "".join(parts)


def predict_adaption(item, cfg):
    url = cfg["base_url"].rstrip("/") + "/api/v1/responses"
    payload = {
        "model": "stack:" + cfg["stack"],
        "input": item["question"],
        "instructions": SYSTEM_PROMPT,
        "temperature": 0,
        "max_output_tokens": cfg["max_tokens"],
    }
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + cfg["api_key"]}
    return _extract_output_text(_http_post_json(url, payload, headers, cfg["timeout"]))


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #
def _blank():
    return {"n": 0, "passed": 0, "factual_sum": 0.0, "fabrication_items": 0,
            "invented_citation_items": 0, "citation_expected": 0, "citation_hit": 0,
            "conflation_items": 0, "hedge_required": 0, "hedge_missing": 0,
            "jaccard_sum": 0.0}


def _acc(b, s):
    b["n"] += 1
    b["passed"] += int(s["passed"])
    b["factual_sum"] += s["factual"]["score"]
    b["fabrication_items"] += int(s["grounding"]["n_ungrounded"] > 0)
    b["invented_citation_items"] += int(s["citation"]["has_invented_citation"])
    if s["citation"]["n_expected"] > 0:
        b["citation_expected"] += 1
        b["citation_hit"] += int(s["citation"]["expected_satisfied"])
    b["conflation_items"] += int(s["conflation"]["conflation"])
    if s["requires_hedge"]:
        b["hedge_required"] += 1
        b["hedge_missing"] += int(not s["hedging"]["hedged"])
    b["jaccard_sum"] += s["jaccard"]


def _finalize(b):
    n = b["n"] or 1
    ce = b["citation_expected"] or 1
    hr = b["hedge_required"] or 1
    return {
        "n": b["n"], "passed": b["passed"], "pass_rate": round(b["passed"] / n, 4),
        "mean_factual": round(b["factual_sum"] / n, 4),
        "items_with_fabrication": b["fabrication_items"],
        "items_with_invented_citation": b["invented_citation_items"],
        "citation_recall": round(b["citation_hit"] / ce, 4),
        "citation_items_scored": b["citation_expected"],
        "conflation_items": b["conflation_items"],
        "hedge_required": b["hedge_required"], "hedge_missing": b["hedge_missing"],
        "mean_jaccard": round(b["jaccard_sum"] / n, 4),
    }


def aggregate(results):
    overall = _blank()
    by_task = {}
    for r in results:
        _acc(overall, r["scores"])
        _acc(by_task.setdefault(r["task_type"], _blank()), r["scores"])
    return _finalize(overall), {t: _finalize(b) for t, b in sorted(by_task.items())}


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #
def write_reports(mode, model_label, overall, by_task, results):
    report = {"mode": mode, "model": model_label, "n_items": overall["n"],
              "overall": overall, "by_task_type": by_task, "items": results}
    (HERE / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md = []
    md.append("# EGFR MutationScientist — independent evaluation report\n")
    md.append(f"- **Mode:** `{mode}`  ")
    md.append(f"- **Model:** `{model_label}`  ")
    md.append(f"- **Items evaluated:** {overall['n']} (independent benchmark; "
              "gold sourced from curated evidence, not the SFT training rows)  ")
    md.append(f"- **Overall pass rate:** {overall['pass_rate']:.1%} "
              f"({overall['passed']}/{overall['n']})  ")
    md.append(f"- **Mean factual correctness:** {overall['mean_factual']:.3f}  ")
    md.append(f"- **Items with fabricated numbers:** {overall['items_with_fabrication']}  ")
    md.append(f"- **Items with invented DOI/PMID citations:** {overall['items_with_invented_citation']}  ")
    md.append(f"- **Citation recall (where a citation was expected):** {overall['citation_recall']:.1%} "
              f"over {overall['citation_items_scored']} items  ")
    md.append(f"- **Biochemical/cellular conflation flags:** {overall['conflation_items']}  ")
    md.append(f"- **Hedging missing where required:** {overall['hedge_missing']}/{overall['hedge_required']}  ")
    md.append(f"- **Mean token-overlap (Jaccard) vs reference:** {overall['mean_jaccard']:.3f}\n")

    md.append("## Scoring dimensions\n")
    md.append("1. **Factual correctness** — fraction of each item's required facts present, minus over-claims.  ")
    md.append("2. **Evidence grounding / citation** — expected DOI/PMID/evidence_id cited; any DOI/PMID not in "
              "the curated corpus is flagged as a potential fabrication.  ")
    md.append("3. **Biochemical-vs-cellular distinction** — conflation of enzyme IC50 with cellular/clinical "
              "or with KD/Ki is flagged.  ")
    md.append("4. **Uncertainty calibration** — items that demand hedging must express it.  ")
    md.append("Plus two ported cardinal checks: **number grounding** (no fabricated values) and **hedging**.\n")

    md.append("## Per task_type\n")
    md.append("| task_type | n | pass | factual | fabricated# | invented-cite | cite-recall | conflation | hedge-missing | Jaccard |")
    md.append("|---|---|---|---|---|---|---|---|---|---|")
    for t, b in by_task.items():
        md.append(f"| {t} | {b['n']} | {b['passed']}/{b['n']} | {b['mean_factual']:.3f} | "
                  f"{b['items_with_fabrication']} | {b['items_with_invented_citation']} | "
                  f"{b['citation_recall']:.0%} | {b['conflation_items']} | "
                  f"{b['hedge_missing']}/{b['hedge_required']} | {b['mean_jaccard']:.3f} |")
    md.append("")

    # Flagged items (anything that did not fully pass)
    failed = [r for r in results if not r["scores"]["passed"]]
    md.append("## Flagged items (did not fully pass)\n")
    if not failed:
        md.append("_None — every item passed all dimensions._\n")
    else:
        md.append("| id | task_type | factual | missed / issue |")
        md.append("|---|---|---|---|")
        for r in failed:
            s = r["scores"]
            issues = []
            if s["factual"]["missed"]:
                issues.append("missing: " + "; ".join(str(m) for m in s["factual"]["missed"][:4]))
            if s["factual"]["overclaims"]:
                issues.append("overclaim: " + "; ".join(str(m) for m in s["factual"]["overclaims"]))
            if s["grounding"]["n_ungrounded"]:
                issues.append("fabricated#: " + ", ".join(s["grounding"]["ungrounded"]))
            if s["citation"]["has_invented_citation"]:
                issues.append("invented-cite: " + ", ".join(
                    s["citation"]["invented_dois"] + s["citation"]["invented_pmids"]))
            if s["citation"]["n_expected"] and not s["citation"]["expected_satisfied"]:
                issues.append("missing expected citation")
            if s["conflation"]["conflation"]:
                issues.append("conflation")
            if s["requires_hedge"] and not s["hedging"]["hedged"]:
                issues.append("no hedging")
            issue = (" | ".join(issues)).replace("\n", " ")[:300] or "—"
            md.append(f"| {r['id']} | {r['task_type']} | {s['factual']['score']:.2f} | {issue} |")
        md.append("")

    md.append("## How to re-run against a live model\n")
    md.append("```bash\n"
              "# local OpenAI-compatible server (e.g. vLLM)\n"
              "OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=sk-x OPENAI_MODEL=<name> \\\n"
              "  python -m scientific_evidence.evaluation.run_benchmark --backend openai\n\n"
              "# Adaption hosted fine-tune (Responses API)\n"
              "ADAPTION_API_KEY=... ADAPTION_STACK=<slug> \\\n"
              "  python -m scientific_evidence.evaluation.run_benchmark --backend adaption\n"
              "```\n")
    (HERE / "evaluation_report.md").write_text("\n".join(md), encoding="utf-8")
    return HERE / "report.json", HERE / "evaluation_report.md"


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="Use each item's reference answer AS the prediction (no API).")
    ap.add_argument("--backend", choices=["openai", "adaption"], default="openai")
    ap.add_argument("--benchmark", default=str(HERE / "scientific_benchmark.jsonl"))
    ap.add_argument("--references", default=str(HERE / "reference_answers.jsonl"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=600)
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args()

    items = load_benchmark(args.benchmark, args.references)
    if args.limit > 0:
        items = items[: args.limit]
    valid_dois, valid_pmids = load_valid_citations()

    if args.dry_run:
        mode, model_label, cfg, predict = "dry-run", "reference-as-prediction", None, predict_dry_run
    elif args.backend == "openai":
        mode = "real:openai"
        cfg = {"base_url": os.environ.get("OPENAI_BASE_URL", "http://localhost:8000/v1"),
               "api_key": os.environ.get("OPENAI_API_KEY", ""),
               "model": os.environ.get("OPENAI_MODEL", ""),
               "max_tokens": args.max_tokens, "timeout": args.timeout}
        if not cfg["model"]:
            sys.exit("REAL openai mode needs OPENAI_MODEL (and usually OPENAI_BASE_URL/OPENAI_API_KEY). "
                     "Use --dry-run to self-test the scorers with no API.")
        model_label = f"{cfg['model']} @ {cfg['base_url']}"
        predict = predict_openai
    else:
        mode = "real:adaption"
        cfg = {"base_url": os.environ.get("ADAPTION_BASE_URL", "https://api.prod.adaptionlabs.ai"),
               "api_key": os.environ.get("ADAPTION_API_KEY", ""),
               "stack": os.environ.get("ADAPTION_STACK", ""),
               "max_tokens": args.max_tokens, "timeout": args.timeout}
        if not cfg["api_key"] or not cfg["stack"]:
            sys.exit("REAL adaption mode needs ADAPTION_API_KEY and ADAPTION_STACK. "
                     "Use --dry-run to self-test with no API.")
        model_label = f"stack:{cfg['stack']}"
        predict = predict_adaption

    results = []
    for idx, item in enumerate(items):
        try:
            prediction = predict(item, cfg)
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError, TimeoutError) as e:
            prediction = ""
            sys.stderr.write(f"[warn] item {item['id']} prediction failed: {e}\n")
        scores = score_item(item, prediction, valid_dois, valid_pmids)
        results.append({"id": item["id"], "task_type": item["task_type"],
                        "question": item["question"], "prediction": prediction, "scores": scores})

    overall, by_task = aggregate(results)
    json_path, md_path = write_reports(mode, model_label, overall, by_task, results)

    print(f"Mode: {mode}   Model: {model_label}")
    print(f"Items: {overall['n']}   Pass rate: {overall['pass_rate']:.1%} "
          f"({overall['passed']}/{overall['n']})   Mean factual: {overall['mean_factual']:.3f}")
    print(f"Fabricated numbers: {overall['items_with_fabrication']} items   "
          f"Invented citations: {overall['items_with_invented_citation']} items   "
          f"Citation recall: {overall['citation_recall']:.1%}")
    print(f"Conflation flags: {overall['conflation_items']}   "
          f"Hedge missing: {overall['hedge_missing']}/{overall['hedge_required']}")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()
