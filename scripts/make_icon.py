"""Génère l'icône Android (soleil rétro à bandes + palmier, style Vice City) et l'écran de démarrage."""
import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

RES = Path(sys.argv[1])
TOP, MID, LOW = (42, 14, 77), (255, 61, 139), (255, 154, 61)


def lerp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def sky(size):
    im = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(im)
    for y in range(size):
        t = y / size
        d.line([(0, y), (size, y)], fill=lerp(TOP, MID, t / .62) if t < .62 else lerp(MID, LOW, (t - .62) / .38))
    return im


def scene(size, transparent=False):
    S = size * 4  # suréchantillonnage
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)) if transparent else sky(S).convert("RGBA")
    d = ImageDraw.Draw(im)
    cx, cy, r = S * .5, S * .52, S * .25
    sun = Image.new("RGBA", (S, S), (0, 0, 0, 0)); sd = ImageDraw.Draw(sun)
    for y in range(int(cy - r), int(cy + r)):
        t = (y - (cy - r)) / (2 * r)
        sd.line([(0, y), (S, y)], fill=lerp((255, 224, 138), (255, 61, 139), t) + (255,))
    mask = Image.new("L", (S, S), 0); md = ImageDraw.Draw(mask)
    md.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    for i in range(5):  # bandes rétro
        y = cy + r * (.12 + i * .2); h = r * (.04 + i * .025)
        md.rectangle([0, y, S, y + h], fill=0)
    im.paste(sun, (0, 0), mask)
    # mer
    d.rectangle([0, S * .74, S, S], fill=(20, 10, 36, 255))
    for i in range(3):
        w = S * (.22 + i * .08); y = S * (.79 + i * .055)
        d.rounded_rectangle([cx - w / 2, y, cx + w / 2, y + S * .012], radius=S * .006, fill=(255, 154, 61, 220 - i * 50))
    # palmier
    px, base = S * .3, S * .76
    trunk = [(px - S * .018, base), (px + S * .012, base)]
    pts = []
    for k in range(21):
        t = k / 20; x = px + math.sin(t * 1.4) * S * .09; y = base - t * S * .5
        pts.append((x, y))
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        w = S * (.022 - .008 * (y1 / base))
        d.line([(x1, y1), (x2, y2)], fill=(20, 10, 36, 255), width=int(S * .028))
    tx, ty = pts[-1]
    # palmes : courbes de Bézier tombantes, épaisseur décroissante + folioles
    for ang, ln, droop in [(-170, .30, .16), (-140, .27, .12), (-105, .2, .05), (-70, .22, .06), (-35, .29, .13), (-5, .31, .17), (200, .22, .14)]:
        a_ = math.radians(ang)
        ex, ey = tx + math.cos(a_) * S * ln, ty + math.sin(a_) * S * ln * .55
        cx_, cy_ = (tx + ex) / 2, min(ty, ey) - S * .07
        ey += S * droop
        prev = (tx, ty)
        for k in range(1, 25):
            t = k / 24
            x = (1 - t) ** 2 * tx + 2 * (1 - t) * t * cx_ + t * t * ex
            y = (1 - t) ** 2 * ty + 2 * (1 - t) * t * cy_ + t * t * ey
            w = int(S * .026 * (1 - t * .85)) + 1
            d.line([prev, (x, y)], fill=(20, 10, 36, 255), width=w)
            if k % 3 == 0 and t < .95:  # folioles
                nx, ny = -(y - prev[1]), (x - prev[0]); nl = math.hypot(nx, ny) or 1
                L = S * .045 * (1 - t * .6)
                d.line([(x, y), (x + nx / nl * L * .4 + (x - prev[0]) * .3, y + abs(ny / nl) * L + S * .01)], fill=(20, 10, 36, 255), width=max(2, w // 2))
            prev = (x, y)
    return im.resize((size, size), Image.LANCZOS)


DENS = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
for name, k in DENS.items():
    folder = RES / f"mipmap-{name}"
    legacy = scene(int(48 * k))
    legacy.save(folder / "ic_launcher.png")
    m = Image.new("L", legacy.size, 0); ImageDraw.Draw(m).ellipse([0, 0, legacy.size[0] - 1, legacy.size[1] - 1], fill=255)
    rnd = Image.new("RGBA", legacy.size, (0, 0, 0, 0)); rnd.paste(legacy, (0, 0), m); rnd.save(folder / "ic_launcher_round.png")
    # icône adaptative : 108 dp dont 72 dp visibles -> scène pleine (le fond est le ciel)
    scene(int(108 * k)).save(folder / "ic_launcher_foreground.png")
(RES / "values" / "ic_launcher_background.xml").write_text(
    '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">#2A0E4D</color>\n</resources>\n')
# écrans de démarrage : fond nuit + icône centrée
for d in RES.glob("drawable*"):
    sp = d / "splash.png"
    if sp.exists():
        w, h = Image.open(sp).size
        bg = Image.new("RGB", (w, h), (20, 10, 36)); s = int(min(w, h) * .38)
        ic = scene(s); m = Image.new("L", (s, s), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, s, s], radius=s // 5, fill=255)
        bg.paste(ic, ((w - s) // 2, (h - s) // 2), m); bg.save(sp)
scene(512).save(RES.parent.parent.parent.parent.parent / "public" / "icon-512.png")
print("icônes générées")
