"""Index des noms de lieux (quartiers, zones, îles) -> position, pour comprendre
« je suis à Port Gellhorn » ou « je viens d'arriver à Key Lento ».

Sources : repères gtadb.org (CC BY 4.0, « Bâtiment, Quartier, Zone » + coordonnées)
et régions/secteurs des lieux importés.
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


@dataclass
class Zone:
    name: str
    x: float
    y: float
    radius: float      # rayon approximatif (m) déduit de la dispersion des points
    n: int
    level: str         # 'area' | 'district' | 'region'


def build(conn: sqlite3.Connection, landmarks_path: str | Path | None) -> dict[str, Zone]:
    pts: dict[tuple[str, str], list[tuple[float, float]]] = {}
    if landmarks_path and Path(landmarks_path).exists():
        data = json.loads(Path(landmarks_path).read_text(encoding="utf-8"))
        for v in data.values():
            name, coords = v[0], v[1]
            parts = [p.strip() for p in name.split(",")]
            if len(parts) >= 2 and coords:
                pts.setdefault((parts[-1], "area"), []).append(tuple(coords))
                if len(parts) >= 3:
                    pts.setdefault((parts[-2], "district"), []).append(tuple(coords))
    for r in conn.execute("""SELECT e.region_label, p.x, p.y FROM entity e
                             JOIN location_point p ON p.entity_id = e.id WHERE e.region_label IS NOT NULL"""):
        pts.setdefault((r[0], "region"), []).append((r[1], r[2]))
    for r in conn.execute("""SELECT json_extract(c.value_json, '$'), p.x, p.y FROM claim c
                             JOIN location_point p ON p.entity_id = c.entity_id
                             WHERE c.field = 'subarea' AND c.status <> 'obsolete'"""):
        if r[0]:
            pts.setdefault((r[0], "district"), []).append((r[1], r[2]))

    zones: dict[str, Zone] = {}
    for (name, level), ps in pts.items():
        if name in ("?", "") or len(ps) < 1:
            continue
        xs, ys = [p[0] for p in ps], [p[1] for p in ps]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        spread = max((((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 for x, y in ps), default=0)
        z = Zone(name, cx, cy, max(400.0, min(spread, 6000.0)), len(ps), level)
        key = norm(name)
        if key not in zones or zones[key].n < z.n:
            zones[key] = z
    return zones


def find(zones: dict[str, Zone], text: str) -> Zone | None:
    """Trouve la zone la plus spécifique citée dans un texte libre."""
    t = f" {norm(text)} "
    hits = [z for k, z in zones.items() if len(k) >= 3 and f" {k} " in t]
    if not hits:
        return None
    # le nom le plus long (le plus précis) l'emporte
    return max(hits, key=lambda z: (len(norm(z.name)), z.n))
