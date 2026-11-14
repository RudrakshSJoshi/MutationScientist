"""Small chart helpers built on Streamlit's native charts (pandas comes with
Streamlit). Charts of predicted values always say lower = stronger."""
from __future__ import annotations
import streamlit as st

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


def wt_vs_mutant_bar(compare: dict, name_fn):
    """compare = {wt:[...], mutant:[...]} of prediction records."""
    recs = (compare.get("wt") or []) + (compare.get("mutant") or [])
    recs = [r for r in recs if r.get("affinity_pred_value") is not None]
    if not recs or pd is None:
        st.info("No predicted values to plot.")
        return
    df = pd.DataFrame([{
        "variant": r["mutation_id"].replace("EGFR_", ""),
        "affinity_pred_value (log10 IC50 µM, lower=stronger)": r["affinity_pred_value"],
    } for r in recs]).set_index("variant")
    st.bar_chart(df)
    st.caption("Lower bar = stronger predicted binding. "
               + ("⚠️ contains MOCK placeholders." if compare.get("any_mock") else ""))


def ranking_table(ranking: list[dict], name_fn):
    if not ranking or pd is None:
        st.info("No predictions to rank.")
        return
    df = pd.DataFrame([{
        "rank": i + 1,
        "inhibitor": name_fn(r["compound_id"]),
        "compound_id": r["compound_id"],
        "affinity_pred_value": r["affinity_pred_value"],
        "binder_prob": r.get("affinity_probability_binary"),
        "source": "MOCK" if r.get("is_mock") else r.get("model_checkpoint", "real"),
    } for i, r in enumerate(ranking)])
    st.dataframe(df, width="stretch", hide_index=True)
    st.caption("Ranked by affinity_pred_value ascending (lower = stronger).")
