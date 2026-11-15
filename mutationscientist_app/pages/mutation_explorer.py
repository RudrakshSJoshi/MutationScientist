"""A. Mutation Explorer — browse EGFR variants, residues, domain, mechanism, evidence."""
from __future__ import annotations
import streamlit as st
from components import ui


def render(ctx):
    data = ctx.data
    st.header("🧬 Mutation Explorer")
    st.caption("EGFR variants from the curated dataset (UniProt P00533, canonical P00533-1).")

    muts = data.list_mutations()
    labels = {m["mutation_id"]: f'{m["mutation_id"]}  ({m.get("mutation_notation") or m.get("mutation_type","")})'
              for m in muts}
    has_cx = set(data.mutations_with_complexes())

    ids = list(labels)
    default_idx = ids.index("EGFR_C797S") if "EGFR_C797S" in ids else 0
    choice = st.selectbox("Select a mutation / variant", ids, index=default_idx,
                          format_func=lambda k: labels[k] + ("  •  has Boltz complex" if k in has_cx else ""))
    m = data.get_mutation(choice)
    if not m:
        st.info("No record.")
        return

    ui.badges("experimental")
    c1, c2 = st.columns(2)
    with c1:
        ui.kv(m, ["mutation_id", "gene", "mutation_notation", "mutation_type",
                  "position", "wt_residue", "mutant_residue", "protein_domain"])
    with c2:
        ui.kv(m, ["mutation_classification", "cancer_type", "resistance_association",
                  "evidence_level", "annotation_confidence"])

    st.subheader("Known biological mechanism")
    st.write(m.get("known_mechanism") or "_Not annotated for this variant._")

    # profile(s) that include this mutation
    profs = [p for p in data.list_profiles()
             if choice in (p.get("individual_mutation_ids") or "") or p.get("sequence_id") == choice]
    if profs:
        st.subheader("Mutation profile(s)")
        for p in profs:
            st.markdown(f"- **{p['profile_id']}** — {p.get('mutation_profile')}: "
                        f"{p.get('biological_context','')}")

    st.subheader("Reference source")
    ref = data.get_reference(m.get("source_id", ""))
    if ref:
        st.markdown(f"[{ref.get('title', m.get('source_id'))}]({m.get('source_url','')})")
    elif m.get("source_url"):
        st.markdown(f"[{m.get('source_id')}]({m['source_url']})")

    # linked evidence
    ev = ctx.evidence.retrieve(mutation_id=choice)
    st.subheader(f"Linked evidence ({ev['count']})")
    if ev["count"]:
        for e in ev["evidence"][:12]:
            cite = (f"PMID:{e['pmid']}" if e["pmid"] else (f"DOI:{e['doi']}" if e["doi"] else ""))
            st.markdown(f"- {e['claim']}  \n  _{e['evidence_type']} · {e.get('compound_id') or 'general'} · {cite}_")
    else:
        st.info("No curated evidence rows reference this variant directly.")

    if choice in has_cx:
        n = len(data.complexes_for(mutation_id=choice))
        st.success(f"• {n} Boltz complex record(s) exist for this variant "
                   f"— see **Molecular Screening** / **MutationScientist Report**.")
