"""Catalogue véhicules/armes : requêtes structurées, filtres, classement pondéré.

Toutes les lectures passent par les vues visible_* (anti-spoiler). Les calculs
sont déterministes : l'IA n'invente jamais un classement, elle appelle ceci.
"""
from __future__ import annotations

import json
import sqlite3

STATS = ["speed", "acceleration", "handling_road", "handling_offroad", "strength"]

import re as _re
_CANON = {"suvs": "SUVs", "suv": "SUVs", "smg": "SMGs", "smgs": "SMGs", "lmg": "LMGs", "lmgs": "LMGs", "utility": "Commercial",
          "service": "Commercial", "industrial": "Commercial", "trucks": "Commercial", "throwable": "Throwables",
          "throwables": "Throwables", "launchers": "Heavy", "heavy": "Heavy", "melee": "Melee"}
_WEAPON_GUESS = [(r"shocker|stun|taser|\.357|es9|k17|dw9|drifter|hobo|pistol|revolver|\.38|\.50|handgun|ap pistol|deagle|eagle", "Handguns"), (r"smg|sub-?machine|micro|uzi|vf5|pd-90", "SMGs"),
                 (r"shotgun|az1200|pump|sawed", "Shotguns"), (r"sniper|marksman|bolt action|longshot|sms-01|laird|ff-50|ff-sr", "Sniper Rifles"),
                 (r"assault|carbine|rifle|556|drx|ar-|battle rifle", "Assault Rifles"), (r"machine gun|lmg|minigun|m249|m60", "LMGs"), (r"1922|tommy", "SMGs"),
                 (r"grenade|molotov|fire bottle|flashbang|bomb|sticky|tear gas|ball", "Throwables"),
                 (r"rpg|launcher|h-at", "Heavy"),
                 (r"fist|switchblade|knife|bat|crowbar|knuckle|machete|hammer|club|golf|wrench|hatchet|axe|baton|bottle|pool cue|shovel|katana|sword|dagger|nipper", "Melee"),
                 (r"binocular|camera|parachute|flashlight|phone|fishing|key|cloner|armor|vest|scuba|jerry", "Gear")]


def canonical_class(cls, name: str = "", kind: str = "vehicle"):
    """Une seule orthographe par classe ; « Boats , Emergency » -> « Boats » ; arme sans classe -> déduite du nom."""
    if cls:
        first = str(cls).split(",")[0].strip()
        return _CANON.get(first.lower(), first)
    if kind == "weapon":
        n = name.lower()
        for rx, c in _WEAPON_GUESS:
            if _re.search(rx, n):
                return c
    return None


def _best_values(conn: sqlite3.Connection, entity_ids: list[str]) -> dict[str, dict]:
    """Pour chaque entité/champ : valeur retenue + toutes les valeurs (contradictions)."""
    out: dict[str, dict] = {e: {} for e in entity_ids}
    if not entity_ids:
        return out
    q = ",".join("?" * len(entity_ids))
    rows = conn.execute(f"""
        SELECT c.entity_id, c.field, c.value_json, c.value_kind, c.source_id, c.source_url,
               c.status, c.observed_at, s.reliability
        FROM visible_claim c JOIN source s ON s.id = c.source_id
        WHERE c.entity_id IN ({q}) AND c.status NOT IN ('obsolete')
        ORDER BY CASE c.status WHEN 'confirmed' THEN 0 WHEN 'probable' THEN 1 ELSE 2 END,
                 s.reliability DESC, c.observed_at DESC""", entity_ids).fetchall()
    for r in rows:
        slot = out[r["entity_id"]].setdefault(r["field"], {"value": json.loads(r["value_json"]),
                                                            "kind": r["value_kind"], "sources": []})
        slot["sources"].append({"source": r["source_id"], "url": r["source_url"],
                                "value": json.loads(r["value_json"]), "status": r["status"],
                                "observed_at": r["observed_at"]})
    for fields in out.values():
        for slot in fields.values():
            slot["contradiction"] = len({json.dumps(s["value"]) for s in slot["sources"]}) > 1
    return out


def get_pref(conn, key: str, default=None):
    r = conn.execute("SELECT value_json FROM user_pref WHERE key=?", (key,)).fetchone()
    return json.loads(r[0]) if r else default


def set_pref(conn, key: str, value) -> None:
    with conn:
        conn.execute("INSERT INTO user_pref(key,value_json) VALUES (?,?) ON CONFLICT(key) DO UPDATE "
                     "SET value_json=excluded.value_json, updated_at=datetime('now')",
                     (key, json.dumps(value, ensure_ascii=False)))


def vehicles(conn: sqlite3.Connection, *, min_stats: dict[str, float] | None = None,
             max_price: float | None = None, seats_min: int | None = None,
             drivetrain: list[str] | None = None, classes: list[str] | None = None,
             exclude_classes: list[str] | None = None, variant_types: list[str] | None = None,
             weights: dict[str, float] | None = None, query: str | None = None,
             limit: int = 5000) -> list[dict]:
    rows = conn.execute("""
        SELECT v.id, v.display_name, vv.model_id, vv.variant_type, vm.manufacturer, vm.class
        FROM visible_entity v
        JOIN vehicle_variant vv ON vv.entity_id = v.id
        JOIN vehicle_model vm ON vm.entity_id = vv.model_id""").fetchall()
    ids = [r["id"] for r in rows]
    vals = _best_values(conn, ids)
    media = {}
    for m in conn.execute(f"SELECT entity_id, url FROM visible_media WHERE entity_id IN ({','.join('?'*len(ids)) or 'NULL'})", ids):
        media.setdefault(m["entity_id"], m["url"])

    weights = weights or {}
    total_w = sum(w for w in weights.values() if w > 0) or 1
    result = []
    for r in rows:
        f = vals[r["id"]]
        val = lambda k: f.get(k, {}).get("value")  # noqa: E731
        cls = canonical_class(val("class") or r["class"], r["display_name"], "vehicle")
        if classes and cls not in classes:
            continue
        if exclude_classes and cls in exclude_classes:
            continue
        if variant_types and r["variant_type"] not in variant_types:
            continue
        if drivetrain and val("drivetrain") not in drivetrain:
            continue
        if seats_min and (val("seats") or 0) < seats_min:
            continue
        if max_price is not None and (val("price") is None or val("price") > max_price):
            continue
        if min_stats and any((val(k) is None or val(k) < v) for k, v in min_stats.items()):
            continue
        if query and query.lower() not in r["display_name"].lower():
            continue
        score = None
        if weights:
            known = [(k, w) for k, w in weights.items() if w > 0 and isinstance(val(k), (int, float))]
            if known:  # stat manquante = non comptée, jamais inventée
                score = round(sum(val(k) * w for k, w in known) / sum(w for _, w in known), 2)
                coverage = sum(w for _, w in known) / total_w
                score = {"value": score, "coverage": round(coverage, 2)}
        result.append({
            "id": r["id"], "name": r["display_name"], "model_id": r["model_id"],
            "variant_type": r["variant_type"], "manufacturer": val("manufacturer") or r["manufacturer"],
            "class": cls, "image": media.get(r["id"]),
            "stats": {k: val(k) for k in STATS},
            "price": val("price"), "seats": val("seats"), "drivetrain": val("drivetrain"),
            "top_speed_kmh": val("top_speed_kmh"), "vehicle_type": val("vehicle_type"), "standout_set": val("standout_set"),
            "score": score,
        })
    if weights:
        result.sort(key=lambda x: (x["score"] is None, -(x["score"] or {}).get("value", 0)))
    else:
        result.sort(key=lambda x: x["name"])
    return result[:limit]


def vehicle_detail(conn, entity_id: str) -> dict | None:
    from . import spoiler
    base = spoiler.get_entity(conn, entity_id)
    if not base:
        return None
    vv = conn.execute("SELECT model_id, variant_type FROM vehicle_variant WHERE entity_id=?", (entity_id,)).fetchone()
    base["fields"] = _best_values(conn, [entity_id])[entity_id]
    if vv:
        base["variant_type"] = vv["variant_type"]
        base["siblings"] = [dict(r) for r in conn.execute("""
            SELECT v.id, v.display_name AS name, vv.variant_type,
                   (SELECT url FROM visible_media m WHERE m.entity_id = v.id LIMIT 1) AS image FROM vehicle_variant vv
            JOIN visible_entity v ON v.id = vv.entity_id
            WHERE vv.model_id = ? AND vv.entity_id <> ? ORDER BY v.display_name""", (vv["model_id"], entity_id))]
        base["kits"] = [dict(r) for r in conn.execute("""
            SELECT k.entity_id AS id, v.display_name AS name FROM kit k
            JOIN visible_entity v ON v.id = k.entity_id WHERE k.variant_id = ?""", (entity_id,))]
        base["mods"] = [dict(r) for r in conn.execute("""
            SELECT o.entity_id AS id, v.display_name AS name, mc.name_fr AS category
            FROM variant_mod vm JOIN mod_option o ON o.entity_id = vm.option_id
            JOIN mod_category mc ON mc.id = o.category_id
            JOIN visible_entity v ON v.id = o.entity_id WHERE vm.variant_id = ?""", (entity_id,))]
    base["hidden_fields"] = conn.execute(
        "SELECT COUNT(DISTINCT field) FROM claim WHERE entity_id=? AND id NOT IN (SELECT id FROM visible_claim)",
        (entity_id,)).fetchone()[0]
    return base


WEAPON_STATS = ["damage", "accuracy", "weapon_handling", "range"]


def weapons(conn: sqlite3.Connection, *, classes: list[str] | None = None,
            min_stats: dict[str, float] | None = None, max_price: float | None = None,
            free_only: bool = False, weights: dict[str, float] | None = None,
            query: str | None = None) -> list[dict]:
    rows = conn.execute("""
        SELECT v.id, v.display_name, wv.model_id, wv.variant_type, wm.class
        FROM visible_entity v JOIN weapon_variant wv ON wv.entity_id = v.id
        JOIN weapon_model wm ON wm.entity_id = wv.model_id""").fetchall()
    ids = [r["id"] for r in rows]
    vals = _best_values(conn, ids)
    media = {}
    if ids:
        for m in conn.execute(f"SELECT entity_id, url FROM visible_media WHERE entity_id IN ({','.join('?'*len(ids))})", ids):
            media.setdefault(m["entity_id"], m["url"])
    out = []
    for r in rows:
        f = vals[r["id"]]
        val = lambda k: f.get(k, {}).get("value")  # noqa: E731
        cls = canonical_class(val("class") or r["class"], r["display_name"], "weapon")
        if classes and cls not in classes:
            continue
        if min_stats and any((val(k) is None or val(k) < v) for k, v in min_stats.items()):
            continue
        # « gratuit » = pas de prix d'achat connu ET un moyen d'obtention visible
        free = val("price") is None and (val("how_to_unlock") is not None or val("purchase_from") is None)
        if free_only and not free:
            continue
        if max_price is not None and val("price") is not None and val("price") > max_price:
            continue
        if query and query.lower() not in r["display_name"].lower():
            continue
        score = None
        if weights:
            known = [(k, w) for k, w in weights.items() if w > 0 and isinstance(val(k), (int, float))]
            if known:
                tw = sum(w for _, w in known)
                score = {"value": round(sum(val(k) * w for k, w in known) / tw, 2),
                         "coverage": round(tw / (sum(w for w in weights.values() if w > 0) or 1), 2)}
        out.append({"id": r["id"], "name": r["display_name"], "model_id": r["model_id"],
                    "variant_type": r["variant_type"], "class": cls, "image": media.get(r["id"]),
                    "stats": {k: val(k) for k in WEAPON_STATS}, "price": val("price"),
                    "capacity": val("capacity"), "moddable": val("moddable"),
                    "free_hint": free, "score": score})
    out.sort(key=(lambda x: (x["score"] is None, -(x["score"] or {}).get("value", 0))) if weights else (lambda x: x["name"]))
    return out


def item_detail(conn, entity_id: str) -> dict | None:
    """Fiche véhicule OU arme, avec variantes sœurs, kits, options et lieux sur la carte."""
    d = _item_detail(conn, entity_id)
    if d:
        d["map_points"] = map_points(conn, entity_id, d["name"]) if not d.get("name_hidden") else []
        st = conn.execute("SELECT status FROM user_item_status WHERE entity_id=?", (entity_id,)).fetchone()
        d["status"] = st[0] if st else None
    return d


def _item_detail(conn, entity_id: str) -> dict | None:
    if entity_id.startswith("weapon:"):
        from . import spoiler
        base = spoiler.get_entity(conn, entity_id)
        if not base:
            return None
        wv = conn.execute("SELECT model_id, variant_type FROM weapon_variant WHERE entity_id=?", (entity_id,)).fetchone()
        base["fields"] = _best_values(conn, [entity_id])[entity_id]
        base["siblings"], base["kits"], base["mods"] = [], [], []
        if wv:
            base["variant_type"] = wv["variant_type"]
            base["siblings"] = [dict(r) for r in conn.execute("""
                SELECT v.id, v.display_name AS name, wv.variant_type,
                       (SELECT url FROM visible_media m WHERE m.entity_id = v.id LIMIT 1) AS image FROM weapon_variant wv
                JOIN visible_entity v ON v.id = wv.entity_id
                WHERE wv.model_id = ? AND wv.entity_id <> ? ORDER BY v.display_name""", (wv["model_id"], entity_id))]
            base["mods"] = [dict(r) for r in conn.execute("""
                SELECT o.entity_id AS id, v.display_name AS name, mc.name_fr AS category
                FROM variant_mod vm JOIN mod_option o ON o.entity_id = vm.option_id
                JOIN mod_category mc ON mc.id = o.category_id
                JOIN visible_entity v ON v.id = o.entity_id WHERE vm.variant_id = ?""", (entity_id,))]
        base["hidden_fields"] = conn.execute(
            "SELECT COUNT(DISTINCT field) FROM claim WHERE entity_id=? AND id NOT IN (SELECT id FROM visible_claim)",
            (entity_id,)).fetchone()[0]
        return base
    return vehicle_detail(conn, entity_id)


def map_points(conn, item_id: str, name: str) -> list[dict]:
    """Lieux de la carte (véhicule d'exception, arme cachée…) qui correspondent à cette fiche."""
    from .assistant import best_match
    kind = "véhicule" if item_id.startswith("vehicle:") else "arme"
    out = []
    for r in conn.execute("""SELECT v.id, v.display_name AS name, v.category, p.x, p.y, p.precision
                             FROM visible_entity v JOIN visible_location p ON p.entity_id = v.id
                             WHERE lower(v.category) LIKE ?""", (f"%{kind}%",)):
        if best_match(r["name"], [{"name": name}], strict=True):
            out.append(dict(r))
    return out
