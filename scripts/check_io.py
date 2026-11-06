import logging
from datetime import datetime, timezone
from pathlib import Path
from tempfile import mkdtemp

import numpy as np
import yaml

from bos.io import read_frame, write_frame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)

def load_expected_shape(config_path: Path) -> tuple[int,int, int]:
    with config_path.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)
    if not isinstance(config,dict) or config.keys() != {"camera"}:
        raise ValueError("Expected exactly one top-level YAML key: camera.")

    camera = config["camera"]
    if not isinstance(camera, dict) or camera.keys() != {"expected_shape","pixel_format",}:
        raise ValueError("Expected camera keys: expected_sahpe and pixel_format.")

    if camera["pixel_format"] != "RGB8":
        raise ValueError("camera.pixel_format must be RGB8.")

    shape = camera["expected_shape"]
    if(not isinstance(shape,list) or len(shape) != 3 or any(type(value) is not int or value < 1 for value in shape) or shape[2] != 3 ): 
        raise ValueError("camera.expected_shape must be [height, width, 3].")

    height, width, channels = shape
    return height, width, channels

def create_test_image(shape: tuple[int,int,int]) -> np.ndarray:
    image = np.empty(shape,dtype=np.uint8)
    middle_column = shape[1] // 2

    image[:, :middle_column] = (255,64,0)
    image[:, middle_column:] = (0,128,255)
    image[0,0] = (0,255,0)

    return image

def main() -> int:
    try:
        log_path = PROJECT_ROOT / "logs" / "io_check.log"
        log_path.parent.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO, 
            format="%(asctime)s %(levelname)s %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_path,encoding="utf-8"),
            ],
        )

        config_path = PROJECT_ROOT / "configs" / "base.yaml"
        expected_shape = load_expected_shape(config_path)
        LOGGER.info("Loaded %s, expected RGB8 shape %s", config_path, expected_shape)

        output_root = PROJECT_ROOT / "data" / "checks"
        output_root.mkdir(parents=True, exist_ok=True)
        run_dir = Path(mkdtemp(prefix="io_check_", dir=output_root))
        LOGGER.info("Output folder: %s", run_dir)

        image = create_test_image(expected_shape)
        written_metadata = write_frame(
            run_dir,
            image,
            source="generated_test_image",
            timestamp_utc=datetime.now(timezone.utc).isoformat(),)
        restored_image, restored_metadata = read_frame(run_dir)

        if not np.array_equal(image, restored_image):
            raise ValueError("The restored pixels differ from the original pixels.")

        if written_metadata != restored_metadata:
            raise ValueError("The restored metadata differs from the original metadata.")

        LOGGER.info("PASS: All pixels and metadata match.")
        return 0

    except (OSError, ValueError, yaml.YAMLError) as error:
        LOGGER.error("I/O check failed: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())