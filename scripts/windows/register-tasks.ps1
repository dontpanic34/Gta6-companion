# Enregistre 2 tâches planifiées : synchro quotidienne (04:17) et serveur au démarrage de session.
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$daily = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$here\daily.ps1`""
$t1 = New-ScheduledTaskTrigger -Daily -At 4:17am
$set = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 15) -ExecutionTimeLimit (New-TimeSpan -Hours 3)
Register-ScheduledTask -TaskName "GTA6Companion-Sync" -Action $daily -Trigger $t1 -Settings $set -Force | Out-Null

$serve = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$here\serve.ps1`""
$t2 = New-ScheduledTaskTrigger -AtLogOn
$set2 = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit 0
Register-ScheduledTask -TaskName "GTA6Companion-Server" -Action $serve -Trigger $t2 -Settings $set2 -Force | Out-Null
Write-Host "Tâches enregistrées : GTA6Companion-Sync (quotidienne) et GTA6Companion-Server (au démarrage)."
