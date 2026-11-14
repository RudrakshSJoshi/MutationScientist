#!/usr/bin/env python3
"""Validate, run, and collect an unchanged EGFR complex cohort by complex_id."""

import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time


SPLITS = {"train": 5515, "validation": 684, "test": 644}
REQUIRED = (
    "README.md", "boltz2/complex_metadata.csv",
    "boltz2/boltz_compatible_dataset.csv", "curated/mutations.csv",
    "curated/compounds.csv", "curated/bindingdb_ligands.csv", "curated/protein_sequences.fasta",
)
ID_FIELDS = ("complex_id", "mutation_id", "compound_id", "split")
SCORE_FIELDS = ("affinity_pred_value", "affinity_probability_binary")
MODEL_FIELDS = ("model_version", "software", "structure_checkpoint_sha256",
                "affinity_checkpoint_sha256", "protocol", *SCORE_FIELDS)
PREDICTION_FIELDS = (
    *ID_FIELDS, *MODEL_FIELDS, "yaml", "yaml_sha256", "msa_files_json",
    "prediction_dir", "structure", "confidence", "embedding", "pre_affinity",
    "confidence_score", "ligand_iptm", "complex_plddt", "structure_checks_passed",
    "experimental_affinity_label", "experimental_affinity_label_unit", "n_replicates",
    "complex_metadata_json", "experimental_reference_json", "reference_join",
)
SCREEN_FIELDS = (
    *PREDICTION_FIELDS, "mutation_name", "compound_name", "inhibitor_class",
    "inhibitor_generation", "covalent_status", "canonical_isomeric_smiles", "chemical_identity_splits",
)
RANK_FIELDS = (*SCREEN_FIELDS, "affinity_rank", "mutation_scored_compounds")
PAIR_FIELDS = (
    "wt_complex_id", "mutant_complex_id", "wt_mutation_id", "mutant_mutation_id",
    "wt_compound_id", "mutant_compound_id", "compound_name", "canonical_isomeric_smiles",
    "wt_split", "mutant_split", "model_version", "affinity_checkpoint_sha256",
    "wt_experimental_affinity_label", "mutant_experimental_affinity_label",
    "wt_affinity_pred_value", "mutant_affinity_pred_value", "mutant_minus_wt",
    "wt_affinity_probability_binary", "mutant_affinity_probability_binary",
    "wt_experimental_reference_json", "mutant_experimental_reference_json",
)
COMPARE_FIELDS = (
    *ID_FIELDS, "baseline_model_version", "specialised_model_version",
    "baseline_affinity_checkpoint_sha256", "specialised_affinity_checkpoint_sha256",
    "experimental_affinity_label", "baseline_affinity_pred_value", "specialised_affinity_pred_value",
    "specialised_minus_baseline", "baseline_affinity_probability_binary",
    "specialised_affinity_probability_binary", "experimental_reference_json",
)
FAILURE_FIELDS = ("complex_id", "model", "status", "detail", "log")


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if not reader.fieldnames or any(None in row or None in row.values() for row in rows):
        raise ValueError(f"Missing header or malformed rows in {path}")
    return rows


def write_csv(path, fields, rows):
    build = path.with_suffix(".tmp")
    with build.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    build.replace(path)


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def json_value(value):
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def valid_id(value):
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]+", value)) and value not in {".", ".."}


def unique_lookup(rows, column, description):
    result = {}
    for row in rows:
        value = row.get(column, "")
        if not value or value in result:
            raise ValueError(f"Missing or duplicate {column} in {description}: {value!r}")
        result[value] = row
    return result


def ligand_identity(compound):
    from rdkit import Chem

    mol = Chem.MolFromSmiles(compound.get("smiles") or compound["isomeric_smiles"])
    if mol is None:
        raise ValueError(f"RDKit could not parse {compound['compound_id']}")
    return Chem.MolToSmiles(mol, isomericSmiles=True)


def dataset(root):
    missing = [name for name in REQUIRED if not (root / name).is_file()]
    for name in ("boltz2/complexes", "boltz2/msa"):
        if not (root / name).is_dir() or not any(p.is_file() and not p.name.startswith(".")
                                                  for p in (root / name).rglob("*")):
            missing.append(name + " (no input files)")
    if missing:
        raise ValueError(f"Incomplete dataset {root}: " + ", ".join(missing))
    if (root / "egfr_dataset_loader.py").is_file():
        check = (
            "from egfr_dataset_loader import EGFRDataset; "
            "ds = EGFRDataset('.'); print(ds.validate()); print(ds.boltz.counts())"
        )
        subprocess.run([sys.executable, "-B", "-c", check], cwd=root, check=True)
    else:
        print("Dataset loader was omitted from delivery. Validating the supplied files directly.")
    rows = read_csv(root / "boltz2/complex_metadata.csv")
    unique_lookup(rows, "complex_id", "complex metadata")
    by_split = Counter(row.get("split") for row in rows)
    if by_split != SPLITS:
        raise ValueError(f"Unexpected split counts: {dict(by_split)}; expected {SPLITS}")
    mutations = unique_lookup(read_csv(root / "curated/mutations.csv"), "mutation_id", "mutations")
    compounds = unique_lookup(
        read_csv(root / "curated/compounds.csv") + read_csv(root / "curated/bindingdb_ligands.csv"),
        "compound_id", "compounds",
    )
    pairs = set()
    ligand_split = {}
    yaml_root = root / "boltz2/complexes"
    yaml_files = {}
    for path in yaml_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".yaml", ".yml"}:
            key = (path.relative_to(yaml_root).parts[0], path.stem)
            if key in yaml_files:
                raise ValueError(f"Duplicate YAML for {key}")
            yaml_files[key] = path
    validation_names = (root / "boltz2/val_names.txt").read_text().splitlines()
    expected_val_ids = {row["complex_id"] for row in rows if row["split"] == "validation"}
    if len(validation_names) != len(expected_val_ids) or set(validation_names) != expected_val_ids:
        raise ValueError("val_names.txt disagrees with the original validation split")
    references = read_csv(root / "boltz2/boltz_compatible_dataset.csv")
    if len(references) != 18189:
        raise ValueError(f"Expected 18189 eligible measurements, found {len(references)}")
    references_by_id = unique_lookup(references, "measurement_id", "eligible reference measurements")
    refs_by_pair = defaultdict(list)
    for ref in references:
        refs_by_pair[ref["mutation_id"], ref["compound_id"]].append(ref)
    used_measurements = set()
    truncated_lists = 0
    for row in rows:
        cid, mid, lid, split = (row.get(field, "") for field in ID_FIELDS)
        if not valid_id(cid) or mid not in mutations or lid not in compounds:
            raise ValueError(f"Invalid identifier mapping for {cid or row}")
        if ligand_split.setdefault(lid, split) != split:
            raise ValueError(f"Ligand crosses data splits: {lid}")
        if (mid, lid) in pairs:
            raise ValueError(f"Duplicate mutation and ligand pair: {mid}, {lid}")
        pairs.add((mid, lid))
        try:
            row["_yaml"] = yaml_files.pop((split, cid))
        except KeyError as exc:
            raise ValueError(f"No YAML with the expected split and stem for {cid}") from exc
        if row["_yaml"].resolve() != (root / row["boltz_input_path"]).resolve():
            raise ValueError(f"Provided YAML path does not match the split and stem: {cid}")
        measurement_ids = row["measurement_ids"].split(";")
        explicit = [references_by_id[value] for value in measurement_ids]
        group = refs_by_pair[mid, lid]
        group_ids = {ref["measurement_id"] for ref in group}
        if (len(group) != int(row["n_replicates"]) or
                len(set(measurement_ids)) != len(measurement_ids) or
                not set(measurement_ids) <= group_ids or used_measurements & group_ids):
            raise ValueError(f"Invalid or reused replicate IDs for {cid}")
        used_measurements.update(group_ids)
        truncated = len(explicit) < len(group)
        truncated_lists += truncated
        row["_refs"] = group if truncated else explicit
        row["_join"] = "measurement_ids_plus_exact_pair" if truncated else "measurement_ids"
        for ref in row["_refs"]:
            if ((ref["mutation_id"], ref["compound_id"], ref["profile_id"]) !=
                    (mid, lid, row["profile_id"]) or ref["measurement_type"] != "IC50"
                    or ref["measurement_relation"] != "=" or ref["boltz_eligibility"] != "eligible"):
                raise ValueError(f"Conflicting or ineligible reference for {cid}")
        labels = [float(ref["boltz_target_value"]) for ref in row["_refs"]]
        label = float(row["affinity_label"])
        if not math.isfinite(label) or abs(sum(labels) / len(labels) - label) > 0.00011:
            raise ValueError(f"Aggregated experimental label differs from its replicates: {cid}")
    if yaml_files:
        raise ValueError(f"Unmatched YAMLs: {len(yaml_files)}")
    print(f"{len(rows)} distinct pairs, {len(ligand_split)} distinct compound IDs, "
          f"{len(used_measurements)} linked of {len(references)} eligible measurements; splits {dict(by_split)}. "
          f"{truncated_lists} truncated source ID lists resolved by the exact pair and replicate count.")
    return sorted(rows, key=lambda r: (list(SPLITS).index(r["split"]), r["complex_id"])), mutations, compounds


def staged_document(path, root):
    import yaml

    document = yaml.safe_load(path.read_text())
    msa_paths = []
    proteins = [entity["protein"] for entity in document["sequences"] if "protein" in entity]
    ligands = [entity["ligand"] for entity in document["sequences"] if "ligand" in entity]
    affinity = [item["affinity"] for item in document.get("properties", []) if "affinity" in item]
    if not proteins or len(affinity) != 1 or not any(
        item.get("id") == affinity[0].get("binder") for item in ligands
    ):
        raise ValueError(f"Expected protein and one ligand marked for affinity in {path}")
    for protein in proteins:
        msa = protein.get("msa")
        if not isinstance(msa, str) or msa in {"", "empty"}:
            raise ValueError(f"Missing precomputed MSA in {path}")
        resolved = (path.parent / msa).resolve()
        if not resolved.is_file() and not Path(msa).is_absolute():
            resolved = (root / msa).resolve()
        if (resolved.suffix.lower() not in {".a3m", ".csv"} or
                not resolved.is_file() or not resolved.stat().st_size):
            raise ValueError(f"Unreadable precomputed MSA for {path}: {msa}")
        msa_paths.append(str(resolved))
        protein["msa"] = str(resolved)
    for template in document.get("templates", []):
        for key in ("cif", "pdb"):
            if key in template:
                resolved = (path.parent / template[key]).resolve()
                if not resolved.is_file():
                    raise ValueError(f"Missing supplied template for {path}: {resolved}")
                template[key] = str(resolved)
    return document, msa_paths


@lru_cache(maxsize=None)
def read_msa_query(path):
    parts = []
    with path.open() as handle:
        if not handle.readline().startswith(">"):
            raise ValueError(f"Missing A3M query header: {path}")
        for line in handle:
            if line.startswith(">"):
                break
            parts.append(line.strip())
    return "".join(parts)


def protein_sequences(path):
    records = {}
    for line in path.read_text().splitlines():
        if line.startswith(">"):
            key = line[1:].split()[0]
            if key in records:
                raise ValueError(f"Repeated FASTA sequence: {key}")
            records[key] = ""
        elif line.strip():
            records[key] += line.strip()
    return records


def validate_yaml(row, root, sequences, compound):
    document, paths = staged_document(row["_yaml"], root)
    protein = next(entity["protein"] for entity in document["sequences"] if "protein" in entity)
    ligand = next(entity["ligand"] for entity in document["sequences"] if "ligand" in entity)
    affinity = next(item["affinity"] for item in document["properties"] if "affinity" in item)
    msa = Path(paths[0])
    if (len(paths) != 1 or msa != (root / row["msa_path"]).resolve()
            or protein["sequence"] != sequences[row["sequence_id"]]
            or (msa.suffix == ".a3m" and read_msa_query(msa) != protein["sequence"])
            or float(affinity["value"]) != float(row["affinity_label"])):
        raise ValueError(f"YAML, MSA query, sequence or label mismatch: {row['complex_id']}")
    if ligand["smiles"] not in {compound.get(k) for k in ("smiles", "isomeric_smiles", "canonical_smiles")}:
        raise ValueError(f"YAML ligand SMILES differs from the source compound: {row['complex_id']}")
    return document, paths


def init_outputs(out):
    out.mkdir(parents=True, exist_ok=True)
    for name in ("baseline_predictions", "embeddings", "comparison_plots"):
        (out / name).mkdir(exist_ok=True)


def selection(rows, args):
    ids = set(args.id or [])
    if args.ids_file:
        ids.update(line.strip() for line in args.ids_file.read_text().splitlines() if line.strip())
    active = [r for r in rows if r["split"] in args.splits and (not ids or r["complex_id"] in ids)]
    if ids - {r["complex_id"] for r in active}:
        raise ValueError("Some selected IDs were absent from the requested splits")
    if not active:
        raise ValueError("No input complexes selected")
    return active


def read_prediction(record, provenance, paths, deliver, model):
    cid = record["complex_id"]
    pred = paths / cid
    affinity = json.loads((pred / f"affinity_{cid}.json").read_text())
    scores = {key: float(affinity[key]) for key in SCORE_FIELDS}
    if not all(math.isfinite(value) for value in scores.values()) or not 0 <= scores[SCORE_FIELDS[1]] <= 1:
        raise ValueError("Nonfinite score or affinity probability outside [0,1]")
    confidence = pred / f"confidence_{cid}_model_0.json"
    values = json.loads(confidence.read_text())
    if not math.isfinite(float(values["confidence_score"])):
        raise ValueError("Nonfinite confidence score")
    structure = pred / f"{cid}_model_0.cif"
    if not structure.is_file() or structure.stat().st_size < 100:
        raise ValueError("Missing predicted mmCIF")
    import gemmi

    parsed = gemmi.read_structure(str(structure))
    if not len(parsed) or len(parsed[0]) < 2:
        raise ValueError("Expected at least a protein and ligand chain in predicted mmCIF")
    output = {
        **record, **provenance, **scores, "prediction_dir": str(pred), "structure": str(structure),
        "confidence": str(confidence), "confidence_score": values["confidence_score"],
        "ligand_iptm": values.get("ligand_iptm"), "complex_plddt": values.get("complex_plddt"),
        "structure_checks_passed": values.get("structure_checks_passed"),
    }
    if model == "baseline":
        import numpy as np

        emb = pred / f"embeddings_{cid}.npz"
        with np.load(emb, allow_pickle=False) as data:
            s, z = data["s"], data["z"]
            if s.ndim == 3 and z.ndim == 4 and s.shape[0] == z.shape[0] == 1:
                s, z = s[0], z[0]
            if (s.ndim != 2 or z.ndim != 3 or z.shape[:2] != (s.shape[0], s.shape[0])
                    or s.shape[-1] != 384 or z.shape[-1] != 128 or not s.size or not z.size or not np.isfinite(s).all() or not np.isfinite(z).all()):
                raise ValueError("Invalid s/z embedding shapes or nonfinite values")
        raw = pred / f"pre_affinity_{cid}.npz"
        with np.load(raw, allow_pickle=False) as data:
            if "atoms" not in data or "chains" not in data or not len(data["atoms"]):
                raise ValueError("Invalid pre-affinity structure archive")
        link = deliver / emb.name
        if link.is_symlink() and link.resolve() != emb.resolve():
            raise ValueError(f"Embedding already points to a different run: {link}")
        if not link.exists():
            if link.is_symlink():
                raise ValueError(f"Broken embedding link: {link}")
            link.symlink_to(os.path.relpath(emb, deliver))
        if not link.is_symlink() or not link.samefile(emb):
            raise ValueError(f"Embedding name already exists with different data: {link}")
        output.update(embedding=str(link), pre_affinity=str(raw))
    return output


def run_shard(args, rows, root, out, compounds):
    if args.enable_kernels and args.accelerator != "gpu":
        raise ValueError("--enable-kernels requires the CUDA GPU backend")
    if args.specialised and (not args.affinity_checkpoint or "train" in args.splits):
        raise ValueError("Specialised inference requires --affinity-checkpoint and held-out splits only")
    if not args.specialised and args.affinity_checkpoint:
        raise ValueError("Baseline must use the pretrained affinity weights in --cache")
    if not args.specialised and len(rows) > 10 and not args.embedding_dir:
        raise ValueError("Set the owner-agreed --embedding-dir for a baseline cohort run")
    tag = "specialised" if args.specialised else "baseline"
    deliver = (args.embedding_dir or out / "embeddings").resolve()
    cache = args.cache.resolve()
    run_dir = out / (f"{tag}_predictions") / args.shard
    inputs = run_dir / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    deliver.mkdir(parents=True, exist_ok=True)
    lock = run_dir / "running"
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise ValueError(f"Shard is locked: {lock}") from exc
    try:
        run_locked(args, rows, root, out, tag, run_dir, inputs, deliver, cache, compounds)
    finally:
        lock.rmdir()


def run_locked(args, rows, root, out, tag, run_dir, inputs, deliver, cache, compounds):
    import yaml

    structure_ckpt = cache / "boltz2_conf.ckpt"
    affinity_ckpt = (args.affinity_checkpoint or cache / "boltz2_aff.ckpt").resolve()
    missing = [p for p in (structure_ckpt, cache / "boltz2_aff.ckpt", affinity_ckpt)
               if not p.is_file() or not p.stat().st_size]
    mols = cache / "mols"
    if not mols.is_dir() or not any(mols.iterdir()):
        missing.append(mols)
    if missing:
        raise ValueError(f"Prepopulate the Boltz cache before inference. Missing: {missing}")
    cmd = [str(args.boltz.resolve()), "predict", str(inputs), "--out_dir", str(run_dir),
           "--cache", str(cache), "--model", "boltz2", "--checkpoint", str(structure_ckpt),
           "--affinity_checkpoint", str(affinity_ckpt), "--accelerator", args.accelerator,
           "--devices", "1", "--seed", str(args.seed), "--recycling_steps", "3",
           "--sampling_steps", "200", "--diffusion_samples", "1",
           "--sampling_steps_affinity", "200", "--diffusion_samples_affinity", "5",
           "--output_format", "mmcif", "--num_workers", "0", "--max_msa_seqs", "8192",
           "--preprocessing-threads", "1"]
    if not args.enable_kernels:
        cmd.append("--no_kernels")
    if not args.boltz.is_file():
        raise ValueError(f"Boltz executable not found: {args.boltz}")
    cli = subprocess.run([cmd[0], "predict", "--help"], check=True, capture_output=True, text=True)
    if "--skip_bad_inputs" in cli.stdout:
        cmd.append("--skip_bad_inputs")
    if tag == "baseline":
        cmd.append("--write_embeddings")
    if args.retry:
        cmd.append("--override")
    provenance = {
        "model_version": f"Boltz-2 {tag}", "software": args.software,
        "structure_checkpoint_sha256": sha256(structure_ckpt),
        "affinity_checkpoint_sha256": sha256(affinity_ckpt),
        "protocol": json_value({"seed": args.seed, "accelerator": args.accelerator,
                                "structure_recycling": 3, "structure_steps": 200, "structure_samples": 1,
                                "affinity_steps": 200, "affinity_samples": 5, "max_msa_seqs": 8192,
                                "kernels": args.enable_kernels, "affinity_mw_correction": False,
                                "external_msa": False}),
    }
    records = {}
    staged = {}
    failed = []
    log = run_dir / "inference.log"
    sequences = protein_sequences(root / "curated/protein_sequences.fasta")
    for row in rows:
        cid = row["complex_id"]
        try:
            document, msas = validate_yaml(row, root, sequences, compounds[row["compound_id"]])
        except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError) as exc:
            failed.append(dict(complex_id=cid, model=tag, status="invalid_input", detail=str(exc), log=str(log)))
            continue
        staged[cid] = yaml.safe_dump(document, sort_keys=False, allow_unicode=True)
        records[cid] = {
            **{field: row[field] for field in ID_FIELDS}, "yaml": str(row["_yaml"]),
            "yaml_sha256": sha256(row["_yaml"]), "msa_files_json": json_value(msas),
            "experimental_affinity_label": row["affinity_label"],
            "experimental_affinity_label_unit": row["affinity_label_unit"],
            "n_replicates": row["n_replicates"],
            "complex_metadata_json": json_value({k: v for k, v in row.items() if not k.startswith("_")}),
            "experimental_reference_json": json_value(row["_refs"]), "reference_join": row["_join"],
            "msa_sha256": {p: file_hash(Path(p)) for p in set(msas)},
        }
    manifest = run_dir / "shard.json"
    request = {"command": [item for item in cmd if item != "--override"], "provenance": provenance, "inputs": records, "failed_inputs": failed}
    if manifest.exists() and json.loads(manifest.read_text()) != request:
        raise ValueError(f"Shard already has a different input or checkpoint manifest: {run_dir}")
    manifest.write_text(json_value(request) + "\n")
    for cid, text in staged.items():
        path = inputs / f"{cid}.yaml"
        if not path.exists() or path.read_text() != text:
            path.write_text(text)
    if {p.name for p in inputs.iterdir()} != {f"{cid}.yaml" for cid in staged}:
        raise ValueError(f"Unexpected staged inputs found in {inputs}")
    start = time.monotonic()
    rc = None
    execution_error = ""
    if records:
        numba_cache = run_dir / "numba_cache"
        numba_cache.mkdir(exist_ok=True)
        env = {**os.environ, "NUMBA_CACHE_DIR": str(numba_cache),
               "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"}
        print(f"Starting Boltz for {len(records)} complex(es). Log: {log}", flush=True)
        with log.open("a", encoding="utf-8") as handle:
            try:
                with subprocess.Popen(cmd, cwd=out, env=env, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True, errors="replace") as process:
                    try:
                        for line in process.stdout:
                            print(line, end="", flush=True)
                            handle.write(line)
                            handle.flush()
                        rc = process.wait()
                    except KeyboardInterrupt:
                        if process.poll() is None:
                            process.terminate()
                            try:
                                process.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait()
                        execution_error = "Run interrupted during inference."
                        handle.write(execution_error + "\n")
                        rc = 130
            except OSError as exc:
                execution_error = f"Unable to launch Boltz: {exc}"
                handle.write(execution_error + "\n")
                rc = 1
    print(f"{args.shard}: Boltz exit {rc}; elapsed {time.monotonic() - start:.1f}s; log {log}")
    result_root = run_dir / "boltz_results_inputs/predictions"
    successes = []
    for cid, row in records.items():
        try:
            successes.append(read_prediction(row, provenance, result_root, deliver, tag))
        except (OSError, KeyError, ValueError, TypeError, RuntimeError) as exc:
            failed.append(dict(complex_id=cid, model=tag, status="failed_or_incomplete",
                               detail=execution_error or str(exc), log=str(log)))
    write_csv(run_dir / "predictions.csv", PREDICTION_FIELDS, successes)
    write_csv(run_dir / "failure_ledger.csv", FAILURE_FIELDS, failed)
    print(f"{tag} {args.shard}: {len(successes)} verified, {len(failed)} failed")
    if failed or rc not in {None, 0}:
        raise SystemExit(2)


file_hash = lru_cache(maxsize=None)(sha256)


def collate(out, rows, tag):
    expected = {row["complex_id"] for row in rows if tag == "baseline" or row["split"] != "train"}
    all_rows = []
    statuses = {}
    for path in sorted((out / f"{tag}_predictions").glob("*/predictions.csv")):
        for row in read_csv(path):
            cid = row["complex_id"]
            if cid not in expected:
                raise ValueError(f"Unexpected {tag} complex ID: {cid}")
            all_rows.append(row)
        for row in read_csv(path.parent / "failure_ledger.csv"):
            if row["complex_id"] not in expected:
                raise ValueError(f"Unexpected {tag} failure ID: {row['complex_id']}")
            statuses[row["complex_id"]] = row
    attempts = out / "setup_attempts.csv"
    if attempts.is_file():
        for row in read_csv(attempts):
            if row["model"] == tag and row["complex_id"] in expected:
                statuses.setdefault(row["complex_id"], row)
    actual = unique_lookup(all_rows, "complex_id", f"{tag} output shards")
    metadata_by_id = {r["complex_id"]: r for r in rows}
    for cid, row in actual.items():
        original = metadata_by_id[cid]
        if any(row[k] != original[k] for k in ID_FIELDS) or row["yaml_sha256"] != sha256(original["_yaml"]):
            raise ValueError(f"Identity mismatch or source YAML changed: {cid}")
    if len({tuple(row[field] for field in MODEL_FIELDS[:-2]) for row in all_rows}) > 1:
        raise ValueError(f"Mixed model configurations in {tag} shards")
    missing = [
        statuses.get(cid, {"complex_id": cid, "model": tag, "status": "unrun",
                           "detail": "No completed shard output"})
        for cid in sorted(expected - actual.keys())
    ]
    return actual, missing


def field(row, names):
    return next((row.get(name) for name in names if row.get(name)), "")


def tables(out, rows, mutations, compounds, wt_ids):
    baseline, missing = collate(out, rows, "baseline")
    specialised, later = collate(out, rows, "specialised")
    write_csv(out / "baseline_predictions.csv", PREDICTION_FIELDS, baseline.values())
    write_csv(out / "specialised_predictions.csv", PREDICTION_FIELDS, specialised.values())
    write_csv(out / "failure_ledger.csv", FAILURE_FIELDS, missing + later)
    coverage = dict(
        expected_baseline=len(rows), verified_baseline=len(baseline),
        expected_specialised=sum(row["split"] != "train" for row in rows),
        verified_specialised=len(specialised),
        missing_baseline=dict(Counter(row["status"] for row in missing)),
        missing_specialised=dict(Counter(row["status"] for row in later)),
    )
    (out / "coverage.json").write_text(json_value(coverage) + "\n")
    scoped = {row["compound_id"] for row in rows} | {key for key, value in compounds.items() if value.get("compound_name")}
    chem = {cid: ligand_identity(compounds[cid]) for cid in sorted(scoped)}
    curated = {chem[key]: value for key, value in compounds.items() if value.get("compound_name")}
    splits_by_chem = defaultdict(set)
    for row in rows:
        splits_by_chem[chem[row["compound_id"]]].add(row["split"])
    screened = []
    for record in baseline.values():
        mutation = mutations[record["mutation_id"]]
        identity = chem[record["compound_id"]]
        compound = curated.get(identity, compounds[record["compound_id"]])
        screened.append({
            **record, "mutation_name": field(mutation, ("mutation_notation", "mutation_name", "name", "mutation", "variant")),
            "compound_name": field(compound, ("compound_name", "name", "preferred_name", "ligand_name")),
            "inhibitor_class": compound.get("drug_class", ""),
            "inhibitor_generation": compound.get("inhibitor_generation", ""),
            "covalent_status": compound.get("covalent_status", ""),
            "canonical_isomeric_smiles": identity,
            "chemical_identity_splits": ";".join(sorted(splits_by_chem[identity])),

        })
    write_csv(out / "screening_results.csv", SCREEN_FIELDS, screened)
    write_csv(out / "affinity_landscape.csv", SCREEN_FIELDS,
              sorted(screened, key=lambda row: (row["compound_id"], row["mutation_id"])))
    profiles = defaultdict(list)
    for row in screened:
        profiles[row["mutation_id"]].append(row)
    rankings = []
    for profile in profiles.values():
        ordered = sorted(profile, key=lambda row: (float(row[SCORE_FIELDS[0]]), row["compound_id"]))
        last, rank = None, 0
        for index, row in enumerate(ordered, 1):
            score = float(row[SCORE_FIELDS[0]])
            rank = index if score != last else rank
            rankings.append({**row, "affinity_rank": rank, "mutation_scored_compounds": len(profile)})
            last = score
    write_csv(out / "inhibitor_rankings.csv", RANK_FIELDS, rankings)
    inferred_wt = {mid for mid, meta in mutations.items() if mid.casefold() in {"wt", "wildtype", "wild_type"}
                   or field(meta, ("mutation_notation", "mutation_name", "name", "mutation", "variant")).casefold()
                   in {"wt", "wild type", "wild-type", "wildtype"}}
    wt_ids = set(wt_ids or inferred_wt)
    if wt_ids - mutations.keys():
        raise ValueError(f"Unknown WT mutation IDs: {wt_ids - mutations.keys()}")
    wt = defaultdict(list)
    for row in screened:
        if row["mutation_id"] in wt_ids:
            wt[row["canonical_isomeric_smiles"]].append(row)
    pairs = []
    for mutant in screened:
        if mutant["mutation_id"] in wt_ids:
            continue
        for reference in wt[mutant["canonical_isomeric_smiles"]]:
            pairs.append({
                **mutant, "wt_complex_id": reference["complex_id"], "mutant_complex_id": mutant["complex_id"],
                "wt_mutation_id": reference["mutation_id"], "mutant_mutation_id": mutant["mutation_id"],
                "wt_compound_id": reference["compound_id"], "mutant_compound_id": mutant["compound_id"],
                "wt_split": reference["split"], "mutant_split": mutant["split"],
                "wt_experimental_affinity_label": reference["experimental_affinity_label"],
                "mutant_experimental_affinity_label": mutant["experimental_affinity_label"],
                "wt_affinity_pred_value": reference[SCORE_FIELDS[0]], "mutant_affinity_pred_value": mutant[SCORE_FIELDS[0]],
                "mutant_minus_wt": float(mutant[SCORE_FIELDS[0]]) - float(reference[SCORE_FIELDS[0]]),
                "wt_affinity_probability_binary": reference[SCORE_FIELDS[1]],
                "mutant_affinity_probability_binary": mutant[SCORE_FIELDS[1]],
                "wt_experimental_reference_json": reference["experimental_reference_json"],
                "mutant_experimental_reference_json": mutant["experimental_reference_json"],
            })
    write_csv(out / "wt_mutant_comparisons.csv", PAIR_FIELDS, pairs)
    comparison = []
    for cid in sorted(baseline.keys() & specialised.keys()):
        b, s = baseline[cid], specialised[cid]
        if b["protocol"] != s["protocol"] or b["structure_checkpoint_sha256"] != s["structure_checkpoint_sha256"] or b["software"] != s["software"]:
            raise ValueError(f"Baseline and specialised protocols differ for {cid}")
        comparison.append({
            **b, "baseline_model_version": b["model_version"], "specialised_model_version": s["model_version"],
            "baseline_affinity_checkpoint_sha256": b["affinity_checkpoint_sha256"],
            "specialised_affinity_checkpoint_sha256": s["affinity_checkpoint_sha256"],
            "baseline_affinity_pred_value": b[SCORE_FIELDS[0]], "specialised_affinity_pred_value": s[SCORE_FIELDS[0]],
            "specialised_minus_baseline": float(s[SCORE_FIELDS[0]]) - float(b[SCORE_FIELDS[0]]),
            "baseline_affinity_probability_binary": b[SCORE_FIELDS[1]], "specialised_affinity_probability_binary": s[SCORE_FIELDS[1]],
        })
    write_csv(out / "baseline_vs_finetuned.csv", COMPARE_FIELDS, comparison)
    print(f"{len(baseline)} verified baseline, {len(specialised)} verified specialised, {len(pairs)} paired WT contrasts")
    if baseline and not wt_ids:
        print("No WT ID resolved. Supply --wt-id for paired WT comparisons.", file=sys.stderr)


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("validate")
    report = actions.add_parser("collect")
    report.add_argument("--wt-id", action="append")
    run = actions.add_parser("run")
    run.add_argument("--boltz", type=Path, required=True)
    run.add_argument("--software", required=True, help="Boltz distribution, version and commit if available")
    run.add_argument("--cache", type=Path, required=True)
    run.add_argument("--shard", required=True)
    run.add_argument("--accelerator", choices=("gpu", "mps", "cpu"), default="gpu")
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--enable-kernels", action="store_true", help="Allow Boltz CUDA kernels on a compatible GPU")
    run.add_argument("--splits", choices=tuple(SPLITS), nargs="+", default=list(SPLITS))
    run.add_argument("--id", action="append")
    run.add_argument("--ids-file", type=Path)
    run.add_argument("--embedding-dir", type=Path)
    run.add_argument("--specialised", action="store_true")
    run.add_argument("--affinity-checkpoint", type=Path)
    run.add_argument("--retry", action="store_true", help="Recompute outputs in this same shard")
    return parser.parse_args()


def main():
    args = arguments()
    root, out = args.dataset.resolve(), args.out.resolve()
    rows, mutations, compounds = dataset(root)
    init_outputs(out)
    if args.action == "validate":
        sequences = protein_sequences(root / "curated/protein_sequences.fasta")
        for row in rows:
            validate_yaml(row, root, sequences, compounds[row["compound_id"]])
        print("Validated all {} YAMLs and precomputed MSA paths".format(len(rows)))
    elif args.action == "run":
        if not valid_id(args.shard):
            raise ValueError("Invalid shard name")
        run_shard(args, selection(rows, args), root, out, compounds)
    else:
        tables(out, rows, mutations, compounds, args.wt_id)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
