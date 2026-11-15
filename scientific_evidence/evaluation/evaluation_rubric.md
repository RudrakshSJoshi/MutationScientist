# EGFR MutationScientist — evaluation rubric

This rubric scores a model's free-text answer to each item in
`scientific_benchmark.jsonl`. It is **deterministic and citation-aware** (no
LLM-as-judge), so the same answer always gets the same score. Gold answers live
in `reference_answers.jsonl`; machine-checkable expectations live in the
benchmark file. The scorers are in `scorers.py` and are ported/extended from the
fine-tune harness `~/Desktop/EGFR_TRAINING/eval/eval_mutationscientist.py`.

## Independence

The benchmark is **independent of the SFT training data**: no `sft_train` prompt
is reused, and every gold value is taken from the curated source of truth
(`curated/affinity_measurements.csv`, Melis 2026 Table 2, Yun 2008,
`primary_evidence.jsonl`), never from a teacher-generated completion. The eval
seed pool (`eval_questions.jsonl`, `sft_test.csv`) only informed the task
taxonomy. Mutation-held-out splits (S768I, L861Q in test; T790M in validation)
are respected — gold is re-derived from primary data, not lifted from held-out
answers.

## Dimensions (per item)

| # | Dimension | How it is scored | Pass condition |
|---|-----------|------------------|----------------|
| 1 | **Factual correctness** | `required_facts` present (keywords and verified value+unit numbers); `forbidden_facts` absent | score == 1.0 (all required present, no over-claims) |
| 2 | **Evidence grounding / citation** | expected DOI/PMID/evidence_id cited; **any** DOI/PMID not in the curated corpus is flagged | expected citation present AND no invented citation |
| 3 | **Biochemical-vs-cellular distinction** | sentence-level flag for equating enzyme IC50 with cellular/clinical, or IC50/GI50 with KD/Ki, without distinguishing | no conflation flag |
| 4 | **Uncertainty calibration** | items marked `requires_hedge` must contain hedging/uncertainty language | hedging present where required |
| + | **Number grounding (cardinal)** | numeric+unit claims must be supported by the prompt/reference context | 0 ungrounded numbers |
| + | **Hedging detector** | keyword hedging signal (feeds dimension 4) | — |

An item **passes** only when all of: factual == 1.0, 0 fabricated numbers, no
invented citation, expected citation satisfied, no conflation, and calibration OK.

## Scoring bands (for human reporting)

- **Factual correctness** (mean over items): fraction of required facts recovered.
- **Fabrication rate**: share of items with >=1 ungrounded number **or** invented
  citation. The target is **0** — this is the project's cardinal rule.
- **Citation recall**: of items where a citation was expected, the share that cited
  at least one correct DOI/PMID/evidence_id.
- **Conflation rate**: share of items that mixed assay layers.
- **Calibration**: share of hedge-required items that hedged.

## Fabrication / invented-citation handling (hard rule)

A fabricated number or an invented DOI/PMID **always fails the item** and is
surfaced explicitly in `evaluation_report.md` and `report.json`. Nothing is
smoothed over. "Invented" means a citation-shaped token (DOI `10.x/...` or a PMID)
that does not occur anywhere in the curated corpus (`valid_citations.json`,
928 DOIs / 1171 PMIDs).

## Human review

For each flagged item, a domain reviewer should check `report.json` →
`items[].scores` for the exact `missed` facts, `ungrounded` numbers and
`invented_*` citations, compare against `reference_answers.jsonl`, and confirm
whether the model's answer is a true error or an acceptable paraphrase the rules
did not anticipate. Reference answers are written for human review as well as for
the dry-run self-test.

## Self-test guarantee

`run_benchmark.py --dry-run` feeds each reference answer back as the prediction
and must score **30/30 pass, 0 fabrications, 100% citation recall** — proving the
gold and the scorers are mutually consistent before any real model is graded.
