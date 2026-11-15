import argparse
import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from tempfile import mkdtemp

import numpy as np

from bos.correlation import estimate_pair
from bos.io import write_frame
from bos.metrics import score_known_shift
from bos.synthetic import make_pair

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHAPE = (112, 128)
WINDOWS = (32, 40, 52)
METHODS = ("oversampled", "fourier")
SHIFT_VALUES = (-2, -1, -0.5, -0.2, -0.1, 0.1, 0.2, 0.5, 1, 2)
DEMO_SHIFT = (1.0, -0.5)


def quick_check() -> None:
    cases = ((0, 0), (1, -2), (-2, 1), (0.2, -0.5), DEMO_SHIFT)
    for u_px, v_px in cases:
        reference, moving = make_pair(SHAPE, u_px, v_px)
        metrics = score_known_shift(estimate_pair(reference, moving), u_px, v_px)
        LOGGER.info(
            "u=%+.2f v=%+.2f px | valid=%.1f%% | RMSE=%.4f px",
            u_px, v_px, 100 * metrics["valid_fraction"], metrics["rmse_px"],
        )
        passed = metrics["valid_fraction"] >= 0.90 and metrics["rmse_px"] <= 0.10
        if not passed:
            raise ValueError(f"Quick check failed at u={u_px}, v={v_px} px.")

    flat = np.full(SHAPE, 0.5, dtype=np.float32)
    if estimate_pair(flat, flat)["valid"].any():
        raise ValueError("A textureless image must not produce valid vectors.")

    for u_px in (4.0, 6.0):
        reference, moving = make_pair(SHAPE, u_px, 0.0)
        if estimate_pair(reference, moving)["valid"].any():
            raise ValueError(f"Expected no valid vectors at u={u_px} px.")

    y, x = np.indices(SHAPE)
    periodic = 0.5 + 0.2 * np.cos(2 * np.pi * x / 3) + 0.2 * np.cos(2 * np.pi * y / 3)
    if estimate_pair(periodic, periodic)["valid"].any():
        raise ValueError("A periodic pattern must reject ambiguous matches.")


def run_sweep(output_path: Path, noise_std: float) -> None:
    shifts = [(0, 0)] + [(value, 0) for value in SHIFT_VALUES]
    shifts += [(0, value) for value in SHIFT_VALUES]
    rows = []

    for method in METHODS:
        LOGGER.info("Running sweep with %s generator.", method)
        for seed in range(10):
            for u_px, v_px in shifts:
                reference, moving = make_pair(
                    SHAPE, u_px, v_px, seed=seed, method=method, noise_std=noise_std
                )
                for window_px in WINDOWS:
                    field = estimate_pair(
                        reference, moving, window_px=window_px, step_px=window_px // 2
                    )
                    metrics = score_known_shift(field, u_px, v_px)
                    rows.append({
                        "method": method,
                        "seed": seed,
                        "noise_std": noise_std,
                        "window_px": window_px,
                        "u_true_px": u_px,
                        "v_true_px": v_px,
                        **metrics,
                    })

    with output_path.open("x", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    LOGGER.info("Saved %d sweep rows to %s", len(rows), output_path)


def save_demo_pair(run_dir: Path) -> None:
    reference, moving = make_pair(SHAPE, *DEMO_SHIFT)
    timestamp = datetime.now(timezone.utc).isoformat()

    for name, image in (("reference", reference), ("moving", moving)):
        frame_dir = run_dir / name
        frame_dir.mkdir()
        gray8 = np.rint(255 * image).astype(np.uint8)
        rgb8 = np.repeat(gray8[..., None], 3, axis=2)
        write_frame(frame_dir, rgb8, source="synthetic_bos", timestamp_utc=timestamp)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate BOS with known shifts.")
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--noise-std", type=float, default=0.0)
    args = parser.parse_args()
    if args.noise_std and not args.sweep:
        parser.error("--noise-std requires --sweep.")

    try:
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_dir / "validate.log", encoding="utf-8"),
            ],
        )

        quick_check()
        LOGGER.info("PASS: Quick validation checks.")

        output_root = PROJECT_ROOT / "data" / "checks"
        output_root.mkdir(parents=True, exist_ok=True)
        run_dir = Path(mkdtemp(prefix="bos_validation_", dir=output_root))
        save_demo_pair(run_dir)
        LOGGER.info("Demo pair: %s | u=%+.2f, v=%+.2f px", run_dir, *DEMO_SHIFT)

        if args.sweep:
            run_sweep(run_dir / "sweep.csv", args.noise_std)

        return 0

    except (OSError, ValueError) as error:
        LOGGER.error("Validation failed: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())