"""Import des éléments parsés dans la base, avec historique.

- Identifiants stables : 'vehicle:<slug-modèle>' et 'vehicle:<slug-modèle>:<slug-variante>'.
- Une valeur qui change ne remplace pas l'ancienne : l'ancienne passe 'obsolete',
  une révision est journalisée, rien n'est supprimé.
- Une source indisponible n'efface jamais rien (l'import est additif).
"""
from __future__ import annotations

import json
import re
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
    ("gtawiki", "GTA Wiki (CC BY-NC-SA 3.0)", "https://gta.wiki", "full_sync", 65),
    ("gtatown", "GTA Town (CC BY 4.0)", "https://gtatown.com", "full_sync", 80),
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
            desc = " · ".join(str(x) for x in (it.fields.get("class"), it.fields.get("manufacturer")) if x)
            alias = f"{label} unique" + (f" — {desc}" if desc else "")
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
                    (eid, "location", loc.name, classify.category_status(loc.category_name),
                     "safe" if classify.category_status(loc.category_name) == "evaluated" else "unknown",
                     loc.category_name, loc.region, "probable"))
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
            ent_status = "evaluated" if where_st == "evaluated" and classify.category_status(s.category) == "evaluated" else "unknown"
            row = conn.execute("SELECT 1 FROM entity WHERE id=?", (eid,)).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO entity(id,kind,canonical_name,neutral_alias,spoiler_status,name_status,category,region_label,reliability) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (eid, kind, s.title, alias, ent_status, "unknown", s.category, s.region, s.reliability))
                report.created.append(eid)
                if ent_status == "unknown":
                    report.quarantined.append((eid, "entity"))
                if s.image:
                    conn.execute("INSERT INTO media(entity_id,url,source_id,spoiler_status) VALUES (?,?,?,?)",
                                 (eid, s.image, source_id, "unknown"))  # miniature : peut montrer le secret
            else:
                conn.execute("UPDATE entity SET reliability=?, region_label=COALESCE(?,region_label) WHERE id=?",
                             (s.reliability, s.region, eid))
            # Contenus par niveau : 1 = où + prérequis, 2 = de quoi s'agit-il, 3 = comment faire
            import re as _re
            hint_sentences = [x.strip() for x in _re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý])", s.what or "") if x.strip()]
            sections = [(1, 0, s.where), (1, 1, s.needs), (3, 0, s.how)] + [(2, i, h) for i, h in enumerate(hint_sentences)]
            # anciens indices en trop (texte raccourci à la source) : supprimés
            conn.execute("DELETE FROM activity_content WHERE entity_id=? AND level=2 AND ord>=?", (eid, len(hint_sentences)))
            for level, ord_, body in sections:
                if not body:
                    continue
                cur = conn.execute("SELECT id, body FROM activity_content WHERE entity_id=? AND level=? AND ord=?",
                                   (eid, level, ord_)).fetchone()
                st = classify.secret_text_status(body) if level < 3 else "evaluated"  # niveau 3 : affiché sur confirmation
                if cur is None:
                    conn.execute("INSERT INTO activity_content(entity_id,level,ord,body,spoiler_status) VALUES (?,?,?,?,?)",
                                 (eid, level, ord_, body, st))
                elif cur["body"] != body:
                    conn.execute("INSERT INTO revision(table_name,row_key,before_json,after_json,origin) VALUES ('activity_content',?,?,?,?)",
                                 (f"{eid}#{level}.{ord_}", json.dumps(cur["body"]), json.dumps(body), f"sync:{source_id}"))
                    conn.execute("UPDATE activity_content SET body=?, spoiler_status=? WHERE id=?", (body, st, cur["id"]))
            if s.video_ref:
                _record_claim_raw(conn, eid, "video", s.video_ref, source_id, s.url, "evaluated", report)
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
            if st == "unknown":
                prefix = r["kind"].split("_")[0]
                fields = {row[0]: json.loads(row[1]) for row in conn.execute(
                    "SELECT field, value_json FROM claim WHERE entity_id=? AND field IN ('manufacturer','class') "
                    "AND status <> 'obsolete'", (r["id"],))}
                label = "Véhicule" if prefix == "vehicle" else "Arme"
                desc = " · ".join(str(x) for x in (fields.get("class"), fields.get("manufacturer")) if x)
                # alias neutre : jamais dérivé du nom (qui peut contenir un personnage)
                conn.execute("UPDATE entity SET neutral_alias=? WHERE id=?", (f"{label} unique" + (f" — {desc}" if desc else ""), r["id"]))
            media_st = "evaluated" if st == "safe" else "unknown"
            conn.execute("UPDATE media SET spoiler_status=? WHERE entity_id=?", (media_st, r["id"]))
    return n


def geocode_unplaced(conn: sqlite3.Connection, zones: dict) -> int:
    """Place approximativement les lieux/secrets sans coordonnées, d'après les noms
    de lieux cités (texte « où le trouver », secteur, région). Précision = 'zone'."""
    from . import gazetteer
    placed = 0
    used: dict[str, int] = {}
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
                # plusieurs éléments sur la même zone : spirale « tournesol » pour ne pas les empiler
                import math
                k = used.get(z.name, 0); used[z.name] = k + 1
                rad = min(z.radius * 0.35, 700) * math.sqrt(k / (k + 6)) if k else 0
                ang = k * 2.39996
                conn.execute("INSERT INTO location_point(entity_id,x,y,precision) VALUES (?,?,?,?)",
                             (r["id"], z.x + rad * math.cos(ang), z.y + rad * math.sin(ang), prec if z.level != "region" else "zone"))
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


def requarantine_sensitive(conn: sqlite3.Connection) -> int:
    """Applique a posteriori la règle des catégories sensibles (jamais l'inverse)."""
    n = 0
    with conn:
        for (eid, cat) in conn.execute("SELECT id, category FROM entity WHERE category IS NOT NULL").fetchall():
            if classify.category_status(cat) == "unknown":
                n += conn.execute("UPDATE entity SET spoiler_status='unknown', name_status='unknown' "
                                  "WHERE id=? AND spoiler_status='evaluated'", (eid,)).rowcount
    return n


def import_wiki_items(conn: sqlite3.Connection, items: list) -> ImportReport:
    """Rattache chaque fiche GTA Wiki à la fiche catalogue existante (même marque + nom),
    sinon crée la fiche. Les textes (anglais) passent par la classification anti-spoiler."""
    from .connectors.gtawiki import SOURCE_ID, wiki_class
    from .assistant import best_match
    report = ImportReport()
    ensure_sources(conn)
    for it in items:
        prefix = it.kind
        cands = [{"id": r[0], "name": r[1]} for r in conn.execute(
            f"SELECT id, canonical_name FROM entity WHERE kind = '{prefix}_variant'")]
        full = " ".join(x for x in (it.fields.get("manufacturer"), it.title) if x)
        m = best_match(full, cands, strict=True) or best_match(it.title, cands, strict=True)
        with conn:
            if m:
                vid = m["id"]
            else:
                pi = ParsedItem(slug=_slugify(it.title), url=it.url, kind=prefix, name=full,
                                fields={"manufacturer": it.fields.get("manufacturer"), "class": wiki_class(it)},
                                images=[it.image] if it.image else [])
                pi.fields = {k: v for k, v in pi.fields.items() if v}
                r = import_items(conn, [pi], SOURCE_ID)
                report.created += r.created
                vid = f"{prefix}:{pi.slug}:std"
            for fname in ("manufacturer", "seats", "price", "body_style"):
                if it.fields.get(fname) is not None:
                    _record_claim(conn, vid, fname, it.fields[fname], SOURCE_ID, it.url, report)
            cls = wiki_class(it)
            if cls:
                _record_claim(conn, vid, "class", cls, SOURCE_ID, it.url, report)
            if it.variants:
                _record_claim_raw(conn, vid, "variants_list", it.variants, SOURCE_ID, it.url, "evaluated", report)
            for fname, txt in it.texts.items():
                st = classify.descriptive_status(txt) if fname in classify.DESCRIPTIVE_TEXT \
                    else classify.field_spoiler_status("description", txt)
                _record_claim_raw(conn, vid, fname, txt, SOURCE_ID, it.url, st, report)
            if it.image and not conn.execute("SELECT 1 FROM media WHERE entity_id=? AND url=?", (vid, it.image)).fetchone():
                ns = conn.execute("SELECT name_status FROM entity WHERE id=?", (vid,)).fetchone()
                conn.execute("INSERT INTO media(entity_id,url,source_id,spoiler_status) VALUES (?,?,?,?)",
                             (vid, it.image, SOURCE_ID, "evaluated" if ns and ns[0] == "safe" else "unknown"))
    reclassify_catalog_names(conn)
    return report


def import_missions(conn: sqlite3.Connection, missions: list[dict], source_id: str = "gtawiki") -> ImportReport:
    """Missions principales : visibles seulement à partir de leur chapitre (porte de progression).
    Le donneur (personnage) suit la même porte. La description (mise en place de l'histoire)
    est rangée en niveau 3 : affichée uniquement sur confirmation explicite."""
    report = ImportReport()
    ensure_sources(conn)
    with conn:
        side_n = 0
        for m in missions:
            if m["chapter"] is not None:
                conn.execute("INSERT INTO chapter(num,title) VALUES (?,?) ON CONFLICT(num) DO UPDATE SET title=excluded.title",
                             (m["chapter"], m["chapter_title"]))
            eid = f"mission:{_slugify(m['title'])}"
            is_side = m["kind"] == "side_mission"
            side_n += is_side
            alias = f"Mission secondaire n°{side_n}" if is_side else f"Mission du chapitre {m['chapter']}"
            if not conn.execute("SELECT 1 FROM entity WHERE id=?", (eid,)).fetchone():
                conn.execute("INSERT INTO entity(id,kind,canonical_name,neutral_alias,spoiler_status,name_status,category,reliability) "
                             "VALUES (?,?,?,?,?,?,?,?)",
                             (eid, m["kind"], m["title"], alias, "evaluated", "unknown" if is_side else "safe",
                              "Missions secondaires" if is_side else (f"Prologue" if m["chapter"] == 0 else f"Chapitre {m['chapter']}"),
                              "probable"))
                report.created.append(eid)
                if m["chapter"]:
                    conn.execute("INSERT INTO spoiler_gate(entity_id,field,kind,chapter) VALUES (?,?,?,?)",
                                 (eid, None, "chapter", m["chapter"]))
            if m.get("giver"):
                cid = f"character:{_slugify(m['giver'])}"
                if not conn.execute("SELECT 1 FROM entity WHERE id=?", (cid,)).fetchone():
                    conn.execute("INSERT INTO entity(id,kind,canonical_name,neutral_alias,spoiler_status,name_status,reliability) "
                                 "VALUES (?,?,?,?,?,?,?)", (cid, "character", m["giver"], "Personnage", "evaluated", "safe", "probable"))
                    if m["chapter"]:
                        conn.execute("INSERT INTO spoiler_gate(entity_id,field,kind,chapter) VALUES (?,?,?,?)",
                                     (cid, None, "chapter", m["chapter"]))
                    elif is_side:  # donneur de mission secondaire : nom masqué jusqu'à révélation
                        conn.execute("UPDATE entity SET name_status='unknown' WHERE id=?", (cid,))
                _record_claim_raw(conn, eid, "giver", m["giver"], source_id, m["url"], "evaluated" if not is_side else "unknown", report)
            if m["chapter"] is not None:
                _record_claim_raw(conn, eid, "chapter", m["chapter"], source_id, m["url"], "evaluated", report)
            _record_claim_raw(conn, eid, "source_page", m["url"], source_id, m["url"], "evaluated", report)
            if m.get("description"):
                cur = conn.execute("SELECT id FROM activity_content WHERE entity_id=? AND level=3 AND ord=0", (eid,)).fetchone()
                if cur:
                    conn.execute("UPDATE activity_content SET body=? WHERE id=?", (m["description"].strip("“” "), cur["id"]))
                else:
                    conn.execute("INSERT INTO activity_content(entity_id,level,ord,body,spoiler_status) VALUES (?,?,?,?,?)",
                                 (eid, 3, 0, m["description"].strip("“” "), "evaluated"))
            if m.get("image") and not conn.execute("SELECT 1 FROM media WHERE entity_id=?", (eid,)).fetchone():
                conn.execute("INSERT INTO media(entity_id,url,source_id,spoiler_status) VALUES (?,?,?,?)",
                             (eid, m["image"], source_id, "unknown"))   # miniature : peut montrer une scène
    return report


def enrich_vehicle_on_demand(conn: sqlite3.Connection, vid: str, name: str, client=None) -> bool:
    """Fiche ouverte sans stats : lit UNE page GTACity (cache 30 j) et rattache stats,
    transmission, places et photo à CETTE fiche (aucun doublon)."""
    from .connectors import gtacity
    from .http import PoliteClient
    client = client or PoliteClient(Path(conn.execute("PRAGMA database_list").fetchone()[2]).parent / "http-cache", min_interval=2)
    try:
        idx = gtacity.vehicle_index(client.get(gtacity.SITEMAP, max_age=24 * 3600).text)
        url = gtacity.find_url(idx, name)
        item = gtacity.parse_vehicle(url, client.get(url, max_age=30 * 24 * 3600).text) if url else None
    except Exception:
        return False
    if not item:
        return False
    report = ImportReport()
    with conn:
        for f, v in item.fields.items():
            if f in ("class",):
                continue
            _record_claim(conn, vid, f, v, "gtacity", url, report)
        for img in item.images:
            if not conn.execute("SELECT 1 FROM media WHERE entity_id=? AND url=?", (vid, img)).fetchone():
                ns = conn.execute("SELECT name_status FROM entity WHERE id=?", (vid,)).fetchone()
                conn.execute("INSERT INTO media(entity_id,url,source_id,spoiler_status) VALUES (?,?,?,?)",
                             (vid, img, "gtacity", "evaluated" if ns and ns[0] == "safe" else "unknown"))
    return True


PROTAGONISTS = {"Jason Duval", "Lucia Caminos", "Jason", "Lucia"}
GENERIC_GIVERS = re.compile(r"^(Strangers|Random|Various|Unknown|Multiple|Phone|Prologue)\b", re.I) if True else None


def reset_text_statuses(conn: sqlite3.Connection) -> None:
    """Recalcule les statuts « automatiques » des textes (avant protect_story_names), pour réparer
    un passage trop strict. Ne touche pas aux textes de niveau 3 ni aux contenus marqués à la main."""
    with conn:
        for cid, f, v, src in conn.execute("SELECT id, field, value_json, source_id FROM claim").fetchall():
            try:
                val = json.loads(v)
            except ValueError:
                continue
            if src == "gtawiki" and f in classify.DESCRIPTIVE_TEXT and isinstance(val, str):
                st = classify.descriptive_status(val)
            elif src == "gta6map" and f in ("description", "subarea") and isinstance(val, str):
                st = classify.secret_text_status(val)
            elif f == "source_page":
                st = "evaluated"
            else:
                continue
            conn.execute("UPDATE claim SET spoiler_status=? WHERE id=?", (st, cid))
        for aid, body in conn.execute("SELECT id, body FROM activity_content WHERE level < 3").fetchall():
            conn.execute("UPDATE activity_content SET spoiler_status=? WHERE id=?", (classify.secret_text_status(body), aid))


def protect_story_names(conn: sqlite3.Connection) -> int:
    """Tout texte affichable qui cite un personnage / une mission / un chapitre encore protégé
    (porte de chapitre, nom masqué) passe en 'unknown'. Les deux héros, connus dès le départ, sont publics."""
    import re as _re
    with conn:
        for name in ("Jason Duval", "Lucia Caminos"):
            eid = f"character:{_slugify(name)}"
            conn.execute("DELETE FROM spoiler_gate WHERE entity_id=?", (eid,))
    names = set()
    for (n,) in conn.execute("SELECT title FROM chapter WHERE num > 0"):
        names.add(n)
    for (n, kind) in conn.execute("""SELECT DISTINCT e.canonical_name, e.kind FROM entity e WHERE e.kind IN ('character','mission','side_mission')
                                AND (e.name_status <> 'safe' OR EXISTS (SELECT 1 FROM spoiler_gate g WHERE g.entity_id = e.id))"""):
        if GENERIC_GIVERS.search(n):
            continue
        names.add(n)
        # prénom seul (« Raul »), pour les PERSONNAGES uniquement (un titre de mission n'a pas de « prénom »)
        if kind == "character" and " " in n and n.split()[0] not in PROTAGONISTS and len(n.split()[0]) >= 4:
            names.add(n.split()[0])
    names = {n for n in names if n not in PROTAGONISTS and len(n) >= 4}
    if not names:
        return 0
    rx = _re.compile(r"\b(" + "|".join(_re.escape(n) for n in sorted(names, key=len, reverse=True)) + r")\b")
    n = 0
    with conn:
        for cid, eid, f, v in conn.execute("SELECT id, entity_id, field, value_json FROM claim WHERE spoiler_status='evaluated'").fetchall():
            own = conn.execute("SELECT canonical_name FROM entity WHERE id=?", (eid,)).fetchone()
            text = json.loads(v) if v.startswith('"') else v
            if isinstance(text, str) and rx.search(text) and not (own and rx.fullmatch(own[0] or "")):
                n += conn.execute("UPDATE claim SET spoiler_status='unknown' WHERE id=?", (cid,)).rowcount
        for aid, body in conn.execute("SELECT id, body FROM activity_content WHERE spoiler_status='evaluated' AND level < 3").fetchall():
            if rx.search(body):
                n += conn.execute("UPDATE activity_content SET spoiler_status='unknown' WHERE id=?", (aid,)).rowcount
        # lien source d'une fiche au titre masqué : l'URL contient le titre
        n += conn.execute("""UPDATE claim SET spoiler_status='unknown' WHERE field='source_page' AND spoiler_status='evaluated'
                             AND entity_id IN (SELECT id FROM entity WHERE name_status <> 'safe')""").rowcount
    return n


def apply_missables(conn: sqlite3.Connection) -> int:
    """Relie les contenus manquables à la mission qui en ferme l'accès (table + détection
    « avant la mission X »). La mission reçoit un compteur, jamais le détail (anti-spoiler)."""
    import re as _re
    mapping = json.loads((Path(__file__).parent / "data" / "missables.json").read_text(encoding="utf-8"))
    titles = {r[1].lower(): r[0] for r in conn.execute("SELECT id, canonical_name FROM entity WHERE kind IN ('mission','side_mission')")}
    links: dict[str, set[str]] = {}
    for eid, conf in mapping.items():
        if not eid.startswith("_") and isinstance(conf, dict) and conf.get("closes_at"):
            links.setdefault(conf["closes_at"], set()).add(eid)
    # détection automatique dans les textes : « avant (la mission) X » / « avant de lancer X »
    for eid, body in conn.execute("""SELECT a.entity_id, a.body FROM activity_content a JOIN entity e ON e.id = a.entity_id
                                     WHERE e.category LIKE '%anquable%' OR e.missable = 1""").fetchall():
        for m in _re.finditer(r"avant (?:la mission |de lancer |de terminer )?[«\"]?\s*([A-Z][\w' !?&-]{2,40}?)\s*[»\"]?(?=[.,;:)]|\s(?:et|ou|du|de)\b|$)", body):
            mid = titles.get(m.group(1).strip().lower())
            if mid:
                links.setdefault(mid, set()).add(eid)
    with conn:
        conn.execute("DELETE FROM claim WHERE field='closes_access'")
        for mid, items in links.items():
            if not conn.execute("SELECT 1 FROM entity WHERE id=?", (mid,)).fetchone():
                continue
            conn.execute("INSERT INTO claim(entity_id,field,value_json,value_kind,source_id,status,spoiler_status) "
                         "VALUES (?,?,?,?,?,?,?)", (mid, "closes_access", json.dumps(sorted(items)), "community",
                                                     "manual", "probable", "unknown"))   # jamais exposé : seul le compte l'est
            for i in items:
                conn.execute("UPDATE entity SET missable=1 WHERE id=?", (i,))
    return sum(len(v) for v in links.values())


# --------------------------------------------------------------------------- GTA Town (CC BY 4.0)
def _chapter_of(label: str | None):
    m = re.search(r"Chapter (\d+)", label or "")
    return int(m.group(1)) if m else None


def import_gtatown(conn: sqlite3.Connection, data: dict) -> dict:
    """Fusionne les exports GTA Town dans la base existante, sans doublon :
    - véhicules / armes : rattachés à la fiche existante (même nom), sinon fiche créée ;
    - missions : même identifiant que GTA Wiki (titre), porte de chapitre ;
    - repères de carte : un point à < 45 u. d'un point existant de même catégorie (ou même nom)
      devient une confirmation de ce point, pas un nouveau marqueur.
    Les données personnelles (statuts, notes, progression) sont dans d'autres tables : jamais touchées."""
    from .connectors import gtatown as gt
    from .assistant import best_match
    ensure_sources(conn)
    rep = ImportReport()
    stats = {"vehicles_linked": 0, "vehicles_new": 0, "weapons_linked": 0, "weapons_new": 0,
             "missions": 0, "points_merged": 0, "points_new": 0, "reference": 0}
    S = gt.SOURCE_ID

    def catalog_entry(kind, e, fields):
        cands = [{"id": r[0], "name": r[1]} for r in conn.execute(
            "SELECT id, canonical_name FROM entity WHERE kind=?", (f"{kind}_variant",))]
        name = e["name"]
        full = name if not e.get("manufacturer") or e["manufacturer"] in name else f"{e['manufacturer']} {name}"
        m = _year_match(full, cands, used) or best_match(full, [c for c in cands if c["id"] not in used], strict=True) \
            or best_match(name, [c for c in cands if c["id"] not in used], strict=True)
        if m:
            used.add(m["id"])
            stats[f"{kind}s_linked"] += 1
            vid = m["id"]
        else:
            stats[f"{kind}s_new"] += 1
            pi = ParsedItem(slug=_slugify(full), url=e["url"], kind=kind, name=full,
                            fields={k: fields[k] for k in ("manufacturer", "class") if fields.get(k)}, images=[])
            import_items(conn, [pi], S)
            vid = f"{kind}:{pi.slug}:std"
            if e.get("spoiler"):   # véhicule/arme lié à l'histoire selon la source : nom masqué
                conn.execute("UPDATE entity SET name_status='unknown' WHERE id=?", (vid,))
        with conn:
            for k, v in fields.items():
                if v is None or v == "":
                    continue
                if k in gt_TEXT:
                    st = classify.descriptive_status(v) if k == "description_en" else classify.field_spoiler_status("how_to_unlock", v)
                    if e.get("spoiler"):
                        st = "unknown"
                    _record_claim_raw(conn, vid, k, v, S, e["url"], st, rep)
                else:
                    _record_claim(conn, vid, k, v, S, e["url"], rep)
        return vid

    gt_TEXT = {"description_en", "how_to_unlock_en"}
    used: set[str] = set()   # une fiche existante ne reçoit qu'une seule ligne GTA Town
    for e in data.get("vehicles", {}).get("entries", []):
        cls = e.get("class") or ""
        standout = cls[len("Standout: "):] if cls.startswith("Standout: ") else None
        catalog_entry("vehicle", e, {
            "manufacturer": e.get("manufacturer"), "class": None if standout else cls or None,
            "standout_set": standout, "vehicle_type": gt.VEHICLE_TYPE_FR.get(e.get("type"), e.get("type")),
            "speed": e.get("speed"), "acceleration": e.get("acceleration"), "handling_road": e.get("handling"),
            "handling_offroad": e.get("offroad"), "strength": e.get("strength"),
            "top_speed_kmh": round(e["top_speed_mph"] * 1.609) if e.get("top_speed_mph") else None,
            "seats": e.get("seats"), "drivetrain": e.get("drivetrain"), "price": e.get("price"),
            "based_on": e.get("real_life") or None, "game_edition": e.get("edition"),
            "description_en": e.get("summary")})
    for e in data.get("weapons", {}).get("entries", []):
        catalog_entry("weapon", e, {
            "manufacturer": e.get("manufacturer"), "class": e.get("class"), "damage": e.get("damage"),
            "fire_rate": e.get("fire_rate"), "accuracy": e.get("accuracy"), "range": e.get("range"),
            "clip_size": e.get("clip_size"), "price": e.get("price"), "attachments": e.get("attachments") or None,
            "based_on": e.get("real_life") or None, "game_edition": e.get("edition"),
            "how_to_unlock_en": e.get("unlock"), "description_en": e.get("summary")})
    reclassify_catalog_names(conn)

    # Missions : porte de chapitre (nom visible une fois le chapitre atteint), résumé en niveau 3.
    ms = []
    for e in data.get("missions", {}).get("entries", []):
        lab = e.get("chapter") or ""
        side = lab.startswith("Side")
        giver = lab.split(" - ", 1)[1] if side and " - " in lab else None
        ch = _chapter_of(lab)
        title = re.sub(r":\s*.*", "", lab.replace("Side: ", "")).strip() if ch else None
        ms.append({"title": e["name"], "chapter": ch, "chapter_title": lab.split(": ", 2)[-1].split(" (")[0].split(" - ")[0] if ch else None,
                   "kind": "side_mission" if side else "mission", "giver": giver, "url": e["url"],
                   "description": e.get("summary")})
        _ = title
    r = import_missions(conn, ms, S)
    stats["missions"] = len(ms)
    with conn:
        for e in data.get("missions", {}).get("entries", []):
            _record_claim_raw(conn, f"mission:{_slugify(e['name'])}", "order", e.get("order"), S, e["url"], "evaluated", rep)

    # Repères de carte
    existing = [(r[0], r[1], r[2], r[3], gazetteer_norm(r[4])) for r in conn.execute(
        "SELECT p.entity_id, p.x, p.y, e.category, e.canonical_name FROM location_point p JOIN entity e ON e.id=p.entity_id")]
    grid: dict[tuple[int, int], list] = {}
    for t in existing:
        grid.setdefault((int(t[1] // 100), int(t[2] // 100)), []).append(t)

    def near(x, y, cat, nname):
        gx, gy = int(x // 100), int(y // 100)
        best = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for t in grid.get((gx + dx, gy + dy), []):
                    d = ((t[1] - x) ** 2 + (t[2] - y) ** 2) ** .5
                    if d < 45 and (t[3] == cat or (nname and t[4] == nname)) and (best is None or d < best[0]):
                        best = (d, t[0])
        return best[1] if best else None

    rows = [(e, gt.collectible_category(e)) for e in data.get("collectibles", {}).get("entries", [])]
    rows += [(e, gt.LOCATION_CAT[e["category"]]) for e in data.get("locations", {}).get("entries", [])
             if e.get("category") in gt.LOCATION_CAT]
    with conn:
        for e, cat in rows:
            xy = gt.to_game(e.get("map_x"), e.get("map_y"))
            if not xy:
                continue
            nname = gazetteer_norm(e["name"])
            hit = near(xy[0], xy[1], cat, nname)
            if hit:
                stats["points_merged"] += 1
                _record_claim_raw(conn, hit, "confirmed_by", "gtatown", S, e["url"], "evaluated", rep)
                continue
            eid = f"location:gtatown-{e['slug']}"
            if not conn.execute("SELECT 1 FROM entity WHERE id=?", (eid,)).fetchone():
                st = classify.category_status(cat)
                conn.execute("INSERT INTO entity(id,kind,canonical_name,spoiler_status,name_status,category,region_label,reliability) "
                             "VALUES (?,?,?,?,?,?,?,?)", (eid, "location", e["name"], st,
                                                          "safe" if st == "evaluated" else "unknown", cat,
                                                          e.get("area") or e.get("county"), "probable"))
                conn.execute("INSERT INTO location_point(entity_id,x,y,precision) VALUES (?,?,?,?)", (eid, xy[0], xy[1], "exact"))
                stats["points_new"] += 1
                t = (eid, xy[0], xy[1], cat, nname)
                grid.setdefault((int(xy[0] // 100), int(xy[1] // 100)), []).append(t)
            for k in ("set", "number", "county"):
                if e.get(k) not in (None, ""):
                    _record_claim_raw(conn, eid, k, e[k], S, e["url"], "evaluated", rep)

    # Fiches de référence : triches, trophées, défis
    with conn:
        for ds, kind in (("cheats", "cheat"), ("trophies", "trophy"), ("challenges", "challenge")):
            for e in data.get(ds, {}).get("entries", []):
                body = {k: v for k, v in e.items() if k not in ("slug", "name", "url", "spoiler")}
                conn.execute("INSERT INTO reference_item(id,kind,name,data_json,spoiler,source_id,source_url) VALUES (?,?,?,?,?,?,?) "
                             "ON CONFLICT(id) DO UPDATE SET name=excluded.name, data_json=excluded.data_json, spoiler=excluded.spoiler, "
                             "source_url=excluded.source_url, updated_at=datetime('now') WHERE data_json<>excluded.data_json OR name<>excluded.name",
                             (f"{kind}:{e['slug']}", kind, e["name"], json.dumps(body, ensure_ascii=False), int(bool(e.get("spoiler"))), S, e["url"]))
                stats["reference"] += 1
    stats["changed"] = len(rep.changed) + len(r.changed)
    stats["quarantined"] = len(rep.quarantined)
    return stats


_YEAR = re.compile(r"^'(\d\d)\s+|\((?:19|20)(\d\d)\)|'(\d\d)\b")


def _split_year(name: str):
    yrs = [g for m in _YEAR.finditer(name) for g in m.groups() if g]
    return gazetteer_norm(_YEAR.sub(" ", name)), (yrs[0] if yrs else None)


def _year_match(name: str, cands: list[dict], used: set) -> dict | None:
    """« '65 Vapid Dominator » ↔ « Vapid Dominator (1965) » : même nom sans l'année, et année
    identique si les deux en ont une (deux millésimes = deux fiches distinctes)."""
    base, yr = _split_year(name)
    best = None
    for c in cands:
        if c["id"] in used:
            continue
        cb, cy = _split_year(c["name"])
        if cb != base:
            continue
        if yr and cy and yr != cy:
            continue
        score = 2 if yr == cy else 1
        if not best or score > best[0]:
            best = (score, c)
    return best[1] if best else None


def gazetteer_norm(s):
    from .gazetteer import norm
    return norm(s or "")
