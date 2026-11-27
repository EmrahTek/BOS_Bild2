import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from bos.io import write_frame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)
CHANNELS = 3
BITS_PER_PIXEL = 24


def require_success(ueye, status: int, operation: str) -> None:
    if status != ueye.IS_SUCCESS:
        raise RuntimeError(f"{operation} failed (uEye return code {status}).")


def get_image_size(ueye, camera):
    image_area = ueye.IS_RECT()
    require_success(
        ueye, ueye.is_AOI(camera, ueye.IS_AOI_IMAGE_GET_AOI,
                         image_area, ueye.sizeof(image_area)),
        "Read image area",
    )
    width, height = image_area.s32Width.value, image_area.s32Height.value
    if width <= 0 or height <= 0:
        raise RuntimeError(f"Invalid image dimensions: {width} x {height}")
    return width, height


def configure_camera(ueye, camera, exposure_ms: float, gain: int) -> float:
    require_success(
        ueye, ueye.is_SetExternalTrigger(camera, ueye.IS_SET_TRIGGER_OFF),
        "Disable external trigger",
    )
    require_success(
        ueye, ueye.is_SetDisplayMode(camera, ueye.IS_SET_DM_DIB),
        "Set DIB memory mode",
    )
    require_success(
        ueye, ueye.is_SetColorMode(camera, ueye.IS_CM_RGB8_PACKED),
        "Set packed RGB8",
    )

    maximum = ueye.IS_SIZE_2D()
    require_success(
        ueye, ueye.is_AOI(camera, ueye.IS_AOI_IMAGE_GET_SIZE_MAX,
                         maximum, ueye.sizeof(maximum)),
        "Read maximum image size",
    )
    image_area = ueye.IS_RECT(
        s32X=0, s32Y=0,
        s32Width=maximum.s32Width.value, s32Height=maximum.s32Height.value,
    )
    require_success(
        ueye, ueye.is_AOI(camera, ueye.IS_AOI_IMAGE_SET_AOI,
                         image_area, ueye.sizeof(image_area)),
        f"Set full image area ({maximum.s32Width.value} x {maximum.s32Height.value})",
    )
    width, height = get_image_size(ueye, camera)
    LOGGER.info("Camera image area: %d x %d", width, height)

    for command, label in (
        (ueye.IS_SET_ENABLE_AUTO_SHUTTER, "exposure"),
        (ueye.IS_SET_ENABLE_AUTO_GAIN, "gain"),
        (ueye.IS_SET_ENABLE_AUTO_WHITEBALANCE, "white balance"),
    ):
        status = ueye.is_SetAutoParameter(camera, command, ueye.double(0), None)
        if status == ueye.IS_NOT_SUPPORTED:
            LOGGER.info("Auto %s is unavailable on this camera.", label)
        else:
            require_success(ueye, status, f"Disable auto {label}")

    unchanged = ueye.IS_IGNORE_PARAMETER
    status = ueye.is_SetHardwareGain(camera, gain, unchanged, unchanged, unchanged)
    require_success(ueye, status, "Set master gain")

    exposure = ueye.double(exposure_ms)
    status = ueye.is_Exposure(
        camera, ueye.IS_EXPOSURE_CMD_SET_EXPOSURE, exposure, ueye.sizeof(exposure)
    )
    require_success(ueye, status, "Set exposure")
    return exposure.value


def capture_pair(ueye, exposure_ms: float, gain: int, heated: bool):
    camera = ueye.HIDS(0)
    require_success(ueye, ueye.is_InitCamera(camera, None), "Open camera")

    try:
        actual_exposure_ms = configure_camera(ueye, camera, exposure_ms, gain)
        width, height = get_image_size(ueye, camera)

        memory = ueye.c_mem_p()
        memory_id, pitch_bytes = ueye.int(), ueye.int()
        status = ueye.is_AllocImageMem(
            camera, width, height, BITS_PER_PIXEL, memory, memory_id
        )
        require_success(ueye, status, "Allocate image memory")
        status = ueye.is_SetImageMem(camera, memory, memory_id)
        require_success(ueye, status, "Activate image memory")
        status = ueye.is_InquireImageMem(
            camera, memory, memory_id, None, None, None, pitch_bytes
        )
        require_success(ueye, status, "Read image row stride")

        pitch = pitch_bytes.value
        row_bytes = width * CHANNELS
        if not memory.value or pitch < row_bytes:
            raise RuntimeError(f"Invalid image buffer or row stride: {pitch} bytes.")

        LOGGER.info(
            "Camera ready: %d x %d RGB8 | exposure %.3f ms | master gain %d",
            width, height, actual_exposure_ms, gain,
        )

        moving_prompt = (
            "When the warm-air flow is ready, press Enter for the heated frame..."
            if heated
            else "Keep the setup still and press Enter for the second frame..."
        )

        frames = []
        for name, prompt in (
            ("reference", "With the heater off, press Enter for the reference frame..."),
            ("moving", moving_prompt),
        ):
            input(prompt)
            status = ueye.is_FreezeVideo(camera, ueye.IS_WAIT)
            require_success(ueye, status, f"Capture {name} frame")
            timestamp = datetime.now(timezone.utc).isoformat()

            # Copy the frame before the driver can reuse its buffer.
            data = ueye.get_data(memory, width, height, BITS_PER_PIXEL, pitch, copy=True)
            rows = data.reshape(height, pitch)
            rgb = rows[:, :row_bytes].reshape(height, width, CHANNELS)

            frames.append((name, np.ascontiguousarray(rgb), timestamp))
            LOGGER.info("Captured %s frame.", name)
    finally:
        # The driver also releases the allocated image memory on exit.
        close_status = ueye.is_ExitCamera(camera)
        if close_status != ueye.IS_SUCCESS:
            LOGGER.error("Close camera failed (uEye return code %s).", close_status)

    require_success(ueye, close_status, "Close camera")
    return frames, actual_exposure_ms


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture a BOS image pair with IDS uEye.")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--exposure-ms", type=float, default=5.0)
    parser.add_argument("--gain", type=int, default=0)
    parser.add_argument("--heated", action="store_true")
    args = parser.parse_args()

    if not np.isfinite(args.exposure_ms) or args.exposure_ms <= 0:
        parser.error("--exposure-ms must be finite and positive.")
    if not 0 <= args.gain <= 100:
        parser.error("--gain must be between 0 and 100.")

    try:
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_dir / "capture.log", encoding="utf-8"),
            ],
        )

        if args.output_dir.exists():
            raise FileExistsError(f"Output folder already exists: {args.output_dir}")

        from pyueye import ueye

        frames, actual_exposure_ms = capture_pair(
            ueye, args.exposure_ms, args.gain, args.heated
        )

        args.output_dir.mkdir(parents=True, exist_ok=False)
        for name, image, timestamp in frames:
            frame_dir = args.output_dir / name
            frame_dir.mkdir()
            write_frame(frame_dir, image, source="ids_ueye", timestamp_utc=timestamp)

        settings = {
            "test": "heated" if args.heated else "static",
            "exposure_requested_ms": args.exposure_ms,
            "exposure_set_ms": actual_exposure_ms,
            "master_gain_requested": args.gain,
            "timestamp_source": "host_utc_after_frame",
        }
        with (args.output_dir / "camera.json").open("x", encoding="utf-8") as file:
            json.dump(settings, file, indent=2)

        LOGGER.info("Saved complete image pair to %s", args.output_dir.resolve())
        return 0

    except (KeyboardInterrupt, EOFError):
        LOGGER.info("Capture cancelled.")
        return 1
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        LOGGER.error("Capture failed: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
