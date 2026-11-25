#!/usr/bin/env bash
# Récupère le fond de carte GTA VI (gtadb.org, CC BY 4.0) via git, comme demandé par
# ses auteurs (« Please do not fetch live data or media from gtadb.org – simply git pull »).
#   zooms 0-5 -> web/public/tiles/day (embarqués dans l'APK, hors ligne)
#   zoom 6    -> backend/data/tiles/day (servi par le PC)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${GTADB_DIR:-$ROOT/.cache/gtadb}"
if [ -d "$SRC/.git" ]; then git -C "$SRC" pull -q; else
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/rolux/gtadb.org "$SRC"
  git -C "$SRC" sparse-checkout set maps/tiles/6/day map/data/6
fi
mkdir -p "$ROOT/web/public/tiles/day" "$ROOT/backend/data/tiles/day"
for z in 0 1 2 3 4 5; do rm -rf "$ROOT/web/public/tiles/day/$z"; cp -r "$SRC/maps/tiles/6/day/$z" "$ROOT/web/public/tiles/day/$z"; done
rm -rf "$ROOT/backend/data/tiles/day/6"; cp -r "$SRC/maps/tiles/6/day/6" "$ROOT/backend/data/tiles/day/6"
cp "$SRC/map/data/6/landmarks.json" "$ROOT/backend/data/gtadb-landmarks.json"
echo "Tuiles prêtes."
