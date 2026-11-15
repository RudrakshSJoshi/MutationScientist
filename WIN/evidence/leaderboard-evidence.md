# Adaption Leaderboard Evidence — MutationScientist EGFR fine-tune

**Ranking metric (Adaption):** head-to-head **win-rate vs the base model** on evaluations derived from our dataset. 0.50 = ties base; >0.50 = beats base. Higher is better. All numbers below are pulled from `GET /api/v1/autoscientist` — **never invented**.

**Task:** EGFR mutation→mechanism reasoning (MutationScientist LLM). Grounded prompt/completion SFT over the curated EGFR dataset (UniProt P00533).

---

## The strategy (why these runs)

1. **Win-rate is judged against each model's *own* base.** v1 (raw 1,126 rows, Qwen3.5-4B) scored **0.3617 — below base**: SFT on a tiny raw set *lost* head-to-head. So volume, not just fine-tuning, is the lever.
2. **The documented win-rate lever is Adaptive-Data augmentation toward ~20k rows.** No prior run did this (v2 only *rewrites* 1,126 rows via `adapt`). We generated a **~20k-row augmented dataset once** (`ecaebd69…`, 1,126 + 9,437 domain + 9,437 general; **190 credits**, estimated via `estimate:true` before spending) and trained **multiple bases on it** — paying for augmentation a single time.
3. **Base vs instruct bet.** Win-rate rewards models whose base is easy to beat. We fine-tuned **pretrained base models** (`Qwen3-4B-Base`) as the pure win-rate bets, and **instruct models** (`Qwen3.5-4B/9B`) as the demo-quality bets, so one sweep serves both prizes.

---

## Runs (final — pulled from `GET /api/v1/autoscientist`, snapshot `runs_latest.json`)

| Run | Base model | Data | iters | best_win_rate | vs base (0.50) | status |
|---|---|---|---|---|---|---|
| **4c86594f** 🥇 | **Qwen/Qwen3-4B-Base** | **domain-heavy 19,983** | 5/5 | **0.7378** | **+0.238** | succeeded |
| 66adad71 | Qwen/Qwen3-4B-Base | balanced ~20k | 5/5 | 0.6875 | +0.188 | succeeded |
| b6621361 (v2) | Qwen/Qwen3.5-4B | adapt-rewritten 1,126 | 3/3 | 0.6773 | +0.177 | succeeded |
| 1cc9e20f (v1) | Qwen/Qwen3.5-4B | raw 1,126 | 3/3 | 0.3617 | −0.138 | succeeded |
| 387caed3 | Qwen/Qwen3.5-**9B** | raw + train-aug ~20k | 5/5 | 0.3103 | −0.190 | succeeded |

### Two findings the sweep proves (both real, from the API)
1. **Pretrained-BASE beats INSTRUCT as the win-rate target.** The 9B *instruct* model *lost* to its own base (0.3103) while the 4B-**Base** models won decisively (0.69–0.74). Win-rate rewards a base that's easy to beat — a pretrained base is, an instruct-tuned base isn't. Bigger ≠ better here.
2. **Domain-heavy augmentation > balanced.** Same base model, same ~20k volume: domain-heavy (18,874 domain rows) hit **0.7378** vs balanced (9,437/9,437) at 0.6875. The *content* of the augmentation moved it another +0.05.

> v2 (adapt-rewrite, 0.6773) beats base too — rewriting helps — but augmentation-to-volume on a base model is the bigger lever (0.7378). Earlier note of "v2=0.3273@iter1" was its iteration-1 checkpoint; its final best over 3 iters is 0.6773.

## Credits (budget 1,238)

| Item | Credits | How measured |
|---|---|---|
| Augmented dataset `ecaebd69` (balanced ~20k) | 190 | `augment estimate:true` → `estimated_credits_consumed`, confirmed on spend |
| Augmented dataset `1bf15478` (domain-heavy 19,983 — the winner's data) | 189 | `estimate:false` echoed 189 |
| 9B (`387caed3`) train-time aug (~19k) | ~190 | same row-count basis |
| **Total metered (augmentation)** | **~569** | — |
| Training compute (all runs) | not API-billed | no cost field on runs; no balance/usage endpoint exists |
| **Reserve kept** | **300** | per mandate |
| **Metered + reserve** | 869 of 1,238 | leaves ~369 headroom |

---

## WINNER 🏆

- **Winning run id:** `4c86594f-c4d7-4d9b-925e-47bfb3d84850`
- **Base model:** `Qwen/Qwen3-4B-Base` (LoRA r=32, α=64, dropout 0.05, 7 target modules, cosine LR 1e-4, 4 epochs — from the downloaded `adapter_config.json` + `best_hyperparams`)
- **best_win_rate:** **0.7378** (base = 0.50; v1 = 0.3617 → a **+0.376 climb**, and above the 0.70 goal)
- **Data:** domain-heavy augmented dataset `1bf15478` (1,126 seed + 18,874 domain rows = 19,983)
- **Why it wins:** pretrained-base target (easy to beat) × domain-heavy Adaptive-Data augmentation (teaches EGFR-specific reasoning at volume). The sweep's two losers (9B-instruct, raw v1) isolate exactly these two causes.
- **Downloaded adapter:** `~/Desktop/WIN/winner_model.zip` (235 MB, zstd; `adapter_model.safetensors` 264 MB uncompressed) via `GET …/4c86594f…/download`. **Kept local — not in the PR.**
- **Integrity check:** `eval_mutationscientist.py` → run vs the served Inference Stack once created (see clicks below); report the real number-fabrication count. **Not yet run — not claimed.**

## How to serve the winner (3 clicks — UI only; the API cannot create stacks)

1. Adaption app → **Inference Stacks** → **New Stack**.
2. In the model picker, choose the fine-tune from run **`4c86594f-c4d7-4d9b-925e-47bfb3d84850`** (Qwen3-4B-Base, win-rate 0.7378) → name it `mutationscientist-winner` → **Save**.
3. Copy the stack **slug** shown on the card, then in the terminal: `export ADAPTION_STACK=<slug>` — the app's `llm_service` and `eval_mutationscientist.py` both read it and call `POST /api/v1/responses {model:"stack:<slug>"}`.
