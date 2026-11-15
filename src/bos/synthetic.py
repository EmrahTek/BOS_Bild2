import numpy as np
from scipy.ndimage import fourier_shift, gaussian_filter, shift

OVERSAMPLING = 8
PADDING_PX = 12

def _downsample(image: np.ndarray, height: int, width: int) -> np.ndarray:
    blocks = image.reshape(height, OVERSAMPLING, width, OVERSAMPLING)
    return blocks.mean(axis=(1,3))

def make_pair( shape: tuple[int,int], u_px: float, v_px: float, *, seed: int = 42, method: str = "oversampled", noise_std: float = 0.0,)-> tuple[np.ndarray, np.ndarray]:
    """Generate a grayscale reference and a shifted image in the range [0,1]."""
    height, width = shape
    if height < 1 or width < 1:
        raise ValueError("Image dimensions must be positive.")
    if not np.isfinite([u_px, v_px]).all() or max(abs(u_px), abs(v_px)) > 8:
        raise ValueError("Synthetic shifts must be within +/-8 px on each axis.")
    
    if not np.isfinite(noise_std) or noise_std < 0 :
        raise ValueError("Noise standard deviation must be finite and non-negtative.")
    
    rng = np.random.default_rng(seed)
    height += 2 * PADDING_PX
    width += 2 * PADDING_PX
    fine_shape = (height*OVERSAMPLING, width*OVERSAMPLING)

    dot_count = max(1,height*width // 45)
    dot_rows = rng.integers(0, fine_shape[0], size = dot_count)
    dot_columns = rng.integers(0,fine_shape[1], size=dot_count)
    dots = np.zeros(fine_shape, dtype=np.float32)
    dots[dot_rows, dot_columns] = 1.0

    darkness = gaussian_filter(dots, sigma=125 * OVERSAMPLING, mode= "constant")
    pattern = 0.85 - 0.65*darkness / darkness.max()
    reference = _downsample(pattern, height,width)

    # Scipy uses array order: (rows, columns), so the shift is ( v,u).
    if method == "oversampled":
        fine_shift = (v_px * OVERSAMPLING, u_px * OVERSAMPLING)
        shifted_pattern = shift(pattern, fine_shift, order=1, mode="constant", cval= 0.85)
        moving = _downsample(shifted_pattern,height, width)
    elif method == "fourier":
        shifted_spectrum = fourier_shift(np.fft.fft2(reference), (v_px,u_px))
        moving = np.fft.ifft2(shifted_spectrum).real
    else:
        raise ValueError(f"Unknown synthetic shift method: {method}")

    inner = np.s_[PADDING_PX: - PADDING_PX:-PADDING_PX]
    reference = reference[inner] + rng.normal(0.0, noise_std,shape)
    moving = moving[inner] + rng.normal(0.0, noise_std, shape)

    return (
        np.clip(reference, 0.0, 1.0).astype(np.float32),
        np.clip(moving, 0.0, 1.0).astype(np.float32),
    )


        
    
