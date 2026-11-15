#!/usr/bin/env python3
"""Tool-free structural analysis of the predicted Boltz complexes (no PyMOL needed).

For each predicted .cif: parse coordinates, find protein residues whose any atom is
within 5 Å of any ligand atom (the binding pocket), and flag whether the mutated
residue(s) for that variant contact the ligand. Writes:
  molecular_analysis/structural_analysis/contacts.csv
  molecular_analysis/structural_analysis/structural_findings.md
  molecular_analysis/structural_analysis/pdb_files/        (hero .cif copies)
  molecular_analysis/structural_analysis/visualisations/   (3Dmol.js HTML per hero)
Distinguishes PREDICTED (computational) structures from experimental — these are ALL predicted.
"""
import json, csv, re, pathlib, shutil
import numpy as np

OUT = pathlib.Path.home() / "Desktop/EGFR_TRAINING"
SA = OUT / "molecular_analysis/structural_analysis"
(SA/"pdb_files").mkdir(parents=True, exist_ok=True)
(SA/"visualisations").mkdir(parents=True, exist_ok=True)
AA3 = {"ALA","ARG","ASN","ASP","CYS","GLN","GLU","GLY","HIS","ILE","LEU","LYS",
       "MET","PHE","PRO","SER","THR","TRP","TYR","VAL","MSE","SEC","PYL"}
CUTOFF = 5.0

def parse_cif_atoms(path):
    """Return list of dicts: comp, seq, asym, elem, xyz. Minimal _atom_site loop parser."""
    lines = pathlib.Path(path).read_text().splitlines()
    i = 0; atoms = []
    while i < len(lines):
        if lines[i].strip() == "loop_":
            cols = []; j = i+1
            while j < len(lines) and lines[j].strip().startswith("_atom_site."):
                cols.append(lines[j].strip()); j += 1
            if cols:
                idx = {c: k for k, c in enumerate(cols)}
                def gi(name):
                    for key in idx:
                        if key.endswith("."+name): return idx[key]
                    return None
                ci={n:gi(n) for n in ("group_PDB","label_comp_id","label_seq_id","label_asym_id",
                                      "type_symbol","Cartn_x","Cartn_y","Cartn_z","auth_seq_id")}
                k = j
                while k < len(lines):
                    s = lines[k].strip()
                    if s.startswith("_") or s == "loop_" or s.startswith("#") or s=="":
                        break
                    parts = s.split()
                    if len(parts) < len(cols): break
                    try:
                        atoms.append({
                            "comp": parts[ci["label_comp_id"]],
                            "seq": parts[ci["auth_seq_id"]] if ci["auth_seq_id"] is not None else parts[ci["label_seq_id"]],
                            "asym": parts[ci["label_asym_id"]],
                            "xyz": (float(parts[ci["Cartn_x"]]),float(parts[ci["Cartn_y"]]),float(parts[ci["Cartn_z"]])),
                        })
                    except (ValueError,TypeError,KeyError): pass
                    k += 1
                i = k; continue
        i += 1
    return atoms

def mutation_positions(mutation_id):
    pos=set()
    for tok in mutation_id.replace("EGFR_","").split("_"):
        m=re.match(r"[A-Za-z](\d+)[A-Za-z]",tok)      # e.g. L858R, T790M, C797S
        if m: pos.add(int(m.group(1)))
        if tok.startswith("ex19del"): pos.update(range(746,751))  # E746-A750
    return pos

def main():
    preds=json.loads((OUT/"boltz_predictions.json").read_text())
    rows=[]; findings=[]
    heroes={"COMPLEX_001557","COMPLEX_000889","COMPLEX_002230","COMPLEX_003136"}  # BLU-945 ladder heroes
    for p in preds:
        sp=p.get("structure_path")
        if not sp or not pathlib.Path(sp).exists(): continue
        atoms=parse_cif_atoms(sp)
        lig=[a for a in atoms if a["comp"] not in AA3]
        prot=[a for a in atoms if a["comp"] in AA3]
        if not lig or not prot: continue
        L=np.array([a["xyz"] for a in lig])
        # min dist per protein residue
        from collections import defaultdict
        resatoms=defaultdict(list)
        for a in prot: resatoms[(a["seq"],a["comp"])].append(a["xyz"])
        pocket=[]
        for (seq,comp),xyz in resatoms.items():
            P=np.array(xyz)
            d=np.sqrt(((P[:,None,:]-L[None,:,:])**2).sum(-1)).min()
            if d<=CUTOFF: pocket.append((int(seq) if str(seq).lstrip('-').isdigit() else seq,comp,round(float(d),2)))
        pocket.sort(key=lambda x:x[2])
        mpos=mutation_positions(p["mutation_id"])
        pocket_pos={q[0] for q in pocket if isinstance(q[0],int)}
        mut_contacts=sorted(mpos & pocket_pos)
        rows.append({"complex_id":p["complex_id"],"compound_id":p["compound_id"],
                     "mutation_id":p["mutation_id"],"n_pocket_residues":len(pocket),
                     "mutated_residue_in_pocket":bool(mut_contacts),
                     "mut_contact_positions":";".join(map(str,mut_contacts)),
                     "top_pocket":";".join(f"{c}{s}({d}A)" for s,c,d in pocket[:8])})
        if p["complex_id"] in heroes or len(findings)<6:
            findings.append((p,pocket[:10],mut_contacts))
        if p["complex_id"] in heroes:
            shutil.copy(sp, SA/"pdb_files"/f"{p['complex_id']}.cif")
            write_viewer(p, SA/"visualisations"/f"{p['complex_id']}.html", mpos)

    with open(SA/"contacts.csv","w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["complex_id","compound_id","mutation_id","n_pocket_residues",
                                       "mutated_residue_in_pocket","mut_contact_positions","top_pocket"])
        w.writeheader(); [w.writerow(r) for r in rows]

    # findings md
    L2=["# Structural findings (PREDICTED complexes — Boltz-2, not experimental)\n",
        f"All structures here are **computational predictions**, not experimentally determined. "
        f"Pocket = protein residues with any atom within {CUTOFF} Å of any ligand atom.\n",
        f"\nAnalysed {len(rows)} predicted complexes. "
        f"Mutated residue in the binding pocket in {sum(r['mutated_residue_in_pocket'] for r in rows)}/{len(rows)}.\n"]
    for p,pocket,mut in findings:
        L2.append(f"\n## {p['complex_id']} — {p['compound_id'].replace('CMP_','')} × {p['mutation_id'].replace('EGFR_','')}")
        L2.append(f"- Predicted affinity: {p['affinity_pred_value']:.3f} log₁₀(IC50 µM); P(binder)={p['affinity_probability_binary']:.2f}")
        L2.append(f"- Mutated residue(s) contacting ligand: {', '.join(map(str,mut)) if mut else 'none within 5 Å'}")
        L2.append(f"- Top pocket residues: {', '.join(f'{c}{s} ({d} Å)' for s,c,d in pocket)}")
    (SA/"structural_findings.md").write_text("\n".join(L2))
    print(f"structural_analysis: {len(rows)} complexes, {sum(r['mutated_residue_in_pocket'] for r in rows)} with mutation in pocket")

def write_viewer(p, outpath, mpos):
    cif=pathlib.Path(p["structure_path"]).read_text().replace("`","'")
    sel=",".join(str(x) for x in sorted(mpos))
    html=f"""<!doctype html><html><head><meta charset="utf-8"><title>{p['complex_id']}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js"></script>
<style>body{{margin:0;font-family:system-ui}}#v{{width:100vw;height:88vh;position:relative}}
#c{{padding:8px 12px;font-size:13px}}</style></head><body>
<div id="c"><b>{p['complex_id']}</b> — {p['compound_id'].replace('CMP_','')} × {p['mutation_id'].replace('EGFR_','')} ·
PREDICTED (Boltz-2) · affinity {p['affinity_pred_value']:.2f} log10(IC50 µM) · mutated residues highlighted magenta</div>
<div id="v"></div>
<script>
const cif=`{cif}`;
const V=$3Dmol.createViewer("v",{{backgroundColor:"white"}});
V.addModel(cif,"cif");
V.setStyle({{}},{{cartoon:{{color:"spectrum"}}}});
V.setStyle({{hetflag:true}},{{stick:{{colorscheme:"greenCarbon"}}}});
[{sel}].forEach(r=>V.setStyle({{resi:r}},{{cartoon:{{color:"magenta"}},stick:{{color:"magenta"}}}}));
V.zoomTo({{hetflag:true}});V.zoom(0.6);V.render();
</script></body></html>"""
    outpath.write_text(html)

if __name__=="__main__": main()
