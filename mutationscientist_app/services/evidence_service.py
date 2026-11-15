"""
evidence_service.py — the scientific-evidence retrieval interface (Person 3).

This one is REAL by default: it serves the curated, cited evidence that already
ships in the dataset (curated/biological_evidence.csv joined to REFERENCES.csv).
Every item keeps its traceable PMID/DOI/URL. Nothing is generated here.

Response shape matches the agreed Person 3 interface:
  { mutation_id, compound_id, evidence: [ {evidence_id, claim, evidence_type,
    source_id, pmid, doi, source_url, ...} ] }
"""
from __future__ import annotations
import json
import urllib.parse
import urllib.request

import config.settings as S


class EvidenceService:
    def __init__(self, dataset_service):
        self.data = dataset_service
        self.rows = dataset_service.evidence  # curated/biological_evidence.csv
        # Optional live retrieval API (Person 3 / Terminal 5). Until it is set we
        # serve the real curated+cited evidence that ships with the dataset.
        self.api_url = S.env(S.ENV_EVIDENCE_API_URL)
        self.live = bool(self.api_url)
        self.last_source = "curated"  # 'live' | 'curated' | 'curated (API fallback)'

    def retrieve(self, mutation_id: str | None = None, compound_id: str | None = None,
                 match: str = "any") -> dict:
        """
        match="any"  -> rows touching the mutation OR the compound (broad recall)
        match="pair" -> rows for exactly this mutation AND compound
        match="exact"-> same as pair

        If a live EVIDENCE_API_URL is configured it is queried first; any error
        degrades gracefully to the curated+cited local evidence (and says so).
        """
        if self.live:
            try:
                res = self._retrieve_live(mutation_id, compound_id, match)
                self.last_source = "live"
                return res
            except Exception:
                self.last_source = "curated (API fallback)"
        else:
            self.last_source = "curated"

        def keep(r):
            m, c = r.get("mutation_id") or "", r.get("compound_id") or ""
            if match in ("pair", "exact") and mutation_id and compound_id:
                return m == mutation_id and c == compound_id
            hits = []
            if mutation_id:
                hits.append(m == mutation_id)
            if compound_id:
                hits.append(c == compound_id)
            return any(hits) if hits else True

        items = []
        for r in self.rows:
            if not keep(r):
                continue
            items.append({
                "evidence_id": r.get("evidence_id", ""),
                "mutation_id": r.get("mutation_id", ""),
                "compound_id": r.get("compound_id", ""),
                "claim": r.get("claim", ""),
                "mechanism": r.get("mechanism", ""),
                "evidence_category": r.get("evidence_category", ""),
                "evidence_type": r.get("evidence_type", ""),
                "assay_type": r.get("assay_type", ""),
                "experimental_model": r.get("experimental_model", ""),
                "experimental_finding": r.get("experimental_finding", ""),
                "evidence_strength": r.get("evidence_strength", ""),
                "source_id": r.get("source_id", ""),
                "source_title": r.get("source_title", ""),
                "publication_year": r.get("publication_year", ""),
                "pmid": r.get("pmid", ""),
                "doi": r.get("doi", ""),
                "source_url": r.get("source_url", ""),
                "is_mock": False,
            })
        return {"mutation_id": mutation_id, "compound_id": compound_id,
                "match": match, "count": len(items), "evidence": items}

    def _retrieve_live(self, mutation_id, compound_id, match) -> dict:
        """Query the live evidence API. Expected JSON: {evidence:[{...}]} or a
        bare list of items. Items keep their PMID/DOI/source so provenance holds."""
        params = {k: v for k, v in (("mutation_id", mutation_id),
                                    ("compound_id", compound_id), ("match", match)) if v}
        url = self.api_url.rstrip("/") + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = json.loads(resp.read())
        items = raw.get("evidence", raw) if isinstance(raw, dict) else raw
        norm = []
        for r in (items or []):
            norm.append({
                "evidence_id": r.get("evidence_id", ""),
                "mutation_id": r.get("mutation_id", mutation_id or ""),
                "compound_id": r.get("compound_id", compound_id or ""),
                "claim": r.get("claim", ""), "mechanism": r.get("mechanism", ""),
                "evidence_category": r.get("evidence_category", ""),
                "evidence_type": r.get("evidence_type", ""),
                "assay_type": r.get("assay_type", ""),
                "experimental_model": r.get("experimental_model", ""),
                "experimental_finding": r.get("experimental_finding", ""),
                "evidence_strength": r.get("evidence_strength", ""),
                "source_id": r.get("source_id", ""), "source_title": r.get("source_title", ""),
                "publication_year": r.get("publication_year", ""),
                "pmid": r.get("pmid", ""), "doi": r.get("doi", ""),
                "source_url": r.get("source_url", ""), "is_mock": False,
            })
        return {"mutation_id": mutation_id, "compound_id": compound_id,
                "match": match, "count": len(norm), "evidence": norm}

    def all_categories(self) -> list[str]:
        return sorted({r.get("evidence_category", "") for r in self.rows if r.get("evidence_category")})

    def mode_label(self) -> str:
        if self.live:
            return "LIVE (retrieval API)" if self.last_source == "live" else \
                   "REAL (curated — API fallback)"
        return "REAL (curated + cited)"
