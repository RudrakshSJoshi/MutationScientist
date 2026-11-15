# MutationScientist — 3-Minute Demo Script

**App:** http://localhost:8501 · **Design:** the *Protein Lens* system (dark default + light toggle, Inter + JetBrains Mono, the **Truth Ladder** provenance palette; a persistent legend lives in the sidebar).
**One-liner:** *"Give it an EGFR mutation and an inhibitor; MutationScientist fuses the measured data, the Boltz-2 prediction, and our fine-tuned LLM's reasoning into one report — and it never shows a guess as a fact."*

**Integration status — all three live**
- **LLM — LIVE.** The fine-tuned **MutationScientist** model at `http://localhost:8000/v1` writes the report (OpenAI-compatible, stable name `mutationscientist`). Badge **✦ LLM REPORT** (violet). The **leaderboard-winning fine-tune is gemma-3-4b at a 0.78 Adaption win-rate** — up from the **0.36** raw baseline; the **0.36 → 0.78** journey is on the Overview.
- **Boltz — LIVE.** The real Boltz-2 run (`boltz_predictions.json`) now carries **~45+ predicted complexes**, surfaced on **Molecular Screening → Boltz run** (predicted-vs-measured scatter). Badge **◈ PRETRAINED BOLTZ** (blue). Pairs without a real prediction stay honestly **⚠ MOCK** (red).
- **Evidence — REAL** (curated + cited); pluggable to a live API via `EVIDENCE_API_URL` when it lands.
- **REST API (new).** `~/Desktop/product/backend` — a FastAPI layer over these same services for the React frontend: `GET /predict`, `GET /evidence`, `POST /interpret` (CORS on). `cd ~/Desktop/product/backend && ./run.sh` → `:8080/docs`.

> **The Truth Ladder — point at the sidebar legend:** 🟢 **MEASURED** (real, cited) · 🔵 **PREDICTED** (Boltz) · 🟣 **REASONED** (our LLM) · 🔴 **PLACEHOLDER** (mock/template). "Green is real, blue is the model, violet is the writing, red is a stand-in." That legend is the integrity story.

### ⚠️ Pre-flight (before presenting — the local model is slow, ~1–2 min/report; cache makes it instant after)
1. Launch with everything wired (the gitignored `.env` is auto-loaded by `run.sh`):
   ```bash
   cd ~/Desktop/application && ./run.sh
   ```
   `.env` holds `BOLTZ_PREDICTIONS_PATH`, `OPENAI_BASE_URL=http://localhost:8000/v1`, `OPENAI_API_KEY=x`, `OPENAI_MODEL=mutationscientist` (the gateway's stable model name).
2. **Pre-generate both hero reports once** (Report page → Generate on the default pair; then **Load non-covalent demo pair** → Generate). They cache to disk (`.llm_cache/`) and then load **instantly** on stage — the output is the real model's own, badged LLM REPORT.
3. Confirm sidebar: **✅ integrity OK**, Boltz **◈ PRETRAINED**, LLM **✦ LLM REPORT**, Evidence **✓ REAL · CITED**.

---

## 0:00 — 0:25 · Overview (set the frame)
- Land on **🏠 Overview**. Four stat tiles: **6,843** complexes · **18,189** eligible rows · **1,341** SFT examples · **19 × 13** mutations × compounds.
- Point to **Service status** (all three real) and the **sidebar Truth Ladder legend**. *"Watch the colours — that legend is how you know what to trust."*
- Scroll to **Model — MutationScientist**: the **win-rate journey** tiles **0.78** best (gemma-3-4b) vs **0.36** raw baseline (**+0.28** over base), with the bar chart. *"We climbed the Adaption win-rate on purpose — augmenting the grounded EGFR set was the lever. This is the model's benchmark, not a lab measurement — it's violet, REASONED."*

## 0:25 — 1:35 · Hero flow 1 — C797S × osimertinib (resistance, evidence-led)
- **🧠 MutationScientist Report** — defaults to **EGFR_C797S × osimertinib**.
- Expand **Assembled context**: **0 predictions · 0 measurements · 15 evidence items**. *"Exactly what the model receives — real numbers only."*
- **Generate** (instant if pre-warmed). Walk it:
  - **✦ LLM REPORT** banner — our fine-tuned model, interpreting only the supplied context.
  - **Computational prediction** → designed honest-empty: *"No Boltz complex for this pair — no prediction shown."* *"Osimertinib is covalent, so it's excluded from the regression target. The honest answer is 'no prediction,' and the model says so and leans on the cited evidence."*
  - Scroll the cited resistance literature (PMIDs/DOIs).

## 1:35 — 2:35 · Hero flow 2 — L858R/C797S × BLU-945 (prediction vs experiment, closed loop)
- Click **🧪 Load non-covalent demo pair: EGFR L858R/C797S × BLU-945** → **Generate**.
- **Prediction snapshot** card: **Predicted (Boltz-2) ≈ 35 nM** (blue ◈) beside **Measured ≈ 44 nM reference** (green 🧪) — the real prediction tracks the measurement; the curated per-assay IC50s are in the table. *"Real prediction, real measurements, each colour-coded — the model then reasons over both."*
- *"Same prediction value flows into the model's `## Computational prediction` section — the loop is closed: dataset → Boltz → our LLM, live."*
- (15s) **🔬 Molecular Screening → Boltz run**: the whole real run at a glance — **~45+ complexes**, a **predicted-vs-measured scatter** (Pearson r shown) across 14 EGFR variants. *"This is the entire Boltz-2 run, every point blue=predicted against green=measured — you can see the pretrained head tracking reality."* Then **Single pair** / **WT vs mutant** for the per-pair and multi-variant views.

## 2:35 — 3:00 · Traceability + close
- **📚 Evidence Explorer** → Mutation = EGFR_C797S, Compound = osimertinib: every claim carries a clickable **PMID / DOI**. (Optional: **🧩 Structure Viewer** — real RCSB structure in live 3D; toggle **☀️ Light mode** to show both validated palettes.)
- **Close:** *"One Figma-designed instrument over four workstreams — dataset, Boltz prediction, cited evidence, and our own model. Every value is traceable and colour-coded by provenance; measured ≠ predicted ≠ model-written; anything untrained is mock and says so."*

---

## Guardrails while presenting
- Pairs **outside the real Boltz run** fall back to **placeholder** values, not predictions — badged red (⚠ MOCK). The real run (**~45+ complexes**) is badged blue (◈ PRETRAINED).
- The report is written by **our fine-tuned model** (✦); if the server is down it degrades to the grounded **template** (red) and says so — never silently.
- **Biochemical IC50 ≠ cellular ≠ clinical**; **IC50 ≠ KD ≠ Ki**.
- Score convention (shown on every prediction surface + sidebar): **affinity = log10(IC50 µM), lower = stronger, NOT pIC50** (1 nM→−3, 1 µM→0).

## Fallback
A pre-recorded screen capture of both hero flows is at **`demo_walkthrough.webm`** (app root) — play it if the live model/server is unavailable.

## Swapping the LLM to the Adaption hosted stack (often faster than local)
`export ADAPTION_API_KEY=… ADAPTION_STACK=<slug>` then `./run.sh` (takes precedence over the local endpoint).

## Pre-flight checklist
- [ ] `./run.sh` up with all env vars; http://localhost:8501 → 200.
- [ ] Sidebar **✅ integrity OK**; Boltz **◈ PRETRAINED**, LLM **✦ LLM REPORT**, Evidence **✓ REAL · CITED**.
- [ ] Both hero reports pre-generated (instant on stage).
- [ ] `.venv/bin/python tests/test_pages.py` → PASS.
