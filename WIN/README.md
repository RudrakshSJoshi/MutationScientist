# MutationScientist / Protein Lens — Hackathon win kit

Two prizes, two evidenced stories.

## 🏆 Best Use of Adaption — we climbed the win-rate on purpose
- **0.3617 → 0.7378** head-to-head win-rate vs base (above the 0.70 goal).
- **Winner:** run `4c86594f` — `Qwen/Qwen3-4B-Base` + domain-heavy Adaptive-Data augmentation (19,983 rows). LoRA r=32, α=64.
- Two findings the sweep *proves* (not assumes):
  1. **Pretrained-base beats instruct** as the win-rate target — the 9B *instruct* model **lost** (0.3103); the 4B-**Base** models won (0.69–0.74).
  2. **Domain-heavy augmentation > balanced** — same base, same ~20k volume: 0.7378 vs 0.6875.
- Every number is from `GET /api/v1/autoscientist` (snapshot: [`evidence/runs_latest.json`](evidence/runs_latest.json)).
- Credit-disciplined: augmentation estimated before every spend, augmented once and reused, 300-credit reserve kept. See [`evidence/spend-ledger.md`](evidence/spend-ledger.md).
- Full write-up: [`evidence/leaderboard-evidence.md`](evidence/leaderboard-evidence.md) · [`evidence/how-we-used-adaption.md`](evidence/how-we-used-adaption.md)

## 🎨 Best-Designed AI Product — the Truth Ladder
Provenance is a first-class visual citizen: a **measured** number, a **predicted** value, a **reasoned** sentence and a **placeholder** are never styled the same. The design *is* the integrity story. See [`evidence/how-we-used-figma.md`](evidence/how-we-used-figma.md).

## Contents
- [`deck/index.html`](deck/index.html) — self-contained 6-slide pitch deck (keyboard nav; win-rate chart is data-bound to the real API numbers).
- [`demo-script.md`](demo-script.md) · [`run-of-show.md`](run-of-show.md) — the live demo + 3-minute run of show.
- [`visuals/hero.png`](visuals/hero.png) — hero visual.
- `evidence/` — API snapshots, launch bodies, the orchestration method, and the four evidence write-ups.

> The 235 MB winning adapter (`winner_model.zip`) is intentionally **not** committed. Reproduce via `GET /api/v1/autoscientist/4c86594f-c4d7-4d9b-925e-47bfb3d84850/download`.
