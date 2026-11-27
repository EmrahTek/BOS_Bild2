"""Show reference, measurement and BOS displacement arrows side by side."""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from analyze import to_gray01
from bos.correlation import estimate_pair
from bos.io import read_frame


def plot_pair(reference, measurement, field, *, arrow_scale=40, stride=3, limit_px=2):
    figure, axes = plt.subplots(
        1, 3, figsize=(13, 7), sharex=True, sharey=True, layout="constrained"
    )
    height, width = reference.shape
    for axis, image, title in zip(
        axes, (reference, measurement, reference),
        ("a  Reference", "b  Measurement", "c  BOS displacement vectors"),
    ):
        axis.imshow(image, cmap="gray", vmin=0, vmax=1, origin="upper")
        axis.set_title(title, fontsize=11)
        axis.set_xlabel("x [px]")
    axes[0].set_ylabel("y [px]")
    x, y, u, v = [field[key] for key in ("x_px", "y_px", "u_px", "v_px")]
    valid = field["valid"] & np.isfinite(u) & np.isfinite(v)
    magnitude = np.ma.array(np.hypot(u, v), mask=~valid)
    # Grid centres are pixel coordinates; extend by half the grid spacing.
    dx = float(x[0, 1] - x[0, 0]) if x.shape[1] > 1 else 20
    dy = float(y[1, 0] - y[0, 0]) if y.shape[0] > 1 else 20
    heat = axes[2].imshow(
        magnitude, cmap="Blues", vmin=0, vmax=limit_px, alpha=.65,
        interpolation="nearest", origin="upper",
        extent=(x.min()-dx/2, x.max()+dx/2, y.max()+dy/2, y.min()-dy/2),
    )
    sampled = np.s_[::stride, ::stride]
    good = valid[sampled]
    arrows = axes[2].quiver(
        x[sampled][good], y[sampled][good], u[sampled][good], v[sampled][good],
        color="#d97706", angles="xy", scale_units="xy", scale=1/arrow_scale,
        width=.004, minlength=0, pivot="tail",
    )
    axes[2].quiverkey(arrows, .12, .06, 1, "1 px", labelpos="N", coordinates="axes")
    for axis in axes:
        axis.set_xlim(-.5, width-.5)
        axis.set_ylim(height-.5, -.5)
    figure.colorbar(heat, ax=list(axes), location="bottom", shrink=.55, label="Displacement magnitude [px]")
    figure.suptitle(f"BOS: pattern displacement | arrow lengths x{arrow_scale:g} | not air velocity", fontsize=12)
    return figure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("measurement", type=Path)
    parser.add_argument("--rotate-cw", type=int, choices=(0,90,180,270), default=0)
    parser.add_argument("--window", type=int, choices=(32,40,52), default=40)
    parser.add_argument("--arrow-scale", type=float, default=40)
    parser.add_argument("--stride", type=int, default=3)
    parser.add_argument("--limit-px", type=float, default=2)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.stride < 1 or not all(np.isfinite(v) and v>0 for v in (args.arrow_scale,args.limit_px)):
        parser.error("Stride must be >=1; scales must be finite and positive.")
    if args.output and args.output.suffix.lower() != '.png':
        parser.error("Output must be a PNG.")
    try:
        images = []
        for folder in (args.reference,args.measurement):
            rgb,_ = read_frame(folder)
            images.append(to_gray01(np.ascontiguousarray(np.rot90(rgb,-args.rotate_cw//90))))
        field = estimate_pair(*images,window_px=args.window,step_px=args.window//2)
        if args.output:
            plt.switch_backend('Agg')
        figure = plot_pair(*images,field,arrow_scale=args.arrow_scale,stride=args.stride,limit_px=args.limit_px)
        if args.output:
            with args.output.open('xb') as file:
                figure.savefig(file,format='png',dpi=200)
            print(f"Saved figure to {args.output}")
        else:
            plt.show()
        plt.close(figure)
    except (OSError,ValueError) as error:
        parser.exit(1,f"Visualization failed: {error}\n")


if __name__ == '__main__':
    main()
