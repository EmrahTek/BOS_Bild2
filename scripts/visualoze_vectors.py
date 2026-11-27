import argparse
import sys
from pathlib import Path
from zipfile import BadZipFile

import matplotlib.pyplot as plt
import numpy as np

from analyze import to_gray01
from bos.io import read_frame


def load_field(path):
    """Load and check the arrays needed for a quiver plot."""
    names = ("x_px", "y_px", "u_px", "v_px", "valid")
    with np.load(path, allow_pickle=False) as archive:
        missing = [name for name in names if name not in archive]
        if missing:
            raise ValueError(f"Missing arrays in {path}: {', '.join(missing)}")
        field = {name: archive[name] for name in names}

    shape = field["x_px"].shape
    if len(shape) != 2 or not all(array.shape == shape for array in field.values()):
        raise ValueError("Expected five two-dimensional arrays with the same shape.")
    if field["valid"].dtype != np.dtype(bool):
        raise ValueError("The valid array must contain Boolean values.")
    return field


def plot_vectors(reference, field, arrow_scale, stride, synthetic):
    """Draw valid BOS vectors in image coordinates over the reference."""
    x, y = field["x_px"], field["y_px"]
    u, v = field["u_px"], field["v_px"]
    height, width = reference.shape

    inside = (0 <= x) & (x < width) & (0 <= y) & (y < height)
    if not inside.all():
        raise ValueError("The field grid falls outside the reference image.")

    valid = field["valid"] & np.isfinite(u) & np.isfinite(v)
    if not valid.any():
        raise ValueError("No valid displacement vectors in this field.")

    sampled = np.s_[::stride, ::stride]
    shown = valid[sampled]
    if not shown.any():
        raise ValueError("No valid vectors at this stride. Try --stride 1.")

    figure, axis = plt.subplots(figsize=(10, 8), layout="constrained")
    axis.imshow(reference, cmap="gray", vmin=0, vmax=1, origin="upper")
    arrows = axis.quiver(
        x[sampled][shown], y[sampled][shown],
        u[sampled][shown], v[sampled][shown],
        angles="xy", scale_units="xy", scale=1 / arrow_scale,
        color="crimson", width=0.0025, pivot="tail", minlength=0,
    )
    axis.quiverkey(
        arrows, X=0.97, Y=0.97, U=1,
        label="1 px displacement", labelpos="W", coordinates="axes",
    )

    axis.set_xlim(-0.5, width - 0.5)
    axis.set_ylim(height - 0.5, -0.5)
    axis.set_xlabel("x [px]")
    axis.set_ylabel("y [px]")

    title = "BOS displacement field over the reference image"
    if synthetic:
        title += " (synthetic data)"
    axis.set_title(
        f"{title}\n"
        f"{valid.sum()}/{valid.size} valid | "
        f"{shown.sum()} displayed | arrow lengths x{arrow_scale:g}"
    )
    return figure


def main():
    parser = argparse.ArgumentParser(description="Plot a stored BOS displacement field.")
    parser.add_argument("reference_dir", type=Path)
    parser.add_argument("field_path", type=Path)
    parser.add_argument("--arrow-scale", type=float, default=20)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--output", type=Path, help="Optional path for a new PNG.")
    args = parser.parse_args()

    if args.field_path.suffix.lower() != ".npz":
        parser.error("field_path must point to an .npz file.")
    if not np.isfinite(args.arrow_scale) or args.arrow_scale <= 0:
        parser.error("--arrow-scale must be finite and positive.")
    if args.stride < 1:
        parser.error("--stride must be at least 1.")
    if args.output is not None and args.output.suffix.lower() != ".png":
        parser.error("--output must use the .png extension.")

    try:
        rgb, metadata = read_frame(args.reference_dir)
        field = load_field(args.field_path)
        if args.output is not None:
            plt.switch_backend("Agg")

        figure = plot_vectors(
            to_gray01(rgb), field, args.arrow_scale, args.stride,
            synthetic=metadata.get("source") == "synthetic_bos",
        )
        if args.output is None:
            plt.show()
        else:
            with args.output.open("xb") as output_file:
                figure.savefig(output_file, format="png", dpi=300)
            print(f"Saved figure to {args.output}")

    except (OSError, ValueError, TypeError, BadZipFile) as error:
        print(f"Visualization failed: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())