#!/usr/bin/env python3
"""
Author the INDEPENDENT EGFR scientific-evaluation benchmark.

This script is the single source of truth for the benchmark: it emits
    scientific_benchmark.jsonl   (question + machine-checkable gold expectations)
    reference_answers.jsonl      (the cited gold prose, for human review + dry-run)
keeping the two mutually consistent by construction.

Design rules (per Person 3 brief + project hard rules):
  * Every numeric claim in a reference answer is a VERIFIED value from the curated
    source of truth (curated/affinity_measurements.csv, Melis 2026 Table 2, Yun 2008,
    primary_evidence.jsonl), never from teacher-generated SFT completions.
  * INDEPENDENT of training: no sft_train prompt is reused. The eval seed pool
    (eval_questions.jsonl, sft_test.csv) only informed the task taxonomy.
  * Citations are real corpus DOIs/PMIDs/evidence_ids; nothing is invented.
  * Biochemical / cellular / clinical layers are kept strictly distinct.
  * Convention surfaced everywhere: biochemical IC50 in nM, lower = stronger;
    Boltz label = log10(IC50 uM), lower = stronger, NOT pIC50.

Run:  python -m scientific_evidence.evaluation.build_benchmark
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MELIS = "10.3389/fonc.2026.1952701"       # Melis et al. 2026, Front Oncol; PMID 42835192
YUN = "10.1073/pnas.0709662105"           # Yun et al. 2008 (T790M raises ATP affinity); PMID 18227510


def kw(*phrases, any_of=False, label=None):
    """keywords fact: default = every phrase required (a nested list within = OR)."""
    f = {"type": "keywords", ("any_of" if any_of else "all_of"): list(phrases)}
    f["label"] = label or ("any:" if any_of else "all:") + "|".join(
        p if isinstance(p, str) else "/".join(p) for p in phrases)
    return f


def num(value, unit="nM", label=None):
    f = {"type": "number", "value": value, "unit": unit}
    f["label"] = label or f"{value} {unit}"
    return f


def numany(pairs, label=None):
    f = {"type": "number", "any_of": [list(p) for p in pairs]}
    f["label"] = label or "num_any:" + ",".join(f"{v}{u}" for v, u in pairs)
    return f


# --------------------------------------------------------------------------- #
# The 30 benchmark items: 6 per task_type across 5 categories.
# --------------------------------------------------------------------------- #
ITEMS = [
    # ---------------- mutation_mechanism ---------------- #
    dict(
        id="MM01", task_type="mutation_mechanism",
        question="What residue change defines EGFR C797S, in which protein domain does it sit, and why does it cause osimertinib resistance?",
        reference_answer=(
            "EGFR C797S is a missense substitution of cysteine to serine at position 797 (C797S) in the "
            "protein kinase domain (UniProt P00533, canonical P00533-1). Cys797 is the nucleophilic thiol "
            "that osimertinib's acrylamide warhead bonds covalently; replacing it with serine removes that "
            "anchor, so osimertinib can no longer form its irreversible covalent bond and loses potency. "
            "This is an on-target acquired resistance mechanism to third-generation covalent EGFR-TKIs. "
            "Source: EVIDENCE_00036; Melis et al. 2026 (DOI 10.3389/fonc.2026.1952701)."),
        required_facts=[kw("C797S"), kw(["cysteine", "Cys"]), kw(["serine", "Ser"]),
                        kw("797"), kw("kinase domain"), kw("covalent"),
                        kw(["acrylamide", "thiol", "anchor"], any_of=True),
                        kw("osimertinib"), kw("resistance")],
        expected_citations=[MELIS, "EVIDENCE_00036"], requires_hedge=False,
    ),
    dict(
        id="MM02", task_type="mutation_mechanism",
        question="What is the EGFR T790M substitution, where is it located, and what resistance does it confer?",
        reference_answer=(
            "EGFR T790M is a missense substitution of threonine to methionine at position 790 (T790M), the "
            "'gatekeeper' residue of the protein kinase domain (UniProt P00533). It confers resistance through "
            "added steric bulk at the gatekeeper and by increasing the kinase's affinity for ATP, which blunts "
            "ATP-competitive inhibitors. It is the classic acquired resistance mechanism to first- and "
            "second-generation EGFR-TKIs. Source: EVIDENCE_00006 (DOI 10.4103/ijp.ijp_1341_25); raised ATP "
            "affinity shown by Yun et al. 2008 (DOI 10.1073/pnas.0709662105)."),
        required_facts=[kw("T790M"), kw(["threonine", "Thr"]), kw(["methionine", "Met"]),
                        kw("790"), kw("gatekeeper"), kw("ATP"),
                        kw(["first- and second-generation", "first-generation", "1st/2nd", "second-generation"], any_of=True),
                        kw("resistance")],
        expected_citations=["10.4103/ijp.ijp_1341_25", YUN], requires_hedge=False,
    ),
    dict(
        id="MM03", task_type="mutation_mechanism",
        question="What kind of mutation is EGFR L858R and what is its functional consequence?",
        reference_answer=(
            "EGFR L858R is a missense substitution of leucine to arginine at position 858 (L858R) in the "
            "activation loop of the protein kinase domain (UniProt P00533). It is an activating, TKI-sensitising "
            "driver mutation that destabilises the inactive kinase conformation and promotes ligand-independent "
            "activity; tumours bearing it are typically sensitive to EGFR-TKIs. It is not itself a resistance "
            "mutation. Source: curated mutation annotation (UniProt P00533); clinical context EVIDENCE_00013 "
            "(DOI 10.1098/rstb.2024.0505)."),
        required_facts=[kw("L858R"), kw(["leucine", "Leu"]), kw(["arginine", "Arg"]),
                        kw("858"), kw("activat"), kw("sensiti"), kw("not")],
        expected_citations=["10.1098/rstb.2024.0505", "EVIDENCE_00013"], requires_hedge=False,
    ),
    dict(
        id="MM04", task_type="mutation_mechanism",
        question="What is an EGFR exon-19 deletion (ex19del) and why does it matter for therapy?",
        reference_answer=(
            "EGFR ex19del is an in-frame deletion in exon 19 of the protein kinase domain; the representative "
            "lesion is delE746_A750 (loss of the ELREA motif, residues 746-750) (UniProt P00533). Like L858R it "
            "is an activating, TKI-sensitising driver mutation and is one of the two most common sensitising EGFR "
            "alterations in NSCLC. Source: EVIDENCE_00011 (DOI 10.3389/fonc.2026.1942222)."),
        required_facts=[kw(["ex19del", "exon-19", "exon 19"], any_of=True),
                        kw(["in-frame deletion", "deletion"], any_of=True),
                        kw("746"), kw("activat"), kw("sensiti"),
                        kw(["ELREA", "E746"], any_of=True)],
        expected_citations=["10.3389/fonc.2026.1942222", "EVIDENCE_00011"], requires_hedge=False,
    ),
    dict(
        id="MM05", task_type="mutation_mechanism",
        question="Describe EGFR S768I: the substitution, its location and functional class.",
        reference_answer=(
            "EGFR S768I is a missense substitution of serine to isoleucine at position 768 (S768I), an exon-20 "
            "point mutation in the protein kinase domain (UniProt P00533). It is an atypical (uncommon) activating "
            "mutation with variable TKI sensitivity; it is not a canonical resistance mutation. Source: "
            "EVIDENCE_00031 (DOI 10.21037/tlcr-2026-0953); atypical-mutation context EVIDENCE_00034 "
            "(DOI 10.1016/j.cllc.2026.05.005)."),
        required_facts=[kw("S768I"), kw(["serine", "Ser"]), kw(["isoleucine", "Ile"]),
                        kw("768"), kw(["exon-20", "exon 20"], any_of=True),
                        kw(["atypical", "uncommon"], any_of=True), kw("activating"), kw("variable")],
        expected_citations=["10.21037/tlcr-2026-0953", "10.1016/j.cllc.2026.05.005", "EVIDENCE_00031"],
        requires_hedge=False,
    ),
    dict(
        id="MM06", task_type="mutation_mechanism",
        question="Describe EGFR L861Q: the substitution, its location and functional class.",
        reference_answer=(
            "EGFR L861Q is a missense substitution of leucine to glutamine at position 861 (L861Q), an exon-21 "
            "atypical activating mutation in the protein kinase domain (UniProt P00533). It is an uncommon "
            "activating mutation with variable TKI sensitivity rather than a resistance mutation. Source: "
            "EVIDENCE_00031 / EVIDENCE_00035 (atypical activating EGFR mutations; DOI 10.21037/tlcr-2026-0953)."),
        required_facts=[kw("L861Q"), kw(["leucine", "Leu"]), kw(["glutamine", "Gln"]),
                        kw("861"), kw(["exon-21", "exon 21"], any_of=True),
                        kw("atypical"), kw("activating")],
        expected_citations=["10.21037/tlcr-2026-0953", "EVIDENCE_00031"], requires_hedge=False,
    ),

    # ---------------- resistance_interpretation ---------------- #
    dict(
        id="RI01", task_type="resistance_interpretation",
        question=("At Km,ATP, osimertinib's biochemical IC50 is 2.82 nM against EGFR L858R and 574 nM against "
                  "L858R/C797S. State the fold-change and what it does and does not demonstrate."),
        reference_answer=(
            "The biochemical enzyme IC50 rises from 2.82 nM (L858R) to 574 nM (L858R/C797S) at Km,ATP, a loss of "
            "potency of roughly 204-fold. This demonstrates reduced target engagement of osimertinib against the "
            "C797S-containing kinase in an isolated-enzyme mobility-shift assay. It does not, by itself, prove "
            "cellular or clinical resistance, and because osimertinib is covalent this IC50 is time-dependent "
            "rather than an equilibrium constant. Source: Melis et al. 2026, Table 2 (DOI 10.3389/fonc.2026.1952701)."),
        required_facts=[num(2.82), num(574), num(204, "fold"), kw("biochemical"),
                        kw("does not"), kw(["cellular", "clinical"], any_of=True),
                        kw(["covalent", "time-dependent"], any_of=True)],
        forbidden_facts=[kw(["proves clinical resistance", "confirms patient resistance"], any_of=True,
                            label="overclaim: biochemical proves clinical")],
        expected_citations=[MELIS], requires_hedge=True,
    ),
    dict(
        id="RI02", task_type="resistance_interpretation",
        question=("Osimertinib's biochemical IC50 against L858R/C797S is 574 nM at Km,ATP but >10000 nM at 1 mM ATP. "
                  "Explain the difference and how to read the 1 mM value."),
        reference_answer=(
            "Osimertinib is ATP-competitive, so raising ATP from Km to a saturating 1 mmol/L shifts the apparent "
            "IC50 upward: 574 nM at Km,ATP versus >10000 nM at 1 mM ATP against L858R/C797S. The 1 mM value is "
            "right-censored (reported as greater-than 10000 nM), so it is a lower bound, not a point estimate, and "
            "the two numbers are not directly comparable across ATP conditions. Source: Melis et al. 2026, Table 2 "
            "(DOI 10.3389/fonc.2026.1952701)."),
        required_facts=[num(574), num(10000), kw(["ATP-competitive", "ATP"], any_of=True),
                        kw(["right-censored", "censored", "lower bound"], any_of=True),
                        kw(["1 mM", "1 mmol"], any_of=True), kw("not")],
        expected_citations=[MELIS], requires_hedge=True,
    ),
    dict(
        id="RI03", task_type="resistance_interpretation",
        question="Mechanistically, why does C797S specifically abolish osimertinib activity while sparing some other inhibitor classes?",
        reference_answer=(
            "Osimertinib works by forming a covalent acrylamide bond to the Cys797 thiol. C797S replaces that "
            "cysteine with serine, removing the nucleophile, so osimertinib cannot anchor covalently and its "
            "irreversible inhibition is lost. Inhibitor classes that do not depend on Cys797 - reversible "
            "ATP-competitive fourth-generation agents (e.g. BLU-945) and allosteric inhibitors (e.g. JBJ-09-063) - "
            "can retain activity against C797S-containing kinases. This is a structural rationale; actual potency "
            "against any given variant still requires measurement. Source: EVIDENCE_00036; Melis et al. 2026 "
            "(DOI 10.3389/fonc.2026.1952701)."),
        required_facts=[kw("C797S"), kw("covalent"), kw(["Cys797", "797"], any_of=True),
                        kw(["serine", "Ser"]), kw(["reversible", "allosteric"], any_of=True),
                        kw(["BLU-945", "JBJ"], any_of=True),
                        kw(["requires measurement", "still requires", "measurement"], any_of=True)],
        expected_citations=[MELIS, "EVIDENCE_00036"], requires_hedge=True,
    ),
    dict(
        id="RI04", task_type="resistance_interpretation",
        question=("What is osimertinib's biochemical IC50 against the L858R/T790M/C797S triple mutant in Melis Table 2, "
                  "and how should the answer report it?"),
        reference_answer=(
            "Melis et al. 2026 Table 2 does not report a value for osimertinib against L858R/T790M/C797S at Km,ATP "
            "(it is listed as not determined, n.d.). The answer must therefore say the value is not available / "
            "not determined rather than supply a number. Independently, the triple mutant is described in the "
            "literature as conferring broad EGFR-TKI resistance. Sources: Melis et al. 2026 (DOI 10.3389/fonc.2026.1952701); "
            "EVIDENCE_00026 (broad triple-mutant resistance)."),
        required_facts=[kw(["L858R/T790M/C797S", "triple"], any_of=True),
                        kw(["not determined", "n.d.", "not available"], any_of=True),
                        kw(["broad", "resistance"], any_of=True)],
        forbidden_facts=[numany([(125, "nM"), (574, "nM"), (1.57, "nM")],
                                label="overclaim: invented triple-mutant osimertinib IC50")],
        expected_citations=[MELIS, "EVIDENCE_00026"], requires_hedge=True,
    ),
    dict(
        id="RI05", task_type="resistance_interpretation",
        question="Why is gefitinib (a first-generation EGFR-TKI) ineffective against T790M-bearing EGFR?",
        reference_answer=(
            "Gefitinib is a reversible, ATP-competitive first-generation quinazoline EGFR-TKI. T790M is the "
            "gatekeeper substitution that adds steric bulk in the ATP pocket and raises the kinase's ATP affinity, "
            "so an ATP-competitive first-generation inhibitor like gefitinib is outcompeted and loses activity. "
            "This is why T790M is the classic resistance mechanism to first/second-generation TKIs. Source: curated "
            "compound annotation (gefitinib, 1st-gen, inactive vs T790M); mechanism EVIDENCE_00006 "
            "(DOI 10.4103/ijp.ijp_1341_25)."),
        required_facts=[kw("gefitinib"), kw(["reversible", "ATP-competitive"], any_of=True),
                        kw(["first-generation", "1st-gen"], any_of=True), kw("T790M"),
                        kw("gatekeeper"), kw("ATP"), kw("resistance")],
        expected_citations=["10.4103/ijp.ijp_1341_25", "EVIDENCE_00006"], requires_hedge=False,
    ),
    dict(
        id="RI06", task_type="resistance_interpretation",
        question=("BLU-945's biochemical IC50 against L858R/C797S is 6.32 nM, versus 574 nM for osimertinib against "
                  "the same variant (Km,ATP). What does this indicate about overcoming C797S resistance?"),
        reference_answer=(
            "Against L858R/C797S at Km,ATP, BLU-945 has a biochemical IC50 of 6.32 nM versus 574 nM for osimertinib - "
            "BLU-945 is roughly 91-fold more potent on this enzyme. BLU-945 is a fourth-generation reversible, "
            "ATP-competitive inhibitor that does not rely on the Cys797 covalent anchor, which is the rationale for "
            "its retained activity against C797S-containing kinases. This is a biochemical enzyme readout and does "
            "not by itself establish cellular or clinical benefit. Sources: Melis et al. 2026 Table 2 "
            "(DOI 10.3389/fonc.2026.1952701); EVIDENCE_00016."),
        required_facts=[num(6.32), num(574), num(91, "fold"), kw("reversible"),
                        kw(["fourth-generation", "4th-gen"], any_of=True), kw("does not"),
                        kw(["cellular", "clinical"], any_of=True)],
        expected_citations=[MELIS, "EVIDENCE_00016"], requires_hedge=True,
    ),

    # ---------------- inhibitor_comparison ---------------- #
    dict(
        id="IC01", task_type="inhibitor_comparison",
        question=("On EGFR L858R/C797S at Km,ATP, rank osimertinib (574 nM), BLU-945 (6.32 nM) and JBJ-09-063 "
                  "(32.9 nM) by biochemical potency and note the caveat."),
        reference_answer=(
            "By biochemical enzyme IC50 at Km,ATP against L858R/C797S, most-to-least potent is: BLU-945 (6.32 nM) > "
            "JBJ-09-063 (32.9 nM) > osimertinib (574 nM) - a lower IC50 means stronger inhibition. BLU-945 "
            "(reversible, 4th-gen) and JBJ-09-063 (allosteric) do not depend on Cys797, unlike covalent osimertinib. "
            "These are isolated-enzyme values and are not interchangeable with cellular or clinical potency. Source: "
            "Melis et al. 2026 Table 2 (DOI 10.3389/fonc.2026.1952701)."),
        required_facts=[num(6.32), num(32.9), num(574), kw(["lower", "stronger"], any_of=True),
                        kw("allosteric"), kw(["not interchangeable", "not", "cellular"], any_of=True)],
        expected_citations=[MELIS], requires_hedge=True,
    ),
    dict(
        id="IC02", task_type="inhibitor_comparison",
        question="BLU-945 inhibits wild-type EGFR with IC50 86.0 nM and L858R/T790M with 4.7 nM (Km,ATP). Interpret the selectivity.",
        reference_answer=(
            "BLU-945 is more potent against the L858R/T790M double mutant (4.7 nM) than against wild-type EGFR "
            "(86.0 nM) - about 18-fold mutant-selectivity by biochemical IC50. Mutant-over-WT selectivity is "
            "desirable because it suggests a wider therapeutic window against the oncogenic kinase relative to "
            "wild-type. This is a biochemical enzyme readout only and does not establish cellular selectivity or "
            "clinical tolerability. Source: Melis et al. 2026 Table 2 (DOI 10.3389/fonc.2026.1952701)."),
        required_facts=[num(86.0), num(4.7), num(18, "fold"),
                        kw(["mutant-selectiv", "selectivity"], any_of=True), kw("does not")],
        expected_citations=[MELIS], requires_hedge=True,
    ),
    dict(
        id="IC03", task_type="inhibitor_comparison",
        question=("JBJ-09-063's biochemical IC50 is 32.9 nM against L858R/C797S but >10000 nM against ex19del/C797S "
                  "(Km,ATP). What does this say about allosteric inhibitors?"),
        reference_answer=(
            "JBJ-09-063 is an allosteric (non-ATP-site) EGFR inhibitor. Its biochemical potency is strongly "
            "context-dependent: 32.9 nM against L858R/C797S but right-censored at >10000 nM against ex19del/C797S at "
            "Km,ATP (essentially inactive up to the highest concentration tested). Allosteric inhibitor activity "
            "depends on the specific driver/resistance combination, so potency cannot be generalised across variants "
            "and must be measured per genotype. Source: Melis et al. 2026 Table 2 (DOI 10.3389/fonc.2026.1952701)."),
        required_facts=[num(32.9), num(10000), kw("allosteric"),
                        kw(["context-dependent", "depends", "cannot be generalised", "must be measured"], any_of=True),
                        kw(["right-censored", "censored", "inactive"], any_of=True)],
        expected_citations=[MELIS], requires_hedge=True,
    ),
    dict(
        id="IC04", task_type="inhibitor_comparison",
        question="Silevertinib's biochemical IC50 is 0.219 nM against L858R but 149 nM against L858R/T790M (Km,ATP). Interpret.",
        reference_answer=(
            "Silevertinib is a fourth-generation covalent EGFR-TKI. It is extremely potent against L858R "
            "(0.219 nM) but much weaker against L858R/T790M (149 nM) at Km,ATP - roughly a 680-fold loss when the "
            "T790M gatekeeper is co-present. So this covalent 4th-generation agent retains sub-nanomolar potency on "
            "some singles but loses potency when T790M co-occurs. This is an isolated-enzyme IC50 and does not by "
            "itself predict cellular or clinical response. Source: Melis et al. 2026 Table 2 (DOI 10.3389/fonc.2026.1952701)."),
        required_facts=[num(0.219), num(149), num(680, "fold"), kw("T790M"), kw("covalent"), kw("does not")],
        expected_citations=[MELIS], requires_hedge=True,
    ),
    dict(
        id="IC05", task_type="inhibitor_comparison",
        question="Compare gefitinib and osimertinib by generation and binding mechanism, and their expected behaviour against T790M.",
        reference_answer=(
            "Gefitinib is a first-generation, reversible ATP-competitive quinazoline EGFR-TKI; osimertinib is a "
            "third-generation irreversible covalent TKI that bonds Cys797 via an acrylamide warhead. Against T790M, "
            "gefitinib is inactive (the gatekeeper raises ATP affinity and sterically hinders first-generation "
            "binding), whereas osimertinib was designed to retain activity against T790M-bearing activating mutants. "
            "Mechanism and generation are curated annotations; variant-specific potency still requires measured data. "
            "Sources: curated compound annotations; EVIDENCE_00036 (osimertinib covalent Cys797; DOI 10.3389/fonc.2026.1952701)."),
        required_facts=[kw("gefitinib"), kw("osimertinib"),
                        kw(["first-generation", "1st-gen"], any_of=True),
                        kw(["third-generation", "3rd-gen"], any_of=True),
                        kw("reversible"), kw("covalent"), kw("T790M"),
                        kw(["Cys797", "acrylamide"], any_of=True)],
        expected_citations=[MELIS, "EVIDENCE_00036"], requires_hedge=False,
    ),
    dict(
        id="IC06", task_type="inhibitor_comparison",
        question="Osimertinib's biochemical IC50 against L858R is 2.82 nM at Km,ATP but 52.5 nM at 1 mM ATP. Why do these differ and which is more physiological?",
        reference_answer=(
            "Osimertinib is ATP-competitive, so its apparent IC50 depends on assay ATP concentration: 2.82 nM at "
            "Km,ATP rises to 52.5 nM at 1 mmol/L ATP against L858R. The 1 mM ATP condition is closer to the high "
            "intracellular ATP concentrations found in cells, so it is often considered the more physiologically "
            "stringent readout, while Km,ATP maximises apparent potency. Neither value is a cellular or clinical "
            "measurement, and a biochemical IC50 does not by itself predict cellular response. Source: Melis et al. "
            "2026 Table 2 (DOI 10.3389/fonc.2026.1952701)."),
        required_facts=[num(2.82), num(52.5), kw(["ATP-competitive", "ATP"], any_of=True),
                        kw(["1 mM", "1 mmol"], any_of=True),
                        kw(["physiolog", "intracellular"], any_of=True), kw("Km")],
        expected_citations=[MELIS], requires_hedge=True,
    ),

    # ---------------- assay_distinction ---------------- #
    dict(
        id="AD01", task_type="assay_distinction",
        question="Why must KD, Ki and IC50 values not be pooled into a single affinity training target?",
        reference_answer=(
            "KD, Ki and IC50 are different physical quantities measured under different models and conditions. KD "
            "is an equilibrium dissociation constant (direct binding); Ki is an inhibition constant from an "
            "enzyme-kinetic model; IC50 is the concentration giving 50% inhibition in a specific assay and depends "
            "on substrate/ATP concentration and assay format, and for covalent drugs it is time-dependent. Pooling "
            "them conflates distinct measurements, so they cannot be pooled and must be kept separate - in this dataset only biochemical "
            "IC50 with relation '=' feeds the regression target, while KD/Ki are held out as an incompatible scale. "
            "Source: Yun et al. 2008 (KD; DOI 10.1073/pnas.0709662105); dataset eligibility rules."),
        required_facts=[kw("KD"), kw("Ki"), kw("IC50"),
                        kw(["equilibrium", "dissociation constant"], any_of=True),
                        kw(["inhibition constant"], any_of=True),
                        kw(["ATP", "substrate", "assay format"], any_of=True),
                        kw(["time-dependent", "covalent"], any_of=True),
                        kw(["separate", "distinct", "not pooled"], any_of=True)],
        expected_citations=[YUN], requires_hedge=True,
    ),
    dict(
        id="AD02", task_type="assay_distinction",
        question="Distinguish a biochemical enzyme IC50 from a cellular viability IC50 for osimertinib, using the dataset's values.",
        reference_answer=(
            "A biochemical enzyme IC50 measures inhibition of the isolated kinase (e.g. osimertinib 574 nM against "
            "L858R/C797S at Km,ATP in a Carna mobility-shift assay). A cellular viability IC50 measures the drug "
            "concentration that halves cell viability in intact cells (e.g. osimertinib 2950 nM in clone-1 "
            "NCI-H1975 cells carrying L858R/T790M/C797S, ATPlite readout). These are different assay layers - target "
            "engagement versus cellular effect - and one must not be presented as the other; cell permeability, "
            "efflux and off-target effects separate them. Source: Melis et al. 2026 (DOI 10.3389/fonc.2026.1952701)."),
        required_facts=[num(574), num(2950), kw("biochemical"),
                        kw(["cellular", "viability"], any_of=True), kw("NCI-H1975"),
                        kw(["must not", "different"], any_of=True)],
        expected_citations=[MELIS], requires_hedge=True,
    ),
    dict(
        id="AD03", task_type="assay_distinction",
        question="Why is a covalent inhibitor's IC50 (e.g. osimertinib) not an equilibrium affinity, and how is it flagged in the data?",
        reference_answer=(
            "For a covalent inhibitor like osimertinib, inhibition increases with incubation time as the "
            "irreversible bond accumulates, so the measured IC50 is time-dependent and is not an equilibrium "
            "constant such as KD. In this dataset covalent osimertinib measurements are flagged "
            "'covalent_time_dependent_IC50' and routed to requires_review, excluded from the biochemical regression "
            "target. Reporting such an IC50 as an equilibrium binding affinity would be incorrect, because they are "
            "not the same quantity. Source: dataset "
            "quality flags; Melis et al. 2026 (DOI 10.3389/fonc.2026.1952701)."),
        required_facts=[kw("covalent"), kw("time-dependent"), kw("osimertinib"),
                        kw("equilibrium"), kw(["KD", "dissociation"], any_of=True),
                        kw(["requires_review", "excluded", "regression target"], any_of=True),
                        kw(["not", "incorrect"], any_of=True)],
        expected_citations=[MELIS], requires_hedge=True,
    ),
    dict(
        id="AD04", task_type="assay_distinction",
        question=("BindingDB lists gefitinib against T790M with a KD of 4.6 nM and IC50 values spanning 22.5-853 nM. "
                  "Why are these not interchangeable, and what caveat applies?"),
        reference_answer=(
            "The 4.6 nM KD is an equilibrium dissociation constant (direct binding; Yun et al. 2008), whereas the "
            "22.5-853 nM figures are IC50 values - functional inhibition concentrations that depend on assay format "
            "and ATP/substrate levels - so they measure different things and must not be equated or averaged "
            "together. The wide IC50 spread also reflects that BindingDB aggregates medians across multiple "
            "publications and assay formats, so apparent gaps may be inter-laboratory/protocol variation rather "
            "than true pharmacological differences. Sources: Yun et al. 2008 (DOI 10.1073/pnas.0709662105); "
            "BindingDB aggregated records."),
        required_facts=[num(4.6), numany([(22.5, "nM"), (853, "nM")]), kw("KD"), kw("IC50"),
                        kw(["equilibrium", "dissociation"], any_of=True),
                        kw(["aggregat", "median", "inter-laboratory", "protocol"], any_of=True),
                        kw(["must not", "different", "not"], any_of=True)],
        expected_citations=[YUN], requires_hedge=True,
    ),
    dict(
        id="AD05", task_type="assay_distinction",
        question="What is the affinity label convention for the Boltz-2 regression target in this dataset, and which measurements are excluded?",
        reference_answer=(
            "The Boltz-2 affinity label is log10(IC50 in micromolar): boltz_target_value = log10(IC50_nM) minus 3, "
            "where LOWER values mean STRONGER binding; it is NOT pIC50. Only eligible biochemical IC50 rows with "
            "relation '=' and a known non-covalent construct feed the target. Covalent/time-dependent IC50s (e.g. "
            "osimertinib), KD/Ki (incompatible scale) and cellular EC50 (ineligible assay type) are excluded. "
            "Source: dataset eligibility rules and DATASET_MANIFEST."),
        required_facts=[kw("log10(IC50"), kw(["micromolar", "uM", "µM"], any_of=True),
                        kw("lower"), kw("stronger"), kw(["not pic50"], any_of=True),
                        kw(["covalent", "excluded"], any_of=True), kw(["KD", "Ki"], any_of=True),
                        kw(["cellular", "EC50"], any_of=True)],
        expected_citations=[], requires_hedge=False,
    ),
    dict(
        id="AD06", task_type="assay_distinction",
        question="Does the dataset provide numeric cellular IC50/GI50 values for the EGFR inhibitors? Answer truthfully.",
        reference_answer=(
            "No. The curated cellular_assays.csv is intentionally header-only: Melis 2026 reports cell-viability "
            "data (an engineered NCI-H1975 model and a 113-cell-line panel) but the numeric values live in "
            "supplementary tables that were not acquired, so under the no-fabrication rule no general cellular "
            "IC50/GI50 numbers were entered. A few specific cellular points are captured as cited primary evidence "
            "(e.g. osimertinib 11.7 nM in parental NCI-H1975), but a general cellular IC50 table is not available "
            "and must not be invented. Source: CELLULAR_ASSAYS_NOTE; Melis et al. 2026 (DOI 10.3389/fonc.2026.1952701)."),
        required_facts=[kw("not"), kw(["header-only", "cellular_assays"], any_of=True),
                        kw(["not acquired", "supplementary", "not available"], any_of=True),
                        kw(["no-fabrication", "must not", "invented"], any_of=True)],
        expected_citations=[MELIS], requires_hedge=True,
    ),

    # ---------------- evidence_qa ---------------- #
    dict(
        id="EQ01", task_type="evidence_qa",
        question="Give the DOI and PMID for the Melis et al. 2026 comparative profiling paper that is the primary source for the biochemical IC50 panel.",
        reference_answer=(
            "The Melis et al. 2026 paper 'Comparative profiling of osimertinib and fourth-generation EGFR "
            "inhibitors on EGFR-mutant proteins and cell lines' has DOI 10.3389/fonc.2026.1952701 and PMID "
            "42835192 (Frontiers in Oncology). Source: REFERENCES.csv / SOURCE_00013."),
        required_facts=[kw("10.3389/fonc.2026.1952701"), kw("42835192")],
        expected_citations=[MELIS, "42835192"], requires_hedge=False,
    ),
    dict(
        id="EQ02", task_type="evidence_qa",
        question="Provide a traceable citation for the claim that EGFR C797S is an acquired on-target resistance mechanism to osimertinib.",
        reference_answer=(
            "EGFR C797S as an acquired on-target osimertinib resistance mechanism in NSCLC is supported in the "
            "dataset by EVIDENCE_00001 - for example Li HJ et al. 2026, 'Repurposing of abemaciclib to overcome "
            "C797S-mediated osimertinib resistance...' (DOI 10.1186/s12929-026-01297-0, PMID 43021317) - among five "
            "catalogued sources (EVIDENCE_00001 to EVIDENCE_00005). Source: biological_evidence.csv."),
        required_facts=[kw("C797S"), kw("resistance"), kw("osimertinib"), kw("EVIDENCE_00001")],
        expected_citations=["10.1186/s12929-026-01297-0", "43021317", "EVIDENCE_00001"], requires_hedge=False,
    ),
    dict(
        id="EQ03", task_type="evidence_qa",
        question="What source supports BLU-945 being active against C797S-containing EGFR mutants?",
        reference_answer=(
            "BLU-945 as a fourth-generation reversible EGFR inhibitor active against C797S-containing mutants is "
            "catalogued as EVIDENCE_00016 to EVIDENCE_00020, including Melis et al. 2026 (DOI 10.3389/fonc.2026.1952701, "
            "PMID 42835192) and a structure-guided reversible-C797S-inhibitor study (DOI 10.1038/s41598-026-51989-8). "
            "Source: biological_evidence.csv."),
        required_facts=[kw("BLU-945"), kw("C797S"), kw(["EVIDENCE_00016", "reversible"], any_of=True)],
        expected_citations=[MELIS, "EVIDENCE_00016", "10.1038/s41598-026-51989-8"], requires_hedge=False,
    ),
    dict(
        id="EQ04", task_type="evidence_qa",
        question="Cite the evidence that osimertinib binds Cys797 covalently via an acrylamide warhead.",
        reference_answer=(
            "Osimertinib's covalent acrylamide bond to Cys797 as its binding mechanism is catalogued as "
            "EVIDENCE_00036 to EVIDENCE_00040, including Melis et al. 2026 (DOI 10.3389/fonc.2026.1952701) and a "
            "Cys-targeting mechanism study (DOI 10.1021/acscentsci.6c01219, PMID 42964983). Source: biological_evidence.csv."),
        required_facts=[kw("covalent"), kw(["Cys797", "797"], any_of=True), kw("acrylamide"),
                        kw("EVIDENCE_00036")],
        expected_citations=["EVIDENCE_00036", MELIS, "10.1021/acscentsci.6c01219"], requires_hedge=False,
    ),
    dict(
        id="EQ05", task_type="evidence_qa",
        question="What evidence supports G719A, S768I and L861Q as atypical activating EGFR mutations with variable TKI sensitivity?",
        reference_answer=(
            "G719X, S768I and L861Q as atypical activating EGFR mutations with variable TKI sensitivity are "
            "supported by EVIDENCE_00031 to EVIDENCE_00035, including a real-world rare-EGFR study "
            "(DOI 10.21037/tlcr-2026-0953) and an uncommon-compound-mutation report (DOI 10.1016/j.cllc.2026.05.005). "
            "Source: biological_evidence.csv."),
        required_facts=[kw(["atypical", "uncommon"], any_of=True), kw("activating"),
                        kw(["S768I", "L861Q", "G719"], any_of=True), kw("EVIDENCE_00031")],
        expected_citations=["10.21037/tlcr-2026-0953", "EVIDENCE_00031", "10.1016/j.cllc.2026.05.005"],
        requires_hedge=False,
    ),
    dict(
        id="EQ06", task_type="evidence_qa",
        question="If asked for a randomized controlled trial PMID proving BLU-945 cures C797S NSCLC patients, how should the model respond?",
        reference_answer=(
            "The model must not invent a citation. The dataset contains biochemical and literature evidence that "
            "BLU-945 is a fourth-generation reversible inhibitor active against C797S-containing kinases "
            "(EVIDENCE_00016 to EVIDENCE_00020), but it contains no randomized controlled trial or clinical-cure "
            "evidence, and BLU-945 is annotated as investigational. The correct response is to state that no such "
            "trial citation is available in the dataset rather than supply a PMID. Source: biological_evidence.csv; "
            "compounds.csv (BLU-945 investigational)."),
        required_facts=[kw(["must not", "not invent"], any_of=True), kw("BLU-945"),
                        kw("investigational"),
                        kw(["no randomized", "no randomised", "no clinical", "no such trial"], any_of=True)],
        expected_citations=["EVIDENCE_00016"], requires_hedge=True,
    ),
]


def main():
    bench_path = HERE / "scientific_benchmark.jsonl"
    ref_path = HERE / "reference_answers.jsonl"
    with bench_path.open("w", encoding="utf-8") as bf, ref_path.open("w", encoding="utf-8") as rf:
        for it in ITEMS:
            bench = {
                "id": it["id"],
                "task_type": it["task_type"],
                "question": it["question"],
                "required_facts": it["required_facts"],
                "forbidden_facts": it.get("forbidden_facts", []),
                "expected_citations": it["expected_citations"],
                "requires_hedge": it["requires_hedge"],
            }
            bf.write(json.dumps(bench, ensure_ascii=False) + "\n")
            rf.write(json.dumps({
                "id": it["id"],
                "task_type": it["task_type"],
                "reference_answer": it["reference_answer"],
            }, ensure_ascii=False) + "\n")
    by_type = {}
    for it in ITEMS:
        by_type[it["task_type"]] = by_type.get(it["task_type"], 0) + 1
    print(f"Wrote {len(ITEMS)} items to {bench_path.name} and {ref_path.name}")
    for t, n in sorted(by_type.items()):
        print(f"  {t}: {n}")


if __name__ == "__main__":
    main()
