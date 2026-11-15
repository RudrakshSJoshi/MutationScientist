# EGFR MutationScientist — independent evaluation report

- **Mode:** `dry-run`  
- **Model:** `reference-as-prediction`  
- **Items evaluated:** 30 (independent benchmark; gold sourced from curated evidence, not the SFT training rows)  
- **Overall pass rate:** 100.0% (30/30)  
- **Mean factual correctness:** 1.000  
- **Items with fabricated numbers:** 0  
- **Items with invented DOI/PMID citations:** 0  
- **Citation recall (where a citation was expected):** 100.0% over 29 items  
- **Biochemical/cellular conflation flags:** 0  
- **Hedging missing where required:** 0/16  
- **Mean token-overlap (Jaccard) vs reference:** 1.000

## Scoring dimensions

1. **Factual correctness** — fraction of each item's required facts present, minus over-claims.  
2. **Evidence grounding / citation** — expected DOI/PMID/evidence_id cited; any DOI/PMID not in the curated corpus is flagged as a potential fabrication.  
3. **Biochemical-vs-cellular distinction** — conflation of enzyme IC50 with cellular/clinical or with KD/Ki is flagged.  
4. **Uncertainty calibration** — items that demand hedging must express it.  
Plus two ported cardinal checks: **number grounding** (no fabricated values) and **hedging**.

## Per task_type

| task_type | n | pass | factual | fabricated# | invented-cite | cite-recall | conflation | hedge-missing | Jaccard |
|---|---|---|---|---|---|---|---|---|---|
| assay_distinction | 6 | 6/6 | 1.000 | 0 | 0 | 100% | 0 | 0/5 | 1.000 |
| evidence_qa | 6 | 6/6 | 1.000 | 0 | 0 | 100% | 0 | 0/1 | 1.000 |
| inhibitor_comparison | 6 | 6/6 | 1.000 | 0 | 0 | 100% | 0 | 0/5 | 1.000 |
| mutation_mechanism | 6 | 6/6 | 1.000 | 0 | 0 | 100% | 0 | 0/0 | 1.000 |
| resistance_interpretation | 6 | 6/6 | 1.000 | 0 | 0 | 100% | 0 | 0/5 | 1.000 |

## Flagged items (did not fully pass)

_None — every item passed all dimensions._

## How to re-run against a live model

```bash
# local OpenAI-compatible server (e.g. vLLM)
OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=sk-x OPENAI_MODEL=<name> \
  python -m scientific_evidence.evaluation.run_benchmark --backend openai

# Adaption hosted fine-tune (Responses API)
ADAPTION_API_KEY=... ADAPTION_STACK=<slug> \
  python -m scientific_evidence.evaluation.run_benchmark --backend adaption
```
