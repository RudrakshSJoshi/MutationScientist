#!/bin/bash
# Launches the augmented-dataset training fleet once ecaebd69 is ready.
# Reuses the single ~190-credit augmentation across all models (no duplicate aug spend).
source ~/Desktop/EGFR_TRAINING/.adaption_key
BASE="https://api.prod.adaptionlabs.ai"; H="Authorization: Bearer $ADAPTION_API_KEY"
DS="ecaebd69-9fca-4c70-a67d-95127d5e157d"; EV=~/Desktop/WIN/evidence
echo "$(date +%H:%M:%S) waiting for augmented dataset $DS ..." >> $EV/fleet.log

# wait for ready
for i in $(seq 1 240); do
  d=$(curl -s -H "$H" "$BASE/api/v1/datasets/$DS/status")
  st=$(echo "$d" | python3 -c "import sys,json;print(json.load(sys.stdin).get('status'))" 2>/dev/null)
  rc=$(echo "$d" | python3 -c "import sys,json;print(json.load(sys.stdin).get('row_count'))" 2>/dev/null)
  echo "$(date +%H:%M:%S) ds status=$st rows=$rc" >> $EV/fleet.log
  if [ "$st" = "succeeded" ] || [ "$st" = "ready" ] || [ "$st" = "completed" ] || [ "$st" = "complete" ]; then break; fi
  if [ "$st" = "failed" ] || [ "$st" = "error" ]; then echo "DS FAILED $d" >> $EV/fleet.log; exit 1; fi
  sleep 30
done

launch () {
  local MODEL="$1"; local KEY="$2"; local TAG="$3"
  # try without column_mapping (augmented-from-raw bakes it in); retry on NOT_PREPARED
  for attempt in $(seq 1 8); do
    resp=$(curl -s -X POST -H "$H" -H "Content-Type: application/json" -d "{\"dataset_id\":\"$DS\",\"model\":\"$MODEL\",\"training_method\":\"instruction\",\"max_iterations\":5,\"target_win_rate\":0.9,\"idempotency_key\":\"$KEY\"}" "$BASE/api/v1/autoscientist")
    id=$(echo "$resp" | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
    if [ -n "$id" ]; then
      echo "$(date +%H:%M:%S) LAUNCHED $TAG ($MODEL) -> $id" >> $EV/fleet.log
      echo "$resp" > $EV/exp_${TAG}_launch.json
      return 0
    fi
    echo "$(date +%H:%M:%S) $TAG launch retry $attempt: $resp" >> $EV/fleet.log
    sleep 15
  done
  echo "$(date +%H:%M:%S) $TAG FAILED to launch" >> $EV/fleet.log
}

launch "Qwen/Qwen3-4B-Base"  "egfr-4bbase-001" "4Bbase"   # pretrained base -> easy to beat -> win-rate bet
launch "Qwen/Qwen3.5-4B"     "egfr-4bins-001"  "4Bins"    # instruct, demo-quality flagship
launch "Qwen/Qwen3.5-2B"     "egfr-2b-001"     "2B"       # fast, weak base -> win-rate insurance
echo "$(date +%H:%M:%S) fleet launch complete" >> $EV/fleet.log
echo "FLEET_DONE"
