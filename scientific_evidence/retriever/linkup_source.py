#!/usr/bin/env python3
"""
linkup_source.py — OPTIONAL live-literature layer over the curated evidence (Person 3, follow-up s2).

The curated corpus is the source of truth and the system works fully offline
without this module.  When a Linkup API key is present, this adds *live, current*
literature (PubMed / Europe PMC-level) for a mutation x inhibitor query and
normalises each hit to the SAME evidence schema the rest of the stack uses, so a
live source is interchangeable with a curated one downstream — and clearly tagged
as live so the two are never confused.

Hard rules honoured here:
  * Fully local by default.  No key -> this layer is simply disabled; nothing
    external is called and nothing is fabricated.
  * NEVER invent a citation.  A live item is emitted only if it carries a real
    source URL.  A DOI / PMID is attached only when one is actually found in the
    result's URL or text; otherwise those fields stay empty and the URL is the
    citation.  We never manufacture an identifier.
  * Results are cached on disk (gitignored) so repeated queries cost no credits.

Linkup API (https://docs.linkup.so):
  POST https://api.linkup.so/v1/search
  Authorization: Bearer $LINKUP_API_KEY
  body: {"q", "depth": "standard", "outputType": "searchResults", "maxResults": N,
         "includeDomains": [...]}
  200: {"results": [{"type": "text", "name", "url", "content", "publishedAt"?}, ...]}

CLI:
  LINKUP_API_KEY=... python -m scientific_evidence.retriever.linkup_source \
      --query "C797S osimertinib resistance" --max 5
  (no key -> prints a clear 'disabled' notice and exits 0; never errors the pipeline)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://api.linkup.so/v1/search"
PKG = Path(__file__).resolve().parents[1]
CACHE_DIR = Path(os.environ.get(
    "LINKUP_CACHE_DIR", str(PKG / "evidence_database" / "linkup_cache")))

# Bias the live search toward citable biomedical literature.  Override with
# LINKUP_INCLUDE_DOMAINS="a.com,b.org" or set it empty to search the open web.
_DEFAULT_DOMAINS = ("pubmed.ncbi.nlm.nih.gov", "www.ncbi.nlm.nih.gov",
                    "pmc.ncbi.nlm.nih.gov", "europepmc.org", "doi.org")

DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"'<>)\]}]+", re.I)
PUBMED_URL_RE = re.compile(r"(?:pubmed\.ncbi\.nlm\.nih\.gov|/pubmed)/(\d{5,9})", re.I)
PMID_TEXT_RE = re.compile(r"\bPMID[:\s]*?(\d{5,9})\b", re.I)


def is_enabled() -> bool:
    return bool(os.environ.get("LINKUP_API_KEY"))


def _include_domains() -> list[str]:
    raw = os.environ.get("LINKUP_INCLUDE_DOMAINS")
    if raw is None:
        return list(_DEFAULT_DOMAINS)
    raw = raw.strip()
    return [d.strip() for d in raw.split(",") if d.strip()] if raw else []


def _clean_doi(doi: str) -> str:
    return doi.rstrip(".,;)]}>\"'").casefold() if doi else ""


def _extract_ids(url: str, text: str) -> tuple[str, str]:
    """Return (pmid, doi), each '' if not genuinely present. Never invented."""
    blob = f"{url}\n{text}"
    pm = PUBMED_URL_RE.search(url) or PMID_TEXT_RE.search(blob)
    pmid = pm.group(1) if pm else ""
    dm = DOI_RE.search(blob)
    doi = _clean_doi(dm.group(0)) if dm else ""
    return pmid, doi


def _year(published_at: str) -> str:
    if not published_at:
        return ""
    m = re.search(r"\b(19|20)\d{2}\b", published_at)
    return m.group(0) if m else ""


def _cache_path(payload: dict) -> Path:
    key = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"{key}.json"


def _normalise(results: list[dict], query: str) -> list[dict]:
    out = []
    for i, r in enumerate(results):
        if r.get("type") not in (None, "text"):
            continue  # skip images etc.
        url = (r.get("url") or "").strip()
        if not url:
            continue  # no traceable source -> never emit (hard rule)
        content = (r.get("content") or r.get("snippet") or "").strip()
        pmid, doi = _extract_ids(url, content)
        out.append({
            "evidence_id": f"LIVE_{pmid or doi or i}",
            "mutation_id": "",
            "compound_id": "",
            "claim": content[:600],
            "mechanism": "",
            "evidence_category": "live_literature",
            "evidence_type": "live_literature",
            "assay_type": "",
            "experimental_model": "",
            "experimental_finding": "",
            "evidence_strength": "live_retrieval_unverified",
            "source_id": "linkup",
            "source_title": (r.get("name") or "").strip(),
            "publication_year": _year(r.get("publishedAt", "")),
            "pmid": pmid,
            "doi": doi,
            "source_url": url,
            "is_mock": False,
            "is_live": True,
            "query": query,
        })
    return out


def search_literature(query: str, *, max_results: int = 5, depth: str = "standard",
                      timeout: int = 60, use_cache: bool = True) -> dict:
    """
    Live literature for `query`, normalised to the evidence schema.

    Returns {"enabled", "cached", "query", "count", "results":[...], "reason"?}.
    Degrades gracefully: no key, a network error or a bad response never raises
    and never fabricates — it returns enabled/ok flags and an empty result set.
    """
    if not is_enabled():
        return {"enabled": False, "cached": False, "query": query, "count": 0,
                "results": [], "reason": "LINKUP_API_KEY not set (live literature disabled; "
                "curated evidence unaffected)"}

    body = {"q": query, "depth": depth, "outputType": "searchResults",
            "maxResults": max(1, int(max_results))}
    domains = _include_domains()
    if domains:
        body["includeDomains"] = domains

    cache_file = _cache_path(body)
    if use_cache and cache_file.is_file():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            cached["cached"] = True
            return cached
        except (ValueError, OSError):
            pass  # fall through to a live call

    req = urllib.request.Request(
        API_URL, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Authorization": "Bearer " + os.environ["LINKUP_API_KEY"],
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError) as e:
        return {"enabled": True, "cached": False, "query": query, "count": 0,
                "results": [], "reason": f"linkup request failed: {type(e).__name__}: {e}"}

    results = _normalise(data.get("results", []) or [], query)
    out = {"enabled": True, "cached": False, "query": query,
           "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "count": len(results), "results": results}
    if use_cache:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        except OSError:
            pass
    return out


def merge_with_curated(curated: dict, live: dict) -> dict:
    """
    Attach live hits to a curated retrieve() result under a separate `live_evidence`
    key (curated evidence is never overwritten or relabelled).  A live hit whose
    DOI or PMID already appears in the curated set is dropped as a duplicate.
    """
    curated = dict(curated)
    have_doi = {(e.get("doi") or "").casefold() for e in curated.get("evidence", []) if e.get("doi")}
    have_pmid = {str(e.get("pmid")) for e in curated.get("evidence", []) if e.get("pmid")}
    fresh = [r for r in live.get("results", [])
             if (r["doi"].casefold() not in have_doi if r["doi"] else True)
             and (str(r["pmid"]) not in have_pmid if r["pmid"] else True)]
    curated["live_evidence"] = fresh
    curated["live_literature"] = {"enabled": live.get("enabled", False),
                                  "cached": live.get("cached", False),
                                  "count": len(fresh),
                                  "reason": live.get("reason", "")}
    return curated


def main():
    ap = argparse.ArgumentParser(description="Live literature via Linkup (optional layer).")
    ap.add_argument("--query", required=True, help='e.g. "C797S osimertinib resistance"')
    ap.add_argument("--max", type=int, default=5)
    ap.add_argument("--depth", default="standard", choices=["flash", "fast", "standard", "deep"])
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    res = search_literature(args.query, max_results=args.max, depth=args.depth,
                            use_cache=not args.no_cache)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if not res["enabled"]:
        print("\n[disabled] " + res["reason"])


if __name__ == "__main__":
    main()
