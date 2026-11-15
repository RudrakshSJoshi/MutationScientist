# EGFR MutationScientist — independent evaluation report

- **Mode:** `real:openai+rag`  
- **Model:** `mutationscientist @ http://localhost:8000/v1 (RAG/open-book)`  
- **Items evaluated:** 30 (independent benchmark; gold sourced from curated evidence, not the SFT training rows)  
- **Overall pass rate:** 16.7% (5/30)  
- **Mean factual correctness:** 0.653  
- **Items with fabricated numbers:** 4  
- **Items with invented DOI/PMID citations:** 1  
- **Citation recall (where a citation was expected):** 79.3% over 29 items  
- **Biochemical/cellular conflation flags:** 2  
- **Hedging missing where required:** 1/16  
- **Mean token-overlap (Jaccard) vs reference:** 0.294

## Scoring dimensions

1. **Factual correctness** — fraction of each item's required facts present, minus over-claims.  
2. **Evidence grounding / citation** — expected DOI/PMID/evidence_id cited; any DOI/PMID not in the curated corpus is flagged as a potential fabrication.  
3. **Biochemical-vs-cellular distinction** — conflation of enzyme IC50 with cellular/clinical or with KD/Ki is flagged.  
4. **Uncertainty calibration** — items that demand hedging must express it.  
Plus two ported cardinal checks: **number grounding** (no fabricated values) and **hedging**.

## Per task_type

| task_type | n | pass | factual | fabricated# | invented-cite | cite-recall | conflation | hedge-missing | Jaccard |
|---|---|---|---|---|---|---|---|---|---|
| assay_distinction | 6 | 0/6 | 0.559 | 1 | 1 | 60% | 1 | 0/5 | 0.212 |
| evidence_qa | 6 | 3/6 | 0.667 | 0 | 0 | 67% | 1 | 1/1 | 0.255 |
| inhibitor_comparison | 6 | 1/6 | 0.668 | 2 | 0 | 83% | 0 | 0/5 | 0.336 |
| mutation_mechanism | 6 | 1/6 | 0.718 | 0 | 0 | 100% | 0 | 0/0 | 0.346 |
| resistance_interpretation | 6 | 0/6 | 0.655 | 1 | 0 | 83% | 0 | 0/5 | 0.323 |

## Flagged items (did not fully pass)

| id | task_type | factual | missed / issue |
|---|---|---|---|
| MM02 | mutation_mechanism | 0.62 | missing: all:threonine/Thr; all:methionine/Met; all:ATP |
| MM03 | mutation_mechanism | 0.71 | missing: all:leucine/Leu; all:arginine/Arg |
| MM04 | mutation_mechanism | 0.67 | missing: all:746; any:ELREA/E746 |
| MM05 | mutation_mechanism | 0.88 | missing: any:exon-20/exon 20 |
| MM06 | mutation_mechanism | 0.43 | missing: all:leucine/Leu; all:glutamine/Gln; any:exon-21/exon 21; all:atypical |
| RI01 | resistance_interpretation | 0.86 | missing: any:covalent/time-dependent | missing expected citation |
| RI02 | resistance_interpretation | 0.83 | missing: any:right-censored/censored/lower bound |
| RI03 | resistance_interpretation | 0.43 | missing: all:serine/Ser; any:reversible/allosteric; any:BLU-945/JBJ; any:requires measurement/still requires/measurement |
| RI04 | resistance_interpretation | 0.67 | missing: any:not determined/n.d./not available |
| RI05 | resistance_interpretation | 0.43 | missing: all:gefitinib; any:reversible/ATP-competitive; any:first-generation/1st-gen; all:ATP |
| RI06 | resistance_interpretation | 0.71 | missing: 91 fold; any:fourth-generation/4th-gen | fabricated#: 91x |
| IC01 | inhibitor_comparison | 0.67 | missing: any:lower/stronger; all:allosteric |
| IC02 | inhibitor_comparison | 0.20 | missing: 86.0 nM; 18 fold; any:mutant-selectiv/selectivity; all:does not | fabricated#: 18x | missing expected citation |
| IC03 | inhibitor_comparison | 0.60 | missing: any:context-dependent/depends/cannot be generalised/must be measured; any:right-censored/censored/inactive |
| IC04 | inhibitor_comparison | 0.67 | missing: 680 fold; all:covalent | fabricated#: 680x |
| IC05 | inhibitor_comparison | 0.88 | missing: any:third-generation/3rd-gen |
| AD01 | assay_distinction | 0.50 | missing: any:equilibrium/dissociation constant; any:ATP/substrate/assay format; any:time-dependent/covalent; any:separate/distinct/not pooled | invented-cite: 10.1021/acscentsci.6c01666 | missing expected citation |
| AD02 | assay_distinction | 0.50 | missing: 574 nM; 2950 nM; all:NCI-H1975 | fabricated#: 11.6 nM |
| AD03 | assay_distinction | 0.86 | missing: any:requires_review/excluded/regression target |
| AD04 | assay_distinction | 1.00 | conflation |
| AD05 | assay_distinction | 0.25 | missing: all:log10(IC50; all:lower; all:stronger; any:not pic50 |
| AD06 | assay_distinction | 0.25 | missing: any:header-only/cellular_assays; any:not acquired/supplementary/not available; any:no-fabrication/must not/invented | missing expected citation |
| EQ01 | evidence_qa | 1.00 | conflation |
| EQ05 | evidence_qa | 0.00 | missing: any:atypical/uncommon; all:activating; any:S768I/L861Q/G719; all:EVIDENCE_00031 | missing expected citation |
| EQ06 | evidence_qa | 0.00 | missing: any:must not/not invent; all:BLU-945; all:investigational; any:no randomized/no randomised/no clinical/no such trial | missing expected citation | no hedging |

## How to re-run against a live model

```bash
# local OpenAI-compatible server (e.g. vLLM)
OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=sk-x OPENAI_MODEL=<name> \
  python -m scientific_evidence.evaluation.run_benchmark --backend openai

# Adaption hosted fine-tune (Responses API)
ADAPTION_API_KEY=... ADAPTION_STACK=<slug> \
  python -m scientific_evidence.evaluation.run_benchmark --backend adaption
```
