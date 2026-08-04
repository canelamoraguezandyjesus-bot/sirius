<#
.SYNOPSIS
    B13 - Verificacion automatica del paquete portatil de Sirius para Windows.

.DESCRIPTION
    Verifica EL ZIP QUE SE VA A DISTRIBUIR, no la carpeta de trabajo de dist.
    El orden importa: primero se copia el ZIP a una ruta temporal privada, se
    comprueba el SHA-256 de esa copia congelada y despues se inspecciona y extrae
    exclusivamente esa misma copia con limites de expansion. Todas las demas
    comprobaciones se hacen sobre lo extraido, y la afirmacion final queda
    limitada a los bytes cuyo hash se verifico.

      A. SHA-256 del ZIP, extraccion, estructura, inventario de hashes y
         ausencia de datos o secretos, todo sobre lo extraido.
      B. Independencia del repositorio: se ejecuta desde la copia extraida en
         una ruta con espacios y con un directorio de trabajo distinto del
         repositorio, del ejecutable y de los datos.
      C. Independencia de Python y uv: el proceso se lanza con un PATH reducido
         a Windows, sin Python, sin uv y sin .venv. No se desinstala nada.
      D. Datos desechables: LOCALAPPDATA, APPDATA, USERPROFILE, TEMP y TMP
         apuntan a una raiz temporal aislada. Nunca se toca la configuracion
         real del usuario y nunca se introduce una clave.
      E. Arranque y segundo arranque, con integridad de SQLite y revision de
         Alembic.
      F. Rutas con espacios.
      G. Rechaza ejecutarse con PowerShell elevado.

    Redirigir variables de entorno NO aisla Windows Credential Manager. Por eso
    la credencial de Sirius debe estar AUSENTE antes de ejecutar el paquete. Si
    la sonda devuelve PRESENT o ERROR, la verificacion aborta antes de ejecutar
    Sirius.exe y no manipula la credencial.

    Esta prueba termina el proceso a proposito. Es una comprobacion tecnica
    desechable y NO sustituye a la PA-019 manual.

.EXAMPLE
    .\scripts\verify_windows_package.ps1

.EXAMPLE
    .\scripts\verify_windows_package.ps1 -ArtifactPath dist\windows\Sirius-0.1.0.dev0-abc1234-windows-x64.zip
#>

[CmdletBinding()]
param(
    [string]$ArtifactPath = "",
    [int]$StartupTimeoutSeconds = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$DistRoot = Join-Path $RepoRoot "dist\windows"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

# Titulo de la ventana del flujo SIN clave (OnboardingWindow). Se compara un
# fragmento ASCII a proposito: el titulo real lleva raya y tilde, y no merece
# la pena que esta verificacion dependa de la codificacion de este archivo.
$OnboardingTitleFragment = "Primera configuraci"

$script:Failures = New-Object System.Collections.Generic.List[string]
$script:Skipped = New-Object System.Collections.Generic.List[string]
$script:Checks = 0

function Write-Step { param([string]$Text) Write-Host "`n=== $Text ===" -ForegroundColor Cyan }
function Write-Info { param([string]$Text) Write-Host "  $Text" -ForegroundColor DarkGray }

function Test-Check {
    param([string]$Name, [bool]$Condition, [string]$Detail = "")
    $script:Checks++
    if ($Condition) {
        Write-Host "  [ok] $Name" -ForegroundColor Green
    }
    else {
        $message = $Name
        if (-not [string]::IsNullOrWhiteSpace($Detail)) { $message = "$Name -> $Detail" }
        Write-Host "  [FALLO] $message" -ForegroundColor Red
        $script:Failures.Add($message)
    }
}

function Add-Skip {
    param([string]$Name, [string]$Reason)
    Write-Host "  [OMITIDA] $Name -> $Reason" -ForegroundColor Yellow
    $script:Skipped.Add("$Name -> $Reason")
}

# --------------------------------------------------------------------------
Write-Step "G. Privilegios"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "  [FALLO] Esta sesion de PowerShell esta ELEVADA." -ForegroundColor Red
    Write-Host "  Sirius no debe requerir administrador. Vuelve a ejecutar esta verificacion" -ForegroundColor Red
    Write-Host "  desde una consola de PowerShell normal, sin elevar. Verificacion NO superada." -ForegroundColor Red
    exit 2
}
Write-Host "  [ok] PowerShell sin elevar." -ForegroundColor Green

# --------------------------------------------------------------------------
Write-Step "A. Localizacion del ZIP a verificar"

# El sujeto de la verificacion es el ZIP. La carpeta de dist solo sirve para
# encontrarlo: nada de lo que se prueba despues sale de ella.
#
# Y se elige por NOMBRE EXACTO, nunca "el mas reciente". Ese atajo produjo
# evidencia falsa: las dos construcciones de f9b68d5 fallaron y no dejaron
# artefacto, el verificador encontro el ZIP de a82972f de una ronda anterior, lo
# valido, y termino como SUPERADA CON RESERVAS acreditando un commit que no era
# el de HEAD. La seleccion y la comprobacion de procedencia viven en
# scripts/package_provenance.py, cubierto por pruebas.
$RepoHead = (& git -C $RepoRoot rev-parse HEAD | Out-String).Trim()
$RepoHeadShort = (& git -C $RepoRoot rev-parse --short HEAD | Out-String).Trim()
if ([string]::IsNullOrWhiteSpace($RepoHead) -or [string]::IsNullOrWhiteSpace($RepoHeadShort)) {
    throw "No se pudo determinar el HEAD del repositorio."
}
$AppVersion = ""
foreach ($line in (Get-Content -LiteralPath (Join-Path $RepoRoot "pyproject.toml"))) {
    if ($line -match '^\s*version\s*=\s*"([^"]+)"') { $AppVersion = $Matches[1]; break }
}
if ([string]::IsNullOrWhiteSpace($AppVersion)) {
    throw "No se pudo leer la version del proyecto en pyproject.toml."
}
Write-Info "HEAD del repositorio: $RepoHead ($RepoHeadShort)   |   version: $AppVersion"

$provenanceScript = Join-Path $PSScriptRoot "package_provenance.py"
if (-not (Test-Path -LiteralPath $provenanceScript)) {
    throw "No existe $provenanceScript, necesario para elegir el artefacto."
}
if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw ("No existe el interprete del entorno en $VenvPython. Ejecuta " +
        "'uv sync' en el repositorio antes de verificar el paquete.")
}

if ([string]::IsNullOrWhiteSpace($ArtifactPath)) {
    $selectionRaw = (& $VenvPython $provenanceScript "select" $DistRoot $AppVersion $RepoHeadShort | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($selectionRaw)) {
        throw "La seleccion del artefacto fallo (codigo $LASTEXITCODE): $selectionRaw"
    }
    $selection = $selectionRaw | ConvertFrom-Json
    if ($null -ne $selection.error) {
        throw $selection.error
    }
    $ZipPath = $selection.zip_path
    Write-Info "Artefacto esperado para este commit: $($selection.expected_name).zip"
}
else {
    if (-not (Test-Path -LiteralPath $ArtifactPath)) { throw "No existe la ruta indicada: $ArtifactPath" }
    $resolved = (Resolve-Path -LiteralPath $ArtifactPath).Path
    if ($resolved.ToLower().EndsWith(".zip")) { $ZipPath = $resolved }
    else { $ZipPath = "$resolved.zip" }
    if (-not (Test-Path -LiteralPath $ZipPath)) {
        throw "No existe el ZIP correspondiente: $ZipPath. La verificacion de B13 se hace sobre el ZIP distribuido."
    }
}

$ArtifactName = [System.IO.Path]::GetFileNameWithoutExtension($ZipPath)
$ZipShaPath = "$ZipPath.sha256"
Write-Info "ZIP a verificar: $ZipPath"

# Una ruta unica evita reutilizar una copia anterior y saca los bytes de dist y
# de cualquier sincronizacion de OneDrive antes de calcular el hash acreditado.
$SmokeRoot = Join-Path $env:TEMP ("Sirius Packaging Smoke Test " + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $SmokeRoot | Out-Null
$FrozenZipPath = Join-Path $SmokeRoot "$ArtifactName.zip"

# --------------------------------------------------------------------------
Write-Step "A. Copia congelada y SHA-256 del ZIP (antes de extraer nada)"

Test-Check "Existe el ZIP" (Test-Path -LiteralPath $ZipPath)
Test-Check "Existe el .zip.sha256" (Test-Path -LiteralPath $ZipShaPath)
if ($script:Failures.Count -gt 0) {
    throw "Falta el ZIP o su hash registrado. Verificacion detenida."
}

$recordedHash = ((Get-Content -LiteralPath $ZipShaPath -Raw).Trim() -split "\s+")[0].ToLower()
Copy-Item -LiteralPath $ZipPath -Destination $FrozenZipPath
Test-Check "El ZIP se congelo en una copia temporal privada" (Test-Path -LiteralPath $FrozenZipPath)
if ($script:Failures.Count -gt 0) {
    throw "No se pudo congelar el ZIP antes de verificarlo. Verificacion detenida."
}

$VerifiedZipHash = (Get-FileHash -LiteralPath $FrozenZipPath -Algorithm SHA256).Hash.ToLower()
Test-Check "El SHA-256 registrado coincide con la copia congelada" (
    $recordedHash -eq $VerifiedZipHash) "registrado $recordedHash / copia $VerifiedZipHash"
if ($script:Failures.Count -gt 0) {
    throw "La copia congelada no coincide con el hash registrado. No se extrae nada. Verificacion detenida."
}
Write-Info "SHA-256 verificado: $VerifiedZipHash"
Write-Info "Copia congelada    : $FrozenZipPath"
Write-Info "Tamano del ZIP     : $([math]::Round((Get-Item -LiteralPath $FrozenZipPath).Length / 1MB, 1)) MB"

# --------------------------------------------------------------------------
Write-Step "A/F. Extraccion acotada de la copia congelada en una ruta con espacios"

$ExtractRoot = Join-Path $SmokeRoot "Paquete Extraido Del Zip"
$IsolatedHome = Join-Path $SmokeRoot "Perfil De Usuario"
$IsolatedData = Join-Path $SmokeRoot "Datos De Sirius"
$IsolatedTemp = Join-Path $SmokeRoot "Temporal Aislado"
$WorkingDirectory = Join-Path $SmokeRoot "Directorio De Trabajo"
$LocalAppData = Join-Path $IsolatedHome "AppData\Local"
$RoamingAppData = Join-Path $IsolatedHome "AppData\Roaming"

foreach ($dir in @($ExtractRoot, $IsolatedHome, $IsolatedData, $IsolatedTemp, $WorkingDirectory, $LocalAppData, $RoamingAppData)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

# La misma implementacion Python inspecciona y extrae la copia congelada. Antes
# de escribir rechaza zip-slip, destinos duplicados, enlaces, mas de 4096
# entradas, entradas mayores de 512 MiB, expansion total mayor de 2 GiB y ratios
# superiores a 200:1. Durante la copia vuelve a imponer los limites individual y
# acumulado sobre los bytes realmente escritos.
$inspectorScript = Join-Path $PSScriptRoot "zip_package_inspector.py"
if (-not (Test-Path -LiteralPath $inspectorScript)) {
    throw "No existe $inspectorScript, necesario para inspeccionar y extraer el ZIP."
}
$inspectionRaw = (& $VenvPython $inspectorScript $FrozenZipPath $ExtractRoot | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($inspectionRaw)) {
    throw "La inspeccion del ZIP fallo (codigo $LASTEXITCODE): $inspectionRaw"
}
$inspection = $inspectionRaw | ConvertFrom-Json
$rootList = @($inspection.roots)
$unsafeEntries = @($inspection.unsafe)
$sizeViolations = @($inspection.size_violations)
$zipEntryCount = [int]$inspection.file_count
$zipTotalEntryCount = [int]$inspection.entry_count
$declaredExpandedBytes = [long]$inspection.total_uncompressed_bytes
$maxEntryBytes = [long]$inspection.max_entry_uncompressed_bytes
$maxCompressionRatio = [double]$inspection.max_compression_ratio

Test-Check "Ninguna entrada del ZIP es insegura" ($unsafeEntries.Count -eq 0) ($unsafeEntries -join "; ")
Test-Check "La expansion y el numero de entradas respetan los limites" (
    $sizeViolations.Count -eq 0) ($sizeViolations -join "; ")
Test-Check "El ZIP tiene exactamente una raiz" ($rootList.Count -eq 1) ("raices: " + ($rootList -join ", "))
Test-Check "La raiz del ZIP es '$ArtifactName'" ($rootList.Count -eq 1 -and $rootList[0] -eq $ArtifactName) ("encontrado: " + ($rootList -join ", "))
if ($script:Failures.Count -gt 0) {
    throw "La estructura o expansion del ZIP no es segura. Verificacion detenida antes de extraer."
}
Write-Info "Entradas totales   : $zipTotalEntryCount"
Write-Info "Expansion declarada: $([math]::Round($declaredExpandedBytes / 1MB, 1)) MB"
Write-Info "Entrada mayor      : $([math]::Round($maxEntryBytes / 1MB, 1)) MB"
Write-Info "Ratio maximo       : $([math]::Round($maxCompressionRatio, 1)):1"

$extractionRaw = (& $VenvPython $inspectorScript "extract" $FrozenZipPath $ExtractRoot | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($extractionRaw)) {
    throw "La extraccion acotada del ZIP fallo (codigo $LASTEXITCODE): $extractionRaw"
}
$extraction = $extractionRaw | ConvertFrom-Json
if (-not [bool]$extraction.ok) {
    throw "La extraccion acotada del ZIP fue rechazada: $($extraction.error)"
}
Test-Check "La extraccion escribio todas las entradas de archivo declaradas" (
    [int]$extraction.file_count -eq $zipEntryCount) (
    "esperadas $zipEntryCount / escritas $($extraction.file_count)")
Test-Check "Los bytes extraidos coinciden con el total declarado" (
    [long]$extraction.total_uncompressed_bytes -eq $declaredExpandedBytes) (
    "declarados $declaredExpandedBytes / escritos $($extraction.total_uncompressed_bytes)")

$FrozenZipHashAfterExtraction = (
    Get-FileHash -LiteralPath $FrozenZipPath -Algorithm SHA256
).Hash.ToLower()
Test-Check "La copia congelada no cambio durante inspeccion y extraccion" (
    $FrozenZipHashAfterExtraction -eq $VerifiedZipHash) (
    "antes $VerifiedZipHash / despues $FrozenZipHashAfterExtraction")

$PackageRoot = Join-Path $ExtractRoot $ArtifactName
Test-Check "La extraccion produjo la raiz del paquete" (Test-Path -LiteralPath $PackageRoot)
Test-Check "La ruta del paquete extraido contiene espacios" ($PackageRoot.Contains(" "))
if ($script:Failures.Count -gt 0) {
    throw "No se pudo extraer el paquete de forma segura. Verificacion detenida."
}
Write-Info "Paquete extraido en: $PackageRoot"
Write-Info "Entradas de archivo en el ZIP: $zipEntryCount"

# A partir de aqui NADA vuelve a mirar dist\windows: todo se comprueba y se
# ejecuta sobre $PackageRoot, extraido de la copia congelada cuyo hash se
# verifico.

# --------------------------------------------------------------------------
