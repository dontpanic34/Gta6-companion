# Serveur API + interface web, écoute uniquement sur l'adresse Tailscale et localhost.
$root = Resolve-Path "$PSScriptRoot\..\.."
Set-Location "$root\backend"
$ts = (& tailscale ip -4 2>$null | Select-Object -First 1)
$hostIp = if ($ts) { $ts } else { "127.0.0.1" }
& .\.venv\Scripts\python -m uvicorn companion.api:app --host $hostIp --port 8765
