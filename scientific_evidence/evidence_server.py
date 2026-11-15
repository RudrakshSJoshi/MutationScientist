#!/usr/bin/env python3
"""
evidence_server.py — a small live HTTP evidence API (Person 3, follow-up s3).

Wraps the in-process retriever (`scientific_evidence.evidence_api.retrieve_evidence`)
in a dependency-free HTTP service so Terminal 3's Evidence Explorer and Terminal 4's
avatar can fetch cited evidence live, behind every answer, without importing Python.

The JSON response matches the agreed Person 3 interface used by
~/Desktop/application/services/evidence_service.py:

  { "mutation_id", "compound_id", "match", "count",
    "evidence": [ {evidence_id, claim, evidence_type, assay_type,
                   source_id, pmid, doi, source_url, evidence_strength, ...} ],
    "context": [...], "pair_variability": [...], "total_matches": N,
    "live_evidence": [...] }          # only when ?live=1 and LINKUP_API_KEY is set

Every evidence item carries structured provenance (pmid / doi / source_url); the
server never synthesises a claim or a citation — it only returns what the curated
index (and, optionally, Linkup) actually holds.

Endpoints
---------
  GET /health
  GET /evidence?mutation_id=EGFR_C797S&compound_id=CMP_OSIMERTINIB&match=pair
  GET /evidence?query=C797S + osimertinib&live=1
      params: mutation_id, compound_id, compound_name, query, assay_type,
              match=any|pair (default any), limit (1-200), live=0|1

Run:  python -m scientific_evidence.evidence_server            # :8077
      EVIDENCE_API_PORT=9000 python -m scientific_evidence.evidence_server
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from .evidence_api import retrieve_evidence
from .retriever import linkup_source

DEFAULT_PORT = int(os.environ.get("EVIDENCE_API_PORT", "8077"))

# Keys the app's evidence_service.retrieve() item shape expects to see.
_APP_ITEM_KEYS = ("evidence_id", "mutation_id", "compound_id", "claim", "mechanism",
                  "evidence_category", "evidence_type", "assay_type",
                  "experimental_model", "experimental_finding", "evidence_strength",
                  "source_id", "source_title", "publication_year",
                  "pmid", "doi", "source_url")


def _app_item(e: dict) -> dict:
    item = {k: e.get(k, "") for k in _APP_ITEM_KEYS}
    item["is_mock"] = False
    return item


def retrieve_app_schema(*, mutation_id=None, compound_id=None, compound_name=None,
                        query=None, assay_type=None, match="any", limit=20,
                        live=False) -> dict:
    """Retrieve curated evidence and return it in the app's response schema.

    match="pair" requires both mutation_id and compound_id. Raises ValueError for
    an unrecognised id/token (never guesses), FileNotFoundError if the index is
    missing — the HTTP layer maps these to 400 / 503.
    """
    kwargs = dict(limit=limit)
    if match == "pair" and not (mutation_id and compound_id):
        raise ValueError("match=pair requires both mutation_id and compound_id")
    if mutation_id:
        kwargs["mutation_id"] = mutation_id
    if compound_id:
        kwargs["compound_id"] = compound_id
    if compound_name:
        kwargs["compound_name"] = compound_name
    if query:
        kwargs["query"] = query
    if assay_type:
        kwargs["assay_type"] = assay_type

    raw = retrieve_evidence(**kwargs)
    evidence = [_app_item(e) for e in raw.get("evidence", [])]
    resp = {
        "mutation_id": raw.get("mutation_id", mutation_id),
        "compound_id": raw.get("compound_id", compound_id),
        "profile_id": raw.get("profile_id"),
        "match": match,
        "count": len(evidence),
        "total_matches": raw.get("total_matches", len(evidence)),
        "evidence": evidence,
        "context": raw.get("context", []),
        "pair_variability": raw.get("pair_variability", []),
        "mode": "REAL (curated + cited)",
    }
    if live:
        q = query or " ".join(filter(None, [mutation_id, compound_id, compound_name])) or ""
        live_res = linkup_source.search_literature(q, max_results=5)
        resp = linkup_source.merge_with_curated(resp, live_res)
    else:
        resp["live_literature"] = {"enabled": False, "count": 0,
                                   "reason": "pass ?live=1 to include live literature"}
        resp["live_evidence"] = []
    return resp


class Handler(BaseHTTPRequestHandler):
    server_version = "EvidenceAPI/1.0"

    def _send(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # CORS preflight for browser callers
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        if parsed.path == "/health":
            self._send(200, {"status": "ok",
                             "live_literature_enabled": linkup_source.is_enabled(),
                             "endpoints": ["/health", "/evidence"]})
            return

        if parsed.path != "/evidence":
            self._send(404, {"error": "not found",
                             "endpoints": ["/health", "/evidence"]})
            return

        if not any(q.get(k) for k in ("mutation_id", "compound_id", "compound_name", "query")):
            self._send(400, {"error": "provide at least one of mutation_id, compound_id, "
                                      "compound_name, query"})
            return
        try:
            limit = int(q.get("limit", "20"))
        except ValueError:
            self._send(400, {"error": "limit must be an integer"})
            return

        try:
            result = retrieve_app_schema(
                mutation_id=q.get("mutation_id"), compound_id=q.get("compound_id"),
                compound_name=q.get("compound_name"), query=q.get("query"),
                assay_type=q.get("assay_type"), match=q.get("match", "any"),
                limit=limit, live=q.get("live", "0") in ("1", "true", "yes"))
        except ValueError as e:
            self._send(400, {"error": str(e)})
            return
        except FileNotFoundError as e:
            self._send(503, {"error": str(e)})
            return
        self._send(200, result)

    def log_message(self, *_):  # quiet
        pass


def main():
    httpd = ThreadingHTTPServer(("127.0.0.1", DEFAULT_PORT), Handler)
    print(f"Evidence API on http://127.0.0.1:{DEFAULT_PORT}  "
          f"(live literature: {'ON' if linkup_source.is_enabled() else 'off'})")
    print(f"  GET http://127.0.0.1:{DEFAULT_PORT}/health")
    print(f"  GET http://127.0.0.1:{DEFAULT_PORT}/evidence?mutation_id=EGFR_C797S&compound_id=CMP_OSIMERTINIB&match=pair")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
