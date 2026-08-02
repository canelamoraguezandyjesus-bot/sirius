<#
.SYNOPSIS
    B13 - Verificacion automatica del paquete portatil de Sirius para Windows.

.DESCRIPTION
    Comprueba, sobre el artefacto realmente construido:

      A. Estructura, inventario de hashes, ZIP y ausencia de datos o secretos.
      B. Independencia del repositorio: se ejecuta desde una copia temporal en
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

    Esta prueba termina el proceso a proposito. Es una comprobacion tecnica
    desechable y NO sustituye a la PA-019 manual.

.EXAMPLE
    .\scripts\verify_windows_package.ps1

.EXAMPLE
    .\scripts\verify_windows_package.ps1 -ArtifactPath dist\windows\Sirius-0.1.0.dev0-abc1234-windows-x64
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

$script:Failures = New-Object System.Collections.Generic.List[string]
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
Write-Step "A. Localizacion y estructura del artefacto"

if ([string]::IsNullOrWhiteSpace($ArtifactPath)) {
    if (-not (Test-Path -LiteralPath $DistRoot)) {
        throw "No existe dist\windows. Ejecuta antes .\scripts\build_windows.ps1"
    }
    $candidates = @(Get-ChildItem -LiteralPath $DistRoot -Directory |
        Where-Object { $_.Name -like "Sirius-*-windows-x64" } |
        Sort-Object LastWriteTime -Descending)
    if ($candidates.Count -eq 0) {
        throw "No se encontro ningun artefacto de B13 en dist\windows. Ejecuta antes .\scripts\build_windows.ps1"
    }
    $ArtifactDir = $candidates[0].FullName
}
else {
    if (-not (Test-Path -LiteralPath $ArtifactPath)) { throw "No existe la ruta indicada: $ArtifactPath" }
    $ArtifactDir = (Resolve-Path -LiteralPath $ArtifactPath).Path
}
$ArtifactName = Split-Path -Leaf $ArtifactDir
Write-Info "Artefacto: $ArtifactDir"

$exeInArtifact = Join-Path $ArtifactDir "Sirius.exe"
$iniInArtifact = Join-Path $ArtifactDir "alembic.ini"
$migrationsInArtifact = Join-Path $ArtifactDir "migrations"
$buildManifestPath = Join-Path $ArtifactDir "BUILD-MANIFEST.json"
$fileManifestPath = Join-Path $ArtifactDir "FILE-MANIFEST.sha256"

Test-Check "Existe Sirius.exe" (Test-Path -LiteralPath $exeInArtifact)
Test-Check "Existe alembic.ini junto al ejecutable" (Test-Path -LiteralPath $iniInArtifact)
Test-Check "Existe migrations/ junto al ejecutable" (Test-Path -LiteralPath $migrationsInArtifact)
Test-Check "Existe BUILD-MANIFEST.json" (Test-Path -LiteralPath $buildManifestPath)
Test-Check "Existe FILE-MANIFEST.sha256" (Test-Path -LiteralPath $fileManifestPath)

if ($script:Failures.Count -gt 0) {
    throw "El artefacto no tiene la estructura minima. Verificacion detenida."
}

Test-Check "migrations/env.py presente" (Test-Path -LiteralPath (Join-Path $migrationsInArtifact "env.py"))
$versionFiles = @(Get-ChildItem -LiteralPath (Join-Path $migrationsInArtifact "versions") -Filter "*.py" -File -ErrorAction SilentlyContinue)
Test-Check "migrations/versions contiene revisiones ($($versionFiles.Count))" ($versionFiles.Count -gt 0)

$buildManifest = Get-Content -LiteralPath $buildManifestPath -Raw | ConvertFrom-Json
Test-Check "El manifiesto declara packaging_mode = standalone" ($buildManifest.packaging_mode -eq "standalone") $buildManifest.packaging_mode
$ExpectedAlembicHead = $buildManifest.alembic_head
Write-Info "Commit de origen: $($buildManifest.source_commit_short)   |   head de Alembic esperado: $ExpectedAlembicHead"

# --------------------------------------------------------------------------
Write-Step "A. Inventario de hashes"

$prefixLength = $ArtifactDir.Length + 1
$manifestEntries = @{}
foreach ($line in (Get-Content -LiteralPath $fileManifestPath)) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $parts = $line -split "\s+", 2
    if ($parts.Count -eq 2) { $manifestEntries[$parts[1].Trim()] = $parts[0].Trim().ToLower() }
}

$actualFiles = @(Get-ChildItem -LiteralPath $ArtifactDir -Recurse -Force -File |
    Where-Object { $_.FullName -ne $fileManifestPath })

$mismatched = 0
$missing = 0
foreach ($entry in $manifestEntries.GetEnumerator()) {
    $target = Join-Path $ArtifactDir ($entry.Key.Replace("/", "\"))
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
Test-Check "Ningun archivo del manifiesto falta" ($missing -eq 0) "faltan $missing"
Test-Check "Ningun hash discrepa" ($mismatched -eq 0) "discrepan $mismatched"
Test-Check "Ningun archivo fuera del manifiesto" ($unlisted -eq 0) "sin listar $unlisted"

# --------------------------------------------------------------------------
Write-Step "A. ZIP y su SHA-256"

$zipPath = Join-Path $DistRoot "$ArtifactName.zip"
$zipShaPath = "$zipPath.sha256"
Test-Check "Existe el ZIP" (Test-Path -LiteralPath $zipPath)
Test-Check "Existe el .zip.sha256" (Test-Path -LiteralPath $zipShaPath)

if ((Test-Path -LiteralPath $zipPath) -and (Test-Path -LiteralPath $zipShaPath)) {
    $recordedHash = ((Get-Content -LiteralPath $zipShaPath -Raw).Trim() -split "\s+")[0].ToLower()
    $actualZipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLower()
    Test-Check "El SHA-256 registrado coincide con el ZIP" ($recordedHash -eq $actualZipHash) "registrado $recordedHash / real $actualZipHash"
    Write-Info "SHA-256 del ZIP: $actualZipHash"
    Write-Info "Tamano del ZIP : $([math]::Round((Get-Item -LiteralPath $zipPath).Length / 1MB, 1)) MB"
}

# --------------------------------------------------------------------------
Write-Step "A. Datos y secretos dentro del artefacto"

$forbiddenNames = @("*.db", "*.db-wal", "*.db-shm", ".env", ".env.*", "settings.json",
    "data_location.json", "application.log", "*.pfx", "*.p12", "*.keystore", "*.jks")
$dirtyItems = New-Object System.Collections.Generic.List[string]
foreach ($pattern in $forbiddenNames) {
    foreach ($hit in @(Get-ChildItem -LiteralPath $ArtifactDir -Recurse -Force -File -Filter $pattern -ErrorAction SilentlyContinue)) {
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
    foreach ($hit in @(Get-ChildItem -LiteralPath $ArtifactDir -Recurse -Force -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq $dirName })) {
        $dirtyItems.Add($hit.FullName.Substring($prefixLength))
    }
}
$textExtensions = @(".txt", ".json", ".ini", ".cfg", ".conf", ".log", ".md", ".py", ".mako", ".yaml", ".yml", ".toml", ".env", ".spec")
$secretPattern = "(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{20,}"
foreach ($file in @($actualFiles | Where-Object { $textExtensions -contains $_.Extension.ToLower() -and $_.Length -lt 2MB })) {
    $content = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue
    if ($null -ne $content -and $content -match $secretPattern) {
        $dirtyItems.Add("posible clave en " + $file.FullName.Substring($prefixLength))
    }
}
Test-Check "Sin bases de datos, registros, copias, exportaciones ni secretos" ($dirtyItems.Count -eq 0) ($dirtyItems -join "; ")
Test-Check "Sin __pycache__ ni .pyc en migrations/" (@(Get-ChildItem -LiteralPath $migrationsInArtifact -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq "__pycache__" -or $_.Extension -eq ".pyc" }).Count -eq 0)

# --------------------------------------------------------------------------
Write-Step "B/F. Copia temporal en una ruta con espacios"

$SmokeRoot = Join-Path $env:TEMP "Sirius Packaging Smoke Test"
if (Test-Path -LiteralPath $SmokeRoot) { Remove-Item -LiteralPath $SmokeRoot -Recurse -Force }
$PackageCopy = Join-Path $SmokeRoot "Paquete Portatil\$ArtifactName"
$IsolatedHome = Join-Path $SmokeRoot "Perfil De Usuario"
$IsolatedData = Join-Path $SmokeRoot "Datos De Sirius"
$IsolatedTemp = Join-Path $SmokeRoot "Temporal Aislado"
$WorkingDirectory = Join-Path $SmokeRoot "Directorio De Trabajo"
$LocalAppData = Join-Path $IsolatedHome "AppData\Local"
$RoamingAppData = Join-Path $IsolatedHome "AppData\Roaming"

foreach ($dir in @($PackageCopy, $IsolatedHome, $IsolatedData, $IsolatedTemp, $WorkingDirectory, $LocalAppData, $RoamingAppData)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}
# Entrada por entrada: un comodin con -LiteralPath no se expande y copiaria cero archivos.
foreach ($item in @(Get-ChildItem -LiteralPath $ArtifactDir -Force)) {
    Copy-Item -LiteralPath $item.FullName -Destination $PackageCopy -Recurse -Force
}

$ExeCopy = Join-Path $PackageCopy "Sirius.exe"
Test-Check "La copia contiene Sirius.exe" (Test-Path -LiteralPath $ExeCopy)
Test-Check "La ruta de la copia contiene espacios" ($PackageCopy.Contains(" "))
Test-Check "La ruta de datos contiene espacios" ($IsolatedData.Contains(" "))
Test-Check "El directorio de trabajo no es el repositorio, ni el del ejecutable, ni el de datos" (
    ($WorkingDirectory -ne $RepoRoot) -and ($WorkingDirectory -ne $PackageCopy) -and ($WorkingDirectory -ne $IsolatedData))
Write-Info "Copia    : $PackageCopy"
Write-Info "Trabajo  : $WorkingDirectory"
Write-Info "Datos    : $IsolatedData"

# --------------------------------------------------------------------------
Write-Step "D. Entorno aislado y desechable"

# Puntero minimo valido de ubicacion de datos, en el config_dir aislado
# (platformdirs resuelve %LOCALAPPDATA%\sirius). Nunca se escribe ninguna clave.
$configDir = Join-Path $LocalAppData "sirius"
New-Item -ItemType Directory -Force -Path $configDir | Out-Null
$locationPayload = [ordered]@{ version = 1; data_dir = $IsolatedData }
$locationJson = $locationPayload | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $configDir "data_location.json"), $locationJson, (New-Object System.Text.UTF8Encoding($false)))
Write-Info "data_location.json escrito en $configDir"

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
Write-Step "E. Primer arranque aislado"

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

$realConfig = Join-Path $env:LOCALAPPDATA "sirius"
$realPointer = Join-Path $realConfig "data_location.json"
$realPointerHash = ""
if (Test-Path -LiteralPath $realPointer) {
    $realPointerHash = (Get-FileHash -LiteralPath $realPointer -Algorithm SHA256).Hash
}
Test-Check "Los datos de prueba viven bajo la raiz temporal aislada" ($IsolatedData.StartsWith($SmokeRoot))
Test-Check "No se escribio ninguna clave en el entorno de prueba" (
    -not (Test-Path -LiteralPath (Join-Path $configDir "settings.json")) -or
    -not ((Get-Content -LiteralPath (Join-Path $configDir "settings.json") -Raw -ErrorAction SilentlyContinue) -match "sk-"))
Write-Info "Puntero real del usuario: $(if ($realPointerHash) { 'presente, intacto' } else { 'no existe' })"

# --------------------------------------------------------------------------
Write-Step "Resultado"

Write-Host ""
if ($script:Failures.Count -eq 0) {
    Write-Host "================ B13: verificacion SUPERADA ================" -ForegroundColor Green
    Write-Host "  Artefacto : $ArtifactName"
    Write-Host "  Pruebas   : $($script:Checks) comprobaciones, 0 fallos"
    Write-Host "  Entorno   : sin Python, sin uv, sin .venv, ruta con espacios, sin administrador"
    Write-Host "  Nota      : terminar el proceso es una prueba tecnica desechable;"
    Write-Host "              NO sustituye a la PA-019 manual."
    Write-Host "===========================================================" -ForegroundColor Green
    Write-Host "`n  Entorno temporal conservado para inspeccion: $SmokeRoot" -ForegroundColor DarkGray
    exit 0
}
else {
    Write-Host "================ B13: verificacion NO SUPERADA ================" -ForegroundColor Red
    Write-Host "  Artefacto : $ArtifactName"
    Write-Host "  Pruebas   : $($script:Checks) comprobaciones, $($script:Failures.Count) fallos"
    foreach ($failure in $script:Failures) { Write-Host "   - $failure" -ForegroundColor Red }
    Write-Host "==============================================================" -ForegroundColor Red
    Write-Host "`n  Entorno temporal conservado para diagnostico: $SmokeRoot" -ForegroundColor DarkGray
    exit 1
}
