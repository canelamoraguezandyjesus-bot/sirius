$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv no esta instalado. Instala uv y vuelve a ejecutar este script."
}

uv python install 3.14.6
uv sync --all-groups
Write-Host "Sirius preparado. Se ha generado uv.lock; incluyelo en el primer commit."
Write-Host "Ejecuta: uv run sirius"
