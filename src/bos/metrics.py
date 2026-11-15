import numpy as np


def score_known_shift(
    field: dict[str, np.ndarray], u_true_px: float, v_true_px: float
) -> dict[str, float]:
    valid = field["valid"]
    if not np.any(valid):
        return {
            "valid_fraction": 0.0,
            "bias_u_px": np.nan,
            "bias_v_px": np.nan,
            "rmse_px": np.nan,
        }

    error_u = field["u_px"][valid] - u_true_px
    error_v = field["v_px"][valid] - v_true_px

    return {
        "valid_fraction": float(valid.mean()),
        "bias_u_px": float(error_u.mean()),
        "bias_v_px": float(error_v.mean()),
        "rmse_px": float(np.sqrt(np.mean(error_u**2 + error_v**2))),
    }