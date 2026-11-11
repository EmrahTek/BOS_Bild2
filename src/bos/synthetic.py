import numpy as np
from scipy.ndimage import fourier_shift, gaussian_filter, shift

OVERSAMPLING = 8
PADDING_PX = 12

def _downsample(image: np.ndarray, height: int, width: int) -> np.ndarray:
    blocks = image.reshape(height, OVERSAMPLING, width, OVERSAMPLING)
    return blocks.mean(axis=(1,3))

