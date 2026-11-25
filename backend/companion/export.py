"""Instantané hors ligne pour l'APK : python -m companion.export --out ../web/public/data/snapshot.json

Exporté avec une progression VIDE (protection anti-spoiler maximale) : seul ce
qui est visible en début de partie est embarqué. Le reste vient du PC quand il
est joignable, filtré selon la vraie progression.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from . import api, catalog, db, spoiler


def build(db_path: str) -> dict:
    tmp = Path(tempfile.mkdtemp()) / "snap.db"
    shutil.copy(db_path, tmp)
    c = db.connect(tmp)
    spoiler.set_progress(c, spoiler.Progress())          # progression vide
    c.execute("DELETE FROM hint_reveal"); c.execute("DELETE FROM solution_unlock")
    c.execute("DELETE FROM name_reveal"); c.execute("DELETE FROM user_item_status"); c.commit()
    api._local.conn = c
    try:
        places = api.places(limit=100000)
        details = {}
        for v in catalog.vehicles(c) + catalog.weapons(c):
            details[v["id"]] = catalog.item_detail(c, v["id"])
        for p in places:
            details[p["id"]] = api.get_entity(p["id"])
        # Contenus verrouillés : servis UNIQUEMENT sur demande explicite (indice / solution / titre)
        locked = {}
        for p in places:
            eid = p["id"]
            hints = [r[0] for r in c.execute("SELECT body FROM activity_content WHERE entity_id=? AND level=2 "
                                             "AND spoiler_status='evaluated' ORDER BY ord", (eid,))]
            sol = [r[0] for r in c.execute("SELECT body FROM activity_content WHERE entity_id=? AND level=3 "
                                           "AND spoiler_status='evaluated' ORDER BY ord", (eid,))]
            vid = c.execute("SELECT value_json FROM claim WHERE entity_id=? AND field='video' AND status<>'obsolete'", (eid,)).fetchone()
            name = c.execute("SELECT canonical_name FROM entity WHERE id=? AND name_status<>'safe'", (eid,)).fetchone()
            if hints or sol or vid or name:
                locked[eid] = {"hints": hints, "solution": sol, "video": json.loads(vid[0]) if vid else None,
                               "name": name[0] if name else None}
        story = {
            "chapters": [{"num": r[0], "title": r[1]} for r in c.execute("SELECT num, title FROM chapter ORDER BY num")],
            "missions": [{"id": r[0], "name": r[1], "alias": r[2], "kind": r[3], "name_safe": r[4] == "safe",
                          "chapter": (json.loads(r[5]) if r[5] else None)}
                         for r in c.execute("""SELECT e.id, e.canonical_name, e.neutral_alias, e.kind, e.name_status,
                              (SELECT value_json FROM claim WHERE entity_id=e.id AND field='chapter' AND status<>'obsolete')
                              FROM entity e WHERE e.kind IN ('mission','side_mission') AND e.spoiler_status='evaluated'""")],
            "characters": [{"id": r[0], "name": r[1], "chapter": r[2]} for r in c.execute("""
                SELECT e.id, e.canonical_name, (SELECT MIN(g.chapter) FROM spoiler_gate g WHERE g.entity_id=e.id AND g.kind='chapter')
                FROM entity e WHERE e.kind='character' AND e.spoiler_status='evaluated' AND e.name_status='safe'""")],
        }
        return {
            "version": 3,
            "story": story,
            "locked": locked,
            "vehicles": catalog.vehicles(c),
            "weapons": catalog.weapons(c),
            "places": places,
            "facets": api.place_facets(),
            "details": details,
            "prefs": {"vehicle_weights": catalog.get_pref(c, "vehicle_weights"),
                      "vehicle_exclude_classes": catalog.get_pref(c, "vehicle_exclude_classes")},
        }
    finally:
        api._local.conn = None
        c.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/companion.db")
    ap.add_argument("--out", default="../web/public/data/snapshot.json")
    a = ap.parse_args()
    data = build(a.db)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(out, f"{out.stat().st_size / 1e6:.1f} Mo", len(data["details"]), "fiches")


if __name__ == "__main__":
    main()
