"""B. Inhibitor Explorer — browse the curated EGFR inhibitor panel."""
from __future__ import annotations
import streamlit as st
from components import ui


def render(ctx):
    data = ctx.data
    st.header("💊 Inhibitor Explorer")
    st.caption("Curated, annotated EGFR inhibitor panel. (BindingDB also contributes "
               f"{data.status()['n_bindingdb_ligands']:,} minimal ligand records used for Boltz volume.)")

    comps = data.list_compounds()
    q = st.text_input("Search by name / synonym / id").strip().lower()
    if q:
        comps = [c for c in comps if q in (c.get("compound_name", "") + c.get("synonyms", "")
                 + c.get("compound_id", "")).lower()]

    cov_filter = st.radio("Covalent status", ["all", "covalent", "non-covalent"], horizontal=True)
    if cov_filter != "all":
        want = "coval" if cov_filter == "covalent" else None
        comps = [c for c in comps if (("coval" in (c.get("covalent_status", "").lower())) == (want == "coval"))]

    if not comps:
        st.info("No inhibitors match.")
        return

    choice = st.selectbox("Inhibitor", [c["compound_id"] for c in comps],
                          format_func=lambda cid: data.compound_display_name(cid))
    c = data.get_compound(choice)

    is_cov = "coval" in (c.get("covalent_status", "").lower())
    ui.badges("experimental")

    col1, col2 = st.columns(2)
    with col1:
        ui.kv(c, ["compound_id", "compound_name", "drug_class", "inhibitor_generation",
                  "binding_mechanism", "covalent_status", "warhead_type"])
    with col2:
        ui.kv(c, ["molecular_formula", "molecular_weight", "pubchem_cid", "chembl_id",
                  "inchikey", "development_status"])

    if is_cov:
        st.warning("**Covalent inhibitor** (e.g. acrylamide → Cys797). Time-dependent "
                   "inhibition is not fully captured by equilibrium affinity — these are "
                   "excluded from the Boltz regression *target* and handled on the reasoning side.")

    smi = c.get("isomeric_smiles") or c.get("canonical_smiles")
    if smi:
        st.subheader("SMILES")
        st.code(smi, language="text")

    if c.get("known_resistance_context"):
        st.subheader("Known resistance context")
        st.write(c["known_resistance_context"])

    # experimental measurements available
    meas = data.measurements_for(compound_id=choice)
    st.subheader(f"Experimental measurements available ({len(meas)})")
    if meas:
        import pandas as pd
        df = pd.DataFrame([{
            "mutation": m.get("mutation_id"), "type": m.get("measurement_type"),
            "value": m.get("original_value"), "unit": m.get("original_unit"),
            "rel": m.get("measurement_relation"), "assay": m.get("assay_type"),
            "source": m.get("publication") or m.get("source_database"),
        } for m in meas[:200]])
        st.dataframe(df, width="stretch", hide_index=True)
        if len(meas) > 200:
            st.caption(f"Showing first 200 of {len(meas)}.")
    else:
        st.info("No curated measurements for this inhibitor.")
