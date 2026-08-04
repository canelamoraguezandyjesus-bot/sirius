<#
.SYNOPSIS
    B13 - Verificacion automatica del paquete portatil de Sirius para Windows.

.DESCRIPTION
    Entrada canonica del verificador. La implementacion se divide por fases para
    mantener separadas la localizacion/extraccion, las comprobaciones estaticas,
    las precondiciones, las utilidades de ejecucion y la evidencia de arranque.
    Todas las fases se cargan en este mismo scope y conservan el comportamiento
    del comando unico documentado.
#>

[CmdletBinding()]
param(
    [string]$ArtifactPath = "",
    [int]$StartupTimeoutSeconds = 10
)

$parts = @(
    "verify_windows_package_01_locate_extract.ps1",
    "verify_windows_package_02_static_checks.ps1",
    "verify_windows_package_03_preconditions.ps1",
    "verify_windows_package_035_credential_gate.ps1",
    "verify_windows_package_04_runtime.ps1",
    "verify_windows_package_05_execute.ps1"
)

foreach ($part in $parts) {
    $partPath = Join-Path $PSScriptRoot $part
    if (-not (Test-Path -LiteralPath $partPath -PathType Leaf)) {
        throw "Falta una fase del verificador B13: $partPath"
    }
}

. (Join-Path $PSScriptRoot $parts[0]) `
    -ArtifactPath $ArtifactPath `
    -StartupTimeoutSeconds $StartupTimeoutSeconds
for ($index = 1; $index -lt $parts.Count; $index++) {
    . (Join-Path $PSScriptRoot $parts[$index])
}
