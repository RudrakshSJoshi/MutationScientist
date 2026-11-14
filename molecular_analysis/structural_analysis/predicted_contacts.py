#!/usr/bin/env python3
"""Extract confidence and pocket contacts from an EGFR Boltz mmCIF structure."""

import argparse
import csv
from pathlib import Path

from Bio.Align import PairwiseAligner
import gemmi
import numpy as np

LANDMARKS = {745, 746, 747, 748, 749, 750, 790, 793, 797, 858}


def heavy_atoms(residue):
    return [atom for atom in residue if atom.element.name not in {"H", "D"}]


def measure(source, wt_fasta, complex_id, protein_id, ligand_id):
    model = gemmi.read_structure(str(source))[0]
    protein, ligand = model[protein_id], model[ligand_id]
    residues = [residue for residue in protein if residue.find_atom("CA", "\x00")]
    sequence = "".join(gemmi.find_tabulated_residue(residue.name).one_letter_code for residue in residues)
    reference = "".join(line.strip() for line in wt_fasta.read_text().splitlines() if not line.startswith(">"))
    aligner = PairwiseAligner()
    aligner.match_score = 2
    aligner.mismatch_score = -1
    aligner.open_gap_score = -10
    aligner.extend_gap_score = -1
    alignment = aligner.align(reference, sequence)[0]
    numbered = {int(i) + 1: residues[j] for i, j in alignment.indices.T if i >= 0 and j >= 0}
    # This verifies the EGFR gatekeeper and hinge landmarks were mapped to the correct region.
    if len(numbered) < 300 or numbered[790].name not in {"THR", "MET"} or numbered[793].name != "MET":
        raise ValueError("Alignment did not preserve the canonical EGFR hinge and gatekeeper")
    ligand_atoms = [atom for residue in ligand for atom in heavy_atoms(residue)]
    if not ligand_atoms:
        raise ValueError("Ligand chain has no heavy atoms")
    lig_xyz = np.array([[atom.pos.x, atom.pos.y, atom.pos.z] for atom in ligand_atoms])
    result = []
    for position in sorted(numbered.keys() | LANDMARKS):
        residue = numbered.get(position)
        atoms = heavy_atoms(residue) if residue else []
        row = dict(complex_id=complex_id, provenance="pretrained Boltz-2 prediction",
                   clinical_position=position, residue= residue.name if residue else "",
                   protein_atom="", ligand_atom="", min_distance_A="", protein_ca_plddt="",
                   ligand_atom_plddt="", status="no_resolved_atoms")
        if atoms:
            xyz = np.array([[atom.pos.x, atom.pos.y, atom.pos.z] for atom in atoms])
            distances = np.linalg.norm(xyz[:, None] - lig_xyz[None, :], axis=2)
            i, j = np.unravel_index(distances.argmin(), distances.shape)
            d = float(distances[i, j])
            row.update(protein_atom=atoms[i].name, ligand_atom=ligand_atoms[j].name,
                       min_distance_A=round(d, 3),
                       protein_ca_plddt=round(residue.find_atom("CA", "\x00").b_iso, 2),
                       ligand_atom_plddt=round(ligand_atoms[j].b_iso, 2),
                       status="within_4A" if d <= 4.0 else "outside_4A")
        if position in LANDMARKS or row["status"] == "within_4A":
            result.append(row)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("structure", type=Path)
    parser.add_argument("wt_fasta", type=Path, help="Single-sequence canonical UniProt P00533 FASTA")
    parser.add_argument("complex_id")
    parser.add_argument("out", type=Path)
    parser.add_argument("--protein-chain", default="A")
    parser.add_argument("--ligand-chain", default="B")
    args = parser.parse_args()
    rows = measure(args.structure, args.wt_fasta, args.complex_id, args.protein_chain, args.ligand_chain)
    with args.out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
