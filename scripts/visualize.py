import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from analyze import to_gray01
from bos.io import read_frame


def plot_difference(
    reference: np.ndarray,
    measurement: np.ndarray,
    *,
    synthetic: bool = False,
) -> Figure:
    """Plot two normalized grayscale images and their signed difference."""
    if (
        reference.ndim != 2
        or reference.shape != measurement.shape
        or reference.size == 0
    ):
        raise ValueError("Expected two non-empty grayscale images of the same shape.")

    for image in (reference, measurement):
        if not np.isfinite(image).all() or image.min() < 0 or image.max() > 1:
            raise ValueError("Expected finite grayscale values in [0, 1].")

    difference = np.subtract(measurement, reference, dtype=np.float32)
    limit = float(np.abs(difference).max())
    if limit == 0.0:
        limit = 1.0

    figure, axes = plt.subplots(
        1, 3, figsize=(13, 4.5), sharex=True, sharey=True, layout="constrained"
    )
    title = "BOS-Bildpaar und Grauwertdifferenz"
    if synthetic:
        title += " (synthetische Daten)"
    figure.suptitle(title)

    reference_plot = axes[0].imshow(
        reference, cmap="gray", vmin=0, vmax=1, origin="upper",
        interpolation="nearest",
    )
    axes[1].imshow(
        measurement, cmap="gray", vmin=0, vmax=1, origin="upper",
        interpolation="nearest",
    )
    difference_plot = axes[2].imshow(
        difference, cmap="RdBu_r", vmin=-limit, vmax=limit, origin="upper",
        interpolation="nearest",
    )

    for axis, label in zip(axes, ("Referenzbild", "Messbild", "Differenzbild")):
        axis.set_title(label)
        axis.set_xlabel("x [px]")
    axes[0].set_ylabel("y [px]")

    figure.colorbar(
        reference_plot, ax=axes[:2], location="bottom",
        label="Normierter Grauwert (dimensionslos)",
    )
    figure.colorbar(
        difference_plot, ax=axes[2], location="bottom",
        label="ΔI = Messbild − Referenzbild (dimensionslos)",
    )
    return figure


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show or export the signed difference between two BOS frames."
    )
    parser.add_argument("reference_dir", type=Path)
    parser.add_argument("measurement_dir", type=Path)
    parser.add_argument("--output", type=Path, help="Optional path for a new PNG.")
    args = parser.parse_args()

    if args.output is not None and args.output.suffix.lower() != ".png":
        parser.error("--output must use the .png extension.")

    try:
        reference_rgb, reference_meta = read_frame(args.reference_dir)
        measurement_rgb, measurement_meta = read_frame(args.measurement_dir)
        synthetic = (
            reference_meta.get("source") == "synthetic_bos"
            or measurement_meta.get("source") == "synthetic_bos"
        )

        if args.output is not None:
            plt.switch_backend("Agg")

        figure = plot_difference(
            to_gray01(reference_rgb), to_gray01(measurement_rgb), synthetic=synthetic
        )
        try:
            if args.output is None:
                plt.show()
            else:
                with args.output.open("xb") as output_file:
                    figure.savefig(output_file, format="png", dpi=300)
                print(f"Saved figure to {args.output}")
        finally:
            plt.close(figure)
    except (OSError, ValueError) as error:
        print(f"Visualization failed: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())