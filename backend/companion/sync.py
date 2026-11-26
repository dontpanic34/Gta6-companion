"""Synchronisation : python -m companion.sync --db data/companion.db [--kind vehicle] [--limit N]

Différentielle : le sitemap fournit <lastmod> ; le cache HTTP utilise ETag /
If-Modified-Since ; les pages inchangées ne sont pas réimportées.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import re
import time
from pathlib import Path

from . import db, importer, spoiler
from .connectors import gta6map, gtabase, gtawiki
from .http import PoliteClient

log = logging.getLogger("sync")


def sync_gtabase(conn, client: PoliteClient, kinds: set[str], limit: int | None) -> dict:
    index = client.get(gtabase.SITEMAP_INDEX).text
    sub = [u for u in gtabase.parse_sitemap(index) if ".en-GB." in u]
    urls: list[str] = []
    for s in sub:
        try:
            urls += gtabase.parse_sitemap(client.get(s, max_age=20 * 3600).text)
        except Exception as e:  # une sous-carte en panne ne bloque pas les autres
            log.warning("Sitemap %s indisponible : %s", s, e)
    targets = [(k, u) for k, u in gtabase.item_urls(urls) if k in kinds]
    if limit:
        targets = targets[:limit]
    log.info("%d fiches à vérifier", len(targets))

    parsed, errors, unchanged = [], [], 0
    for i, (kind, url) in enumerate(targets, 1):
        try:
            r = client.get(url, max_age=20 * 3600)
            parsed.append(gtabase.parse_item(url, r.text, kind))
            unchanged += (not r.changed)
        except Exception as e:
            errors.append((url, str(e)))
            log.warning("Échec %s : %s", url, e)
        if i % 25 == 0:
            log.info("%d/%d", i, len(targets))

    rep = importer.import_items(conn, parsed, "gtabase")
    spoiler.reindex(conn)
    return {"source": "gtabase", "checked": len(targets), "parsed": len(parsed),
            "unchanged_pages": unchanged, "errors": errors, "created": len(rep.created),
            "changed": rep.changed, "quarantined": rep.quarantined}


def sync_gta6map(conn, client: PoliteClient, limit: int | None) -> dict:
    errors: list = []
    # 1) Lieux issus de la carte du jeu
    locs = []
    cats = gta6map.category_urls(client.get(gta6map.LOCATIONS_INDEX, max_age=20 * 3600).text)
    for u in cats[:limit] if limit else cats:
        try:
            locs += gta6map.parse_category(u, client.get(u, max_age=20 * 3600).text)
        except Exception as e:
            errors.append((u, str(e)))
    # 2) Secrets (index + pages de regroupement)
    items, hubs = gta6map.secret_links(client.get(gta6map.SECRETS_INDEX, max_age=6 * 3600).text)
    seen_hubs: set[str] = set()
    while hubs:
        h = hubs.pop()
        if h in seen_hubs:
            continue
        seen_hubs.add(h)
        try:
            more, more_hubs = gta6map.secret_links(client.get(h, max_age=6 * 3600).text)
            items += more
            hubs += more_hubs
        except Exception as e:
            errors.append((h, str(e)))
    items = sorted(set(items))
    if limit:
        items = items[:limit]
    secrets = []
    for u in items:
        try:
            secrets.append(gta6map.parse_secret(u, client.get(u, max_age=20 * 3600).text))
        except Exception as e:
            errors.append((u, str(e)))
    r1 = importer.import_map_locations(conn, locs)
    r2 = importer.import_secrets(conn, secrets)
    importer.requarantine_sensitive(conn)
    from . import gazetteer
    importer.geocode_unplaced(conn, gazetteer.build(conn, Path(conn.execute("PRAGMA database_list").fetchone()[2]).parent / "gtadb-landmarks.json"))
    spoiler.reindex(conn)
    return {"source": "gta6map", "locations": len(locs), "secrets": len(secrets), "errors": errors,
            "created": len(r1.created) + len(r2.created), "changed": r1.changed + r2.changed,
            "quarantined": r1.quarantined + r2.quarantined}


def sync_gtawiki(conn, client: PoliteClient, kinds: set[str], limit: int | None) -> dict:
    targets = []
    if "vehicle" in kinds:
        targets += [("vehicle",) + t for t in gtawiki.vehicle_index(client.get(gtawiki.VEHICLE_INDEX, max_age=20 * 3600).text)]
    if "weapon" in kinds:
        targets += [("weapon",) + t for t in gtawiki.vehicle_index(client.get(gtawiki.WEAPON_INDEX, max_age=20 * 3600).text)]
    if limit:
        targets = targets[:limit]
    items, errors, skipped = [], [], 0
    for i, (kind, title, url, group) in enumerate(targets, 1):
        try:
            it = gtawiki.parse_item(title, url, kind, client.get(url, max_age=20 * 3600).text, group)
            (items.append(it) if it else None); skipped += it is None
        except Exception as e:
            errors.append((url, str(e)))
        if i % 25 == 0:
            log.info("gtawiki %d/%d", i, len(targets))
    rep = importer.import_wiki_items(conn, items)
    try:
        ms = gtawiki.parse_missions(client.get(gtawiki.MISSIONS_INDEX, max_age=20 * 3600).text)
        importer.import_missions(conn, ms)
    except Exception as e:
        errors.append((gtawiki.MISSIONS_INDEX, str(e)))
    spoiler.reindex(conn)
    return {"source": "gtawiki", "checked": len(targets), "parsed": len(items), "not_gta6": skipped, "errors": errors,
            "created": len(rep.created), "changed": rep.changed, "quarantined": rep.quarantined}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/companion.db")
    ap.add_argument("--cache", default="data/http-cache")
    ap.add_argument("--source", action="append", choices=["gtabase", "gta6map", "gtawiki"])
    ap.add_argument("--kind", action="append", choices=["vehicle", "weapon"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--interval", type=float, default=3.0)
    ap.add_argument("--report-dir", default="data/reports")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)  # stdout : PowerShell n'affiche pas d'erreur rouge
    Path(a.db).parent.mkdir(parents=True, exist_ok=True)
    conn = db.connect(a.db)
    client = PoliteClient(a.cache, min_interval=a.interval)
    Path(a.report_dir).mkdir(parents=True, exist_ok=True)
    sources = a.source or ["gtabase", "gta6map", "gtawiki"]
    for src in sources:
        try:  # une source en échec n'empêche pas les autres
            kinds = set(a.kind or ["vehicle", "weapon"])
            report = (sync_gtabase(conn, client, kinds, a.limit) if src == "gtabase"
                      else sync_gtawiki(conn, client, kinds, a.limit) if src == "gtawiki"
                      else sync_gta6map(conn, client, a.limit))
        except Exception as e:
            log.exception("Source %s en échec", src)
            report = {"source": src, "fatal": str(e), "created": 0, "changed": [], "quarantined": [], "errors": []}
        importer.protect_story_names(conn)   # après chaque source : aucun nom protégé dans un texte affiché
        out = Path(a.report_dir) / f"sync-{src}-{time.strftime('%Y%m%d-%H%M%S')}.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("%s : rapport %s (créés %d, modifiés %d, quarantaine %d, erreurs %d)", src, out,
                 report["created"], len(report["changed"]), len(report["quarantined"]), len(report["errors"]))


if __name__ == "__main__":
    main()
