"""Connecteur GTA Wiki (gta.wiki) — licence CC BY-NC-SA 3.0 (usage personnel non commercial).

robots.txt interdit api.php et les URL avec paramètres (pagination…) : on ne lit QUE
des pages simples /w/<Titre>, à faible débit. Chaque donnée est attribuée « GTA Wiki ».
On n'extrait que la partie Grand Theft Auto VI des pages multi-jeux.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

BASE = "https://gta.wiki"
SOURCE_ID = "gtawiki"
VEHICLE_INDEX = f"{BASE}/w/Vehicles_in_GTA_VI"
WEAPON_INDEX = f"{BASE}/w/Weapons_in_GTA_VI"   # (les pages Category: sont interdites par robots.txt)
SKIP = re.compile(r"^(Category|File|Template|Special|Help|GTA_Wiki|Talk|User|Grand_Theft_Auto|GTA_VI|Vehicles_in|Weapons_in|"
                  r"Animals_in|Achievements|100%25|Airplanes|Bicycles|Boats|Helicopters|Motorcycles|Leonida|Vice_City|Rockstar)", re.I)
TEXT_SECTIONS = {"Description": "description_en", "Design": "design_en", "Performance": "performance_en",
                 "Locations": "location_text_en", "Modifications": "modifications_en", "Overview": "description_en",
                 "Acquisition": "how_to_unlock_en"}


def clean(s: str) -> str:
    s = re.sub(r"<sup.*?</sup>", "", s, flags=re.S)
    s = re.sub(r"\[\s*edit[^\]]*\]", "", re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


@dataclass
class WikiItem:
    title: str
    url: str
    kind: str                       # vehicle | weapon
    group: str | None = None        # groupe de la page liste (ex. « Sports & supercars »)
    fields: dict = field(default_factory=dict)
    texts: dict = field(default_factory=dict)
    variants: list[str] = field(default_factory=list)
    image: str | None = None


def vehicle_index(page: str) -> list[tuple[str, str, str]]:
    """(titre, url, groupe) depuis le tableau « Table » de Vehicles_in_GTA_VI."""
    out, seen = [], set()
    start = page.find('id="Table"')
    stop = page.find('id="Gallery"', start)
    sect = page[start:stop if stop > 0 else None]
    for tb in re.findall(r"<table.*?</table>", sect, re.S):
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tb, re.S)
        headers: list[str] = []
        for r in rows:
            cells = re.findall(r"<t([hd])[^>]*>(.*?)</t[hd]>", r, re.S)
            if cells and all(k == "h" for k, _ in cells):
                headers = [clean(c) for _, c in cells]
                continue
            for i, (_, c) in enumerate(cells):
                for href, title in re.findall(r'<a href="/w/([^"#?]+)"[^>]*title="([^"]+)"', c):
                    if SKIP.match(href) or href in seen:
                        continue
                    seen.add(href)
                    out.append((html.unescape(title), f"{BASE}/w/{href}", headers[i] if i < len(headers) else None))
    return out


def category_index(page: str) -> list[tuple[str, str, None]]:
    body = page[page.find('id="mw-pages"'):] if 'id="mw-pages"' in page else page
    out, seen = [], set()
    for href, title in re.findall(r'<a href="/w/([^"#?]+)"[^>]*title="([^"]+)"', body):
        if SKIP.match(href) or href in seen:
            continue
        seen.add(href)
        out.append((html.unescape(title), f"{BASE}/w/{href}", None))
    return out


def _gta6_part(section_html: str) -> str:
    """Dans une section multi-jeux, garde la sous-partie « Grand Theft Auto VI »."""
    parts = re.split(r'(<h[34][^>]*>.*?</h[34]>|<span class="h3-dummy">.*?</span>)', section_html, flags=re.S)
    if len(parts) == 1:
        return section_html
    keep, on = [], False
    for p in parts:
        if re.match(r'<h[34]|<span class="h3-dummy"', p):
            on = bool(re.search(r"Grand Theft Auto VI\b|\bGTA VI\b", clean(p)))
            continue
        if on:
            keep.append(p)
    return "".join(keep)


def parse_item(title: str, url: str, kind: str, page: str, group: str | None = None) -> WikiItem | None:
    if "Grand Theft Auto VI" not in page[:page.find("infobox-root") + 20000]:
        return None
    sub = re.search(r'<div class="infobox-subtitle">([^<]+)</div>', page)
    if not sub or not re.search({"vehicle": r"VEHICLE", "weapon": r"WEAPON|GEAR|EQUIPMENT|ITEM"}[kind], sub.group(1).upper()):
        return None                          # page fabricant, personnage, catégorie…
    it = WikiItem(title=title, url=url, kind=kind, group=group)
    multi = False
    for lab, val in re.findall(r'infobox-row-label">(.*?)</div>\s*<div class="infobox-row-value">(.*?)</div></div>', page, re.S):
        lab, raw = clean(lab), val
        v = clean(val)
        if lab == "Appears in":
            multi = bool(re.search(r"Grand Theft Auto (?:IV|V\b|III|San|Vice City(?! VI)|Liberty|Chinatown|Online)|GTA Online|Episodes", v))
        elif lab == "Manufacturer":
            it.fields["manufacturer"] = v
        elif lab == "Type":
            it.fields["type"] = v
        elif lab == "Body style":
            it.fields["body_style"] = _game_value(raw, v, multi)
        elif lab == "Capacity":
            m = re.search(r"\d+", _game_value(raw, v, multi) or "")
            if m:
                it.fields["seats"] = int(m.group(0))
        elif lab == "Variants":
            it.variants = [html.unescape(t) for t in re.findall(r'title="([^"]+)"', raw)] or [v]
        elif lab in ("Price",):
            gv = _game_value(raw, v, multi, strict=True)
            m = re.search(r"\$\s?([\d,]+)", gv or "")
            if m:
                it.fields["price"] = int(m.group(1).replace(",", ""))
    img = re.search(r'<div class="infobox-image">.*?<img src="([^"]+)"', page, re.S)
    if img:
        it.image = BASE + re.sub(r"/thumb(/.+?)/\d+px-[^/?]+", r"\1", img.group(1).split("?")[0])
    # sections de texte (partie GTA VI uniquement)
    heads = list(re.finditer(r'<h2[^>]*id="([^"]+)"[^>]*>', page))
    for i, h in enumerate(heads):
        sid = h.group(1).replace("_", " ")
        key = TEXT_SECTIONS.get(sid)
        if not key:
            continue
        end = heads[i + 1].start() if i + 1 < len(heads) else len(page)
        txt = clean(_gta6_part(page[h.end():end]) if multi else page[h.end():end])
        txt = re.sub(r"This article covers recently .*? as more details are documented\.\s*", "", txt)
        if txt and len(txt) > 20:
            it.texts[key] = txt[:2500]
    return it


def _game_value(raw: str, v: str, multi: bool, strict: bool = False) -> str | None:
    """Valeur pour GTA VI dans un champ multi-jeux (« … ( GTA VI ) »).
    Sans aucune mention de jeu, la valeur vaut pour tous les jeux, GTA VI compris."""
    if not multi:
        return v
    chunks = [clean(c) for c in re.split(r"<br\s*/?>|</li>", raw) if clean(c)]
    tagged = [c for c in chunks if re.search(r"\(\s*[^)]*(?:GTA|EFLC|Online)[^)]*\)", c)]
    for c in tagged:
        if re.search(r"\bGTA VI\b", c):
            return re.sub(r"\(\s*[^)]*\)", "", c).strip() or c
    return None if tagged else v


TYPE_CLASS = [(r"super", "Super"), (r"sports", "Sports"), (r"muscle", "Muscle"), (r"sedan|saloon|station wagon", "Sedans"),
              (r"suv", "SUVs"), (r"pickup|pick-up", "Pickups"), (r"off-road|buggy|monster", "Off-Road"), (r"compact|hatch", "Compacts"),
              (r"coup", "Coupes"), (r"motorcycle|bike|scooter|chopper", "Motorcycles"), (r"bicycle|bmx", "Cycles"),
              (r"boat|ship|jet ski|airboat|yacht|submarine", "Boats"), (r"helicopter", "Helicopters"), (r"plane|jet|aircraft", "Planes"),
              (r"van|bus", "Vans"), (r"truck|lorry|industrial|utility|tractor|excavator", "Commercial"),
              (r"emergency|police|ambulance|fire", "Emergency"), (r"train|tram", "Trains")]


def wiki_class(it: "WikiItem") -> str | None:
    src = f"{it.fields.get('type', '')} {it.group or ''}".lower()
    for rx, cls in TYPE_CLASS:
        if re.search(rx, src):
            return cls
    return None


MISSIONS_INDEX = f"{BASE}/w/Missions_in_GTA_VI"


def parse_missions(page: str) -> list[dict]:
    """Missions par chapitre (Prologue = 0) et donneur, depuis « Missions in GTA VI »."""
    out = []
    h2s = list(re.finditer(r'<h2 id="([^"]+)"[^>]*>(.*?)</h2>', page, re.S))
    for i, h in enumerate(h2s):
        sid, title = h.group(1), clean(h.group(2))
        if sid == "Prologue":
            chapter, kind = 0, "mission"
        elif sid.startswith("Chapter_"):
            m = re.match(r"Chapter_(\d+)", sid)
            chapter, kind = int(m.group(1)), "mission"
        elif sid == "Side_Missions":
            chapter, kind = None, "side_mission"
        else:
            continue
        chapter_title = title.split(":", 1)[1].strip() if ":" in title else title
        end = h2s[i + 1].start() if i + 1 < len(h2s) else len(page)
        sect = page[h.end():end]
        giver = None
        for tok in re.finditer(r'<h3 id="[^"]+"[^>]*>(.*?)</h3>|<tr>(.*?)</tr>', sect, re.S):
            if tok.group(1) is not None:
                giver = clean(tok.group(1))
                continue
            cells = re.findall(r"<td[^>]*>(.*?)</td>", tok.group(2), re.S)
            if len(cells) < 2:
                continue
            link = re.search(r'<a href="/w/([^"#?]+)"[^>]*title="([^"]+)"', cells[1])
            if not link:
                continue
            img = re.search(r'<img[^>]+src="([^"]+)"', cells[0])
            out.append({
                "kind": kind, "chapter": chapter, "chapter_title": chapter_title, "giver": giver,
                "title": html.unescape(link.group(2)), "url": f"{BASE}/w/{link.group(1)}",
                "description": clean(cells[2]) if len(cells) > 2 else None,
                "image": BASE + re.sub(r"/thumb(/.+?)/\d+px-[^/?]+", r"\1", img.group(1).split("?")[0]) if img else None,
            })
    return out
