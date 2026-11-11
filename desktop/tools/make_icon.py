"""Generate the TubeForge app icon (gradient rounded square + play/download)."""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

S = 1024
C1 = (124, 92, 255)   # violet
C2 = (34, 211, 238)   # cyan


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# diagonal gradient
base = Image.new("RGBA", (S, S), (0, 0, 0, 0))
px = base.load()
for y in range(S):
    for x in range(S):
        t = (x + y) / (2 * S - 2)
        px[x, y] = (*lerp(C1, C2, t), 255)

mask = Image.new("L", (S, S), 0)
d = ImageDraw.Draw(mask)
d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.235), fill=255)
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
img.paste(base, (0, 0), mask)

# subtle glossy highlight
gloss = Image.new("RGBA", (S, S), (0, 0, 0, 0))
gd = ImageDraw.Draw(gloss)
gd.ellipse([-S * 0.35, -S * 0.62, S * 1.35, S * 0.38], fill=(255, 255, 255, 34))
gloss.putalpha(Image.composite(gloss.getchannel("A"), Image.new("L", (S, S), 0), mask))
img = Image.alpha_composite(img, gloss)

# inner dark disc
disc = Image.new("RGBA", (S, S), (0, 0, 0, 0))
dd = ImageDraw.Draw(disc)
m = int(S * 0.155)
dd.ellipse([m, m, S - m, S - m], fill=(11, 14, 20, 242))
img = Image.alpha_composite(img, disc)

# gradient play triangle inside the disc
tri_mask = Image.new("L", (S, S), 0)
td = ImageDraw.Draw(tri_mask)
cx, cy = S * 0.515, S * 0.5
w, h = S * 0.205, S * 0.30
td.polygon([(cx - w * 0.55, cy - h * 0.5), (cx - w * 0.55, cy + h * 0.5), (cx + w * 0.72, cy)], fill=255)
tri = Image.new("RGBA", (S, S), (0, 0, 0, 0))
tp = tri.load()
for y in range(S):
    for x in range(S):
        t = (x + y) / (2 * S - 2)
        tp[x, y] = (*lerp(C2, C1, t), 255)
img.paste(tri, (0, 0), tri_mask)

# small download badge bottom-right
bx, by, br = int(S * 0.735), int(S * 0.735), int(S * 0.155)
badge = Image.new("RGBA", (S, S), (0, 0, 0, 0))
bd = ImageDraw.Draw(badge)
bd.ellipse([bx - br, by - br, bx + br, by + br], fill=(255, 255, 255, 255))
img = Image.alpha_composite(img, badge)

arrow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ad = ImageDraw.Draw(arrow)
aw = int(S * 0.030)
ad.rounded_rectangle([bx - aw, by - int(S * 0.078), bx + aw, by + int(S * 0.018)], radius=aw, fill=(11, 14, 20, 255))
ad.polygon([(bx - int(S * 0.052), by + int(S * 0.004)), (bx + int(S * 0.052), by + int(S * 0.004)), (bx, by + int(S * 0.062))], fill=(11, 14, 20, 255))
ad.rounded_rectangle([bx - int(S * 0.060), by + int(S * 0.072), bx + int(S * 0.060), by + int(S * 0.094)], radius=int(S * 0.011), fill=(11, 14, 20, 255))
img = Image.alpha_composite(img, arrow)

img.save(ASSETS / "logo.png")
img.resize((256, 256), Image.LANCZOS).save(
    ASSETS / "icon.ico",
    sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print("wrote", ASSETS / "icon.ico")
