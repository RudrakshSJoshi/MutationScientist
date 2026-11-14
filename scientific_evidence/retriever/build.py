"""Build the packaged SQLite evidence index from a dataset checkout."""

import argparse
import csv
import html
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import NamedTemporaryFile

PACKAGE = Path(__file__).resolve().parents[1]
DATABASE = PACKAGE / "evidence_database" / "evidence.sqlite3"
DEFAULT_DATASET = PACKAGE.parent / "EGFR_RESEARCH_DATASET"

ASSAYS = {
    "biochemical_kinase_mobility_shift": "enzyme_inhibition",
    "biochemical_binding": "biochemical_binding",
    "enzyme_inhibition": "enzyme_inhibition",
    "cellular_viability": "cellular_viability",
    "cellular_pathway_inhibition": "cellular_pathway_inhibition",
}
FRONTIERS = (
    "https://www.frontiersin.org/journals/oncology/articles/10.3389/fonc.2026.1952701/full"
)
YUN_DOI = "10.1073/pnas.0709662105"
MELIS_DOI = "10.3389/fonc.2026.1952701"
MELIS_TITLE = "Comparative profiling of osimertinib and fourth-generation EGFR inhibitors on EGFR-mutant proteins and cell lines"
YUN_TITLE = "The T790M mutation in EGFR kinase causes drug resistance by increasing the affinity for ATP"
SOURCE_ALIASES = {
    "BindingDB": "SOURCE_BINDINGDB",
    "UNIPROT_P00533": "SOURCE_UNIPROT",
}
CLAIM_SCOPE_NOTES = {
    "EVIDENCE_00009": (
        "The source's case involved C797S with no detectable T790M. "
        "Use primary T790M data for gefitinib resistance mechanisms."
    ),
    "EVIDENCE_00027": (
        "The cited work studies osimertinib resistance. Broad cross-inhibitor "
        "resistance requires drug-specific evidence."
    ),
}


def read_csv(root, name):
    with (root / name).open(encoding="utf-8", newline="") as stream:
        yield from csv.DictReader(stream)


def split(value):
    return [piece.strip() for piece in value.split(";") if piece.strip()]


def normalise(value):
    return " ".join(value.strip().casefold().split())


def source_fields(row, source, source_id):
    url = row.get("source_url") or source.get("source_url")
    doi = row.get("doi") or source.get("doi")
    if url == "https://europepmc.org/abstract/MED/" and (
        source.get("database_record_id") == "PMC13634975"
    ):
        url = FRONTIERS
        doi = MELIS_DOI
    pmid = row.get("pmid") or source.get("pmid")
    if not url and doi:
        url = "https://doi.org/" + doi
    if not url and pmid:
        url = "https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/"
    return {
        "source_id": source_id or None,
        "source_title": html.unescape(
            row.get("source_title") or source.get("title") or row.get("publication") or ""
        ) or None,
        "pmid": pmid or None,
        "doi": doi or None,
        "source_url": url or None,
    }


def record(evidence_id, claim, kind, category, origin, *, assay_type=None,
           strength="not_assessed", mutation_id=None, profile_id=None,
           compound_id=None, cancer_context=None, source=None, details=None):
    return {
        "evidence_id": evidence_id, "claim": claim, "evidence_type": kind,
        "assay_type": assay_type, "evidence_category": category,
        "evidence_strength": strength, "mutation_id": mutation_id or None,
        "profile_id": profile_id or None, "compound_id": compound_id or None,
        "cancer_context": cancer_context or None,
        **source_fields({}, {}, None), **(source or {}),
        "origin": origin, "details": details or {},
    }


def measurement(row, origin, sources, compounds):
    raw_assay = row["assay_type"]
    curated_binding = row.get("doi", "").lower() == YUN_DOI and row["measurement_type"] == "KD"
    assay = "biochemical_binding" if curated_binding else ASSAYS.get(raw_assay, "unspecified")
    source_id = row.get("source_id") or {
        "BindingDB": "SOURCE_BINDINGDB",
        "literature": "SOURCE_MELIS" if row.get("doi") == MELIS_DOI else "",
    }.get(row.get("source_database"), "")
    source = source_fields(row, sources.get(source_id, {}), source_id)
    if curated_binding:
        source["source_title"] = YUN_TITLE
        source["source_url"] = "https://doi.org/" + YUN_DOI
    name = compounds.get(row["compound_id"], row["compound_id"])
    relation = row.get("measurement_relation", "") or None
    value = row.get("original_value") or None
    endpoint = row["measurement_type"]
    variant = row.get("mutation_profile") or row["mutation_id"]
    if value:
        quantity = " ".join(filter(None, (relation, value, row["original_unit"])))
        claim = f"{name} against {variant}: reported {endpoint} {quantity}."
    else:
        claim = f"{name} against {variant}: {endpoint} was not determined."
    if assay == "unspecified":
        claim += " The assay format is unspecified in this dataset."
    if row.get("assay_description"):
        claim += f" {row['assay_description'].rstrip('.')}."
    if row.get("cell_line"):
        claim += f" Cell line: {row['cell_line']}."
    if curated_binding:
        claim += " Direct binding by fluorescence quenching (Yun et al., Table 1)."
    details = {
        "measurement_type": endpoint,
        "relation": relation, "value": value, "unit": row.get("original_unit") or None,
        "normalized_value": row.get("normalised_value") or None,
        "normalized_unit": row.get("normalised_unit") or None,
        "raw_assay_type": raw_assay,
        "assay_description": row.get("assay_description") or None,
        "protein_construct": row.get("protein_construct") or None,
        "organism": row.get("organism") or None,
        "temperature": row.get("temperature") or None,
        "ph": row.get("ph") or None,
        "cell_line": row.get("cell_line") or None,
        "treatment_duration": row.get("treatment_duration") or None,
        "quality_flag": row.get("quality_flag") or None,
        "source_record_id": row.get("source_record_id") or None,
        "source_database": row.get("source_database") or None,
        "database_record_url": row.get("source_url") if curated_binding else None,
        "publication_year": row.get("publication_year") or None,
        "missing_value_reason": row.get("exclusion_reason") if not value else None,
    }
    if source_id == "SOURCE_MELIS" and "C797S" in row["mutation_id"] and (
        row.get("quality_flag") == "covalent_time_dependent_IC50"
    ):
        details["interpretation_note"] = (
            "The original dataset flag tracks the compound class. The C797S construct lacks the "
            "Cys797 covalent anchor. Table 2 does not mark this value as covalent/time-dependent."
        )
    return record(
        row.get("measurement_id") or row["assay_id"], claim,
        "experimental" if value else "assay_status",
        "measurement", origin, assay_type=assay,
        strength="primary_table" if raw_assay in ASSAYS or curated_binding else "database_record",
        mutation_id=row["mutation_id"], profile_id=row.get("profile_id"),
        compound_id=row["compound_id"], cancer_context=row.get("cancer_type"),
        source=source, details=details,
    )


def rows_with_origin(root, file, id_column):
    for row in read_csv(root, file):
        yield row, {"kind": "dataset", "file": file, "record_id": row[id_column]}


def load_records(root, db):
    sources = {row["source_id"]: row for row in read_csv(root, "REFERENCES.csv")}
    for source in sources.values():
        if source.get("database_record_id") == "PMC13634975" and source["title"] == MELIS_TITLE:
            source.update(pmid="42835192", doi=MELIS_DOI, source_url=FRONTIERS)
    mutations = {row["mutation_id"]: row for row in read_csv(root, "curated/mutations.csv")}
    profiles = {row["profile_id"]: row for row in read_csv(root, "curated/mutation_profiles.csv")}
    variant_profiles = {row["sequence_id"]: key for key, row in profiles.items() if row["sequence_id"]}
    for mid in mutations:
        variant_profiles.setdefault(mid, "PROF_" + mid.removeprefix("EGFR_"))
    compounds = {"BDB_5447": "gefitinib"}
    aliases = {}

    for mid, row in mutations.items():
        for label in (mid, row["mutation_notation"]):
            aliases["mutation", normalise(label)] = mid
    for pid, row in profiles.items():
        for label in (pid, row["mutation_profile"], row["mutation_profile"].replace("/", "_")):
            aliases["profile", normalise(label)] = pid
        for component in split(row["individual_mutation_ids"]):
            if component in mutations and variant_profiles[component] != pid:
                db.execute("INSERT INTO profile_components VALUES (?, ?)", (component, pid))
    for row in read_csv(root, "curated/bindingdb_ligands.csv"):
        cid = row["compound_id"]
        aliases["compound", normalise(cid)] = cid
    for row in read_csv(root, "curated/compounds.csv"):
        cid = row["compound_id"]
        compounds[cid] = row["compound_name"]
        for label in (cid, row["compound_name"], *split(row["synonyms"])):
            aliases["compound", normalise(label)] = cid
    db.executemany("INSERT INTO aliases VALUES (?, ?, ?)", ((*key, value) for key, value in aliases.items()))
    db.executemany("INSERT INTO compound_equivalents VALUES (?, ?)", (
        ("CMP_GEFITINIB", "BDB_5447"), ("BDB_5447", "CMP_GEFITINIB"),
    ))
    for row in read_csv(root, "validation/conflicting_measurements.csv"):
        db.execute("INSERT INTO coverage VALUES (?, ?, ?)", (
            row["mutation_id"], row["compound_id"], json.dumps(row),
        ))

    for sid, row in sources.items():
        yield record(sid, "Reference entry: " + html.unescape(row["title"]), "reference",
                     "publication", {"kind": "dataset", "file": "REFERENCES.csv", "record_id": sid},
                     source=source_fields(row, row, sid), details={
                         "source_type": row["source_type"],
                         "publication_year": row["publication_year"] or None,
                     })

    for row, origin in rows_with_origin(root, "curated/mutations.csv", "mutation_id"):
        mid = row["mutation_id"]
        sid = row["source_id"]
        yield record(mid, f"{row['mutation_notation']}: {row['known_mechanism']}",
                     "annotation", "mutation_annotation", origin, mutation_id=mid,
                     profile_id=variant_profiles[mid], cancer_context=row["cancer_type"],
                     source=source_fields(row, sources.get(SOURCE_ALIASES.get(sid, sid), {}), sid),
                     details={key: row[key] for key in (
                         "reference_isoform", "position", "wt_residue", "mutant_residue",
                         "mutation_classification", "protein_domain", "resistance_association",
                         "annotation_confidence", "evidence_level",
                     )})

    for row, origin in rows_with_origin(root, "curated/mutation_profiles.csv", "profile_id"):
        pid = row["profile_id"]
        sid = row["source_ids"]
        known_mid = next((mid for mid, profile in variant_profiles.items() if profile == pid), None)
        yield record(pid, f"{row['mutation_profile']}: {row['biological_context']}",
                     "annotation", "mutation_profile", origin, mutation_id=known_mid,
                     profile_id=pid, cancer_context=row["cancer_type"],
                     source=source_fields(row, sources.get(SOURCE_ALIASES.get(sid, sid), {}), sid),
                     details={"component_ids": split(row["individual_mutation_ids"]),
                              "classification": row["classification"],
                              "annotation_confidence": row["annotation_confidence"]})

    for row, origin in rows_with_origin(root, "curated/compounds.csv", "compound_id"):
        cid = row["compound_id"]
        mechanism = row["binding_mechanism"]
        yield record(cid, f"{row['compound_name']}: {mechanism}.", "annotation",
                     "compound_annotation", origin, compound_id=cid,
                     source=source_fields(row, {}, row["source_id"]),
                     details={key: row[key] for key in (
                         "compound_name", "synonyms", "inhibitor_generation", "covalent_status",
                         "known_resistance_context", "annotation_confidence", "inchikey",
                     )})

    for row, origin in rows_with_origin(root, "curated/biological_evidence.csv", "evidence_id"):
        sid, mid = row["source_id"], row["mutation_id"]
        interpretation = CLAIM_SCOPE_NOTES.get(row["evidence_id"])
        verification = "citation_scope_flagged" if interpretation else "dataset_annotation_unverified"
        yield record(
            row["evidence_id"], row["claim"], row["evidence_type"], row["evidence_category"], origin,
            assay_type=row["assay_type"] or None, strength=row["evidence_strength"],
            mutation_id=mid, profile_id=variant_profiles.get(mid),
            compound_id=row["compound_id"], cancer_context=row["cancer_type"],
            source=source_fields(row, sources[sid], sid),
            details={"mechanism": row["mechanism"], "experimental_model": row["experimental_model"],
                     "experimental_finding": row["experimental_finding"],
                     "annotation_confidence": row["annotation_confidence"],
                     "claim_verification": verification, "interpretation_note": interpretation,
                     "original_source_url": row["source_url"] or None},
        )

    for path, key in (("curated/affinity_measurements.csv", "measurement_id"),
                      ("curated/cellular_assays.csv", "assay_id")):
        for row, origin in rows_with_origin(root, path, key):
            yield measurement(row, origin, sources, compounds)

    for row, origin in rows_with_origin(root, "curated/protein_structures/structures_index.csv", "pdb_id"):
        pdb = row["pdb_id"]
        yield record(pdb, html.unescape(row["title"]), "experimental", "structural_observation",
                     origin, assay_type="structural_experiment", strength="database_record",
                     source={**source_fields(row, {}, pdb), "source_title": html.unescape(row["title"])},
                     details={key: row[key] for key in ("method", "resolution_A", "bound_ligands",
                                                       "mutation_status", "uniprot")})

    with (PACKAGE / "evidence_database" / "primary_evidence.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            supplemental = json.loads(line)
            yield record(**supplemental)


def index_row(item):
    cls = item["evidence_strength"]
    priorities = {"primary_table": 0, "primary_observation": 0, "database_record": 2,
                  "literature_association": 3}
    values = tuple(item[key] for key in (
        "evidence_id", "mutation_id", "profile_id", "compound_id", "evidence_type",
        "assay_type", "evidence_category", "cancer_context", "pmid",
    ))
    details = item["details"]
    if details.get("claim_verification") == "citation_scope_flagged":
        cls = "scope_flagged"
    priority = 1 if item["evidence_type"] == "assay_status" else priorities.get(cls, 4)
    # Index labels and study descriptions, without duplicating the full payload.
    search_text = " ".join(str(value) for value in (
        *values, item["claim"], item["source_title"], item["doi"], item["source_id"],
        details.get("resistance_association"), details.get("known_resistance_context"),
        details.get("mechanism"), details.get("synonyms"), details.get("raw_assay_type"),
        details.get("locator"), details.get("source_record_id"), details.get("assay_description"),
    ) if value)
    context = item["cancer_context"]
    if context and ("nsclc" in context.lower() or "non-small-cell lung cancer" in context.lower()):
        search_text += " NSCLC non-small-cell lung cancer"
    return (*values, (item["doi"] or "").lower() or None, priority,
            json.dumps(item, ensure_ascii=False, separators=(",", ":")), search_text)


def build(dataset_root, destination):
    if not (dataset_root / "DATASET_MANIFEST.json").exists():
        dataset_root = dataset_root / "EGFR_RESEARCH_DATASET"
    if not (dataset_root / "DATASET_MANIFEST.json").is_file():
        raise FileNotFoundError(f"Dataset manifest missing in {dataset_root}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=destination.parent, suffix=".sqlite3", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with closing(sqlite3.connect(temporary)) as db, db:
            db.executescript((PACKAGE / "evidence_index" / "schema.sql").read_text(encoding="utf-8"))
            db.executemany(
                "INSERT INTO evidence VALUES (NULL,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (index_row(item) for item in load_records(dataset_root, db)),
            )
            db.execute("INSERT INTO search(search) VALUES ('rebuild')")
            db.execute("INSERT INTO search(search, rank) VALUES ('integrity-check', 1)")
            db.execute("PRAGMA user_version = 1")
            total = db.execute("SELECT count(*) FROM evidence").fetchone()[0]
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DATABASE)
    args = parser.parse_args()
    print(f"Indexed {build(args.dataset, args.output):,} records in {args.output}")
