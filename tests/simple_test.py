import moondream
from PIL import Image

IMG_PATH = ""

model = moondream.vl(endpoint="http://localhost:2020/v1")
print(
    model.query(
        Image.open(IMG_PATH),
        "what is going on here",
        reasoning=True,
    )
)
