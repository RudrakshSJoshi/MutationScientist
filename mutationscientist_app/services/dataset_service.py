"""
dataset_service.py — the single source of truth for everything the app reads
from EGFR_RESEARCH_DATASET.

It wraps the project's own `egfr_dataset_loader.EGFRDataset` (pure stdlib) and
adds the extra curated tables the loader does not surface (biological evidence,
mutation profiles, structure index, bindingdb ligands, references).

It NEVER invents records. Lookups that have no data return empty — the UI shows
"no data for this combination" rather than a fabricated row.
"""
from __future__ import annotations
import csv, sys, importlib.util
from pathlib import Path
from functools import lru_cache

import config.settings as S

csv.field_size_limit(10_000_000)


# --------------------------------------------------------------------------- discovery
def _search_up(start: Path, predicate, levels: int = 6):
    cur = start
    for _ in range(levels):
        hit = predicate(cur)
        if hit:
            return hit
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def find_dataset_root() -> Path:
    pinned = S.env(S.ENV_DATASET_ROOT)
    if pinned:
        p = Path(pinned).expanduser().resolve()
        if (p / "DATASET_MANIFEST.json").exists():
            return p
        raise FileNotFoundError(f"{S.ENV_DATASET_ROOT}={p} has no DATASET_MANIFEST.json")
    hit = _search_up(
        S.APP_DIR,
        lambda d: (d / S.DATASET_DIRNAME / "DATASET_MANIFEST.json").exists()
        and (d / S.DATASET_DIRNAME),
    )
    if hit:
        return hit.resolve()
    raise FileNotFoundError(
        f"Could not find '{S.DATASET_DIRNAME}/' above {S.APP_DIR}. "
        f"Set {S.ENV_DATASET_ROOT} to its path."
    )


def find_loader_path() -> Path:
    pinned = S.env(S.ENV_LOADER_PATH)
    if pinned:
        p = Path(pinned).expanduser().resolve()
        if p.exists():
            return p
        raise FileNotFoundError(f"{S.ENV_LOADER_PATH}={p} does not exist")
    hit = _search_up(S.APP_DIR, lambda d: (d / S.LOADER_FILENAME).exists() and (d / S.LOADER_FILENAME))
    if hit:
        return hit.resolve()
    raise FileNotFoundError(
        f"Could not find '{S.LOADER_FILENAME}' above {S.APP_DIR}. Set {S.ENV_LOADER_PATH}."
    )


def _import_loader(loader_path: Path):
    spec = importlib.util.spec_from_file_location("egfr_dataset_loader", loader_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["egfr_dataset_loader"] = mod
    spec.loader.exec_module(mod)
    return mod


def _read_csv(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(newline="") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------- service
class DatasetService:
    def __init__(self, dataset_root: Path | None = None, loader_path: Path | None = None):
        self.root = Path(dataset_root).resolve() if dataset_root else find_dataset_root()
        self.loader_path = Path(loader_path).resolve() if loader_path else find_loader_path()
        self._loader = _import_loader(self.loader_path)
        self.ds = self._loader.EGFRDataset(self.root)
        self.label_to_ic50_nM = self._loader.label_to_ic50_nM
        self.ic50_nM_to_label = self._loader.ic50_nM_to_label

        # loader-surfaced
        self.manifest = self.ds.manifest
        self.mutations = self.ds.mutations            # curated/mutations.csv
        self.compounds = self.ds.compounds            # curated/compounds.csv (named panel)
        self.measurements = self.ds.measurements      # curated/affinity_measurements.csv
        self.references = self.ds.references           # REFERENCES.csv
        self.boltz = self.ds.boltz
        self.llm = self.ds.llm

        # extra curated tables the loader does not expose
        c = self.root / "curated"
        self.profiles = _read_csv(c / "mutation_profiles.csv")
        self.evidence = _read_csv(c / "biological_evidence.csv")
        self.bindingdb_ligands = _read_csv(c / "bindingdb_ligands.csv")
        self.structures = _read_csv(c / "protein_structures" / "structures_index.csv")

        # indexes
        self._mut_by_id = {m["mutation_id"]: m for m in self.mutations}
        self._cmp_by_id = {c_["compound_id"]: c_ for c_ in self.compounds}
        self._bdb_by_id = {l["compound_id"]: l for l in self.bindingdb_ligands}
        self._prof_by_id = {p["profile_id"]: p for p in self.profiles}
        self._ref_by_id = {r["source_id"]: r for r in self.references}

    # ---- integrity -------------------------------------------------------
    def status(self) -> dict:
        bc = self.boltz.counts()
        lc = self.llm.counts()
        sk = self.ds.shared_keys()
        return {
            "root": str(self.root),
            "version": self.manifest.get("dataset_version", "?"),
            "boltz": bc,
            "llm": lc,
            "shared": sk,
            "n_mutations": len(self.mutations),
            "n_compounds_named": len(self.compounds),
            "n_bindingdb_ligands": len(self.bindingdb_ligands),
            "n_measurements": len(self.measurements),
            "n_evidence": len(self.evidence),
            "n_structures": len(self.structures),
            "n_references": len(self.references),
        }

    @lru_cache(maxsize=1)
    def validate(self) -> tuple:
        return tuple(self.ds.validate())

    # ---- mutations -------------------------------------------------------
    def list_mutations(self) -> list[dict]:
        return self.mutations

    def get_mutation(self, mutation_id: str) -> dict | None:
        return self._mut_by_id.get(mutation_id)

    def get_profile(self, profile_id: str) -> dict | None:
        return self._prof_by_id.get(profile_id)

    def list_profiles(self) -> list[dict]:
        return self.profiles

    # ---- compounds -------------------------------------------------------
    def list_compounds(self) -> list[dict]:
        """The curated, named inhibitor panel (full annotation)."""
        return self.compounds

    def get_compound(self, compound_id: str) -> dict | None:
        """Named panel compound, or a minimal BindingDB ligand record."""
        if compound_id in self._cmp_by_id:
            return self._cmp_by_id[compound_id]
        bdb = self._bdb_by_id.get(compound_id)
        if bdb:
            return {
                "compound_id": compound_id,
                "compound_name": compound_id,
                "canonical_smiles": bdb.get("smiles", ""),
                "isomeric_smiles": bdb.get("smiles", ""),
                "drug_class": "(BindingDB ligand — minimal record)",
                "covalent_status": "unknown",
                "source_id": "BindingDB",
                "_bindingdb_only": True,
            }
        return None

    def compound_display_name(self, compound_id: str) -> str:
        c = self.get_compound(compound_id)
        return c.get("compound_name") or compound_id if c else compound_id

    # ---- measurements & complexes ---------------------------------------
    def measurements_for(self, mutation_id: str | None = None, compound_id: str | None = None) -> list[dict]:
        rows = self.measurements
        if mutation_id:
            rows = [r for r in rows if r.get("mutation_id") == mutation_id]
        if compound_id:
            rows = [r for r in rows if r.get("compound_id") == compound_id]
        return rows

    def complexes_for(self, mutation_id: str | None = None, compound_id: str | None = None) -> list:
        out = []
        for cx in self.boltz:
            if mutation_id and cx.mutation_id != mutation_id:
                continue
            if compound_id and cx.compound_id != compound_id:
                continue
            out.append(cx)
        return out

    def get_complex(self, complex_id: str):
        for cx in self.boltz:
            if cx.complex_id == complex_id:
                return cx
        return None

    @lru_cache(maxsize=1)
    def available_pairs(self) -> frozenset:
        """(mutation_id, compound_id) pairs that actually have a Boltz complex."""
        return frozenset((cx.mutation_id, cx.compound_id) for cx in self.boltz)

    def compounds_tested_against(self, mutation_id: str) -> list[str]:
        """compound_ids that have at least one complex OR measurement for this mutation."""
        ids = {cx.compound_id for cx in self.boltz if cx.mutation_id == mutation_id}
        ids |= {r["compound_id"] for r in self.measurements if r.get("mutation_id") == mutation_id}
        return sorted(ids)

    def mutations_with_complexes(self) -> list[str]:
        return sorted({cx.mutation_id for cx in self.boltz})

    # ---- structures ------------------------------------------------------
    def structures_for(self, mutation_id: str | None = None) -> list[dict]:
        """
        The structure index is EGFR-wide (RCSB entries for P00533); it is not
        reliably mutation-tagged. We return all entries and let the UI note this,
        rather than guessing a mutation->PDB mapping that the data does not assert.
        """
        return self.structures

    # ---- references ------------------------------------------------------
    def get_reference(self, source_id: str) -> dict | None:
        return self._ref_by_id.get(source_id)
