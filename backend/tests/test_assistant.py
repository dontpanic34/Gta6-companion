import json

from companion import assistant, db, importer, spoiler
from companion.connectors import gta6map
from companion.connectors.gtabase import ParsedItem
from tests.test_gta6map import CATEGORY, SECRET


def setup():
    c = db.connect()
    importer.import_map_locations(c, gta6map.parse_category("https://gta6map.city/fr/locations/stunt-jump/", CATEGORY))
    importer.import_secrets(c, [gta6map.parse_secret("https://gta6map.city/fr/secrets/x/", SECRET.replace("Mariana County", "Vice City"))])
    importer.import_items(c, [
        ParsedItem("futo", "u", "vehicle", "Karin Futo", {"class": "Sports", "speed": 6, "acceleration": 7.5, "handling_road": 8, "handling_offroad": 5}),
        ParsedItem("gauntlet", "u", "vehicle", "Bravado Gauntlet", {"class": "Muscle", "speed": 9, "acceleration": 9, "handling_road": 4, "handling_offroad": 3}),
        ParsedItem("outlaw", "u", "vehicle", "Mer-Can Outlaw", {"class": "Off-Road", "speed": 3, "acceleration": 6, "handling_road": 3, "handling_offroad": 8.4}),
        ParsedItem("akulus", "u", "weapon", "Akulus", {"class": "Handguns", "damage": 5, "moddable": "Can be modified"}),
        ParsedItem("bat", "u", "weapon", "Bat", {"class": "Melee", "damage": 3, "moddable": "Cannot be modified"}),
    ])
    spoiler.reindex(c)
    return assistant.Assistant(c, None), c


def test_location_question_lists_nearby_without_spoilers():
    a, _ = setup()
    r = a.route("s", "Je suis à Vice City, il y a quoi à faire ?")
    assert "Vice City" in r.text and r.cards
    assert "CANARI" not in json.dumps(r.to_json())          # titre du secret masqué
    assert r.actions[0]["type"] == "open_map"
    # mémoire de session : « autour de moi » réutilise la zone
    assert "Vice City" in a.route("s", "Et autour de moi ?").text


def test_unknown_zone_is_admitted():
    a, _ = setup()
    assert "ne connais pas" in a.route("s", "Je suis sur Atlantide").text


def test_vehicle_queries():
    a, _ = setup()
    r = a.route("s", "Quelles voitures sont meilleures hors route ?")
    assert r.cards[0]["name"] == "Mer-Can Outlaw"
    r = a.route("s", "Je veux une voiture qui ne dérape pas")
    assert "Bravado Gauntlet" not in [c["name"] for c in r.cards]
    r = a.route("s", "Compare-moi la Futo et la Gauntlet")
    assert r.actions[0]["type"] == "open_compare" and len(r.cards) == 2


def test_weapon_attachment_without_data_is_honest():
    a, _ = setup()
    r = a.route("s", "J'ai besoin d'une arme avec un silencieux")
    assert "ne contient pas encore" in r.text
    assert [c["name"] for c in r.cards] == ["Akulus"]        # le bâton (non modifiable, mêlée) est exclu


def test_chat_falls_back_to_rules_without_ollama(monkeypatch):
    a, _ = setup()
    monkeypatch.setattr(a, "ollama_available", lambda: False)
    out = a.chat("s", "Quelles voitures sont meilleures hors route ?")
    assert out["engine"] == "règles" and out["cards"]


def test_chat_with_mocked_ollama_uses_tools(monkeypatch):
    a, _ = setup()
    monkeypatch.setattr(a, "ollama_available", lambda: True)
    calls = iter([
        {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "find_vehicles", "arguments": {"min_handling_offroad": 7, "ignored": 1}}}]},
        {"role": "assistant", "content": "La Mer-Can Outlaw est la meilleure en tout-terrain."},
    ])
    seen = []
    monkeypatch.setattr(a, "_ollama", lambda msgs: (seen.append(msgs), next(calls))[1])
    out = a.chat("s", "meilleur tout-terrain ?")
    assert out["text"].startswith("La Mer-Can Outlaw") and out["cards"][0]["name"] == "Mer-Can Outlaw"
    tool_msg = seen[1][-1]
    assert tool_msg["role"] == "tool" and "donnees_non_fiables" in tool_msg["content"]
