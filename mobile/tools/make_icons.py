from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "desktop" / "assets" / "logo.png"
RES = ROOT / "mobile" / "app" / "src" / "main" / "res"

sizes = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
base = Image.open(SRC).convert("RGBA")


def round_crop(img: Image.Image) -> Image.Image:
    size = img.size[0]
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


for density, px in sizes.items():
    folder = RES / f"mipmap-{density}"
    folder.mkdir(parents=True, exist_ok=True)
    icon = base.resize((px, px), Image.LANCZOS)
    icon.save(folder / "ic_launcher.png")
    round_crop(icon).save(folder / "ic_launcher_round.png")
    print("wrote", folder, px)

# Adaptive icon (API 26+): safe zone is the inner 66% of the canvas.
for density, px in sizes.items():
    folder = RES / f"mipmap-{density}"
    canvas = int(px * 108 / 48)
    inner = int(canvas * 0.72)
    art = base.resize((inner, inner), Image.LANCZOS)
    layer = Image.new("RGBA", (canvas, canvas), (11, 14, 20, 255))
    layer.paste(art, ((canvas - inner) // 2, (canvas - inner) // 2), art)
    layer.save(folder / "ic_launcher_foreground.png")
    print("wrote foreground", folder, canvas)
