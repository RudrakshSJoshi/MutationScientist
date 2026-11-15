"""
theme.py — injects the "Protein Lens" design system (design-system.md) over
Streamlit so the app reads as a Figma-designed research instrument.

- Dark-first, with a validated light palette (manual toggle, pure-CSS swap).
- Inter + JetBrains Mono; the Truth Ladder provenance palette.
- Responsive (sidebar/stat-tiles collapse on mobile), accessible focus rings,
  honoured reduced-motion, subtle content fade-in.

Call `inject(light=...)` once per run, before the page body is drawn.
"""
from __future__ import annotations
import streamlit as st

# --- palette tokens (design-system.md §2) ---------------------------------
DARK_VARS = """
  --bg:#0A0E17; --surface-1:#111726; --surface-2:#19202F; --surface-3:#212A3B;
  --border:#26303F; --border-strong:#35415A;
  --text-1:#EAEEF6; --text-2:#A6B2C6; --text-3:#6E7C93;
  --accent:#35C4E8; --accent-hover:#6BD8F0; --accent-weak:rgba(53,196,232,.14);
  --measured:#0CA30C; --measured-bed:rgba(12,163,12,.14);
  --predicted:#3987E5; --predicted-bed:rgba(57,135,229,.14);
  --finetuned:#7C8CF0; --finetuned-bed:rgba(124,140,240,.16);
  --reasoned:#9085E9; --reasoned-bed:rgba(144,133,233,.16);
  --placeholder:#E05A5A; --placeholder-bed:rgba(224,90,90,.14);
  --warn:#FAB219;
"""
LIGHT_VARS = """
  --bg:#F6F8FC; --surface-1:#FFFFFF; --surface-2:#EEF2F8; --surface-3:#E4EAF3;
  --border:#DCE3EE; --border-strong:#C2CDDD;
  --text-1:#0E1726; --text-2:#44546B; --text-3:#6B7A91;
  --accent:#0C87A8; --accent-hover:#0A7391; --accent-weak:rgba(12,135,168,.10);
  --measured:#008300; --measured-bed:rgba(0,131,0,.10);
  --predicted:#2A78D6; --predicted-bed:rgba(42,120,214,.10);
  --finetuned:#6250D6; --finetuned-bed:rgba(98,80,214,.10);
  --reasoned:#6250D6; --reasoned-bed:rgba(98,80,214,.10);
  --placeholder:#D03B3B; --placeholder-bed:rgba(208,59,59,.10);
  --warn:#B9820F;
"""

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root{
  --r-sm:6px; --r-md:10px; --r-lg:14px;
  --sans:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  --mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
}

/* ---- base ---------------------------------------------------------------- */
html, body, .stApp, [data-testid="stAppViewContainer"]{ background:var(--bg); color:var(--text-1); font-family:var(--sans); }
.block-container{ max-width:1180px; padding-top:2.2rem; padding-bottom:4rem; }
code, kbd, pre, .stCode, [data-testid="stCode"] *,
[data-testid="stMetricValue"], [data-testid="stDataFrame"] [role="gridcell"], .mono{ font-family:var(--mono) !important; }

/* content fade-in (reduced-motion honoured below) */
[data-testid="stMain"] .block-container > div{ animation:fade .22s ease both; }
@keyframes fade{ from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:none} }

/* ---- typography (design-system.md §3) ------------------------------------ */
h1, .stMarkdown h1{ font-family:var(--sans); font-weight:650; font-size:1.9rem; line-height:1.2; letter-spacing:-.01em; color:var(--text-1); }
h2, .stMarkdown h2{ font-weight:600; font-size:1.3rem; line-height:1.4; color:var(--text-1); margin-top:.4rem; }
h3, .stMarkdown h3{ font-weight:600; font-size:1.02rem; color:var(--text-1); }
h5, .stMarkdown h5{ font-weight:600; font-size:.82rem; text-transform:uppercase; letter-spacing:.05em; color:var(--text-2); }
.stMarkdown p, .stMarkdown li{ color:var(--text-1); font-size:.96rem; line-height:1.55; }
[data-testid="stCaptionContainer"], .stCaption, small{ color:var(--text-3) !important; }
a, a:visited{ color:var(--accent); text-decoration:none; }
a:hover{ color:var(--accent-hover); text-decoration:underline; }
.main h1:first-of-type, .main h2:first-of-type{ padding-bottom:.5rem; border-bottom:1px solid var(--border); }

/* ---- sidebar / app shell ------------------------------------------------- */
section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div{
  background:var(--surface-1) !important; border-right:1px solid var(--border); }
section[data-testid="stSidebar"] .block-container{ padding-top:1.4rem; }
section[data-testid="stSidebar"] div[role="radiogroup"]{ gap:3px; }
section[data-testid="stSidebar"] div[role="radiogroup"] > div{ border-radius:var(--r-sm); border:1px solid transparent; cursor:pointer; transition:background .12s,border-color .12s; }
section[data-testid="stSidebar"] div[role="radiogroup"] > div:hover{ background:var(--surface-2); }
section[data-testid="stSidebar"] div[role="radiogroup"] > div[data-selected="true"]{ background:var(--accent-weak); border-color:color-mix(in srgb, var(--accent) 42%, transparent); }
section[data-testid="stSidebar"] label[data-testid="stRadioOption"]{ width:100%; padding:7px 11px; margin:0; }
section[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child{ display:none !important; }
section[data-testid="stSidebar"] div[role="radiogroup"] p{ font-size:.95rem; color:var(--text-2); margin:0; }
section[data-testid="stSidebar"] div[role="radiogroup"] > div[data-selected="true"] p{ color:var(--accent-hover); font-weight:600; }

/* ---- buttons ------------------------------------------------------------- */
.stButton > button, .stDownloadButton > button{ border-radius:var(--r-sm); font-family:var(--sans); font-weight:600; min-height:40px; border:1px solid var(--border-strong); background:var(--surface-2); color:var(--text-1); transition:background .12s,border-color .12s,transform .02s,box-shadow .12s; }
.stButton > button:hover, .stDownloadButton > button:hover{ background:var(--surface-3); border-color:var(--accent); }
.stButton > button:active{ transform:translateY(1px); }
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"]{ background:var(--accent); color:#06121a; border:0; font-weight:700; }
.stButton > button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover{ background:var(--accent-hover); box-shadow:0 2px 14px color-mix(in srgb,var(--accent) 40%,transparent); }

/* ---- inputs / selects ---------------------------------------------------- */
div[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input{ background:var(--surface-2) !important; border-color:var(--border) !important; border-radius:var(--r-sm) !important; color:var(--text-1) !important; }
div[data-baseweb="select"] > div:focus-within, .stTextInput input:focus{ border-color:var(--accent) !important; box-shadow:0 0 0 2px var(--accent-weak) !important; }
label p{ color:var(--text-2) !important; font-weight:500; }
.main div[role="radiogroup"]{ gap:6px; }

/* ---- a11y: visible keyboard focus everywhere ----------------------------- */
a:focus-visible, button:focus-visible, [role="radio"]:focus-visible,
[data-baseweb="select"] *:focus-visible, input:focus-visible, summary:focus-visible,
[data-baseweb="tab"]:focus-visible{ outline:2px solid var(--accent) !important; outline-offset:2px !important; border-radius:4px; }

/* ---- tabs ---------------------------------------------------------------- */
.stTabs [data-baseweb="tab-list"]{ gap:4px; border-bottom:1px solid var(--border); }
.stTabs [data-baseweb="tab"]{ color:var(--text-2); font-weight:500; padding:6px 2px; }
.stTabs [aria-selected="true"]{ color:var(--accent-hover) !important; }
.stTabs [data-baseweb="tab-highlight"]{ background:var(--accent) !important; }

/* ---- metrics (stat tiles) ------------------------------------------------ */
div[data-testid="stMetric"]{ background:var(--surface-1); border:1px solid var(--border); border-radius:var(--r-md); padding:14px 16px; transition:border-color .12s, transform .12s; }
div[data-testid="stMetric"]:hover{ border-color:var(--border-strong); transform:translateY(-1px); }
[data-testid="stMetricValue"]{ font-weight:600; color:var(--text-1); }
[data-testid="stMetricLabel"] p{ color:var(--text-2) !important; font-size:.82rem; text-transform:uppercase; letter-spacing:.03em; }
[data-testid="stMetricDelta"]{ color:var(--text-3) !important; }
[data-testid="stMetricDelta"] svg{ display:none; }

/* ---- dataframes ---------------------------------------------------------- */
[data-testid="stDataFrame"]{ border:1px solid var(--border); border-radius:var(--r-md); }
[data-testid="stDataFrame"] [role="columnheader"]{ background:var(--surface-3) !important; color:var(--text-2) !important; text-transform:uppercase; font-size:.74rem; letter-spacing:.03em; }

/* KV table */
table.kv{ width:100%; border-collapse:collapse; margin:.2rem 0 .6rem; }
table.kv td{ padding:7px 10px; border-bottom:1px solid var(--border); vertical-align:top; font-size:.9rem; }
table.kv td.k{ color:var(--text-2); width:42%; font-weight:500; }
table.kv td.v{ color:var(--text-1); font-family:var(--mono); font-size:.86rem; }

/* ---- cards / expanders / alerts ----------------------------------------- */
div[data-testid="stVerticalBlockBorderWrapper"]{ background:var(--surface-1); border-radius:var(--r-md); }
details[data-testid="stExpander"], [data-testid="stExpander"] details{ background:var(--surface-1); border:1px solid var(--border) !important; border-radius:var(--r-md) !important; }
[data-testid="stExpander"] summary:hover{ color:var(--accent-hover); }
hr{ border-color:var(--border); }
div[data-testid="stAlert"]{ border-radius:var(--r-md); border:1px solid var(--border); border-left-width:4px; background:var(--surface-1); color:var(--text-1); }

/* ---- provenance pill + legend (the Truth Ladder) ------------------------- */
.prov-row{ display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin:.1rem 0 .4rem; }
.prov-pill{ display:inline-flex; align-items:center; gap:6px; background:var(--pb); color:var(--pc); border:1px solid color-mix(in srgb, var(--pc) 38%, transparent); padding:3px 10px; border-radius:999px; font-family:var(--sans); font-weight:700; font-size:11px; line-height:1.1; letter-spacing:.04em; text-transform:uppercase; white-space:nowrap; vertical-align:middle; }
.prov-dot{ width:7px; height:7px; border-radius:50%; background:var(--pc); box-shadow:0 0 0 2px color-mix(in srgb, var(--pc) 22%, transparent); }
.prov-legend{ border:1px solid var(--border); border-radius:var(--r-md); background:var(--surface-1); padding:10px 12px; margin-top:6px; }
.prov-legend .lh{ font-size:.7rem; text-transform:uppercase; letter-spacing:.06em; color:var(--text-3); margin-bottom:7px; font-weight:700; }
.prov-legend .li{ display:flex; align-items:center; gap:8px; margin:5px 0; font-size:.8rem; color:var(--text-2); }
.prov-legend .sw{ width:9px; height:9px; border-radius:50%; flex:0 0 auto; }

/* score callout + honest-empty */
.score-callout{ background:var(--surface-2); border:1px solid var(--border); border-left:3px solid var(--accent); border-radius:var(--r-sm); padding:9px 13px; color:var(--text-2); font-size:.82rem; margin:.3rem 0 .6rem; font-family:var(--mono); line-height:1.5; }
.honest-empty{ background:var(--surface-1); border:1px dashed var(--border-strong); border-radius:var(--r-md); padding:18px; text-align:center; color:var(--text-2); font-size:.92rem; }

/* brand mark */
.brandmark{ display:flex; align-items:center; gap:10px; margin:0 0 2px; }
.brandmark .logo{ width:30px; height:30px; border-radius:8px; display:grid; place-items:center; background:linear-gradient(135deg,var(--accent),var(--reasoned)); color:#06121a; font-weight:800; font-size:16px; }
.brandmark .wm{ font-family:var(--sans); font-weight:700; font-size:1.12rem; color:var(--text-1); letter-spacing:-.01em; line-height:1; }
.brandmark .wm small{ display:block; font-weight:500; font-size:.68rem; color:var(--text-3); text-transform:uppercase; letter-spacing:.06em; margin-top:3px; }

/* ---- responsive (design-system.md §4: sidebar collapses < 860px) --------- */
@media (max-width: 860px){
  .block-container{ padding-top:1.2rem; padding-left:1rem; padding-right:1rem; }
  h1, .stMarkdown h1{ font-size:1.5rem; }
  div[data-testid="stMetric"]{ padding:11px 12px; }
  [data-testid="stMetricValue"]{ font-size:1.4rem !important; }
  .score-callout{ font-size:.74rem; }
  /* stack any horizontal columns on narrow screens */
  [data-testid="stHorizontalBlock"]{ flex-wrap:wrap; }
  [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]{ min-width:100% !important; flex:1 1 100% !important; }
}

/* ---- reduced motion ------------------------------------------------------ */
@media (prefers-reduced-motion: reduce){ *{ transition:none !important; animation:none !important; } }
"""


def inject(light: bool = False):
    vars_ = LIGHT_VARS if light else DARK_VARS
    st.markdown(f"<style>:root{{{vars_}}}\n{BASE_CSS}</style>", unsafe_allow_html=True)
