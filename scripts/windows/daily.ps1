# Tâche quotidienne : sauvegarde, puis synchronisation de toutes les sources.
$ErrorActionPreference = "Continue"
$root = Resolve-Path "$PSScriptRoot\..\.."
Set-Location "$root\backend"
$py = ".\.venv\Scripts\python"
New-Item -ItemType Directory -Force data\logs | Out-Null
$log = "data\logs\daily-$(Get-Date -Format yyyyMMdd).log"
& $py -m companion.backup --db data\companion.db --dir data\backups --keep 30 *>> $log
& $py -m companion.sync --db data\companion.db *>> $log
# Succès Xbox (si la clé OpenXBL est configurée)
if ($env:XBL_API_KEY) { & $py -c "from companion import db, xbox; print(xbox.sync(db.connect('data/companion.db')))" *>> $log }
# Traduction FR des textes anglais (Ollama local)
& $py -m companion.translate --db data\companion.db *>> $log
# Instantané hors ligne pour la prochaine version de l'APK
& $py -m companion.export --db data\companion.db --out ..\web\public\data\snapshot.json *>> $log
