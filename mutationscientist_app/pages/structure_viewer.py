"""D. Molecular Structure Viewer — real RCSB PDB entries for EGFR (P00533),
rendered in-browser with 3Dmol.js (no Python structure package needed).

Structures are EXPERIMENTAL (RCSB). Any predicted structure (Person 2) would be
shown separately and labelled as computational — none are fabricated here."""
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components
from components import ui

VIEWER = """
<div id="v" style="height:520px;width:100%;position:relative;border-radius:8px;"></div>
<script src="https://3Dmol.org/build/3Dmol-min.js"></script>
<script>
  let v = $3Dmol.createViewer("v", {backgroundColor: "0x0e1117"});
  $3Dmol.download("pdb:%PDB%", v, {}, function () {
    v.setStyle({}, {cartoon: {color: "spectrum"}});
    v.addStyle({hetflag: true}, {stick: {radius: 0.2}});
    v.zoomTo();
    v.render();
  });
</script>
"""


def render(ctx):
    data = ctx.data
    st.header("🧩 Molecular Structure Viewer")
    ui.badges("experimental")
    st.caption("Experimental structures from RCSB PDB for EGFR (UniProt P00533). "
               "The index is EGFR-wide and not reliably mutation-tagged, so entries are "
               "not auto-mapped to a specific variant — pick one and verify in its title.")

    structs = data.structures_for()
    if not structs:
        st.info("No structure index found.")
        return

    import pandas as pd
    df = pd.DataFrame([{
        "pdb_id": s.get("pdb_id"), "method": s.get("method"),
        "resolution_A": s.get("resolution_A"), "ligands": s.get("bound_ligands"),
        "title": (s.get("title") or "")[:90],
    } for s in structs])
    st.dataframe(df, width="stretch", hide_index=True, height=240)

    pdb = st.selectbox("View structure", [s["pdb_id"] for s in structs])
    chosen = next((s for s in structs if s["pdb_id"] == pdb), None)
    if chosen:
        st.markdown(f"**{pdb}** — {chosen.get('title','')}  \n"
                    f"_{chosen.get('method')} · {chosen.get('resolution_A')} Å · "
                    f"ligands: {chosen.get('bound_ligands') or 'none listed'}_  \n"
                    f"[Open on RCSB]({chosen.get('source_url','')})")
        components.html(VIEWER.replace("%PDB%", pdb), height=540)
        st.caption("Cartoon = protein (spectrum N→C); sticks = bound heteroatoms/ligand. "
                   "Rendered live from RCSB via 3Dmol.js.")
