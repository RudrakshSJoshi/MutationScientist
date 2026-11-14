#!/usr/bin/env python3
"""Poll the AutoScientist run until it ends; auto-download the model on success."""
import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

BASE = "https://api.prod.adaptionlabs.ai"
K = os.environ["ADAPTION_API_KEY"]
RUN = os.environ.get("RUN_ID", "1cc9e20f-4cdb-45cb-9491-7e7ac4bdd8f4")
OUT = Path(__file__).resolve().parent / "best_model.zip"
INTERVAL = 180          # 3 min
MAX_POLLS = 80          # ~4 hours safety cap

def get(p):
    r = urllib.request.Request(BASE + p, headers={"Authorization": "Bearer " + K})
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode())

def download():
    r = urllib.request.Request(BASE + f"/api/v1/autoscientist/{RUN}/download",
                               headers={"Authorization": "Bearer " + K})
    with urllib.request.urlopen(r, timeout=300) as resp:
        data = resp.read()
    OUT.write_bytes(data)
    return len(data)

print(f"[monitor] watching run {RUN}", flush=True)
for i in range(MAX_POLLS):
    try:
        r = get(f"/api/v1/autoscientist/{RUN}")
    except Exception as e:
        print(f"[monitor] poll error: {e}", flush=True); time.sleep(INTERVAL); continue
    st = r.get("status")
    print(f"[monitor] {time.strftime('%H:%M:%S')} status={st} "
          f"iters={r.get('iterations_completed')}/{r.get('max_iterations')} "
          f"best_win_rate={r.get('best_win_rate')}", flush=True)
    if st in ("succeeded", "failed", "cancelled"):
        print(f"[monitor] FINAL status={st}", flush=True)
        if st == "succeeded" and r.get("download_available"):
            try:
                n = download()
                print(f"[monitor] downloaded model -> {OUT} ({n} bytes)", flush=True)
            except Exception as e:
                print(f"[monitor] download failed: {e} (fetch manually from the run's /download)", flush=True)
        print(json.dumps(r, indent=2), flush=True)
        sys.exit(0)
    time.sleep(INTERVAL)
print("[monitor] still running after cap; check the dashboard.", flush=True)
