"""Catalogue véhicules/armes : requêtes structurées, filtres, classement pondéré.

Toutes les lectures passent par les vues visible_* (anti-spoiler). Les calculs
sont déterministes : l'IA n'invente jamais un classement, elle appelle ceci.
"""
from __future__ import annotations

import json
import sqlite3

STATS = ["speed", "acceleration", "handling_road", "handling_offroad", "strength"]


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
             limit: int = 500) -> list[dict]:
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
        cls = val("class") or r["class"]
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
            SELECT v.id, v.display_name AS name, vv.variant_type FROM vehicle_variant vv
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
