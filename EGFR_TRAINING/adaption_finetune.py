#!/usr/bin/env python3
"""
adaption_finetune.py — push the EGFR MutationScientist SFT dataset to Adaption
AutoScientist and launch a Qwen/Qwen3.5-4B supervised fine-tune (SFT, LoRA).

Endpoints (verified from docs.adaptionlabs.ai, 2026-11-14):
  BASE = https://api.prod.adaptionlabs.ai   (paths under /api/v1/...)
  auth : Authorization: Bearer $ADAPTION_API_KEY   (key format pt_live_...)
  POST /api/v1/datasets/upload/initiate   {name, file_format}        -> {upload_url, dataset_id?}
  PUT  <upload_url>                        (raw file bytes)
  POST /api/v1/datasets/upload/complete    {dataset_id|upload id}    -> {dataset_id}
  POST /api/v1/autoscientist               {dataset_id, model, training_method, column_mapping}
  GET  /api/v1/autoscientist/{id}          -> {status, ...}
  GET  /api/v1/autoscientist/models        -> supported base models

SFT requires >= 1000 rows. We upload sft_train + sft_validation (1,126) and keep
sft_test (215) as a held-out external eval. Column mapping: prompt, completion.

Nothing here fabricates results. It only does what Adaption returns. The paid
training run is launched ONLY with --yes.

Usage:
  export ADAPTION_API_KEY=pt_live_...
  python adaption_finetune.py --check-models          # list supported base models
  python adaption_finetune.py --dry-run               # validate file + plan, no API calls
  python adaption_finetune.py --upload-only           # push dataset, print dataset_id
  python adaption_finetune.py --yes                    # push + LAUNCH the fine-tune
  python adaption_finetune.py --yes --dataset-id DS..  # launch on an already-uploaded dataset
"""
from __future__ import annotations
import argparse, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

BASE = os.environ.get("ADAPTION_BASE_URL", "https://api.prod.adaptionlabs.ai").rstrip("/")
MODEL = os.environ.get("ADAPTION_MODEL_ID", "Qwen/Qwen3.5-4B")
TRAINING_METHOD = "instruction"            # SFT
COLUMN_MAPPING = {"prompt": "prompt", "completion": "completion"}
DEFAULT_FILE = Path(__file__).resolve().parent / "sft_train_plus_val.csv"
DATASET_NAME = "egfr_mutationscientist_sft_train_plus_val"


def _key() -> str:
    k = os.environ.get("ADAPTION_API_KEY")
    if not k:
        sys.exit("ERROR: ADAPTION_API_KEY is not set. Create one in Adaption → Settings → "
                 "API keys, then `export ADAPTION_API_KEY=pt_live_...` and re-run.")
    return k


def _req(method: str, url: str, body=None, headers=None, raw: bytes | None = None, timeout=120):
    h = {"Authorization": f"Bearer {_key()}"}
    if headers:
        h.update(headers)
    h = {k: v for k, v in h.items() if v != ""}  # drop blanked headers (presigned S3 PUT)
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    if body is not None and raw is None:
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt.strip().startswith(("{", "[")) else txt)
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:1000]
        sys.exit(f"HTTP {e.code} on {method} {url}\n{detail}")
    except urllib.error.URLError as e:
        sys.exit(f"Network error on {method} {url}: {e}")


def check_models():
    _, out = _req("GET", f"{BASE}/api/v1/autoscientist/models")
    print(json.dumps(out, indent=2))


def validate_file(path: Path):
    import csv
    if not path.exists():
        sys.exit(f"ERROR: {path} not found. Build it first (sft_train + sft_validation).")
    rows = list(csv.DictReader(path.open()))
    empty = sum(1 for r in rows if not r.get("prompt", "").strip() or not r.get("completion", "").strip())
    print(f"file         : {path}")
    print(f"rows         : {len(rows)}  (SFT floor = 1000 -> {'OK' if len(rows) >= 1000 else 'BELOW FLOOR'})")
    print(f"empty p/c    : {empty}  ({'OK' if empty == 0 else 'PROBLEM'})")
    print(f"columns      : {list(rows[0].keys()) if rows else '[]'}")
    if len(rows) < 1000 or empty:
        sys.exit("ERROR: dataset does not meet requirements.")
    return len(rows)


def upload_dataset(path: Path) -> str:
    """RAW processing: train on our already-prepared prompt/completion rows as-is
    (no adaptation/augmentation, so our grounded completions are not rewritten)."""
    size = path.stat().st_size
    print("1/2 create dataset (processing_mode=raw) …")
    _, cr = _req("POST", f"{BASE}/api/v1/datasets", body={"source": {
        "name": DATASET_NAME, "file_format": "csv",
        "processing_mode": "raw", "column_mapping": COLUMN_MAPPING}})
    dataset_id = cr.get("dataset_id") or cr.get("id")
    up = cr.get("upload_instructions") or {}
    upload_url = up.get("url") or cr.get("upload_url")
    if not (dataset_id and upload_url):
        sys.exit(f"create returned no id/upload url: {json.dumps(cr)[:500]}")
    print(f"    dataset_id={dataset_id}  status={cr.get('status')}  ({size} bytes)")

    import re
    s3_key = up.get("s3_key") or re.search(r"amazonaws\.com/(.+?\.csv)\?", upload_url).group(1)

    print("2/3 PUT file to presigned URL …")
    _req("PUT", upload_url, raw=path.read_bytes(),
         headers={"Content-Type": "text/csv", "Authorization": ""})  # presigned: no bearer

    print("3/3 finalize upload (triggers processing) …")
    _req("POST", f"{BASE}/api/v1/datasets/{dataset_id}/upload/complete",
         body={"s3_key": s3_key, "file_size_bytes": size})
    print("    uploaded + finalized.")
    return dataset_id


def wait_dataset_ready(dataset_id: str, interval=10, max_wait=900) -> dict:
    print(f"waiting for dataset {dataset_id} to become trainable …")
    waited = 0
    while True:
        _, d = _req("GET", f"{BASE}/api/v1/datasets/{dataset_id}/status")
        st = d.get("status")
        print(f"    status={st}  row_count={d.get('row_count')}")
        if st in ("ready", "succeeded", "awaiting_input", "complete", "completed") and d.get("row_count"):
            return d
        if st in ("failed", "error", "preprocessing_failed"):
            sys.exit(f"dataset processing failed: {json.dumps(d)[:500]}")
        waited += interval
        if waited >= max_wait:
            print("    (timeout; check the dashboard)")
            return d
        time.sleep(interval)


def launch_run(dataset_id: str, model: str, retries: int = 6) -> dict:
    print(f"launching AutoScientist SFT run  model={model}  dataset={dataset_id} …")
    # NOTE: for raw-processed datasets the column mapping is baked in at create
    # time; re-sending column_mapping here is REJECTED ("columns not in dataset").
    body = {"dataset_id": dataset_id, "model": model, "training_method": TRAINING_METHOD}
    url = f"{BASE}/api/v1/autoscientist"
    for attempt in range(retries):
        h = {"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"}
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=h, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                run = json.loads(r.read().decode())
            print(json.dumps(run, indent=2))
            return run
        except urllib.error.HTTPError as e:
            detail = e.read().decode()
            if e.code == 422 and "NOT_PREPARED" in detail and attempt < retries - 1:
                print(f"    not prepared yet, retrying in 15s ({attempt+1}/{retries}) …")
                time.sleep(15)
                continue
            sys.exit(f"HTTP {e.code} launching run:\n{detail[:800]}")
    sys.exit("run launch kept returning NOT_PREPARED")


def poll(experiment_id: str, interval=30, limit=0):
    print(f"polling run {experiment_id} (Ctrl-C to stop; the run keeps going) …")
    n = 0
    while True:
        _, r = _req("GET", f"{BASE}/api/v1/autoscientist/{experiment_id}")
        st = r.get("status")
        print(f"  [{time.strftime('%H:%M:%S')}] status={st}")
        if st in ("succeeded", "failed", "cancelled"):
            print(json.dumps(r, indent=2))
            return
        n += 1
        if limit and n >= limit:
            return
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=DEFAULT_FILE)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--check-models", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="validate file + print plan, no API calls")
    ap.add_argument("--upload-only", action="store_true", help="upload dataset, print dataset_id, stop")
    ap.add_argument("--dataset-id", help="skip upload; launch on this existing dataset_id")
    ap.add_argument("--yes", action="store_true", help="CONFIRM launching the paid fine-tune")
    ap.add_argument("--poll", action="store_true")
    args = ap.parse_args()

    if args.check_models:
        check_models(); return

    n = validate_file(args.file)
    print(f"\nplan: upload {args.file.name} ({n} rows) -> SFT {args.model} "
          f"(method={TRAINING_METHOD}, map={COLUMN_MAPPING})\n")
    if args.dry_run:
        print("dry-run: no API calls made."); return

    dataset_id = args.dataset_id or upload_dataset(args.file)
    wait_dataset_ready(dataset_id)
    if args.upload_only:
        print(f"\nUPLOADED + READY. dataset_id={dataset_id}\n"
              f"Launch with: python {Path(__file__).name} --yes --dataset-id {dataset_id}")
        return

    if not args.yes:
        sys.exit("\nDataset path ready. Launching a fine-tune is a PAID job — re-run with --yes "
                 "to start it (optionally add --dataset-id to reuse an upload).")

    run = launch_run(dataset_id, args.model)
    eid = run.get("id") or run.get("experiment_id")
    if eid and args.poll:
        poll(eid)
    elif eid:
        print(f"\nrun started: {eid}\nCheck: python {Path(__file__).name} --poll  (or GET /api/v1/autoscientist/{eid})")


if __name__ == "__main__":
    main()
