"""Connecteur GTA6Map.city (pages HTML publiques uniquement).

robots.txt interdit /data/ et /tiles/ : on ne les touche JAMAIS (le client
HTTP vérifie robots.txt avant chaque requête). On lit seulement les pages
/fr/locations/<catégorie>/ et /fr/secrets/<slug>/.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

BASE = "https://gta6map.city"
SOURCE_ID = "gta6map"
LOCATIONS_INDEX = f"{BASE}/fr/locations/"
SECRETS_INDEX = f"{BASE}/fr/secrets/"
# Pages de regroupement (pas des secrets individuels)
SECRET_HUBS = {"activities", "creatures-encounters", "easter-eggs", "hidden-places", "hidden-weapons",
               "meditation-spots", "money-stashes", "mysteries", "new", "rare-vehicles",
               "references-cameos", "tips-mechanics", "trophies-missables", "safe-codes"}

CATEGORY_KIND = {
    "Créatures et rencontres": "random_encounter", "Easter eggs": "easter_egg", "Mystères": "mystery",
    "Lieux cachés": "location", "Armes cachées": "collectible", "Véhicules rares": "collectible",
    "Planques d’argent": "collectible", "Activités": "activity", "Références et caméos": "easter_egg",
}


@dataclass
class MapLocation:
    marker_id: str
    name: str
    category_slug: str
    category_name: str
    region: str | None
    subarea: str | None
    description: str | None
    x: float | None = None
    y: float | None = None
    url: str = ""


@dataclass
class Secret:
    slug: str
    url: str
    title: str
    category: str | None
    tags: list[str] = field(default_factory=list)
    where: str | None = None
    what: str | None = None
    precision: str = "unknown"
    region: str | None = None
    reliability: str = "to_verify"
    creators: int | None = None
    image: str | None = None
    video: str | None = None


def _clean(s: str | None) -> str | None:
    if s is None:
        return None
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
    return t or None


def category_urls(index_html: str) -> list[str]:
    slugs = sorted(set(re.findall(r'href="/fr/locations/([a-z0-9-]+)/"', index_html)))
    return [f"{BASE}/fr/locations/{s}/" for s in slugs]


def secret_links(page: str) -> tuple[list[str], list[str]]:
    """Retourne (secrets individuels, pages de regroupement)."""
    slugs = sorted(set(re.findall(r'href="/fr/secrets/([a-z0-9-]+)/"', page)))
    items = [f"{BASE}/fr/secrets/{s}/" for s in slugs if s not in SECRET_HUBS]
    hubs = [f"{BASE}/fr/secrets/{s}/" for s in slugs if s in SECRET_HUBS]
    return items, hubs


_COORD = re.compile(r"-(-?\d+(?:\.\d+)?)_(-?\d+(?:\.\d+)?)$")


def parse_category(url: str, page: str) -> list[MapLocation]:
    cat_slug = url.rstrip("/").rsplit("/", 1)[-1]
    crumb = re.findall(r'"name":"([^"]+)","item":"[^"]+/locations/[a-z0-9-]+/"', page)
    cat_name = crumb[-1] if crumb else cat_slug
    out: list[MapLocation] = []
    # Découpe par région (<h2>Région <small>n</small></h2><ul class="rows">…</ul>)
    for block in re.finditer(r"<h2>(.*?)</h2>\s*<ul class=\"rows\">(.*?)</ul>", page, re.S):
        region = _clean(re.sub(r"<small.*?</small>", "", block.group(1), flags=re.S))
        for li in re.finditer(r"<li>(.*?)</li>", block.group(2), re.S):
            a = re.search(r'href="/fr/\?m=([^"]+)">(.*?)</a>', li.group(1), re.S)
            if not a:
                continue
            mid = html.unescape(a.group(1))
            d = re.search(r'<span class="d">(.*?)</span>', li.group(1), re.S)
            sub = re.search(r"<small>(.*?)</small>", li.group(1), re.S)
            loc = MapLocation(marker_id=mid, name=_clean(a.group(2)) or mid, category_slug=cat_slug,
                              category_name=cat_name, region=region, subarea=_clean(sub.group(1)) if sub else None,
                              description=_clean(d.group(1)) if d else None, url=f"{BASE}/fr/?m={mid}")
            c = _COORD.search(mid)
            if c:
                loc.x, loc.y = float(c.group(1)), float(c.group(2))
            out.append(loc)
    return out


PRECISION = {"exact": "exact", "à proximité": "nearby", "zone": "zone"}


def parse_secret(url: str, page: str) -> Secret:
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    title = _clean((re.search(r"<h1>(.*?)</h1>", page, re.S) or [None, slug])[1]) or slug
    eyebrow = re.search(r'<p class="eyebrow">GTA 6 · (.*?)</p>', page, re.S)
    s = Secret(slug=slug, url=url, title=title, category=_clean(eyebrow.group(1)) if eyebrow else None)
    tags_html = re.search(r'<div class="tags">(.*?)</div>', page, re.S)
    if tags_html:
        s.tags = [t for t in (_clean(x) for x in re.findall(r"<span[^>]*>(.*?)</span>", tags_html.group(1), re.S)) if t]
    for t in s.tags:
        tl = t.lower()
        if tl in PRECISION:
            s.precision = PRECISION[tl]
        elif tl.startswith("montré par"):
            n = re.search(r"\d+", t)
            s.creators = int(n.group(0)) if n else None
        elif "confirmé" in tl:
            s.reliability = "confirmed"
        elif "signalé" in tl:
            s.reliability = "probable" if (s.creators or 0) >= 2 else "to_verify"
        elif "théorie" in tl or "rumeur" in tl:
            s.reliability = "theory"
        else:
            s.region = s.region or t
    if s.reliability == "to_verify" and (s.creators or 0) >= 2 and any("signalé" in t.lower() for t in s.tags):
        s.reliability = "probable"

    def section(title_rx: str) -> str | None:
        m = re.search(rf"<h2><span[^>]*>{title_rx}</span></h2>(.*?)(?=<h2|$)", page, re.S)
        return _clean(m.group(1)) if m else None

    s.where = section(r"Où le trouver")
    s.what = section(r"De quoi s(?:’|')agit-il")
    img = re.search(r'<a class="hero"[^>]*><img src="([^"]+)"', page)
    s.image = BASE + img.group(1) if img else None
    vid = re.search(r'<button class="vid[^"]*"[^>]*>(.*?)</button>', page, re.S)
    s.video = _clean(vid.group(1)) if vid else None
    return s
