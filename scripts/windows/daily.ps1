# Tâche quotidienne : sauvegarde, puis synchronisation de toutes les sources.
$ErrorActionPreference = "Continue"
$root = Resolve-Path "$PSScriptRoot\..\.."
Set-Location "$root\backend"
$py = ".\.venv\Scripts\python"
New-Item -ItemType Directory -Force data\logs | Out-Null
$log = "data\logs\daily-$(Get-Date -Format yyyyMMdd).log"
& $py -m companion.backup --db data\companion.db --dir data\backups --keep 30 *>> $log
& $py -m companion.sync --db data\companion.db *>> $log
