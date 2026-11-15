# Run the EGFR molecular analysis

## Inputs

Use the original dataset directory with the six data files and `boltz2/complexes` and `boltz2/msa` folders. The user’s Mac has the dataset at `~/Downloads/EGFR_RESEARCH_DATASET 2` and Boltz in `~/egfr-escape-atlas/task2/.venv`. For a GPU runner, carry the dataset tree together so its source-relative MSA links resolve. The pipeline stages a copy of each selected YAML under its original stem and rebases only file paths. It reads the experimental labels and preserves the source YAML and CSV files.

Prepare the checkpoint cache on the inference machine. For the installed community CLI, the following command downloads the official weights and CCD data. The cache should contain `mols/`, `boltz2_conf.ckpt`, and `boltz2_aff.ckpt`. Use a path writable by the inference account.

```bash
VENV="$HOME/egfr-escape-atlas/task2/.venv"
DATA="$HOME/Downloads/EGFR_RESEARCH_DATASET 2"
CACHE="$HOME/.boltz"
"$VENV/bin/python" -c 'from pathlib import Path; from boltz.main import download_boltz2; p = Path.home() / ".boltz"; p.mkdir(exist_ok=True); download_boltz2(p); print(p)'
```

The Python environment needs Boltz, NumPy, PyYAML, RDKit and Gemmi. Matplotlib is needed for the report plots. Start inside the extracted `molecular_analysis/` directory. Set `VENV`, `DATA` and `CACHE` to their paths on the machine running inference. Record the exact installed Boltz version.

## Quick GPU diagnostic

From Terminal, run `"$VENV/bin/python" -B kinase_smoke_test.py`. This local diagnostic uses EGFR residues 696–1022, 16 rows from the supplied MSA and the original brigatinib ligand. It writes to a fresh directory and prints progress every 20 seconds, with a ten-minute timeout. A pass checks the structure, confidence, both affinity fields and embedding arrays. The input construct and sampling differ from the original complex, so use the diagnostic only to test the output path. Benchmark the original full-length input separately on the intended production GPU.

## Verify a pilot and agree the handoff directory

```bash
"$VENV/bin/python" -B pipeline.py --dataset "$DATA" validate
"$VENV/bin/python" -B pipeline.py --dataset "$DATA" run \
  --boltz "$VENV/bin/boltz" --software boltz-community/2.13.0 \
  --cache "$CACHE" --accelerator gpu --enable-kernels --shard pilot \
  --id COMPLEX_000001
"$VENV/bin/python" -B pipeline.py --dataset "$DATA" collect --wt-id EGFR_WT
```

Use a CUDA GPU for this full-length benchmark after the MPS attempt crossed an hour without completing structure prediction. The example allows Boltz's CUDA kernels on a compatible runner. The pipeline shows output live and saves it to the shard log. Measure runtime, peak VRAM and compressed embedding size before scheduling the cohort. At about 1,250 tokens, the raw FP32 pair tensor `z` alone is about **0.80 GB per complex** with 128 channels, or **5.5 TB for 6,843** before compression. Storage planning should use measured on-disk bytes, including the prediction and processed-input artifacts.

Agree the full-run `--embedding-dir` with the training owner. For a portable output tree, use its `embeddings/` subdirectory. The default pilot mapping uses that directory. The baseline CSV contains the original YAML, source hash, MSA paths, prediction directory, scores, confidence output, embeddings, pre-affinity structure and unchanged experimental labels. The input manifest records MSA and checkpoint SHA-256 hashes. The embedding directory uses links to the raw NPZs to avoid another large copy. For transfer to a different machine, preserve the complete output tree or dereference links explicitly and verify file sizes.

The affinity fork uses processed records, processed MSAs and ligand molecules alongside the pre-affinity structure and the embedding. The raw `baseline_predictions/<shard>/boltz_results_inputs/` trees retain them. Have the training owner load one training complex through their actual dataset module to verify token order, shapes and fork compatibility. If the owner consolidates outputs for the audited fork, package only train and validation artifacts for training. Its split loader treats every record outside the validation list as training. Retain the test artifacts for evaluation.

## Shared project repository

Keep the CLI, evaluation code, report and small audited tables within the task folder assigned by the team. Use an agreed output path for model caches and bulk prediction/embedding artifacts, and record their mapping and location in the task folder. The training owner needs the manifest, processed structures, ligand and MSA data, and embedding files through the agreed handoff path.

## Run the cohort

Use disjoint ID lists from the metadata or one shard per split. To preserve a single inference protocol, use the same executable, checkpoint hashes, backend and settings, including for later specialised scoring. If the pilot completed under different settings, use it as a benchmark and put production outputs in a separate output root with `--out`. If using the same output root, exclude pilot IDs from subsequent shards.

```bash
"$VENV/bin/python" -B pipeline.py --dataset "$DATA" run \
  --boltz "$VENV/bin/boltz" --software boltz-community/2.13.0 \
  --cache "$CACHE" --accelerator gpu --enable-kernels --shard production_batch_001 \
  --splits train --ids-file train_batch_001.txt --embedding-dir "$EMBEDDING_DIR"
"$VENV/bin/python" -B pipeline.py --dataset "$DATA" collect --wt-id EGFR_WT
```

`coverage.json` gives the expected and verified totals. `failure_ledger.csv` distinguishes unrun rows and failed outputs. A failed shard can be resumed using its original invocation and name. Use `--retry` if the CLI's existing-output detection is skipping an incomplete result. The wrapper records incomplete or unreadable outputs even if Boltz exits successfully.

## Evaluate the specialised affinity checkpoint

Use `--specialised --affinity-checkpoint /path/to/owner_checkpoint.ckpt --splits validation test` with a new shard name and the same Boltz executable and other run settings. A fork-specific checkpoint format should be smoke-tested with the owner’s runtime before scaling. Then run the collector again, followed by `evaluate.py "$DATA"` using the environment with Matplotlib installed. Use `dataset_audit.py "$DATA"` to regenerate the chemical-identity and named-inhibitor tables. Run `structural_analysis/analyse_structures.py` with NumPy and Matplotlib to regenerate the experimental overlays. For a Boltz-produced protein–ligand mmCIF, run `structural_analysis/predicted_contacts.py` with the source CIF, the single-record canonical P00533 FASTA (`raw/mutations/uniprot_P00533.fasta`), complex ID and destination CSV. This uses Biopython for clinical residue mapping, and reads pLDDT from the Boltz B-factor field.
