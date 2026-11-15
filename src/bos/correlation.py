import numpy as np
from scipy.ndimage import maximum_filter
from scipy.signal import correlate

MIN_STD = 0.01
MIN_PEAK = 0.60
MIN_PEAK_MARGIN = 0.03


def _box_sums(image: np.ndarray, size: int) -> np.ndarray:
    # Each window sum is the difference of four cumulative sums.
    integral = np.pad(image.cumsum(axis=0).cumsum(axis=1), ((1, 0), (1, 0)))
    return (
        integral[size:, size:] - integral[:-size, size:]
        - integral[size:, :-size] + integral[:-size, :-size]
    )


def _ncc_scores(template: np.ndarray, search: np.ndarray) -> np.ndarray:
    centered = template - template.mean()
    template_energy = np.sum(centered**2)
    size = template.shape[0]

    candidate_sums = _box_sums(search, size)
    candidate_energy = _box_sums(search**2, size) - candidate_sums**2 / template.size
    candidate_energy = np.maximum(candidate_energy, 0.0)
    minimum_energy = template.size * MIN_STD**2
    scores = np.full(candidate_energy.shape, -np.inf)

    if template_energy >= minimum_energy:
        numerator = correlate(search, centered, mode="valid", method="fft")
        np.divide(
            numerator,
            np.sqrt(template_energy * candidate_energy),
            out=scores,
            where=candidate_energy >= minimum_energy,
        )
        finite = np.isfinite(scores)
        scores[finite] = np.clip(scores[finite], -1.0, 1.0)

    return scores


def _subpixel_offset(left: float, center: float, right: float) -> float:
    if not np.isfinite([left, center, right]).all():
        return np.nan

    curvature = left - 2.0 * center + right
    if curvature >= -1e-12:
        return np.nan

    offset = 0.5 * (left - right) / curvature
    return float(offset) if abs(offset) <= 0.5 else np.nan


def _estimate_window(
    template: np.ndarray, search: np.ndarray, radius: int
) -> tuple[float, float, float, float]:
    scores = _ncc_scores(template, search)
    peak_y, peak_x = np.unravel_index(scores.argmax(), scores.shape)
    peak = scores[peak_y, peak_x]

    if not np.isfinite(peak):
        return np.nan, np.nan, np.nan, np.nan

    last_index = 2 * radius
    if not (0 < peak_x < last_index and 0 < peak_y < last_index):
        return np.nan, np.nan, peak, np.nan

    local_peaks = scores == maximum_filter(scores, size=3, mode="constant", cval=-np.inf)
    local_peaks[peak_y - 1:peak_y + 2, peak_x - 1:peak_x + 2] = False
    second_peak = np.max(scores[local_peaks], initial=-np.inf)
    margin = peak - second_peak if np.isfinite(second_peak) else np.nan

    if peak < MIN_PEAK or (np.isfinite(margin) and margin < MIN_PEAK_MARGIN):
        return np.nan, np.nan, peak, margin

    offset_x = _subpixel_offset(scores[peak_y, peak_x - 1], peak, scores[peak_y, peak_x + 1])
    offset_y = _subpixel_offset(scores[peak_y - 1, peak_x], peak, scores[peak_y + 1, peak_x])
    if not np.isfinite([offset_x, offset_y]).all():
        return np.nan, np.nan, peak, margin

    return peak_x - radius + offset_x, peak_y - radius + offset_y, peak, margin


def estimate_pair(
    reference: np.ndarray,
    moving: np.ndarray,
    *,
    window_px: int = 40,
    step_px: int = 20,
    search_radius_px: int = 4,
) -> dict[str, np.ndarray]:
    """Estimate u (right) and v (down) on a regular grid in the reference image."""
    reference = np.asarray(reference, dtype=np.float64)
    moving = np.asarray(moving, dtype=np.float64)

    if reference.ndim != 2 or reference.shape != moving.shape:
        raise ValueError("Expected two grayscale images of the same shape.")
    if window_px < 2 or step_px < 1 or search_radius_px < 2:
        raise ValueError("Invalid window, grid step or search radius.")

    height, width = reference.shape
    radius = search_radius_px
    if min(height, width) < window_px + 2 * radius:
        raise ValueError("Image is too small for the window and its search border.")

    for image in (reference, moving):
        if not np.isfinite(image).all() or image.min() < 0.0 or image.max() > 1.0:
            raise ValueError("Expected finite grayscale values in [0, 1].")

    tops = np.arange(radius, height - window_px - radius + 1, step_px)
    lefts = np.arange(radius, width - window_px - radius + 1, step_px)
    center_offset = (window_px - 1) / 2.0
    x_px, y_px = np.meshgrid(lefts + center_offset, tops + center_offset)

    field = {"x_px": x_px, "y_px": y_px}
    field_names = ("u_px", "v_px", "ncc_peak", "peak_margin")
    for name in field_names:
        field[name] = np.full(x_px.shape, np.nan, dtype=np.float32)

    for row, top in enumerate(tops):
        for column, left in enumerate(lefts):
            bottom, right = top + window_px, left + window_px
            template = reference[top:bottom, left:right]
            search = moving[top - radius:bottom + radius, left - radius:right + radius]
            result = _estimate_window(template, search, radius)
            for name, value in zip(field_names, result):
                field[name][row, column] = value

    field["valid"] = np.isfinite(field["u_px"]) & np.isfinite(field["v_px"])
    return field