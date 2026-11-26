# Enregistre 2 tâches planifiées : synchro 5 fois par jour et serveur au démarrage de session.
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$daily = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$here\daily.ps1`""
# 5 mises à jour par jour (seul ce qui a changé est relu)
$t1 = @("4:17am", "9:17am", "1:17pm", "5:17pm", "9:17pm") | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ }
$set = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 15) -ExecutionTimeLimit (New-TimeSpan -Hours 3)
Register-ScheduledTask -TaskName "GTA6Companion-Sync" -Action $daily -Trigger $t1 -Settings $set -Force | Out-Null

$serve = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$here\serve.ps1`""
$t2 = New-ScheduledTaskTrigger -AtLogOn
$set2 = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit 0
Register-ScheduledTask -TaskName "GTA6Companion-Server" -Action $serve -Trigger $t2 -Settings $set2 -Force | Out-Null
Write-Host "Tâches enregistrées : GTA6Companion-Sync (5 fois par jour) et GTA6Companion-Server (au démarrage)."
# Pare-feu : autoriser le téléphone du réseau PRIVÉ (Wi-Fi maison) uniquement, port 8765
if (-not (Get-NetFirewallRule -DisplayName "GTA6Companion" -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -DisplayName "GTA6Companion" -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow -Profile Private | Out-Null
}
# Démarrer le serveur tout de suite (sans attendre la prochaine ouverture de session)
Start-ScheduledTask -TaskName "GTA6Companion-Server"
Write-Host "Pare-feu configuré, serveur démarré. Le téléphone le trouvera tout seul sur le Wi-Fi."
