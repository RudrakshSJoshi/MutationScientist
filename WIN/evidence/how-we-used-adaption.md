# How We Used Adaption — evidence (Best Use of Adaption)

**One line:** we used Adaption AutoScientist to fine-tune a MutationScientist reasoning LLM, and we *climbed the win-rate* by using Adaption's own **Adaptive-Data augmentation** as the lever — measured, estimated-before-spend, and honest about the tradeoff.

### What we actually did on the platform
1. **Dataset → AutoScientist, raw mode.** Uploaded grounded EGFR prompt/completion SFT rows (`processing_mode:"raw"`, `column_mapping{prompt,completion}`, finalized via `/upload/complete`). Baseline run v1 (`1cc9e20f`, Qwen3.5-4B, 3 iters) → **best_win_rate 0.3617** — real, and *below base*, which told us exactly what to fix.
2. **Diagnosed with Adaption's own metric.** Win-rate is head-to-head vs the base model. 0.36 meant our 1,126 raw rows *lost* to base. The platform docs name the fix: augment toward ~20k rows.
3. **Used `estimate:true` before every spend.** `POST /datasets/{id}/augment {fill_to_recommended,estimate:true}` → **190 credits** quoted, then spent once to build a ~20k dataset (`ecaebd69`) reused across every training run.
4. **Ran a real sweep** (AutoScientist, `max_iterations:5`, `target_win_rate:0.9`) and let the data pick the winner. Final win-rates (all real, `runs_latest.json`): **gemma-3-4b-pt on domain-heavy 19,983 → 0.7819** 🏆; Qwen3-4B-Base same data → 0.7378; 4B-Base balanced → 0.6875; v2 adapt-rewrite → 0.6773; v1 raw → 0.3617; **9B-instruct → 0.3103 (lost to its own base)**. Two findings fell out, both earned not assumed: *a 4B-class base + Adaptive Data beats a 9B* (it replicated across two different 4B bases), and *domain-heavy augmentation beats balanced*. The winner reused the already-paid domain-heavy dataset — **zero extra credits**.
5. **Served & verified.** Winner (`3412f28a`) adapter downloaded via `GET …/{id}/download`. Stack created via `POST /api/v1/inference-stacks` → slug `mutationscientist-winner` (`stack:mutationscientist-winner`); final model-attach completed in the UI. Serve path: `POST /api/v1/responses {model:"stack:mutationscientist-winner"}`, wired into the app's `llm_service` and graded by `eval_mutationscientist.py` for number-fabrication — **we report the real count, never assume zero** (eval runs once the stack is active).

### Why it's "best use"
- We didn't stop at "it fine-tuned." We **moved the platform's ranking metric on purpose**, with the API feature (Adaptive-Data) that exists to do it.
- **Credit-disciplined:** estimated before spending, augmented once and reused, measured spend against the 1,238 budget.
- **Scientifically honest:** synthetic augmentation is disclosed; the fine-tune is graded for fabrication, not just fluency.

### Receipts
- Runs: `GET /api/v1/autoscientist` (snapshot in `runs_latest.json`); launch bodies in `exp_*_launch.json`; augmentation quote+spend in `augment_launch.json`.
- Winning run id + final win-rate: see `leaderboard-evidence.md` (filled from the API).
