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

from . import catalog, db, spoiler

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


@app.get("/api/vehicles/{entity_id:path}", dependencies=[Depends(auth)])
def get_vehicle(entity_id: str):
    d = catalog.vehicle_detail(conn(), entity_id)
    if not d:
        raise HTTPException(404, "Introuvable ou masqué par la protection anti-spoiler")
    return d


@app.get("/api/entity/{entity_id:path}", dependencies=[Depends(auth)])
def get_entity(entity_id: str):
    d = spoiler.get_entity(conn(), entity_id)
    if not d:
        raise HTTPException(404, "Introuvable ou masqué par la protection anti-spoiler")
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


_web = Path(__file__).resolve().parents[2] / "web" / "dist"
if _web.exists():
    app.mount("/", StaticFiles(directory=_web, html=True), name="web")
