#!/bin/bash
source ~/Desktop/EGFR_TRAINING/.adaption_key
BASE="https://api.prod.adaptionlabs.ai"; H="Authorization: Bearer $ADAPTION_API_KEY"
for i in $(seq 1 180); do  # ~6h at 120s
  snap=$(curl -s -H "$H" "$BASE/api/v1/autoscientist")
  hit=$(echo "$snap" | python3 -c "
import sys,json
rs=json.load(sys.stdin)['runs']
for r in rs:
    if r['id'].startswith('1cc9e20f'): continue
    if r.get('best_win_rate') is not None or r.get('status')=='succeeded':
        print(r['id'][:8],r['model'],r.get('status'),r.get('best_win_rate')); break
")
  if [ -n "$hit" ]; then echo "FIRST_RESULT $hit"; exit 0; fi
  sleep 120
done
echo "FIRST_RESULT_TIMEOUT"
