"""C. Molecular Screening — Boltz predictions, WT-vs-mutant, inhibitor rankings.
Experimental measurements and model predictions are never shown as the same thing."""
from __future__ import annotations
import streamlit as st
from components import ui
from visualisations import charts


def render(ctx):
    data, boltz = ctx.data, ctx.boltz
    st.header("🔬 Molecular Screening")
    st.markdown(f"Prediction source: {ui.badge('mock') if not boltz.real_mode else ui.badge('pretrained')}",
                unsafe_allow_html=True)
    if not boltz.real_mode:
        ui.mock_banner("Boltz predictions")
    st.caption(ctx.score_definition)

    tab_rank, tab_cmp, tab_pair = st.tabs(
        ["Inhibitor ranking (per mutation)", "WT vs mutant (per inhibitor)", "Single pair"])

    muts_with_cx = data.mutations_with_complexes()

    with tab_rank:
        if not muts_with_cx:
            st.info("No complexes available.")
        else:
            mid = st.selectbox("Mutation", muts_with_cx, key="rank_mut")
            ranking = boltz.ranking_for(mid)
            charts.ranking_table(ranking, data.compound_display_name)

    with tab_cmp:
        # compounds that appear in >1 variant make the nicest comparison
        cmp_ids = sorted({cx.compound_id for cx in data.boltz})
        cid = st.selectbox("Inhibitor", cmp_ids,
                           format_func=data.compound_display_name, key="cmp_cmp")
        compare = boltz.compare_wt_mutant(cid)
        charts.wt_vs_mutant_bar(compare, data.compound_display_name)
        if not compare["wt"]:
            st.info("No WT complex for this inhibitor in the dataset (nothing fabricated).")

    with tab_pair:
        c1, c2 = st.columns(2)
        mid = c1.selectbox("Mutation", muts_with_cx or ["(none)"], key="pair_mut")
        cids = data.compounds_tested_against(mid) if muts_with_cx else []
        cid = c2.selectbox("Inhibitor", cids or ["(none)"],
                           format_func=data.compound_display_name, key="pair_cmp")
        if cids:
            preds = boltz.predictions_for(mutation_id=mid, compound_id=cid)
            meas = data.measurements_for(mutation_id=mid, compound_id=cid)

            st.subheader("Model prediction(s)")
            if preds:
                for p in preds:
                    ui.badges(ui.pred_source(p))
                    ui.kv(p, ["complex_id", "model_checkpoint", "affinity_pred_value",
                              "affinity_probability_binary", "structure_path"])
            else:
                st.info("No Boltz complex for this exact pair.")

            st.subheader("Experimental measurement(s) — distinct from predictions")
            if meas:
                import pandas as pd
                st.dataframe(pd.DataFrame([{
                    "type": m.get("measurement_type"), "value": m.get("original_value"),
                    "unit": m.get("original_unit"), "rel": m.get("measurement_relation"),
                    "boltz_target": m.get("boltz_target_value"), "assay": m.get("assay_type"),
                    "source": m.get("publication") or m.get("source_database"),
                } for m in meas]), width="stretch", hide_index=True)
            else:
                st.info("No curated measurement for this exact pair.")
        else:
            st.info("Pick a mutation that has complexes.")
