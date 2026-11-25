import json

from companion import db, importer, translate
from companion.connectors import gtawiki
from companion.connectors.gtabase import ParsedItem

LIST = """<h2 id="Table">Table</h2><table><tr><th>Sports &amp; supercars</th><th>SUVs</th></tr>
<tr><td><a href="/w/Banshee" title="Banshee">Banshee</a></td><td><a href="/w/Category:SUVs" title="Category:SUVs">x</a></td></tr></table>
<h2 id="Gallery">Gallery</h2>"""

PAGE = """<div class="infobox-root"><div class="infobox-subtitle">VEHICLE</div>
<div class="infobox-image"><img src="/images/thumb/Banshee-GTAVI.png/300px-Banshee-GTAVI.png?x"></div>
<div class="infobox-row-container"><div class="infobox-row-label">Appears in</div>
<div class="infobox-row-value"><i>Grand Theft Auto IV</i> <i>Grand Theft Auto VI</i></div></div>
<div class="infobox-row-container"><div class="infobox-row-label">Type</div>
<div class="infobox-row-value">Sports car</div></div>
<div class="infobox-row-container"><div class="infobox-row-label">Manufacturer</div>
<div class="infobox-row-value">Bravado</div></div>
<div class="infobox-row-container"><div class="infobox-row-label">Capacity</div>
<div class="infobox-row-value">2 (driver and passenger)</div></div></div>
<h2 id="Design">Design</h2><p><span class="h3-dummy"><i>Grand Theft Auto IV</i></span>Old GTA IV design text here.</p>
<p><span class="h3-dummy"><i>Grand Theft Auto VI</i></span>A sleek roadster design for Leonida.</p>
<h2 id="Gallery">Gallery</h2>"""


def test_index_and_parse_gta6_only():
    idx = gtawiki.vehicle_index(LIST)
    assert idx == [("Banshee", "https://gta.wiki/w/Banshee", "Sports & supercars")]
    it = gtawiki.parse_item("Banshee", idx[0][1], "vehicle", PAGE, idx[0][2])
    assert it.fields["manufacturer"] == "Bravado" and it.fields["seats"] == 2
    assert it.texts["design_en"] == "A sleek roadster design for Leonida."   # pas le texte GTA IV
    assert it.image == "https://gta.wiki/images/Banshee-GTAVI.png"
    assert gtawiki.parse_item("Bravado", "u", "vehicle", PAGE.replace("VEHICLE", "MANUFACTURER")) is None


def test_import_merges_with_existing_and_translates():
    c = db.connect()
    importer.import_items(c, [ParsedItem("banshee", "u", "vehicle", "Bravado Banshee", {"class": "Sports", "speed": 7})])
    it = gtawiki.parse_item("Banshee", "https://gta.wiki/w/Banshee", "vehicle", PAGE, "Sports & supercars")
    importer.import_wiki_items(c, [it])
    assert c.execute("SELECT COUNT(*) FROM entity WHERE kind='vehicle_variant'").fetchone()[0] == 1   # fusionné
    assert c.execute("SELECT 1 FROM claim WHERE entity_id='vehicle:banshee:std' AND field='design_en'").fetchone()
    n = translate.run(c, translator=lambda t: "Un roadster élégant pour Leonida.")
    assert n == 1
    fr = c.execute("SELECT value_json FROM claim WHERE entity_id='vehicle:banshee:std' AND field='design'").fetchone()[0]
    assert json.loads(fr).startswith("Un roadster")
    assert translate.run(c, translator=lambda t: "x") == 0   # pas de double traduction
