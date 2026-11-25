"""Succès Xbox via OpenXBL (https://xbl.io) — clé dans la variable XBL_API_KEY (sur le PC).

Anti-spoiler : seuls les succès DÉBLOQUÉS sont affichés avec leur nom (vous les avez
déjà faits). Pour les autres, on ne donne qu'un compteur. Un succès débloqué peut
faire avancer la progression si un mapping est défini (progress_json, ex. {"chapter": 3}).
"""
from __future__ import annotations

import json
import os
import sqlite3
import urllib.request

API = "https://xbl.io/api/v2"
GTA6_NAMES = ("grand theft auto vi", "gta vi", "grand theft auto 6")


def _get(path: str, key: str, opener=urllib.request.urlopen) -> dict:
    req = urllib.request.Request(f"{API}{path}", headers={"X-Authorization": key, "Accept": "application/json",
                                                         "Accept-Language": "fr-FR"})
    with opener(req, timeout=30) as r:
        return json.loads(r.read())


def find_title_id(key: str, opener=urllib.request.urlopen) -> str | None:
    data = _get("/achievements", key, opener)
    for t in data.get("titles", []):
        if any(n in (t.get("name") or "").lower() for n in GTA6_NAMES):
            return str(t.get("titleId"))
    return None


def sync(conn: sqlite3.Connection, key: str | None = None, title_id: str | None = None,
         opener=urllib.request.urlopen) -> dict:
    key = key or os.environ.get("XBL_API_KEY")
    if not key:
        return {"ok": False, "error": "Clé OpenXBL absente (variable XBL_API_KEY sur le PC)."}
    title_id = title_id or os.environ.get("GTA6_TITLE_ID") or find_title_id(key, opener)
    if not title_id:
        return {"ok": False, "error": "GTA VI introuvable dans l'historique de jeux du compte Xbox."}
    data = _get(f"/achievements/title/{title_id}", key, opener)
    n_new = 0
    with conn:
        for a in data.get("achievements", []):
            unlocked = (a.get("progressState") == "Achieved")
            when = (a.get("progression") or {}).get("timeUnlocked")
            prev = conn.execute("SELECT unlocked FROM xbox_achievement WHERE id=?", (str(a["id"]),)).fetchone()
            if unlocked and (not prev or not prev[0]):
                n_new += 1
            conn.execute("""INSERT INTO xbox_achievement(id,title_id,name,description,unlocked,unlocked_at,synced_at)
                            VALUES (?,?,?,?,?,?,datetime('now'))
                            ON CONFLICT(id) DO UPDATE SET name=excluded.name, description=excluded.description,
                              unlocked=excluded.unlocked, unlocked_at=excluded.unlocked_at, synced_at=excluded.synced_at""",
                         (str(a["id"]), title_id, a.get("name", ""), a.get("description") or a.get("lockedDescription"),
                          int(unlocked), when))
        # Progression automatique : le chapitre max parmi les succès débloqués mappés
        best = 0
        for (pj,) in conn.execute("SELECT progress_json FROM xbox_achievement WHERE unlocked=1 AND progress_json IS NOT NULL"):
            best = max(best, int(json.loads(pj).get("chapter", 0)))
        if best:
            conn.execute("UPDATE progress_state SET chapter = MAX(chapter, ?) WHERE id = 1", (best,))
    return {"ok": True, "title_id": title_id, "new_unlocked": n_new, **summary(conn)}


def summary(conn: sqlite3.Connection) -> dict:
    total, done = conn.execute("SELECT COUNT(*), COALESCE(SUM(unlocked),0) FROM xbox_achievement").fetchone()
    unlocked = [dict(r) for r in conn.execute(
        "SELECT name, description, unlocked_at FROM xbox_achievement WHERE unlocked=1 ORDER BY unlocked_at DESC")]
    # Les succès non débloqués ne sont jamais nommés (spoiler potentiel)
    return {"total": total, "unlocked_count": done, "unlocked": unlocked, "locked_count": total - done}
