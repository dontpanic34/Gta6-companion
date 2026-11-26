"""Découpe une planche d'icônes (grille) en PNG transparents.
Le « damier de transparence » dessiné dans l'image est retiré par remplissage depuis les bords
(pixels clairs et peu saturés), puis un liseré blanc + contour sombre est recréé autour du dessin."""
import sys
from collections import deque
from pathlib import Path
from PIL import Image, ImageFilter, ImageChops

src, out = Path(sys.argv[1]), Path(sys.argv[2])
cols, rows, size = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
out.mkdir(parents=True, exist_ok=True)
img = Image.open(src).convert("RGB")
W, H = img.size
cw, ch = W / cols, H / rows


def is_bg(p):
    r, g, b = p
    return min(r, g, b) > 185 and max(r, g, b) - min(r, g, b) < 22   # blanc / gris clair du damier


def keep_main(mask):
    """Garde la plus grande zone du dessin (et ce qui la touche presque), retire les fragments isolés."""
    import numpy as np
    a = np.array(mask) > 0
    h, w = a.shape
    lab = np.zeros((h, w), np.int32); n = 0; sizes = {}
    for y in range(h):
        for x in range(w):
            if a[y, x] and not lab[y, x]:
                n += 1; stack = [(y, x)]; lab[y, x] = n; cnt = 0
                while stack:
                    cy, cx = stack.pop(); cnt += 1
                    for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                        if 0 <= ny < h and 0 <= nx < w and a[ny, nx] and not lab[ny, nx]:
                            lab[ny, nx] = n; stack.append((ny, nx))
                sizes[n] = cnt
    if not sizes:
        return mask
    big = max(sizes, key=sizes.get)
    keep = {k for k, v in sizes.items() if v >= sizes[big] * 0.04}   # gros morceaux = parties du même dessin
    out = np.isin(lab, list(keep))
    return Image.fromarray((out * 255).astype("uint8"))


for j in range(rows):
    for i in range(cols):
        box = (int(i * cw), int(j * ch), int((i + 1) * cw), int((j + 1) * ch))
        cell = img.crop(box)
        w, h = cell.size
        px = cell.load()
        mask = Image.new("L", (w, h), 255)
        m = mask.load()
        q = deque([(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)])
        seen = set()
        while q:
            x, y = q.popleft()
            if (x, y) in seen or not (0 <= x < w and 0 <= y < h):
                continue
            seen.add((x, y))
            if not is_bg(px[x, y]):
                continue
            m[x, y] = 0
            q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
        mask = mask.filter(ImageFilter.MedianFilter(3))
        mask = keep_main(mask)          # retire les bouts des icônes voisines
        bbox = mask.getbbox()
        if not bbox:
            continue
        art = Image.new("RGBA", (w, h), (0, 0, 0, 0)); art.paste(cell, (0, 0), mask)
        art, mask = art.crop(bbox), mask.crop(bbox)
        # recentrage sur un carré + marge pour le liseré
        side = int(max(art.size) * 1.18)
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        off = ((side - art.size[0]) // 2, (side - art.size[1]) // 2)
        m2 = Image.new("L", (side, side), 0); m2.paste(mask, off)
        rim = m2.filter(ImageFilter.MaxFilter(int(side * 0.035) | 1))          # liseré blanc
        edge = rim.filter(ImageFilter.MaxFilter(int(side * 0.02) | 1))          # contour sombre
        canvas.paste((20, 10, 36, 255), (0, 0), edge)
        canvas.paste((255, 255, 255, 255), (0, 0), rim)
        canvas.paste(art, off, art)
        canvas.resize((size, size), Image.LANCZOS).save(out / f"{j * cols + i:02d}.png", optimize=True)
print("ok")
