"""F. MutationScientist Report — assembles mutation + compound + Boltz prediction
+ evidence into one structured context and generates the grounded report.

This is the end-to-end integrated workflow (the demo question):
  'How does EGFR C797S affect the predicted interaction with osimertinib, and
   what evidence supports the proposed resistance mechanism?'"""
from __future__ import annotations
import json
import streamlit as st
from components import ui


def render(ctx):
    data, boltz, evsvc, llm = ctx.data, ctx.boltz, ctx.evidence, ctx.llm
    st.header("🧠 MutationScientist Report")
    st.markdown("LLM mode: " + (ui.badge("llm") if llm.real_mode else ui.badge("template")),
                unsafe_allow_html=True)

    # --- selection -------------------------------------------------------
    muts = [m["mutation_id"] for m in data.list_mutations()]
    if "_ms_mut" not in st.session_state:
        # KEEP the headline default: EGFR_C797S × osimertinib (covalent -> no Boltz complex).
        st.session_state["_ms_mut"] = "EGFR_C797S" if "EGFR_C797S" in muts else (muts[0] if muts else None)

    # One-click non-covalent demo pair: this one DOES have a Boltz complex, so the
    # report also shows a real prediction-vs-experiment pair (BLU-945 is a named,
    # reversible/non-covalent mutant-selective TKI, included in the regression target).
    NONCOV_MUT, NONCOV_CMP = "EGFR_L858R_C797S", "CMP_BLU945"
    if st.button(
        "🧪 Load non-covalent demo pair (has a Boltz prediction): "
        "EGFR L858R/C797S × BLU-945",
        help="The headline C797S × osimertinib pair is covalent and has no Boltz "
             "complex, so it shows 'no prediction'. This companion pair has a real "
             "Boltz complex plus a curated measurement.",
    ):
        st.session_state["_ms_mut"] = NONCOV_MUT
        st.session_state["_ms_want_cmp"] = NONCOV_CMP
        st.rerun()

    c1, c2 = st.columns(2)
    mid = c1.selectbox("Mutation", muts, key="_ms_mut")

    # The curated, named inhibitor panel is ALWAYS offered (osimertinib, BLU-945,
    # …) — the headline C797S × osimertinib pair has evidence but no Boltz
    # complex/measurement, so it must stay selectable even though it is not in
    # `compounds_tested_against`. Any extra BindingDB ligands with data for this
    # mutation are appended after the named panel.
    named_panel = [c["compound_id"] for c in data.list_compounds()]
    tested = data.compounds_tested_against(mid)
    options = named_panel + [t for t in tested if t not in named_panel]

    # Honour a pending quick-select, then reconcile any stale value against the
    # current mutation's option list (options change when the mutation changes).
    want = st.session_state.pop("_ms_want_cmp", None)
    if want and want in options:
        st.session_state["_ms_cmp"] = want
    if st.session_state.get("_ms_cmp") not in options:
        st.session_state.pop("_ms_cmp", None)

    if "_ms_cmp" in st.session_state:
        cid = c2.selectbox("Inhibitor", options, key="_ms_cmp",
                           format_func=data.compound_display_name)
    else:
        default_cmp = next((i for i, o in enumerate(options) if "OSIMERT" in o.upper()), 0)
        cid = c2.selectbox("Inhibitor", options, index=default_cmp, key="_ms_cmp",
                           format_func=data.compound_display_name)

    mutation = data.get_mutation(mid)
    compound = data.get_compound(cid)
    preds = boltz.predictions_for(mutation_id=mid, compound_id=cid)
    meas = data.measurements_for(mutation_id=mid, compound_id=cid)
    ev = evsvc.retrieve(mutation_id=mid, compound_id=cid, match="any")["evidence"]

    # --- what's assembled ------------------------------------------------
    with st.expander("Assembled context (exactly what the model receives)", expanded=False):
        colA, colB, colC = st.columns(3)
        colA.metric("Boltz predictions", len(preds), "MOCK" if any(p.get("is_mock") for p in preds) else "real")
        colB.metric("Experimental measurements", len(meas))
        colC.metric("Evidence items", len(ev))

    spin = ("Assembling context and generating with the fine-tuned MutationScientist "
            "model…" if llm.real_mode else "Assembling context and generating…")
    if st.button("🧪 Generate research report", type="primary"):
        with st.spinner(spin):
            report = llm.generate(mutation, compound, preds, ev, meas, data)
        st.session_state["_last_report"] = report

    report = st.session_state.get("_last_report")
    if not report:
        st.info("Select a mutation–inhibitor pair and click **Generate research report**.")
        return

    # --- provenance banner ----------------------------------------------
    if report.get("is_mock"):
        ui.badges("template")
        st.warning(f"📝 This report was produced by **{report.get('model')}**, not the "
                   "fine-tuned MutationScientist model. It restates only values present in the "
                   "dataset context; it invents no numbers or citations.")
    else:
        ui.badges("llm")
        cached = " _(served from cache)_" if report.get("_cached") else ""
        st.success(f"✦ Reasoned by the fine-tuned **MutationScientist** model "
                   f"(`{report.get('model')}`){cached}. Interprets only the supplied context.")
    if any(p.get("is_mock") for p in preds):
        st.info("ℹ️ The Boltz values interpreted in this report are **MOCK placeholders** "
                "(predicted≠experimental); they go live when real predictions are supplied.")

    st.markdown("---")
    st.markdown(report["report_markdown"])

    st.markdown("---")
    with st.expander("Raw structured context (JSON)"):
        st.code(json.dumps(report.get("context", {}), indent=2), language="json")
    st.download_button("⬇️ Download report (Markdown)",
                       report["report_markdown"],
                       file_name=f"MutationScientist_{mid}_{cid}.md")
