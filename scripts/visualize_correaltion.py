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


def plot_subpixel(template, search, radius, label):
    """Show the NCC samples and the accepted parabolic peak along each axis."""
    scores = _ncc_scores(template, search)
    u, v, peak, _ = _estimate_window(template, search, radius)

    figure, axes = plt.subplots(
        1, 2, figsize=(10, 4.6), sharey=True, layout="constrained"
    )
    title = f"Parabolic subpixel interpolation\n{label}"

    if not np.isfinite(peak):
        figure.suptitle(title)
        for axis in axes:
            axis.set_axis_off()
        figure.text(0.5, 0.5, "No usable NCC maximum", ha="center")
        return figure

    peak_y, peak_x = np.unravel_index(scores.argmax(), scores.shape)
    last_row, last_column = np.array(scores.shape) - 1
    accepted = np.isfinite([u, v]).all()

    if accepted:
        status = "Window accepted"
    elif peak_y in (0, last_row) or peak_x in (0, last_column):
        status = "Window rejected | peak at search boundary"
    else:
        status = "Window rejected | quality or interpolation check"
    figure.suptitle(f"{title}\n{status}")

    profiles = (
        (axes[0], scores[peak_y, :], peak_x, u, "Horizontal", "u"),
        (axes[1], scores[:, peak_x], peak_y, v, "Vertical", "v"),
    )

    for axis, profile, index, estimate, direction, symbol in profiles:
        indices = np.arange(max(0, index - 1), min(profile.size, index + 2))
        positions = indices - radius
        samples = profile[indices]
        finite = np.isfinite(samples)
        integer_peak = index - radius

        axis.axvline(
            integer_peak, color="gray", linestyle="--", label="Integer peak"
        )
        axis.plot(positions[finite], samples[finite], "o", label="NCC samples")
        axis.set_xticks(positions)
        axis.set_xlabel(f"Candidate displacement {symbol} [px]")
        axis.set_title(direction)

        if accepted:
            left, center, right = samples
            a = (left - 2 * center + right) / 2
            b = (right - left) / 2
            offsets = np.linspace(-1, 1, 201)
            fitted = a * offsets**2 + b * offsets + center

            offset = estimate - integer_peak
            peak_height = a * offset**2 + b * offset + center
            axis.plot(integer_peak + offsets, fitted, label="Parabola")
            axis.plot(
                estimate, peak_height, "r*", markersize=11,
                label=f"Subpixel peak {symbol} = {estimate:+.3f} px",
            )

        axis.legend(fontsize="small")

    axes[0].set_ylabel("NCC (dimensionless)")
    return figure


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
        raise ValueError(
            f"Grid cell outside the grid of {tops.size} rows and {lefts.size} columns."
        )

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
    figure.suptitle(f"Correlation window and search region\n{label}")

    panels = (
        (reference, template, left, top, "Reference image", "Correlation window", "tab:orange"),
        (measurement, search, left - radius, top - radius, "Measurement image", "Search region", "tab:blue"),
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
            Rectangle(
                (x - 0.5, y - 0.5), width, height,
                fill=False, edgecolor=color, linewidth=2,
            )
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
        image_plot, ax=axes, shrink=0.8, label="Normalized intensity (dimensionless)"
    )
    return figure


def plot_ncc(template, search, radius, label):
    """Plot the NCC map and mark the integer peak selected by the estimator."""
    scores = _ncc_scores(template, search)
    u, v, peak, margin = _estimate_window(template, search, radius)

    figure, axis = plt.subplots(figsize=(7, 7), layout="constrained")
    figure.suptitle(f"NCC map of the correlation window\n{label}")

    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("lightgray")
    edge = radius + 0.5
    score_plot = axis.imshow(
        np.ma.masked_invalid(scores), cmap=cmap, vmin=-1, vmax=1,
        origin="upper", interpolation="nearest", extent=(-edge, edge, edge, -edge),
    )
    figure.colorbar(score_plot, ax=axis, label="NCC (dimensionless)")

    if np.isfinite(peak):
        peak_y, peak_x = np.unravel_index(scores.argmax(), scores.shape)
        axis.plot(
            peak_x - radius, peak_y - radius, "rx", markersize=12, markeredgewidth=2
        )
        peak_text = f"× Maximum {peak:.3f}"
    else:
        peak_text = "No usable NCC value"

    margin_text = f"{margin:.3f}" if np.isfinite(margin) else "–"
    status = "accepted" if np.isfinite([u, v]).all() else "rejected"
    axis.set_title(f"{peak_text}   |   Peak margin {margin_text}\nWindow {status}")

    shifts = np.arange(-radius, radius + 1)
    axis.set_xticks(shifts)
    axis.set_yticks(shifts)
    axis.set_xlabel("Horizontal candidate displacement u [px]")
    axis.set_ylabel("Vertical candidate displacement v [px]")
    return figure


def main():
    parser = argparse.ArgumentParser(description="Plot one BOS window and its NCC map.")
    parser.add_argument("reference_dir", type=Path)
    parser.add_argument("measurement_dir", type=Path)
    parser.add_argument("--window", type=int, choices=(32, 40, 52), default=40)
    parser.add_argument("--cell", nargs=2, type=int, metavar=("ROW", "COL"))
    parser.add_argument(
        "--subpixel", action="store_true", help="Show or export only the subpixel figure."
    )
    parser.add_argument("--output-dir", type=Path, help="Existing directory for the PNG files.")
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
        label = f"Grid cell ({row}, {column})"
        if "synthetic_bos" in (reference_meta.get("source"), measurement_meta.get("source")):
            label += " | synthetic data"

        if args.output_dir is not None:
            plt.switch_backend("Agg")

        if args.subpixel:
            figure = plot_subpixel(template, search, radius, label)
            figures = ((figure, "04_subpixel_interpolation.png"),)
        else:
            window_figure = plot_window(
                reference, measurement, template, search, top, left, radius, label
            )
            ncc_figure = plot_ncc(template, search, radius, label)
            figures = (
                (window_figure, "02_correlation_window.png"),
                (ncc_figure, "03_ncc_map.png"),
            )

        if args.output_dir is None:
            plt.show()
        else:
            paths = [args.output_dir / filename for _, filename in figures]
            for path in paths:
                if path.exists():
                    raise FileExistsError(f"Output file already exists: {path}")
            for (figure, _), path in zip(figures, paths):
                with path.open("xb") as output_file:
                    figure.savefig(output_file, format="png", dpi=300)
                print(f"Saved figure to {path}")

    except (OSError, ValueError) as error:
        print(f"Visualization failed: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())