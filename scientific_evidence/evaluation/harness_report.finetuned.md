# MutationScientist evaluation report

- **Mode:** `real:openai`
- **Items evaluated:** 218
- **Potential fabricated numbers:** 21 across 20 items (fabrication rate 9.2%)
- **Biochemical/cellular conflation flags:** 1 (0.5%)
- **Items with hedging/uncertainty:** 212 (97.2%)
- **Mean token-overlap (Jaccard) vs reference:** 0.384
- **Total numeric+unit claims in predictions:** 367

## Per task_type

| task_type | n | pred #s | ungrounded #s | fab items | fab rate | conflation | hedged | mean Jaccard |
|---|---|---|---|---|---|---|---|---|
| assay_distinction | 32 | 61 | 1 | 1 | 3.1% | 1 | 31 | 0.367 |
| evidence_qa | 15 | 0 | 0 | 0 | 0.0% | 0 | 15 | 0.388 |
| experimental_interpretation | 83 | 128 | 11 | 10 | 12.0% | 0 | 83 | 0.409 |
| inhibitor_comparison | 59 | 170 | 7 | 7 | 11.9% | 0 | 55 | 0.416 |
| mutation_classification | 8 | 0 | 0 | 0 | 0.0% | 0 | 7 | 0.245 |
| mutation_mechanism | 12 | 0 | 0 | 0 | 0.0% | 0 | 12 | 0.271 |
| resistance_interpretation | 9 | 8 | 2 | 2 | 22.2% | 0 | 9 | 0.269 |

## Flagged potential fabrications

| idx | source | task_type | ungrounded number(s) | prompt |
|---|---|---|---|---|
| 6 | sft_test.csv#6 | experimental_interpretation | 10x | Using Melis et al. 2026 biochemical kinase data at Km,ATP: osimertinib IC50 is 12.5 nM against wild-type EGFR and 125 nM against EGFR ex19del/T790M/C797S. Inter |
| 7 | sft_test.csv#7 | experimental_interpretation | 14x | Using Melis et al. 2026 biochemical kinase data at Km,ATP: BLU-945 IC50 is 86.0 nM against wild-type EGFR and 6.32 nM against EGFR L858R/C797S. Interpret the ef |
| 9 | sft_test.csv#9 | experimental_interpretation | 562-fold | Using Melis et al. 2026 biochemical kinase data at Km,ATP: silevertinib IC50 is 0.265 nM against wild-type EGFR and 149 nM against EGFR L858R/T790M. Interpret t |
| 10 | sft_test.csv#10 | experimental_interpretation | 1.32-fold | Using Melis et al. 2026 biochemical kinase data at Km,ATP: silevertinib IC50 is 0.265 nM against wild-type EGFR and 0.348 nM against EGFR L858R/C797S. Interpret |
| 11 | sft_test.csv#11 | experimental_interpretation | 0.86x | Using Melis et al. 2026 biochemical kinase data at Km,ATP: silevertinib IC50 is 0.265 nM against wild-type EGFR and 0.226 nM against EGFR ex19del/C797S. Interpr |
| 14 | sft_test.csv#14 | experimental_interpretation | 68x | Using Melis et al. 2026 biochemical kinase data at 1 mmol/L ATP: JBJ-09-063 IC50 is 148 nM against wild-type EGFR and 10000 nM against EGFR ex19del. Interpret t |
| 15 | sft_test.csv#15 | experimental_interpretation | 939x | Using Melis et al. 2026 biochemical kinase data at 1 mmol/L ATP: silevertinib IC50 is 10.7 nM against wild-type EGFR and 10000 nM against EGFR ex19del/T790M/C79 |
| 18 | sft_test.csv#18 | experimental_interpretation | 562x | In the Melis 2026 biochemical kinase panel at Km,ATP, silevertinib gives an IC50 of 149 nM against EGFR L858R/T790M versus 0.265 nM against wild-type EGFR. Inte |
| 44 | sft_test.csv#44 | inhibitor_comparison | 1736x | Compare two mid-ranked EGFR WT binders from BindingDB: BDB_200757 (19 nM) and BDB_793107 (33000 nM). Which is more potent? |
| 46 | sft_test.csv#46 | inhibitor_comparison | 8x | Compare two mid-ranked EGFR T790M/C797S binders from BindingDB: BDB_547869 (2.4 nM) and BDB_547948 (19 nM). Which is more potent? |
| 114 | sft_test.csv#114 | inhibitor_comparison | 160x | Against EGFR S768I, BDB_557878 has a median IC50 of 34.0 nM and BDB_557906 has 5400.0 nM. How do they compare? |
| 115 | sft_test.csv#115 | inhibitor_comparison | 19.1x | Against EGFR S768I, BDB_557878 has a median IC50 of 34.0 nM and BDB_557856 has 650.0 nM. How do they compare? |
| 123 | sft_test.csv#123 | inhibitor_comparison | 10.4x | Against EGFR exon 19 deletion (ex19del), BDB_790083 has a median IC50 of 16.9 nM and BDB_789958 has 176.0 nM. How do they compare? |
| 166 | sft_test.csv#166 | experimental_interpretation | 30000 nM, 50000 nM | BindingDB compound BDB_557905 has an aggregated median IC50 of 29000 nM (from 1 measurement record(s)) against EGFR S768I. How potent is this against the varian |
| 171 | sft_test.csv#171 | inhibitor_comparison | 50% | Of the BindingDB compounds tested against EGFR S768I (BDB_557888 = 10 nM; BDB_557892 = 110 nM; BDB_557876 = 130 nM; BDB_557874 = 130 nM; BDB_557889 = 2700 nM; B |
| 181 | sft_test.csv#181 | resistance_interpretation | 32.4-fold | EGFR T790M/C797S is a known TKI-resistance genotype. How should the spread of these BindingDB IC50s (best BDB_547926 = 4.9 nM; worst BDB_707485 = 158 nM) be int |
| 189 | sft_test.csv#189 | resistance_interpretation | 122x | EGFR T790M/C797S is a known TKI-resistance genotype. How should the spread of these BindingDB IC50s (best BDB_707536 = 1.23 nM; worst BDB_701470 = 150 nM) be in |
| 209 | sft_test.csv#209 | inhibitor_comparison | 3.3x | Compare two EGFR L858R/C797S compounds from BindingDB: BDB_727119 (1.5 nM) and BDB_759557 (4.9 nM). Which engages the target more potently and by roughly how mu |
| 216 | eval_questions.jsonl#1 | experimental_interpretation | 204x | At Km,ATP, osimertinib IC50 is 2.82 nM (L858R) vs 574 nM (L858R/C797S). State the fold-change and what it does not prove. |
| 217 | eval_questions.jsonl#2 | assay_distinction | 50% | Why must KD, Ki and IC50 not be pooled into one affinity training target? |
