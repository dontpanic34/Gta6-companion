# Installation sur le PC Windows (à lancer une fois, PowerShell, depuis ce dossier).
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\..\.."
Set-Location "$root\backend"
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install fastapi uvicorn httpx pytest python-multipart pillow
.\.venv\Scripts\python -m pytest -q
Set-Location "$root\web"
npm install
npm run build
# Fond de carte HD (zoom 6) et repères des quartiers pour l'assistant
& "$PSScriptRoot\fetch-tiles.ps1"
# Jeton d'accès (à saisir aussi dans Réglages sur le téléphone)
if (-not [Environment]::GetEnvironmentVariable("COMPANION_TOKEN", "User")) {
  $tok = -join ((48..57) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
  [Environment]::SetEnvironmentVariable("COMPANION_TOKEN", $tok, "User")
  Write-Host "Jeton créé : $tok  (notez-le pour l'application Android)"
} else {
  Write-Host "Jeton existant : $([Environment]::GetEnvironmentVariable('COMPANION_TOKEN', 'User'))  (à saisir dans l'appli)"
}
# Modèle IA local pour l'assistant (RTX 4080 SUPER 16 Go : 14B quantifié)
if (Get-Command ollama -ErrorAction SilentlyContinue) { ollama pull qwen2.5:14b } else { Write-Host "Ollama absent : l'assistant fonctionnera en mode sans IA." }
# Clé OpenXBL (xbl.io > connexion Microsoft > API key), facultative
if (-not [Environment]::GetEnvironmentVariable("XBL_API_KEY", "User")) {
  $k = Read-Host "Clé OpenXBL (laisser vide pour plus tard)"
  if ($k) { [Environment]::SetEnvironmentVariable("XBL_API_KEY", $k, "User") }
}
Write-Host "Installation terminée. Lancez register-tasks.ps1 pour l'automatisation."
Set-Location $PSScriptRoot
