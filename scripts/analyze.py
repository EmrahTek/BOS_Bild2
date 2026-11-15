import argparse
import logging
from pathlib import Path
from tempfile import mkdtemp

import numpy as np

from bos.correlation import estimate_pair
from bos.io import read_frame

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def to_gray01(rgb8: np.ndarray) -> np.ndarray:
    rgb_weights = np.array([0.299, 0.587, 0.114], dtype=np.float32)
    gray = (rgb8.astype(np.float32) / np.float32(255.0)) @ rgb_weights
    return np.clip(gray, 0.0, 1.0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze two stored BOS frames.")
    parser.add_argument("reference_dir", type=Path)
    parser.add_argument("moving_dir", type=Path)
    parser.add_argument("--window", type=int, choices=(32, 40, 52), default=40)
    args = parser.parse_args()

    try:
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_dir / "analyze.log", encoding="utf-8"),
            ],
        )

        LOGGER.info(
            "Reference: %s | Moving: %s | W=%d px",
            args.reference_dir, args.moving_dir, args.window,
        )

        reference_rgb, _ = read_frame(args.reference_dir)
        moving_rgb, _ = read_frame(args.moving_dir)
        field = estimate_pair(
            to_gray01(reference_rgb),
            to_gray01(moving_rgb),
            window_px=args.window,
            step_px=args.window // 2,
        )

        output_root = PROJECT_ROOT / "data" / "processed"
        output_root.mkdir(parents=True, exist_ok=True)
        output_dir = Path(mkdtemp(prefix="bos_pair_", dir=output_root))
        field["magnitude_px"] = np.hypot(field["u_px"], field["v_px"])
        output_path = output_dir / "field.npz"
        np.savez_compressed(output_path, **field)
        LOGGER.info("Saved field to %s", output_path)

        valid = field["valid"]
        LOGGER.info("Valid vectors: %d/%d", int(valid.sum()), valid.size)
        if not valid.any():
            LOGGER.error("No valid displacement vectors.")
            return 1

        LOGGER.info(
            "Median displacement: u=%+.3f px, v=%+.3f px",
            np.median(field["u_px"][valid]), np.median(field["v_px"][valid]),
        )
        return 0

    except (OSError, ValueError) as error:
        LOGGER.error("Analysis failed: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())