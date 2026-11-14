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


class EvidenceService:
    def __init__(self, dataset_service):
        self.data = dataset_service
        self.rows = dataset_service.evidence  # curated/biological_evidence.csv

    def retrieve(self, mutation_id: str | None = None, compound_id: str | None = None,
                 match: str = "any") -> dict:
        """
        match="any"  -> rows touching the mutation OR the compound (broad recall)
        match="pair" -> rows for exactly this mutation AND compound
        match="exact"-> same as pair
        """
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

    def all_categories(self) -> list[str]:
        return sorted({r.get("evidence_category", "") for r in self.rows if r.get("evidence_category")})

    def mode_label(self) -> str:
        return "REAL (curated + cited)"
