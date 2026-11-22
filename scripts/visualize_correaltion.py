import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

from analyze import to_gray01
from bos.correlation import _estimate_window, _ncc_scores
from bos.io import read_frame

SEARCH_RADIUS_PX = 4


def select_window(reference, measurement, window, radius, cell):
    """Select the same template and search region as the BOS analysis."""
    if reference.ndim != 2 or reference.shape != measurement.shape:
        raise ValueError("Expected two grayscale images of the same shape.")

    height, width = reference.shape
    step = window // 2
    tops = np.arange(radius, height - window - radius + 1, step)
    lefts = np.arange(radius, width - window - radius + 1, step)

    if tops.size == 0 or lefts.size == 0:
        raise ValueError(f"Both image dimensions must be at least {window + 2 * radius} px.")

    if cell is None:
        row, column = tops.size // 2, lefts.size // 2
    else:
        row, column = cell
    if not (0 <= row < tops.size and 0 <= column < lefts.size):
        raise ValueError(f"Grid cell outside the grid of {tops.size} rows and {lefts.size} columns.")

    top, left = tops[row], lefts[column]
    bottom, right = top + window, left + window
    template = reference[top:bottom, left:right].astype(np.float64)
    search = measurement[
        top - radius:bottom + radius, left - radius:right + radius
    ].astype(np.float64)

    return row, column, top, left, template, search


def plot_window(reference, measurement, template, search, top, left, radius, label):
    """Show the selected regions in the full images and as close-ups."""
    figure, axes = plt.subplots(2, 2, figsize=(10, 9), layout="constrained")
    figure.suptitle(f"Korrelationsfenster und Suchregion\n{label}")

    panels = (
        (reference, template, left, top, "Referenzbild", "Korrelationsfenster", "tab:orange"),
        (measurement, search, left - radius, top - radius, "Messbild", "Suchregion", "tab:blue"),
    )
    for column, panel in enumerate(panels):
        image, region, x, y, image_title, region_title, color = panel
        overview, detail = axes[:, column]
        height, width = region.shape

        image_plot = overview.imshow(
            image, cmap="gray", vmin=0, vmax=1, origin="upper",
            interpolation="nearest",
        )
        overview.add_patch(
            Rectangle((x - 0.5, y - 0.5), width, height,
                      fill=False, edgecolor=color, linewidth=2)
        )
        overview.set_title(image_title)

        detail.imshow(
            region, cmap="gray", vmin=0, vmax=1, origin="upper",
            interpolation="nearest",
            extent=(x - 0.5, x + width - 0.5, y + height - 0.5, y - 0.5),
        )
        detail.set_title(f"{region_title} ({width} × {height} px)", color=color)

    for axis in axes.flat:
        axis.set_xlabel("x [px]")
        axis.set_ylabel("y [px]")

    figure.colorbar(
        image_plot, ax=axes, shrink=0.8, label="Normierter Grauwert (dimensionslos)"
    )
    return figure


def plot_ncc(template, search, radius, label):
    """Plot the NCC map and mark the integer peak selected by the estimator."""
    scores = _ncc_scores(template, search)
    u, v, peak, margin = _estimate_window(template, search, radius)

    figure, axis = plt.subplots(figsize=(7, 7), layout="constrained")
    figure.suptitle(f"NCC-Karte des Korrelationsfensters\n{label}")

    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("lightgray")
    edge = radius + 0.5
    score_plot = axis.imshow(
        np.ma.masked_invalid(scores), cmap=cmap, vmin=-1, vmax=1,
        origin="upper", interpolation="nearest", extent=(-edge, edge, edge, -edge),
    )
    figure.colorbar(score_plot, ax=axis, label="NCC (dimensionslos)")

    if np.isfinite(peak):
        peak_y, peak_x = np.unravel_index(scores.argmax(), scores.shape)
        axis.plot(peak_x - radius, peak_y - radius, "rx", markersize=12, markeredgewidth=2)
        peak_text = f"× Maximum {peak:.3f}"
    else:
        peak_text = "Kein auswertbarer NCC-Wert"

    margin_text = f"{margin:.3f}" if np.isfinite(margin) else "–"
    status = "gültig" if np.isfinite([u, v]).all() else "verworfen"
    axis.set_title(f"{peak_text}   |   Peak-Margin {margin_text}\nFenster {status}")

    shifts = np.arange(-radius, radius + 1)
    axis.set_xticks(shifts)
    axis.set_yticks(shifts)
    axis.set_xlabel("Horizontaler Kandidatenversatz u [px]")
    axis.set_ylabel("Vertikaler Kandidatenversatz v [px]")
    return figure


def main():
    parser = argparse.ArgumentParser(description="Plot one BOS window and its NCC map.")
    parser.add_argument("reference_dir", type=Path)
    parser.add_argument("measurement_dir", type=Path)
    parser.add_argument("--window", type=int, choices=(32, 40, 52), default=40)
    parser.add_argument("--cell", nargs=2, type=int, metavar=("ROW", "COL"))
    parser.add_argument("--output-dir", type=Path, help="Existing directory for both PNGs.")
    args = parser.parse_args()

    try:
        reference_rgb, reference_meta = read_frame(args.reference_dir)
        measurement_rgb, measurement_meta = read_frame(args.measurement_dir)
        reference = to_gray01(reference_rgb)
        measurement = to_gray01(measurement_rgb)

        radius = SEARCH_RADIUS_PX
        row, column, top, left, template, search = select_window(
            reference, measurement, args.window, radius, args.cell
        )
        label = f"Rasterzelle ({row}, {column})"
        if "synthetic_bos" in (reference_meta.get("source"), measurement_meta.get("source")):
            label += " · synthetische Daten"

        if args.output_dir is not None:
            plt.switch_backend("Agg")

        window_figure = plot_window(
            reference, measurement, template, search, top, left, radius, label
        )
        ncc_figure = plot_ncc(template, search, radius, label)

        if args.output_dir is None:
            plt.show()
        else:
            paths = (
                args.output_dir / "02_korrelationsfenster.png",
                args.output_dir / "03_ncc_karte.png",
            )
            for path in paths:
                if path.exists():
                    raise FileExistsError(f"Output file already exists: {path}")
            for figure, path in zip((window_figure, ncc_figure), paths):
                with path.open("xb") as output_file:
                    figure.savefig(output_file, format="png", dpi=300)
                print(f"Saved figure to {path}")

    except (OSError, ValueError) as error:
        print(f"Visualization failed: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())