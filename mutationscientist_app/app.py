"""
MutationScientist — EGFR Molecular Discovery
Person 4 deliverable: the integrated research application.

Ties together the dataset, Boltz predictions (Person 2), evidence retrieval
(Person 3) and the fine-tuned LLM (Person 1) behind one interface. Every service
runs REAL when real outputs are supplied and MOCK otherwise — always labelled.

Run:  streamlit run app.py     (from the application/ directory)
"""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))  # make packages importable

import config.settings as S
from services.dataset_service import DatasetService
from services.boltz_service import BoltzService
from services.evidence_service import EvidenceService
from services.llm_service import LLMService
from components import ui, theme
from pages import (mutation_explorer, inhibitor_explorer, molecular_screening,
                   structure_viewer, evidence_explorer, mutation_scientist)

st.set_page_config(page_title=S.APP_TITLE, page_icon=S.APP_ICON, layout="wide")
theme.inject()


@st.cache_resource(show_spinner="Loading EGFR_RESEARCH_DATASET…")
def build_services():
    data = DatasetService()
    return SimpleNamespace(
        data=data,
        boltz=BoltzService(data),
        evidence=EvidenceService(data),
        llm=LLMService(),
        score_definition=S.SCORE_DEFINITION,
    )


def overview(ctx):
    st.header("🏠 Overview")
    st.markdown(
        "**MutationScientist** investigates mutation-dependent EGFR–inhibitor "
        "interactions and acquired resistance in NSCLC, combining a **Boltz-2 affinity** "
        "model with an **evidence-grounded LLM**. This app is the integration layer."
    )
    s = ctx.data.status()
    a, b, c, d = st.columns(4)
    a.metric("Boltz complexes", f"{s['boltz']['total_complexes']:,}",
             f"train {s['boltz']['train']} / val {s['boltz']['validation']} / test {s['boltz']['test']}")
    b.metric("Eligible measurement rows", f"{s['boltz']['eligible_measurement_rows']:,}")
    c.metric("LLM SFT examples", f"{s['llm']['total']:,}")
    d.metric("Mutations × compounds", f"{s['n_mutations']} × {s['n_compounds_named']}",
             f"+{s['n_bindingdb_ligands']:,} BDB ligands")

    st.markdown("#### Service status")
    st.markdown(
        f"- **Boltz predictions** — {ctx.boltz.mode_label()}  {ui.badge('mock') if not ctx.boltz.real_mode else ui.badge('pretrained')}\n"
        f"- **Evidence retrieval** — {ctx.evidence.mode_label()}  {ui.badge('real')}\n"
        f"- **MutationScientist LLM** — {ctx.llm.mode_label()}  {ui.badge('llm') if ctx.llm.real_mode else ui.badge('template')}",
        unsafe_allow_html=True,
    )
    if not ctx.boltz.real_mode or not ctx.llm.real_mode:
        st.info("Running with mock placeholders for the parts not yet delivered. Set "
                f"`{S.ENV_BOLTZ_PREDICTIONS}` (Person 2) and `{S.ENV_ADAPTION_API_KEY}`+"
                f"`{S.ENV_ADAPTION_STACK}` (Person 1) to go live — no UI change needed.")

    st.markdown("#### The demo question")
    st.markdown("> *How does EGFR **C797S** affect the predicted interaction with "
                "**osimertinib**, and what evidence supports the proposed resistance mechanism?*  \n"
                "→ open **MutationScientist Report** (defaults to this pair).")

    ui.score_callout(ctx.score_definition)
    st.caption("Not for clinical decisions. Predicted affinity ≠ inhibition ≠ clinical efficacy.")


PAGES = {
    "🏠 Overview": overview,
    "🧬 Mutation Explorer": mutation_explorer.render,
    "💊 Inhibitor Explorer": inhibitor_explorer.render,
    "🔬 Molecular Screening": molecular_screening.render,
    "🧩 Structure Viewer": structure_viewer.render,
    "📚 Evidence Explorer": evidence_explorer.render,
    "🧠 MutationScientist Report": mutation_scientist.render,
}


def main():
    try:
        ctx = build_services()
    except Exception as e:
        st.error(f"Could not load the dataset: {e}")
        st.stop()

    with st.sidebar:
        st.markdown(
            "<div class='brandmark'><div class='logo'>◈</div>"
            "<div class='wm'>MutationScientist<small>EGFR Molecular Discovery</small></div></div>",
            unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        choice = st.radio("Navigate", list(PAGES), label_visibility="collapsed")
        st.markdown("---")
        s = ctx.data.status()
        st.caption(f"dataset **{s['version']}** · {s['boltz']['total_complexes']:,} complexes · "
                   f"{s['llm']['total']:,} SFT rows")
        probs = ctx.data.validate()
        if probs:
            st.error(f"⚠️ {len(probs)} integrity issue(s)")
        else:
            st.success("✅ integrity OK")
        st.markdown(
            f"Boltz: {ui.badge('mock') if not ctx.boltz.real_mode else ui.badge('pretrained')}<br>"
            f"LLM: {ui.badge('template') if not ctx.llm.real_mode else ui.badge('llm')}",
            unsafe_allow_html=True)

    PAGES[choice](ctx)


if __name__ == "__main__":
    main()
