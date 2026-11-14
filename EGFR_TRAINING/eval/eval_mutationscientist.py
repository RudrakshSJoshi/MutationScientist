#!/usr/bin/env python3
"""
Evaluation harness for the fine-tuned EGFR "MutationScientist" LLM.

Pure Python standard library only (csv, json, re, argparse, urllib, os, sys).
NO third-party dependencies.

What it tests (the CARDINAL PROJECT RULE the model must obey):
  * NEVER fabricate numbers (IC50/Ki/KD/affinity values), mutations, or citations.
  * Keep biochemical affinity, cellular assays and clinical response DISTINCT.
  * Hedge / express uncertainty where appropriate.

Usage
-----
Self-test the scorer with NO network / NO API (predictions == references):
    python3 eval_mutationscientist.py --dry-run

Run against the real fine-tuned model later (Adaption AutoScientist Responses API):
    ADAPTION_API_KEY=... ADAPTION_STACK=<stack-slug> python3 eval_mutationscientist.py

(A generic OpenAI /chat/completions path is also available via --backend openai.)

Outputs ~/Desktop/EGFR_TRAINING/eval/report.json and report.md
"""

import argparse
import csv
import json
import os
import re
import sys
import urllib.request
import urllib.error

# --------------------------------------------------------------------------- #
# Paths (resolved relative to the user's home so it is portable)
# --------------------------------------------------------------------------- #
HOME = os.path.expanduser("~")
DATASET_DIR = os.path.join(HOME, "Desktop", "EGFR_RESEARCH_DATASET", "mutation_scientist")
DEFAULT_CSV = os.path.join(DATASET_DIR, "sft_test.csv")
DEFAULT_JSONL = os.path.join(DATASET_DIR, "eval_questions.jsonl")
OUT_DIR = os.path.join(HOME, "Desktop", "EGFR_TRAINING", "eval")

# --------------------------------------------------------------------------- #
# MutationScientist system persona (used only in REAL mode)
# --------------------------------------------------------------------------- #
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
    "(GI50 / viability) and clinical response STRICTLY distinct; never treat one as "
    "evidence for another.\n"
    "4. Hedge appropriately: a biochemical IC50 does not prove cellular or clinical "
    "outcome; a classification label does not substitute for measured data.\n"
    "Answer concisely and factually."
)

# --------------------------------------------------------------------------- #
# Number-with-unit extraction  (scorer (a) — the most important metric)
# --------------------------------------------------------------------------- #
# Concentration units: nM, µM/μM/uM, mM, pM, M ; multipliers: fold, x ; percent.
# Lookbehind (?<![A-Za-z]) stops us treating the trailing letter/digits of a
# mutation token (e.g. T790M, L858R, IC50, C797S) as a "<number> <unit>" claim.
# Lookahead (?![A-Za-z0-9]) stops partial-word matches (e.g. "10 mg").
_UNIT = r"(?:nM|\u00b5M|\u03bcM|uM|mM|pM|fold|%|x|M)"
NUM_UNIT_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d[\d,]*(?:\.\d+)?)\s*-?\s*(" + _UNIT + r")(?![A-Za-z0-9])",
    re.IGNORECASE,
)


def _norm_unit(u):
    u = u.lower()
    if u in ("\u00b5m", "\u03bcm", "um"):
        return "um"  # micromolar
    return u


def _norm_value(num_text):
    return round(float(num_text.replace(",", "")), 4)


def extract_numbers(text):
    """Return a list of {raw, value, unit, key} for every <number><unit> claim."""
    out = []
    for m in NUM_UNIT_RE.finditer(text or ""):
        num_text, unit_text = m.group(1), m.group(2)
        try:
            value = _norm_value(num_text)
        except ValueError:
            continue
        unit = _norm_unit(unit_text)
        out.append(
            {
                "raw": m.group(0).strip(),
                "value": value,
                "unit": unit,
                "key": (value, unit),
            }
        )
    return out


def number_grounding(prediction, context_text):
    """
    Flag any numeric+unit claim in PREDICTION whose (value, unit) does not appear
    in the context (reference_completion + prompt). Returns dict with counts and
    the list of ungrounded (potentially fabricated) numbers.
    """
    context_keys = {n["key"] for n in extract_numbers(context_text)}
    pred_numbers = extract_numbers(prediction)
    ungrounded = [n for n in pred_numbers if n["key"] not in context_keys]
    return {
        "n_pred_numbers": len(pred_numbers),
        "n_ungrounded": len(ungrounded),
        "ungrounded": [n["raw"] for n in ungrounded],
    }


# --------------------------------------------------------------------------- #
# Scorer (b) — biochemical-vs-cellular conflation (keyword heuristic)
# --------------------------------------------------------------------------- #
_CELLULAR_TERMS = ("gi50", "cellular", "cell-based", "cell line", "viability", "ic90 cell")
_BINDING_TERMS = (
    "binding affinity",
    "equilibrium affinity",
    "equilibrium binding",
    "dissociation constant",
    "kd",
    "ki ",
)
# Words that show the text is DISTINGUISHING rather than conflating.
_DISTINCTION_TERMS = (
    "not ",
    "rather than",
    "whereas",
    "while ",
    "!=",
    "≠",            # the not-equal sign
    "independent",
    "distinct",
    "different",
    "cannot",
    "does not",
    "do not",
    "isolated",
    "excluded",
    "separate",
    "neither",
    "nor ",
    "n't",
    "must not",
    "should not",
)

_SENT_SPLIT = re.compile(r"(?<=[.!?;])\s+")


def _has_any(s, terms):
    return any(t in s for t in terms)


def conflation_flag(prediction):
    """
    Heuristic: flag a sentence that affirmatively equates a biochemical IC50 with
    cellular response, OR equates IC50/GI50 with equilibrium binding affinity/KD,
    WITHOUT any distinguishing / negating language. Good (reference-style) answers
    always draw the distinction, so this should rarely fire on grounded text.
    """
    flags = []
    for sent in _SENT_SPLIT.split(prediction or ""):
        s = sent.lower()
        if "ic50" not in s and "gi50" not in s:
            continue
        if _has_any(s, _DISTINCTION_TERMS):
            continue  # the sentence explicitly separates the concepts -> fine
        # (i) IC50/GI50 asserted to BE equilibrium binding affinity / KD
        equates_binding = _has_any(s, _BINDING_TERMS)
        # (ii) a biochemical readout asserted to equal a cellular readout (or vice versa)
        mixes_layers = ("biochemical" in s and _has_any(s, _CELLULAR_TERMS))
        if equates_binding or mixes_layers:
            flags.append(sent.strip())
    return {"conflation": bool(flags), "sentences": flags}


# --------------------------------------------------------------------------- #
# Scorer (c) — uncertainty / hedging present (keyword heuristic)
# --------------------------------------------------------------------------- #
_HEDGE_TERMS = (
    "require validation",
    "requires validation",
    "validation is required",
    "cannot be inferred",
    "cannot",
    "does not",
    "do not",
    "not substitute",
    "does not prove",
    "not inferred",
    "not establish",
    "not by itself",
    "not demonstrate",
    "experimental",
    "must be read",
    "remain distinct",
    "isolated",
    "plausible",
    "typically",
    "uncertain",
    "not quantif",
    "no acquired-resistance",
    "does not, in itself",
    " may ",
    " not ",
)


def hedging_flag(prediction):
    s = (prediction or "").lower()
    hits = [t.strip() for t in _HEDGE_TERMS if t in s]
    return {"hedged": bool(hits), "hits": sorted(set(hits))}


# --------------------------------------------------------------------------- #
# Scorer (d) — token-overlap (Jaccard) vs reference
# --------------------------------------------------------------------------- #
_WORD_RE = re.compile(r"[a-z0-9]+")


def _word_set(text):
    return set(_WORD_RE.findall((text or "").lower()))


def jaccard(prediction, reference):
    a, b = _word_set(prediction), _word_set(reference)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# --------------------------------------------------------------------------- #
# Data loading -> unified list of items
# --------------------------------------------------------------------------- #
def load_items(csv_path, jsonl_path):
    items = []

    # sft_test.csv
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for i, row in enumerate(csv.DictReader(fh)):
            items.append(
                {
                    "source": "sft_test.csv",
                    "source_index": i,
                    "prompt": row.get("prompt", "") or "",
                    "reference_completion": row.get("completion", "") or "",
                    "task_type": row.get("task_type", "") or "unknown",
                    "context": {
                        "mutation_id": row.get("mutation_id", ""),
                        "compound_id": row.get("compound_id", ""),
                        "source_ids": row.get("source_ids", ""),
                        "review_status": row.get("review_status", ""),
                        "annotation_confidence": row.get("annotation_confidence", ""),
                    },
                }
            )

    # eval_questions.jsonl  (reference may be short / may be treated as empty-ish)
    if os.path.exists(jsonl_path):
        with open(jsonl_path, encoding="utf-8") as fh:
            for j, line in enumerate(fh):
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                items.append(
                    {
                        "source": "eval_questions.jsonl",
                        "source_index": j,
                        "prompt": rec.get("question", "") or "",
                        "reference_completion": rec.get("reference_answer", "") or "",
                        "task_type": rec.get("task_type", "") or "unknown",
                        "context": {"source_ids": ",".join(rec.get("source_ids", []))},
                    }
                )
    return items


# --------------------------------------------------------------------------- #
# Model-call layer (pluggable)
# --------------------------------------------------------------------------- #
def predict_dry_run(item):
    """Self-test mode: the reference completion IS the prediction (no API)."""
    return item["reference_completion"]


def _http_post_json(url, payload, headers, timeout):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_output_text(body):
    """Pull generated text out of an Adaption Responses reply."""
    txt = body.get("output_text")
    if isinstance(txt, str) and txt:
        return txt
    # Fallback: output[].content[].text (OpenAI Responses-style shape)
    parts = []
    for block in body.get("output", []) or []:
        for c in block.get("content", []) or []:
            if isinstance(c, dict) and isinstance(c.get("text"), str):
                parts.append(c["text"])
            elif isinstance(c, str):
                parts.append(c)
    return "".join(parts)


def predict_adaption(item, cfg):
    """
    Call an Adaption AutoScientist fine-tuned model via the Responses API.
      POST {base}/api/v1/responses
      body: {"model": "stack:<slug>", "input": <prompt>, "instructions": <persona>, ...}
      reply: {"output_text": "..."} (or output[].content[].text)
    """
    url = cfg["base_url"].rstrip("/") + "/api/v1/responses"
    payload = {
        "model": "stack:" + cfg["stack"],
        "input": item["prompt"],
        "instructions": SYSTEM_PROMPT,
        "temperature": 0,
        "max_output_tokens": cfg["max_tokens"],
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + cfg["api_key"],
    }
    body = _http_post_json(url, payload, headers, cfg["timeout"])
    return _extract_output_text(body)


def predict_openai(item, cfg):
    """Generic OpenAI-compatible /chat/completions call via urllib (optional)."""
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": item["prompt"]},
        ],
        "temperature": 0,
        "max_tokens": cfg["max_tokens"],
    }
    headers = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = "Bearer " + cfg["api_key"]
    body = _http_post_json(url, payload, headers, cfg["timeout"])
    return body["choices"][0]["message"]["content"]


# --------------------------------------------------------------------------- #
# Scoring one item
# --------------------------------------------------------------------------- #
def score_item(item, prediction):
    context_text = (item["reference_completion"] or "") + "\n" + (item["prompt"] or "")
    grounding = number_grounding(prediction, context_text)
    conflation = conflation_flag(prediction)
    hedging = hedging_flag(prediction)
    sim = jaccard(prediction, item["reference_completion"])
    return {
        "grounding": grounding,
        "conflation": conflation,
        "hedging": hedging,
        "jaccard": round(sim, 4),
    }


# --------------------------------------------------------------------------- #
# Aggregation + report
# --------------------------------------------------------------------------- #
def aggregate(results):
    def blank():
        return {
            "n": 0,
            "pred_numbers": 0,
            "ungrounded_numbers": 0,
            "items_with_fabrication": 0,
            "conflation_items": 0,
            "hedged_items": 0,
            "jaccard_sum": 0.0,
        }

    overall = blank()
    by_task = {}

    for r in results:
        tt = r["task_type"]
        bucket = by_task.setdefault(tt, blank())
        for b in (overall, bucket):
            b["n"] += 1
            b["pred_numbers"] += r["scores"]["grounding"]["n_pred_numbers"]
            b["ungrounded_numbers"] += r["scores"]["grounding"]["n_ungrounded"]
            if r["scores"]["grounding"]["n_ungrounded"] > 0:
                b["items_with_fabrication"] += 1
            if r["scores"]["conflation"]["conflation"]:
                b["conflation_items"] += 1
            if r["scores"]["hedging"]["hedged"]:
                b["hedged_items"] += 1
            b["jaccard_sum"] += r["scores"]["jaccard"]

    def finalize(b):
        n = b["n"] or 1
        return {
            "n": b["n"],
            "pred_numbers": b["pred_numbers"],
            "ungrounded_numbers": b["ungrounded_numbers"],
            "items_with_fabrication": b["items_with_fabrication"],
            "fabrication_rate": round(b["items_with_fabrication"] / n, 4),
            "conflation_items": b["conflation_items"],
            "conflation_rate": round(b["conflation_items"] / n, 4),
            "hedged_items": b["hedged_items"],
            "hedged_rate": round(b["hedged_items"] / n, 4),
            "mean_jaccard": round(b["jaccard_sum"] / n, 4),
        }

    return finalize(overall), {tt: finalize(b) for tt, b in sorted(by_task.items())}


def build_flagged(results):
    flagged = []
    for r in results:
        ung = r["scores"]["grounding"]["ungrounded"]
        if ung:
            flagged.append(
                {
                    "index": r["index"],
                    "source": r["source"],
                    "source_index": r["source_index"],
                    "task_type": r["task_type"],
                    "ungrounded_numbers": ung,
                    "prompt_snippet": r["prompt"][:160],
                }
            )
    return flagged


def write_reports(mode, overall, by_task, flagged, results):
    os.makedirs(OUT_DIR, exist_ok=True)
    report = {
        "mode": mode,
        "n_items": overall["n"],
        "overall": overall,
        "by_task_type": by_task,
        "flagged_potential_fabrications": flagged,
    }
    json_path = os.path.join(OUT_DIR, "report.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    # Markdown
    md = []
    md.append("# MutationScientist evaluation report\n")
    md.append(f"- **Mode:** `{mode}`")
    md.append(f"- **Items evaluated:** {overall['n']}")
    md.append(
        f"- **Potential fabricated numbers:** {overall['ungrounded_numbers']} "
        f"across {overall['items_with_fabrication']} items "
        f"(fabrication rate {overall['fabrication_rate']:.1%})"
    )
    md.append(
        f"- **Biochemical/cellular conflation flags:** {overall['conflation_items']} "
        f"({overall['conflation_rate']:.1%})"
    )
    md.append(
        f"- **Items with hedging/uncertainty:** {overall['hedged_items']} "
        f"({overall['hedged_rate']:.1%})"
    )
    md.append(f"- **Mean token-overlap (Jaccard) vs reference:** {overall['mean_jaccard']:.3f}")
    md.append(f"- **Total numeric+unit claims in predictions:** {overall['pred_numbers']}\n")

    md.append("## Per task_type\n")
    md.append(
        "| task_type | n | pred #s | ungrounded #s | fab items | fab rate | "
        "conflation | hedged | mean Jaccard |"
    )
    md.append("|---|---|---|---|---|---|---|---|---|")
    for tt, b in by_task.items():
        md.append(
            f"| {tt} | {b['n']} | {b['pred_numbers']} | {b['ungrounded_numbers']} | "
            f"{b['items_with_fabrication']} | {b['fabrication_rate']:.1%} | "
            f"{b['conflation_items']} | {b['hedged_items']} | {b['mean_jaccard']:.3f} |"
        )
    md.append("")

    md.append("## Flagged potential fabrications\n")
    if not flagged:
        md.append("_None — no ungrounded numeric+unit claims detected._\n")
    else:
        md.append("| idx | source | task_type | ungrounded number(s) | prompt |")
        md.append("|---|---|---|---|---|")
        for f in flagged:
            nums = ", ".join(f["ungrounded_numbers"])
            snip = f["prompt_snippet"].replace("|", "\\|").replace("\n", " ")
            md.append(
                f"| {f['index']} | {f['source']}#{f['source_index']} | "
                f"{f['task_type']} | {nums} | {snip} |"
            )
        md.append("")

    md_path = os.path.join(OUT_DIR, "report.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))

    return json_path, md_path


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="MutationScientist evaluation harness")
    ap.add_argument("--dry-run", action="store_true",
                    help="Use each row's reference completion AS the prediction (no API).")
    ap.add_argument("--csv", default=DEFAULT_CSV, help="Path to sft_test.csv")
    ap.add_argument("--jsonl", default=DEFAULT_JSONL, help="Path to eval_questions.jsonl")
    ap.add_argument("--limit", type=int, default=0, help="Evaluate only the first N items (0 = all)")
    ap.add_argument("--backend", choices=["adaption", "openai"], default="adaption",
                    help="REAL mode backend (default: adaption Responses API)")
    ap.add_argument("--max-tokens", type=int, default=512, help="REAL mode: max output tokens")
    ap.add_argument("--timeout", type=int, default=120, help="REAL mode: HTTP timeout (s)")
    args = ap.parse_args()

    items = load_items(args.csv, args.jsonl)
    if args.limit > 0:
        items = items[: args.limit]

    if args.dry_run:
        mode = "dry-run"
        cfg = None
        predict_fn = predict_dry_run
    elif args.backend == "adaption":
        mode = "real:adaption"
        cfg = {
            "base_url": os.environ.get("ADAPTION_BASE_URL", "https://api.prod.adaptionlabs.ai"),
            "api_key": os.environ.get("ADAPTION_API_KEY", ""),
            "stack": os.environ.get("ADAPTION_STACK", ""),
            "max_tokens": args.max_tokens,
            "timeout": args.timeout,
        }
        if not cfg["api_key"] or not cfg["stack"]:
            sys.exit(
                "REAL adaption mode needs ADAPTION_API_KEY and ADAPTION_STACK "
                "(the trained stack slug; the model is called as 'stack:<ADAPTION_STACK>'). "
                "Optionally set ADAPTION_BASE_URL. Use --dry-run to self-test with no API."
            )
        predict_fn = lambda it: predict_adaption(it, cfg)
    else:  # openai
        mode = "real:openai"
        cfg = {
            "base_url": os.environ.get("OPENAI_BASE_URL", ""),
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
            "model": os.environ.get("OPENAI_MODEL", ""),
            "max_tokens": args.max_tokens,
            "timeout": args.timeout,
        }
        if not cfg["base_url"] or not cfg["model"]:
            sys.exit(
                "REAL openai mode needs OPENAI_BASE_URL and OPENAI_MODEL (and usually "
                "OPENAI_API_KEY). Use --dry-run to self-test the scorer with no API."
            )
        predict_fn = lambda it: predict_openai(it, cfg)

    results = []
    for idx, item in enumerate(items):
        if args.dry_run:
            prediction = predict_fn(item)
        else:
            try:
                prediction = predict_fn(item)
            except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError) as e:
                prediction = ""
                sys.stderr.write(f"[warn] item {idx} prediction failed: {e}\n")
        results.append(
            {
                "index": idx,
                "source": item["source"],
                "source_index": item["source_index"],
                "task_type": item["task_type"],
                "prompt": item["prompt"],
                "prediction": prediction,
                "scores": score_item(item, prediction),
            }
        )

    overall, by_task = aggregate(results)
    flagged = build_flagged(results)
    json_path, md_path = write_reports(mode, overall, by_task, flagged, results)

    # Console summary
    print(f"Mode: {mode}")
    print(f"Items evaluated: {overall['n']}")
    print(f"Total numeric+unit claims in predictions: {overall['pred_numbers']}")
    print(f"Ungrounded (potential fabrications): {overall['ungrounded_numbers']} "
          f"across {overall['items_with_fabrication']} items "
          f"(rate {overall['fabrication_rate']:.1%})")
    print(f"Biochemical/cellular conflation flags: {overall['conflation_items']} "
          f"({overall['conflation_rate']:.1%})")
    print(f"Items with hedging/uncertainty: {overall['hedged_items']} "
          f"({overall['hedged_rate']:.1%})")
    print(f"Mean Jaccard vs reference: {overall['mean_jaccard']:.3f}")
    print()
    print("Per task_type:")
    hdr = f"  {'task_type':<28} {'n':>4} {'pred#':>6} {'ungr':>5} {'fab':>4} {'conf':>5} {'hedge':>6} {'jacc':>6}"
    print(hdr)
    for tt, b in by_task.items():
        print(f"  {tt:<28} {b['n']:>4} {b['pred_numbers']:>6} "
              f"{b['ungrounded_numbers']:>5} {b['items_with_fabrication']:>4} "
              f"{b['conflation_items']:>5} {b['hedged_items']:>6} {b['mean_jaccard']:>6.3f}")
    print()
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")


if __name__ == "__main__":
    main()
