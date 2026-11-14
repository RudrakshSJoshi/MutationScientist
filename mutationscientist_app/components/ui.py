"""Shared UI helpers: source badges, banners, small tables. Keeps provenance
(experimental vs pretrained vs fine-tuned vs mock) visible everywhere."""
from __future__ import annotations
import streamlit as st

BADGES = {
    "experimental": ("🧪 EXPERIMENTAL", "#1b5e20", "#e8f5e9"),
    "pretrained":   ("🤖 PRETRAINED Boltz", "#0d47a1", "#e3f2fd"),
    "finetuned":    ("🎯 FINE-TUNED Boltz", "#4a148c", "#f3e5f5"),
    "mock":         ("⚠️ MOCK / PLACEHOLDER", "#b71c1c", "#ffebee"),
    "real":         ("✅ REAL (cited)", "#1b5e20", "#e8f5e9"),
    "llm":          ("💬 LLM REPORT", "#004d40", "#e0f2f1"),
    "template":     ("📝 TEMPLATE (not the model)", "#e65100", "#fff3e0"),
}


def badge(kind: str) -> str:
    label, fg, bg = BADGES.get(kind, (kind.upper(), "#333", "#eee"))
    return (f"<span style='background:{bg};color:{fg};padding:2px 8px;border-radius:10px;"
            f"font-size:0.75rem;font-weight:700;white-space:nowrap'>{label}</span>")


def badges(*kinds: str):
    st.markdown(" ".join(badge(k) for k in kinds), unsafe_allow_html=True)


def mock_banner(where: str):
    st.warning(f"⚠️ **MOCK DATA** in {where}. These are interface placeholders, "
               "not real model outputs. Supply real outputs to switch to live mode.")


def kv(d: dict, keys: list[str] | None = None):
    rows = [(k, d.get(k, "")) for k in (keys or d.keys())]
    rows = [(k, v) for k, v in rows if v not in (None, "", [])]
    md = "\n".join(f"| **{k}** | {v} |" for k, v in rows)
    st.markdown("| field | value |\n|---|---|\n" + md)


def pred_source(rec: dict) -> str:
    if rec.get("is_mock"):
        return "mock"
    ck = (rec.get("model_checkpoint") or "").lower()
    return "finetuned" if "fine" in ck else "pretrained"
