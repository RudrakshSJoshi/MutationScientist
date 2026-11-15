# MutationScientist — 60–90s Live Demo Script

**Product:** MutationScientist / *Protein Lens* — EGFR mutation-to-mechanism explainer
**Loop shown:** real Boltz-2 prediction → interpreted by the Adaption-fine-tuned MutationScientist LLM → spoken by an Anam avatar, every number wearing its source.

> Timing target: 75s. Numbers in **[MEASURED]** are real curated IC50s; **[PREDICTED]** are real Boltz-2 outputs; the LLM narration is **[REASONED]**. Nothing is invented on stage.

---

### [0:00–0:12] The question (hook)
**On screen:** MutationScientist home, dark lab-instrument UI. The Anam avatar "Dr. Mutasci" is live.
**Presenter (to the avatar):** *"A patient on osimertinib just progressed. Did the C797S mutation break the drug?"*

### [0:12–0:35] The honest answer (the integrity beat)
**Avatar speaks (grounded):** *"Osimertinib is a covalent inhibitor — it bonds to cysteine 797. C797S removes that cysteine, so the covalent mechanism is lost. We don't show a Boltz affinity here because a covalent warhead isn't a fair target for the affinity head — and we won't fabricate one."*
**On screen:** the **honest-empty-state** panel lights up: *"No Boltz complex for this pair — no prediction shown."* Beside it, the **MEASURED** evidence: IC50 **2.82 nM** (L858R) → **574 nM** (L858R/C797S), with cited sources.
**Beat:** *"That jump is real, and it's measured — not predicted."*

### [0:35–1:00] Closing the loop (prediction × reasoning)
**Presenter:** *"Then what should we reach for instead?"*
**On screen:** switch to the **L858R/C797S × BLU-945** pair. The signature **green-vs-blue** chart appears.
**Avatar speaks:** *"BLU-945 is a fourth-generation, non-covalent inhibitor. Boltz-2 predicts an affinity of **−1.36 log10 IC50 µM** — lower is stronger — and the curated measurements agree: **6.32 nM** against the resistant triple mutant."*
**Beat:** The chart shows **PREDICTED** (blue) beside **MEASURED** (green) — the model and the lab lining up.

### [1:00–1:15] Why you can trust it
**On screen:** the **Truth Ladder** legend overlays — green MEASURED, blue PREDICTED, violet REASONED, red PLACEHOLDER.
**Presenter:** *"Every sentence the model just spoke is grounded in that curated dataset, and our Adaption fine-tune beats the base model head-to-head — with zero number-fabrication on our eval. This is a research instrument you can put in front of an oncologist."*

---

## Shot list / fallback
- **Primary:** live Anam avatar + live app. Mic-permission granted beforehand.
- **Fallback A (no network for Anam):** pre-recorded 20s avatar clip + live app.
- **Fallback B (app only):** click the two hero flows in the app; presenter narrates the avatar lines.
- The two hero pairs are one-click presets in **Molecular Screening** / **MutationScientist Report**.

## Hard honesty rules on stage
- Covalent pair shows **no prediction** by design — say so out loud; it is the integrity proof, not a bug.
- Never read a MOCK value as real. If `boltz_service` is still MOCK for a pair, the ⚠ badge is visible — don't cite that number.
- Win-rate quoted on stage must match the Adaption API (see `evidence/leaderboard-evidence.md`).
