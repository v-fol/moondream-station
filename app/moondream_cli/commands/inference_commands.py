from urllib.error import URLError
from moondream_cli.utils.image import load_image


class InferenceCommands:
    """Inference-related commands for Moondream CLI."""

    def __init__(self, md):
        self.md = md

    def caption(
        self,
        image_path: str,
        length: str = "normal",
        stream: bool = True,
        max_tokens: int = 500,
    ) -> None:
        """Generate a caption for an image."""
        settings = {"max_tokens": max_tokens}

        try:
            image = load_image(image_path)
            print(f"Generating {'streaming ' if stream else ''}caption...")

            if stream:
                # Handle streaming response
                for chunk in self.md.caption(image, length=length, stream=True)[
                    "caption"
                ]:
                    print(chunk, end="", flush=True)
                print("\n------ Completed ------")
            else:
                # Handle regular response
                result = self.md.caption(image, length=length, settings=settings)
                print(f"Caption: {result.get('caption')}")

        except Exception as e:
            print(f"Error generating caption: {e}")
            if isinstance(e, URLError):
                print(
                    "Moondream Station was not able to be reached. Ensure it is running."
                )

    def query(
        self, image_path: str, question: str, stream: bool = True, max_tokens: int = 500
    ) -> None:
        """Answer a visual query about an image."""
        settings = {"max_tokens": max_tokens}

        try:
            image = load_image(image_path)
            print(f"Answering {'streaming ' if stream else ''}query: {question}")

            if stream:
                # Handle streaming response
                for chunk in self.md.query(image, question, stream=True)["answer"]:
                    print(chunk, end="", flush=True)
                print("\n------ Completed ------")
            else:
                # Handle regular response
                result = self.md.query(image, question, settings=settings)
                print(f"Answer: {result.get('answer')}")

        except Exception as e:
            print(f"Error generating query: {e}")
            if isinstance(e, URLError):
                print(
                    "Moondream Station was not able to be reached. Ensure it is running."
                )

    def detect(self, image_path: str, obj: str) -> None:
        """Detect objects in an image."""
        try:
            image = load_image(image_path)
            print(f"Detecting object: {obj}")

            result = self.md.detect(image, obj)

            objects = result.get("objects", [])
            if not objects:
                print(f"No {obj} objects detected.")
            else:
                print(f"Detected {len(objects)} {obj}(s):")
                for obj_data in objects:
                    print(f"  Position: {obj_data}")

        except Exception as e:
            print(f"Error detecting objects: {e}")
            if isinstance(e, URLError):
                print(
                    "Moondream Station was not able to be reached. Ensure it is running."
                )

    def point(self, image_path: str, obj: str) -> None:
        """Find points corresponding to an object in an image."""
        try:
            image = load_image(image_path)
            print(f"Finding points for: {obj}")

            result = self.md.point(image, obj)

            points = result.get("points", [])
            count = len(points)

            if not points:
                print(f"No points found for {obj}.")
            else:
                print(f"Found {count} point(s) for {obj}:")
                for point in points:
                    print(f"  {point}")

        except Exception as e:
            print(f"Error finding points: {e}")
            if isinstance(e, URLError):
                print(
                    "Moondream Station was not able to be reached. Ensure it is running."
                )
