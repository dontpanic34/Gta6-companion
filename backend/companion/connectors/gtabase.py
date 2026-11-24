"""Connecteur GTABase (gtabase.com/gta-6/).

Politique : synchronisation complète, lente (>= 3 s entre requêtes), via
sitemap + cache conditionnel. robots.txt respecté. Usage personnel.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

BASE = "https://www.gtabase.com"
SOURCE_ID = "gtabase"
SITEMAP_INDEX = f"{BASE}/sitemap-4seo.xml"
VEHICLE_URL = re.compile(r"^https://www\.gtabase\.com/gta-6/vehicles/([a-z0-9-]+)$")
WEAPON_URL = re.compile(r"^https://www\.gtabase\.com/gta-6/weapons/([a-z0-9-]+)$")
NON_ITEM_SLUGS = {"comparison", "best-vehicles", "best-weapons"}

# Clés de champ GTABase -> champ canonique interne
FIELD_MAP = {
    "manufacturer": "manufacturer", "vehicle-class": "class", "seats": "seats",
    "drivetrain": "drivetrain", "gears": "gears", "weight": "weight_kg",
    "gta6-model-year": "model_year", "based-on": "based_on", "converted-from": "base_model",
    "price-story": "price", "sell-price-stolen": "sell_price_stolen",
    "speed": "speed", "acceleration": "acceleration", "asphalt-handling": "handling_road",
    "off-road-handling": "handling_offroad", "strength": "strength",
    "gta6-style": "style", "gta6-era": "era", "gta6-security": "security",
    "gta6-keyless": "access", "gta6-tracker": "tracker", "gta6-can-register": "can_register",
    "gta6-standout-set": "standout_set", "gta6-specialist": "specialist",
    "gta6-body-condition": "body_condition", "game-edition": "game_edition",
    "how-to-unlock": "how_to_unlock",
    # armes (clés vérifiées sur 103 fiches réelles)
    "weapon-class": "class", "damage": "damage", "accuracy": "accuracy", "handling": "weapon_handling",
    "range": "range", "max-ammo": "capacity", "purchase": "purchase_from",
    "modifications": "moddable", "ammo-upgrade": "ammo_upgrade",
    "fire-rate": "fire_rate", "recoil": "recoil",
}
NUMERIC = {"seats", "gears", "weight_kg", "model_year", "price", "sell_price_stolen",
           "speed", "acceleration", "handling_road", "handling_offroad", "strength",
           "damage", "fire_rate", "range", "accuracy", "recoil", "capacity", "weapon_handling",
           "ammo_upgrade"}
STAT_SCALE_10 = {"speed", "acceleration", "handling_road", "handling_offroad", "strength",
                 "damage", "accuracy", "weapon_handling", "range"}


@dataclass
class ParsedItem:
    slug: str
    url: str
    kind: str                      # 'vehicle' | 'weapon'
    name: str
    fields: dict = field(default_factory=dict)
    base_model_slug: str | None = None
    images: list[str] = field(default_factory=list)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _number(s: str) -> float | int | None:
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", s)
    if not m:
        return None
    n = float(m.group(0).replace(",", ""))
    return int(n) if n.is_integer() else n


def parse_sitemap(xml: str) -> list[str]:
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)


def item_urls(urls: list[str]) -> list[tuple[str, str]]:
    out = []
    for u in urls:
        for kind, rx in (("vehicle", VEHICLE_URL), ("weapon", WEAPON_URL)):
            m = rx.match(u)
            if m and m.group(1) not in NON_ITEM_SLUGS:
                out.append((kind, u))
    return out


def parse_item(url: str, page: str, kind: str) -> ParsedItem:
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    name = _clean(h1.group(1)) if h1 else slug
    name = re.sub(r"^GTA 6\s+|\s+(?:GTA 6|in GTA 6)$", "", name).strip()
    item = ParsedItem(slug=slug, url=url, kind=kind, name=name)

    for m in re.finditer(r'<li class="field-entry ([\w-]+)[^"]*">(.*?)</li>', page, re.S):
        key, inner = m.group(1), m.group(2)
        canon = FIELD_MAP.get(key)
        if not canon or "field-value" not in inner:
            continue
        raw_html = inner.split("field-value", 1)[1].split(">", 1)[-1]
        if canon == "base_model":
            link = re.search(r'href="/gta-6/(?:vehicles|weapons)/([a-z0-9-]+)"', raw_html)
            item.base_model_slug = link.group(1) if link else None
            item.fields["base_model"] = _clean(raw_html)
            continue
        value = _clean(raw_html)
        if not value:
            continue
        if canon in NUMERIC:
            num = _number(value)
            if num is None:
                continue
            item.fields[canon] = num
        else:
            item.fields[canon] = value

    loc = re.search(r"Location:\s*(?:</[^>]+>\s*)*(.*?)(?:Here is the exact location|<img|</p>)", page, re.S)
    if loc and _clean(loc.group(1)):
        item.fields["location_text"] = _clean(loc.group(1))

    slug_key = slug.replace("-", "")
    for src in re.findall(r'<img[^>]+src="(/images/gta-6/[^"]+)"', page):
        if slug_key in src.replace("-", "") and "/maps/" not in src and src not in item.images:
            item.images.append(BASE + src.split("?")[0])
    return item
