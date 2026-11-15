#!/usr/bin/env python3
"""Build a prioritized, chunked queue of Boltz complex YAMLs for the overnight run.

Priority:
  1. JBJ-09-063 curated-panel complexes (trustworthy curated labels; BLU-945's 8
     are already done in results/, so excluded here).
  2. Stratified BindingDB-labeled complexes: per variant, pick complexes evenly
     spaced across the experimental affinity_label range (so validation spans a
     real dynamic range, and per-mutation rankings have several inhibitors).

Writes sanitized YAMLs (absolute MSA paths, training-label `value` left intact —
boltz ignores it for inference) into queue/chunkNN/ dirs of CHUNK complexes each.
"""
import sys, re, pathlib, csv
HOME = pathlib.Path.home()
sys.path.insert(0, str(HOME / "Desktop"))
from egfr_dataset_loader import EGFRDataset

DS = HOME / "Desktop/EGFR_RESEARCH_DATASET"
MSADIR = (DS / "boltz2/msa").resolve()
QROOT = HOME / "Desktop/EGFR_TRAINING/boltz_run/queue"
ALREADY = {"COMPLEX_000889","COMPLEX_001557","COMPLEX_002230","COMPLEX_003136",
           "COMPLEX_005937","COMPLEX_006596","COMPLEX_006685","COMPLEX_006843"}  # BLU-945 ladder
PER_VARIANT = int(sys.argv[1]) if len(sys.argv) > 1 else 4
CHUNK = 12

ds = EGFRDataset(str(DS))
allcx = [c for sp in ("train","validation","test") for c in ds.boltz.split(sp)]
by_id = {c.complex_id: c for c in allcx}

# source yaml path for a complex id (canonical, not the " 2.yaml" dupes)
def src_yaml(cid):
    for sp in ("train","validation","test"):
        p = DS / "boltz2/complexes" / sp / f"{cid}.yaml"
        if p.exists():
            return p
    return None

ordered = []
# 1) JBJ-09-063
jbj = [c for c in allcx if c.compound_id == "CMP_JBJ09063" and c.complex_id not in ALREADY]
ordered += sorted(jbj, key=lambda c: c.complex_id)

# 2) stratified BindingDB sample per variant (exclude curated-panel compounds &
#    already-done); evenly spaced across affinity_label
from collections import defaultdict
byvar = defaultdict(list)
curated = {"CMP_BLU945","CMP_JBJ09063"}
for c in allcx:
    if c.complex_id in ALREADY: continue
    if c.compound_id in curated: continue
    if c.affinity_label is None: continue
    byvar[c.mutation_id].append(c)
for var, cs in byvar.items():
    cs = sorted(cs, key=lambda c: c.affinity_label)
    if not cs: continue
    n = min(PER_VARIANT, len(cs))
    # evenly spaced indices across the sorted-by-affinity list
    idxs = [round(i*(len(cs)-1)/(n-1)) for i in range(n)] if n > 1 else [0]
    for i in sorted(set(idxs)):
        ordered.append(cs[i])

# de-dup preserve order
seen=set(); queue=[]
for c in ordered:
    if c.complex_id in seen: continue
    seen.add(c.complex_id); queue.append(c)

# write chunks
import shutil
if QROOT.exists(): shutil.rmtree(QROOT)
QROOT.mkdir(parents=True)
manifest = []
for i, c in enumerate(queue):
    ch = QROOT / f"chunk{i//CHUNK:02d}"
    ch.mkdir(exist_ok=True)
    sp = src_yaml(c.complex_id)
    if sp is None:
        print("WARN no yaml for", c.complex_id); continue
    txt = sp.read_text()
    txt = re.sub(r"msa:\s*([^\n]+)",
                 lambda m: f"msa: {MSADIR/pathlib.Path(m.group(1).strip().strip(chr(39)+chr(34))).name}",
                 txt)
    (ch / f"{c.complex_id}.yaml").write_text(txt)
    manifest.append((c.complex_id, c.mutation_id, c.compound_id, c.affinity_label, f"chunk{i//CHUNK:02d}"))

with open(QROOT / "queue_manifest.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["complex_id","mutation_id","compound_id","affinity_label","chunk"])
    w.writerows(manifest)

nchunks = (len(queue)+CHUNK-1)//CHUNK
print(f"queued {len(queue)} complexes in {nchunks} chunks of {CHUNK}")
print(f"  JBJ-09-063: {len(jbj)}   stratified BindingDB: {len(queue)-len(jbj)}")
print(f"  variants covered: {len(byvar)}")
print(f"manifest: {QROOT/'queue_manifest.csv'}")
