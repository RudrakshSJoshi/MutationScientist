# How We Used Figma — evidence (Best-Designed AI Product)

**One line:** the design's job is to make a scientific AI *trustworthy at a glance* — so provenance, not decoration, is the entire visual system. We call it the **Truth Ladder**.

### The design system (`figma-design/design-system.md` → realised in the app + deck)
- **Codename *Protein Lens*.** A dark, lab-instrument aesthetic (`--bg #0A0E17`), Inter for UI + **JetBrains Mono for every scientific value** (affinity, IC50, SMILES, PDB id) — monospacing *signals* "this is a measured/computed quantity, read it exactly."
- **The Truth Ladder — the signature.** Four provenance tiers, each shown as **dot + icon + UPPERCASE label** (never colour alone, so it's CVD-safe and AA-accessible):
  - 🧪 **MEASURED** (green `#0CA30C`) — observed/published truth
  - ◈ **PREDICTED** (blue `#3987E5`) — Boltz-2 affinity
  - ✦ **REASONED** (violet `#9085E9`) — the fine-tuned LLM's narrative
  - ⚠ **PLACEHOLDER** (red `#E05A5A`) — a stand-in, loud not hidden
- **"Discovery cyan"** (`#35C4E8`) is reserved for chrome (buttons, focus, nav) — deliberately *outside* the provenance hues so interface is never mistaken for data.

### The two design moves that sell the product
1. **Honest-empty-state as a *designed* state.** For the covalent C797S × osimertinib pair there is no fair Boltz prediction — so the UI shows a dignified "No Boltz complex for this pair — no prediction shown (nothing fabricated)", not a blank or a fake row. The honesty rule, made visible.
2. **The signature prediction-vs-experiment chart.** For L858R/C797S × BLU-945 (real `COMPLEX_001557`), a green **MEASURED** bar sits beside a blue **PREDICTED** bar, both direct-labelled, lower-is-stronger stated — the model and the lab, side by side.

### Why it's "best-designed"
- **Accessibility is built in, not bolted on:** body ≥ 4.5:1, UI ≥ 3:1 contrast; provenance never colour-alone; visible 2px focus ring; 40px hit targets; `prefers-color-scheme` + `prefers-reduced-motion` honoured (checklist in `design-system.md §7`).
- **One coherent system across surfaces:** the same tokens, pills and charts drive the Streamlit research app *and* this pitch deck — learn the legend once, trust the whole product.
- **The design encodes the ethics.** "Never fabricate" isn't a footnote; it's the visual grammar.

### Receipts
- `~/Desktop/figma-design/design-system.md` (full spec) · `~/Desktop/WIN/deck/index.html` (the system, live) · `~/Desktop/application/` (the research app using the same provenance badges).
