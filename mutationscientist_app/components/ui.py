"""Shared UI helpers: the Truth Ladder provenance pills, callouts, KV tables.

Provenance is a first-class visual citizen (design-system.md §2.3 / §4): a
measured value, a model prediction, an LLM sentence and a placeholder are never
styled the same. The four tiers:

  MEASURED (green)   observed / published truth   → experimental, real
  PREDICTED (blue)   Boltz-2 affinity model       → pretrained, fine-tuned
  REASONED (violet)  MutationScientist LLM         → llm report
  PLACEHOLDER (red)  interface stand-in, not real → mock, template
"""
from __future__ import annotations
import html
import streamlit as st

# tier -> (foreground colour, tint bed)  [dark palette]
_TIER = {
    "measured":    ("#0CA30C", "rgba(12,163,12,.14)"),
    "predicted":   ("#3987E5", "rgba(57,135,229,.14)"),
    "finetuned":   ("#7C8CF0", "rgba(124,140,240,.16)"),
    "reasoned":    ("#9085E9", "rgba(144,133,233,.16)"),
    "placeholder": ("#E05A5A", "rgba(224,90,90,.14)"),
}

# app badge kind -> (label with icon, tier)
BADGES = {
    "experimental": ("🧪 Experimental", "measured"),
    "real":         ("✓ Real · cited", "measured"),
    "pretrained":   ("◈ Pretrained Boltz", "predicted"),
    "finetuned":    ("◈ Fine-tuned Boltz", "finetuned"),
    "llm":          ("✦ LLM report", "reasoned"),
    "mock":         ("⚠ Mock · placeholder", "placeholder"),
    "template":     ("⚠ Template · not the model", "placeholder"),
}


def badge(kind: str) -> str:
    label, tier = BADGES.get(kind, (kind.replace("_", " ").title(), "placeholder"))
    fg, bg = _TIER.get(tier, _TIER["placeholder"])
    return (f"<span class='prov-pill' style='--pc:{fg};--pb:{bg}'>"
            f"<span class='prov-dot'></span>{html.escape(label)}</span>")


def badges(*kinds: str):
    pills = "".join(badge(k) for k in kinds)
    st.markdown(f"<div class='prov-row'>{pills}</div>", unsafe_allow_html=True)


def mock_banner(where: str):
    st.warning(f"⚠️ **MOCK DATA** in {where}. These are clearly-labelled interface "
               "placeholders, not real model outputs — supply real outputs to switch "
               "to live mode. Nothing here is a scientific result.")


def score_callout(text: str):
    """The persistent score-convention strip shown on every prediction surface."""
    st.markdown(f"<div class='score-callout'>{html.escape(text)}</div>",
                unsafe_allow_html=True)


def honest_empty(msg: str):
    """A designed, dignified 'no data' state — never a blank or a fabricated row."""
    st.markdown(f"<div class='honest-empty'>{html.escape(msg)}</div>",
                unsafe_allow_html=True)


def provenance_legend():
    """Persistent Truth Ladder legend — the product's integrity key, always visible."""
    items = [
        ("measured", "MEASURED", "observed · cited"),
        ("predicted", "PREDICTED", "Boltz-2 model"),
        ("reasoned", "REASONED", "our LLM"),
        ("placeholder", "PLACEHOLDER", "mock · not real"),
    ]
    rows = "".join(
        f"<div class='li'><span class='sw' style='background:{_TIER[t][0]}'></span>"
        f"<b style='color:{_TIER[t][0]}'>{lbl}</b>&nbsp;· {desc}</div>"
        for t, lbl, desc in items)
    st.markdown(f"<div class='prov-legend'><div class='lh'>Provenance — the Truth Ladder</div>"
                f"{rows}</div>", unsafe_allow_html=True)


def kv(d: dict, keys: list[str] | None = None):
    """Two-column field/value card. Scientific values render monospaced."""
    rows = [(k, d.get(k, "")) for k in (keys or list(d.keys()))]
    rows = [(k, v) for k, v in rows if v not in (None, "", [])]
    if not rows:
        return
    body = []
    for k, v in rows:
        vcell = html.escape(str(v))
        body.append(f"<tr><td class='k'>{html.escape(k)}</td>"
                    f"<td class='v'>{vcell}</td></tr>")
    st.markdown("<table class='kv'>" + "".join(body) + "</table>",
                unsafe_allow_html=True)


def pred_source(rec: dict) -> str:
    if rec.get("is_mock"):
        return "mock"
    ck = (rec.get("model_checkpoint") or "").lower()
    return "finetuned" if "fine" in ck else "pretrained"
