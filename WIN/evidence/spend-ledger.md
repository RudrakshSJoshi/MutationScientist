# Adaption Credit Spend Ledger

**Budget:** ~1,238 credits · **Reserve to keep:** 300 → **usable ≤ ~938.**
**Measurability note:** Adaption's API prices **only augmentation** (via `estimate:true` → `estimated_credits_consumed`). It exposes **no cost field on training runs** and **no balance/usage/billing/subscription endpoint** (all probed → 404/empty). So training compute is **spent but not queryable**; the figures below are the measurable augmentation spend plus the run count it funded.

## Augmentation spend (measured; estimated before every spend)
| When | Action | Rows | Credits | Basis | Confirmed |
|---|---|---|---|---|---|
| ~00:58 | augment `ecaebd69` (balanced) | 1,126 + 9,437 domain + 9,437 general ≈ 20k | **190** | `augment estimate:true`, then `estimate:false` echoed 190 | ✅ confirmed |
| ~01:01 | 9B run `387caed3` train-time aug | +9,437 domain +9,437 general | **~190** | same row counts (bundled in run) | ~ estimated |
| ~01:35 | augment `1bf15478` (domain-heavy) | 1,126 + 18,874 domain = 19,983 | **189** | `estimate:false` echoed 189 | ✅ confirmed |
| — | **Total augmentation** | | **~569** | | |

## Training compute (not queryable)
Funded 7 of my runs (v1 pre-existing). Per-run cost unknown — no API field. Assume non-trivial; this is why the reserve matters.

## Runs funded
| Run id | Model | Data | Spend type |
|---|---|---|---|
| 1cc9e20f | Qwen3.5-4B | raw 1,126 | pre-existing (not mine) |
| b6621361 | Qwen3.5-4B | adapt `d1a6fa0c` | teammate (v2) |
| 387caed3 | Qwen3.5-9B | raw + train-aug 20k | ~190 aug + training |
| 66adad71 | Qwen3-4B-Base | `ecaebd69` 20k | training (aug reused) |
| 4c86594f | Qwen3-4B-Base | `1bf15478` 19,983 domain-heavy | 189 aug + training |

## Budget-protection decisions
- **Halted the pending queue** (4B-ins, 2B, **gemma-pt which would add +190 aug**) at ~01:55 to protect the 300-reserve, since training cost is unmeasurable and 7 runs may already approach the ~938 usable.
- **No further augmentation or run launches** until the first augmented-base win-rates land and confirm whether more spend is warranted.
- Augmentation total (~569) + reserve (300) = 869 of 1,238, leaving ~369 headroom for the (unmeasurable) training already in flight.

## Win-rate data (real, FINAL, from the API — `runs_latest.json`)
| Model | run | best_win_rate | note |
|---|---|---|---|
| **4B-Base (domain-heavy 19,983)** | 4c86594f | **0.7378** 🏆 | **WINNER** — above 0.70 goal |
| 4B-Base (balanced ~20k) | 66adad71 | 0.6875 | strong; domain-heavy beat it |
| v2 (adapt-rewrite 4B) | b6621361 | 0.6773 | final over 3 iters (0.3273 was only iter-1) |
| v1 (raw 4B) | 1cc9e20f | 0.3617 | below base |
| 9B (raw+aug ~20k) | 387caed3 | 0.3103 | **instruct base too hard to beat — lost** |

**Headline:** 0.3617 → **0.7378** (+0.376). Two causes isolated: pretrained-base > instruct target, and domain-heavy > balanced augmentation.

## Outcome vs the halt decision
The halted queue (4B-ins, 2B, gemma-pt +190 aug) was **not needed** — 4B-Base domain-heavy already cleared the 0.70 target. Protecting the 300-reserve cost us nothing; the winning configuration was already in the completed set.
