"""Synchronisation : python -m companion.sync --db data/companion.db [--kind vehicle] [--limit N]

Différentielle : le sitemap fournit <lastmod> ; le cache HTTP utilise ETag /
If-Modified-Since ; les pages inchangées ne sont pas réimportées.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import time
from pathlib import Path

from . import db, importer, spoiler
from .connectors import gtabase
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/companion.db")
    ap.add_argument("--cache", default="data/http-cache")
    ap.add_argument("--kind", action="append", choices=["vehicle", "weapon"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--interval", type=float, default=3.0)
    ap.add_argument("--report-dir", default="data/reports")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    Path(a.db).parent.mkdir(parents=True, exist_ok=True)
    conn = db.connect(a.db)
    client = PoliteClient(a.cache, min_interval=a.interval)
    report = sync_gtabase(conn, client, set(a.kind or ["vehicle", "weapon"]), a.limit)
    Path(a.report_dir).mkdir(parents=True, exist_ok=True)
    out = Path(a.report_dir) / f"sync-{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Rapport : %s (créés %d, modifiés %d, quarantaine %d, erreurs %d)", out,
             report["created"], len(report["changed"]), len(report["quarantined"]), len(report["errors"]))


if __name__ == "__main__":
    main()
