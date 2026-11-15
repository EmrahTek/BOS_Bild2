import numpy as np
from scipy.ndimage import gaussian_filter, shift, fourier_shift


# Simulation parameters
OVERSAMPLING = 8
PADDING_PX = 12

# Approximate Gaussian dot size in final image pixels
DOT_SIGMA_PX = 1.25


def downsample(
    image: np.ndarray,
    height: int,
    width: int
) -> np.ndarray:
    """Reduce image resolution by averaging pixel blocks."""

    expected_shape = (
        height * OVERSAMPLING,
        width * OVERSAMPLING
    )

    if image.shape != expected_shape:
        raise ValueError(
            f"Expected image shape {expected_shape}, "
            f"but received {image.shape}."
        )

    # Group high-resolution pixels into blocks
    blocks = image.reshape(
        height,
        OVERSAMPLING,
        width,
        OVERSAMPLING
    )

    # Average the pixels inside each block
    downsampled_image = blocks.mean(axis=(1, 3))

    return downsampled_image


def make_pair(
    shape: tuple[int, int],
    u_px: float,
    v_px: float,
    *,
    seed: int = 42,
    method: str = "oversampled",
    noise_std: float = 0.0
) -> tuple[np.ndarray, np.ndarray]:
    """Create a reference image and an image with a known shift."""

    # -------------------------------------------------
    # 1. Validate input parameters
    # -------------------------------------------------

    height, width = shape

    if height < 1 or width < 1:
        raise ValueError("Image dimensions must be positive.")

    if not np.isfinite([u_px, v_px]).all():
        raise ValueError("Displacements must be finite.")

    if abs(u_px) > 8 or abs(v_px) > 8:
        raise ValueError("Maximum displacement is 8 pixels.")

    if not np.isfinite(noise_std) or noise_std < 0:
        raise ValueError("Noise standard deviation must be valid.")

    if method not in ("oversampled", "fourier"):
        raise ValueError(f"Unknown method: {method}")

    # -------------------------------------------------
    # 2. Create random number generator
    # -------------------------------------------------

    rng = np.random.default_rng(seed)

    # -------------------------------------------------
    # 3. Calculate image dimensions with padding
    # -------------------------------------------------

    padded_height = height + 2 * PADDING_PX
    padded_width = width + 2 * PADDING_PX

    fine_height = padded_height * OVERSAMPLING
    fine_width = padded_width * OVERSAMPLING

    fine_shape = (fine_height, fine_width)

    # -------------------------------------------------
    # 4. Generate random dot positions
    # -------------------------------------------------

    dot_count = max(
        1,
        padded_height * padded_width // 45
    )

    dot_rows = rng.integers(
        0,
        fine_height,
        size=dot_count
    )

    dot_columns = rng.integers(
        0,
        fine_width,
        size=dot_count
    )

    # Create an empty grayscale image
    dots = np.zeros(fine_shape, dtype=np.float32)

    # Place the random dots
    dots[dot_rows, dot_columns] = 1.0

    # -------------------------------------------------
    # 5. Apply Gaussian blur
    # -------------------------------------------------

    sigma = DOT_SIGMA_PX * OVERSAMPLING

    darkness = gaussian_filter(
        dots,
        sigma=sigma,
        mode="constant"
    )

    # Create dark dots on a bright background
    pattern = 0.85 - 0.65 * darkness / darkness.max()

    # -------------------------------------------------
    # 6. Create the reference image
    # -------------------------------------------------

    reference = downsample(
        pattern,
        padded_height,
        padded_width
    )

    # -------------------------------------------------
    # 7. Create the shifted image
    # -------------------------------------------------

    if method == "oversampled":

        # Convert displacement to high-resolution pixels
        fine_shift = (
            v_px * OVERSAMPLING,
            u_px * OVERSAMPLING
        )

        # Shift high-resolution image
        shifted_pattern = shift(
            pattern,
            shift=fine_shift,
            order=1,
            mode="constant",
            cval=0.85
        )

        # Reduce shifted image resolution
        moving = downsample(
            shifted_pattern,
            padded_height,
            padded_width
        )

    else:

        # Transform reference image to frequency domain
        reference_spectrum = np.fft.fft2(reference)

        # Apply displacement in frequency domain
        shifted_spectrum = fourier_shift(
            reference_spectrum,
            shift=(v_px, u_px)
        )

        # Transform back to spatial domain
        moving = np.fft.ifft2(shifted_spectrum).real

    # -------------------------------------------------
    # 8. Remove padding
    # -------------------------------------------------

    reference = reference[
        PADDING_PX:-PADDING_PX,
        PADDING_PX:-PADDING_PX
    ]

    moving = moving[
        PADDING_PX:-PADDING_PX,
        PADDING_PX:-PADDING_PX
    ]

    # -------------------------------------------------
    # 9. Add independent Gaussian noise
    # -------------------------------------------------

    reference_noise = rng.normal(
        0.0,
        noise_std,
        shape
    )

    moving_noise = rng.normal(
        0.0,
        noise_std,
        shape
    )

    reference = reference + reference_noise
    moving = moving + moving_noise

    # -------------------------------------------------
    # 10. Limit pixel values to [0, 1]
    # -------------------------------------------------

    reference = np.clip(
        reference,
        0.0,
        1.0
    ).astype(np.float32)

    moving = np.clip(
        moving,
        0.0,
        1.0
    ).astype(np.float32)

    return reference, moving