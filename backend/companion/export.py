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
            details[p["id"]] = spoiler.get_entity(c, p["id"])
        return {
            "version": 1,
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
