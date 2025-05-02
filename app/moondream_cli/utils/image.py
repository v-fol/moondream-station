from PIL import Image
import os


def load_image(image_path: str) -> Image.Image:
    """Load an image from a file path."""
    if not os.path.exists(image_path):
        print(f"Error: Image not found at path '{image_path}'")
        raise FileNotFoundError(f"Image not found at {image_path}")

    try:
        return Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"Error loading image: {e}")
        raise
