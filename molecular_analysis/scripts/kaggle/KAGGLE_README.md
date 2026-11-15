# Boltz-2 affinity inference on Kaggle P100 — scale-out path

This is the **ready-to-run** config for generating Boltz-2 affinity predictions for
the EGFR complexes on a CUDA GPU, when the local Apple-MPS run is too slow for the
full set. (The MPS run works — see `../README_RUN.md` — but at ~20 min/complex it is
only practical for the demo subset. The full `complexes/test` + `validation` is
thousands of complexes → use a GPU.)

## The two non-obvious gotchas (already handled in `kaggle_boltz_infer.py`)
1. **Precision.** Boltz-2 hardcodes `precision="bf16-mixed"` in its Trainer. The
   Kaggle **P100 is Pascal (sm_60) and has no bf16** → the stock `boltz predict`
   CLI will error or produce garbage on P100. The driver forces
   `PRECISION=16-mixed` (fp16), which Pascal supports. On A100/L4 you may switch
   back to `bf16-mixed` for speed.
2. **Kernels.** The CUDA-only fused kernels (`cuequivariance`, `trifast`) aren't
   reliably present in the Kaggle image. The driver passes `no_kernels=True`
   (the inference-time equivalent of the training config's `use_trifast: false`).

## Step 1 — make a Kaggle Dataset from the complexes + MSAs
Upload the `boltz2/` folder **with its structure intact** so the relative MSA paths
inside each YAML (`msa: ../../msa/<variant>.a3m`) still resolve:
```
egfr-boltz2/                      <- Kaggle dataset slug
  boltz2/
    complexes/
      test/        COMPLEX_*.yaml
      validation/  COMPLEX_*.yaml
      train/       COMPLEX_*.yaml   (optional; huge)
    msa/           EGFR_*.a3m       (all 17 — required)
```
Tip: strip the macOS `* 2.yaml` duplicate artifacts before zipping
(`find boltz2/complexes -name '* 2.yaml' -delete`).

## Step 2 — notebook cells (P100 accelerator ON, internet ON for weights)
```python
!pip -q install boltz
# copy the driver + aggregator into the working dir (upload them as a small dataset,
# or paste their contents into a cell)
import shutil; shutil.copy('/kaggle/input/boltz-scripts/kaggle_boltz_infer.py', '.')
shutil.copy('/kaggle/input/boltz-scripts/build_predictions.py', '.')
shutil.copy('/kaggle/input/boltz-scripts/egfr_dataset_loader.py', '.')  # for the join
```
```python
# run affinity inference over a split (resume-friendly: override=False skips done ones)
!PRECISION=16-mixed ACC=gpu RECYCLE=3 SS=200 SSA=200 DSA=5 \
    python kaggle_boltz_infer.py \
    /kaggle/input/egfr-boltz2/boltz2/complexes/test \
    /kaggle/working/results
```
First run downloads the Boltz-2 weights (`boltz2_conf.ckpt`, `boltz2_aff.ckpt`) and
the CCD to `~/.boltz` (needs internet). ~2–3 GB.

## Step 3 — aggregate to the app schema
`build_predictions.py` expects the EGFR dataset loader + dataset root for the join.
On Kaggle point it at the uploaded dataset root (symlink or set DS_ROOT):
```python
import os
os.environ  # build_predictions.py uses ~/Desktop/EGFR_RESEARCH_DATASET by default;
# on Kaggle, edit DS_ROOT at the top of build_predictions.py to the input path, e.g.
#   DS_ROOT = Path('/kaggle/input/egfr-research-dataset/EGFR_RESEARCH_DATASET')
!python build_predictions.py /kaggle/working/boltz_predictions.json /kaggle/working/results
```
Download `boltz_predictions.json` and drop it where the app's
`BOLTZ_PREDICTIONS_PATH` points. It is a plain JSON array of per-complex records.

## P100 memory note (16 GB)
EGFR full-length is **1210 aa** — a large single chain. On P100 16 GB a full-length
structure pass can approach the VRAM limit. If you hit CUDA OOM:
- lower `num_subsampled_msa` (driver default 1024 → try 512 or 256),
- lower `max_msa_seqs`,
- or run splits in chunks. The run is resume-friendly (`override=False`), so an OOM
  on one complex won't lose the ones already written.

## Throughput
Budget on P100 ~ a few minutes/complex at these settings (fp16, 1210 aa) — far
faster than the ~20 min/complex on MPS. For the whole `test` split, chunk across
Kaggle's session limit and let `override=False` resume across sessions.

## Label convention (do NOT change)
`affinity_pred_value = log10(IC50 in µM); LOWER = STRONGER; NOT pIC50.`
`affinity_probability_binary = P(binder)`. Same convention as the dataset YAML `value`.
