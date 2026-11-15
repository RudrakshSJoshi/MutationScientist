#!/bin/bash
source ~/Desktop/EGFR_TRAINING/.adaption_key
BASE="https://api.prod.adaptionlabs.ai"; H="Authorization: Bearer $ADAPTION_API_KEY"
EV=~/Desktop/WIN/evidence; LOG=$EV/final_monitor.log
KEY="387caed3 66adad71 4c86594f"   # decisive: 9B-aug, 4B-Base balanced, 4B-Base domain-heavy
for i in $(seq 1 200); do  # ~8h at 150s
  snap=$(curl -s -H "$H" "$BASE/api/v1/autoscientist"); echo "$snap" > $EV/runs_latest.json
  echo "$snap" | python3 - >> $LOG <<'PY'
import sys,json,datetime
d=json.load(sys.stdin); ts=datetime.datetime.now().strftime('%H:%M:%S')
print(f"[{ts}]")
for r in sorted(d['runs'],key=lambda x:x.get('created_at','')):
    print(f"  {r['id'][:8]} {r['model'][:18]:18} {r['status']:9} it{r.get('iterations_completed')}/{r.get('max_iterations')} wr={r.get('best_win_rate')}")
PY
  settled=$(echo "$snap" | python3 -c "
import sys,json
key='387caed3 66adad71 4c86594f'.split()
rs={r['id'][:8]:r for r in json.load(sys.stdin)['runs']}
done=all(rs.get(k,{}).get('status') in ('succeeded','failed','cancelled') for k in key)
print('YES' if done else 'NO')")
  if [ "$settled" = "YES" ]; then echo "KEY_RUNS_SETTLED" >> $LOG; echo "KEY_RUNS_DONE"; exit 0; fi
  sleep 150
done
echo "FINAL_MONITOR_CAP"
