from companion import db, importer, spoiler
from companion.connectors import gta6map

CATEGORY = """
<script type="application/ld+json">{"itemListElement":[{"@type":"ListItem","position":3,"name":"Saut spectaculaire","item":"https://gta6map.city/fr/locations/stunt-jump/"}]}</script>
<h2>Vice City <small>2</small></h2><ul class="rows">
<li><span><a rel="nofollow" href="/fr/?m=Cio-stunt-jump--1667_-712">Banner Hotel &amp; Spa Parking Stunt Jump</a><span class="d">à environ 106 m de « Banner Hotel »</span></span><small>Salton</small></li>
<li><span><a rel="nofollow" href="/fr/?m=Pg6asjl022">Apollo Aggregates South</a></span><small>Balsero</small></li>
</ul>
"""

SECRET = """
<p class="eyebrow">GTA 6 · Créatures et rencontres</p>
<h1>Quête CANARI qui se termine par un fusil unique</h1>
<div class="tags"><span class="tag hot">Signalé par des joueurs</span><span class="tag">Montré par 3 créateurs</span><span class="tag">Zone</span><span class="tag">Mariana County</span></div>
<a class="hero" rel="nofollow" href="/fr/?m=s-x"><img src="/img/s/x.jpg" alt=""></a>
<h2><span data-nosnippet>Où le trouver</span></h2><p>Marais au sud-ouest de Hamlet, la nuit.</p>
<h2><span data-nosnippet>De quoi s’agit-il</span></h2><p>Une créature CANARI.</p>
"""

SECRET_SPOILER_WHERE = SECRET.replace("Marais au sud-ouest de Hamlet, la nuit.",
                                      "Après avoir terminé la mission finale, allez au phare.")


def test_parse_category_and_coords():
    locs = gta6map.parse_category("https://gta6map.city/fr/locations/stunt-jump/", CATEGORY)
    assert len(locs) == 2
    assert locs[0].name == "Banner Hotel & Spa Parking Stunt Jump"
    assert (locs[0].x, locs[0].y) == (-1667.0, -712.0)
    assert locs[0].region == "Vice City" and locs[0].category_name == "Saut spectaculaire"
    assert locs[1].x is None


def test_parse_secret_fields():
    s = gta6map.parse_secret("https://gta6map.city/fr/secrets/x/", SECRET)
    assert s.precision == "zone" and s.region == "Mariana County"
    assert s.creators == 3 and s.reliability == "probable"
    assert s.where.startswith("Marais") and "créature" in s.what


def test_secret_import_is_spoiler_safe():
    c = db.connect()
    importer.import_secrets(c, [gta6map.parse_secret("https://gta6map.city/fr/secrets/x/", SECRET)])
    spoiler.reindex(c)
    e = spoiler.get_entity(c, "secret:x")
    assert e["name"] == "Créatures et rencontres — Mariana County"
    assert [x["body"] for x in e["content"]] == ["Marais au sud-ouest de Hamlet, la nuit."]
    assert e["media"] == []  # miniature non vérifiée
    assert "CANARI" not in str(e) and spoiler.search(c, "fusil") == []
    spoiler.reveal_next_hint(c, "secret:x")
    assert "créature" in str(spoiler.get_entity(c, "secret:x")["content"])


def test_secret_with_narrative_location_is_quarantined():
    c = db.connect()
    rep = importer.import_secrets(c, [gta6map.parse_secret("https://gta6map.city/fr/secrets/y/", SECRET_SPOILER_WHERE)])
    assert ("secret:y", "entity") in rep.quarantined
    assert spoiler.get_entity(c, "secret:y") is None


def test_map_locations_import():
    c = db.connect()
    importer.import_map_locations(c, gta6map.parse_category("https://gta6map.city/fr/locations/stunt-jump/", CATEGORY))
    assert c.execute("SELECT COUNT(*) FROM visible_location").fetchone()[0] == 1
    assert {e["display_name"] for e in spoiler.list_visible(c, "location")} == {
        "Banner Hotel & Spa Parking Stunt Jump", "Apollo Aggregates South"}
