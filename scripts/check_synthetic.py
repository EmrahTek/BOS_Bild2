import matplotlib.pyplot as plt

# Import make_pair from your own module
# Adjust this import to your actual module name
from bos.synthetic import make_pair


def main() -> None:

    reference, moving = make_pair(
        shape=(200, 300),
        u_px=2.0,
        v_px=1.0,
        seed=42,
        method="oversampled",
        noise_std=0.01
    )

    print("Reference shape:", reference.shape)
    print("Moving shape:", moving.shape)

    print("Reference dtype:", reference.dtype)
    print("Moving dtype:", moving.dtype)

    plt.figure(figsize=(8, 5))
    plt.imshow(reference, cmap="gray", vmin=0, vmax=1)
    plt.title("Reference Image")
    plt.axis("off")
    plt.show()

    plt.figure(figsize=(8, 5))
    plt.imshow(moving, cmap="gray", vmin=0, vmax=1)
    plt.title("Shifted Image")
    plt.axis("off")
    plt.show()


if __name__ == "__main__":
    main()