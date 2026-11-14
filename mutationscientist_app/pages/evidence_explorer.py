"""E. Evidence Explorer — Person 3's retrieval service. Real, cited evidence."""
from __future__ import annotations
import streamlit as st
from components import ui


def render(ctx):
    data, evsvc = ctx.data, ctx.evidence
    st.header("📚 Evidence Explorer")
    ui.badges("real")
    st.caption("Curated biological evidence with traceable PMID/DOI/source links.")

    c1, c2, c3 = st.columns([2, 2, 1])
    mut_ids = ["(any)"] + [m["mutation_id"] for m in data.list_mutations()]
    cmp_ids = ["(any)"] + sorted({r.get("compound_id") for r in evsvc.rows if r.get("compound_id")})
    mid = c1.selectbox("Mutation", mut_ids)
    cid = c2.selectbox("Compound", cmp_ids, format_func=lambda x: data.compound_display_name(x) if x != "(any)" else x)
    match = c3.radio("Match", ["any", "pair"], help="'pair' = this mutation AND this compound")

    res = evsvc.retrieve(
        mutation_id=None if mid == "(any)" else mid,
        compound_id=None if cid == "(any)" else cid,
        match=match,
    )
    st.subheader(f"{res['count']} evidence item(s)")
    if not res["count"]:
        st.info("No curated evidence matched (nothing invented).")
        return

    for e in res["evidence"]:
        with st.container(border=True):
            st.markdown(f"**{e['evidence_id']}** · {e['mutation_id']} × {e.get('compound_id') or 'general'} "
                        f"· _{e['evidence_category'] or e['evidence_type']}_")
            st.write(e["claim"])
            meta = []
            if e.get("assay_type"):
                meta.append(f"assay: {e['assay_type']}")
            if e.get("evidence_strength"):
                meta.append(f"strength: {e['evidence_strength']}")
            if e.get("publication_year"):
                meta.append(str(e["publication_year"]))
            if meta:
                st.caption(" · ".join(meta))
            links = []
            if e.get("pmid"):
                links.append(f"[PMID:{e['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{e['pmid']}/)")
            if e.get("doi"):
                links.append(f"[DOI:{e['doi']}](https://doi.org/{e['doi']})")
            if e.get("source_url"):
                links.append(f"[source]({e['source_url']})")
            if links:
                st.markdown(" · ".join(links))
            if e.get("source_title"):
                st.caption(e["source_title"])
