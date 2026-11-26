# Serveur API + interface web, écoute uniquement sur l'adresse Tailscale et localhost.
$root = Resolve-Path "$PSScriptRoot\..\.."
Set-Location "$root\backend"
# Écoute sur le réseau de la maison (le téléphone en Wi-Fi le trouve tout seul).
# Accès sans jeton depuis le Wi-Fi local ; jeton obligatoire depuis l'extérieur (Tailscale).
& .\.venv\Scripts\python -m uvicorn companion.api:app --host 0.0.0.0 --port 8765
