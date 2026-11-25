"""API FastAPI. Lancement : uvicorn companion.api:app --host 127.0.0.1 --port 8765

Sécurité : jeton obligatoire (variable COMPANION_TOKEN) sauf en local pur.
Exposer uniquement via Tailscale, jamais directement sur Internet.
"""
from __future__ import annotations

import os
import secrets
import threading
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import catalog, db, importer, spoiler

DB_PATH = os.environ.get("COMPANION_DB", "data/companion.db")
TOKEN = os.environ.get("COMPANION_TOKEN")
_local = threading.local()

app = FastAPI(title="GTA VI Companion", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def conn():
    c = getattr(_local, "conn", None)
    if c is None:
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        c = _local.conn = db.connect(DB_PATH)
    return c


def auth(authorization: str | None = Header(default=None)):
    if TOKEN and not (authorization and secrets.compare_digest(authorization, f"Bearer {TOKEN}")):
        raise HTTPException(401, "Jeton invalide")


class ProgressIn(BaseModel):
    chapter: int = 0
    completed_missions: list[str] = []
    met_characters: list[str] = []
    discovered_regions: list[str] = []


class StatusIn(BaseModel):
    status: str


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/progress", dependencies=[Depends(auth)])
def get_progress():
    c = conn()
    return {
        "chapter": c.execute("SELECT chapter FROM progress_state").fetchone()[0],
        "completed_missions": [r[0] for r in c.execute("SELECT entity_id FROM progress_mission")],
        "met_characters": [r[0] for r in c.execute("SELECT entity_id FROM progress_character")],
        "discovered_regions": [r[0] for r in c.execute("SELECT entity_id FROM progress_region")],
    }


@app.put("/api/progress", dependencies=[Depends(auth)])
def put_progress(p: ProgressIn):
    spoiler.set_progress(conn(), spoiler.Progress(p.chapter, set(p.completed_missions),
                                                  set(p.met_characters), set(p.discovered_regions)))
    return get_progress()


@app.get("/api/vehicles", dependencies=[Depends(auth)])
def list_vehicles(
    q: str | None = None,
    min_speed: float | None = None, min_acceleration: float | None = None,
    min_handling_road: float | None = None, min_handling_offroad: float | None = None,
    min_strength: float | None = None,
    max_price: float | None = None, seats_min: int | None = None,
    drivetrain: list[str] = Query(default=[]), vclass: list[str] = Query(default=[]),
    exclude_class: list[str] = Query(default=[]), variant_type: list[str] = Query(default=[]),
    use_profile: bool = False,
):
    c = conn()
    mins = {k: v for k, v in {"speed": min_speed, "acceleration": min_acceleration,
                              "handling_road": min_handling_road, "handling_offroad": min_handling_offroad,
                              "strength": min_strength}.items() if v is not None}
    weights = catalog.get_pref(c, "vehicle_weights") if use_profile else None
    excl = exclude_class or (catalog.get_pref(c, "vehicle_exclude_classes", []) if use_profile else [])
    return catalog.vehicles(c, min_stats=mins, max_price=max_price, seats_min=seats_min,
                            drivetrain=drivetrain or None, classes=vclass or None,
                            exclude_classes=excl or None, variant_types=variant_type or None,
                            weights=weights, query=q)


@app.get("/api/weapons", dependencies=[Depends(auth)])
def list_weapons(q: str | None = None, wclass: list[str] = Query(default=[]),
                 min_damage: float | None = None, min_accuracy: float | None = None,
                 min_range: float | None = None, min_handling: float | None = None,
                 max_price: float | None = None, free_only: bool = False, ranked: bool = False):
    mins = {k: v for k, v in {"damage": min_damage, "accuracy": min_accuracy, "range": min_range,
                              "weapon_handling": min_handling}.items() if v is not None}
    w = catalog.get_pref(conn(), "weapon_weights", {"damage": 0.4, "accuracy": 0.25, "range": 0.2,
                                                     "weapon_handling": 0.15}) if ranked else None
    return catalog.weapons(conn(), classes=wclass or None, min_stats=mins, max_price=max_price,
                           free_only=free_only, weights=w, query=q)


@app.get("/api/vehicles/{entity_id:path}", dependencies=[Depends(auth)])
def get_vehicle(entity_id: str):
    d = catalog.item_detail(conn(), entity_id)
    if not d:
        raise HTTPException(404, "Introuvable ou masqué par la protection anti-spoiler")
    return d


@app.get("/api/entity/{entity_id:path}", dependencies=[Depends(auth)])
def get_entity(entity_id: str):
    c = conn()
    d = spoiler.get_entity(c, entity_id)
    if not d:
        raise HTTPException(404, "Introuvable ou masqué par la protection anti-spoiler")
    d["has_solution"] = bool(c.execute("SELECT 1 FROM activity_content WHERE entity_id=? AND level=3", (entity_id,)).fetchone())
    st = c.execute("SELECT status FROM user_item_status WHERE entity_id=?", (entity_id,)).fetchone()
    d["status"] = st[0] if st else None
    row = {"name": d["name"], "category": d.get("category")}
    link_catalog(c, [row])
    cat = (d.get("category") or "").lower()
    if not row.get("linked_id") and ("véhicule" in cat or "vehicle" in cat) and not d.get("name_hidden"):
        # fiche absente : lecture à la demande d'UNE page GTACity (cache), puis nouvelle liaison
        if importer.resolve_on_demand(c, d["name"]):
            link_catalog(c, [row])
    if row.get("linked_id"):
        d["linked"] = {"id": row["linked_id"], "image": row["image"], "stats": row["linked_stats"]}
    loc = c.execute("SELECT x, y, precision FROM visible_location WHERE entity_id=?", (entity_id,)).fetchone()
    d["location"] = dict(loc) if loc else None
    return d


@app.post("/api/entity/{entity_id:path}/hint", dependencies=[Depends(auth)])
def hint(entity_id: str):
    spoiler.reveal_next_hint(conn(), entity_id)
    return get_entity(entity_id)


@app.post("/api/entity/{entity_id:path}/solution", dependencies=[Depends(auth)])
def solution(entity_id: str, confirm: bool = False):
    try:
        spoiler.unlock_solution(conn(), entity_id, confirmed=confirm)
    except PermissionError as e:
        raise HTTPException(400, str(e))
    return get_entity(entity_id)


@app.post("/api/entity/{entity_id:path}/reveal-name", dependencies=[Depends(auth)])
def reveal_name(entity_id: str, confirm: bool = False):
    try:
        spoiler.reveal_name(conn(), entity_id, confirmed=confirm)
    except PermissionError as e:
        raise HTTPException(400, str(e))
    return get_entity(entity_id)


PLACE_KINDS = ("location", "secret_quest", "random_encounter", "dynamic_event", "easter_egg",
               "mystery", "activity", "collectible", "property")


@app.get("/api/places", dependencies=[Depends(auth)])
def places(region: str | None = None, category: str | None = None, kind: str | None = None,
           hide_done: bool = False, secrets_only: bool = False, limit: int = 3000):
    c = conn()
    sql = f"""SELECT v.id, v.kind, v.display_name AS name, v.category, v.region_label AS region,
                     v.reliability, p.x, p.y, p.precision, u.status
              FROM visible_entity v
              LEFT JOIN visible_location p ON p.entity_id = v.id
              LEFT JOIN user_item_status u ON u.entity_id = v.id
              WHERE v.kind IN ({",".join("?" * len(PLACE_KINDS))})"""
    args: list = list(PLACE_KINDS)
    if region:
        sql += " AND v.region_label = ?"; args.append(region)
    if category:
        sql += " AND v.category = ?"; args.append(category)
    if kind:
        sql += " AND v.kind = ?"; args.append(kind)
    if secrets_only:
        sql += " AND v.id LIKE 'secret:%'"
    if hide_done:
        sql += " AND COALESCE(u.status,'') NOT IN ('discovered','done')"
    sql += " ORDER BY v.category, v.display_name LIMIT ?"; args.append(limit)
    rows = [dict(r) for r in c.execute(sql, args)]
    link_catalog(c, rows)
    return rows


def link_catalog(c, rows: list[dict]) -> None:
    """Relie un lieu « véhicule d'exception » / « arme » à sa fiche catalogue (photo, stats)."""
    from .assistant import best_match
    veh = wea = None
    for r in rows:
        cat = (r.get("category") or "").lower()
        if "véhicule" in cat or "vehicle" in cat:
            veh = veh if veh is not None else catalog.vehicles(c)
            m = best_match(r["name"], veh, strict=True)
        elif "arme" in cat or "weapon" in cat:
            wea = wea if wea is not None else catalog.weapons(c)
            m = best_match(r["name"], wea, strict=True)
        else:
            continue
        if m:
            r["linked_id"], r["image"] = m["id"], m["image"]
            r["linked_stats"] = m["stats"]


@app.get("/api/places/facets", dependencies=[Depends(auth)])
def place_facets():
    c = conn()
    q = f"FROM visible_entity WHERE kind IN ({','.join('?' * len(PLACE_KINDS))})"
    return {
        "regions": [dict(r) for r in c.execute(
            f"SELECT region_label AS name, COUNT(*) AS n {q} AND region_label IS NOT NULL GROUP BY 1 ORDER BY 2 DESC", PLACE_KINDS)],
        "categories": [dict(r) for r in c.execute(
            f"SELECT category AS name, COUNT(*) AS n, MAX(id LIKE 'secret:%') AS secret {q} AND category IS NOT NULL GROUP BY 1 ORDER BY 2 DESC", PLACE_KINDS)],
    }


class ChatIn(BaseModel):
    message: str
    session: str = "default"
    history: list[dict] = []


_assistant = {}


def assistant_for(c):
    from . import assistant
    key = id(c)
    if key not in _assistant:
        _assistant[key] = assistant.Assistant(c, Path(DB_PATH).resolve().parent / "gtadb-landmarks.json")
    return _assistant[key]


@app.post("/api/assistant", dependencies=[Depends(auth)])
def chat(body: ChatIn):
    return assistant_for(conn()).chat(body.session, body.message[:2000], body.history)


@app.get("/api/xbox", dependencies=[Depends(auth)])
def xbox_summary():
    from . import xbox
    return xbox.summary(conn())


@app.post("/api/xbox/sync", dependencies=[Depends(auth)])
def xbox_sync():
    from . import xbox
    return xbox.sync(conn())


@app.get("/api/search", dependencies=[Depends(auth)])
def search(q: str):
    return spoiler.search(conn(), q)


@app.get("/api/prefs/{key}", dependencies=[Depends(auth)])
def get_pref(key: str):
    return catalog.get_pref(conn(), key)


@app.put("/api/prefs/{key}", dependencies=[Depends(auth)])
def put_pref(key: str, value: dict | list | str | float | int):
    catalog.set_pref(conn(), key, value)
    return catalog.get_pref(conn(), key)


@app.get("/api/garage", dependencies=[Depends(auth)])
def garage():
    c = conn()
    return [dict(r) for r in c.execute("""
        SELECT u.entity_id AS id, v.display_name AS name, u.status FROM user_item_status u
        JOIN visible_entity v ON v.id = u.entity_id
        WHERE u.status IN ('owned','wanted','favorite','lost') ORDER BY v.display_name""")]


@app.put("/api/status/{entity_id:path}", dependencies=[Depends(auth)])
def set_status(entity_id: str, s: StatusIn):
    c = conn()
    with c:
        c.execute("INSERT INTO user_item_status(entity_id,status) VALUES (?,?) "
                  "ON CONFLICT(entity_id) DO UPDATE SET status=excluded.status", (entity_id, s.status))
    return {"id": entity_id, "status": s.status}


_tiles = Path(DB_PATH).resolve().parent / "tiles"
if _tiles.exists():  # zoom 6 du fond de carte (les zooms 0-5 sont embarqués dans l'APK)
    app.mount("/tiles-hd", StaticFiles(directory=_tiles), name="tiles")

_web = Path(__file__).resolve().parents[2] / "web" / "dist"
if _web.exists():
    app.mount("/", StaticFiles(directory=_web, html=True), name="web")
