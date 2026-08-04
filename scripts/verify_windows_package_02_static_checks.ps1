Write-Step "A. Estructura del paquete extraido"

$exeInArtifact = Join-Path $PackageRoot "Sirius.exe"
$iniInArtifact = Join-Path $PackageRoot "alembic.ini"
$migrationsInArtifact = Join-Path $PackageRoot "migrations"
$buildManifestPath = Join-Path $PackageRoot "BUILD-MANIFEST.json"
$fileManifestPath = Join-Path $PackageRoot "FILE-MANIFEST.sha256"

Test-Check "Existe Sirius.exe" (Test-Path -LiteralPath $exeInArtifact)
Test-Check "Existe alembic.ini junto al ejecutable" (Test-Path -LiteralPath $iniInArtifact)
Test-Check "Existe migrations/ junto al ejecutable" (Test-Path -LiteralPath $migrationsInArtifact)
Test-Check "Existe BUILD-MANIFEST.json" (Test-Path -LiteralPath $buildManifestPath)
Test-Check "Existe FILE-MANIFEST.sha256" (Test-Path -LiteralPath $fileManifestPath)

if ($script:Failures.Count -gt 0) {
    throw "El paquete extraido no tiene la estructura minima. Verificacion detenida."
}

Test-Check "migrations/env.py presente" (Test-Path -LiteralPath (Join-Path $migrationsInArtifact "env.py"))
$versionFiles = @(Get-ChildItem -LiteralPath (Join-Path $migrationsInArtifact "versions") -Filter "*.py" -File -ErrorAction SilentlyContinue)
Test-Check "migrations/versions contiene revisiones ($($versionFiles.Count))" ($versionFiles.Count -gt 0)

$buildManifest = Get-Content -LiteralPath $buildManifestPath -Raw | ConvertFrom-Json
Test-Check "El manifiesto declara packaging_mode = standalone" ($buildManifest.packaging_mode -eq "standalone") $buildManifest.packaging_mode

# Procedencia, sobre el manifiesto YA EXTRAIDO. El nombre del ZIP se puede
# renombrar a mano; el manifiesto es lo que dice de que commit salio el binario,
# asi que se comparan las dos formas, completa y corta, contra el HEAD real.
$provenanceRaw = (& $VenvPython $provenanceScript "verify" $buildManifestPath $RepoHead $RepoHeadShort | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($provenanceRaw)) {
    throw "La comprobacion de procedencia fallo (codigo $LASTEXITCODE): $provenanceRaw"
}
$provenance = $provenanceRaw | ConvertFrom-Json
Test-Check "El artefacto procede del HEAD actual ($RepoHeadShort)" ([bool]$provenance.ok) (
    @($provenance.errors) -join "; ")
if (-not $provenance.ok) {
    throw ("El artefacto no procede del commit actual, asi que esta verificacion no puede " +
        "acreditarlo. Construye desde el HEAD actual y vuelve a verificar.")
}

$ExpectedAlembicHead = $buildManifest.alembic_head
Write-Info "Commit de origen: $($buildManifest.source_commit_short)   |   head de Alembic esperado: $ExpectedAlembicHead"

# --------------------------------------------------------------------------
Write-Step "A. Inventario de hashes sobre el contenido extraido"

$prefixLength = $PackageRoot.Length + 1
$manifestEntries = @{}
foreach ($line in (Get-Content -LiteralPath $fileManifestPath)) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $parts = $line -split "\s+", 2
    if ($parts.Count -eq 2) { $manifestEntries[$parts[1].Trim()] = $parts[0].Trim().ToLower() }
}

$actualFiles = @(Get-ChildItem -LiteralPath $PackageRoot -Recurse -Force -File |
    Where-Object { $_.FullName -ne $fileManifestPath })

$mismatched = 0
$missing = 0
foreach ($entry in $manifestEntries.GetEnumerator()) {
    $target = Join-Path $PackageRoot ($entry.Key.Replace("/", "\"))
    if (-not (Test-Path -LiteralPath $target)) { $missing++; continue }
    $actual = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $entry.Value) { $mismatched++ }
}
$unlisted = 0
foreach ($file in $actualFiles) {
    $relative = $file.FullName.Substring($prefixLength).Replace("\", "/")
    if (-not $manifestEntries.ContainsKey($relative)) { $unlisted++ }
}

Test-Check "FILE-MANIFEST.sha256 cubre $($manifestEntries.Count) archivos" ($manifestEntries.Count -gt 0)
Test-Check "Ningun archivo del manifiesto falta en el ZIP" ($missing -eq 0) "faltan $missing"
Test-Check "Ningun hash del ZIP discrepa del manifiesto" ($mismatched -eq 0) "discrepan $mismatched"
Test-Check "El ZIP no trae ningun archivo fuera del manifiesto" ($unlisted -eq 0) "sin listar $unlisted"
# El manifiesto no se lista a si mismo: el ZIP debe traer exactamente los
# archivos del manifiesto mas ese unico archivo.
Test-Check "El recuento del ZIP cuadra con el manifiesto" ($zipEntryCount -eq ($manifestEntries.Count + 1)) "zip $zipEntryCount / manifiesto+1 $($manifestEntries.Count + 1)"

# --------------------------------------------------------------------------
Write-Step "A. Datos y secretos dentro del paquete extraido"

$forbiddenNames = @("*.db", "*.db-wal", "*.db-shm", ".env", ".env.*", "settings.json",
    "data_location.json", "application.log", "*.pfx", "*.p12", "*.keystore", "*.jks")
$dirtyItems = New-Object System.Collections.Generic.List[string]
foreach ($pattern in $forbiddenNames) {
    foreach ($hit in @(Get-ChildItem -LiteralPath $PackageRoot -Recurse -Force -File -Filter $pattern -ErrorAction SilentlyContinue)) {
        $dirtyItems.Add($hit.FullName.Substring($prefixLength))
    }
}

# Solo es contaminacion el material de clave PRIVADA. Un almacen publico de CA
# (certifi/cacert.pem) es legitimo y necesario para verificar TLS.
foreach ($certificate in @($actualFiles | Where-Object { @(".pem", ".crt", ".cer", ".key") -contains $_.Extension.ToLower() -and $_.Length -lt 8MB })) {
    $certificateText = Get-Content -LiteralPath $certificate.FullName -Raw -ErrorAction SilentlyContinue
    if ($null -ne $certificateText -and $certificateText -match "-----BEGIN [A-Z ]*PRIVATE KEY-----") {
        $dirtyItems.Add("clave privada en " + $certificate.FullName.Substring($prefixLength))
    }
}
foreach ($dirName in @("logs", "backups", "exports")) {
    foreach ($hit in @(Get-ChildItem -LiteralPath $PackageRoot -Recurse -Force -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq $dirName })) {
        $dirtyItems.Add($hit.FullName.Substring($prefixLength))
    }
}
$textExtensions = @(".txt", ".json", ".ini", ".cfg", ".conf", ".log", ".md", ".py", ".mako", ".yaml", ".yml", ".toml", ".env", ".spec")
$secretPattern = "(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{20,}"
foreach ($file in @($actualFiles | Where-Object { $textExtensions -contains $_.Extension.ToLower() -and $_.Length -lt 2MB })) {
    $content = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue
    if ($null -ne $content -and $content -match $secretPattern) {
        # Se informa la RUTA, nunca la coincidencia.
        $dirtyItems.Add("posible clave en " + $file.FullName.Substring($prefixLength))
    }
}
Test-Check "Sin bases de datos, registros, copias, exportaciones ni secretos" ($dirtyItems.Count -eq 0) ($dirtyItems -join "; ")
Test-Check "Sin __pycache__ ni .pyc en migrations/" (@(Get-ChildItem -LiteralPath $migrationsInArtifact -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq "__pycache__" -or $_.Extension -eq ".pyc" }).Count -eq 0)

# Ningun codigo del paquete puede ejecutarse si estructura, procedencia,
# inventario, hashes o contaminacion han fallado. El ZIP y su checksum pueden
# haber sido regenerados alrededor de un ejecutable manipulado; registrar el
# fallo y continuar hasta el smoke test ejecutaria precisamente ese contenido.
if ($script:Failures.Count -gt 0) {
    throw ("El paquete extraido no supera las comprobaciones estaticas de estructura, " +
        "procedencia, inventario, hashes o contaminacion. No se ejecutara Sirius.exe.")
}

# --------------------------------------------------------------------------
