# Récupère le fond de carte GTA VI (gtadb.org, CC BY 4.0) via git, comme le demandent ses auteurs.
#   zoom 6 -> backend\data\tiles\day\6 (servi par le PC) ; repères des quartiers -> backend\data\gtadb-landmarks.json
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\..\.."
$src = Join-Path $root ".cache\gtadb"
if (Test-Path (Join-Path $src ".git")) { git -C $src pull -q }
else {
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/rolux/gtadb.org $src
  git -C $src sparse-checkout set maps/tiles/6/day/6 map/data/6
}
$data = Join-Path $root "backend\data"
New-Item -ItemType Directory -Force (Join-Path $data "tiles\day") | Out-Null
$dst = Join-Path $data "tiles\day\6"
if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
Copy-Item -Recurse (Join-Path $src "maps\tiles\6\day\6") $dst
Copy-Item (Join-Path $src "map\data\6\landmarks.json") (Join-Path $data "gtadb-landmarks.json") -Force
Write-Host "Fond de carte HD et repères prêts."
