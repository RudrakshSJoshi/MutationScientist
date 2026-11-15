#!/bin/bash
source ~/Desktop/EGFR_TRAINING/.adaption_key 2>/dev/null
RUN="3412f28a-4fd9-44f5-b92a-1d471af16e69"
WIN=0.7378  # current champion to beat
for _ in $(seq 1 120); do
  r=$(curl -sS -H "Authorization: Bearer $ADAPTION_API_KEY" "https://api.prod.adaptionlabs.ai/api/v1/autoscientist/$RUN")
  st=$(echo "$r" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['status'],d.get('iterations_completed'),d.get('best_win_rate'))" 2>/dev/null)
  echo "$(date +%H:%M:%S) $st"
  set -- $st
  if [ "$1" = "succeeded" ] || [ "$1" = "failed" ] || [ "$1" = "cancelled" ]; then
    echo "GEMMA_DONE status=$1 best_win_rate=$3 (champion=$WIN)"
    echo "$r" > ~/Desktop/WIN/evidence/gemma_final.json
    break
  fi
  sleep 180
done
