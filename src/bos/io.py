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

def read_frame(run_dir: Path) -> tuple[np.ndarray, dict]:
    image_path = run_dir / FRAME_FILENAME

    with Image.open(image_path, formats=["TIFF"]) as stored_image:
        if(
            stored_image.mode != "RGB"
            or stored_image.n_frames != 1
            or stored_image.tag_v2.get(BITSPERSAMPLE) != ( 8,8,8)

        ):
            raise ValueError(f"Expected a single-frame RGB8 TIFF: {image_path}")

        image = np.array(stored_image)

    metadata_path = run_dir / METADATA_FILENAME
    with metadata_path.open(encoding="utf-8") as metada_file:
        metadata = json.load(metada_file)

    if not isinstance(metadata, dict): 
        raise ValueError(f"Expected a JSON object in {metadata_path}.")

    for key, expected_value in describe_rgb8(image).items():
        if metadata.get(key) != expected_value:
            raise ValueError(f"Metadata field {key ! r} does not match { image_path}.")
    return image,metadata
        