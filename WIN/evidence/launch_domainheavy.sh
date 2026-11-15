#!/bin/bash
source ~/Desktop/EGFR_TRAINING/.adaption_key
BASE="https://api.prod.adaptionlabs.ai"; H="Authorization: Bearer $ADAPTION_API_KEY"
DS="1bf15478-4286-4eaf-b139-8c2c772f57be"; EV=~/Desktop/WIN/evidence; LOG=$EV/domainheavy.log
echo "$(date +%H:%M:%S) waiting for domain-heavy $DS" >> $LOG
for i in $(seq 1 240); do
  d=$(curl -s -H "$H" "$BASE/api/v1/datasets/$DS/status")
  st=$(echo "$d" | python3 -c "import sys,json;print(json.load(sys.stdin).get('status'))" 2>/dev/null)
  rc=$(echo "$d" | python3 -c "import sys,json;print(json.load(sys.stdin).get('row_count'))" 2>/dev/null)
  echo "$(date +%H:%M:%S) ds=$st rows=$rc" >> $LOG
  if [ "$st" = "succeeded" ] || [ "$st" = "ready" ] || [ "$st" = "completed" ] || [ "$st" = "complete" ]; then break; fi
  if [ "$st" = "failed" ] || [ "$st" = "error" ]; then echo "FAILED $d" >> $LOG; exit 1; fi
  sleep 30
done
for attempt in $(seq 1 10); do
  resp=$(curl -s -X POST -H "$H" -H "Content-Type: application/json" -d "{\"dataset_id\":\"$DS\",\"model\":\"Qwen/Qwen3-4B-Base\",\"training_method\":\"instruction\",\"max_iterations\":5,\"target_win_rate\":0.9,\"idempotency_key\":\"egfr-dh-4bbase\"}" "$BASE/api/v1/autoscientist")
  id=$(echo "$resp" | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
  if [ -n "$id" ]; then echo "$(date +%H:%M:%S) LAUNCHED dh-4Bbase -> $id" >> $LOG; echo "$resp" > $EV/exp_dh4Bbase_launch.json; echo "DH_LAUNCHED $id"; exit 0; fi
  echo "$(date +%H:%M:%S) retry $attempt: $resp" >> $LOG; sleep 20
done
echo "DH_FAILED"; exit 1
