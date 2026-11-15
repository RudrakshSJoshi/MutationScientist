# 3-Minute Pitch — Run of Show

**Team:** MutationScientist / *Protein Lens* · Imperial AI Hackathon
**Prizes targeted:** Best Use of Adaption (win-rate leaderboard) · Best-Designed AI Product (Figma)
**Roles:** Presenter (drives story) · Driver (clicks app/avatar). One laptop, deck + app + avatar pre-opened in three tabs.

| Time | Slide / Screen | Presenter says (beats) | Driver does |
|---|---|---|---|
| **0:00–0:25** | Deck S1 (title) → S2 (problem) | "EGFR mutations are why targeted lung-cancer drugs stop working. A researcher's real question: *will drug Y still bind mutant X — and can I trust the answer?*" | Deck on S2 |
| **0:25–0:55** | Deck S3 (two-model system) | "We built a mutation-to-mechanism engine: **Boltz-2** predicts binding, a **fine-tuned MutationScientist LLM** reasons over curated *measured* data, and an **Anam avatar** speaks it. Prediction, measurement, reasoning — never confused." | Advance to S3 (system diagram) |
| **0:55–1:25** | Deck S4 (Adaption result) | "On Adaption's leaderboard, our fine-tune beats the base model head-to-head: **[WIN-RATE]** win-rate, up from a 0.36 raw baseline — the lift came from Adaptive-Data augmentation to ~20k rows. And our eval shows **zero number-fabrication**." | Advance to S4 (leaderboard chart) |
| **1:25–2:40** | **LIVE** app + avatar | Run `demo-script.md`: covalent C797S×osimertinib honest-empty-state + real IC50 jump → BLU-945 real Boltz prediction vs experiment. | Switch to app tab; click the 2 presets; avatar speaks |
| **2:40–3:00** | Deck S5 (why we win) | "Adaption: a real, evidenced win-rate climb. Figma: the **Truth Ladder** — provenance as a first-class visual citizen, an honest-by-construction research instrument. That's how we win both." | Advance to S5 (Truth Ladder + two-prize close) |

## Pre-flight checklist (run 10 min before)
- [ ] App live: `cd ~/Desktop/application && ./run.sh` → http://localhost:8501 (HTTP 200)
- [ ] Avatar live: `cd ~/Desktop/anam-explainer && npm start` → http://localhost:3000, mic allowed
- [ ] `boltz_service` pointed at real predictions if `boltz_predictions.json` is ready (`BOLTZ_PREDICTIONS_PATH`); otherwise the ⚠ MOCK badge is honest and fine
- [ ] `llm_service` pointed at the winning fine-tune (`ADAPTION_API_KEY` + `ADAPTION_STACK=<slug>`)
- [ ] Deck open at S1 in a separate tab; laptop on mains; network check for Anam
- [ ] Win-rate on S4 matches `evidence/leaderboard-evidence.md` exactly
- [ ] **Avatar grounding:** the avatar must speak from structured context only — never free-chat the raw model (it hallucinates, e.g. C797S → "position 179"). Server falls back to a "general" pack and refuses if none. Drive it with the two preset questions, not open Q&A.

## The two sentences that win each prize (say them)
- **Adaption:** "We didn't just fine-tune — we *climbed*: base → **[WIN-RATE]** head-to-head, and we can show the credits, the runs, and the augmentation lever that moved it."
- **Figma:** "Our design signature is the **Truth Ladder** — a measured number, a model prediction, an LLM sentence and a placeholder are never styled the same. The design *is* the integrity story."
