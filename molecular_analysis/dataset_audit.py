#!/usr/bin/env python3
"""Audit chemical identity overlap and export observed experimental references."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path

from pipeline import dataset, json_value, ligand_identity, read_csv, sha256, write_csv

PRIORITIES = (
    "EGFR_WT", "EGFR_L858R", "EGFR_ex19del", "EGFR_T790M", "EGFR_C797S",
    "EGFR_L858R_T790M", "EGFR_L858R_C797S", "EGFR_ex19del_T790M",
    "EGFR_ex19del_C797S", "EGFR_T790M_C797S", "EGFR_L858R_T790M_C797S",
    "EGFR_ex19del_T790M_C797S",
)


def audit(root, out):
    rows, mutations, compounds = dataset(root)
    curated = {key: value for key, value in compounds.items() if value.get("compound_name")}
    scoped = set(curated) | {row["compound_id"] for row in rows}
    identity = {key: ligand_identity(compounds[key]) for key in sorted(scoped)}
    curated_by_identity = {identity[key]: value for key, value in curated.items()}
    same_chemistry = defaultdict(list)
    for row in rows:
        same_chemistry[identity[row["compound_id"]]].append(row)

    cross_split = {
        key: group for key, group in same_chemistry.items() if len({row["split"] for row in group}) > 1
    }
    overlap = []
    for key, group in cross_split.items():
        for row in group:
            overlap.append({
                **row, "canonical_isomeric_smiles": key,
                "curated_compound_name": curated_by_identity.get(key, {}).get("compound_name", ""),
                "chemical_identity_splits": ";".join(sorted({item["split"] for item in group})),
            })
    write_csv(out / "cross_split_chemical_identities.csv",
              ("complex_id", "mutation_id", "compound_id", "split", "canonical_isomeric_smiles",
               "curated_compound_name", "chemical_identity_splits"), overlap)

    write_csv(out / "complex_input_manifest.csv", (
        "complex_id", "mutation_id", "profile_id", "compound_id", "split", "boltz_input_path",
        "yaml_sha256", "msa_path", "sequence_id", "affinity_label", "affinity_label_unit",
        "n_replicates", "reference_join", "eligible_measurement_ids", "named_compound",
        "exact_chemical_identity_crosses_splits",
    ), [
        {**row, "yaml_sha256": sha256(row["_yaml"]), "reference_join": row["_join"],
         "eligible_measurement_ids": ";".join(ref["measurement_id"] for ref in row["_refs"]),
         "named_compound": curated_by_identity.get(identity[row["compound_id"]], {}).get("compound_name", ""),
         "exact_chemical_identity_crosses_splits": identity[row["compound_id"]] in cross_split}
        for row in rows
    ])

    group_size = Counter((row["mutation_id"], row["split"]) for row in rows)
    write_csv(out / "mutation_coverage.csv", ("mutation_id", "mutation_name", "train", "validation", "test", "total"), [
        {"mutation_id": mid, "mutation_name": value["mutation_notation"],
         **{split: group_size[mid, split] for split in ("train", "validation", "test")},
         "total": sum(group_size[mid, split] for split in ("train", "validation", "test"))}
        for mid, value in mutations.items()
    ])

    raw = read_csv(root / "curated/affinity_measurements.csv")
    groups = defaultdict(list)
    for row in raw:
        groups[row["mutation_id"], row["compound_id"]].append(row)
    named_pairs = []
    named_measurements = []
    for key, compound in curated.items():
        name = compound["compound_name"]
        chemistry = identity[key]
        aliases = {row["compound_id"] for row in same_chemistry.get(chemistry, [])} | {key}
        cohort = {mid: [row for row in same_chemistry.get(chemistry, []) if row["mutation_id"] == mid]
                  for mid in PRIORITIES}
        observed_mutations = set(PRIORITIES) | {r["mutation_id"] for r in same_chemistry.get(chemistry, [])}
        for mid in sorted(observed_mutations):
            pairs = cohort.get(mid, [row for row in same_chemistry.get(chemistry, []) if row["mutation_id"] == mid])
            references = [row for alias in sorted(aliases) for row in groups[mid, alias]]
            if not pairs and not references:
                continue
            named_measurements.extend(
                {**row, "curated_compound_id": key, "compound_name": name} for row in references
            )
            named_pairs.append({
                "curated_compound_id": key, "compound_name": name,
                "inhibitor_class": compound["drug_class"], "covalent_status": compound["covalent_status"],
                "mutation_id": mid, "mutation_name": mutations[mid]["mutation_notation"],
                "cohort_status": "present_in_boltz" if pairs else "experimental_reference_only",
                "complex_ids": ";".join(row["complex_id"] for row in pairs),
                "dataset_compound_ids": ";".join(sorted({row["compound_id"] for row in pairs})),
                "splits": ";".join(sorted({row["split"] for row in pairs})),
                "cohort_labels_json": json_value({row["complex_id"]: row["affinity_label"] for row in pairs}),
                "measurement_count": len(references),
            })
    write_csv(out / "named_inhibitor_references.csv", (
        "curated_compound_id", "compound_name", "inhibitor_class", "covalent_status", "mutation_id",
        "mutation_name", "cohort_status", "complex_ids", "dataset_compound_ids", "splits",
        "cohort_labels_json", "measurement_count",
    ), named_pairs)
    if named_measurements:
        write_csv(out / "named_inhibitor_measurements.csv", tuple(named_measurements[0]), named_measurements)

    # Pair only observations from the same paper, assay condition, compound and units.
    conditions = defaultdict(dict)
    for row in raw:
        if row["source_database"] == "literature" and row["measurement_type"] == "IC50":
            key = (row["compound_id"], row["source_record_id"], row["doi"], row["original_unit"])
            if row["mutation_id"] in conditions[key]:
                raise ValueError(f"Ambiguous literature measurement for {key} and {row['mutation_id']}")
            conditions[key][row["mutation_id"]] = row
    controls = (
        ("EGFR_L858R", "EGFR_L858R_C797S"), ("EGFR_ex19del", "EGFR_ex19del_C797S"),
        ("EGFR_L858R_T790M", "EGFR_L858R_T790M_C797S"),
        ("EGFR_ex19del_T790M", "EGFR_ex19del_T790M_C797S"),
        ("EGFR_WT", "EGFR_L858R"), ("EGFR_WT", "EGFR_ex19del"),
    )
    contrasts = []
    for key, data in conditions.items():
        compound, condition, doi, unit = key
        for pre, post in controls:
            if pre not in data or post not in data:
                continue
            a, b = data[pre], data[post]
            av, bv = a["original_value"], b["original_value"]
            if a["measurement_relation"] != "=" or b["measurement_relation"] not in {"=", ">"} or not av or not bv:
                continue
            contrasts.append(dict(
                compound_id=compound, compound_name=curated[compound]["compound_name"],
                reference_mutation_id=pre, comparison_mutation_id=post, condition=condition, doi=doi,
                unit=unit, reference_value=av, comparison_value=bv,
                comparison_relation=b["measurement_relation"],
                fold_ic50_or_lower_bound=round(float(bv) / float(av), 4),
                reference_measurement_id=a["measurement_id"], comparison_measurement_id=b["measurement_id"],
            ))
    write_csv(out / "experimental_matched_contrasts.csv", (
        "compound_id", "compound_name", "reference_mutation_id", "comparison_mutation_id", "condition", "doi",
        "unit", "reference_value", "comparison_value", "comparison_relation", "fold_ic50_or_lower_bound",
        "reference_measurement_id", "comparison_measurement_id",
    ), contrasts)
    print(f"{len(same_chemistry)} exact canonical structures; {len(cross_split)} cross splits "
          f"across {len(overlap)} complexes; affected complexes by split: {dict(Counter(row['split'] for row in overlap))}")
    print(f"{len(named_pairs)} named inhibitor reference groups and {len(contrasts)} measured contrasts")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    options = parser.parse_args()
    audit(options.dataset.resolve(), options.out.resolve())
