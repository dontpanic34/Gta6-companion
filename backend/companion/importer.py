"""Import des éléments parsés dans la base, avec historique.

- Identifiants stables : 'vehicle:<slug-modèle>' et 'vehicle:<slug-modèle>:<slug-variante>'.
- Une valeur qui change ne remplace pas l'ancienne : l'ancienne passe 'obsolete',
  une révision est journalisée, rien n'est supprimé.
- Une source indisponible n'efface jamais rien (l'import est additif).
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from . import classify
from .connectors.gtabase import STAT_SCALE_10, ParsedItem

SOURCES = [
    ("gtabase", "GTABase", "https://www.gtabase.com", "full_sync", 70),
    ("gta6map", "GTA6Map.city", "https://gta6map.city", "full_sync", 70),
    ("gtacity", "GTACity", "https://gtacity.gg", "on_demand", 70),
    ("gtadb_landmarks", "GTA VI Landmarks (CC BY 4.0)", "https://map.gtadb.org", "full_sync", 75),
    ("manual", "Saisie personnelle", None, "full_sync", 90),
]


@dataclass
class ImportReport:
    created: list[str] = field(default_factory=list)
    changed: list[tuple[str, str]] = field(default_factory=list)
    quarantined: list[tuple[str, str]] = field(default_factory=list)


def ensure_sources(conn: sqlite3.Connection) -> None:
    conn.executemany("INSERT OR IGNORE INTO source(id,name,base_url,policy,reliability) VALUES (?,?,?,?,?)", SOURCES)


def _upsert_entity(conn, eid: str, kind: str, name: str, report: ImportReport) -> None:
    row = conn.execute("SELECT canonical_name FROM entity WHERE id = ?", (eid,)).fetchone()
    if row is None:
        status = classify.entity_spoiler_status(kind, name)
        conn.execute("INSERT INTO entity(id,kind,canonical_name,spoiler_status) VALUES (?,?,?,?)",
                     (eid, kind, name, status))
        conn.execute("INSERT INTO revision(table_name,row_key,after_json,origin) VALUES ('entity',?,?,?)",
                     (eid, json.dumps({"name": name, "kind": kind}), "import"))
        report.created.append(eid)
        if status == "unknown":
            report.quarantined.append((eid, "name"))


def _record_claim(conn, eid: str, fname: str, value, source_id: str, url: str, report: ImportReport) -> None:
    vjson = json.dumps(value, ensure_ascii=False)
    cur = conn.execute(
        "SELECT id, value_json FROM claim WHERE entity_id=? AND field=? AND source_id=? AND status <> 'obsolete'",
        (eid, fname, source_id)).fetchone()
    if cur and cur["value_json"] == vjson:
        return
    status_sp = classify.field_spoiler_status(fname, value)
    if cur:
        conn.execute("UPDATE claim SET status='obsolete' WHERE id=?", (cur["id"],))
        conn.execute("INSERT INTO revision(table_name,row_key,before_json,after_json,origin) "
                     "VALUES ('claim',?,?,?,?)", (f"{eid}#{fname}", cur["value_json"], vjson, f"sync:{source_id}"))
        report.changed.append((eid, fname))
    # Un champ statistique /10 provient d'une notation communautaire du site, pas du jeu.
    value_kind = "community" if fname in STAT_SCALE_10 else "official"
    conn.execute(
        "INSERT INTO claim(entity_id,field,value_json,value_kind,source_id,source_url,status,spoiler_status) "
        "VALUES (?,?,?,?,?,?,?,?)", (eid, fname, vjson, value_kind, source_id, url, "probable", status_sp))
    if status_sp == "unknown":
        report.quarantined.append((eid, fname))


def import_items(conn: sqlite3.Connection, items: list[ParsedItem], source_id: str = "gtabase") -> ImportReport:
    report = ImportReport()
    ensure_sources(conn)
    by_slug = {i.slug: i for i in items}
    with conn:
        for it in items:
            prefix = it.kind  # 'vehicle' | 'weapon'
            base = by_slug.get(it.base_model_slug) if it.base_model_slug else None
            model_slug = it.base_model_slug or it.slug
            model_id = f"{prefix}:{model_slug}"
            model_name = (base.name if base else it.fields.get("base_model")) if it.base_model_slug else it.name

            _upsert_entity(conn, model_id, f"{prefix}_model", model_name, report)
            conn.execute(f"INSERT OR IGNORE INTO {prefix}_model(entity_id, manufacturer, class) VALUES (?,?,?)",
                         (model_id, it.fields.get("manufacturer"), it.fields.get("class")))

            variant_id = f"{model_id}:{'std' if not it.base_model_slug else it.slug}"
            vtype = "standard" if not it.base_model_slug else "named"
            _upsert_entity(conn, variant_id, f"{prefix}_variant", it.name, report)
            conn.execute(f"INSERT OR IGNORE INTO {prefix}_variant(entity_id, model_id, variant_type) VALUES (?,?,?)",
                         (variant_id, model_id, vtype))

            for fname, value in it.fields.items():
                if fname == "base_model":
                    continue
                _record_claim(conn, variant_id, fname, value, source_id, it.url, report)

            name_status = conn.execute("SELECT spoiler_status FROM entity WHERE id=?", (variant_id,)).fetchone()[0]
            for img in it.images:
                if not conn.execute("SELECT 1 FROM media WHERE entity_id=? AND url=?", (variant_id, img)).fetchone():
                    conn.execute("INSERT INTO media(entity_id,url,source_id,spoiler_status) VALUES (?,?,?,?)",
                                 (variant_id, img, source_id, name_status))
    return report
