<#
.SYNOPSIS
    B13 - Verificacion automatica del paquete portatil de Sirius para Windows.

.DESCRIPTION
    Verifica EL ZIP QUE SE VA A DISTRIBUIR, no la carpeta de trabajo de dist.
    El orden importa: primero se comprueba el SHA-256 del ZIP, despues se
    extrae ese mismo ZIP a una ruta temporal con espacios, y todas las demas
    comprobaciones -inventario de hashes, contaminacion y arranques- se hacen
    sobre la copia extraida. La afirmacion final queda limitada al ZIP cuyo
    hash se verifico.

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

    Limite conocido y declarado: redirigir variables de entorno de sistema de
    archivos NO aisla Windows Credential Manager. La credencial vive en la
    sesion del usuario de Windows, no en %LOCALAPPDATA%. Por eso, antes de los
    arranques, se comprueba la PRECONDICION de que la credencial de Sirius no
    existe en esta sesion. Si existe, la prueba de onboarding sin clave se
    OMITE de forma explicita y no se declara superada. La comprobacion usa el
    puerto de aplicacion y solo obtiene un booleano: nunca lee, imprime,
    exporta, modifica ni borra el valor.

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
if ([string]::IsNullOrWhiteSpace($ArtifactPath)) {
    if (-not (Test-Path -LiteralPath $DistRoot)) {
        throw "No existe dist\windows. Ejecuta antes .\scripts\build_windows.ps1"
    }
    $candidates = @(Get-ChildItem -LiteralPath $DistRoot -File |
        Where-Object { $_.Name -like "Sirius-*-windows-x64.zip" } |
        Sort-Object LastWriteTime -Descending)
    if ($candidates.Count -eq 0) {
        throw "No se encontro ningun ZIP de B13 en dist\windows. Ejecuta antes .\scripts\build_windows.ps1"
    }
    $ZipPath = $candidates[0].FullName
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

# --------------------------------------------------------------------------
Write-Step "A. SHA-256 del ZIP (antes de extraer nada)"

Test-Check "Existe el ZIP" (Test-Path -LiteralPath $ZipPath)
Test-Check "Existe el .zip.sha256" (Test-Path -LiteralPath $ZipShaPath)
if ($script:Failures.Count -gt 0) {
    throw "Falta el ZIP o su hash registrado. Verificacion detenida."
}

$recordedHash = ((Get-Content -LiteralPath $ZipShaPath -Raw).Trim() -split "\s+")[0].ToLower()
$VerifiedZipHash = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash.ToLower()
Test-Check "El SHA-256 registrado coincide con el ZIP" ($recordedHash -eq $VerifiedZipHash) "registrado $recordedHash / real $VerifiedZipHash"
if ($script:Failures.Count -gt 0) {
    throw "El ZIP no coincide con su hash registrado. No se extrae nada. Verificacion detenida."
}
Write-Info "SHA-256 verificado: $VerifiedZipHash"
Write-Info "Tamano del ZIP    : $([math]::Round((Get-Item -LiteralPath $ZipPath).Length / 1MB, 1)) MB"

# --------------------------------------------------------------------------
Write-Step "A/F. Extraccion del ZIP verificado en una ruta con espacios"

$SmokeRoot = Join-Path $env:TEMP "Sirius Packaging Smoke Test"
if (Test-Path -LiteralPath $SmokeRoot) { Remove-Item -LiteralPath $SmokeRoot -Recurse -Force }

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

Add-Type -AssemblyName System.IO.Compression.FileSystem

# Antes de extraer: la raiz del ZIP tiene que ser exactamente una carpeta, y
# tiene que llamarse como el artefacto. Un ZIP plano, o con dos raices, o con
# una raiz distinta, no es el paquete que este verificador sabe validar.
$zipRoots = New-Object System.Collections.Generic.HashSet[string]
$zipEntryCount = 0
$archive = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
try {
    foreach ($entry in $archive.Entries) {
        $segments = $entry.FullName -split "/"
        [void]$zipRoots.Add($segments[0])
        if (-not [string]::IsNullOrEmpty($entry.Name)) { $zipEntryCount++ }
    }
}
finally {
    $archive.Dispose()
}

$rootList = @($zipRoots)
Test-Check "El ZIP tiene exactamente una raiz" ($rootList.Count -eq 1) ("raices: " + ($rootList -join ", "))
Test-Check "La raiz del ZIP es '$ArtifactName'" ($rootList.Count -eq 1 -and $rootList[0] -eq $ArtifactName) ("encontrado: " + ($rootList -join ", "))
if ($script:Failures.Count -gt 0) {
    throw "La estructura del ZIP no es la esperada. Verificacion detenida."
}

[System.IO.Compression.ZipFile]::ExtractToDirectory($ZipPath, $ExtractRoot)

$PackageRoot = Join-Path $ExtractRoot $ArtifactName
Test-Check "La extraccion produjo la raiz del paquete" (Test-Path -LiteralPath $PackageRoot)
Test-Check "La ruta del paquete extraido contiene espacios" ($PackageRoot.Contains(" "))
if ($script:Failures.Count -gt 0) {
    throw "No se pudo extraer el paquete. Verificacion detenida."
}
Write-Info "Paquete extraido en: $PackageRoot"
Write-Info "Entradas de archivo en el ZIP: $zipEntryCount"

# A partir de aqui NADA vuelve a mirar dist\windows: todo se comprueba y se
# ejecuta sobre $PackageRoot, que es el contenido real del ZIP verificado.

# --------------------------------------------------------------------------
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

# --------------------------------------------------------------------------
Write-Step "B/F. Aislamiento de rutas"

$ExeCopy = Join-Path $PackageRoot "Sirius.exe"
Test-Check "El ejecutable a probar sale del ZIP extraido" ($ExeCopy.StartsWith($ExtractRoot))
Test-Check "El ejecutable a probar NO sale de dist\windows" (-not $ExeCopy.StartsWith($DistRoot))
Test-Check "La ruta de datos contiene espacios" ($IsolatedData.Contains(" "))
Test-Check "El directorio de trabajo no es el repositorio, ni el del ejecutable, ni el de datos" (
    ($WorkingDirectory -ne $RepoRoot) -and ($WorkingDirectory -ne $PackageRoot) -and ($WorkingDirectory -ne $IsolatedData))
Test-Check "El directorio de trabajo queda FUERA de la carpeta extraida" (-not $WorkingDirectory.StartsWith($ExtractRoot))
Test-Check "Los datos quedan FUERA de la carpeta extraida" (-not $IsolatedData.StartsWith($ExtractRoot))
Write-Info "Ejecutable: $ExeCopy"
Write-Info "Trabajo   : $WorkingDirectory"
Write-Info "Datos     : $IsolatedData"

# --------------------------------------------------------------------------
Write-Step "D. Entorno aislado y desechable"

# Puntero minimo valido de ubicacion de datos, en el config_dir aislado
# (platformdirs resuelve %LOCALAPPDATA%\sirius). Nunca se escribe ninguna clave.
$configDir = Join-Path $LocalAppData "sirius"
New-Item -ItemType Directory -Force -Path $configDir | Out-Null
$locationPayload = [ordered]@{ version = 1; data_dir = $IsolatedData }
$locationJson = $locationPayload | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $configDir "data_location.json"), $locationJson, (New-Object System.Text.UTF8Encoding($false)))
Write-Info "data_location.json de prueba escrito en $configDir"

# Deliberadamente SIN %SystemRoot% a secas: el lanzador de Python (py.exe) se
# instala ahi, y su presencia debilitaria la afirmacion de que el proceso
# empaquetado no alcanza ningun Python. Con system32, Wbem y WindowsPowerShell
# basta de sobra para una aplicacion de escritorio.
$MinimalPath = "$env:SystemRoot\system32;$env:SystemRoot\System32\Wbem;$env:SystemRoot\System32\WindowsPowerShell\v1.0"

$pathHasInterpreter = $false
foreach ($entry in ($MinimalPath -split ";")) {
    if ([string]::IsNullOrWhiteSpace($entry)) { continue }
    foreach ($binary in @("python.exe", "python3.exe", "uv.exe", "uvx.exe", "py.exe")) {
        if (Test-Path -LiteralPath (Join-Path $entry $binary)) { $pathHasInterpreter = $true }
    }
}
Test-Check "C. El PATH reducido no contiene Python, py ni uv" (-not $pathHasInterpreter)
Test-Check "C. El PATH reducido no contiene ningun .venv" (-not ($MinimalPath -match "\.venv"))

$IsolatedEnv = @{
    "SystemRoot"             = $env:SystemRoot
    "windir"                 = $env:windir
    "SystemDrive"            = $env:SystemDrive
    "PATH"                   = $MinimalPath
    "PATHEXT"                = ".COM;.EXE;.BAT;.CMD"
    "COMSPEC"                = "$env:SystemRoot\system32\cmd.exe"
    "LOCALAPPDATA"           = $LocalAppData
    "APPDATA"                = $RoamingAppData
    "USERPROFILE"            = $IsolatedHome
    "HOMEDRIVE"              = $env:HOMEDRIVE
    "HOMEPATH"               = $env:HOMEPATH
    "TEMP"                   = $IsolatedTemp
    "TMP"                    = $IsolatedTemp
    "PROCESSOR_ARCHITECTURE" = $env:PROCESSOR_ARCHITECTURE
    "NUMBER_OF_PROCESSORS"   = $env:NUMBER_OF_PROCESSORS
    "ProgramData"            = $env:ProgramData
    "ProgramFiles"           = $env:ProgramFiles
    "PUBLIC"                 = $env:PUBLIC
    "USERNAME"               = $env:USERNAME
    "COMPUTERNAME"           = $env:COMPUTERNAME
}
foreach ($banned in @("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME", "UV_PROJECT_ENVIRONMENT")) {
    Test-Check "C. La variable $banned no se pasa al proceso" (-not $IsolatedEnv.ContainsKey($banned))
}

# --------------------------------------------------------------------------
Write-Step "D. Precondicion: Windows Credential Manager"

# Redirigir LOCALAPPDATA/APPDATA/USERPROFILE NO aisla Credential Manager: la
# credencial pertenece a la sesion del usuario de Windows. Si la credencial
# real de Sirius existe, el ejecutable seguira el camino CON clave y esta
# verificacion no puede afirmar que probo el onboarding sin clave.
#
# La consulta usa el puerto de aplicacion (ApiKeySettingsUseCase.has_key), que
# por contrato devuelve un booleano y nunca el valor. No se lee, imprime,
# exporta, modifica ni borra nada. No se usa cmdkey.
$CredentialProbe = Join-Path $SmokeRoot "probe_credential_presence.py"
$credentialProbeSource = @'
"""Precondicion de B13: SOLO existencia de la credencial de Sirius.

Usa el puerto de aplicacion, que por contrato nunca devuelve el valor de la
clave. Imprime unicamente PRESENT, ABSENT o ERROR <TipoDeExcepcion>. Este
script no escribe, no borra y no muestra ningun secreto.
"""

import sys

try:
    from sirius.adapters.secrets.keyring_store import KeyringSecretStore
    from sirius.application.api_key_settings import ApiKeySettingsError, ApiKeySettingsUseCase
except Exception as exc:  # noqa: BLE001 - solo se reporta el tipo
    print("ERROR " + type(exc).__name__)
    sys.exit(0)

try:
    print("PRESENT" if ApiKeySettingsUseCase(KeyringSecretStore()).has_key() else "ABSENT")
except ApiKeySettingsError as exc:
    print("ERROR " + type(exc).__name__)
except Exception as exc:  # noqa: BLE001 - solo se reporta el tipo
    print("ERROR " + type(exc).__name__)
'@
[System.IO.File]::WriteAllText($CredentialProbe, $credentialProbeSource, (New-Object System.Text.UTF8Encoding($false)))

$CredentialState = "ERROR NoProbe"
if (Test-Path -LiteralPath $VenvPython) {
    $probeOutput = (& $VenvPython $CredentialProbe 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($probeOutput)) {
        $CredentialState = ($probeOutput -split "`n")[-1].Trim()
    }
}
Write-Info "Credencial de Sirius en esta sesion de Windows (servicio 'Sirius', clave 'openai_api_key'): $CredentialState"

$NoKeyPreconditionMet = ($CredentialState -eq "ABSENT")
Test-Check "La precondicion de Credential Manager se pudo evaluar" ($CredentialState -eq "ABSENT" -or $CredentialState -eq "PRESENT") $CredentialState

if (-not $NoKeyPreconditionMet) {
    Write-Host "  La credencial de Sirius EXISTE en esta sesion de Windows (o no se pudo consultar)." -ForegroundColor Yellow
    Write-Host "  Redirigir variables de entorno no aisla Credential Manager, asi que el flujo" -ForegroundColor Yellow
    Write-Host "  sin clave NO puede comprobarse aqui. Para ejecutarlo, usa una cuenta de Windows" -ForegroundColor Yellow
    Write-Host "  sin la credencial de Sirius: ver docs/implementation/B13_PACKAGING.md," -ForegroundColor Yellow
    Write-Host "  seccion 'Prueba de onboarding sin clave'. No se toca la credencial real." -ForegroundColor Yellow
}

# --------------------------------------------------------------------------
Write-Step "D. Estado previo del data_location.json real del usuario"

# Se resuelve con el MISMO criterio que la aplicacion: su propio resolve_paths.
$RealConfigDir = ""
if (Test-Path -LiteralPath $VenvPython) {
    $RealConfigDir = (& $VenvPython -c "from sirius.infrastructure.paths import resolve_paths; print(resolve_paths().config_dir)" 2>&1 | Out-String).Trim()
}
if ([string]::IsNullOrWhiteSpace($RealConfigDir) -or $RealConfigDir.Contains("Traceback")) {
    # Reserva: el mismo destino que usa platformdirs en Windows.
    $RealConfigDir = Join-Path $env:LOCALAPPDATA "sirius"
    Write-Info "resolve_paths no disponible; se usa la ruta de reserva."
}
$RealPointer = Join-Path $RealConfigDir "data_location.json"

$RealPointerExistedBefore = Test-Path -LiteralPath $RealPointer
$RealPointerHashBefore = ""
if ($RealPointerExistedBefore) {
    $RealPointerHashBefore = (Get-FileHash -LiteralPath $RealPointer -Algorithm SHA256).Hash.ToLower()
}
Write-Info "Puntero real: $RealPointer"
Write-Info "Antes de arrancar -> existe: $RealPointerExistedBefore   hash: $(if ($RealPointerHashBefore) { $RealPointerHashBefore } else { '(no aplica)' })"
Test-Check "El puntero real del usuario NO esta dentro del entorno de prueba" (-not $RealPointer.StartsWith($SmokeRoot))

# --------------------------------------------------------------------------
# Utilidades de lanzamiento y consulta
# --------------------------------------------------------------------------

if (-not ([System.Management.Automation.PSTypeName]'SiriusWindowProbe').Type) {
    Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public static class SiriusWindowProbe
{
    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")]
    private static extern int GetWindowTextLength(IntPtr hWnd);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);

    public static string[] VisibleTitles(uint targetPid)
    {
        List<string> found = new List<string>();
        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam)
        {
            uint pid;
            GetWindowThreadProcessId(hWnd, out pid);
            if (pid == targetPid && IsWindowVisible(hWnd))
            {
                int length = GetWindowTextLength(hWnd);
                StringBuilder builder = new StringBuilder(length + 1);
                GetWindowText(hWnd, builder, builder.Capacity);
                found.Add(builder.ToString());
            }
            return true;
        }, IntPtr.Zero);
        return found.ToArray();
    }
}
"@
}

$SqliteHelper = Join-Path $SmokeRoot "query_sqlite.py"
$sqliteHelperSource = @'
"""Consulta de solo lectura usada por la verificacion de B13."""
import json
import sqlite3
import sys

connection = sqlite3.connect(sys.argv[1])
try:
    rows = connection.execute(sys.argv[2]).fetchall()
finally:
    connection.close()
print(json.dumps([list(row) for row in rows]))
'@
[System.IO.File]::WriteAllText($SqliteHelper, $sqliteHelperSource, (New-Object System.Text.UTF8Encoding($false)))

function Invoke-SqliteQuery {
    param([string]$DatabasePath, [string]$Sql)
    $raw = & $VenvPython $SqliteHelper $DatabasePath $Sql
    if ($LASTEXITCODE -ne 0) { throw "La consulta SQLite fallo: $Sql" }
    return ($raw | Out-String).Trim() | ConvertFrom-Json
}

function Start-IsolatedSirius {
    param([string]$ExePath, [string]$WorkDir, [hashtable]$Environment)
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $ExePath
    $startInfo.WorkingDirectory = $WorkDir
    $startInfo.UseShellExecute = $false
    $startInfo.EnvironmentVariables.Clear()
    foreach ($key in $Environment.Keys) {
        $startInfo.EnvironmentVariables[$key] = $Environment[$key]
    }
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    [void]$process.Start()
    return $process
}

function Stop-IsolatedSirius {
    param($Process)
    if ($Process.HasExited) { return }
    [void]$Process.CloseMainWindow()
    if (-not $Process.WaitForExit(4000)) {
        $Process.Kill()
        [void]$Process.WaitForExit(5000)
    }
}

function Invoke-SmokeLaunch {
    param([string]$Label)

    $process = Start-IsolatedSirius -ExePath $ExeCopy -WorkDir $WorkingDirectory -Environment $IsolatedEnv
    $databasePath = Join-Path $IsolatedData "sirius.db"
    $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    $titles = @()
    $sawWindow = $false

    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 500
        if ($process.HasExited) { break }
        $titles = @([SiriusWindowProbe]::VisibleTitles([uint32]$process.Id))
        if ($titles.Count -gt 0) { $sawWindow = $true; break }
    }

    $stillAlive = -not $process.HasExited
    if ($stillAlive -and -not $sawWindow) {
        $titles = @([SiriusWindowProbe]::VisibleTitles([uint32]$process.Id))
        $sawWindow = $titles.Count -gt 0
    }

    Test-Check "$Label - el proceso sigue vivo tras $StartupTimeoutSeconds s" $stillAlive (
        $(if ($process.HasExited) { "salio con codigo $($process.ExitCode)" } else { "" }))
    Test-Check "$Label - hay una ventana superior visible de Sirius" $sawWindow ("titulos: " + ($titles -join " | "))
    if ($titles.Count -gt 0) { Write-Info "Ventana: '$($titles -join "' | '")'" }

    # No basta con que exista "una ventana": tiene que ser la del flujo sin
    # clave. Solo se afirma si la precondicion de Credential Manager se cumple.
    $titleText = ($titles -join " | ")
    if ($NoKeyPreconditionMet) {
        Test-Check "$Label - la ventana es la del onboarding sin clave" (
            $titleText -like "*$OnboardingTitleFragment*") ("titulos: " + $titleText)
    }
    else {
        Add-Skip "$Label - la ventana es la del onboarding sin clave" (
            "la credencial de Sirius existe en esta sesion de Windows (estado: $CredentialState); " +
            "el flujo sin clave no es observable aqui")
    }

    Stop-IsolatedSirius -Process $process

    Test-Check "$Label - se creo sirius.db" (Test-Path -LiteralPath $databasePath)

    $logPath = Join-Path $IsolatedData "logs\application.log"
    Test-Check "$Label - se creo el registro local" (Test-Path -LiteralPath $logPath)
    if (Test-Path -LiteralPath $logPath) {
        $logText = Get-Content -LiteralPath $logPath -Raw
        Test-Check "$Label - sin RecursionError en el registro" (-not ($logText -match "RecursionError"))
        Test-Check "$Label - sin Traceback no controlado en el registro" (-not ($logText -match "Traceback \(most recent call last\)"))
        Test-Check "$Label - sin error de migraciones en el registro" (-not ($logText -match "(?i)alembic.*(error|failed)|no such table|Can't locate revision"))
        # Se comprueba "Sirius iniciando", no "Sirius iniciado". Motivo, medido y
        # reproducible tambien fuera del paquete: migrations/env.py llama a
        # fileConfig(alembic.ini) con el disable_existing_loggers=True que trae
        # logging por omision, y eso deja los loggers "sirius" y "sirius.main" con
        # disabled=True. Todo lo que Sirius registre DESPUES de migrar se pierde,
        # incluido "Sirius iniciado". Es un defecto de observabilidad de la
        # aplicacion (S13), ajeno al empaquetado, y por eso B13 no lo corrige.
        # Consecuencia para esta verificacion: las dos comprobaciones de arriba
        # sobre el registro solo cubren con certeza hasta el final de las
        # migraciones. El arranque completo se demuestra ademas por la ventana
        # visible y por el esquema en head.
        Test-Check "$Label - el registro confirma el inicio" ($logText -match "Sirius iniciando")
    }

    return $databasePath
}

# --------------------------------------------------------------------------
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
else {
    $script:TablesAfterFirst = @()
}

# --------------------------------------------------------------------------
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

# --------------------------------------------------------------------------
Write-Step "D. La configuracion real del usuario no se toco"

$RealPointerExistsAfter = Test-Path -LiteralPath $RealPointer
$RealPointerHashAfter = ""
if ($RealPointerExistsAfter) {
    $RealPointerHashAfter = (Get-FileHash -LiteralPath $RealPointer -Algorithm SHA256).Hash.ToLower()
}
Write-Info "Despues de arrancar -> existe: $RealPointerExistsAfter   hash: $(if ($RealPointerHashAfter) { $RealPointerHashAfter } else { '(no aplica)' })"

# Comprobaciones reales, no un mensaje informativo: si el ejecutable hubiera
# escrito el puntero del usuario pese al entorno redirigido, esto falla.
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

Test-Check "Los datos de prueba viven bajo la raiz temporal aislada" ($IsolatedData.StartsWith($SmokeRoot))
Test-Check "No se escribio ninguna clave en el entorno de prueba" (
    -not (Test-Path -LiteralPath (Join-Path $configDir "settings.json")) -or
    -not ((Get-Content -LiteralPath (Join-Path $configDir "settings.json") -Raw -ErrorAction SilentlyContinue) -match "sk-"))

# La credencial real solo se consulto por existencia; nunca se modifico.
$CredentialStateAfter = "ERROR NoProbe"
if (Test-Path -LiteralPath $VenvPython) {
    $probeOutputAfter = (& $VenvPython $CredentialProbe 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($probeOutputAfter)) {
        $CredentialStateAfter = ($probeOutputAfter -split "`n")[-1].Trim()
    }
}
Test-Check "La credencial de Windows sigue en el mismo estado que antes" (
    $CredentialStateAfter -eq $CredentialState) "antes $CredentialState / ahora $CredentialStateAfter"

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
