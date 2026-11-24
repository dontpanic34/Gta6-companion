from fastapi.testclient import TestClient

from companion import catalog, classify, db, importer
from companion.connectors import gtabase
from companion.connectors.gtabase import ParsedItem

PAGE = """
<h1>Karin Futo GTA 6</h1>
<ul>
<li class="field-entry manufacturer "><span class="field-label">Manufacturer</span><span class="field-value "> Karin </span></li>
<li class="field-entry vehicle-class "><span class="field-label">Vehicle Class</span><span class="field-value "> Sports </span></li>
<li class="field-entry seats "><span class="field-label">Seats</span><span class="field-value ">2</span></li>
<li class="field-entry drivetrain "><span class="field-label">Drive Train</span><span class="field-value ">RWD</span></li>
<li class="field-entry price-story "><span class="field-label">Price</span><span class="field-value ">$9,500</span></li>
<li class="field-entry speed "><span class="field-value ">6.0</span></li>
<li class="field-entry acceleration "><span class="field-value ">7.5</span></li>
<li class="field-entry asphalt-handling "><span class="field-value ">8.0</span></li>
<li class="field-entry how-to-unlock "><span class="field-label">How</span><span class="field-value ">Reward after completing the mission Big Betrayal</span></li>
</ul>
<p>Karin Futo GTA 6 Location:</strong> Spawns in traffic.</p>
<img src="/images/gta-6/vehicles/sports/karin-futo.jpg">
"""


def items():
    futo = gtabase.parse_item("https://www.gtabase.com/gta-6/vehicles/futo", PAGE, "vehicle")
    muscle = ParsedItem("gauntlet", "u", "vehicle", "Bravado Gauntlet",
                        {"class": "Muscle", "speed": 9.0, "acceleration": 9.0, "handling_road": 4.0})
    unique = ParsedItem("raul-futo", "u2", "vehicle", "Raul's Futo",
                        {"class": "Sports", "speed": 7.0}, base_model_slug="futo")
    return [futo, muscle, unique]


def test_parser_fields():
    it = items()[0]
    assert it.name == "Karin Futo"
    assert it.fields["price"] == 9500 and it.fields["drivetrain"] == "RWD"
    assert it.fields["location_text"] == "Spawns in traffic."
    assert it.images == ["https://www.gtabase.com/images/gta-6/vehicles/sports/karin-futo.jpg"]


def test_classifier_quarantines_narrative_text():
    assert classify.field_spoiler_status("how_to_unlock", "Reward after completing the mission X") == "unknown"
    assert classify.field_spoiler_status("how_to_unlock", "Ultimate Edition") == "evaluated"
    assert classify.field_spoiler_status("location_text", "Spawns in traffic.") == "evaluated"
    assert classify.entity_spoiler_status("vehicle_variant", "Raul's Futo") == "unknown"
    assert classify.field_spoiler_status("mystery_field", 1) == "unknown"


def test_import_variants_history_and_spoilers():
    c = db.connect()
    rep = importer.import_items(c, items())
    assert ("vehicle:futo:std", "how_to_unlock") in rep.quarantined
    names = {v["name"] for v in catalog.vehicles(c)}
    assert names == {"Karin Futo", "Bravado Gauntlet"}  # « Raul's Futo » masqué (nom révélateur)
    d = catalog.vehicle_detail(c, "vehicle:futo:std")
    assert "how_to_unlock" not in d["fields"] and d["hidden_fields"] == 1
    assert d["fields"]["speed"]["kind"] == "community"

    # Changement de valeur : historique conservé, rien supprimé
    changed = items()
    changed[0].fields["price"] = 12000
    rep2 = importer.import_items(c, changed)
    assert rep2.changed == [("vehicle:futo:std", "price")]
    assert c.execute("SELECT COUNT(*) FROM claim WHERE entity_id='vehicle:futo:std' AND field='price'").fetchone()[0] == 2
    assert catalog.vehicle_detail(c, "vehicle:futo:std")["fields"]["price"]["value"] == 12000
    assert c.execute("SELECT COUNT(*) FROM revision WHERE table_name='claim'").fetchone()[0] == 1

    # Source vide (indisponible) : rien ne disparaît
    importer.import_items(c, [])
    assert len(catalog.vehicles(c)) == 2


def test_weighted_ranking_and_filters():
    c = db.connect()
    importer.import_items(c, items())
    w = catalog.get_pref(c, "vehicle_weights")
    ranked = catalog.vehicles(c, weights=w, exclude_classes=["Muscle"])
    assert [v["name"] for v in ranked] == ["Karin Futo"]
    assert ranked[0]["score"]["coverage"] < 1  # stats manquantes signalées, pas inventées
    assert catalog.vehicles(c, min_stats={"handling_road": 7}) [0]["name"] == "Karin Futo"
    assert catalog.vehicles(c, max_price=5000) == []


def test_api_end_to_end(tmp_path, monkeypatch):
    from companion import api
    monkeypatch.setattr(api, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(api, "TOKEN", "secret")
    api._local.conn = None
    importer.import_items(api.conn(), items())
    cl = TestClient(api.app)
    assert cl.get("/api/vehicles").status_code == 401
    h = {"Authorization": "Bearer secret"}
    r = cl.get("/api/vehicles", params={"use_profile": True}, headers=h).json()
    assert [v["name"] for v in r] == ["Karin Futo"]
    assert cl.get("/api/vehicles/vehicle:futo:raul-futo", headers=h).status_code == 404
    assert cl.put("/api/status/vehicle:futo:std", json={"status": "owned"}, headers=h).status_code == 200
    assert cl.get("/api/garage", headers=h).json()[0]["status"] == "owned"
    api._local.conn = None
