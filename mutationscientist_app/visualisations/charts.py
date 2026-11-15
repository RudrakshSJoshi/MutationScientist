"""Small chart helpers built on Streamlit's native charts (pandas comes with
Streamlit). Charts of predicted values always say lower = stronger."""
from __future__ import annotations
import streamlit as st
from components import ui

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


def _fmt_nM(v):
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    return f"{v:,.2f} nM" if v < 1000 else f"{v/1000:,.2f} µM"


def pred_vs_exp(pred: dict):
    """The signature comparison: PREDICTED (blue, Boltz-2) beside MEASURED (green).
    Uses the real prediction's IC50-equivalents when present; always labels
    provenance and the lower=stronger convention. Never conflates the two."""
    if not pred:
        return
    is_mock = pred.get("is_mock")
    pv_log = pred.get("affinity_pred_value")
    pv_nM = pred.get("affinity_pred_ic50_nM_equiv")
    ev_nM = pred.get("experimental_ic50_nM_equiv")
    prob = pred.get("affinity_probability_binary")
    conf = pred.get("confidence_score")

    c1, c2, c3 = st.columns(3)
    with c1:
        ui.badges("mock" if is_mock else ui.pred_source(pred))
        st.metric("Predicted affinity (Boltz-2)",
                  _fmt_nM(pv_nM) if pv_nM is not None else (f"{pv_log}" if pv_log is not None else "—"),
                  help="affinity_pred_value = log10(IC50 µM), lower = stronger.")
        sub = []
        if pv_log is not None:
            sub.append(f"log10(IC50 µM) = {pv_log:.3f}")
        if prob is not None:
            sub.append(f"binder prob {prob:.2f}")
        if sub:
            st.caption(" · ".join(sub))
    with c2:
        if ev_nM is not None:
            ui.badges("experimental")
            st.metric("Measured IC50 (reference)", _fmt_nM(ev_nM),
                      help="The experimental value this complex was compared against.")
        else:
            ui.badges("experimental")
            st.metric("Measured IC50 (reference)", "see table")
    with c3:
        if conf is not None and not is_mock:
            st.metric("Model confidence", f"{conf:.2f}")
    if is_mock:
        st.caption("⚠️ Predicted values are MOCK placeholders — predicted ≠ experimental.")
    else:
        st.caption("Predicted (Boltz-2) vs measured are distinct quantities; lower = stronger.")


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
