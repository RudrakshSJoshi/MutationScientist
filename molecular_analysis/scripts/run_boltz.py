#!/usr/bin/env python3
"""Drive boltz predict with affinity on MPS/CPU.

Bypasses the CLI's gpu|cpu|tpu Choice (Lightning itself supports 'mps') and
forces a stable float32 precision, since boltz hardcodes bf16-mixed which is
unreliable on Apple MPS / CPU.

Usage:
  ACC=mps RECYCLE=3 SS=200 SSA=200 DSA=5 python run_boltz.py <input_dir_or_yaml> <out_dir>
"""
import sys, os
import pytorch_lightning as pl

# Force stable fp32 (boltz hardcodes bf16-mixed, bad on MPS/CPU)
_orig = pl.Trainer.__init__
def _patched(self, *a, **k):
    k["precision"] = "32-true"
    return _orig(self, *a, **k)
pl.Trainer.__init__ = _patched

from boltz.main import predict

data = sys.argv[1]
out_dir = sys.argv[2]
acc = os.environ.get("ACC", "mps")

print(f"[run_boltz] data={data} out={out_dir} accelerator={acc} "
      f"recycle={os.environ.get('RECYCLE','3')} ss={os.environ.get('SS','200')} "
      f"ssa={os.environ.get('SSA','200')} dsa={os.environ.get('DSA','5')}", flush=True)

predict.callback(
    data=data,
    out_dir=out_dir,
    cache=os.path.expanduser("~/.boltz"),
    checkpoint=None,
    affinity_checkpoint=None,
    devices=1,
    accelerator=acc,
    recycling_steps=int(os.environ.get("RECYCLE", "3")),
    sampling_steps=int(os.environ.get("SS", "200")),
    diffusion_samples=1,
    sampling_steps_affinity=int(os.environ.get("SSA", "200")),
    diffusion_samples_affinity=int(os.environ.get("DSA", "5")),
    max_parallel_samples=1,
    step_scale=None,
    write_full_pae=False,
    write_full_pde=False,
    output_format="mmcif",
    num_workers=0,
    override=(os.environ.get("OVERRIDE", "1") == "1"),
    seed=42,
    use_msa_server=False,
    msa_server_url="https://api.colabfold.com",
    msa_pairing_strategy="greedy",
    msa_server_username=None,
    msa_server_password=None,
    api_key_header=None,
    api_key_value=None,
    use_potentials=False,
    model="boltz2",
    method=None,
    affinity_mw_correction=False,
    preprocessing_threads=1,
    max_msa_seqs=8192,
    subsample_msa=True,
    num_subsampled_msa=1024,
    no_kernels=True,
    write_embeddings=False,
)
print("[run_boltz] DONE", flush=True)
