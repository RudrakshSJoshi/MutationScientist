# EGFR MutationScientist — independent evaluation report

- **Mode:** `real:openai`  
- **Model:** `/Users/home/Desktop/EGFR_TRAINING/mlx_model @ http://localhost:8000/v1`  
- **Items evaluated:** 30 (independent benchmark; gold sourced from curated evidence, not the SFT training rows)  
- **Overall pass rate:** 0.0% (0/30)  
- **Mean factual correctness:** 0.555  
- **Items with fabricated numbers:** 6  
- **Items with invented DOI/PMID citations:** 9  
- **Citation recall (where a citation was expected):** 0.0% over 29 items  
- **Biochemical/cellular conflation flags:** 0  
- **Hedging missing where required:** 3/16  
- **Mean token-overlap (Jaccard) vs reference:** 0.231

## Scoring dimensions

1. **Factual correctness** — fraction of each item's required facts present, minus over-claims.  
2. **Evidence grounding / citation** — expected DOI/PMID/evidence_id cited; any DOI/PMID not in the curated corpus is flagged as a potential fabrication.  
3. **Biochemical-vs-cellular distinction** — conflation of enzyme IC50 with cellular/clinical or with KD/Ki is flagged.  
4. **Uncertainty calibration** — items that demand hedging must express it.  
Plus two ported cardinal checks: **number grounding** (no fabricated values) and **hedging**.

## Per task_type

| task_type | n | pass | factual | fabricated# | invented-cite | cite-recall | conflation | hedge-missing | Jaccard |
|---|---|---|---|---|---|---|---|---|---|
| assay_distinction | 6 | 0/6 | 0.529 | 2 | 1 | 0% | 0 | 1/5 | 0.207 |
| evidence_qa | 6 | 0/6 | 0.528 | 1 | 6 | 0% | 0 | 0/1 | 0.224 |
| inhibitor_comparison | 6 | 0/6 | 0.681 | 2 | 0 | 0% | 0 | 1/5 | 0.286 |
| mutation_mechanism | 6 | 0/6 | 0.616 | 0 | 2 | 0% | 0 | 0/0 | 0.259 |
| resistance_interpretation | 6 | 0/6 | 0.425 | 1 | 0 | 0% | 0 | 1/5 | 0.180 |

## Flagged items (did not fully pass)

| id | task_type | factual | missed / issue |
|---|---|---|---|
| MM01 | mutation_mechanism | 0.78 | missing: all:serine/Ser; all:osimertinib | invented-cite: 10.1038/s41586-026-0766-9 | missing expected citation |
| MM02 | mutation_mechanism | 0.88 | missing: any:first- and second-generation/first-generation/1st/2nd/second-generation | invented-cite: 10.1158/1535-7163.mct-25-1046 | missing expected citation |
| MM03 | mutation_mechanism | 0.57 | missing: all:leucine/Leu; all:arginine/Arg; all:sensiti | missing expected citation |
| MM04 | mutation_mechanism | 0.67 | missing: all:746; any:ELREA/E746 | missing expected citation |
| MM05 | mutation_mechanism | 0.38 | missing: all:serine/Ser; all:isoleucine/Ile; any:exon-20/exon 20; any:atypical/uncommon | missing expected citation |
| MM06 | mutation_mechanism | 0.43 | missing: all:leucine/Leu; all:glutamine/Gln; any:exon-21/exon 21; all:atypical | missing expected citation |
| RI01 | resistance_interpretation | 0.71 | missing: all:biochemical; any:covalent/time-dependent | missing expected citation |
| RI02 | resistance_interpretation | 0.83 | missing: any:right-censored/censored/lower bound | missing expected citation |
| RI03 | resistance_interpretation | 0.43 | missing: all:serine/Ser; any:reversible/allosteric; any:BLU-945/JBJ; any:requires measurement/still requires/measurement | missing expected citation |
| RI04 | resistance_interpretation | 0.00 | missing: any:L858R/T790M/C797S/triple; any:not determined/n.d./not available; any:broad/resistance | missing expected citation | no hedging |
| RI05 | resistance_interpretation | 0.00 | missing: all:gefitinib; any:reversible/ATP-competitive; any:first-generation/1st-gen; all:T790M | missing expected citation |
| RI06 | resistance_interpretation | 0.57 | missing: 91 fold; all:reversible; any:fourth-generation/4th-gen | fabricated#: 91x | missing expected citation |
| IC01 | inhibitor_comparison | 0.67 | missing: any:lower/stronger; all:allosteric | missing expected citation | no hedging |
| IC02 | inhibitor_comparison | 0.60 | missing: 18 fold; any:mutant-selectiv/selectivity | fabricated#: 18x | missing expected citation |
| IC03 | inhibitor_comparison | 0.40 | missing: all:allosteric; any:context-dependent/depends/cannot be generalised/must be measured; any:right-censored/censored/inactive | missing expected citation |
| IC04 | inhibitor_comparison | 0.67 | missing: 680 fold; all:covalent | fabricated#: 680x | missing expected citation |
| IC05 | inhibitor_comparison | 0.75 | missing: all:reversible; all:T790M | missing expected citation |
| IC06 | inhibitor_comparison | 1.00 | missing expected citation |
| AD01 | assay_distinction | 0.75 | missing: any:ATP/substrate/assay format; any:time-dependent/covalent | missing expected citation | no hedging |
| AD02 | assay_distinction | 0.33 | missing: 574 nM; 2950 nM; all:NCI-H1975; any:must not/different | fabricated#: 11.6 nM | invented-cite: 10.1186/s12929-026-01627-6 | missing expected citation |
| AD03 | assay_distinction | 0.86 | missing: any:requires_review/excluded/regression target | missing expected citation |
| AD04 | assay_distinction | 0.86 | missing: num_any:22.5nM,853nM | fabricated#: 50% | missing expected citation |
| AD05 | assay_distinction | 0.12 | missing: all:log10(IC50; any:micromolar/uM/µM; all:lower; all:stronger |
| AD06 | assay_distinction | 0.25 | missing: any:header-only/cellular_assays; any:not acquired/supplementary/not available; any:no-fabrication/must not/invented | missing expected citation |
| EQ01 | evidence_qa | 0.00 | missing: all:10.3389/fonc.2026.1952701; all:42835192 | fabricated#: 10nM | invented-cite: 10.1158/1535-7163.mct-25-1058, 39910252 | missing expected citation |
| EQ02 | evidence_qa | 0.75 | missing: all:EVIDENCE_00001 | invented-cite: 10.1021/acs.jmedchem.6c02266 | missing expected citation |
| EQ03 | evidence_qa | 0.67 | missing: any:EVIDENCE_00016/reversible | invented-cite: 10.1021/acs.jmedchem.6c02266 | missing expected citation |
| EQ04 | evidence_qa | 0.25 | missing: any:Cys797/797; all:acrylamide; all:EVIDENCE_00036 | invented-cite: 10.3390/ijms262412162 | missing expected citation |
| EQ05 | evidence_qa | 0.75 | missing: all:EVIDENCE_00031 | invented-cite: 10.1186/s12929-026-01392-9 | missing expected citation |
| EQ06 | evidence_qa | 0.75 | missing: all:investigational | invented-cite: 10.1186/s12929-026-01292-6 | missing expected citation |

## How to re-run against a live model

```bash
# local OpenAI-compatible server (e.g. vLLM)
OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=sk-x OPENAI_MODEL=<name> \
  python -m scientific_evidence.evaluation.run_benchmark --backend openai

# Adaption hosted fine-tune (Responses API)
ADAPTION_API_KEY=... ADAPTION_STACK=<slug> \
  python -m scientific_evidence.evaluation.run_benchmark --backend adaption
```
