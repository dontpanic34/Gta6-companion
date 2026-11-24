# Installation sur le PC Windows (à lancer une fois, PowerShell, depuis ce dossier).
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\..\.."
Set-Location "$root\backend"
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install fastapi uvicorn httpx pytest
.\.venv\Scripts\python -m pytest -q
Set-Location "$root\web"
npm install
npm run build
# Jeton d'accès (à saisir aussi dans Réglages sur le téléphone)
if (-not [Environment]::GetEnvironmentVariable("COMPANION_TOKEN", "User")) {
  $tok = -join ((48..57) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
  [Environment]::SetEnvironmentVariable("COMPANION_TOKEN", $tok, "User")
  Write-Host "Jeton créé : $tok  (notez-le pour l'application Android)"
}
Write-Host "Installation terminée. Lancez register-tasks.ps1 pour l'automatisation."
