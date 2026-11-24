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
    assert classify.name_status("vehicle_variant", "Raul's Futo") == "unknown"
    assert classify.name_status("vehicle_variant", "Karin Futo") == "safe"
    assert classify.field_spoiler_status("mystery_field", 1) == "unknown"


def test_import_variants_history_and_spoilers():
    c = db.connect()
    rep = importer.import_items(c, items())
    assert ("vehicle:futo:std", "how_to_unlock") in rep.quarantined
    names = {v["name"] for v in catalog.vehicles(c)}
    # « Raul's Futo » : visible, mais sous un nom neutre (le vrai révèle un personnage)
    assert names == {"Karin Futo", "Bravado Gauntlet", "Véhicule unique — Karin Futo"}
    assert "Raul" not in str(catalog.vehicles(c))
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
    assert len(catalog.vehicles(c)) == 3


def test_weighted_ranking_and_filters():
    c = db.connect()
    importer.import_items(c, items())
    w = catalog.get_pref(c, "vehicle_weights")
    ranked = catalog.vehicles(c, weights=w, exclude_classes=["Muscle"])
    assert [v["name"] for v in ranked] == ["Karin Futo", "Véhicule unique — Karin Futo"]
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
    assert [v["name"] for v in r][0] == "Karin Futo" and "Bravado Gauntlet" not in str(r)
    raul = cl.get("/api/vehicles/vehicle:futo:raul-futo", headers=h).json()
    assert raul["name"] == "Véhicule unique — Karin Futo" and raul["media"] == []
    assert cl.put("/api/status/vehicle:futo:std", json={"status": "owned"}, headers=h).status_code == 200
    assert cl.get("/api/garage", headers=h).json()[0]["status"] == "owned"
    api._local.conn = None


def test_api_places_and_reveal(tmp_path, monkeypatch):
    from companion import api
    from companion.connectors import gta6map
    from tests.test_gta6map import CATEGORY, SECRET
    monkeypatch.setattr(api, "DB_PATH", str(tmp_path / "p.db"))
    monkeypatch.setattr(api, "TOKEN", None)
    api._local.conn = None
    c = api.conn()
    importer.import_map_locations(c, gta6map.parse_category("https://gta6map.city/fr/locations/stunt-jump/", CATEGORY))
    importer.import_secrets(c, [gta6map.parse_secret("https://gta6map.city/fr/secrets/x/", SECRET)])
    cl = TestClient(api.app)
    assert len(cl.get("/api/places", params={"region": "Vice City"}).json()) == 2
    sec = cl.get("/api/places", params={"secrets_only": True}).json()
    assert [s["name"] for s in sec] == ["Créatures et rencontres — Mariana County"]
    facets = cl.get("/api/places/facets").json()
    assert {"name": "Vice City", "n": 2} in facets["regions"]
    assert cl.post("/api/entity/secret:x/reveal-name").status_code == 400
    assert "CANARI" in cl.post("/api/entity/secret:x/reveal-name", params={"confirm": True}).json()["name"]
    api._local.conn = None


def test_weapons_variants_and_free_filter():
    c = db.connect()
    sms = ParsedItem("sms-01", "u", "weapon", "Shrewsbury SMS-01",
                     {"class": "Sniper Rifles", "damage": 6.8, "accuracy": 8.6, "price": 2150, "purchase_from": "Ammu-Nation"})
    gun_nut = ParsedItem("gun-nut-sms-01", "u2", "weapon", "Gun Nut SMS-01",
                         {"class": "Sniper Rifles", "damage": 7.2, "how_to_unlock": "Ultimate Edition"},
                         base_model_slug="sms-01")
    importer.import_items(c, [sms, gun_nut])
    names = [w["name"] for w in catalog.weapons(c)]
    assert names == ["Gun Nut SMS-01", "Shrewsbury SMS-01"]
    assert [w["name"] for w in catalog.weapons(c, free_only=True)] == ["Gun Nut SMS-01"]
    d = catalog.item_detail(c, "weapon:sms-01:gun-nut-sms-01")
    assert d["variant_type"] == "named" and [s["name"] for s in d["siblings"]] == ["Shrewsbury SMS-01"]
    ranked = catalog.weapons(c, weights={"damage": 1})
    assert ranked[0]["name"] == "Gun Nut SMS-01"
