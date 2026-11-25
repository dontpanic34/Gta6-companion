"""Import des éléments parsés dans la base, avec historique.

- Identifiants stables : 'vehicle:<slug-modèle>' et 'vehicle:<slug-modèle>:<slug-variante>'.
- Une valeur qui change ne remplace pas l'ancienne : l'ancienne passe 'obsolete',
  une révision est journalisée, rien n'est supprimé.
- Une source indisponible n'efface jamais rien (l'import est additif).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
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


def _upsert_entity(conn, eid: str, kind: str, name: str, report: ImportReport,
                   alias: str | None = None) -> None:
    row = conn.execute("SELECT canonical_name FROM entity WHERE id = ?", (eid,)).fetchone()
    if row is None:
        status = classify.entity_spoiler_status(kind, name)
        nstatus = classify.name_status(kind, name)
        conn.execute("INSERT INTO entity(id,kind,canonical_name,neutral_alias,spoiler_status,name_status) "
                     "VALUES (?,?,?,?,?,?)", (eid, kind, name, alias, status, nstatus))
        conn.execute("INSERT INTO revision(table_name,row_key,after_json,origin) VALUES ('entity',?,?,?)",
                     (eid, json.dumps({"name": name, "kind": kind}), "import"))
        report.created.append(eid)
        if status == "unknown" or nstatus == "unknown":
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
            if not model_name:  # modèle hors lot : nom existant en base, sinon déduit du slug
                ex = conn.execute("SELECT canonical_name FROM entity WHERE id=?", (model_id,)).fetchone()
                brand = it.fields.get("manufacturer")
                model_name = ex[0] if ex else " ".join(filter(None, [brand, model_slug.replace("-", " ").title()]))

            _upsert_entity(conn, model_id, f"{prefix}_model", model_name, report)
            conn.execute(f"INSERT OR IGNORE INTO {prefix}_model(entity_id, manufacturer, class) VALUES (?,?,?)",
                         (model_id, it.fields.get("manufacturer"), it.fields.get("class")))

            variant_id = f"{model_id}:{'std' if not it.base_model_slug else it.slug}"
            vtype = "standard" if not it.base_model_slug else "named"
            label = "Véhicule" if prefix == "vehicle" else "Arme"
            alias = f"{label} unique — {model_name}" if it.base_model_slug else None
            _upsert_entity(conn, variant_id, f"{prefix}_variant", it.name, report, alias)
            conn.execute(f"INSERT OR IGNORE INTO {prefix}_variant(entity_id, model_id, variant_type) VALUES (?,?,?)",
                         (variant_id, model_id, vtype))

            for fname, value in it.fields.items():
                if fname == "base_model":
                    continue
                _record_claim(conn, variant_id, fname, value, source_id, it.url, report)

            # Une photo peut montrer un véhicule de personnage : même statut que le nom.
            name_status = "evaluated" if conn.execute(
                "SELECT name_status FROM entity WHERE id=?", (variant_id,)).fetchone()[0] == "safe" else "unknown"
            for img in it.images:
                if not conn.execute("SELECT 1 FROM media WHERE entity_id=? AND url=?", (variant_id, img)).fetchone():
                    conn.execute("INSERT INTO media(entity_id,url,source_id,spoiler_status) VALUES (?,?,?,?)",
                                 (variant_id, img, source_id, name_status))
    return report


def _slugify(s: str) -> str:
    import re
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def import_map_locations(conn: sqlite3.Connection, locs: list, source_id: str = "gta6map") -> ImportReport:
    """Marqueurs issus de la carte du jeu : publics par nature (visibles en jeu)."""
    report = ImportReport()
    ensure_sources(conn)
    with conn:
        for loc in locs:
            eid = f"location:{_slugify(loc.marker_id)}"
            if not conn.execute("SELECT 1 FROM entity WHERE id=?", (eid,)).fetchone():
                conn.execute(
                    "INSERT INTO entity(id,kind,canonical_name,spoiler_status,name_status,category,region_label,reliability) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (eid, "location", loc.name, "evaluated", "safe", loc.category_name,
                     loc.region, "probable"))
                report.created.append(eid)
            if loc.x is not None and not conn.execute("SELECT 1 FROM location_point WHERE entity_id=?", (eid,)).fetchone():
                conn.execute("INSERT INTO location_point(entity_id,x,y,precision) VALUES (?,?,?,?)",
                             (eid, loc.x, loc.y, "exact"))
            for fname, val in (("subarea", loc.subarea), ("description", loc.description)):
                if val:
                    # texte factuel de carte (« à 106 m de … ») : sûr s'il n'a pas d'indice narratif
                    st = classify.secret_text_status(val)
                    _record_claim_raw(conn, eid, fname, val, source_id, loc.url, st, report)
    return report


def _record_claim_raw(conn, eid, fname, value, source_id, url, spoiler_status, report, status="probable"):
    vjson = json.dumps(value, ensure_ascii=False)
    cur = conn.execute("SELECT id, value_json FROM claim WHERE entity_id=? AND field=? AND source_id=? "
                       "AND status <> 'obsolete'", (eid, fname, source_id)).fetchone()
    if cur and cur["value_json"] == vjson:
        return
    if cur:
        conn.execute("UPDATE claim SET status='obsolete' WHERE id=?", (cur["id"],))
        conn.execute("INSERT INTO revision(table_name,row_key,before_json,after_json,origin) VALUES ('claim',?,?,?,?)",
                     (f"{eid}#{fname}", cur["value_json"], vjson, f"sync:{source_id}"))
        report.changed.append((eid, fname))
    conn.execute("INSERT INTO claim(entity_id,field,value_json,value_kind,source_id,source_url,status,spoiler_status) "
                 "VALUES (?,?,?,?,?,?,?,?)", (eid, fname, vjson, "community", source_id, url, status, spoiler_status))
    if spoiler_status == "unknown":
        report.quarantined.append((eid, fname))


def import_secrets(conn: sqlite3.Connection, secrets: list, source_id: str = "gta6map") -> ImportReport:
    """Secrets communautaires : titre masqué (alias neutre), « où » = niveau 1,
    « de quoi s'agit-il » = niveau 2 (indice à la demande). Doute => quarantaine."""
    from .connectors.gta6map import CATEGORY_KIND
    report = ImportReport()
    ensure_sources(conn)
    with conn:
        for s in secrets:
            eid = f"secret:{s.slug}"
            kind = CATEGORY_KIND.get(s.category or "", "easter_egg")
            alias = f"{s.category or 'Secret'} — {s.region or 'Leonida'}"
            where_st = classify.secret_text_status(s.where)
            ent_status = "evaluated" if where_st == "evaluated" else "unknown"
            row = conn.execute("SELECT 1 FROM entity WHERE id=?", (eid,)).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO entity(id,kind,canonical_name,neutral_alias,spoiler_status,name_status,category,region_label,reliability) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (eid, kind, s.title, alias, ent_status, "unknown", s.category, s.region, s.reliability))
                report.created.append(eid)
                if ent_status == "unknown":
                    report.quarantined.append((eid, "entity"))
                if s.where:
                    conn.execute("INSERT INTO activity_content(entity_id,level,ord,body,spoiler_status) VALUES (?,?,?,?,?)",
                                 (eid, 1, 0, s.where, where_st))
                if s.what:
                    conn.execute("INSERT INTO activity_content(entity_id,level,ord,body,spoiler_status) VALUES (?,?,?,?,?)",
                                 (eid, 2, 0, s.what, classify.secret_text_status(s.what)))
                if s.image:
                    conn.execute("INSERT INTO media(entity_id,url,source_id,spoiler_status) VALUES (?,?,?,?)",
                                 (eid, s.image, source_id, "unknown"))  # miniature : peut montrer le secret
            else:
                conn.execute("UPDATE entity SET reliability=?, region_label=COALESCE(?,region_label) WHERE id=?",
                             (s.reliability, s.region, eid))
            _record_claim_raw(conn, eid, "source_page", s.url, source_id, s.url, "evaluated", report)
            _record_claim_raw(conn, eid, "precision", s.precision, source_id, s.url, "evaluated", report)
            if s.creators:
                _record_claim_raw(conn, eid, "creators_count", s.creators, source_id, s.url, "evaluated", report)
    return report


def reclassify_catalog_names(conn: sqlite3.Connection) -> int:
    """Réapplique les règles de nom aux fiches catalogue (après évolution des règles).
    Ne rend jamais visible un nom marqué manuellement : seules les règles auto s'appliquent."""
    n = 0
    with conn:
        for r in conn.execute("SELECT id, kind, canonical_name FROM entity WHERE kind IN "
                              "('vehicle_model','vehicle_variant','weapon_model','weapon_variant')").fetchall():
            conn.execute("UPDATE entity SET spoiler_status=? WHERE id=?",
                         (classify.entity_spoiler_status(r["kind"], r["canonical_name"]), r["id"]))
            st = classify.name_status(r["kind"], r["canonical_name"])
            n += conn.execute("UPDATE entity SET name_status=? WHERE id=? AND name_status<>?",
                              (st, r["id"], st)).rowcount
            if st == "unknown" and r["kind"].endswith("_variant"):
                prefix = r["kind"].split("_")[0]
                model = conn.execute(f"SELECT e.canonical_name FROM {prefix}_variant v JOIN entity e "
                                     f"ON e.id = v.model_id WHERE v.entity_id=?", (r["id"],)).fetchone()
                label = "Véhicule" if prefix == "vehicle" else "Arme"
                conn.execute("UPDATE entity SET neutral_alias=? WHERE id=? AND neutral_alias IS NULL",
                             (f"{label} unique — {model[0] if model else '?'}", r["id"]))
            media_st = "evaluated" if st == "safe" else "unknown"
            conn.execute("UPDATE media SET spoiler_status=? WHERE entity_id=?", (media_st, r["id"]))
    return n


def geocode_unplaced(conn: sqlite3.Connection, zones: dict) -> int:
    """Place approximativement les lieux/secrets sans coordonnées, d'après les noms
    de lieux cités (texte « où le trouver », secteur, région). Précision = 'zone'."""
    from . import gazetteer
    placed = 0
    rows = conn.execute("""
        SELECT e.id, e.region_label,
               (SELECT group_concat(body, ' ') FROM activity_content a WHERE a.entity_id = e.id AND a.level = 1) AS where_txt,
               (SELECT json_extract(value_json,'$') FROM claim c WHERE c.entity_id = e.id AND c.field='subarea'
                  AND c.status <> 'obsolete' LIMIT 1) AS subarea
        FROM entity e LEFT JOIN location_point p ON p.entity_id = e.id
        WHERE p.entity_id IS NULL AND e.kind IN ('location','secret_quest','random_encounter','dynamic_event',
              'easter_egg','mystery','activity','collectible','property')""").fetchall()
    with conn:
        for r in rows:
            z = None
            for txt, prec in ((r["where_txt"], "zone"), (r["subarea"], "nearby"), (r["region_label"], "zone")):
                if txt:
                    z = gazetteer.find(zones, txt)
                    if z:
                        break
            if z:
                conn.execute("INSERT INTO location_point(entity_id,x,y,precision) VALUES (?,?,?,?)",
                             (r["id"], z.x, z.y, prec if z.level != "region" else "zone"))
                placed += 1
    return placed


def resolve_on_demand(conn: sqlite3.Connection, name: str, client=None) -> str | None:
    """Fiche véhicule absente du catalogue : lit UNE page GTACity (à la demande, cache 30 j)
    et l'importe. Retourne l'id de la variante ou None."""
    from .connectors import gtacity
    from .http import PoliteClient
    client = client or PoliteClient(Path(conn.execute("PRAGMA database_list").fetchone()[2]).parent / "http-cache", min_interval=2)
    try:
        idx = gtacity.vehicle_index(client.get(gtacity.SITEMAP, max_age=24 * 3600).text)
        url = gtacity.find_url(idx, name)
        if not url:
            return None
        item = gtacity.parse_vehicle(url, client.get(url, max_age=30 * 24 * 3600).text)
    except Exception:
        return None
    if not item:
        return None
    # pas de doublon de modèle : on rattache au modèle GTABase existant s'il a le même slug
    import_items(conn, [item], "gtacity")
    vid = f"vehicle:{item.base_model_slug or item.slug}:{'std' if not item.base_model_slug else item.slug}"
    reclassify_catalog_names(conn)
    return vid
