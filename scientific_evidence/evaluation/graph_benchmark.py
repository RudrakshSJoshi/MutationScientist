"""Check graph keyword search against scoped cases and the indexed source records."""

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from scientific_evidence.evidence_api import search_graph
from scientific_evidence.retriever.graph import PROTEIN
from scientific_evidence.retriever.search import DATABASE

QUESTIONS = Path(__file__).with_name("graph_questions.jsonl")
ROW_LINKS = {
    "reports_on_variant": ("mutation", "mutation_id"),
    "reports_on_profile": ("profile", "profile_id"),
    "mentions_inhibitor": ("compound", "compound_id"),
    "has_assay_type": ("assay", "assay_type"),
}


def require(test, message):
    if not test:
        raise ValueError(message)


def record_at(db, evidence_id):
    result = db.execute("SELECT payload FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
    require(result is not None, f"Missing indexed evidence {evidence_id}")
    return json.loads(result[0])


def verify_edge(db, edge, nodes, row):
    start = nodes[edge["from"]]
    end = nodes[edge["to"]]
    relation = edge["relation"]
    evidence_id = row["evidence_id"]
    if relation in ROW_LINKS:
        kind, field = ROW_LINKS[relation]
        return start["id"] == f"evidence:{evidence_id}" and end["id"] == f"{kind}:{row[field]}"
    if relation == "part_of_profile":
        link = db.execute(
            "SELECT 1 FROM profile_components WHERE component_id = ? AND profile_id = ?",
            (start["identifier"], end["identifier"]),
        ).fetchone()
        return bool(link) and start["type"] == "mutation" and end["id"] == f"profile:{evidence_id}"
    if relation == "same_compound_as":
        equivalent = db.execute(
            "SELECT 1 FROM compound_equivalents WHERE compound_id = ? AND equivalent_id = ?",
            (start["identifier"], end["identifier"]),
        ).fetchone()
        return bool(equivalent) and start["id"] == f"compound:{row['compound_id']}" and end["type"] == "compound"
    if relation in {"has_indexed_variant", "has_indexed_profile"}:
        kind, category = ("mutation", "mutation_annotation") if relation.endswith("variant") else ("profile", "mutation_profile")
        return start["id"] == f"protein:{PROTEIN}" and end["id"] == f"{kind}:{evidence_id}" and row["evidence_category"] == category
    if relation == "references_protein":
        return (
            start["id"] == f"evidence:{evidence_id}" and end["id"] == f"protein:{PROTEIN}"
            and (evidence_id == "SOURCE_UNIPROT" or row["details"].get("uniprot") == PROTEIN)
        )
    if relation == "references_structure":
        pdb = row["details"].get("pdb_id") or evidence_id
        return start["id"] == f"evidence:{evidence_id}" and end["id"] == f"structure:{pdb}" and row["assay_type"] == "structural_experiment"
    if relation == "reports_endpoint":
        endpoint = row["details"].get("measurement_type", "").upper()
        return start["id"] == f"evidence:{evidence_id}" and end["id"] == f"endpoint:{endpoint}"
    source_key = row["doi"] or row["pmid"] or row["source_url"]
    if relation == "reported_in":
        return (
            start["id"] == f"evidence:{evidence_id}" and end["id"] == f"source:{source_key}"
            and bool(row["source_url"])
        )
    if relation == "identified_by":
        kind = end["type"]
        return kind in {"doi", "pmid"} and start["id"] == f"source:{source_key}" and end["identifier"] == row[kind].casefold()
    return False


def verify_case(db, case, graph):
    if "anchor" in case:
        require(case["anchor"] in graph["anchors"], "Expected graph anchor was absent.")
    if "min_matches" in case:
        require(graph["total_matches"] >= case["min_matches"], "Too few indexed records matched.")
    else:
        for key, scope in (("direct", "direct"), ("related", "related_profile")):
            matches = {row["evidence_id"] for row in graph["evidence"] if row["match_scope"] == scope}
            require(matches == set(case[key]), f"{scope} expected {case[key]}, got {sorted(matches)}")
        require(graph["total_matches"] == len(case["direct"]) + len(case["related"]), "Unexpected result count.")

    nodes = {node["id"]: node for node in graph["nodes"]}
    for card in graph["evidence"]:
        row = record_at(db, card["evidence_id"])
        require(row == {key: value for key, value in card.items() if key != "match_scope"},
                f"Evidence card {card['evidence_id']} differs from its indexed source.")
    for edge in graph["edges"]:
        row = record_at(db, edge["evidence_id"])
        require(verify_edge(db, edge, nodes, row), f"Unsupported graph edge {edge}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DATABASE)
    args = parser.parse_args()
    cases = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]
    failures = []
    cards = 0
    edges = 0
    with closing(sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        for case in cases:
            try:
                graph = search_graph(case["keywords"], database=args.database, limit=5, **case.get("filters", {}))
                verify_case(db, case, graph)
            except (KeyError, ValueError) as exc:
                failures.append(case["id"])
                print(f"{case['id']} FAIL {exc}")
            else:
                cards += len(graph["evidence"])
                edges += len(graph["edges"])
                print(f"{case['id']} PASS")
    print(f"{len(cases) - len(failures)}/{len(cases)} cases passed. Verified {cards} evidence cards and {edges} graph edges.")
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
