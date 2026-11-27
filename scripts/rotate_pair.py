"""Create lossless clockwise-rotated copies of a BOS image pair."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from bos.io import describe_rgb8, read_frame


def rotate_pair(source: Path, output: Path):
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError("Output must be a new folder, different from the source.")
    frames = []
    for name in ("reference", "moving"):
        folder = source / name
        if (folder / "frame.json").exists():
            image, metadata = read_frame(folder)
        else:
            # Imported TIFF pairs can lack acquisition metadata. Do not invent it.
            with Image.open(folder / "frame.tif") as stored:
                if stored.mode != "RGB" or stored.n_frames != 1:
                    raise ValueError("Expected a single-frame RGB8 TIFF.")
                image = np.array(stored)
            describe_rgb8(image)
            metadata = {"source": "imported_tiff", "timestamp_utc": None}
        rotated = np.ascontiguousarray(np.rot90(image, k=-1))
        metadata.update(describe_rgb8(rotated))
        metadata["rotation_clockwise_deg"] = 90
        metadata["original_frame"] = str((folder / "frame.tif").resolve())
        frames.append((name, rotated, metadata))
    if frames[0][1].shape != frames[1][1].shape:
        raise ValueError("Reference and moving image dimensions must match.")
    output.mkdir(parents=True, exist_ok=False)
    for name, image, metadata in frames:
        folder = output / name
        folder.mkdir()
        with (folder / "frame.tif").open("xb") as file:
            Image.fromarray(image).save(file, format="TIFF", compression="raw")
        (folder / "frame.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (output / "rotation.json").write_text(json.dumps({
        "source_pair": str(source.resolve()), "rotation_clockwise_deg": 90,
        "coordinates": "Rotated image: u positive right, v positive down",
    }, indent=2) + "\n")
    print(f"Saved clockwise-rotated pair to {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        rotate_pair(args.source, args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Rotation failed: {error}\n")


if __name__ == "__main__":
    main()
