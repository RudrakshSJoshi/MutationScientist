#!/usr/bin/env python3
"""Run a bounded local Boltz-2 diagnostic on EGFR C797S and brigatinib."""

import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

import gemmi
import numpy as np
import yaml

FIRST_RESIDUE = 696
LAST_RESIDUE = 1022
MSA_DEPTH = 16
NAME = "EGFR_C797S_brigatinib_kinase_diagnostic"
TIMEOUT_SECONDS = 600


def a3m_records(path):
    header, chunks = "", []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(">"):
                if header:
                    yield header, "".join(chunks)
                header, chunks = line, []
            else:
                chunks.append(line)
    if header:
        yield header, "".join(chunks)


def crop_alignment(sequence, expected_width):
    columns = []
    for character in sequence:
        if character.islower():
            if columns:
                columns[-1].append(character)
        else:
            columns.append([character])
    if len(columns) != expected_width:
        raise ValueError(f"MSA row has {len(columns)} aligned columns, expected {expected_width}")
    return "".join("".join(column) for column in columns[FIRST_RESIDUE - 1:LAST_RESIDUE])


def prepare_input(dataset, directory):
    source = dataset / "boltz2/complexes/train/COMPLEX_000001.yaml"
    document = yaml.safe_load(source.read_text())
    protein = next(entry["protein"] for entry in document["sequences"] if "protein" in entry)
    ligand = next(entry["ligand"] for entry in document["sequences"] if "ligand" in entry)
    sequence = protein["sequence"]
    if len(sequence) != 1210 or sequence[796] != "S":
        raise ValueError("Expected the full-length C797S EGFR input for COMPLEX_000001")
    a3m = (source.parent / protein["msa"]).resolve()
    query = sequence[FIRST_RESIDUE - 1:LAST_RESIDUE]
    alignment_path = directory / f"{NAME}.a3m"
    rows, seen = [], set()
    for header, row in a3m_records(a3m):
        cropped = crop_alignment(row, len(sequence))
        if not rows and cropped != query:
            raise ValueError("Cropped MSA query does not match the kinase-domain sequence")
        identity = "".join(letter for letter in cropped if letter.isupper())
        if identity and identity not in seen:
            rows.extend((header, cropped))
            seen.add(identity)
        if len(seen) == MSA_DEPTH:
            break
    if len(seen) != MSA_DEPTH:
        raise ValueError(f"Could not select {MSA_DEPTH} distinct kinase-domain sequences")
    alignment_path.write_text("\n".join(rows) + "\n")
    diagnostic = {
        "version": 1,
        "sequences": [
            {"protein": {"id": protein["id"], "sequence": query, "msa": str(alignment_path)}},
            {"ligand": ligand},
        ],
        "properties": [{"affinity": {"binder": ligand["id"]}}],
    }
    input_path = directory / f"{NAME}.yaml"
    input_path.write_text(yaml.safe_dump(diagnostic, sort_keys=False))
    return input_path


def stop(process):
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def run(input_path, directory, boltz, cache, accelerator):
    command = [
        str(boltz.resolve()), "predict", str(input_path), "--out_dir", str(directory),
        "--cache", str(cache), "--accelerator", accelerator, "--model", "boltz2",
        "--devices", "1", "--seed", "42", "--num_workers", "0", "--preprocessing-threads", "1",
        "--recycling_steps", "0", "--sampling_steps", "10", "--diffusion_samples", "1",
        "--sampling_steps_affinity", "10", "--diffusion_samples_affinity", "1",
        "--max_parallel_samples", "1", "--max_msa_seqs", str(MSA_DEPTH),
        "--no_write_full_pae", "--no_write_full_pde", "--no_kernels", "--write_embeddings",
    ]
    numba_cache = directory / "numba_cache"
    numba_cache.mkdir()
    env = {**os.environ, "NUMBA_CACHE_DIR": str(numba_cache), "PYTHONUNBUFFERED": "1",
           "PYTHONDONTWRITEBYTECODE": "1"}
    log = directory / "inference.log"
    start = time.monotonic()
    with log.open("w") as log_writer, log.open("rb") as log_reader:
        process = subprocess.Popen(command, cwd=directory, env=env, stdout=log_writer,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            while process.poll() is None:
                elapsed = time.monotonic() - start
                # Print each heartbeat even during a single Boltz forward pass.
                chunk = log_reader.read()
                if chunk:
                    print(chunk.decode(errors="replace").replace("\r", "\n"), end="", flush=True)
                if elapsed >= TIMEOUT_SECONDS:
                    raise TimeoutError(f"Diagnostic stopped after {TIMEOUT_SECONDS // 60} minutes. Log: {log}")
                print(f"\nBoltz is running · {elapsed:.0f}s elapsed", flush=True)
                try:
                    process.wait(timeout=min(20, TIMEOUT_SECONDS - elapsed))
                except subprocess.TimeoutExpired:
                    continue
        except (KeyboardInterrupt, TimeoutError):
            stop(process)
            raise
        finally:
            trailing = log_reader.read()
            if trailing:
                print(trailing.decode(errors="replace").replace("\r", "\n"), end="", flush=True)
    if process.returncode:
        raise RuntimeError(f"Boltz exited with {process.returncode}. Log: {log}")
    print(f"\nBoltz process finished in {time.monotonic() - start:.1f}s")


def verify(directory):
    result = directory / f"boltz_results_{NAME}" / "predictions" / NAME
    scores = json.loads((result / f"affinity_{NAME}.json").read_text())
    value = float(scores["affinity_pred_value"])
    probability = float(scores["affinity_probability_binary"])
    if not math.isfinite(value) or not 0 <= probability <= 1:
        raise ValueError("Diagnostic affinity scores are invalid")
    structure = gemmi.read_structure(str(result / f"{NAME}_model_0.cif"))
    if len(structure) != 1 or len(structure[0]) != 2:
        raise ValueError("Diagnostic structure is missing the protein or ligand chain")
    confidence = json.loads((result / f"confidence_{NAME}_model_0.json").read_text())
    if not math.isfinite(float(confidence["confidence_score"])):
        raise ValueError("Diagnostic structure confidence is invalid")
    with np.load(result / f"embeddings_{NAME}.npz", allow_pickle=False) as data:
        s, z = data["s"], data["z"]
        if s.ndim == 3 and z.ndim == 4 and s.shape[0] == z.shape[0] == 1:
            s, z = s[0], z[0]
        if (s.ndim != 2 or z.ndim != 3 or z.shape != (s.shape[0], s.shape[0], 128)
                or s.shape[0] <= LAST_RESIDUE - FIRST_RESIDUE + 1 or s.shape[1] != 384
                or not np.isfinite(s).all() or not np.isfinite(z).all()):
            raise ValueError("Diagnostic embedding tensors are invalid")
        print(f"Verified affinity output, structure, confidence and embeddings {s.shape}, {z.shape}.")
    print(f"Diagnostic outputs: {result}")


def main():
    home = Path.home()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=home / "Downloads/EGFR_RESEARCH_DATASET 2")
    parser.add_argument("--cache", type=Path, default=home / ".boltz")
    parser.add_argument("--out", type=Path, default=home / "egfr-escape-atlas/task2/results")
    parser.add_argument("--boltz", type=Path, default=Path(sys.executable).parent / "boltz")
    parser.add_argument("--accelerator", choices=("mps", "cpu", "gpu"), default="mps")
    args = parser.parse_args()
    cache = args.cache.expanduser().resolve()
    for name in ("mols", "boltz2_conf.ckpt", "boltz2_aff.ckpt"):
        if not (cache / name).exists():
            raise ValueError(f"Missing cache component: {cache / name}")
    args.out.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="kinase_diagnostic_", dir=args.out.resolve()))
    print(f"Diagnosing only. The 327-residue kinase input and reduced sampling are outside the full-length baseline.\nRun directory: {directory}", flush=True)
    source = prepare_input(args.dataset.resolve(), directory)
    run(source, directory, args.boltz, cache, args.accelerator)
    verify(directory)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit("Diagnostic interrupted.")
    except (OSError, ValueError, RuntimeError) as error:
        raise SystemExit(str(error))
