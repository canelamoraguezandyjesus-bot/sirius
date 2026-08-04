<#
.SYNOPSIS
    B13 - Entrada canonica y segura del empaquetado de Sirius 0.1 para Windows.

.DESCRIPTION
    Acredita el checkout limpio, valida las rutas peligrosas, crea un worktree
    temporal detached del commit capturado y delega toda la construccion en esa
    instantanea. El checkout original solo controla el proceso y recibe al final
    los artefactos ya validados.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ControllerRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$GuardScript = Join-Path $PSScriptRoot "packaging_path_guard.py"
$SnapshotHelper = Join-Path $PSScriptRoot "package_snapshot.py"

if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    throw "No esta definida LOCALAPPDATA; no se puede ubicar el entorno de empaquetado."
}
if ([string]::IsNullOrWhiteSpace($env:TEMP)) {
    throw "No esta definida TEMP; no se puede crear el snapshot privado."
}

# Solo se derivan rutas. No se crea nada, no se invoca uv y no se obtiene ningun
# ejecutable del entorno de packaging antes de que ambas rutas sean validadas.
$PackagingVenv = Join-Path $env:LOCALAPPDATA "Sirius\packaging-venv"
$SnapshotContainer = Join-Path $env:TEMP ("Sirius-B13-" + [guid]::NewGuid().ToString("N"))
$SnapshotRoot = Join-Path $SnapshotContainer "snapshot"

foreach ($required in @($GuardScript, $SnapshotHelper)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Falta un controlador necesario del build: $required"
    }
}

$PythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
$PythonPrefix = @()
if ($null -eq $PythonCommand) {
    $PythonCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    $PythonPrefix = @("-3.14")
}
if ($null -eq $PythonCommand) {
    throw "BLOCKED_EXTERNAL_TOOLCHAIN: no se encontro python.exe ni py.exe para ejecutar las guardas."
}

function Invoke-JsonController {
    param([string]$Script, [string[]]$Arguments, [string]$What)
    $raw = (& $PythonCommand.Source @PythonPrefix $Script @Arguments | Out-String).Trim()
    $exitCode = $LASTEXITCODE
    if ([string]::IsNullOrWhiteSpace($raw)) { throw "$What no produjo un resultado verificable." }
    try { $result = $raw | ConvertFrom-Json }
    catch { throw "$What devolvio una respuesta no valida: $raw" }
    if ($exitCode -ne 0 -or -not [bool]$result.ok) {
        $detail = if ($null -ne $result.error) { [string]$result.error } else { "comprobacion rechazada" }
        throw "$What fallo: $detail"
    }
    return $result
}

function Preserve-FailedBuildDiagnostics {
    <# Copia solo diagnosticos tecnicos conocidos fuera del snapshot antes de
       eliminarlo. Nunca copia el volcado completo de entorno ni el artefacto. #>
    param(
        [string]$Snapshot,
        [string]$Controller,
        [string]$CommitShort,
        [string]$FailureText
    )

    $source = Join-Path $Snapshot "build\packaging"
    if (-not (Test-Path -LiteralPath $source -PathType Container)) { return "" }

    $candidates = @(Get-ChildItem -LiteralPath $source -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -like "build-*.log" -or
            $_.Name -like "nuitka-crash-report-*.xml" -or
            $_.Name -eq "pyside6-deploy-dry-run.txt"
        })
    if ($candidates.Count -eq 0) { return "" }

    $stamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
    $destination = Join-Path $Controller (
        "build\packaging-diagnostics\$CommitShort\$stamp-" + [guid]::NewGuid().ToString("N"))
    $copyFailures = New-Object System.Collections.Generic.List[string]
    $copied = 0

    try {
        New-Item -ItemType Directory -Path $destination -Force -ErrorAction Stop | Out-Null
    }
    catch {
        [Console]::Error.WriteLine(
            "B13 DIAGNOSTICS ERROR: no se pudo crear '$destination': $($_.Exception.Message)")
        return ""
    }

    foreach ($candidate in $candidates) {
        try {
            Copy-Item -LiteralPath $candidate.FullName -Destination $destination -Force -ErrorAction Stop
            $copied++
        }
        catch {
            $copyFailures.Add("$($candidate.Name): $($_.Exception.Message)")
        }
    }

    try {
        $failurePath = Join-Path $destination "failure.txt"
        [System.IO.File]::WriteAllText(
            $failurePath,
            $FailureText + [Environment]::NewLine,
            (New-Object System.Text.UTF8Encoding($false)))
        $copied++
    }
    catch {
        $copyFailures.Add("failure.txt: $($_.Exception.Message)")
    }

    foreach ($copyFailure in $copyFailures) {
        [Console]::Error.WriteLine("B13 DIAGNOSTICS ERROR: $copyFailure")
    }
    if ($copied -eq 0) {
        try { Remove-Item -LiteralPath $destination -Recurse -Force -ErrorAction Stop }
        catch { [Console]::Error.WriteLine("B13 DIAGNOSTICS ERROR: $($_.Exception.Message)") }
        return ""
    }
    return $destination
}

# El commit y los unicos metadatos de Git que necesita el manifiesto se capturan
# mientras el checkout original todavia es la unica fuente disponible.
$source = Invoke-JsonController $SnapshotHelper @("capture", $ControllerRoot) "Captura del checkout"
$SourceCommit = [string]$source.commit
$SourceCommitShort = [string]$source.commit_short
$SourceBranch = [string]$source.branch
$OriginMainCommit = [string]$source.origin_main
$DescendsFromOriginMain = [bool]$source.descends_from_origin_main

# Se conserva y se aplica primero la guarda de LOCALAPPDATA. La misma guarda
# impide ademas que el worktree temporal caiga dentro del checkout vivo.
$packagingGuard = Invoke-JsonController $GuardScript @($ControllerRoot, $PackagingVenv) "Guarda de LOCALAPPDATA"
$snapshotGuard = Invoke-JsonController $GuardScript @($ControllerRoot, $SnapshotRoot) "Guarda del snapshot"
Write-Host "  [ok] Ruta de empaquetado validada: $($packagingGuard.packaging_path)" -ForegroundColor Green
Write-Host "  [ok] Ruta temporal del snapshot validada: $($snapshotGuard.packaging_path)" -ForegroundColor Green

# Una sola construccion puede usar este destino de publicacion a la vez. El
# FileStream con FileShare.None coordina procesos y sesiones de Windows mediante
# el propio sistema de archivos. El archivo marcador puede quedar tras cerrar el
# proceso; eso no es un bloqueo obsoleto, porque la exclusividad depende del
# handle abierto y se libera automaticamente si el proceso termina.
$PublishDestinationRoot = Join-Path $ControllerRoot "dist\windows"
$PublicationLockPath = Join-Path $PublishDestinationRoot ".b13-publish.lock"
$PublicationLockStream = $null
try {
    New-Item -ItemType Directory -Path $PublishDestinationRoot -Force -ErrorAction Stop | Out-Null
    $PublicationLockStream = [System.IO.File]::Open(
        $PublicationLockPath,
        [System.IO.FileMode]::OpenOrCreate,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None)
}
catch [System.IO.IOException] {
    throw ("Ya hay otra construccion de B13 usando el destino '$PublishDestinationRoot', " +
        "o no se pudo adquirir su bloqueo exclusivo '$PublicationLockPath'. " +
        "La publicacion concurrente se rechaza para no mezclar ni restaurar artefactos de otra ejecucion.")
}
catch {
    if ($null -ne $PublicationLockStream) { $PublicationLockStream.Dispose() }
    throw
}
Write-Host "  [ok] Bloqueo exclusivo de publicacion adquirido: $PublicationLockPath" -ForegroundColor Green

$BuildFailure = $null
try {
    New-Item -ItemType Directory -Path $SnapshotContainer | Out-Null
    & git -C $ControllerRoot worktree add --detach $SnapshotRoot $SourceCommit
    if ($LASTEXITCODE -ne 0) { throw "git worktree add fallo con codigo $LASTEXITCODE." }

    $actualSnapshotCommit = (& git -C $SnapshotRoot rev-parse HEAD | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $actualSnapshotCommit -ne $SourceCommit) {
        throw "El worktree no corresponde exactamente al commit capturado $SourceCommit."
    }

    $SnapshotImplementation = Join-Path $SnapshotRoot "scripts\build_windows_impl.ps1"
    if (-not (Test-Path -LiteralPath $SnapshotImplementation -PathType Leaf)) {
        throw "El snapshot no contiene la implementacion versionada del build."
    }

    # Desde aqui toda fuente, configuracion, modulo y salida intermedia procede
    # del snapshot. El checkout vivo solo se comunica como destino de publicacion.
    & $SnapshotImplementation `
        -SnapshotRoot $SnapshotRoot `
        -PublishRoot $ControllerRoot `
        -SourceCommit $SourceCommit `
        -SourceCommitShort $SourceCommitShort `
        -SourceBranch $SourceBranch `
        -OriginMainCommit $OriginMainCommit `
        -DescendsFromOriginMain $DescendsFromOriginMain
}
catch {
    # Antes de eliminar el snapshot se copian fuera de el los diagnosticos de
    # compilacion disponibles. Un fallo al preservarlos se registra, pero nunca
    # sustituye ni oculta la excepcion original del build.
    $BuildFailure = $_
    $diagnostics = Preserve-FailedBuildDiagnostics `
        -Snapshot $SnapshotRoot `
        -Controller $ControllerRoot `
        -CommitShort $SourceCommitShort `
        -FailureText $BuildFailure.ToString()
    if (-not [string]::IsNullOrWhiteSpace($diagnostics)) {
        [Console]::Error.WriteLine("B13 DIAGNOSTICS: conservados en '$diagnostics'.")
    }
    throw
}
finally {
    $CleanupFailures = New-Object System.Collections.Generic.List[string]

    # Cada limpieza tiene su propio try/catch: la retirada fallida del registro
    # nunca impide intentar borrar fisicamente la raiz temporal.
    try {
        & git -C $ControllerRoot worktree remove --force $SnapshotRoot
        if ($LASTEXITCODE -ne 0) {
            $CleanupFailures.Add("git worktree remove fallo con codigo $LASTEXITCODE para '$SnapshotRoot'.")
        }
    }
    catch {
        $CleanupFailures.Add("git worktree remove no pudo ejecutarse para '$SnapshotRoot': $($_.Exception.Message)")
    }

    try {
        if (Test-Path -LiteralPath $SnapshotContainer) {
            Remove-Item -LiteralPath $SnapshotContainer -Recurse -Force -ErrorAction Stop
        }
    }
    catch {
        $CleanupFailures.Add("No se pudo eliminar la raiz temporal '$SnapshotContainer': $($_.Exception.Message)")
    }

    # El handle se cierra despues de publicar, hacer rollback y limpiar el
    # snapshot. Dispose se intenta siempre; un fallo queda agregado sin ocultar
    # la excepcion original del build.
    try {
        if ($null -ne $PublicationLockStream) {
            $PublicationLockStream.Dispose()
            $PublicationLockStream = $null
        }
    }
    catch {
        $CleanupFailures.Add("No se pudo liberar el bloqueo exclusivo de publicacion: $($_.Exception.Message)")
    }

    if ($CleanupFailures.Count -gt 0) {
        foreach ($cleanupFailure in $CleanupFailures) {
            # Console.Error deja evidencia clara sin convertirse en una excepcion
            # terminante que tape el fallo original o salte otra limpieza.
            [Console]::Error.WriteLine("B13 CLEANUP ERROR: $cleanupFailure")
        }
        if ($null -eq $BuildFailure) {
            throw ("La construccion termino, pero fallo la limpieza del snapshot o del bloqueo: " +
                ($CleanupFailures -join " | "))
        }
    }
}
