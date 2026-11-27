import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from bos.io import read_frame, write_frame
from bos.correlation import estimate_pair
from analyze import to_gray01
from capture import (
    CHANNELS, BITS_PER_PIXEL,
    configure_camera, get_image_size, require_success,
)


def record(args):
    from pyueye import ueye

    # Never overwrite an existing recording.
    args.output.mkdir(parents=True, exist_ok=False)

    metadata = {
        "complete": False,
        "requested_fps": args.fps,
        "requested_seconds": args.seconds,
        "exposure_requested_ms": args.exposure_ms,
        "gain": args.gain,
        "timestamp_source": "host_after_capture",
        "frames": [],
    }

    camera = ueye.HIDS(0)
    opened = False

    try:
        require_success(
            ueye, ueye.is_InitCamera(camera, None), "Open camera"
        )
        opened = True

        metadata["exposure_set_ms"] = configure_camera(
            ueye, camera, args.exposure_ms, args.gain
        )

        width, height = get_image_size(ueye, camera)
        metadata["image_size"] = [width, height]

        memory = ueye.c_mem_p()
        memory_id = ueye.int()
        pitch = ueye.int()

        require_success(
            ueye,
            ueye.is_AllocImageMem(
                camera, width, height, BITS_PER_PIXEL,
                memory, memory_id,
            ),
            "Allocate memory",
        )

        require_success(
            ueye,
            ueye.is_SetImageMem(camera, memory, memory_id),
            "Set image memory",
        )

        require_success(
            ueye,
            ueye.is_InquireImageMem(
                camera, memory, memory_id,
                None, None, None, pitch,
            ),
            "Read image stride",
        )

        if not memory.value or pitch.value < width * CHANNELS:
            raise RuntimeError("Invalid camera buffer.")

        def capture(name):
            require_success(
                ueye,
                ueye.is_FreezeVideo(camera, ueye.IS_WAIT),
                "Capture frame",
            )

            captured_at = time.monotonic()
            timestamp = datetime.now(timezone.utc).isoformat()

            data = ueye.get_data(
                memory, width, height, BITS_PER_PIXEL,
                pitch.value, copy=True,
            )

            rows = data.reshape(height, pitch.value)
            image = rows[:, :width * CHANNELS]
            image = np.ascontiguousarray(
                image.reshape(height, width, CHANNELS)
            )

            folder = args.output / name
            folder.mkdir(parents=True)

            write_frame(
                folder,
                image,
                source="ids_ueye",
                timestamp_utc=timestamp,
            )

            return captured_at

        input("With the heat source OFF, press Enter for the reference frame...")
        capture("reference")

        input(
            "Turn on the heat source. When the warm-air flow is ready, "
            "press Enter to start recording..."
        )

        start = time.monotonic()

        while time.monotonic() - start < args.seconds:
            index = len(metadata["frames"])
            name = f"frames/{index:06d}"

            captured_at = capture(name)
            elapsed = captured_at - start

            metadata["frames"].append({
                "path": name,
                "time_s": elapsed,
            })

            print(f"Frame {index}: {elapsed:.3f} s", flush=True)

            # Skip missed time slots when capture or storage falls behind.
            # Do not compensate with a burst of closely spaced frames.
            now = time.monotonic() - start
            next_slot = (int(now * args.fps) + 1) / args.fps
            wait = min(next_slot, args.seconds) - now
            time.sleep(max(0, wait))

        metadata["elapsed_seconds"] = time.monotonic() - start
        metadata["complete"] = True

    finally:
        # Preserve frames already saved if recording is interrupted.
        with (args.output / "sequence.json").open(
            "x", encoding="utf-8"
        ) as file:
            json.dump(metadata, file, indent=2)

        if opened:
            require_success(
                ueye, ueye.is_ExitCamera(camera), "Close camera"
            )

    frames = metadata["frames"]

    print(f"Saved {len(frames)} lossless frames.")

    if len(frames) > 1:
        measured_fps = (
            (len(frames) - 1)
            / (frames[-1]["time_s"] - frames[0]["time_s"])
        )
        print(f"Measured average frame rate: {measured_fps:.2f} fps")

        if measured_fps < args.fps * 0.9:
            print(
                "WARNING: The target frame rate was not reached. "
                "Video playback will use the recorded timestamps."
            )


def process(args):
    import matplotlib
    matplotlib.use("Agg")

    import matplotlib.pyplot as plt
    from matplotlib.animation import FFMpegWriter

    if not FFMpegWriter.isAvailable():
        raise RuntimeError("ffmpeg is required to create an MP4 video.")

    metadata = json.loads(
        (args.sequence / "sequence.json").read_text()
    )

    if not metadata.get("complete"):
        raise ValueError("The recording is incomplete.")

    frames = metadata["frames"]
    times = np.array([f["time_s"] for f in frames], dtype=float)

    if (
        len(times) == 0
        or not np.isfinite(times).all()
        or times[0] < 0
        or np.any(np.diff(times) <= 0)
    ):
        raise ValueError("Invalid frame timestamps.")

    duration = float(metadata["elapsed_seconds"])

    if not np.isfinite(duration) or duration < times[-1]:
        raise ValueError("Invalid recording duration.")

    reference, _ = read_frame(args.sequence / "reference")
    reference = np.ascontiguousarray(np.rot90(reference, k=-(args.rotate_cw // 90)))
    reference_gray = to_gray01(reference)

    args.output.mkdir(parents=True, exist_ok=False)
    fields_dir = args.output / "fields"
    fields_dir.mkdir()

    # Compare every heated frame with the same cold reference.
    for index, frame in enumerate(frames):
        image, _ = read_frame(args.sequence / frame["path"])
        image = np.ascontiguousarray(np.rot90(image, k=-(args.rotate_cw // 90)))

        field = estimate_pair(
            reference_gray,
            to_gray01(image),
            window_px=args.window,
            step_px=args.window // 2,
        )

        field["magnitude_px"] = np.hypot(
            field["u_px"], field["v_px"]
        )

        np.savez_compressed(
            fields_dir / f"{index:06d}.npz",
            **field,
            time_s=times[index],
        )

        print(
            f"Processing: {index + 1}/{len(frames)} | "
            f"Valid: {field['valid'].mean():.1%}",
            flush=True,
        )

    settings = {
        "window_px": args.window,
        "step_px": args.window // 2,
        "component": args.component,
        "limit_px": args.limit_px,
        "output_fps": args.fps,
        "rotation_clockwise_deg": args.rotate_cw,
        "reference": str(
            (args.sequence / "reference").resolve()
        ),
        "playback": "Hold previous sample using recorded timestamps",
    }

    (args.output / "processing.json").write_text(
        json.dumps(settings, indent=2)
    )

    figure, axes = plt.subplots(
        1, 2, figsize=(10, 7), layout="constrained"
    )

    raw_plot = axes[0].imshow(reference)
    axes[0].set_title("Raw image")

    with np.load(fields_dir / "000000.npz") as field:
        values = np.ma.array(
            field[f"{args.component}_px"],
            mask=~field["valid"],
        )

        bos_plot = axes[1].imshow(
            values,
            cmap="gray",
            vmin=-args.limit_px,
            vmax=args.limit_px,
            interpolation="nearest",
            extent=(0, reference.shape[1], reference.shape[0], 0),
        )

    axes[1].set_title(f"BOS: {args.component} displacement")

    for axis in axes:
        axis.set_axis_off()

    figure.colorbar(
        bos_plot,
        ax=axes[1],
        label="Displacement [px]; invalid cells masked",
    )

    title = figure.suptitle("")

    writer = FFMpegWriter(
        fps=args.fps,
        codec="libx264",
        extra_args=["-pix_fmt", "yuv420p", "-crf", "18"],
    )

    current_index = -1
    video_path = args.output / "bos.mp4"

    try:
        with writer.saving(figure, str(video_path), dpi=100):
            count = max(1, int(np.ceil(duration * args.fps)))

            for tick in range(count):
                video_time = tick / args.fps

                # Hold the previous measurement until the next sample time.
                index = max(
                    0,
                    int(np.searchsorted(
                        times, video_time, side="right"
                    )) - 1,
                )

                if index != current_index:
                    image, _ = read_frame(
                        args.sequence / frames[index]["path"]
                    )
                    image = np.ascontiguousarray(np.rot90(
                        image, k=-(args.rotate_cw // 90)
                    ))
                    raw_plot.set_data(image)

                    with np.load(
                        fields_dir / f"{index:06d}.npz"
                    ) as field:
                        bos_plot.set_data(np.ma.array(
                            field[f"{args.component}_px"],
                            mask=~field["valid"],
                        ))

                    current_index = index

                title.set_text(
                    f"t={video_time:.2f} s | "
                    f"sample={times[index]:.2f} s | "
                    "BOS displacement, not temperature"
                )

                writer.grab_frame()

    finally:
        plt.close(figure)

    print(f"Video saved to {video_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Record lossless BOS sequences and export processed videos"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    recording = commands.add_parser("record")
    recording.add_argument("output", type=Path)
    recording.add_argument("--seconds", type=float, default=10)
    recording.add_argument("--fps", type=float, default=10)
    recording.add_argument("--exposure-ms", type=float, default=5)
    recording.add_argument("--gain", type=int, default=0)

    processing = commands.add_parser("process")
    processing.add_argument("sequence", type=Path)
    processing.add_argument("output", type=Path)
    processing.add_argument(
        "--window", type=int, choices=(32, 40, 52), default=40
    )
    processing.add_argument(
        "--component", choices=("u", "v"), default="u"
    )
    processing.add_argument("--limit-px", type=float, default=1)
    processing.add_argument("--fps", type=float, default=10)
    processing.add_argument(
        "--rotate-cw", type=int, choices=(0, 90, 180, 270), default=0,
        help="Rotate reference and frames clockwise before BOS analysis.",
    )

    args = parser.parse_args()

    positive = [args.fps]

    if args.command == "record":
        positive += [args.seconds, args.exposure_ms]
        if not 0 <= args.gain <= 100:
            parser.error("Gain must be between 0 and 100.")
    else:
        positive += [args.limit_px]

    if not all(np.isfinite(x) and x > 0 for x in positive):
        parser.error("Numeric values must be finite and positive.")

    try:
        if args.command == "record":
            record(args)
        else:
            process(args)
    except (
        OSError, RuntimeError, ValueError,
        KeyError, ImportError, EOFError, KeyboardInterrupt,
    ) as error:
        print(f"Operation failed: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
