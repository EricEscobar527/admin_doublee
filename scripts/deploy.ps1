# Actualiza el VPS con lo último de GitHub (rama main) y reinicia los contenedores.
# Uso: .\scripts\deploy.ps1 -Server 123.45.67.89
# Solo despliega lo que ya está en GitHub: haz commit y push antes. .env, imágenes y base no se tocan.
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [string]$User = "root",
    [string]$Path = "/opt/admin-doublee"
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (git status --porcelain) { Write-Warning "Hay cambios sin commit; no se van a desplegar." }
git fetch origin main --quiet
if (git log origin/main..HEAD --oneline) { Write-Warning "Hay commits sin push; haz 'git push' para desplegarlos." }

ssh "$User@$Server" "cd $Path && git pull --ff-only && docker compose -f docker-compose.prod.yml up -d --build --remove-orphans && docker compose -f docker-compose.prod.yml ps"
