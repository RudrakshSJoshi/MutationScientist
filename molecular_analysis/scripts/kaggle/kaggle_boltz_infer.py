#!/usr/bin/env python3
"""Boltz-2 affinity INFERENCE driver for Kaggle P100 (or any CUDA box).

Why this wrapper instead of the bare `boltz predict` CLI:
  * Boltz-2 HARDCODES precision "bf16-mixed" (boltz/main.py Trainer). The Kaggle
    P100 is Pascal (sm_60) and has NO bf16 -> the stock CLI crashes/garbles on P100.
    We force precision "16-mixed" (fp16), which Pascal supports.  <-- the key fix
  * We disable the CUDA-only fused kernels (cuequivariance / trifast) that are not
    reliably built in the Kaggle image (no_kernels=True; equivalent to the
    training-config `use_trifast: false`).

On an Ampere+ GPU (A100/L4/T4-with-bf16... actually T4 is Turing=fp16 too) you can
leave PRECISION=16-mixed; on A100 you may set PRECISION=bf16-mixed for speed.

Usage (Kaggle cell):
  !pip -q install boltz
  !PRECISION=16-mixed ACC=gpu python kaggle_boltz_infer.py \
        /kaggle/input/egfr-boltz2/boltz2/complexes/test  /kaggle/working/results

Then aggregate:
  !python build_predictions.py /kaggle/working/boltz_predictions.json /kaggle/working/results

Env knobs: PRECISION (default 16-mixed), ACC (gpu), RECYCLE(3), SS(200),
SSA(200), DSA(5), DEVICES(1).
"""
import sys, os
import pytorch_lightning as pl

PRECISION = os.environ.get("PRECISION", "16-mixed")
_orig = pl.Trainer.__init__
def _patched(self, *a, **k):
    k["precision"] = PRECISION          # override boltz's hardcoded bf16-mixed
    return _orig(self, *a, **k)
pl.Trainer.__init__ = _patched

from boltz.main import predict

data, out_dir = sys.argv[1], sys.argv[2]
print(f"[kaggle_boltz_infer] data={data} out={out_dir} precision={PRECISION} "
      f"acc={os.environ.get('ACC','gpu')}", flush=True)

predict.callback(
    data=data, out_dir=out_dir,
    cache=os.path.expanduser(os.environ.get("BOLTZ_CACHE", "~/.boltz")),
    checkpoint=None, affinity_checkpoint=None,
    devices=int(os.environ.get("DEVICES", "1")),
    accelerator=os.environ.get("ACC", "gpu"),
    recycling_steps=int(os.environ.get("RECYCLE", "3")),
    sampling_steps=int(os.environ.get("SS", "200")),
    diffusion_samples=1,
    sampling_steps_affinity=int(os.environ.get("SSA", "200")),
    diffusion_samples_affinity=int(os.environ.get("DSA", "5")),
    max_parallel_samples=1, step_scale=None,
    write_full_pae=False, write_full_pde=False,
    output_format="mmcif", num_workers=int(os.environ.get("NW", "2")),
    override=False,                      # resume-friendly: skips complexes already done
    seed=42, use_msa_server=False,
    msa_server_url="https://api.colabfold.com", msa_pairing_strategy="greedy",
    msa_server_username=None, msa_server_password=None,
    api_key_header=None, api_key_value=None,
    use_potentials=False, model="boltz2", method=None,
    affinity_mw_correction=False, preprocessing_threads=int(os.environ.get("NW", "2")),
    max_msa_seqs=8192, subsample_msa=True, num_subsampled_msa=1024,
    no_kernels=True, write_embeddings=False,
)
print("[kaggle_boltz_infer] DONE", flush=True)
