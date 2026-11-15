"""Keyword discovery over typed relationships in the existing SQLite evidence index."""

import re
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from .question import ASSAY_TERMS, DOI, ENDPOINT, FILLER, PMID, entity_spans
from .search import DATABASE, TOKEN, experimental_filters, select

PROTEIN = "P00533"
PROTEIN_NAME = "EGFR · Epidermal growth factor receptor"
PROTEIN_URL = "https://www.uniprot.org/uniprotkb/P00533/entry"
GRAPH_ASSAYS = (*ASSAY_TERMS, "unspecified")
ATP_CONDITIONS = ("Km,ATP", "1 mmol/L ATP")
PROTEIN_TERMS = re.compile(
    r"\b(?:p00533(?:-1)?|egfr(?:_human)?|erbb-?1|her-?1|epidermal growth factor receptor)\b",
    re.I,
)
STRUCTURE = re.compile(r"\b(?:pdb\s+)?([0-9][a-z0-9]{3})\b", re.I)
BROWSE_WORDS = FILLER | {"protein", "proteins", "uniprot", "gene", "related", "graph"}
IDENTITY_COLUMNS = {
    "mutation": "e.mutation_id",
    "profile": "e.profile_id",
    "compound": "e.compound_id",
    "assay": "e.assay_type",
    "endpoint": "upper(json_extract(e.payload, '$.details.measurement_type'))",
    "doi": "e.doi",
    "pmid": "e.pmid",
}
VERIFIABLE = (
    "(json_extract(e.payload, '$.source_url') LIKE 'https://%' OR "
    "json_extract(e.payload, '$.source_url') LIKE 'http://%') AND "
    "coalesce(json_extract(e.payload, '$.details.claim_verification'), '') <> 'citation_scope_flagged'"
)


def keyword_seeds(db, keywords):
    seeds = defaultdict(set)
    mask = list(keywords)

    def add(kind, value, span):
        seeds[kind].add(value)
        start, end = span
        mask[start:end] = " " * (end - start)

    for regex, kind in ((DOI, "doi"), (PMID, "pmid")):
        for match in regex.finditer(keywords):
            add(kind, match[1].rstrip(".,;?)]}").casefold(), match.span())
    entity_text = "".join(mask)
    for kind, value, span in entity_spans(db, entity_text):
        add(kind, value, span)
    for match in PROTEIN_TERMS.finditer("".join(mask)):
        add("protein", PROTEIN, match.span())
    # Scan the original text so a protein name in an assay phrase stays recognizable.
    for assay, pattern in ASSAY_TERMS.items():
        label = re.escape(assay).replace("_", "[ _]+")
        for match in re.finditer(f"(?:{pattern}|\\b{label}\\b)", entity_text, re.I):
            add("assay", assay, match.span())
    for match in ENDPOINT.finditer("".join(mask)):
        endpoint = re.sub(r"[\s_]", "", match[1]).translate(str.maketrans("₅₀", "50")).upper()
        add("endpoint", endpoint, match.span())
    for match in STRUCTURE.finditer("".join(mask)):
        pdb = match[1].upper()
        if db.execute(
            "SELECT 1 FROM evidence WHERE assay_type = 'structural_experiment' AND "
            "(evidence_id = ? OR json_extract(payload, '$.details.pdb_id') = ?) LIMIT 1",
            (pdb, pdb),
        ).fetchone():
            add("structure", pdb, match.span())
    tokens = dict.fromkeys(word for word in TOKEN.findall("".join(mask).casefold()) if word not in BROWSE_WORDS)
    return dict(seeds), " AND ".join(f'"{word}"' for word in tokens) or None


def predicate(column, values):
    return f"{column} IN ({', '.join('?' for _ in values)})"


def linked_records(db, seeds, match, limit, offset, options):
    filters = [VERIFIABLE]
    params = []
    if options["assay_type"]:
        filters.append("e.assay_type = ?")
        params.append(options["assay_type"])
    for condition, value in experimental_filters(options["cell_line"], options["atp_condition"]):
        filters.append(condition)
        params.append(value)
    mutations = sorted(seeds.get("mutation", ()))
    if mutations:
        condition = predicate("e.mutation_id", mutations)
        params.extend(mutations)
        if not options["exact_only"]:
            component = predicate("component_id", mutations)
            condition += f" OR e.profile_id IN (SELECT profile_id FROM profile_components WHERE {component})"
            params.extend(mutations)
        filters.append(f"({condition})")
    for kind, column in IDENTITY_COLUMNS.items():
        if kind == "mutation" or kind not in seeds:
            continue
        values = sorted(seeds[kind])
        if kind == "compound":
            equivalents = db.execute(
                f"SELECT equivalent_id FROM compound_equivalents WHERE {predicate('compound_id', values)}",
                values,
            )
            values = sorted(set(values) | {row[0] for row in equivalents})
        filters.append(predicate(column, values))
        params.extend(values)
    if "protein" in seeds:
        filters.append(
            "(e.mutation_id IS NOT NULL OR e.profile_id IS NOT NULL OR e.evidence_id = 'SOURCE_UNIPROT' "
            "OR json_extract(e.payload, '$.details.uniprot') = ?)"
        )
        params.append(PROTEIN)
    if "structure" in seeds:
        values = sorted(seeds["structure"])
        evidence_id = predicate("e.evidence_id", values)
        pdb_id = predicate("json_extract(e.payload, '$.details.pdb_id')", values)
        filters.append(f"({evidence_id} OR {pdb_id})")
        params.extend(values * 2)
    hits, count = select(db, filters, params, match, limit, offset, count=True)
    for record in hits:
        record["match_scope"] = (
            "related_profile" if mutations and record["mutation_id"] not in mutations else "direct"
        )
    return hits, count


def build_graph(db, seeds, hits):
    nodes = {}
    edges = {}

    def node(kind, identifier, label=None, url=None):
        key = f"{kind}:{identifier}"
        nodes.setdefault(key, {"id": key, "type": kind, "identifier": identifier,
                               "label": label or identifier, "source_url": url})
        return key

    def edge(start, relation, end, evidence_id):
        key = (start, relation, end, evidence_id)
        edges[key] = dict(zip(("from", "relation", "to", "evidence_id"), key))

    protein = node("protein", PROTEIN, PROTEIN_NAME, PROTEIN_URL) if seeds.get("protein") else None
    labels = {
        row[0]: row[1] for row in db.execute(
            "SELECT compound_id, json_extract(payload, '$.details.compound_name') FROM evidence "
            "WHERE evidence_category = 'compound_annotation'"
        )
    }
    equivalent_compounds = dict(db.execute(
        "SELECT equivalent_id, compound_id FROM compound_equivalents WHERE substr(compound_id, 1, 4) = 'CMP_'"
    ))
    labels.update({alias: labels.get(canonical) for alias, canonical in equivalent_compounds.items()})
    anchors = []
    for kind, ids in seeds.items():
        for identifier in sorted(ids):
            display = labels.get(identifier) if kind == "compound" else None
            if kind == "assay":
                display = identifier.replace("_", " ")
            anchors.append(node(kind, identifier, display))

    profile_ids = sorted({r["profile_id"] for r in hits if r["profile_id"]})
    components = defaultdict(list)
    if profile_ids:
        for pid, mid in db.execute(
            f"SELECT profile_id, component_id FROM profile_components WHERE {predicate('profile_id', profile_ids)} "
            "ORDER BY profile_id, component_id", profile_ids,
        ):
            components[pid].append(mid)

    for record in hits:
        eid = record["evidence_id"]
        result = node("evidence", eid)
        mid, pid, cid = (record[key] for key in ("mutation_id", "profile_id", "compound_id"))
        if mid or pid or eid == "SOURCE_UNIPROT" or record["details"].get("uniprot") == PROTEIN:
            protein = node("protein", PROTEIN, PROTEIN_NAME, PROTEIN_URL)
        if mid:
            mutation = node("mutation", mid)
            edge(result, "reports_on_variant", mutation, eid)
            edge(protein, "has_indexed_variant", mutation, mid)
        if pid:
            profile = node("profile", pid)
            edge(protein, "has_indexed_profile", profile, pid)
            edge(result, "reports_on_profile", profile, eid)
            for component in components.get(pid, ()):
                edge(node("mutation", component), "part_of_profile", profile, pid)
        if protein and not (mid or pid) and (
            eid == "SOURCE_UNIPROT" or record["details"].get("uniprot") == PROTEIN
        ):
            edge(result, "references_protein", protein, eid)
        if cid:
            compound = node("compound", cid, labels.get(cid))
            edge(result, "mentions_inhibitor", compound, eid)
            if cid in equivalent_compounds:
                canonical = equivalent_compounds[cid]
                edge(compound, "same_compound_as", node("compound", canonical, labels.get(canonical)), eid)
        if record["assay_type"]:
            assay = record["assay_type"]
            edge(result, "has_assay_type", node("assay", assay, assay.replace("_", " ")), eid)
        endpoint = record["details"].get("measurement_type")
        if endpoint:
            edge(result, "reports_endpoint", node("endpoint", endpoint.upper()), eid)
        pdb = record["details"].get("pdb_id")
        if record["assay_type"] == "structural_experiment":
            edge(result, "references_structure", node("structure", pdb or eid), eid)
        source_key = record["doi"] or record["pmid"] or record["source_url"]
        source = node("source", source_key, record["source_title"] or record["source_id"], record["source_url"])
        edge(result, "reported_in", source, eid)
        for kind in ("pmid", "doi"):
            if record[kind] and record[kind].casefold() in seeds.get(kind, ()):
                edge(source, "identified_by", node(kind, record[kind].casefold()), eid)

    return anchors, list(nodes.values()), list(edges.values())


def search_graph(keywords, *, exact_only=False, assay_type=None, cell_line=None, atp_condition=None,
                 limit=15, offset=0, database=DATABASE):
    """Find evidence via keyword-matched nodes and return the traversed relationships."""
    if not isinstance(keywords, str) or not keywords.strip() or len(keywords) > 200:
        raise ValueError("Enter 1–200 characters for graph keyword search.")
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("Graph limit must be an integer from 1 to 50.")
    if type(offset) is not int or offset < 0:
        raise ValueError("Graph offset must be a nonnegative integer.")
    if type(exact_only) is not bool:
        raise ValueError("exact_only must be a boolean.")
    if assay_type is not None and assay_type not in GRAPH_ASSAYS:
        raise ValueError("Unknown graph assay type.")
    if atp_condition is not None and atp_condition not in ATP_CONDITIONS:
        raise ValueError("Choose ATP Km or 1 mmol/L ATP.")
    if cell_line is not None and (
        not isinstance(cell_line, str) or not cell_line.strip() or len(cell_line) > 100
    ):
        raise ValueError("Enter 1–100 characters for the cell line or clone.")
    options = {
        "exact_only": exact_only, "assay_type": assay_type,
        "cell_line": cell_line.strip() if cell_line is not None else None, "atp_condition": atp_condition,
    }
    path = Path(database).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Evidence database missing at {path}. Run scientific_evidence.retriever.build.")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        seeds, match = keyword_seeds(db, keywords)
        if not (seeds or match):
            raise ValueError("Enter a protein, variant, drug, assay or publication keyword.")
        hits, count = linked_records(db, seeds, match, limit, offset, options)
        anchors, nodes, edges = build_graph(db, seeds, hits)
        browse = {}
        if seeds.keys() == {"protein"} and not match:
            for kind, category, column in (
                ("Variants", "mutation_annotation", "mutation_id"),
                ("Inhibitors", "compound_annotation", "compound_id"),
            ):
                browse[kind] = [
                    {"keyword": identifier, "label": label or identifier.removeprefix("EGFR_")}
                    for identifier, label in db.execute(
                        f"SELECT {column}, json_extract(payload, '$.details.compound_name') FROM evidence "
                        f"WHERE evidence_category = ? AND {column} IS NOT NULL ORDER BY {column}", (category,),
                    )
                ]
            browse["Assays"] = [
                {"keyword": assay, "label": assay.replace("_", " ")}
                for assay, in db.execute(
                    "SELECT DISTINCT assay_type FROM evidence WHERE assay_type IS NOT NULL ORDER BY assay_type"
                )
                if assay in ASSAY_TERMS
            ]
    return {"keywords": keywords, "filters": options, "anchors": anchors, "nodes": nodes, "edges": edges,
            "evidence": hits, "total_matches": count, "limit": limit, "offset": offset, "browse": browse}
