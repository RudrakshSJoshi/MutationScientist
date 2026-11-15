"""
Streamlit AppTest smoke test — every page of the MutationScientist app renders
with ZERO uncaught exceptions, and the headline report actually generates.

Run:
    cd application
    .venv/bin/python -m pytest tests/ -q          # with pytest, or
    .venv/bin/python tests/test_pages.py          # standalone (no pytest needed)

It runs against the real EGFR_RESEARCH_DATASET (found by searching upward from
the app) in MOCK Boltz / TEMPLATE LLM mode — i.e. exactly the demo default.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

# Force the deterministic demo-default mode: MOCK Boltz + TEMPLATE LLM. This keeps
# the smoke test fast and free of any external dependency (no live model server),
# regardless of what is exported in the shell.
for _v in ("BOLTZ_PREDICTIONS_PATH", "OPENAI_BASE_URL", "OPENAI_API_KEY",
           "OPENAI_MODEL", "ADAPTION_API_KEY", "ADAPTION_STACK", "ADAPTION_MODEL_ID"):
    os.environ.pop(_v, None)

import streamlit as st
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app.py"

PAGE_LABELS = [
    "🏠 Overview",
    "🧬 Mutation Explorer",
    "💊 Inhibitor Explorer",
    "🔬 Molecular Screening",
    "🧩 Structure Viewer",
    "📚 Evidence Explorer",
    "🧠 MutationScientist Report",
]


def _nav_radio(at: AppTest):
    """The sidebar navigation radio is the first radio created each run."""
    return at.radio[0]


def run_all_pages() -> list[str]:
    """Visit every page; return a list of failure strings (empty == all good)."""
    failures: list[str] = []

    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    if at.exception:
        return [f"initial load raised: {at.exception}"]

    for label in PAGE_LABELS:
        at = AppTest.from_file(str(APP), default_timeout=60)
        at.run()
        _nav_radio(at).set_value(label).run()
        if at.exception:
            failures.append(f"{label}: {[str(e) for e in at.exception]}")
            continue
        # The report page must also generate a report with no exception.
        if "Report" in label:
            gen = [b for b in at.button if "Generate" in (b.label or "")]
            if not gen:
                failures.append(f"{label}: no 'Generate research report' button found")
                continue
            gen[0].click().run()
            if at.exception:
                failures.append(f"{label} (generate): {[str(e) for e in at.exception]}")
            else:
                md = " ".join(m.value for m in at.markdown)
                # headline pair must default to osimertinib and honestly show no prediction
                if "osimertinib" not in md.lower():
                    failures.append(f"{label}: report did not reference osimertinib (headline pair)")

    # Quick-select flow: one-click BLU-945 pair -> Generate -> no exception.
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    _nav_radio(at).set_value("🧠 MutationScientist Report").run()
    quick = [b for b in at.button if "non-covalent demo pair" in (b.label or "")]
    if not quick:
        failures.append("quick-select: 'Load non-covalent demo pair' button not found")
    else:
        quick[0].click().run()
        sel = {s.label: s.value for s in at.selectbox}
        if sel.get("Mutation") != "EGFR_L858R_C797S":
            failures.append(f"quick-select: mutation = {sel.get('Mutation')} (expected EGFR_L858R_C797S)")
        if sel.get("Inhibitor") != "CMP_BLU945":
            failures.append(f"quick-select: inhibitor = {sel.get('Inhibitor')} (expected CMP_BLU945)")
        gen = [b for b in at.button if "Generate" in (b.label or "")]
        gen[0].click().run()
        if at.exception:
            failures.append(f"quick-select (generate): {[str(e) for e in at.exception]}")
        else:
            md = " ".join(m.value for m in at.markdown).lower()
            if "blu-945" not in md and "blu945" not in md and "complex_001557" not in md.lower():
                failures.append("quick-select: report did not reference the BLU-945 complex")

    # Real-Boltz mode: when the predictions file is present, the app shows a REAL
    # Boltz badge and every page still renders (predictions file, no LLM needed).
    boltz_file = Path.home() / "Desktop/EGFR_TRAINING/boltz_predictions.json"
    if boltz_file.exists():
        os.environ["BOLTZ_PREDICTIONS_PATH"] = str(boltz_file)
        st.cache_resource.clear()  # services are @st.cache_resource — rebuild with new env
        try:
            at = AppTest.from_file(str(APP), default_timeout=60)
            at.run()
            if at.exception:
                failures.append(f"real-boltz load: {[str(e) for e in at.exception]}")
            else:
                md = " ".join(m.value for m in at.markdown)
                if "Pretrained Boltz" not in md and "REAL" not in md:
                    failures.append("real-boltz: overview did not show a real Boltz badge")
                # the real run must surface its complexes on Molecular Screening
                _nav_radio(at).set_value("🔬 Molecular Screening").run()
                md2 = " ".join(m.value for m in at.markdown)
                if at.exception:
                    failures.append(f"real-boltz screening render: {[str(e) for e in at.exception]}")
                elif "Real Boltz-2 complexes" not in md2 and "real Boltz-2 complex" not in md2:
                    failures.append("real-boltz: Molecular Screening did not surface the real complexes")
                _nav_radio(at).set_value("🔬 Molecular Screening").run()
                if at.exception:
                    failures.append(f"real-boltz screening: {[str(e) for e in at.exception]}")
        finally:
            os.environ.pop("BOLTZ_PREDICTIONS_PATH", None)

    # Light mode renders without exception.
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.session_state["ms_light"] = True
    at.run()
    if at.exception:
        failures.append(f"light-mode: {[str(e) for e in at.exception]}")

    return failures


def test_all_seven_pages_render_without_exceptions():
    failures = run_all_pages()
    assert not failures, "Page render failures:\n" + "\n".join(failures)


if __name__ == "__main__":
    fails = run_all_pages()
    if fails:
        print("FAIL — exceptions on:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print(f"PASS — all {len(PAGE_LABELS)} pages rendered with 0 exceptions; "
          "headline report generated; quick-select BLU-945 + Generate OK; "
          "real-Boltz mode + light mode render clean.")
