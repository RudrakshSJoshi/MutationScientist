# MutationScientist evaluation report

- **Mode:** `real:openai`
- **Items evaluated:** 218
- **Potential fabricated numbers:** 138 across 108 items (fabrication rate 49.5%)
- **Biochemical/cellular conflation flags:** 30 (13.8%)
- **Items with hedging/uncertainty:** 201 (92.2%)
- **Mean token-overlap (Jaccard) vs reference:** 0.224
- **Total numeric+unit claims in predictions:** 784

## Per task_type

| task_type | n | pred #s | ungrounded #s | fab items | fab rate | conflation | hedged | mean Jaccard |
|---|---|---|---|---|---|---|---|---|
| assay_distinction | 32 | 124 | 16 | 10 | 31.2% | 7 | 30 | 0.201 |
| evidence_qa | 15 | 0 | 0 | 0 | 0.0% | 2 | 15 | 0.203 |
| experimental_interpretation | 83 | 254 | 80 | 62 | 74.7% | 8 | 81 | 0.240 |
| inhibitor_comparison | 59 | 383 | 36 | 30 | 50.8% | 11 | 52 | 0.242 |
| mutation_classification | 8 | 1 | 1 | 1 | 12.5% | 1 | 8 | 0.140 |
| mutation_mechanism | 12 | 1 | 1 | 1 | 8.3% | 0 | 8 | 0.178 |
| resistance_interpretation | 9 | 21 | 4 | 4 | 44.4% | 1 | 7 | 0.202 |

## Flagged potential fabrications

| idx | source | task_type | ungrounded number(s) | prompt |
|---|---|---|---|---|
| 5 | sft_test.csv#5 | experimental_interpretation | 4.43-fold | Using Melis et al. 2026 biochemical kinase data at Km,ATP: osimertinib IC50 is 12.5 nM against wild-type EGFR and 2.82 nM against EGFR L858R. Interpret the effe |
| 8 | sft_test.csv#8 | experimental_interpretation | 2.23-fold | Using Melis et al. 2026 biochemical kinase data at Km,ATP: BLU-945 IC50 is 86.0 nM against wild-type EGFR and 38.5 nM against EGFR ex19del/C797S. Interpret the  |
| 9 | sft_test.csv#9 | experimental_interpretation | 566-fold, 566-fold, 50% | Using Melis et al. 2026 biochemical kinase data at Km,ATP: silevertinib IC50 is 0.265 nM against wild-type EGFR and 149 nM against EGFR L858R/T790M. Interpret t |
| 10 | sft_test.csv#10 | experimental_interpretation | 1.31-fold, 1.31-fold | Using Melis et al. 2026 biochemical kinase data at Km,ATP: silevertinib IC50 is 0.265 nM against wild-type EGFR and 0.348 nM against EGFR L858R/C797S. Interpret |
| 11 | sft_test.csv#11 | experimental_interpretation | 15% | Using Melis et al. 2026 biochemical kinase data at Km,ATP: silevertinib IC50 is 0.265 nM against wild-type EGFR and 0.226 nM against EGFR ex19del/C797S. Interpr |
| 12 | sft_test.csv#12 | experimental_interpretation | 1 mM, 1 mM | Using Melis et al. 2026 biochemical kinase data at 1 mmol/L ATP: BLU-945 IC50 is 1490 nM against wild-type EGFR and 409 nM against EGFR L858R. Interpret the eff |
| 13 | sft_test.csv#13 | experimental_interpretation | 2.35-fold | Using Melis et al. 2026 biochemical kinase data at 1 mmol/L ATP: BLU-945 IC50 is 1490 nM against wild-type EGFR and 550 nM against EGFR ex19del/C797S. Interpret |
| 14 | sft_test.csv#14 | experimental_interpretation | 67-fold | Using Melis et al. 2026 biochemical kinase data at 1 mmol/L ATP: JBJ-09-063 IC50 is 148 nM against wild-type EGFR and 10000 nM against EGFR ex19del. Interpret t |
| 15 | sft_test.csv#15 | experimental_interpretation | 930-fold | Using Melis et al. 2026 biochemical kinase data at 1 mmol/L ATP: silevertinib IC50 is 10.7 nM against wild-type EGFR and 10000 nM against EGFR ex19del/T790M/C79 |
| 16 | sft_test.csv#16 | resistance_interpretation | 70% | Why does the EGFR L858R/T790M variant matter for choosing an inhibitor generation, given its listed resistance to 1st/2nd-gen TKI? |
| 17 | sft_test.csv#17 | experimental_interpretation | 1.21-fold | In the Melis 2026 biochemical kinase panel at Km,ATP, silevertinib gives an IC50 of 0.219 nM against EGFR L858R versus 0.265 nM against wild-type EGFR. Interpre |
| 18 | sft_test.csv#18 | experimental_interpretation | 562-fold, 562-fold | In the Melis 2026 biochemical kinase panel at Km,ATP, silevertinib gives an IC50 of 149 nM against EGFR L858R/T790M versus 0.265 nM against wild-type EGFR. Inte |
| 19 | sft_test.csv#19 | experimental_interpretation | 460-fold, 460-fold | In the Melis 2026 biochemical kinase panel at Km,ATP, silevertinib gives an IC50 of 122 nM against EGFR ex19del/T790M versus 0.265 nM against wild-type EGFR. In |
| 20 | sft_test.csv#20 | assay_distinction | 50%, 0.2 mM, 50%, 5 mM | For silevertinib against EGFR L858R, the Melis 2026 panel reports IC50 = 0.219 nM at Km,ATP and 1.86 nM at 1 mM ATP. Why do these differ and which is more physi |
| 22 | sft_test.csv#22 | resistance_interpretation | 50% | The Melis 2026 panel reports silevertinib with IC50 = 1.32 nM against EGFR ex19del/C797S at 1mM ATP. Interpret this from a resistance standpoint. |
| 23 | sft_test.csv#23 | assay_distinction | 20 µM, 5 mM | For osimertinib against EGFR ex19del/T790M, the Melis 2026 panel reports IC50 = 1.41 nM at Km,ATP and 41.0 nM at 1 mM ATP. Why do these differ and which is more |
| 29 | sft_test.csv#29 | experimental_interpretation | 100 nM | BindingDB lists compound BDB_557894 with a median IC50 of 510 nM against EGFR S768I (based on 1 measurement). Interpret its potency. |
| 30 | sft_test.csv#30 | experimental_interpretation | 100 nM | BindingDB lists compound BDB_557848 with a median IC50 of 48 nM against EGFR S768I (based on 1 measurement). Interpret its potency. |
| 31 | sft_test.csv#31 | experimental_interpretation | 1 nM | BindingDB lists compound BDB_50468247 with a median IC50 of 0.91 nM against EGFR S768I (based on 1 measurement). Interpret its potency. |
| 32 | sft_test.csv#32 | experimental_interpretation | 100 nM, 500 nM, 50%, 50% | BindingDB lists compound BDB_557887 with a median IC50 of 110 nM against EGFR S768I (based on 1 measurement). Interpret its potency. |
| 34 | sft_test.csv#34 | experimental_interpretation | 100 nM | BindingDB lists compound BDB_557855 with a median IC50 of 81 nM against EGFR S768I (based on 1 measurement). Interpret its potency. |
| 35 | sft_test.csv#35 | experimental_interpretation | 50% | BindingDB lists compound BDB_557860 with a median IC50 of 66 nM against EGFR S768I (based on 1 measurement). Interpret its potency. |
| 36 | sft_test.csv#36 | inhibitor_comparison | 50% | Among these BindingDB compounds tested against EGFR S768I — BDB_557872 5 nM; BDB_557894 510 nM; BDB_557848 48 nM; BDB_50468247 0.91 nM; BDB_557887 110 nM; BDB_5 |
| 40 | sft_test.csv#40 | inhibitor_comparison | 50%, 22-fold | Compare two mid-ranked EGFR S768I binders from BindingDB: BDB_557872 (5 nM) and BDB_557887 (110 nM). Which is more potent? |
| 44 | sft_test.csv#44 | inhibitor_comparison | 50%, 1,737-fold | Compare two mid-ranked EGFR WT binders from BindingDB: BDB_200757 (19 nM) and BDB_793107 (33000 nM). Which is more potent? |
| 46 | sft_test.csv#46 | inhibitor_comparison | 50%, 8-fold | Compare two mid-ranked EGFR T790M/C797S binders from BindingDB: BDB_547869 (2.4 nM) and BDB_547948 (19 nM). Which is more potent? |
| 49 | sft_test.csv#49 | experimental_interpretation | 50% | BindingDB lists compound BDB_717314 with a median IC50 of 0.33 nM against EGFR C797S (based on 1 measurement). Interpret its potency. |
| 65 | sft_test.csv#65 | experimental_interpretation | 50% | BindingDB reports a median IC50 of 4 nM for BDB_5447 tested against EGFR G719C. What does this tell you, and what does it not? |
| 66 | sft_test.csv#66 | experimental_interpretation | 50% | BindingDB reports a median IC50 of 1.2 nM for BDB_525446 tested against EGFR ex19del/T790M/C797S. What does this tell you, and what does it not? |
| 70 | sft_test.csv#70 | inhibitor_comparison | 10-fold | Contrast the biochemical potency of BDB_761658 (median IC50 0.4 nM) and BDB_765210 (median IC50 4 nM) against EGFR L858R/T790M. |
| 72 | sft_test.csv#72 | inhibitor_comparison | 18.5-fold | Contrast the biochemical potency of BDB_765131 (median IC50 2 nM) and BDB_790088 (median IC50 37.1 nM) against EGFR L858R. |
| 73 | sft_test.csv#73 | experimental_interpretation | 50% | In BindingDB, compound BDB_525480 has an aggregated median IC50 of 0.7 nM against the EGFR L858R/T790M/C797S variant. Interpret this value and its limitations. |
| 75 | sft_test.csv#75 | inhibitor_comparison | 82-fold | Contrast the biochemical potency of BDB_525469 (median IC50 5.5 nM) and BDB_671007 (median IC50 450 nM) against EGFR L858R/T790M/C797S. |
| 80 | sft_test.csv#80 | inhibitor_comparison | 68-fold | For EGFR L861Q, compare the most potent compound BDB_5447 (median IC50 2.2 nM) with the least potent BDB_50379214 (median IC50 150 nM). What is the approximate  |
| 81 | sft_test.csv#81 | inhibitor_comparison | 68-fold | Contrast the biochemical potency of BDB_5447 (median IC50 2.2 nM) and BDB_50379214 (median IC50 150 nM) against EGFR L861Q. |
| 85 | sft_test.csv#85 | experimental_interpretation | 50% | In an aggregated BindingDB dataset, compound BDB_557858 has a median IC50 of 4.0 nM against the EGFR S768I variant. How should this value be interpreted? |
| 86 | sft_test.csv#86 | experimental_interpretation | 14 µM, 100,000 nM | Interpret the reported potency of BDB_557909 (median IC50 14000.0 nM) against EGFR S768I. |
| 87 | sft_test.csv#87 | experimental_interpretation | 50% | What does a median IC50 of 210.0 nM tell you about BDB_557901 as an inhibitor of EGFR S768I? |
| 88 | sft_test.csv#88 | experimental_interpretation | 50% | Summarise the activity of BDB_557890 against the EGFR S768I variant given its BindingDB median IC50 of 15.0 nM. |
| 89 | sft_test.csv#89 | experimental_interpretation | 50% | In an aggregated BindingDB dataset, compound BDB_557865 has a median IC50 of 2.0 nM against the EGFR S768I variant. How should this value be interpreted? |
| 90 | sft_test.csv#90 | experimental_interpretation | 50% | Interpret the reported potency of BDB_557851 (median IC50 2.5 nM) against EGFR S768I. |
| 92 | sft_test.csv#92 | experimental_interpretation | 50% | Summarise the activity of BDB_557903 against the EGFR S768I variant given its BindingDB median IC50 of 490.0 nM. |
| 95 | sft_test.csv#95 | inhibitor_comparison | 7,000-fold | Against EGFR S768I, BDB_557865 has a median IC50 of 2.0 nM and BDB_557909 has 14000.0 nM. How do they compare? |
| 96 | sft_test.csv#96 | inhibitor_comparison | 33-fold | Against EGFR S768I, BDB_557865 has a median IC50 of 2.0 nM and BDB_557897 has 66.0 nM. How do they compare? |
| 97 | sft_test.csv#97 | inhibitor_comparison | 5,600-fold | Against EGFR S768I, BDB_557851 has a median IC50 of 2.5 nM and BDB_557909 has 14000.0 nM. How do they compare? |
| 100 | sft_test.csv#100 | assay_distinction | 50% | BDB_557865 shows a median IC50 of 2.0 nM against EGFR S768I. Does this mean it will work in patients with this mutation? |
| 101 | sft_test.csv#101 | inhibitor_comparison | 175-fold | Against EGFR L858R/T790M, BDB_765222 has a median IC50 of 0.6 nM and BDB_625609 has 105.0 nM. How do they compare? |
| 102 | sft_test.csv#102 | inhibitor_comparison | 36.7-fold | Against EGFR L858R/T790M, BDB_765222 has a median IC50 of 0.6 nM and BDB_200805 has 22.0 nM. How do they compare? |
| 106 | sft_test.csv#106 | experimental_interpretation | 50% | In an aggregated BindingDB dataset, compound BDB_557878 has a median IC50 of 34.0 nM against the EGFR S768I variant. How should this value be interpreted? |
| 107 | sft_test.csv#107 | experimental_interpretation | 50% | Interpret the reported potency of BDB_557856 (median IC50 650.0 nM) against EGFR S768I. |
| 108 | sft_test.csv#108 | experimental_interpretation | 50% | What does a median IC50 of 2200.0 nM tell you about BDB_557879 as an inhibitor of EGFR S768I? |
| 109 | sft_test.csv#109 | experimental_interpretation | 50% | Summarise the activity of BDB_557883 against the EGFR S768I variant given its BindingDB median IC50 of 67.0 nM. |
| 110 | sft_test.csv#110 | experimental_interpretation | 50% | In an aggregated BindingDB dataset, compound BDB_557900 has a median IC50 of 220.0 nM against the EGFR S768I variant. How should this value be interpreted? |
| 111 | sft_test.csv#111 | experimental_interpretation | 5.4 µM, 50% | Interpret the reported potency of BDB_557906 (median IC50 5400.0 nM) against EGFR S768I. |
| 112 | sft_test.csv#112 | inhibitor_comparison | 1.94-fold | Among these compounds tested against EGFR S768I (median IC50 values in nM): BDB_557878 (34.0 nM), BDB_557856 (650.0 nM), BDB_557879 (2200.0 nM), BDB_557883 (67. |
| 113 | sft_test.csv#113 | inhibitor_comparison | 50% | For EGFR S768I, which of these is the weakest inhibitor by median IC50: BDB_557878 (34.0 nM), BDB_557856 (650.0 nM), BDB_557879 (2200.0 nM), BDB_557883 (67.0 nM |
| 114 | sft_test.csv#114 | inhibitor_comparison | 159-fold | Against EGFR S768I, BDB_557878 has a median IC50 of 34.0 nM and BDB_557906 has 5400.0 nM. How do they compare? |
| 115 | sft_test.csv#115 | inhibitor_comparison | 19.1-fold | Against EGFR S768I, BDB_557878 has a median IC50 of 34.0 nM and BDB_557856 has 650.0 nM. How do they compare? |
| 116 | sft_test.csv#116 | inhibitor_comparison | 80.6-fold | Against EGFR S768I, BDB_557883 has a median IC50 of 67.0 nM and BDB_557906 has 5400.0 nM. How do they compare? |
| 120 | sft_test.csv#120 | experimental_interpretation | 50% | In an aggregated BindingDB dataset, compound BDB_717392 has a median IC50 of 0.51 nM against the EGFR C797S variant. How should this value be interpreted? |
| 122 | sft_test.csv#122 | experimental_interpretation | 50% | In an aggregated BindingDB dataset, compound BDB_679684 has a median IC50 of 70.0 nM against the EGFR exon 19 deletion (ex19del) variant. How should this value  |
| 123 | sft_test.csv#123 | inhibitor_comparison | 10.4-fold, 50% | Against EGFR exon 19 deletion (ex19del), BDB_790083 has a median IC50 of 16.9 nM and BDB_789958 has 176.0 nM. How do they compare? |
| 124 | sft_test.csv#124 | assay_distinction | 50% | BDB_790096 shows a median IC50 of 8.98 nM against EGFR exon 19 deletion (ex19del). Does this mean it will work in patients with this mutation? |
| 125 | sft_test.csv#125 | experimental_interpretation | 50% | In an aggregated BindingDB dataset, compound BDB_717540 has a median IC50 of 0.75 nM against the EGFR ex19del/T790M variant. How should this value be interprete |
| 126 | sft_test.csv#126 | experimental_interpretation | 50% | What does a median IC50 of 0.02 nM tell you about BDB_717471 as an inhibitor of EGFR ex19del/T790M? |
| 131 | sft_test.csv#131 | mutation_mechanism | 2% | Explain the molecular nature of the EGFR L861Q mutation. |
| 132 | sft_test.csv#132 | mutation_classification | 1% | Is EGFR L861Q an activating mutation, a resistance mutation, or both? |
| 134 | sft_test.csv#134 | inhibitor_comparison | 1%, 100-fold, 10-fold | What is the relevance of EGFR L861Q to EGFR inhibitor selection? |
| 138 | sft_test.csv#138 | experimental_interpretation | 52-fold, 18.3-fold | At Km,ATP, BLU-945 (CMP_BLU945) inhibits wild-type EGFR with IC50 = 86.0 nM and the L858R/T790M double mutant with IC50 = 4.7 nM. Interpret the mutant-vs-WT sel |
| 139 | sft_test.csv#139 | assay_distinction | 10 µM, 100-fold | For BLU-945 (CMP_BLU945) against the exon-19 deletion (ex19del) mutant, IC50 = 40.2 nM at Km,ATP but 504 nM at 1 mM ATP. Explain the difference. |
| 140 | sft_test.csv#140 | assay_distinction | 50% | BLU-945 (CMP_BLU945) is reported with an IC50 of 7.61 nM against L858R at Km,ATP. Is this the same as its binding affinity (KD/Ki)? |
| 141 | sft_test.csv#141 | experimental_interpretation | 50%, 10 nM | Interpret the potency of BindingDB compound BDB_50529707 against WT EGFR: median IC50 = 78.5 nM (n = 4 measurement(s)). |
| 142 | sft_test.csv#142 | experimental_interpretation | 50% | Interpret the potency of BindingDB compound BDB_790008 against L858R EGFR: median IC50 = 37.3 nM (n = 1 measurement(s)). |
| 143 | sft_test.csv#143 | experimental_interpretation | 50% | Interpret the potency of BindingDB compound BDB_200793 against L858R EGFR: median IC50 = 0.17 nM (n = 1 measurement(s)). |
| 149 | sft_test.csv#149 | assay_distinction | 50% | Give the full potency ordering of these compounds against ex19del/T790M EGFR and explain what kind of data this is. Median IC50s: BDB_717513 0.04 nM, BDB_717494 |
| 150 | sft_test.csv#150 | resistance_interpretation | 100-fold | Why does the EGFR ex19del/T790M/C797S annotation (classification = "activating+resistance", resistance = "osimertinib") matter for choosing or designing an EGFR |
| 152 | sft_test.csv#152 | experimental_interpretation | 50% | Interpret the potency of BindingDB compound BDB_789995 against L858R/T790M EGFR: median IC50 = 3.56 nM (n = 1 measurement(s)). |
| 153 | sft_test.csv#153 | assay_distinction | 50% | Give the full potency ordering of these compounds against L858R/T790M EGFR and explain what kind of data this is. Median IC50s: BDB_789988 400.0 nM, BDB_789995  |
| 158 | sft_test.csv#158 | experimental_interpretation | 50% | Interpret the potency of BindingDB compound BDB_50308944 against WT EGFR: median IC50 = 90.0 nM (n = 1 measurement(s)). |
| 159 | sft_test.csv#159 | inhibitor_comparison | 104-fold | Contrast the potency of BDB_717186 (median IC50 0.25 nM) and BDB_759867 (median IC50 26.0 nM) against L858R/C797S EGFR. |
| 162 | sft_test.csv#162 | experimental_interpretation | 50% | BindingDB compound BDB_557888 (structure SMILES: COc1cc2ncnc(Nc3ccc(Br)c(Cl)c3)c2cc1OC1CCN(C1)C(=O)C=C) has an aggregated median IC50 of 10 nM (from 1 measureme |
| 163 | sft_test.csv#163 | experimental_interpretation | 50% | BindingDB compound BDB_557876 has an aggregated median IC50 of 130 nM (from 1 measurement record(s)) against EGFR S768I. How potent is this against the variant, |
| 164 | sft_test.csv#164 | experimental_interpretation | 50% | BindingDB compound BDB_557889 has an aggregated median IC50 of 2700 nM (from 1 measurement record(s)) against EGFR S768I. How potent is this against the variant |
| 165 | sft_test.csv#165 | experimental_interpretation | 50% | BindingDB compound BDB_557891 (structure SMILES: COc1cc2ncnc(Nc3cccc(CO)c3)c2cc1OC1CCN(C1)C(=O)C=C) has an aggregated median IC50 of 4500 nM (from 1 measurement |
| 166 | sft_test.csv#166 | experimental_interpretation | 29 µM, 50% | BindingDB compound BDB_557905 has an aggregated median IC50 of 29000 nM (from 1 measurement record(s)) against EGFR S768I. How potent is this against the varian |
| 167 | sft_test.csv#167 | experimental_interpretation | 50% | BindingDB compound BDB_557902 has an aggregated median IC50 of 3900 nM (from 1 measurement record(s)) against EGFR S768I. How potent is this against the variant |
| 168 | sft_test.csv#168 | experimental_interpretation | 50% | BindingDB compound BDB_557892 (structure SMILES: COc1cc2ncnc(Nc3ccc(Cl)c(CO)c3)c2cc1OC1CCN(CC1)C(=O)C=C) has an aggregated median IC50 of 110 nM (from 1 measure |
| 169 | sft_test.csv#169 | experimental_interpretation | 50% | BindingDB compound BDB_557874 has an aggregated median IC50 of 130 nM (from 1 measurement record(s)) against EGFR S768I. How potent is this against the variant, |
| 170 | sft_test.csv#170 | inhibitor_comparison | 11-fold | Among these BindingDB compounds profiled against EGFR S768I (BDB_557888 = 10 nM; BDB_557892 = 110 nM; BDB_557876 = 130 nM; BDB_557874 = 130 nM; BDB_557889 = 270 |
| 171 | sft_test.csv#171 | inhibitor_comparison | 29 µM | Of the BindingDB compounds tested against EGFR S768I (BDB_557888 = 10 nM; BDB_557892 = 110 nM; BDB_557876 = 130 nM; BDB_557874 = 130 nM; BDB_557889 = 2700 nM; B |
| 173 | sft_test.csv#173 | inhibitor_comparison | 2,900-fold | Contrast the strongest and weakest BindingDB compounds against EGFR S768I: BDB_557888 (10 nM) versus BDB_557905 (29000 nM). |
| 174 | sft_test.csv#174 | inhibitor_comparison | 41-fold | Compare BDB_557892 (110 nM) and BDB_557891 (4500 nM) as inhibitors of EGFR S768I. |
| 180 | sft_test.csv#180 | inhibitor_comparison | 32-fold | Contrast the strongest and weakest BindingDB compounds against EGFR T790M/C797S: BDB_547926 (4.9 nM) versus BDB_707485 (158 nM). |
| 182 | sft_test.csv#182 | experimental_interpretation | 50%, 50% | BindingDB compound BDB_765212 has an aggregated median IC50 of 4 nM (from 1 measurement record(s)) against EGFR L858R/T790M. How potent is this against the vari |
| 184 | sft_test.csv#184 | experimental_interpretation | 1 nM, 50% | BindingDB compound BDB_759830 (structure SMILES: COc4cc3ncnc(c1cn(C)nc1c2ccccc2)c3nc4NC(=O)c5cnn(C(F)(F)F)c5C) has an aggregated median IC50 of 0.7 nM (from 1 m |
| 189 | sft_test.csv#189 | resistance_interpretation | 122-fold | EGFR T790M/C797S is a known TKI-resistance genotype. How should the spread of these BindingDB IC50s (best BDB_707536 = 1.23 nM; worst BDB_701470 = 150 nM) be in |
| 190 | sft_test.csv#190 | experimental_interpretation | 50% | BindingDB compound BDB_717341 has an aggregated median IC50 of 0.44 nM (from 1 measurement record(s)) against EGFR C797S. How potent is this against the variant |
| 192 | sft_test.csv#192 | experimental_interpretation | 50% | BindingDB compound BDB_717526 has an aggregated median IC50 of 0.01 nM (from 1 measurement record(s)) against EGFR ex19del/T790M. How potent is this against the |
| 195 | sft_test.csv#195 | inhibitor_comparison | 68.5-fold | Compare two EGFR L858R compounds from BindingDB: BDB_790012 (0.61 nM) and BDB_789957 (41.8 nM). Which engages the target more potently and by roughly how much? |
| 196 | sft_test.csv#196 | inhibitor_comparison | 222-fold | Contrast the strongest and weakest EGFR L858R inhibitors in this BindingDB set: BDB_200004 at 1.0 nM versus BDB_789958 at 222.0 nM. |
| 198 | sft_test.csv#198 | experimental_interpretation | 33 µM, 50% | Interpret the BindingDB potency of compound BDB_793079 against the EGFR WT variant (median IC50 33000.0 nM). |
| 199 | sft_test.csv#199 | experimental_interpretation | 50% | Interpret the BindingDB potency of compound BDB_50431333 against the EGFR WT variant (median IC50 61.0 nM). |
| 200 | sft_test.csv#200 | experimental_interpretation | 50%, 4.6 µM | Interpret the BindingDB potency of compound BDB_50192486 against the EGFR WT variant (median IC50 4600.0 nM). |
| 202 | sft_test.csv#202 | assay_distinction | 33 µM | What should I keep in mind about the source and quality of these EGFR WT IC50 values (e.g. BDB_793079 at 33000.0 nM) when I read them? |
| 204 | sft_test.csv#204 | experimental_interpretation | 50% | Interpret the BindingDB potency of compound BDB_50141097 against the EGFR WT variant (median IC50 21.0 nM). |
| 209 | sft_test.csv#209 | inhibitor_comparison | 3.3-fold | Compare two EGFR L858R/C797S compounds from BindingDB: BDB_727119 (1.5 nM) and BDB_759557 (4.9 nM). Which engages the target more potently and by roughly how mu |
| 212 | sft_test.csv#212 | experimental_interpretation | 50% | Interpret the BindingDB potency of compound BDB_717399 against the EGFR C797S variant (median IC50 0.55 nM). |
| 217 | eval_questions.jsonl#2 | assay_distinction | 50%, 50% | Why must KD, Ki and IC50 not be pooled into one affinity training target? |
