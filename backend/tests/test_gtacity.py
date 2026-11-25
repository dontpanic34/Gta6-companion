from companion import catalog, db, importer
from companion.connectors import gtacity

SITEMAP = """<urlset><url><loc>https://gtacity.gg/fr/gta-6/vehicules/suvs/kamacho</loc></url>
<url><loc>https://gtacity.gg/fr/gta-6/vehicules/suvs/kamacho/gunrunner-kamacho</loc></url>
<url><loc>https://gtacity.gg/fr/gta-6/vehicules/suvs/kamacho/black-moth-kamacho</loc></url>
<url><loc>https://gtacity.gg/fr/gta-6/vehicules/compare</loc></url></urlset>"""
PAGE = """<script type="application/ld+json">{"@graph":[{"@type":"WebPage","about":{"@type":"Product","name":"Canis Gunrunner Kamacho",
"brand":{"@type":"Brand","name":"Canis"},"additionalProperty":[{"name":"Speed","value":5},{"name":"Off-road","value":7.2},{"name":"Seats","value":4}]}}]}</script>
<dt>Transmission</dt><dd>Transmission intégrale</dd>
<img src="https://assets.codmunity.gg/optimized/gtacity_vehicles_suvs_gta_city_gunrunner_kamacho.webp">"""


def test_index_and_match():
    idx = gtacity.vehicle_index(SITEMAP)
    assert gtacity.find_url(idx, "Canis Gunrunner Kamacho").endswith("/kamacho/gunrunner-kamacho")
    assert gtacity.find_url(idx, "Canis Kamacho").endswith("/suvs/kamacho")
    assert gtacity.find_url(idx, "Pegassi Zentorno") is None


def test_parse_and_import():
    url = "https://gtacity.gg/fr/gta-6/vehicules/suvs/kamacho/gunrunner-kamacho"
    it = gtacity.parse_vehicle(url, PAGE)
    assert it.base_model_slug == "kamacho" and it.fields["handling_offroad"] == 7.2
    assert it.fields["drivetrain"] == "AWD" and it.fields["seats"] == 4 and it.images
    c = db.connect()
    importer.import_items(c, [it], "gtacity"); importer.reclassify_catalog_names(c)
    v = catalog.vehicle_detail(c, "vehicle:kamacho:gunrunner-kamacho")
    assert v["name"] == "Canis Gunrunner Kamacho" and v["media"]
    assert v["fields"]["speed"]["sources"][0]["source"] == "gtacity"
