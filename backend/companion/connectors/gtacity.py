"""Connecteur GTACity — À LA DEMANDE uniquement.

Leurs CGU interdisent la copie en masse sans accord écrit. On ne lit donc qu'UNE
fiche à la fois, quand l'utilisateur l'ouvre (lieu touché sur la carte, question à
l'assistant), avec cache. Le sitemap public sert seulement d'index de noms -> URL.
"""
from __future__ import annotations

import html
import json
import re

from .gtabase import ParsedItem

SITEMAP = "https://gtacity.gg/sitemaps/fr.xml"
SOURCE_ID = "gtacity"
STAT = {"Speed": "speed", "Acceleration": "acceleration", "Handling": "handling_road",
        "Off-road": "handling_offroad", "Strength": "strength", "Seats": "seats"}
DRIVE = {"intégrale": "AWD", "propulsion": "RWD", "traction": "FWD"}


def norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def vehicle_index(sitemap_xml: str) -> dict[str, str]:
    """slug normalisé -> URL (fiches véhicules uniquement)."""
    out = {}
    for u in re.findall(r"<loc>([^<]+)</loc>", sitemap_xml):
        m = re.match(r"https://gtacity\.gg/fr/gta-6/vehicules/[a-z0-9-]+/([a-z0-9-]+)(?:/([a-z0-9-]+))?$", u)
        if m and m.group(1) not in ("compare",):
            out[norm((m.group(2) or m.group(1)).replace("-", " "))] = u
    return out


def find_url(index: dict[str, str], name: str) -> str | None:
    """« Canis Gunrunner Kamacho » -> …/kamacho/gunrunner-kamacho ; « Vapid Stanier (1955) » -> stanier-55.
    Le slug omet la marque ; les années s'écrivent sur 2 chiffres côté GTACity."""
    toks = norm(name).split()
    toks += [t[2:] for t in toks if re.fullmatch(r"(19|20)\d\d", t)]
    best, best_score = None, 0.0
    for slug, url in index.items():
        st = slug.split()
        words = [t for t in st if not t.isdigit()]
        if not words or not all(t in toks for t in words):
            continue                      # chaque mot (hors année) du slug doit figurer dans le nom
        years = [t for t in st if t.isdigit()]
        if years and not any(y in toks for y in years) and any(t.isdigit() for t in toks):
            continue                      # années contradictoires (Stanier 55 vs Stanier 98)
        score = len(words) / max(len([t for t in toks if not t.isdigit()]), 1) + 0.01 * sum(y in toks for y in years)
        if score > best_score:
            best, best_score = url, score
    return best if best_score >= 0.5 else None


def parse_vehicle(url: str, page: str) -> ParsedItem | None:
    about = None
    for b in re.findall(r'<script[^>]*ld\+json[^>]*>(.*?)</script>', page, re.S):
        try:
            d = json.loads(b)
        except ValueError:
            continue
        for g in d.get("@graph", [d]):
            a = g.get("about") if isinstance(g, dict) else None
            if isinstance(a, dict) and a.get("@type") == "Product":
                about = a
    if not about:
        return None
    m = re.match(r".*/vehicules/([a-z0-9-]+)/([a-z0-9-]+)(?:/([a-z0-9-]+))?$", url)
    cls, model, variant = m.group(1), m.group(2), m.group(3)
    fields: dict = {"manufacturer": (about.get("brand") or {}).get("name"), "class": cls.replace("-", " ").title()}
    for p in about.get("additionalProperty", []):
        k = STAT.get(p.get("name"))
        if k and isinstance(p.get("value"), (int, float)):
            fields[k] = p["value"]
    tr = re.search(r"Transmission\s*</[^>]+>\s*<[^>]+>\s*([^<]+)", page)
    if tr:
        low = html.unescape(tr.group(1)).lower()
        drive = next((v for k, v in DRIVE.items() if k in low), None)
        if drive:
            fields["drivetrain"] = drive
    img = re.search(r'(https://assets\.codmunity\.gg/[^"\s]+\.(?:webp|jpg|png))', page)
    it = ParsedItem(slug=variant or model, url=url, kind="vehicle", name=html.unescape(about.get("name", model)),
                    fields={k: v for k, v in fields.items() if v is not None},
                    base_model_slug=model if variant else None, images=[img.group(1)] if img else [])
    return it
