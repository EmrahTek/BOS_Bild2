import numpy as np

from bos.synthetic import make_pair
from bos.correlation import estimate_pair


def main() -> None:

    # Known displacement
    true_u = 2.0
    true_v = 1.0

    # Generate synthetic images
    reference, moving = make_pair(
        shape=(200, 300),
        u_px=true_u,
        v_px=true_v,
        seed=42,
        method="oversampled",
        noise_std=0.01
    )

    # Estimate displacement
    field = estimate_pair(
        reference,
        moving,
        window_px=40,
        step_px=20,
        search_radius_px=4
    )

    # Select valid measurements
    valid = field["valid"]

    if not np.any(valid):
        print("No valid displacement measurements found.")
        return

    # Calculate median displacement
    measured_u = np.median(field["u_px"][valid])
    measured_v = np.median(field["v_px"][valid])

    # Calculate errors
    error_u = measured_u - true_u
    error_v = measured_v - true_v

    print(f"Valid windows: {np.count_nonzero(valid)}")
    print(f"Total windows: {valid.size}")

    print(f"True u: {true_u:.3f} px")
    print(f"Measured u: {measured_u:.3f} px")

    print(f"True v: {true_v:.3f} px")
    print(f"Measured v: {measured_v:.3f} px")

    print(f"Error u: {error_u:.3f} px")
    print(f"Error v: {error_v:.3f} px")


if __name__ == "__main__":
    main()