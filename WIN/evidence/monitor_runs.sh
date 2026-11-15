#!/bin/bash
source ~/Desktop/EGFR_TRAINING/.adaption_key
BASE="https://api.prod.adaptionlabs.ai"; H="Authorization: Bearer $ADAPTION_API_KEY"
EV=~/Desktop/WIN/evidence; LOG=$EV/runs_monitor.log
for i in $(seq 1 200); do  # ~10h at 180s
  snap=$(curl -s -H "$H" "$BASE/api/v1/autoscientist")
  echo "$snap" > $EV/runs_latest.json
  echo "$snap" | python3 - "$i" <<'PY' >> $LOG
import sys,json
poll=sys.argv[1]
import datetime
d=json.load(sys.stdin)
runs=d.get('runs',[])
ts=datetime.datetime.now().strftime('%H:%M:%S')
running=0; total=len(runs)
lines=[]
for r in runs:
    st=r.get('status')
    if st in ('running','queued','pending','preparing'): running+=1
    lines.append(f"  {r['id'][:8]} {r['model'][:22]:22} {st:10} iters={r.get('iterations_completed')}/{r.get('max_iterations')} wr={r.get('best_win_rate')}")
print(f"[{ts}] poll{poll} total={total} running={running}")
print("\n".join(lines))
# signal file for "all settled"
import os
if total>=5 and running==0:
    open(os.path.expanduser('~/Desktop/WIN/evidence/ALL_SETTLED'),'w').write(ts)
PY
  if [ -f $EV/ALL_SETTLED ]; then echo "ALL_SETTLED detected" >> $LOG; echo "ALL_RUNS_SETTLED"; exit 0; fi
  sleep 180
done
echo "MONITOR_CAP_REACHED"
