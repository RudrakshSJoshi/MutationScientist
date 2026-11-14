# EGFR molecular analysis

14 November 2026

## Status

| Work | Result |
| --- | --- |
| Dataset validation | 6,843 YAMLs verified against metadata, sequence records, precomputed MSA queries, ligand SMILES and experimental labels |
| Pretrained Boltz-2 | 0 of 6,843 verified. The cache is ready. CPU and MPS pilots on the full-length input were stopped during structure prediction. |
| Embedding handoff | 0 verified. The full-run output directory is pending agreement with the training owner. |
| Experimental structures | Ten deposited X-ray structures analysed. Five coordinate overlays and residue-level contact measurements are included. |
| Specialised Boltz-2 | 0 of 1,328 held-out complexes completed. The specialised affinity checkpoint is pending. |

The installed executable is `boltz-community 2.13.0` with PyTorch 2.15.0. The initial download in this execution session failed on Hugging Face name resolution. The cache was subsequently downloaded successfully in Terminal and both checkpoint files plus the chemical component data were verified. The CPU pilot on `COMPLEX_000001` (EGFR C797S with brigatinib) passed preprocessing and started structure prediction using the supplied 1,210-residue sequence and MSA. The CPU backend was selected because PyTorch did not expose MPS in this execution session. I stopped the CPU pilot after approximately 21 minutes with no structure output, to free resources for an MPS pilot. The MPS run started at 19:18 GMT, completed preprocessing in 3.27 seconds, confirmed that MPS was in use, and wrote no prediction files before being stopped at 20:24 GMT. The one-item progress display remained at zero throughout the forward pass. Both pilot logs are included. The short kinase-domain diagnostic uses reduced settings to check the output path and GPU execution. The MPS diagnostic finished in 75.7 seconds. It wrote the two affinity fields, one mmCIF, confidence data, and readable embedding arrays with shapes (367, 384) and (367, 367, 128). Both Boltz structure and affinity pose checks returned false. The reduced diagnostic establishes file generation and GPU execution. There are still zero full-length predictions or embeddings for the affinity-training handoff. [Boltz documentation](https://github.com/jwohlwend/boltz/blob/main/docs/prediction.md) · [Boltz Community documentation](https://pypi.org/project/boltz-community/)

## Dataset and evaluation audit

The dataset manifest identifies the delivery as version `1.1.0-llm-expanded`. The delivery omitted `egfr_dataset_loader.py`, so validation used the delivered files directly. The original files were read-only inputs.

- Counts matched **5,515 train, 684 validation and 644 test**, covering **16 variants and 4,160 compound IDs**. Distinct mutation–compound IDs and YAML stems matched one-to-one. All 6,843 YAMLs encode a **1,205- or 1,210-residue precursor**, with matching A3M query sequences. The experimental crystal structures are kinase-domain constructs.
- Of **18,189 eligible IC50 measurements**, **7,857** are attached to the selected cohort. The aggregate log-space labels agree with the underlying replicate means at the supplied precision. Two metadata cells list only 20 IDs despite having 31 and 42 replicates. The full exact mutation–compound groups reproduce both labels and are explicitly marked in the reference join.
- Compound IDs are split-disjoint. RDKit canonical isomeric SMILES identify **4,133 distinct exact molecular structures** and **11 structures spanning multiple splits**, involving **56 complexes**. The overlap affects 33 training, 15 validation and 8 test complexes. Gefitinib's WT record is in test under `BDB_50338602`, and its mutant records are in train under `BDB_5447`. Preserve the supplied splits and report metrics for those splits alongside a sensitivity analysis excluding identities seen in multiple splits. Scaffold-level separation was not established.
- The pair-level experimental labels mix studies and ATP conditions. For example, BLU-945 in L858R combines **7.61 nM** at the enzyme’s ATP Km and **409 nM** at 1 mM ATP. The supplied log-space mean corresponds to approximately **55.8 nM** and should be interpreted as an aggregate label. Condition-specific references are retained. [Melis et al., Table 2](https://doi.org/10.3389/fonc.2026.1952701)

| Mutation profile | Complexes in supplied cohort |
| --- | ---: |
| WT | 2,000 |
| L858R | 573 |
| E746_A750del | 233 |
| T790M | 100 |
| C797S | 313 |
| L858R/T790M/C797S | 906 |
| E746_A750del/T790M/C797S | 158 |

The complete 16-variant coverage, per-split counts, named inhibitor references and chemical-identity overlaps are in the companion CSVs. The input manifest maps each complex ID to its YAML hash, MSA, experimental label and reference measurements.

## Inhibitor observations

- **Gefitinib and erlotinib.** Exact chemical matching resolved **10 gefitinib complexes** across two BindingDB IDs and **6 erlotinib complexes** across two IDs. Both cover WT, L858R, T790M and C797S. Neither has a supplied E746_A750del or L858R/T790M/C797S complex. Shared WT–mutant assay conditions should be checked before interpreting the curated aggregate differences as mutation effects. The WT and L858R gefitinib crystals preserve a roughly **2.67 Å** hinge contact, even though published direct binding measurements show a substantial L858R affinity shift. [Yun et al.](https://doi.org/10.1016/j.ccr.2006.12.017)
- **Osimertinib.** The source cohort excludes covalent inhibitors, so no osimertinib YAML is present. In published enzyme assays at **1 mM ATP**, adding C797S raised osimertinib IC50 from **15.8 to 3,880 nM** on the E746_A750del background and from **155 to >10,000 nM** on L858R/T790M. The latter is a **>64.5-fold** increase, a lower bound. The WT-at-resistance-sites crystal 6JXT records the Cys797 covalent bond. Triple-mutant 6LUD still resolves a ligand pose with no corresponding deposited bond. [Melis et al., Table 2](https://doi.org/10.3389/fonc.2026.1952701) · [6JXT](https://www.rcsb.org/structure/6JXT) · [6LUD](https://www.rcsb.org/structure/6LUD)
- **BLU-945 and JBJ-09-063.** At **1 mM ATP**, JBJ-09-063 had IC50 **54.9 nM** on the L858R triple mutant and **>10,000 nM** on the exon-19 deletion triple mutant. BLU-945 had IC50 **217 nM** and **79.2 nM** on the same two backgrounds. This is an experimental, mutation-background-dependent comparison between an allosteric inhibitor and a reversible ATP-site inhibitor. The Boltz cohort has eight BLU-945 and four JBJ-09-063 complexes, all in train. Censored JBJ-09-063 exon-19 records are experimental references outside the Boltz cohort. [Melis et al., Table 2](https://doi.org/10.3389/fonc.2026.1952701)
- **Brigatinib.** The supplied cohort contains six brigatinib complexes. The PDB structure 7ZYM is a ligand and resistance-profile reference for T790M/C797S complex `COMPLEX_003293`. Its closest brigatinib contacts to Met790 and Met793 are 3.43 and 2.80 Å, respectively. The two linked biochemical IC50s for that complex are **2 and 194 nM**, a 97-fold spread. The original aggregate is about **19.7 nM**. The C797S-only pilot is a different resistance profile. [7ZYM](https://www.rcsb.org/structure/7ZYM)
- **Gatekeeper and exon-19 landmarks.** The WT and T790M AEE788 crystal structures both resolve the ligand in the ATP pocket. The closest gatekeeper contact is 3.02 Å in WT and 3.83 Å in T790M. Coordinate proximity cannot isolate an ATP-competition mechanism or show a steric clash. The apo deletion crystal analysed here is L747_E749del, a distinct genotype from the project's E746_A750del sequence. [2J6M](https://www.rcsb.org/structure/2J6M) · [2JIU](https://www.rcsb.org/structure/2JIU) · [Yun et al.](https://doi.org/10.1073/pnas.0709662105) · [7TVD](https://www.rcsb.org/structure/7TVD)

## Team handoff

Benchmark the original `COMPLEX_000001` YAML on an available CUDA GPU. Record structure and affinity runtimes, peak VRAM, and actual bytes per complete result. Have the affinity-training owner open the resulting embedding and confirm the handoff path before planning a cohort run. The short Mac diagnostic cannot estimate full-length throughput. If the team wants to consider kinase-domain inputs for production, agree the construct, MSA transformation and evaluation protocol jointly and treat it as its own run.

Keep the scripts, report and small audit tables in the assigned task folder of the team repository. Checkpoints, environments, and bulk embeddings remain in local or agreed shared storage. The working directory on this Mac has no Git metadata and no team repo changes were made.

## Pretrained and specialised comparison

No quantitative model comparison is available. The pipeline preserves `affinity_pred_value` and `affinity_probability_binary` separately. Lower `affinity_pred_value` represents a lower predicted log₁₀(IC₅₀ in µM) and orders the predicted inhibitor rankings. Rankings should be interpreted among plausible binders. The binder-probability head has a separate objective, and this eligible enzyme-IC50 cohort supplies no dedicated decoy benchmark. A positive mutant-minus-WT score indicates weaker predicted potency on the mutant under the same model settings. [Boltz prediction documentation](https://github.com/jwohlwend/boltz/blob/main/docs/prediction.md)

Once the specialised affinity checkpoint is available, the evaluation code joins pretrained and specialised results by held-out complex ID with the original labels and identical recorded structure checkpoint and settings. It reports MAE and RMSE by split and mutation profile, plus sensitivity summaries for canonical-identity overlap and paired prediction plots. Partial runs report their own coverage. Test labels enter the evaluation only after both sets of predictions have been fixed.

## Experimental validation still needed

For selected reversible inhibitors, use matched WT/mutant kinase constructs, recorded ATP concentrations and assay timings to reproduce mutation-dependent IC50 shifts. Use direct binding assays where available to distinguish changes in intrinsic binding from ATP competition. For osimertinib, measure time dependence and covalent occupancy or kinetics under matched conditions, with an activating-background pair that differs only at C797. Validate selected predicted poses against deposited structures for the exact ligand and genotype where available. Cellular response requires a separate assay and readout.
