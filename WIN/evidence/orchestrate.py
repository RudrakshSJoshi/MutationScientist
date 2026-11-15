#!/usr/bin/env python3
"""Master training orchestrator for the EGFR Adaption win-rate sweep.

Respects the platform rule: ONE training run per dataset at a time (409 otherwise).
Keeps each dataset busy by chaining jobs; launches the top win-rate bet first.
Logs win-rates as they come in; exits (notifying the session) when all jobs settle.

Never fabricates: every number logged is read straight from GET /autoscientist.
"""
import json, os, time, urllib.request, urllib.error, datetime
from pathlib import Path

BASE = "https://api.prod.adaptionlabs.ai"
K = os.environ["ADAPTION_API_KEY"]
EV = Path.home() / "Desktop/WIN/evidence"
LOG = EV / "orchestrate.log"

RAW   = "8db28bbb-1c2e-418e-889c-b1c465f95935"   # raw 1,126
AUG20 = "ecaebd69-9fca-4c70-a67d-95127d5e157d"   # augmented ~20k (reused across its chain)

# Job queue. Each: model, dataset, optional extra body (train-time aug), tag.
# Priority order matters: first eligible job per free dataset launches first.
AUG_BODY = {"augmentation_domain_rows": 9437, "augmentation_general_rows": 9437}
JOBS = [
    # ecaebd69 chain (reuse the one 20k augmentation — no extra aug credits):
    {"tag": "4Bbase", "model": "Qwen/Qwen3-4B-Base", "ds": AUG20, "extra": {}},        # TOP win-rate bet
    {"tag": "4Bins",  "model": "Qwen/Qwen3.5-4B",    "ds": AUG20, "extra": {}},        # demo quality
    {"tag": "2B",     "model": "Qwen/Qwen3.5-2B",    "ds": AUG20, "extra": {}},        # fast, weak base
    # raw chain (after the running 9B frees 8db28bbb) — one more base bet w/ train-time aug:
    {"tag": "gemmabase", "model": "google/gemma-3-4b-pt", "ds": RAW, "extra": AUG_BODY},
]
for j in JOBS:
    j["run_id"] = None
    j["done"] = False

def req(method, url, body=None, timeout=120):
    h = {"Authorization": f"Bearer {K}"}
    data = json.dumps(body).encode() if body is not None else None
    if body is not None: h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def log(msg):
    line = f"{datetime.datetime.now():%H:%M:%S} {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f: f.write(line + "\n")

def all_runs():
    s, o = req("GET", f"{BASE}/api/v1/autoscientist")
    return json.loads(o).get("runs", []) if s == 200 else []

def ds_ready(ds):
    if ds == RAW: return True
    s, o = req("GET", f"{BASE}/api/v1/datasets/{ds}/status")
    if s != 200: return False
    d = json.loads(o)
    return d.get("status") in ("succeeded", "ready", "completed", "complete") and d.get("row_count")

ACTIVE = ("running", "queued", "pending", "preparing", "in_progress")

def launch(job):
    body = {"dataset_id": job["ds"], "model": job["model"], "training_method": "instruction",
            "max_iterations": 5, "target_win_rate": 0.9,
            "idempotency_key": f"egfr-orch-{job['tag']}"}
    body.update(job["extra"])
    s, o = req("POST", f"{BASE}/api/v1/autoscientist", body=body)
    if s in (200, 201, 202):
        rid = json.loads(o).get("id")
        job["run_id"] = rid
        (EV / f"exp_{job['tag']}_launch.json").write_text(o)
        log(f"LAUNCHED {job['tag']} ({job['model']}) on {job['ds'][:8]} -> {rid}")
        return True
    if s == 409:
        return False  # dataset busy; try later
    log(f"launch {job['tag']} HTTP {s}: {o[:160]}")
    return False

log("=== orchestrator start ===")
for _ in range(600):  # ~10h at 60s
    runs = all_runs()
    by_id = {r["id"]: r for r in runs}
    # datasets currently busy (any active run on them, incl. external 9B/v2)
    busy = {r["dataset_id"] for r in runs if r.get("status") in ACTIVE}

    # update/settle my launched jobs
    for j in JOBS:
        if j["run_id"] and not j["done"]:
            r = by_id.get(j["run_id"])
            if r and r.get("status") in ("succeeded", "failed", "cancelled"):
                j["done"] = True
                log(f"SETTLED {j['tag']} {r.get('status')} best_win_rate={r.get('best_win_rate')}")

    # launch eligible jobs (one per free dataset per pass)
    launched_ds = set()
    for j in JOBS:
        if j["run_id"] or j["done"]:
            continue
        if j["ds"] in busy or j["ds"] in launched_ds:
            continue
        if not ds_ready(j["ds"]):
            continue
        if launch(j):
            launched_ds.add(j["ds"])
            busy.add(j["ds"])

    # periodic status line
    wr = {j["tag"]: (by_id.get(j["run_id"], {}).get("best_win_rate") if j["run_id"] else None) for j in JOBS}
    log("state " + " ".join(f"{j['tag']}={'done' if j['done'] else (j['run_id'][:8] if j['run_id'] else 'queued')}:{wr[j['tag']]}" for j in JOBS))

    if all(j["done"] for j in JOBS):
        log("=== ALL JOBS SETTLED ===")
        (EV / "ORCH_COMPLETE").write_text(datetime.datetime.now().isoformat())
        print("ORCHESTRATION_COMPLETE", flush=True)
        break
    time.sleep(60)
else:
    log("=== orchestrator time cap reached ===")
    print("ORCHESTRATION_CAP", flush=True)
