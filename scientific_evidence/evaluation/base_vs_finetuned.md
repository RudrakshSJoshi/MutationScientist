# Base vs fine-tuned — independent EGFR benchmark

- **Fine-tuned:** `/Users/home/Desktop/EGFR_TRAINING/mlx_model @ http://localhost:8000/v1`
- **Base:** `Qwen/Qwen3.5-4B @ http://localhost:8000/v1`
- **Items:** 30 (identical independent benchmark, identical deterministic scorers, temperature 0)

## Headline metrics

| Metric | Fine-tuned | Base | Δ (ft−base) | Better |
|---|---|---|---|---|
| Pass rate | 0.0% | 0.0% | 0.0% | **tie** |
| Mean factual correctness | 0.555 | 0.636 | -0.081 | **base** |
| Items with fabricated numbers | 6 | 11 | -5 | **fine-tuned** |
| Items with invented DOI/PMID | 9 | 0 | 9 | **base** |
| Citation recall | 0.0% | 0.0% | 0.0% | **tie** |
| Biochem/cellular conflation flags | 0 | 5 | -5 | **fine-tuned** |
| Hedging missing (of required) | 3 | 0 | 3 | **base** |
| Mean overlap vs reference (Jaccard) | 0.231 | 0.183 | 0.048 | **fine-tuned** |

## Pass rate by task category

| Category | Fine-tuned | Base |
|---|---|---|
| assay_distinction | 0/6 | 0/6 |
| evidence_qa | 0/6 | 0/6 |
| inhibitor_comparison | 0/6 | 0/6 |
| mutation_mechanism | 0/6 | 0/6 |
| resistance_interpretation | 0/6 | 0/6 |

## Where the fine-tune fixed a base failure (0)

_No item where the fine-tune passed and the base failed._

## Honest limitations — items the fine-tune still failed (30)

| id | task | fine-tuned issue |
|---|---|---|
| MM01 | mutation_mechanism | invented-cite: 10.1038/s41586-026-0766-9; missing expected citation; missing: all:serine/Ser; all:osimertinib |
| MM02 | mutation_mechanism | invented-cite: 10.1158/1535-7163.mct-25-1046; missing expected citation; missing: any:first- and second-generation/first-generation/1st/2nd/ |
| MM03 | mutation_mechanism | missing expected citation; missing: all:leucine/Leu; all:arginine/Arg; all:sensiti |
| MM04 | mutation_mechanism | missing expected citation; missing: all:746; any:ELREA/E746 |
| MM05 | mutation_mechanism | missing expected citation; missing: all:serine/Ser; all:isoleucine/Ile; any:exon-20/exon 20 |
| MM06 | mutation_mechanism | missing expected citation; missing: all:leucine/Leu; all:glutamine/Gln; any:exon-21/exon 21 |
| RI01 | resistance_interpretation | missing expected citation; missing: all:biochemical; any:covalent/time-dependent |
| RI02 | resistance_interpretation | missing expected citation; missing: any:right-censored/censored/lower bound |
| RI03 | resistance_interpretation | missing expected citation; missing: all:serine/Ser; any:reversible/allosteric; any:BLU-945/JBJ |
| RI04 | resistance_interpretation | missing expected citation; missing: any:L858R/T790M/C797S/triple; any:not determined/n.d./not available; any:broad/resistance; no hedging |
