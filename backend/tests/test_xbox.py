import io
import json

from companion import db, xbox


class Fake:
    def __init__(self, routes): self.routes = routes
    def __call__(self, req, timeout=0):
        path = req.full_url.split("/api/v2", 1)[1]
        assert req.headers.get("X-authorization") == "k"
        return io.BytesIO(json.dumps(self.routes[path]).encode())


ROUTES = {
    "/achievements": {"titles": [{"name": "Forza", "titleId": 1}, {"name": "Grand Theft Auto VI", "titleId": 42}]},
    "/achievements/title/42": {"achievements": [
        {"id": "1", "name": "Bienvenue à Leonida", "description": "Terminer le prologue", "progressState": "Achieved",
         "progression": {"timeUnlocked": "2026-11-20T10:00:00Z"}},
        {"id": "2", "name": "CANARI Trahison finale", "description": "CANARI", "progressState": "NotStarted"},
    ]},
}


def test_sync_hides_locked_names_and_maps_progress():
    c = db.connect()
    c.execute("INSERT INTO xbox_achievement(id,title_id,name,progress_json) VALUES ('1','42','x','{\"chapter\": 2}')"); c.commit()
    out = xbox.sync(c, key="k", opener=Fake(ROUTES))
    assert out["ok"] and out["title_id"] == "42" and out["new_unlocked"] == 1
    assert out["unlocked_count"] == 1 and out["locked_count"] == 1
    assert "CANARI" not in json.dumps(out)
    assert c.execute("SELECT chapter FROM progress_state").fetchone()[0] == 2


def test_missing_key():
    assert not xbox.sync(db.connect(), key=None)["ok"]
