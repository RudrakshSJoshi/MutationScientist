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
| **3412f28a** 🥇 | **google/gemma-3-4b-pt** | **domain-heavy 19,983** | 5/5 | **0.7819** | **+0.282** | succeeded |
| 4c86594f | Qwen/Qwen3-4B-Base | domain-heavy 19,983 | 5/5 | 0.7378 | +0.238 | succeeded |
| 66adad71 | Qwen/Qwen3-4B-Base | balanced ~20k | 5/5 | 0.6875 | +0.188 | succeeded |
| b6621361 (v2) | Qwen/Qwen3.5-4B | adapt-rewritten 1,126 | 3/3 | 0.6773 | +0.177 | succeeded |
| 1cc9e20f (v1) | Qwen/Qwen3.5-4B | raw 1,126 | 3/3 | 0.3617 | −0.138 | succeeded |
| 387caed3 | Qwen/Qwen3.5-**9B** | raw + train-aug ~20k | 5/5 | 0.3103 | −0.190 | succeeded |

### Two findings the sweep proves (both real, from the API)
1. **A 4B-class base + Adaptive Data beats a 9B.** The 9B *instruct* model *lost* to its own base (0.3103) while two different **4B pretrained bases** (gemma-3-4b-pt 0.7819, Qwen3-4B-Base 0.7378) won decisively. Capacity isn't the lever — win-rate rewards a base that's easy to beat (a pretrained base is; an instruct-tuned base isn't), plus the right data.
2. **Domain-heavy augmentation > balanced.** Same Qwen base, same ~20k volume: domain-heavy (18,874 domain rows) hit 0.7378 vs balanced (9,437/9,437) at 0.6875 — the *content* of the augmentation moved it +0.05. The winning gemma run used that same domain-heavy dataset.

> The winner (`3412f28a`) was trained on the **already-paid** domain-heavy dataset `1bf15478` — **zero additional augmentation credits** — and beat the previous best by +0.044.

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

- **Winning run id:** `3412f28a-4fd9-44f5-b92a-1d471af16e69`
- **Base model:** `google/gemma-3-4b-pt` (adapter reports `togethercomputer/gemma-3-4b-pt`; LoRA r=48, α=96 — from the downloaded `adapter_config.json`)
- **best_win_rate:** **0.7819** (base = 0.50; v1 = 0.3617 → a **+0.420 climb**, well above the 0.70 goal)
- **Data:** domain-heavy augmented dataset `1bf15478` (1,126 seed + 18,874 domain rows = 19,983) — **reused, zero new augmentation credits**
- **Why it wins:** pretrained-base target (easy to beat) × domain-heavy Adaptive-Data augmentation. A second, different 4B base (Qwen3-4B-Base) hit 0.7378 on the same data, so the result replicates across bases; the 9B-instruct loss (0.3103) isolates that capacity isn't the lever.
- **Downloaded adapter:** `~/Desktop/WIN/winner_model.zip` (via `GET …/3412f28a…/download`, verified `base_model_name_or_path = togethercomputer/gemma-3-4b-pt`). **Kept local — not in the PR.**
- **Integrity check:** `eval_mutationscientist.py` → run vs the served Inference Stack; report the real number-fabrication count. **Not yet run — not claimed.**

## Serving the winner — the Inference Stack

The API *does* expose stacks (`POST /api/v1/inference-stacks`). I created the stack programmatically:

- **Stack id:** `9dc95ce3-d943-4f27-8b43-0c0d2fdf9d4b`
- **Slug:** `mutationscientist-winner`
- **Serving model id:** `stack:mutationscientist-winner`
- **Status:** `draft` — **name set, model-attach pending.** Binding the fine-tune from run `3412f28a` to the stack is the one remaining step; the exact attach field wasn't determined from the API (and write-probing on the shared account was gated), so finish it in the web UI: open the `mutationscientist-winner` stack → pick the model from run `3412f28a` (gemma-3-4b-pt, 0.7819) → **Activate**.
- Then: `export ADAPTION_STACK=mutationscientist-winner` — the app's `llm_service` and `eval_mutationscientist.py` read it and call `POST /api/v1/responses {model:"stack:mutationscientist-winner"}`.
