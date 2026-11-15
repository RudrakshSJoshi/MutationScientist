#!/usr/bin/env python3
"""
Deterministic scorers for the independent EGFR scientific-evaluation benchmark.

Standard library ONLY (re, json). No third-party deps, no LLM-as-judge: every
score is rule-based and reproducible.

The first four scorers are PORTED (lightly adapted) from the fine-tune eval
harness `~/Desktop/EGFR_TRAINING/eval/eval_mutationscientist.py` so the two
evaluations speak the same language:

    number_grounding   - flag numeric+unit claims not supported by the context
                         (the CARDINAL no-fabrication metric)
    conflation_flag    - flag biochemical<->cellular / IC50<->KD conflation
    hedging_flag       - detect appropriate uncertainty / calibration language
    jaccard            - token-overlap vs the reference answer

This module ADDS two benchmark-specific, citation-aware scorers:

    factual_correctness - fraction of an item's REQUIRED facts that are present,
                          minus any FORBIDDEN (over-claiming) assertions
    citation_presence   - did the answer cite the expected DOI/PMID/evidence_id,
                          and did it invent any DOI/PMID not in the corpus?

Hard rule honoured throughout: we never reward a fabricated number or citation;
an invented DOI/PMID is always surfaced, never silently dropped.
"""

import json
import re
from pathlib import Path

# --------------------------------------------------------------------------- #
# (a) number grounding  (ported from eval_mutationscientist.py)
# --------------------------------------------------------------------------- #
_UNIT = r"(?:nM|µM|μM|uM|mM|pM|fold|%|x|M)"
NUM_UNIT_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d[\d,]*(?:\.\d+)?)\s*-?\s*(" + _UNIT + r")(?![A-Za-z0-9])",
    re.IGNORECASE,
)


def _norm_unit(u):
    u = u.lower()
    return "um" if u in ("µm", "μm", "um") else u


def _norm_value(num_text):
    return round(float(num_text.replace(",", "")), 4)


def extract_numbers(text):
    """Return {raw, value, unit, key} for every <number><unit> claim."""
    out = []
    for m in NUM_UNIT_RE.finditer(text or ""):
        try:
            value = _norm_value(m.group(1))
        except ValueError:
            continue
        unit = _norm_unit(m.group(2))
        out.append({"raw": m.group(0).strip(), "value": value, "unit": unit,
                    "key": (value, unit)})
    return out


def number_grounding(prediction, context_text):
    """Flag numeric+unit claims in PREDICTION whose (value, unit) is absent from
    the context (reference answer + question + any supplied evidence)."""
    context_keys = {n["key"] for n in extract_numbers(context_text)}
    pred_numbers = extract_numbers(prediction)
    ungrounded = [n for n in pred_numbers if n["key"] not in context_keys]
    return {
        "n_pred_numbers": len(pred_numbers),
        "n_ungrounded": len(ungrounded),
        "ungrounded": [n["raw"] for n in ungrounded],
    }


# --------------------------------------------------------------------------- #
# (b) biochemical<->cellular / IC50<->KD conflation  (ported)
# --------------------------------------------------------------------------- #
_CELLULAR_TERMS = ("gi50", "cellular", "cell-based", "cell line", "viability", "ic90 cell")
_BINDING_TERMS = ("binding affinity", "equilibrium affinity", "equilibrium binding",
                  "dissociation constant", "kd", "ki ")
_DISTINCTION_TERMS = ("not ", "rather than", "whereas", "while ", "!=", "≠",
                      "independent", "distinct", "different", "cannot", "does not",
                      "do not", "isolated", "excluded", "separate", "neither", "nor ",
                      "n't", "must not", "should not")
_SENT_SPLIT = re.compile(r"(?<=[.!?;])\s+")


def _has_any(s, terms):
    return any(t in s for t in terms)


def conflation_flag(prediction):
    """Flag a sentence that affirmatively equates a biochemical IC50 with a
    cellular response, or IC50/GI50 with equilibrium binding/KD, WITHOUT any
    distinguishing/negating language."""
    flags = []
    for sent in _SENT_SPLIT.split(prediction or ""):
        s = sent.lower()
        if "ic50" not in s and "gi50" not in s:
            continue
        if _has_any(s, _DISTINCTION_TERMS):
            continue
        equates_binding = _has_any(s, _BINDING_TERMS)
        mixes_layers = "biochemical" in s and _has_any(s, _CELLULAR_TERMS)
        if equates_binding or mixes_layers:
            flags.append(sent.strip())
    return {"conflation": bool(flags), "sentences": flags}


# --------------------------------------------------------------------------- #
# (c) hedging / uncertainty calibration  (ported)
# --------------------------------------------------------------------------- #
_HEDGE_TERMS = ("require validation", "requires validation", "validation is required",
                "cannot be inferred", "cannot", "does not", "do not", "not substitute",
                "does not prove", "not inferred", "not establish", "not by itself",
                "not demonstrate", "experimental", "must be read", "remain distinct",
                "isolated", "plausible", "typically", "uncertain", "not quantif",
                "no acquired-resistance", "does not, in itself", " may ", " not ",
                "not available", "not determined", "requires measurement", "lower bound",
                "right-censored", "censored")


def hedging_flag(prediction):
    s = (prediction or "").lower()
    hits = [t.strip() for t in _HEDGE_TERMS if t in s]
    return {"hedged": bool(hits), "hits": sorted(set(hits))}


# --------------------------------------------------------------------------- #
# (d) token overlap vs reference  (ported)
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
# (e) factual correctness  (NEW)  -- required/forbidden assertion checking
# --------------------------------------------------------------------------- #
# A benchmark item lists `required_facts`; each is one of:
#   {"type": "keywords", "all_of": [...]}        every phrase must appear (any of nested lists = OR)
#   {"type": "keywords", "any_of": [...]}        at least one phrase must appear
#   {"type": "number",  "value": x, "unit": "nM"} the (value,unit) must appear
#   {"type": "number",  "any_of": [[v,u],...]}   at least one of these (value,unit) pairs
# and optional `forbidden_facts` with the same shapes (presence = over-claim penalty).

def _kw_present(text, phrase):
    """Case-insensitive substring; a list means OR over its members."""
    low = text.lower()
    if isinstance(phrase, (list, tuple)):
        return any(_kw_present(text, p) for p in phrase)
    return phrase.lower() in low


def _number_present(pred_keys, value, unit):
    return (_norm_value(str(value)), _norm_unit(unit)) in pred_keys


def _fact_satisfied(fact, prediction, pred_keys):
    t = fact.get("type")
    if t == "keywords":
        if "all_of" in fact:
            return all(_kw_present(prediction, p) for p in fact["all_of"])
        if "any_of" in fact:
            return any(_kw_present(prediction, p) for p in fact["any_of"])
        return False
    if t == "number":
        if "any_of" in fact:
            return any(_number_present(pred_keys, v, u) for v, u in fact["any_of"])
        return _number_present(pred_keys, fact["value"], fact["unit"])
    return False


def factual_correctness(prediction, required_facts, forbidden_facts=None):
    pred_keys = {n["key"] for n in extract_numbers(prediction)}
    required_facts = required_facts or []
    forbidden_facts = forbidden_facts or []
    hits, misses = [], []
    for fact in required_facts:
        (hits if _fact_satisfied(fact, prediction, pred_keys) else misses).append(
            fact.get("label", fact)
        )
    overclaims = [f.get("label", f) for f in forbidden_facts
                  if _fact_satisfied(f, prediction, pred_keys)]
    n = len(required_facts) or 1
    # recall of required facts (1.0 if none required), minus 1/n per over-claim, clamped to [0,1]
    base = (len(hits) / n) if required_facts else 1.0
    raw = base - (len(overclaims) / n)
    return {
        "score": round(max(0.0, min(1.0, raw)), 4),
        "required": len(required_facts),
        "hits": len(hits),
        "missed": misses,
        "overclaims": overclaims,
    }


# --------------------------------------------------------------------------- #
# (f) citation presence + invented-citation detection  (NEW)
# --------------------------------------------------------------------------- #
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>)\]]+)", re.I)
PMID_RE = re.compile(r"(?:\bpmid[:#\s]*|pubmed\.ncbi\.nlm\.nih\.gov/)(\d{6,9})", re.I)
# dataset identifiers we treat as citeable provenance
ID_RE = re.compile(r"\b((?:EVIDENCE|MEAS|SOURCE|PROF|BDB)_[A-Za-z0-9_]+)\b")

_DEFAULT_VALID = Path(__file__).resolve().parent / "valid_citations.json"


def load_valid_citations(path=_DEFAULT_VALID):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return (set(d.lower() for d in data.get("dois", [])),
            set(data.get("pmids", [])))


def _clean_doi(d):
    return d.strip().lower().rstrip(".,;)]}")


def citation_presence(prediction, expected_citations, valid_dois, valid_pmids):
    """
    expected_citations: list of strings (DOIs, PMIDs or dataset IDs) at least one
    of which the answer should surface.  Returns recall of expected citations and,
    critically, any DOI/PMID-shaped token that is NOT in the curated corpus
    (a potential fabricated citation -- the hard-rule violation).
    """
    pred_dois = {_clean_doi(d) for d in DOI_RE.findall(prediction or "")}
    pred_pmids = set(PMID_RE.findall(prediction or ""))
    pred_ids = set(ID_RE.findall(prediction or ""))
    found_tokens = pred_dois | pred_pmids | {i.upper() for i in pred_ids}

    expected = [str(c).strip() for c in (expected_citations or [])]
    exp_norm = {(_clean_doi(c) if c.lower().startswith("10.") else c.upper()
                 if re.match(r"(?i)(EVIDENCE|MEAS|SOURCE|PROF|BDB)_", c) else c)
                for c in expected}
    matched = exp_norm & found_tokens
    expected_hit = (len(matched) > 0) if expected else True

    invented_dois = sorted(d for d in pred_dois if d not in valid_dois)
    invented_pmids = sorted(p for p in pred_pmids if p not in valid_pmids)
    return {
        "expected_satisfied": expected_hit,
        "n_expected": len(expected),
        "matched_expected": sorted(matched),
        "cited_dois": sorted(pred_dois),
        "cited_pmids": sorted(pred_pmids),
        "invented_dois": invented_dois,
        "invented_pmids": invented_pmids,
        "has_invented_citation": bool(invented_dois or invented_pmids),
    }


# --------------------------------------------------------------------------- #
# Composite per-item scorer
# --------------------------------------------------------------------------- #
def score_item(item, prediction, valid_dois, valid_pmids):
    """Score one benchmark item.  `item` carries the gold expectations; the
    reference answer + question form the grounding context for number checks."""
    ctx = (item.get("reference_answer") or "") + "\n" + (item.get("question") or "")
    for ev in item.get("evidence_context", []) or []:
        ctx += "\n" + str(ev)
    grounding = number_grounding(prediction, ctx)
    citation = citation_presence(prediction, item.get("expected_citations"),
                                 valid_dois, valid_pmids)
    factual = factual_correctness(prediction, item.get("required_facts"),
                                  item.get("forbidden_facts"))
    conflation = conflation_flag(prediction)
    hedging = hedging_flag(prediction)
    sim = round(jaccard(prediction, item.get("reference_answer", "")), 4)

    # uncertainty calibration: if the gold says hedging is required, reward only
    # when present; if not required, neither reward nor penalise.
    needs_hedge = bool(item.get("requires_hedge"))
    calibration = (not needs_hedge) or hedging["hedged"]

    passed = (
        factual["score"] >= 0.999
        and grounding["n_ungrounded"] == 0
        and not citation["has_invented_citation"]
        and citation["expected_satisfied"]
        and not conflation["conflation"]
        and calibration
    )
    return {
        "factual": factual,
        "grounding": grounding,
        "citation": citation,
        "conflation": conflation,
        "hedging": hedging,
        "calibration_ok": calibration,
        "requires_hedge": needs_hedge,
        "jaccard": sim,
        "passed": passed,
    }
