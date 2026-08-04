$ExecutionFailure = $null
$DatabasePath = ""
$script:TablesAfterFirst = @()

try {
    Write-Step "E. Primer arranque aislado, desde el ZIP extraido"

    $DatabasePath = Invoke-SmokeLaunch -Label "1er arranque"

    if (Test-Path -LiteralPath $DatabasePath) {
        $versionRows = Invoke-SqliteQuery -DatabasePath $DatabasePath -Sql "SELECT version_num FROM alembic_version"
        $revisions = @($versionRows | ForEach-Object { $_[0] })
        Test-Check "El esquema alcanzo el head de Alembic ($ExpectedAlembicHead)" (
            $revisions.Count -eq 1 -and $revisions[0] -eq $ExpectedAlembicHead) ("encontrado: " + ($revisions -join ","))

        $tableRows = Invoke-SqliteQuery -DatabasePath $DatabasePath -Sql "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        $script:TablesAfterFirst = @($tableRows | ForEach-Object { $_[0] })
        Write-Info "Tablas creadas: $($script:TablesAfterFirst.Count)"

        $integrity = Invoke-SqliteQuery -DatabasePath $DatabasePath -Sql "PRAGMA integrity_check"
        Test-Check "PRAGMA integrity_check devuelve ok" ($integrity[0][0] -eq "ok") $integrity[0][0]
    }

    # ----------------------------------------------------------------------
    Write-Step "E. Segundo arranque, reutilizando el mismo entorno temporal"

    $null = Invoke-SmokeLaunch -Label "2do arranque"

    if (Test-Path -LiteralPath $DatabasePath) {
        $versionRows = Invoke-SqliteQuery -DatabasePath $DatabasePath -Sql "SELECT version_num FROM alembic_version"
        $revisions = @($versionRows | ForEach-Object { $_[0] })
        Test-Check "La revision de Alembic sigue siendo el head esperado" (
            $revisions.Count -eq 1 -and $revisions[0] -eq $ExpectedAlembicHead) ("encontrado: " + ($revisions -join ","))
        Test-Check "El esquema no se duplico (una sola fila en alembic_version)" ($revisions.Count -eq 1) "filas: $($revisions.Count)"

        $tableRows = Invoke-SqliteQuery -DatabasePath $DatabasePath -Sql "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        $tablesAfterSecond = @($tableRows | ForEach-Object { $_[0] })
        Test-Check "El inventario de tablas es identico al del primer arranque" (
            ($tablesAfterSecond -join ",") -eq ($script:TablesAfterFirst -join ",")) (
            "antes $($script:TablesAfterFirst.Count) / ahora $($tablesAfterSecond.Count)")

        $integrity = Invoke-SqliteQuery -DatabasePath $DatabasePath -Sql "PRAGMA integrity_check"
        Test-Check "PRAGMA integrity_check sigue devolviendo ok" ($integrity[0][0] -eq "ok") $integrity[0][0]
    }
}
catch {
    # No se relanza aqui: el finally debe comprobar siempre el estado real del
    # usuario. La excepcion original se registra despues como fallo verificable.
    $ExecutionFailure = $_
}
finally {
    # Estas postcondiciones protegen estado real del usuario y deben ejecutarse
    # aunque falle un arranque o cualquier consulta SQLite. Cada bloque contiene
    # sus propios errores para que una comprobacion rota no impida las restantes
    # ni oculte la excepcion original de ejecucion.
    Write-Step "D. La configuracion real del usuario no se toco"

    try {
        $RealPointerExistsAfter = Test-Path -LiteralPath $RealPointer
        $RealPointerHashAfter = ""
        if ($RealPointerExistsAfter) {
            $RealPointerHashAfter = (Get-FileHash -LiteralPath $RealPointer -Algorithm SHA256).Hash.ToLower()
        }
        Write-Info "Despues de arrancar -> existe: $RealPointerExistsAfter   hash: $(if ($RealPointerHashAfter) { $RealPointerHashAfter } else { '(no aplica)' })"

        Test-Check "La existencia del data_location.json real no cambio" (
            $RealPointerExistedBefore -eq $RealPointerExistsAfter) (
            "antes $RealPointerExistedBefore / ahora $RealPointerExistsAfter")
        if ($RealPointerExistedBefore -and $RealPointerExistsAfter) {
            Test-Check "El SHA-256 del data_location.json real es identico" (
                $RealPointerHashBefore -eq $RealPointerHashAfter) (
                "antes $RealPointerHashBefore / ahora $RealPointerHashAfter")
        }
        elseif (-not $RealPointerExistedBefore -and -not $RealPointerExistsAfter) {
            Test-Check "El data_location.json real sigue sin existir" $true
        }
    }
    catch {
        Test-Check "Se pudo comprobar el data_location.json real despues de los arranques" $false $_.Exception.Message
    }

    try {
        Test-Check "Los datos de prueba viven bajo la raiz temporal aislada" ($IsolatedData.StartsWith($SmokeRoot))
        $settingsPath = Join-Path $configDir "settings.json"
        $settingsContainKey = (Test-Path -LiteralPath $settingsPath) -and (
            (Get-Content -LiteralPath $settingsPath -Raw -ErrorAction SilentlyContinue) -match "sk-")
        Test-Check "No se escribio ninguna clave en el entorno de prueba" (-not $settingsContainKey)
    }
    catch {
        Test-Check "Se pudo comprobar que el entorno temporal no contiene una clave" $false $_.Exception.Message
    }

    try {
        # B13 solo ejecuta el paquete cuando la credencial estaba ausente. Volver
        # a obtener ABSENT demuestra que el paquete no dejo una credencial
        # persistente en la sesion real de Windows, sin comparar ningun valor.
        $CredentialStateAfter = "ERROR NoProbe"
        if (Test-Path -LiteralPath $VenvPython) {
            $probeOutputAfter = (& $VenvPython $CredentialProbe 2>&1 | Out-String).Trim()
            if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($probeOutputAfter)) {
                $CredentialStateAfter = ($probeOutputAfter -split "`n")[-1].Trim()
            }
        }
        Test-Check "La credencial de Sirius sigue ausente despues de los arranques" (
            $CredentialStateAfter -eq "ABSENT") "antes $CredentialState / ahora $CredentialStateAfter"
    }
    catch {
        Test-Check "Se pudo comprobar la credencial de Sirius despues de los arranques" $false $_.Exception.Message
    }
}

if ($null -ne $ExecutionFailure) {
    $executionDetail = $ExecutionFailure.Exception.Message
    if ([string]::IsNullOrWhiteSpace($executionDetail)) {
        $executionDetail = $ExecutionFailure.ToString()
    }
    Test-Check "Los dos arranques y las validaciones SQLite terminaron sin excepciones" $false $executionDetail
}

# --------------------------------------------------------------------------
Write-Step "Resultado"

Write-Host ""
if ($script:Failures.Count -eq 0 -and $script:Skipped.Count -eq 0) {
    Write-Host "================ B13: verificacion SUPERADA ================" -ForegroundColor Green
    Write-Host "  ZIP       : $ArtifactName.zip"
    Write-Host "  SHA-256   : $VerifiedZipHash"
    Write-Host "  Probado   : la copia EXTRAIDA de ese ZIP, no dist\windows"
    Write-Host "  Pruebas   : $($script:Checks) comprobaciones, 0 fallos, 0 omitidas"
    Write-Host "  Entorno   : sin Python, sin uv, sin .venv, ruta con espacios, sin administrador"
    Write-Host "  Nota      : terminar el proceso es una prueba tecnica desechable;"
    Write-Host "              NO sustituye a la PA-019 manual."
    Write-Host "===========================================================" -ForegroundColor Green
    Write-Host "`n  Entorno temporal conservado para inspeccion: $SmokeRoot" -ForegroundColor DarkGray
    exit 0
}
elseif ($script:Failures.Count -eq 0) {
    Write-Host "========= B13: verificacion SUPERADA CON RESERVAS =========" -ForegroundColor Yellow
    Write-Host "  ZIP       : $ArtifactName.zip"
    Write-Host "  SHA-256   : $VerifiedZipHash"
    Write-Host "  Probado   : la copia EXTRAIDA de ese ZIP, no dist\windows"
    Write-Host "  Pruebas   : $($script:Checks) comprobaciones, 0 fallos, $($script:Skipped.Count) OMITIDAS"
    Write-Host "  NO se ha demostrado:" -ForegroundColor Yellow
    foreach ($skip in $script:Skipped) { Write-Host "   - $skip" -ForegroundColor Yellow }
    Write-Host "  Para cubrirlo, ver docs/implementation/B13_PACKAGING.md," -ForegroundColor Yellow
    Write-Host "  seccion 'Prueba de onboarding sin clave'." -ForegroundColor Yellow
    Write-Host "===========================================================" -ForegroundColor Yellow
    Write-Host "`n  Entorno temporal conservado para inspeccion: $SmokeRoot" -ForegroundColor DarkGray
    exit 0
}
else {
    Write-Host "================ B13: verificacion NO SUPERADA ================" -ForegroundColor Red
    Write-Host "  ZIP       : $ArtifactName.zip"
    Write-Host "  Pruebas   : $($script:Checks) comprobaciones, $($script:Failures.Count) fallos, $($script:Skipped.Count) omitidas"
    foreach ($failure in $script:Failures) { Write-Host "   - $failure" -ForegroundColor Red }
    foreach ($skip in $script:Skipped) { Write-Host "   - (omitida) $skip" -ForegroundColor Yellow }
    Write-Host "==============================================================" -ForegroundColor Red
    Write-Host "`n  Entorno temporal conservado para diagnostico: $SmokeRoot" -ForegroundColor DarkGray
    exit 1
}
