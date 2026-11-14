#!/usr/bin/env python3
"""Measure deposited experimental EGFR coordinates using clinical residue numbering."""

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
SPECS = {
    "1M17": ("WT", "erlotinib", "AQ4", 24),
    "2ITY": ("WT", "gefitinib", "IRE", 0),
    "2ITZ": ("L858R", "gefitinib", "IRE", 0),
    "6JXT": ("WT at resistance sites", "osimertinib", "YY3", 0),
    "6LUD": ("L858R/T790M/C797S", "osimertinib", "YY3", 0),
    "6LUB": ("L858R/T790M/C797S", "CH7233163", "EUX", 0),
    "2J6M": ("WT", "AEE788", "AEE", 0),
    "2JIU": ("T790M", "AEE788", "AEE", 0),
    "7ZYM": ("T790M/C797S", "brigatinib", "6GY", 0),
    "7TVD": ("L747_E749del", "apo", "", 0),
}
LANDMARKS = (745, 746, 747, 748, 749, 750, 790, 793, 797, 858)
ANCHORS = (718, 719, 720, 721, 723, 726, 744, 745, 768, 769, 772, 788, 789, 791, 792, 793,
           794, 795, 796, 798, 799, 800, 803, 831, 832, 833, 835, 837, 853, 854, 855, 856, 857)
OVERLAYS = (("2ITY", "2ITZ"), ("6JXT", "6LUD"), ("2J6M", "2JIU"), ("6LUD", "6LUB"), ("2ITY", "7TVD"))


def write_csv(name, rows):
    with (ROOT / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def parse(pdb_id):
    state, drug, ligand_name, offset = SPECS[pdb_id]
    lines = (ROOT / "pdb_files" / f"{pdb_id}.pdb").read_text().splitlines()
    source_atoms = [line for line in lines if line.startswith(("ATOM  ", "HETATM"))]
    master = next(line.split() for line in lines if line.startswith("MASTER"))
    if not lines[0].rstrip().endswith(pdb_id) or lines[-1] != "END" or sum(line[16] in {" ", "A"} for line in source_atoms) != int(master[9]):
        raise ValueError(f"Incomplete coordinate file: {pdb_id}")
    coordinates = {}
    for line in source_atoms:
        if line[21] != "A" or line[76:78].strip() in {"H", "D"}:
            continue
        hetero = line.startswith("HETATM")
        residue = line[17:20].strip()
        if hetero and residue != ligand_name:
            continue
        position = int(line[22:26]) + (0 if hetero else offset)
        name = line[12:16].strip()
        key = (hetero, position, line[26], name)
        occupancy = float(line[54:60])
        priority = (occupancy, line[16] in {" ", "A"})
        old = coordinates.get(key)
        if old is None or old[0] < priority:
            xyz = np.array([float(line[i:i+8]) for i in (30, 38, 46)])
            coordinates[key] = (priority, {"xyz": xyz, "residue": residue, "position": position, "name": name})
    protein = [atom for (hetero, *_), (_, atom) in coordinates.items() if not hetero]
    ligand = [atom for (hetero, *_), (_, atom) in coordinates.items() if hetero]
    if bool(ligand_name) != bool(ligand) or not protein:
        raise ValueError(f"Missing chain A components in {pdb_id}")
    resolution = next(float(line.split()[3]) for line in lines if line.startswith("REMARK   2 RESOLUTION."))
    links = [line.rstrip() for line in lines if line.startswith("LINK ") and ligand_name
             and ligand_name in (line[17:20].strip(), line[47:50].strip())]
    return {"id": pdb_id, "state": state, "drug": drug, "ligand": ligand, "protein": protein,
            "resolution": resolution, "offset": offset, "ligand_code": ligand_name, "links": links}


def arrays(atoms):
    return np.array([atom["xyz"] for atom in atoms])


def ca_atoms(structure):
    return {atom["position"]: atom["xyz"] for atom in structure["protein"] if atom["name"] == "CA"}


def fit(reference, moving):
    ref, mov = ca_atoms(reference), ca_atoms(moving)
    positions = [i for i in ANCHORS if i in ref and i in mov]
    target, source = np.array([ref[i] for i in positions]), np.array([mov[i] for i in positions])
    src_c, dst_c = source.mean(axis=0), target.mean(axis=0)
    u, _, vt = np.linalg.svd((source - src_c).T @ (target - dst_c))
    sign = np.diag([1, 1, np.linalg.det(u @ vt)])
    rot = u @ sign @ vt
    return lambda xyz: (xyz - src_c) @ rot + dst_c, target, source


def rmsd(first, second):
    return float(np.sqrt(np.mean(np.sum((first - second) ** 2, axis=-1))))


def contacts(structure):
    rows = []
    prot, lig = structure["protein"], structure["ligand"]
    for position in sorted({atom["position"] for atom in prot} | set(LANDMARKS)):
        atoms = [a for a in prot if a["position"] == position]
        row = {"pdb_id": structure["id"], "provenance": "experimental X-ray",
               "construct": structure["state"], "inhibitor": structure["drug"],
               "clinical_position": position, "residue": atoms[0]["residue"] if atoms else "",
               "residue_atom": "", "ligand_atom": "", "min_distance_A": "",
               "status": "no_ligand" if atoms else "no_resolved_atoms"}
        if atoms and lig:
            distances = np.linalg.norm(arrays(atoms)[:, None] - arrays(lig)[None, :], axis=2)
            i, j = np.unravel_index(distances.argmin(), distances.shape)
            row.update(residue_atom=atoms[i]["name"], ligand_atom=lig[j]["name"],
                       min_distance_A=round(float(distances[i, j]), 3),
                       status="within_4A" if distances[i, j] <= 4.0 else "outside_4A")
        if position in LANDMARKS or row["status"] == "within_4A":
            rows.append(row)
    return rows


def show_overlay(axis, reference, moving, transform):
    lig = arrays(reference["ligand"])
    center = lig.mean(axis=0)
    _, _, vectors = np.linalg.svd(lig - center, full_matrices=False)
    project = lambda xyz: ((xyz - center) @ vectors[:2].T)
    colors = ("#255c90", "#b54137")
    for index, (structure, change) in enumerate(((reference, lambda x: x), (moving, transform))):
        color = colors[index]
        for number, offsets in {790: (-20, 8), 793: (5, -11), 797: (-15, 8)}.items():
            if number in ca_atoms(structure):
                xy = project(change(ca_atoms(structure)[number]))
                axis.scatter(*xy, color=color, s=25, marker=["o", "x"][index], zorder=3)
                if index == 0:
                    axis.annotate(str(number), xy, xytext=offsets, textcoords="offset points", fontsize=8)
        if structure["ligand"]:
            xy = project(change(arrays(structure["ligand"])))
            axis.scatter(*xy.T, color=color, alpha=.66, s=16, label=f"{structure['id']} · {structure['state']}")
    drug = reference["drug"]
    name = drug if drug[0].isupper() else drug.capitalize()
    axis.set_title(f"{name} · {reference['id']} and {moving['id']}", loc="left",
                   fontsize=11, fontweight="bold", pad=12)
    axis.set_aspect("equal", adjustable="datalim")
    axis.grid(alpha=.16)
    axis.set_xlabel("Projected coordinate (Å)")
    axis.set_ylabel("Projected coordinate (Å)")
    axis.legend(fontsize=8, loc="upper center", bbox_to_anchor=(.5, -.22), frameon=False)


def main():
    structures = {pdb_id: parse(pdb_id) for pdb_id in SPECS}
    entries = []
    for pdb_id, entry in structures.items():
        ca = ca_atoms(entry)
        entries.append({
            "pdb_id": pdb_id, "provenance": "experimental X-ray", "construct": entry["state"],
            "inhibitor": entry["drug"], "resolution_A": entry["resolution"], "ligand_code": entry["ligand_code"],
            "author_to_clinical_offset": entry["offset"],
            "deposited_ligand_link": "; ".join(entry["links"]),
            "CA_746_to_750_A": round(float(np.linalg.norm(ca[746] - ca[750])), 3) if {746, 750} <= ca.keys() else "",
            "source": f"https://www.rcsb.org/structure/{pdb_id}",
        })
    write_csv("structure_inventory.csv", entries)
    write_csv("experimental_contacts.csv", [row for entry in structures.values() for row in contacts(entry)])
    figure, axes = plt.subplots(1, 3, figsize=(16.5, 4.7), layout="constrained")
    comparisons = []
    for i, (reference_id, moving_id) in enumerate(OVERLAYS):
        reference, moving = structures[reference_id], structures[moving_id]
        transform, ref_ca, mov_ca = fit(reference, moving)
        same_ligand = reference["ligand_code"] == moving["ligand_code"] and bool(reference["ligand_code"])
        a = {atom["name"]: atom["xyz"] for atom in reference["ligand"]}
        b = {atom["name"]: atom["xyz"] for atom in moving["ligand"]}
        names = sorted(a.keys() & b.keys()) if same_ligand else []
        comparisons.append({
            "reference_pdb_id": reference_id, "mobile_pdb_id": moving_id, "fit_CA_atom_count": len(ref_ca),
            "fit_CA_RMSD_A": round(rmsd(ref_ca, transform(mov_ca)), 3),
            "matched_ligand_atom_count": len(names),
            "ligand_RMSD_A": round(rmsd(np.array([a[n] for n in names]),
                                       transform(np.array([b[n] for n in names]))), 3) if names else "",
        })
        if i < len(axes):
            show_overlay(axes[i], reference, moving, transform)
    figure.suptitle("Deposited EGFR kinase structures · ligand and pocket overlay", fontweight="bold", fontsize=15)
    figure.savefig(ROOT / "visualisations/experimental_pose_overlays.png", dpi=180, facecolor="white")
    write_csv("experimental_overlays.csv", comparisons)
    print(f"{len(structures)} experimental structures, {len(comparisons)} coordinate overlays")


if __name__ == "__main__":
    main()
