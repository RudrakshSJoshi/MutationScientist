#!/usr/bin/env python3
"""Compare fixed baseline and specialised scores on the same labelled held-out rows."""

import argparse
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pipeline import read_csv, write_csv


def evaluate(dataset, out):
    paired = read_csv(out / "baseline_vs_finetuned.csv")
    if not paired:
        print("No matched pretrained and specialised predictions to evaluate.")
        return
    metadata = {r["complex_id"]: r for r in read_csv(dataset / "boltz2/complex_metadata.csv")}
    if any(r["split"] not in {"validation", "test"} or metadata[r["complex_id"]]["split"] != r["split"] for r in paired):
        raise ValueError("Comparison contains rows outside their supplied held-out splits.")
    overlap = {r["complex_id"]: r["chemical_identity_splits"].split(";")
               for r in read_csv(out / "cross_split_chemical_identities.csv")}
    counts = Counter(r["split"] for r in metadata.values())
    (out / "comparison_plots").mkdir(exist_ok=True)
    results = []
    for split in ("validation", "test"):
        observed = [r for r in paired if r["split"] == split]
        if not observed:
            continue
        fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.4), layout="constrained", sharex=True, sharey=True)
        x = np.array([float(metadata[r["complex_id"]]["affinity_label"]) for r in observed])
        scores = {k: np.array([float(r[f"{k}_affinity_pred_value"]) for r in observed])
                  for k in ("baseline", "specialised")}
        bounds = (min(x.min(), *(p.min() for p in scores.values())),
                  max(x.max(), *(p.max() for p in scores.values())))
        for axis, (name, values) in zip(axes, scores.items()):
            alias_mask = np.array([r["complex_id"] in overlap for r in observed])
            axis.scatter(x[~alias_mask], values[~alias_mask], s=12, alpha=.6, color="#255c90", label="Other rows")
            if alias_mask.any():
                axis.scatter(x[alias_mask], values[alias_mask], s=19, alpha=.8, color="#bf4a3c",
                             label="Chemical identity in another split")
            axis.plot(bounds, bounds, ls="--", lw=1, color="#888888")
            axis.set_title(name.capitalize(), loc="left", fontweight="bold")
            axis.set_xlabel("Experimental log₁₀(IC₅₀ in µM)")
            axis.legend(loc="best", fontsize=7, frameon=False)
        axes[0].set_ylabel("Predicted log₁₀(IC₅₀ in µM)")
        fig.suptitle(f"{split.capitalize()} · same {len(observed):,} complexes")
        fig.savefig(out / "comparison_plots" / f"{split}_predicted_vs_experimental.png", dpi=170)
        plt.close(fig)
        profiles = ["all", *sorted({r["mutation_id"] for r in observed})]
        for scope in ("original", "canonical_identity_disjoint_subset"):
            for profile in profiles:
                mask = np.array([
                    (profile == "all" or r["mutation_id"] == profile)
                    and (scope == "original" or r["complex_id"] not in overlap) for r in observed
                ])
                if not mask.any():
                    continue
                base, specialised = (scores[k][mask] - x[mask] for k in scores)
                base_mae, spec_mae = np.abs(base).mean(), np.abs(specialised).mean()
                results.append(dict(
                    split=split, scope=scope, mutation_id=profile, n=mask.sum(), split_expected=counts[split],
                    compound_count=len({r["compound_id"] for r, use in zip(observed, mask) if use}),
                    baseline_mae=base_mae, specialised_mae=spec_mae, delta_mae=spec_mae - base_mae,
                    baseline_rmse=np.sqrt(np.mean(base ** 2)), specialised_rmse=np.sqrt(np.mean(specialised ** 2)),
                ))
    if results:
        write_csv(out / "held_out_metrics.csv", tuple(results[0]), results)
    print(f"Wrote held-out metrics for {len(paired)} paired predictions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    evaluate(args.dataset, args.out)
