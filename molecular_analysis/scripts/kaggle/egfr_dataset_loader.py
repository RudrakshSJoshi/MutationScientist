#!/usr/bin/env python3
# ======================================================================================
# egfr_dataset_loader.py
#
# One loader that exposes the two training inputs in the EGFR_RESEARCH_DATASET:
#   Component 1 (BoltzDataset) -> Boltz-2 affinity-head fine-tuning input
#   Component 2 (LLMDataset)   -> MutationScientist LLM (SFT) input/output
#
# Assumes you have extracted the zip so that everything lives under a folder named
# "EGFR_RESEARCH_DATASET" (the zip's own name).
#
# Usage:
#   python egfr_dataset_loader.py                      # uses ./EGFR_RESEARCH_DATASET
#   python egfr_dataset_loader.py /path/to/EGFR_RESEARCH_DATASET
#   python egfr_dataset_loader.py --describe           # print the exact input formats
#
# As a library:
#   from egfr_dataset_loader import EGFRDataset
#   ds = EGFRDataset("EGFR_RESEARCH_DATASET")
#   boltz = ds.boltz; llm = ds.llm
#   for cx in boltz.split("train"): print(cx.complex_id, cx.affinity_label, cx.ligand_smiles[:20])
#   for ex in llm.split("train"):   print(ex.prompt[:60], "->", ex.completion[:60])
#
# Pure standard library (csv, json, re, pathlib). No third-party dependencies.
# ======================================================================================
from __future__ import annotations
import csv, json, re, sys, argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

# --------------------------------------------------------------------------------------
# The verified Boltz-2 affinity label convention (do not change — see README / dataset docs)
#   affinity_label (the YAML `value`) = log10(IC50 in micromolar)  ==  log10(IC50_nM) - 3
#   LOWER = STRONGER binding.  NOT pIC50.
# --------------------------------------------------------------------------------------
BOLTZ_LABEL_UNIT = "log10(IC50_uM)"
def ic50_nM_to_label(ic50_nM: float) -> float:   # helper: convert a raw IC50 (nM) to the label
    import math; return round(math.log10(ic50_nM) - 3.0, 4)
def label_to_ic50_nM(label: float) -> float:     # inverse
    return 10.0 ** (label + 3.0)

csv.field_size_limit(10_000_000)
def _read_csv(p: Path) -> list[dict]:
    with p.open(newline="") as f: return list(csv.DictReader(f))
def _read_jsonl(p: Path) -> list[dict]:
    if not p.exists(): return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]

# ======================================================================================
# COMPONENT 1 — Boltz-2 affinity fine-tuning
# ======================================================================================
@dataclass
class BoltzComplex:
    """One protein-ligand complex = one Boltz training example.
    The YAML at `yaml_path` is literally what you feed to `boltz predict`."""
    complex_id: str
    split: str                 # "train" | "validation" | "test"
    mutation_id: str           # EGFR_* (-> mutations.csv)
    compound_id: str           # CMP_* or BDB_* (-> compounds.csv / bindingdb_ligands.csv)
    sequence_id: str           # == mutation_id (FASTA record id)
    affinity_label: float      # the training target: log10(IC50 in uM), lower = stronger
    affinity_label_unit: str   # "log10(IC50_uM)"
    n_replicates: int          # how many raw measurements were averaged into this label
    measurement_ids: str       # source MEAS_* ids (';'-joined, truncated in metadata)
    yaml_path: Path            # the Boltz input YAML (absolute)
    msa_path: Path             # the precomputed MSA (.a3m) this complex uses
    protein_sequence: str      # parsed from the YAML (mutant EGFR sequence)
    ligand_smiles: str         # parsed from the YAML

_YAML_SEQ = re.compile(r'sequence:\s*(\S+)')
_YAML_MSA = re.compile(r'msa:\s*(\S+)')
_YAML_SMI = re.compile(r"smiles:\s*'([^']*)'")
_YAML_VAL = re.compile(r'value:\s*([-\d.eE]+)')

def _parse_boltz_yaml(path: Path) -> dict:
    """Minimal parser for this dataset's fixed YAML schema (no PyYAML needed)."""
    t = path.read_text()
    return {
        "sequence": (_YAML_SEQ.search(t) or _re_fail(path, "sequence")).group(1),
        "msa":      (_YAML_MSA.search(t) or _re_fail(path, "msa")).group(1),
        "smiles":   (_YAML_SMI.search(t) or _re_fail(path, "smiles")).group(1),
        "value":    float((_YAML_VAL.search(t) or _re_fail(path, "value")).group(1)),
    }
def _re_fail(path, field): raise ValueError(f"Malformed Boltz YAML {path}: missing '{field}'")

class BoltzDataset:
    """Component 1. Exposes the Boltz-2 affinity fine-tuning input.

    INPUT FORMAT (per complex YAML — this is exactly what `boltz predict` consumes):
        version: 1
        sequences:
          - protein: {id: A, sequence: <mutant EGFR seq>, msa: <path to .a3m>}
          - ligand:  {id: B, smiles: '<ligand SMILES>'}
        properties:
          - affinity: {binder: B, value: <log10(IC50 in uM)>}   # the training label

    Splits are LIGAND-DISJOINT (a given ligand is entirely in one split) -> scaffold-held-out.
    `boltz2/val_names.txt` lists the validation complex names for the repo's `split_file`.
    """
    def __init__(self, root: Path):
        self.root = root
        self.dir = root / "boltz2"
        self.label_unit = BOLTZ_LABEL_UNIT
        self.metadata = _read_csv(self.dir / "complex_metadata.csv")
        self.eligible_rows = _read_csv(self.dir / "boltz_compatible_dataset.csv")  # full labelled index (pre-dedup)
        self.val_names = [l.strip() for l in (self.dir / "val_names.txt").read_text().splitlines() if l.strip()]
        self._complexes: list[BoltzComplex] = []
        for m in self.metadata:
            ypath = root / m["boltz_input_path"]
            parsed = _parse_boltz_yaml(ypath)
            self._complexes.append(BoltzComplex(
                complex_id=m["complex_id"], split=m["split"], mutation_id=m["mutation_id"],
                compound_id=m["compound_id"], sequence_id=m["sequence_id"],
                affinity_label=float(m["affinity_label"]), affinity_label_unit=m["affinity_label_unit"],
                n_replicates=int(m["n_replicates"]), measurement_ids=m["measurement_ids"],
                yaml_path=ypath, msa_path=root / m["msa_path"],
                protein_sequence=parsed["sequence"], ligand_smiles=parsed["smiles"],
            ))

    def split(self, name: str) -> list[BoltzComplex]:
        assert name in ("train", "validation", "test")
        return [c for c in self._complexes if c.split == name]
    def all(self) -> list[BoltzComplex]: return list(self._complexes)
    def __iter__(self) -> Iterator[BoltzComplex]: return iter(self._complexes)
    def __len__(self) -> int: return len(self._complexes)

    def counts(self) -> dict:
        from collections import Counter
        c = Counter(x.split for x in self._complexes)
        return {"total_complexes": len(self._complexes), "eligible_measurement_rows": len(self.eligible_rows),
                "train": c["train"], "validation": c["validation"], "test": c["test"],
                "by_variant": dict(Counter(x.mutation_id for x in self._complexes))}

# ======================================================================================
# COMPONENT 2 — MutationScientist LLM (SFT)
# ======================================================================================
@dataclass
class LLMExample:
    """One SFT example. The model learns INPUT=prompt -> OUTPUT=completion.
    Only `prompt` and `completion` are used for training; the rest is audit metadata."""
    prompt: str            # INPUT  (self-contained: all numbers/context inline)
    completion: str        # OUTPUT (the target answer)
    task_type: str
    mutation_id: str       # EGFR_* link to Component 1 / mutations.csv
    compound_id: str       # CMP_*/BDB_* link to Component 1 / compounds.csv
    source_ids: str        # provenance -> REFERENCES.csv / Melis2026 / UNIPROT_P00533
    review_status: str     # model_generated_grounded | teacher_generated_unverified_autochecked
    annotation_confidence: str
    split: str             # train | validation | test

# AutoScientist raw/SFT upload mapping (only prompt+completion train)
AUTOSCIENTIST_COLUMN_MAPPING = {"prompt": "prompt", "completion": "completion"}
LLM_4B_MIN_SFT_ROWS = 1000   # gemma-3-4b-it / Qwen3.5-4B raw-SFT minimum

class LLMDataset:
    """Component 2. Exposes the LLM SFT input/output.

    INPUT FORMAT (what you upload to the fine-tuning platform): a CSV whose columns are
        prompt, completion, task_type, mutation_id, profile_id, compound_id,
        evidence_ids, source_ids, review_status, annotation_confidence
    Map ONLY prompt->input and completion->output; the rest are metadata for audit/eval.
    """
    def __init__(self, root: Path):
        self.root = root
        self.dir = root / "mutation_scientist"
        self.column_mapping = AUTOSCIENTIST_COLUMN_MAPPING
        self._splits = {}
        for name, fname in (("train","sft_train.csv"),("validation","sft_validation.csv"),("test","sft_test.csv")):
            rows = _read_csv(self.dir / fname)
            self._splits[name] = [LLMExample(
                prompt=r["prompt"], completion=r["completion"], task_type=r.get("task_type",""),
                mutation_id=r.get("mutation_id",""), compound_id=r.get("compound_id",""),
                source_ids=r.get("source_ids",""), review_status=r.get("review_status",""),
                annotation_confidence=r.get("annotation_confidence",""), split=name,
            ) for r in rows]
        # extra assets
        self.source_jsonl = {n: _read_jsonl(self.dir / f"{n}.jsonl") for n in
                             ("mutation_understanding","experimental_evidence_reasoning","research_reasoning","teacher_generated")}
        self.eval_questions = _read_jsonl(self.dir / "eval_questions.jsonl")
        self.preference_pairs = _read_jsonl(self.dir / "preference_pairs.jsonl")  # optional DPO

    def split(self, name: str) -> list[LLMExample]:
        assert name in ("train","validation","test"); return self._splits[name]
    def all(self) -> list[LLMExample]: return [e for s in self._splits.values() for e in s]
    def pairs(self, name: str) -> list[tuple[str,str]]:
        """Just (prompt, completion) tuples for a split — the minimal training signal."""
        return [(e.prompt, e.completion) for e in self._splits[name]]

    def counts(self) -> dict:
        from collections import Counter
        allx = self.all()
        return {"total": len(allx), "train": len(self._splits["train"]),
                "validation": len(self._splits["validation"]), "test": len(self._splits["test"]),
                "by_review_status": dict(Counter(e.review_status for e in allx)),
                "by_task_type": dict(Counter(e.task_type for e in allx)),
                "eval_questions": len(self.eval_questions), "preference_pairs": len(self.preference_pairs)}

    def meets_4b_floor(self) -> dict:
        tr = len(self._splits["train"]); trv = tr + len(self._splits["validation"])
        return {"min_required": LLM_4B_MIN_SFT_ROWS, "train_only": tr, "train_only_ok": tr >= LLM_4B_MIN_SFT_ROWS,
                "train_plus_val": trv, "train_plus_val_ok": trv >= LLM_4B_MIN_SFT_ROWS,
                "recommendation": ("upload sft_train" if tr >= LLM_4B_MIN_SFT_ROWS
                                   else "upload sft_train + sft_validation (and keep sft_test as external eval)")}

# ======================================================================================
# TOP-LEVEL
# ======================================================================================
class EGFRDataset:
    """Loads both components + the shared reference tables (the join keys between them)."""
    def __init__(self, root: str | Path = "EGFR_RESEARCH_DATASET"):
        self.root = Path(root).expanduser().resolve()
        if not (self.root / "DATASET_MANIFEST.json").exists():
            raise FileNotFoundError(f"{self.root} is not an EGFR_RESEARCH_DATASET folder (no DATASET_MANIFEST.json)")
        self.manifest = json.loads((self.root / "DATASET_MANIFEST.json").read_text())
        # shared reference tables (link Component 1 <-> Component 2 by mutation_id / compound_id)
        self.mutations   = _read_csv(self.root / "curated" / "mutations.csv")
        self.compounds   = _read_csv(self.root / "curated" / "compounds.csv")
        self.measurements= _read_csv(self.root / "curated" / "affinity_measurements.csv")
        self.references  = _read_csv(self.root / "REFERENCES.csv")
        self.boltz = BoltzDataset(self.root)
        self.llm   = LLMDataset(self.root)

    def validate(self) -> list[str]:
        """Cheap integrity checks; returns a list of problems (empty = all good)."""
        probs = []
        mut_ids = {m["mutation_id"] for m in self.mutations}
        cmp_ids = {c["compound_id"] for c in self.compounds} | \
                  {r["compound_id"] for r in _read_csv(self.root/"curated"/"bindingdb_ligands.csv")}
        # Boltz: files exist, label present, ids resolve
        for cx in self.boltz:
            if not cx.yaml_path.exists(): probs.append(f"missing YAML {cx.yaml_path}")
            if not cx.msa_path.exists(): probs.append(f"missing MSA {cx.msa_path}")
            if cx.mutation_id not in mut_ids: probs.append(f"{cx.complex_id}: unknown mutation {cx.mutation_id}")
            if cx.compound_id not in cmp_ids: probs.append(f"{cx.complex_id}: unknown compound {cx.compound_id}")
            if cx.protein_sequence == "" or cx.ligand_smiles == "": probs.append(f"{cx.complex_id}: empty seq/smiles")
        # LLM: no empty prompt/completion
        for ex in self.llm.all():
            if not ex.prompt.strip() or not ex.completion.strip(): probs.append("empty LLM prompt/completion")
        return probs

    def shared_keys(self) -> dict:
        bvar = {c.mutation_id for c in self.boltz}; lvar = {e.mutation_id for e in self.llm.all() if e.mutation_id}
        bcmp = {c.compound_id for c in self.boltz}; lcmp = {e.compound_id for e in self.llm.all() if e.compound_id}
        return {"mutation_ids_in_both": sorted(bvar & lvar),
                "n_compound_ids_in_both": len(bcmp & lcmp)}

# ------------------------------- CLI / describe ----------------------------------------
FORMAT_DOC = """
================= INPUT FORMATS EXPOSED BY THIS LOADER =================

COMPONENT 1 — Boltz-2 affinity fine-tuning  (BoltzComplex)
  One complex = one YAML (fed directly to `boltz predict`):
    version: 1
    sequences:
      - protein: {id: A, sequence: <mutant EGFR AA sequence>, msa: <.a3m path>}
      - ligand:  {id: B, smiles: '<ligand SMILES>'}
    properties:
      - affinity: {binder: B, value: <LABEL>}
  LABEL = affinity_label = log10(IC50 in uM) = log10(IC50_nM) - 3 ; LOWER = STRONGER (NOT pIC50).
  Splits: train / validation / test, LIGAND-DISJOINT (scaffold-held-out). val_names.txt -> split_file.
  Also exposed: boltz_compatible_dataset.csv (full 18k eligible measurement rows, pre-dedup).

COMPONENT 2 — MutationScientist LLM (SFT)  (LLMExample)
  Upload CSV columns: prompt, completion, task_type, mutation_id, profile_id, compound_id,
                      evidence_ids, source_ids, review_status, annotation_confidence
  TRAIN SIGNAL: prompt (INPUT) -> completion (OUTPUT). Map only those two; rest = metadata.
  Splits: train / validation / test, MUTATION-held-out (S768I, L861Q -> test; T790M -> val).
  review_status: model_generated_grounded (hand) | teacher_generated_unverified_autochecked (LLM-made, number-checked).

LINK between the two: shared mutation_id (EGFR_*) and compound_id (CMP_*/BDB_*);
  boltz2/complex_metadata.csv maps complex_id -> mutation_id + compound_id + affinity_label.
=======================================================================
"""

def main(argv=None):
    ap = argparse.ArgumentParser(description="Load & sanity-check the EGFR_RESEARCH_DATASET two training inputs.")
    ap.add_argument("root", nargs="?", default="EGFR_RESEARCH_DATASET", help="extracted dataset folder")
    ap.add_argument("--describe", action="store_true", help="print the exact input formats and exit")
    ap.add_argument("--validate", action="store_true", help="run integrity checks")
    args = ap.parse_args(argv)
    if args.describe: print(FORMAT_DOC); return

    ds = EGFRDataset(args.root)
    print(f"Loaded {ds.root}  (version {ds.manifest.get('dataset_version')})\n")
    print("COMPONENT 1 — Boltz-2 affinity fine-tuning")
    bc = ds.boltz.counts()
    print(f"  training complexes (YAMLs): {bc['total_complexes']}  (train {bc['train']} / val {bc['validation']} / test {bc['test']})")
    print(f"  full eligible measurement rows: {bc['eligible_measurement_rows']}")
    print(f"  label unit: {ds.boltz.label_unit}  (log10 IC50 uM; lower=stronger)")
    ex = ds.boltz.split('train')[0]
    print(f"  example: {ex.complex_id}  {ex.mutation_id} + {ex.compound_id}  label={ex.affinity_label} (IC50~{label_to_ic50_nM(ex.affinity_label):.1f} nM)")
    print(f"           YAML={ex.yaml_path.name}  MSA={ex.msa_path.name}  smiles={ex.ligand_smiles[:40]}")
    print("\nCOMPONENT 2 — MutationScientist LLM (SFT)")
    lc = ds.llm.counts()
    print(f"  examples: {lc['total']}  (train {lc['train']} / val {lc['validation']} / test {lc['test']})")
    print(f"  by review_status: {lc['by_review_status']}")
    print(f"  eval_questions: {lc['eval_questions']}  preference_pairs: {lc['preference_pairs']}")
    floor = ds.llm.meets_4b_floor()
    print(f"  4B SFT floor ({floor['min_required']}): train_only={floor['train_only']} ok={floor['train_only_ok']} | "
          f"train+val={floor['train_plus_val']} ok={floor['train_plus_val_ok']}")
    print(f"  -> {floor['recommendation']}")
    le = ds.llm.split('train')[0]
    print(f"  example IN : {le.prompt[:90]}...")
    print(f"  example OUT: {le.completion[:90]}...")
    print("\nLINK (shared keys)")
    sk = ds.shared_keys()
    print(f"  mutation_ids in both components: {len(sk['mutation_ids_in_both'])}")
    print(f"  compound_ids in both components: {sk['n_compound_ids_in_both']}")
    if args.validate:
        probs = ds.validate()
        print(f"\nVALIDATION: {'ALL OK' if not probs else str(len(probs))+' problems'}")
        for p in probs[:20]: print("  -", p)

if __name__ == "__main__":
    main()
