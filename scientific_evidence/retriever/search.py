"""Exact metadata filters and SQLite FTS5 ranking for EGFR evidence."""

import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

DATABASE = Path(__file__).resolve().parents[1] / "evidence_database" / "evidence.sqlite3"
TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE)
PMID_PREFIX = re.compile(r"^(?:pmid:\s*|https?://pubmed\.ncbi\.nlm\.nih\.gov/)", re.IGNORECASE)


def alias(db, kind, value):
    if value is None:
        return None
    label = " ".join(value.strip().casefold().split())
    row = db.execute(
        "SELECT canonical_id FROM aliases WHERE kind = ? AND alias = ?", (kind, label)
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown {kind}: {value!r}")
    return row[0]


def select(db, where, params, match, limit, offset=0, *, count=False):
    relation = "evidence e JOIN search ON search.rowid = e.row_id" if match else "evidence e"
    terms = (["search MATCH ?"] if match else []) + where
    values = ([match] if match else []) + params
    predicate = " AND ".join(terms) or "1"
    order = "e.priority, bm25(search), e.evidence_id" if match else "e.priority, e.evidence_id"
    total = None
    if count:
        total = db.execute(f"SELECT count(*) FROM {relation} WHERE {predicate}", values).fetchone()[0]
    payloads = db.execute(
        f"SELECT e.payload FROM {relation} WHERE {predicate} ORDER BY {order} LIMIT ? OFFSET ?",
        [*values, limit, offset],
    )
    return [json.loads(row[0]) for row in payloads], total


def retrieve(
    mutation_id=None, compound_id=None, *, query=None, mutation_profile=None,
    compound_name=None, resistance_mechanism=None, cancer_context=None,
    evidence_category=None, evidence_type=None, assay_type=None, measurement_type=None,
    publication_title=None, pmid=None, doi=None, include_context=True,
    limit=20, offset=0, database=DATABASE, measurement_values=(), related_limit=8,
    cell_line=None, atp_condition=None,
):
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError("limit must be an integer from 1 to 200")
    if type(offset) is not int or offset < 0:
        raise ValueError("offset must be a nonnegative integer")
    if type(related_limit) is not int or not 0 <= related_limit <= 40:
        raise ValueError("related_limit must be an integer from 0 to 40")
    path = Path(database).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Evidence database missing at {path}. Run scientific_evidence.retriever.build.")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        if query and " + " in query and not (mutation_id or mutation_profile or compound_id or compound_name):
            variant, inhibitor = query.split(" + ", 1)
            if "/" in variant or variant.strip().lower().startswith("prof_"):
                mutation_profile = variant
            else:
                mutation_id = variant
            compound_name, query = inhibitor, None
        mid = alias(db, "mutation", mutation_id)
        pid = alias(db, "profile", mutation_profile)
        cid = alias(db, "compound", compound_id)
        named_cid = alias(db, "compound", compound_name)
        cid = cid or named_cid
        equivalents = [cid] + [row[0] for row in db.execute(
            "SELECT equivalent_id FROM compound_equivalents WHERE compound_id = ? ORDER BY equivalent_id",
            (cid,),
        )] if cid else []
        if named_cid and named_cid not in equivalents:
            raise ValueError("compound_id and compound_name identify different compounds")
        related = [row[0] for row in db.execute(
            "SELECT profile_id FROM profile_components WHERE component_id = ? ORDER BY profile_id", (mid,)
        )] if mid else []
        if mid and pid and pid not in [*related, "PROF_" + mid.removeprefix("EGFR_")]:
            raise ValueError("mutation_id does not belong to mutation_profile")

        # Quote user tokens so FTS operators and punctuation stay literal.
        tokens = TOKEN.findall(" ".join(filter(None, (query, resistance_mechanism, publication_title))))
        match = " AND ".join(f'"{token}"' for token in tokens) or None
        filters = []
        values = []
        for column, value in (
            ("evidence_category", evidence_category), ("evidence_type", evidence_type),
            ("pmid", PMID_PREFIX.sub("", pmid.strip()).rstrip("/") if pmid else None),
            ("doi", DOI_PREFIX.sub("", doi.strip()).casefold() if doi else None),
        ):
            if value is not None:
                filters.append(f"e.{column} = ? COLLATE NOCASE")
                values.append(value.strip())
        if assay_type is not None:
            filters.append(
                "(e.assay_type = ? COLLATE NOCASE OR "
                "json_extract(e.payload, '$.details.raw_assay_type') = ? COLLATE NOCASE)"
            )
            values.extend([assay_type.strip()] * 2)
        if measurement_type is not None:
            filters.append("json_extract(e.payload, '$.details.measurement_type') = ? COLLATE NOCASE")
            values.append(measurement_type.strip())
        if cell_line is not None:
            filters.append("json_extract(e.payload, '$.details.cell_line') = ? COLLATE NOCASE")
            values.append(cell_line)
        if atp_condition is not None:
            filters.append("instr(lower(json_extract(e.payload, '$.details.assay_description')), lower(?)) > 0")
            values.append(atp_condition)
        if measurement_values:
            predicates = []
            for relation, value, unit in measurement_values:
                predicates.append(
                    "(CAST(json_extract(e.payload, '$.details.value') AS REAL) = ? AND "
                    "json_extract(e.payload, '$.details.unit') = ? AND "
                    "json_extract(e.payload, '$.details.relation') = ?)"
                )
                values.extend((value, unit, relation or "="))
            filters.append("(" + " OR ".join(predicates) + ")")
        if cancer_context:
            names = {
                "nsclc", "non small cell lung cancer",
            }
            normalized = " ".join(TOKEN.findall(cancer_context.casefold()))
            if normalized in names:
                filters.append("e.cancer_context IN ('NSCLC', 'Non-small-cell lung cancer')")
            else:
                filters.append("e.cancer_context = ? COLLATE NOCASE")
                values.append(cancer_context.strip())
        if publication_title:
            filters.append("instr(lower(json_extract(e.payload, '$.source_title')), lower(?)) > 0")
            values.append(publication_title.strip())
        variant_filter = "e.profile_id = ?" if pid else "e.mutation_id = ?"
        variant = pid or mid
        compound_filter = f"e.compound_id IN ({', '.join('?' for _ in equivalents)})"
        exact_filters = filters + ([variant_filter] if variant else []) + ([compound_filter] if cid else [])
        exact_values = values + ([variant] if variant else []) + equivalents
        hits, total = select(db, exact_filters, exact_values, match, limit, offset, count=True)
        context = []
        if include_context and variant and cid:
            mutation_context, _ = select(
                db, filters + [variant_filter, "e.compound_id IS NULL",
                               "e.evidence_type IN ('annotation', 'literature_reported')"],
                values + [variant], match, 8,
            )
            compound_context, _ = select(
                db, filters + [compound_filter, "e.mutation_id IS NULL", "e.evidence_type = 'annotation'"],
                values + equivalents, match, 2,
            )
            for item in mutation_context + compound_context:
                item["match_scope"] = "entity_context"
                context.append(item)
            if related and not pid:
                placeholders = ", ".join("?" for _ in related)
                related_rows, _ = select(
                    db, filters + [f"e.profile_id IN ({placeholders})", compound_filter],
                    values + related + equivalents, match, related_limit,
                )
                for item in related_rows:
                    item["match_scope"] = "related_profile"
                    context.append(item)

        conflicts = []
        if variant and cid:
            coverage_mid = "EGFR_" + pid.removeprefix("PROF_") if pid else mid
            conflicts = [json.loads(row[0]) for row in db.execute(
                f"SELECT spread_json FROM coverage e WHERE e.mutation_id = ? AND {compound_filter} ORDER BY e.compound_id",
                [coverage_mid, *equivalents],
            )]
        for item in hits:
            item["match_scope"] = "direct"
        return {
            "mutation_id": mid or ("EGFR_" + pid.removeprefix("PROF_") if pid else None),
            "profile_id": pid, "compound_id": cid, "evidence": hits, "context": context,
            "total_matches": total, "limit": limit, "offset": offset,
            "pair_variability": conflicts,
        }
