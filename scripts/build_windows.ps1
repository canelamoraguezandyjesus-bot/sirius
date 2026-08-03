<#
.SYNOPSIS
    B13 - Entrada canonica y segura del empaquetado de Sirius 0.1 para Windows.

.DESCRIPTION
    Valida que el entorno dedicado de empaquetado quede fuera del checkout antes
    de derivar ejecutables del entorno, asignar UV_PROJECT_ENVIRONMENT, crear
    directorios o ejecutar uv sync. Solo despues delega en la implementacion
    interna del build.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$GuardScript = Join-Path $PSScriptRoot "packaging_path_guard.py"
$ImplementationScript = Join-Path $PSScriptRoot "build_windows_impl.ps1"

if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    throw "No esta definida LOCALAPPDATA; no se puede ubicar el entorno de empaquetado."
}

# Esta es la unica derivacion permitida antes de la guarda. No se crean rutas,
# no se deriva ningun ejecutable, no se asigna UV_PROJECT_ENVIRONMENT y no se
# invoca uv hasta que packaging_path_guard.py confirme la contencion.
$PackagingVenv = Join-Path $env:LOCALAPPDATA "Sirius\packaging-venv"

if (-not (Test-Path -LiteralPath $GuardScript -PathType Leaf)) {
    throw "Falta el validador de ruta de empaquetado: $GuardScript"
}
if (-not (Test-Path -LiteralPath $ImplementationScript -PathType Leaf)) {
    throw "Falta la implementacion interna del build: $ImplementationScript"
}

$PythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
$PythonPrefix = @()
if ($null -eq $PythonCommand) {
    $PythonCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    $PythonPrefix = @("-3.14")
}
if ($null -eq $PythonCommand) {
    throw "BLOCKED_EXTERNAL_TOOLCHAIN: no se encontro python.exe ni py.exe para ejecutar la guarda de ruta."
}

$guardOutput = (& $PythonCommand.Source @PythonPrefix $GuardScript $RepoRoot $PackagingVenv | Out-String).Trim()
$guardExit = $LASTEXITCODE
if ([string]::IsNullOrWhiteSpace($guardOutput)) {
    throw "La guarda de ruta no produjo un resultado verificable."
}

try {
    $guardResult = $guardOutput | ConvertFrom-Json
}
catch {
    throw "La guarda de ruta devolvio una respuesta no valida: $guardOutput"
}

if ($guardExit -ne 0 -or -not [bool]$guardResult.ok) {
    $guardMessage = if ($null -ne $guardResult.error) { [string]$guardResult.error } else { "ruta rechazada" }
    throw "Entorno de empaquetado no permitido: $guardMessage"
}

Write-Host "  [ok] Ruta de empaquetado validada antes de cualquier sincronizacion: $($guardResult.packaging_path)" -ForegroundColor Green

# La implementacion contiene la carga de MSVC, la sincronizacion de dependencias,
# Nuitka, el montaje, los manifiestos y el ZIP. Al llegar aqui la precondicion
# peligrosa ya esta cerrada.
& $ImplementationScript
