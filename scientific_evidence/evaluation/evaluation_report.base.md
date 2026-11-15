# EGFR MutationScientist — independent evaluation report

- **Mode:** `real:openai`  
- **Model:** `Qwen/Qwen3.5-4B @ http://localhost:8000/v1`  
- **Items evaluated:** 30 (independent benchmark; gold sourced from curated evidence, not the SFT training rows)  
- **Overall pass rate:** 0.0% (0/30)  
- **Mean factual correctness:** 0.636  
- **Items with fabricated numbers:** 11  
- **Items with invented DOI/PMID citations:** 0  
- **Citation recall (where a citation was expected):** 0.0% over 29 items  
- **Biochemical/cellular conflation flags:** 5  
- **Hedging missing where required:** 0/16  
- **Mean token-overlap (Jaccard) vs reference:** 0.183

## Scoring dimensions

1. **Factual correctness** — fraction of each item's required facts present, minus over-claims.  
2. **Evidence grounding / citation** — expected DOI/PMID/evidence_id cited; any DOI/PMID not in the curated corpus is flagged as a potential fabrication.  
3. **Biochemical-vs-cellular distinction** — conflation of enzyme IC50 with cellular/clinical or with KD/Ki is flagged.  
4. **Uncertainty calibration** — items that demand hedging must express it.  
Plus two ported cardinal checks: **number grounding** (no fabricated values) and **hedging**.

## Per task_type

| task_type | n | pass | factual | fabricated# | invented-cite | cite-recall | conflation | hedge-missing | Jaccard |
|---|---|---|---|---|---|---|---|---|---|
| assay_distinction | 6 | 0/6 | 0.547 | 3 | 0 | 0% | 3 | 0/5 | 0.182 |
| evidence_qa | 6 | 0/6 | 0.528 | 0 | 0 | 0% | 0 | 0/1 | 0.141 |
| inhibitor_comparison | 6 | 0/6 | 0.793 | 2 | 0 | 0% | 0 | 0/5 | 0.228 |
| mutation_mechanism | 6 | 0/6 | 0.707 | 3 | 0 | 0% | 0 | 0/0 | 0.173 |
| resistance_interpretation | 6 | 0/6 | 0.607 | 3 | 0 | 0% | 2 | 0/5 | 0.190 |

## Flagged items (did not fully pass)

| id | task_type | factual | missed / issue |
|---|---|---|---|
| MM01 | mutation_mechanism | 0.78 | missing: all:covalent; any:acrylamide/thiol/anchor | missing expected citation |
| MM02 | mutation_mechanism | 0.75 | missing: all:gatekeeper; all:ATP | fabricated#: 50% | missing expected citation |
| MM03 | mutation_mechanism | 1.00 | fabricated#: 50% | missing expected citation |
| MM04 | mutation_mechanism | 0.50 | missing: all:746; all:activat; any:ELREA/E746 | fabricated#: 50%, 70% | missing expected citation |
| MM05 | mutation_mechanism | 0.50 | missing: any:exon-20/exon 20; any:atypical/uncommon; all:activating; all:variable | missing expected citation |
| MM06 | mutation_mechanism | 0.71 | missing: any:exon-21/exon 21; all:atypical | missing expected citation |
| RI01 | resistance_interpretation | 0.57 | missing: 2.82 nM; 574 nM; any:covalent/time-dependent | missing expected citation |
| RI02 | resistance_interpretation | 0.83 | missing: any:right-censored/censored/lower bound | fabricated#: 50%, 20 µM | missing expected citation |
| RI03 | resistance_interpretation | 0.43 | missing: all:covalent; any:reversible/allosteric; any:BLU-945/JBJ; any:requires measurement/still requires/measurement | missing expected citation | conflation |
| RI04 | resistance_interpretation | 0.67 | missing: any:broad/resistance | missing expected citation |
| RI05 | resistance_interpretation | 0.57 | missing: any:reversible/ATP-competitive; any:first-generation/1st-gen; all:gatekeeper | fabricated#: 100-fold | missing expected citation |
| RI06 | resistance_interpretation | 0.57 | missing: 91 fold; all:reversible; any:fourth-generation/4th-gen | fabricated#: 89-fold | missing expected citation | conflation |
| IC01 | inhibitor_comparison | 0.67 | missing: any:lower/stronger; all:allosteric | missing expected citation |
| IC02 | inhibitor_comparison | 1.00 | missing expected citation |
| IC03 | inhibitor_comparison | 0.80 | missing: any:context-dependent/depends/cannot be generalised/must be measured | fabricated#: 300-fold | missing expected citation |
| IC04 | inhibitor_comparison | 0.67 | missing: all:covalent; all:does not | missing expected citation |
| IC05 | inhibitor_comparison | 0.62 | missing: all:reversible; all:covalent; any:Cys797/acrylamide | missing expected citation |
| IC06 | inhibitor_comparison | 1.00 | fabricated#: 50%, 20 µM | missing expected citation |
| AD01 | assay_distinction | 0.75 | missing: any:ATP/substrate/assay format; any:time-dependent/covalent | missing expected citation |
| AD02 | assay_distinction | 0.33 | missing: 574 nM; 2950 nM; all:NCI-H1975; any:must not/different | fabricated#: 50%, 50% | missing expected citation | conflation |
| AD03 | assay_distinction | 0.71 | missing: all:osimertinib; any:requires_review/excluded/regression target | fabricated#: 50% | missing expected citation | conflation |
| AD04 | assay_distinction | 0.86 | missing: any:aggregat/median/inter-laboratory/protocol | fabricated#: 50% | missing expected citation | conflation |
| AD05 | assay_distinction | 0.12 | missing: all:log10(IC50; any:micromolar/uM/µM; all:lower; all:stronger |
| AD06 | assay_distinction | 0.50 | missing: any:header-only/cellular_assays; any:no-fabrication/must not/invented | missing expected citation |
| EQ01 | evidence_qa | 0.00 | missing: all:10.3389/fonc.2026.1952701; all:42835192 | missing expected citation |
| EQ02 | evidence_qa | 0.75 | missing: all:EVIDENCE_00001 | missing expected citation |
| EQ03 | evidence_qa | 0.67 | missing: any:EVIDENCE_00016/reversible | missing expected citation |
| EQ04 | evidence_qa | 0.75 | missing: all:EVIDENCE_00036 | missing expected citation |
| EQ05 | evidence_qa | 0.75 | missing: all:EVIDENCE_00031 | missing expected citation |
| EQ06 | evidence_qa | 0.25 | missing: any:must not/not invent; all:investigational; any:no randomized/no randomised/no clinical/no such trial | missing expected citation |

## How to re-run against a live model

```bash
# local OpenAI-compatible server (e.g. vLLM)
OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=sk-x OPENAI_MODEL=<name> \
  python -m scientific_evidence.evaluation.run_benchmark --backend openai

# Adaption hosted fine-tune (Responses API)
ADAPTION_API_KEY=... ADAPTION_STACK=<slug> \
  python -m scientific_evidence.evaluation.run_benchmark --backend adaption
```
