import json
from pathlib import Path

import numpy as np
from PIL import Image
from PIL.TiffImagePlugin import BITSPERSAMPLE

FRAME_FILENAME = "frame.tif"
METADATA_FILENAME = "frame.json"


def describe_rgb8(image: np.ndarray) -> dict:
    if image.ndim != 3:
        raise ValueError("Image must have three dimensions.")

    if image.shape[2] != 3:
        raise ValueError("Image must have three color channels.")

    if image.dtype != np.uint8:
        raise ValueError("Image must use uint8 values.")
    
    return {
        "file_name": FRAME_FILENAME,
        "shape": list(image.shape),
        "dtype": str(image.dtype),
        "pixel_format": "RGB8",
        "channel_order": " RGB",
    }

## Alle Parameter nach * müssen als Keyword Arguments angegeben werden.
def write_frame(run_dir: Path, image: np.ndarray, *, source:str, timestamp_utc:str ) -> dict:
    metadata = describe_rgb8(image)
    metadata["source"] = source
    metadata["timestamp_utc"] = timestamp_utc

    with(run_dir / FRAME_FILENAME).open("xb") as image_file:
        Image.fromarray(image).save(image_file, format="TIFF", compression="raw")

    with(run_dir / METADATA_FILENAME).open("x", encoding="utf-8") as metadata_file:
        json.dump(metadata, metadata_file, indent=2)
        metadata_file.write("\n")
    return metadata

