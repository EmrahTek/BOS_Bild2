import argparse
import sys
from pathlib import Path
from zipfile import BadZipFile

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap


def plot_quality(peak, margin, valid):
    """Plot correlation strength, peak separation, and window validity."""
    figure, axes = plt.subplots(1, 3, figsize=(13, 4.5), layout="constrained")
    figure.suptitle("BOS correlation quality and vector validity")

    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("lightgray")

    peak_plot = axes[0].imshow(
        np.ma.masked_invalid(peak), cmap=cmap, vmin=-1, vmax=1,
        origin="upper", interpolation="nearest",
    )
    axes[0].set_title("NCC maximum")
    figure.colorbar(
        peak_plot, ax=axes[0], location="bottom", label="NCC (dimensionless)"
    )

    margin_plot = axes[1].imshow(
        np.ma.masked_invalid(margin), cmap=cmap, vmin=0, vmax=2,
        origin="upper", interpolation="nearest",
    )
    axes[1].set_title("Peak margin")
    figure.colorbar(
        margin_plot, ax=axes[1], location="bottom",
        label="NCC peak difference (dimensionless)",
    )

    validity_plot = axes[2].imshow(
        valid, cmap=ListedColormap(["#b65c3a", "#2878a0"]),
        vmin=-0.5, vmax=1.5, origin="upper", interpolation="nearest",
    )
    axes[2].set_title(f"Validity ({valid.sum()}/{valid.size})")
    colorbar = figure.colorbar(
        validity_plot, ax=axes[2], location="bottom", ticks=[0, 1],
    )
    colorbar.set_ticklabels(["Rejected", "Valid"])

    for axis in axes:
        axis.set_xlabel("Grid column")
        axis.set_ylabel("Grid row")

    return figure


def main():
    parser = argparse.ArgumentParser(description="Plot BOS field quality maps.")
    parser.add_argument("field_path", type=Path)
    parser.add_argument("--output", type=Path, help="Optional path for a new PNG.")
    args = parser.parse_args()

    if args.output is not None and args.output.suffix.lower() != ".png":
        parser.error("--output must use the .png extension.")

    try:
        with np.load(args.field_path, allow_pickle=False) as field:
            peak = field["ncc_peak"]
            margin = field["peak_margin"]
            valid = field["valid"]

        if valid.ndim != 2 or valid.size == 0 or valid.dtype != np.dtype(bool):
            raise ValueError("Expected a non-empty two-dimensional Boolean mask.")
        if peak.shape != valid.shape or margin.shape != valid.shape:
            raise ValueError("The three quality arrays must have the same shape.")

        if args.output is not None:
            plt.switch_backend("Agg")

        figure = plot_quality(peak, margin, valid)
        if args.output is None:
            plt.show()
        else:
            with args.output.open("xb") as output_file:
                figure.savefig(output_file, format="png", dpi=300)
            print(f"Saved figure to {args.output}")

    except (OSError, ValueError, KeyError, TypeError, BadZipFile) as error:
        print(f"Visualization failed: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())