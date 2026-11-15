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
    # Derive IC50-nM equivalents from the log10(IC50 µM) values when the explicit
    # fields are absent (real file records carry the log value only) so the snapshot
    # shows a clean nM figure instead of a raw float.
    if pv_nM is None and pv_log is not None:
        try: pv_nM = 10.0 ** (float(pv_log) + 3.0)
        except (TypeError, ValueError): pv_nM = None
    if ev_nM is None and pred.get("experimental_affinity_label") is not None:
        try: ev_nM = 10.0 ** (float(pred["experimental_affinity_label"]) + 3.0)
        except (TypeError, ValueError): ev_nM = None
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


def winrate_journey(journey, baseline, best, ties_base, source):
    """The fine-tune's Adaption win-rate climb: baseline → best. Reasoned (violet)
    provenance — this is the MODEL's benchmark, never a biochemical measurement."""
    import config.settings as S  # local import keeps charts importable standalone
    ui.badges("llm")
    c1, c2, c3 = st.columns(3)
    c1.metric("Best win-rate", f"{best:.2f}", f"gemma-3-4b · +{(best-baseline):.2f} vs raw baseline")
    c2.metric("Raw baseline", f"{baseline:.2f}", "Qwen3.5-4B · no augmentation", delta_color="off")
    c3.metric("Beats base by", f"+{(best-ties_base):.2f}", f"base = {ties_base:.2f} (ties)", delta_color="off")
    if pd is not None:
        df = pd.DataFrame(
            [{"stage": s, "win-rate (vs base, higher=better)": round(w, 4)} for s, w, _ in journey]
        ).set_index("stage")
        st.bar_chart(df, horizontal=True, color="#9085E9")
    st.caption(f"{source}")


def boltz_run_overview(records: list[dict]):
    """All REAL Boltz-2 complexes at a glance: predicted-vs-measured scatter +
    a ranked, provenance-separated table. Predicted (blue) and measured (green)
    are distinct quantities and are never conflated."""
    if not records:
        ui.honest_empty("No real Boltz-2 predictions loaded (mock mode) — nothing fabricated.")
        return
    n = len(records)
    muts = len({r.get("mutation_id") for r in records})
    cmps = len({r.get("compound_id") for r in records})
    c1, c2, c3 = st.columns(3)
    with c1:
        ui.badges("pretrained")
        st.metric("Real Boltz-2 complexes", f"{n}")
    c2.metric("EGFR variants", f"{muts}")
    c3.metric("Inhibitors", f"{cmps}")

    pairs = [(r.get("experimental_affinity_label"), r.get("affinity_pred_value"))
             for r in records
             if r.get("experimental_affinity_label") is not None
             and r.get("affinity_pred_value") is not None]
    if pairs and pd is not None:
        df = pd.DataFrame({
            "measured  log10(IC50 µM)": [e for e, _ in pairs],
            "predicted  log10(IC50 µM)": [p for _, p in pairs],
        })
        st.scatter_chart(df, x="measured  log10(IC50 µM)", y="predicted  log10(IC50 µM)",
                         color="#3987E5", height=320)
        r = _pearson([e for e, _ in pairs], [p for _, p in pairs])
        rtxt = f"Pearson r = {r:.2f} across {len(pairs)} complexes · " if r is not None else ""
        st.caption(f"{rtxt}both axes log10(IC50 µM), lower = stronger; the closer to the "
                   "diagonal, the better the pretrained affinity head tracks the measurement.")

    rows = []
    for i, r in enumerate(records):
        rows.append({
            "rank": i + 1,
            "inhibitor": r.get("compound_name") or r.get("compound_id"),
            "variant": r.get("mutation_label") or (r.get("mutation_id") or "").replace("EGFR_", ""),
            "predicted (log10 µM)": r.get("affinity_pred_value"),
            "pred IC50": _fmt_nM(r.get("affinity_pred_ic50_nM_equiv")),
            "measured IC50": _fmt_nM(r.get("experimental_ic50_nM_equiv")),
            "binder prob": r.get("affinity_probability_binary"),
            "sampling": "default" if "default" in (r.get("sampling_settings") or "") else "reduced",
        })
    if pd is not None:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption("Ranked by predicted affinity (lower = stronger). Predicted = Boltz-2 "
               "pretrained head; measured = curated experimental IC50 — distinct quantities.")


def _pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx and dy else None


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
