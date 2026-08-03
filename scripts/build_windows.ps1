<#
.SYNOPSIS
    B13 - Construccion canonica del paquete portatil de Sirius 0.1 para Windows 11 x64.

.DESCRIPTION
    Unico procedimiento de construccion soportado. Produce una distribucion
    STANDALONE (nunca onefile), sin instalador, sin firma y sin autoactualizacion,
    en:

        dist/windows/Sirius-<version>-<sha corto>-windows-x64/
        dist/windows/Sirius-<version>-<sha corto>-windows-x64.zip
        dist/windows/Sirius-<version>-<sha corto>-windows-x64.zip.sha256

    "Reproducible" aqui NO significa identidad binaria byte a byte. Significa
    mismo commit, dependencias bloqueadas por uv.lock, configuracion de
    despliegue versionada (pysidedeploy.spec), un unico comando, el mismo modo
    de Nuitka, la misma estructura de artefacto y un manifiesto con las
    versiones exactas del toolchain.

.EXAMPLE
    .\scripts\build_windows.ps1
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BuildDir = Join-Path $RepoRoot "build"
$PackagingDir = Join-Path $BuildDir "packaging"
$DeployDir = Join-Path $BuildDir "deploy"
$DistRoot = Join-Path $RepoRoot "dist\windows"
$VersionedSpec = Join-Path $RepoRoot "pysidedeploy.spec"
$WorkingSpec = Join-Path $PackagingDir "pysidedeploy.spec"
$DryRunFile = Join-Path $PackagingDir "pyside6-deploy-dry-run.txt"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$VenvDeploy = Join-Path $RepoRoot ".venv\Scripts\pyside6-deploy.exe"

$BuildStart = Get-Date

function Write-Step { param([string]$Text) Write-Host "`n=== $Text ===" -ForegroundColor Cyan }
function Write-Ok { param([string]$Text) Write-Host "  [ok] $Text" -ForegroundColor Green }
function Write-Warn2 { param([string]$Text) Write-Host "  [aviso] $Text" -ForegroundColor Yellow }

function Invoke-Native {
    <#  Ejecuta un binario y falla ante cualquier codigo de salida no cero.
        Devuelve la salida estandar como texto. #>
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$What
    )
    $output = & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$What fallo con codigo de salida $LASTEXITCODE."
    }
    if ($null -eq $output) { return "" }
    return ($output | Out-String)
}

function Write-Utf8NoBom {
    param([string]$Path, [string]$Content)
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Remove-Tree {
    <#  Borra EXCLUSIVAMENTE una ruta de salida propia de este script.
        No se usa git clean ni ningun borrado amplio.

        Se reintenta porque el arbol vive bajo OneDrive: la sincronizacion (o un
        antivirus) puede mantener un archivo abierto justo despues de crearlo, y
        un borrado incompleto deja restos que hacen fallar a Nuitka con
        "assert not os.path.isfile(...)" al regenerar el mismo modulo. #>
    param([string]$Path)
    for ($attempt = 1; $attempt -le 5; $attempt++) {
        if (-not (Test-Path -LiteralPath $Path)) { return }
        try {
            Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
        }
        catch {
            if ($attempt -eq 5) { throw "No se pudo eliminar '$Path' tras 5 intentos: $($_.Exception.Message)" }
            Start-Sleep -Seconds 2
        }
    }
    if (Test-Path -LiteralPath $Path) {
        throw "La ruta '$Path' sigue existiendo tras 5 intentos de borrado."
    }
}

# --------------------------------------------------------------------------
Write-Step "1/13 Entorno del sistema"

if (-not [System.Environment]::Is64BitOperatingSystem) {
    throw "B13 requiere Windows x64. Este sistema no es de 64 bits."
}
if (-not [System.Environment]::Is64BitProcess) {
    throw "Esta sesion de PowerShell es de 32 bits. Usa PowerShell x64."
}
$osCaption = (Get-CimInstance Win32_OperatingSystem).Caption
$osVersion = [System.Environment]::OSVersion.Version.ToString()
$WindowsVersion = "$osCaption $osVersion"
Write-Ok "Windows: $WindowsVersion ($env:PROCESSOR_ARCHITECTURE)"
Write-Ok "PowerShell: $($PSVersionTable.PSVersion.ToString())"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warn2 "Esta sesion esta elevada. Sirius no necesita administrador; la verificacion debe ejecutarse sin elevar."
}

# --------------------------------------------------------------------------
Write-Step "2/13 Estado del repositorio"

Push-Location $RepoRoot
try {
    $SourceCommit = (Invoke-Native "git" @("rev-parse", "HEAD") "git rev-parse HEAD").Trim()
    $SourceCommitShort = (Invoke-Native "git" @("rev-parse", "--short", "HEAD") "git rev-parse --short HEAD").Trim()
    $branchRaw = (& git rev-parse --abbrev-ref HEAD | Out-String).Trim()
    $SourceBranch = $branchRaw

    $status = (& git status --porcelain | Out-String).Trim()
    $SourceDirty = -not [string]::IsNullOrWhiteSpace($status)

    & git rev-parse --verify --quiet "refs/remotes/origin/main" > $null 2>$null
    $hasOriginMain = ($LASTEXITCODE -eq 0)
    $OriginMainCommit = ""
    $DescendsFromOriginMain = $false
    if ($hasOriginMain) {
        $OriginMainCommit = (Invoke-Native "git" @("rev-parse", "origin/main") "git rev-parse origin/main").Trim()
        & git merge-base --is-ancestor $OriginMainCommit $SourceCommit
        $DescendsFromOriginMain = ($LASTEXITCODE -eq 0)
    }
    else {
        throw "No existe la referencia origin/main. Ejecuta 'git fetch origin' antes de construir."
    }
}
finally {
    Pop-Location
}

Write-Ok "Commit de origen: $SourceCommit ($SourceCommitShort)"
Write-Ok "Rama: $SourceBranch"
Write-Ok "origin/main: $OriginMainCommit"
if ($DescendsFromOriginMain) {
    Write-Ok "El commit de origen desciende de origin/main."
}
else {
    Write-Warn2 "El commit de origen NO desciende de origin/main. Queda registrado en el manifiesto."
}
if ($SourceDirty) {
    # Se aborta, no se avisa. El artefacto se nombra con el sha corto de HEAD y
    # el manifiesto declara source_commit = HEAD, pero lo que Nuitka compila es
    # el arbol de trabajo. Con cambios sin confirmar esas dos cosas dejan de ser
    # la misma: dos ejecutables materialmente distintos podrian repartirse con
    # la misma procedencia, y una edicion local sin revisar viajaria bajo un SHA
    # revisado. Un paquete no puede atribuirse a HEAD si su contenido real no es
    # el de HEAD, asi que aqui no hay nada que registrar: hay que parar.
    #
    # Antes de MSVC, de uv y de compilar, para no dejar a medias un entorno ni
    # gastar varios minutos en un artefacto que no seria atribuible.
    Write-Host ""
    Write-Host "  El arbol de trabajo tiene cambios sin confirmar:" -ForegroundColor Red
    foreach ($line in ($status -split "`n")) {
        if (-not [string]::IsNullOrWhiteSpace($line)) { Write-Host "    $($line.TrimEnd())" -ForegroundColor Red }
    }
    Write-Host ""
    throw ("El empaquetado exige un arbol limpio. El artefacto se nombraria con $SourceCommitShort y " +
        "el manifiesto declararia source_commit=$SourceCommit, pero se compilaria el arbol de trabajo, " +
        "que no coincide con ese commit. Confirma o descarta los cambios y vuelve a construir. " +
        "Todo artefacto valido de B13 lleva source_dirty=false.")
}
Write-Ok "Arbol de trabajo limpio."

# --------------------------------------------------------------------------
Write-Step "3/13 Entorno de compilacion MSVC x64"

$vsWhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vsWhere)) {
    throw "BLOCKED_EXTERNAL_TOOLCHAIN: no se encontro vswhere.exe en '$vsWhere'. Falta Visual Studio Build Tools 2022."
}

$vsInstallPath = (& $vsWhere -products * -latest -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Out-String).Trim()
if ([string]::IsNullOrWhiteSpace($vsInstallPath)) {
    throw "BLOCKED_EXTERNAL_TOOLCHAIN: no hay ninguna instalacion de Visual Studio con el componente MSVC v143 x64 (VC.Tools.x86.x64)."
}
$VsDevCmd = Join-Path $vsInstallPath "Common7\Tools\VsDevCmd.bat"
if (-not (Test-Path -LiteralPath $VsDevCmd)) {
    throw "BLOCKED_EXTERNAL_TOOLCHAIN: no se encontro VsDevCmd.bat en '$VsDevCmd'."
}
Write-Ok "Visual Studio: $vsInstallPath"

# Carga el entorno x64 en ESTA sesion, para no obligar a abrir manualmente una
# "Developer PowerShell". Se vuelca el entorno del .bat y se importa aqui.
New-Item -ItemType Directory -Force -Path $PackagingDir | Out-Null
$envDump = Join-Path $PackagingDir "msvc-env.txt"
$loadEnvCmd = Join-Path $PackagingDir "load-msvc-env.cmd"
# VsDevCmd.bat invoca vswhere.exe por nombre; sin el directorio del instalador en
# el PATH imprime un error enganoso aunque termine bien.
$vsInstallerDir = Split-Path -Parent $vsWhere
$loadEnvBody = @"
@echo off
set "PATH=%PATH%;$vsInstallerDir"
call "$VsDevCmd" -arch=x64 -host_arch=x64 -no_logo
if errorlevel 1 exit /b 1
set > "$envDump"
"@
Write-Utf8NoBom -Path $loadEnvCmd -Content $loadEnvBody
& cmd.exe /c "`"$loadEnvCmd`""
if ($LASTEXITCODE -ne 0) {
    throw "BLOCKED_EXTERNAL_TOOLCHAIN: VsDevCmd.bat -arch=x64 fallo con codigo $LASTEXITCODE."
}

foreach ($line in Get-Content -LiteralPath $envDump) {
    $idx = $line.IndexOf("=")
    if ($idx -gt 0) {
        $name = $line.Substring(0, $idx)
        $value = $line.Substring($idx + 1)
        if ($name -notmatch "^(PROMPT|_.*)$") {
            Set-Item -Path ("Env:" + $name) -Value $value -ErrorAction SilentlyContinue
        }
    }
}

$clPath = (Get-Command cl.exe -ErrorAction SilentlyContinue)
$dumpbinPath = (Get-Command dumpbin.exe -ErrorAction SilentlyContinue)
if ($null -eq $clPath) {
    throw "BLOCKED_EXTERNAL_TOOLCHAIN: cl.exe sigue sin estar disponible tras cargar VsDevCmd.bat."
}
if ($null -eq $dumpbinPath) {
    throw "BLOCKED_EXTERNAL_TOOLCHAIN: dumpbin.exe sigue sin estar disponible tras cargar VsDevCmd.bat."
}
if ($clPath.Source -notmatch "Hostx64\\x64") {
    throw "cl.exe no es el compilador x64 alojado en x64: $($clPath.Source)"
}
Write-Ok "cl.exe: $($clPath.Source)"
Write-Ok "dumpbin.exe: $($dumpbinPath.Source)"

$clBanner = (& cmd.exe /c "cl 2>&1" | Select-Object -First 1 | Out-String).Trim()
$CompilerVersion = "desconocida"
if ($clBanner -match "(\d+\.\d+\.\d+(\.\d+)?)") { $CompilerVersion = $Matches[1] }
$WindowsSdk = "desconocido"
if (Test-Path Env:WindowsSDKVersion) { $WindowsSdk = ($env:WindowsSDKVersion).TrimEnd("\") }
$VcToolsVersion = "desconocida"
if (Test-Path Env:VCToolsVersion) { $VcToolsVersion = $env:VCToolsVersion }
Write-Ok "MSVC cl $CompilerVersion (toolset $VcToolsVersion), Windows SDK $WindowsSdk"

# --------------------------------------------------------------------------
Write-Step "4/13 Interprete y dependencias bloqueadas"

$UvVersion = (Invoke-Native "uv" @("--version") "uv --version").Trim()
Write-Ok "uv: $UvVersion"

Push-Location $RepoRoot
try {
    Invoke-Native "uv" @("lock", "--check") "uv lock --check" | Out-Null
    Write-Ok "uv.lock coherente con pyproject.toml."
    # --no-default-groups es imprescindible: pyproject.toml declara
    # default-groups = ["dev"], asi que "uv sync --frozen --group packaging"
    # instalaba dev ADEMAS de packaging, justo lo contrario del entorno aislado
    # que documenta B13. No es teorico: en la construccion registrada Nuitka
    # llego a arrastrar mypy por importacion estatica. El aislamiento se
    # consigue no instalando el grupo, no tapandolo con exclusiones de Nuitka.
    Invoke-Native "uv" @("sync", "--frozen", "--no-default-groups", "--group", "packaging") `
        "uv sync --frozen --no-default-groups --group packaging" | Out-Null
    Write-Ok "Entorno sincronizado desde uv.lock: grupo 'packaging', sin los grupos por omision."
}
finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $VenvPython)) { throw "No existe el interprete del entorno: $VenvPython" }
if (-not (Test-Path -LiteralPath $VenvDeploy)) { throw "No existe pyside6-deploy en el entorno: $VenvDeploy" }

# El aislamiento se comprueba, no se supone: el entorno debe traer lo normal del
# proyecto y lo de packaging, y NO las herramientas exclusivas de desarrollo.
$RequiredDistributions = @("PySide6", "nuitka", "alembic", "SQLAlchemy", "keyring")
$ForbiddenDistributions = @("mypy", "pytest", "ruff", "pytest-qt", "pytest-cov")
$probeSource = @'
"""Inventario del entorno de empaquetado. No instala ni modifica nada."""

import importlib.metadata as metadata
import sys

required = [name for name in sys.argv[1].split(",") if name]
forbidden = [name for name in sys.argv[2].split(",") if name]
absent, present = [], []
for name in required:
    try:
        metadata.version(name)
    except metadata.PackageNotFoundError:
        absent.append(name)
for name in forbidden:
    try:
        metadata.version(name)
        present.append(name)
    except metadata.PackageNotFoundError:
        pass
print("FALTAN=" + ",".join(absent))
print("SOBRAN=" + ",".join(present))
'@
$probePath = Join-Path $PackagingDir "probe-environment.py"
Write-Utf8NoBom -Path $probePath -Content $probeSource
$probeOutput = (Invoke-Native $VenvPython @($probePath, ($RequiredDistributions -join ","), ($ForbiddenDistributions -join ",")) "inventario del entorno" | Out-String)
$absentRequired = (($probeOutput -split "`n" | Where-Object { $_ -like "FALTAN=*" }) -join "").Replace("FALTAN=", "").Trim()
$presentForbidden = (($probeOutput -split "`n" | Where-Object { $_ -like "SOBRAN=*" }) -join "").Replace("SOBRAN=", "").Trim()

if (-not [string]::IsNullOrWhiteSpace($absentRequired)) {
    throw "El entorno de empaquetado no tiene dependencias necesarias: $absentRequired"
}
if (-not [string]::IsNullOrWhiteSpace($presentForbidden)) {
    throw ("El entorno de empaquetado contiene herramientas exclusivas de desarrollo: $presentForbidden. " +
        "Debe sincronizarse con --no-default-groups para que el grupo 'dev' no entre.")
}
Write-Ok "Entorno aislado: estan $($RequiredDistributions -join ', '); no esta ninguna de $($ForbiddenDistributions -join ', ')."

$PythonVersion = (Invoke-Native $VenvPython @("-c", "import platform; print(platform.python_version())") "python --version").Trim()
if ($PythonVersion -notmatch "^3\.14\.") {
    throw "Se requiere Python 3.14.x. El entorno tiene $PythonVersion."
}
$pythonBits = (Invoke-Native $VenvPython @("-c", "import struct; print(struct.calcsize('P')*8)") "python bits").Trim()
if ($pythonBits -ne "64") {
    throw "El interprete de Python no es de 64 bits (detectado: $pythonBits bits)."
}
Write-Ok "Python: $PythonVersion (64 bits)"

$PySide6Version = (Invoke-Native $VenvPython @("-c", "import PySide6; print(PySide6.__version__)") "PySide6 version").Trim()
$QtVersion = (Invoke-Native $VenvPython @("-c", "from PySide6.QtCore import qVersion; print(qVersion())") "Qt version").Trim()
$NuitkaVersion = (Invoke-Native $VenvPython @("-c", "import importlib.metadata as m; print(m.version('nuitka'))") "Nuitka version").Trim()
Write-Ok "PySide6 $PySide6Version / Qt $QtVersion / Nuitka $NuitkaVersion"

$AppVersion = ""
foreach ($line in Get-Content -LiteralPath (Join-Path $RepoRoot "pyproject.toml")) {
    if ($line -match '^\s*version\s*=\s*"([^"]+)"') { $AppVersion = $Matches[1]; break }
}
if ([string]::IsNullOrWhiteSpace($AppVersion)) { throw "No se pudo leer la version del proyecto en pyproject.toml." }
Write-Ok "Version de aplicacion: $AppVersion"

$AlembicHead = (Invoke-Native $VenvPython @("-c", "from sirius.adapters.persistence.migrations import get_supported_schema_version as v; print(v())") "alembic head").Trim()
Write-Ok "Head de Alembic: $AlembicHead"

# --------------------------------------------------------------------------
Write-Step "5/13 Configuracion de despliegue"

if (-not (Test-Path -LiteralPath $VersionedSpec)) { throw "Falta pysidedeploy.spec en la raiz del repositorio." }

# La configuracion versionada no puede contener rutas absolutas del equipo que
# construye: debe servir igual desde cualquier otro checkout.
$specText = Get-Content -LiteralPath $VersionedSpec -Raw
$forbiddenPatterns = @(
    '[A-Za-z]:\\',
    '\.venv',
    '\$env:',
    '%TEMP%',
    '%USERPROFILE%'
)
foreach ($pattern in $forbiddenPatterns) {
    if ($specText -match $pattern) {
        throw "pysidedeploy.spec contiene una ruta local o absoluta (patron '$pattern'). La configuracion versionada debe ser relativa y portable."
    }
}
if ($specText -notmatch "(?m)^\s*mode\s*=\s*standalone\s*$") {
    throw "pysidedeploy.spec no declara 'mode = standalone'. B13 no admite onefile."
}
Write-Ok "pysidedeploy.spec es portable y declara mode = standalone."

# Copia de trabajo con rutas absolutas resueltas. pyside6-deploy reescribe el
# archivo de configuracion que se le pasa, asi que nunca se le entrega el
# archivo versionado: de ese modo el arbol de Git no se ensucia al construir.
$workingSpecText = $specText
$workingSpecText = $workingSpecText -replace "(?m)^\s*project_dir\s*=.*$", ("project_dir = " + $RepoRoot.Replace('$', '$$'))
$workingSpecText = $workingSpecText -replace "(?m)^\s*input_file\s*=.*$", ("input_file = " + (Join-Path $RepoRoot "src\sirius\__main__.py").Replace('$', '$$'))
$workingSpecText = $workingSpecText -replace "(?m)^\s*exec_directory\s*=.*$", ("exec_directory = " + $DeployDir.Replace('$', '$$'))
Write-Utf8NoBom -Path $WorkingSpec -Content $workingSpecText
Write-Ok "Copia de trabajo: $WorkingSpec"

# --------------------------------------------------------------------------
Write-Step "6/13 Limpieza de las salidas propias"

$ArtifactName = "Sirius-$AppVersion-$SourceCommitShort-windows-x64"
$ArtifactDir = Join-Path $DistRoot $ArtifactName
$ZipPath = Join-Path $DistRoot "$ArtifactName.zip"
$ZipShaPath = "$ZipPath.sha256"
$NuitkaScratch = Join-Path $RepoRoot "src\sirius\deployment"

Remove-Tree $DeployDir
Remove-Tree $NuitkaScratch
Remove-Tree $ArtifactDir
if (Test-Path -LiteralPath $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
if (Test-Path -LiteralPath $ZipShaPath) { Remove-Item -LiteralPath $ZipShaPath -Force }
Write-Ok "Salidas anteriores eliminadas (solo rutas propias de este script)."

# --------------------------------------------------------------------------
Write-Step "7/13 Dry-run de pyside6-deploy"

$dryRunCmdFile = Join-Path $PackagingDir "run-dry-run.cmd"
$dryRunBody = @"
@echo off
cd /d "$RepoRoot"
"$VenvDeploy" -c "$WorkingSpec" --dry-run > "$DryRunFile" 2>&1
exit /b %errorlevel%
"@
Write-Utf8NoBom -Path $dryRunCmdFile -Content $dryRunBody
& cmd.exe /c "`"$dryRunCmdFile`""
if ($LASTEXITCODE -ne 0) {
    Write-Host (Get-Content -LiteralPath $DryRunFile -Raw)
    throw "pyside6-deploy --dry-run fallo con codigo $LASTEXITCODE."
}

$dryRunText = Get-Content -LiteralPath $DryRunFile -Raw
if ($dryRunText -match "--onefile") {
    throw "El comando efectivo de Nuitka contiene --onefile. B13 exige standalone; construccion detenida."
}
if ($dryRunText -notmatch "--standalone") {
    throw "El comando efectivo de Nuitka no contiene --standalone."
}
if ($dryRunText -notmatch "--windows-console-mode=disable") {
    throw "El comando efectivo de Nuitka no desactiva la consola."
}
if ($dryRunText -notmatch "--output-filename=Sirius\.exe") {
    throw "El comando efectivo de Nuitka no nombra el ejecutable Sirius.exe."
}
# Alembic ejecuta migrations/env.py y migrations/versions/*.py desde disco, no
# los importa. Sin estas dos inclusiones el binario compila igual y despues
# muere al migrar con ModuleNotFoundError, que es justo el fallo que estas dos
# comprobaciones existen para impedir que vuelva sin avisar.
if ($dryRunText -notmatch "--include-module=logging\.config") {
    throw "El comando efectivo de Nuitka no incluye logging.config, que necesita migrations/env.py."
}
if ($dryRunText -notmatch "--include-package=alembic") {
    throw "El comando efectivo de Nuitka no incluye el paquete alembic, que necesitan las revisiones de migracion."
}
Write-Ok "Comando efectivo guardado en build/packaging/pyside6-deploy-dry-run.txt"
Write-Ok "Modo standalone confirmado; sin onefile; sin consola."

$NuitkaCommand = ""
foreach ($line in (Get-Content -LiteralPath $DryRunFile)) {
    if ($line -match "-m nuitka ") { $NuitkaCommand = $line.Trim() }
}

# --------------------------------------------------------------------------
Write-Step "8/13 Compilacion con Nuitka (standalone)"

$stamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
$BuildLog = Join-Path $PackagingDir "build-$stamp.log"
$deployCmdFile = Join-Path $PackagingDir "run-deploy.cmd"
$deployBody = @"
@echo off
cd /d "$RepoRoot"
"$VenvDeploy" -c "$WorkingSpec" -v > "$BuildLog" 2>&1
exit /b %errorlevel%
"@
Write-Utf8NoBom -Path $deployCmdFile -Content $deployBody

Write-Host "  Compilando. Esto tarda varios minutos..."
$compileStart = Get-Date
& cmd.exe /c "`"$deployCmdFile`""
$deployExit = $LASTEXITCODE
$compileSeconds = [math]::Round(((Get-Date) - $compileStart).TotalSeconds, 1)

# Cuando Nuitka aborta deja un nuitka-crash-report.xml en el directorio actual,
# es decir en la raiz del repositorio. Se traslada a build/packaging/ para
# conservarlo como evidencia sin ensuciar el arbol de Git, que tiene que quedar
# limpio.
$crashReport = Join-Path $RepoRoot "nuitka-crash-report.xml"
if (Test-Path -LiteralPath $crashReport) {
    $preservedCrashReport = Join-Path $PackagingDir "nuitka-crash-report-$stamp.xml"
    Move-Item -LiteralPath $crashReport -Destination $preservedCrashReport -Force
    Write-Warn2 "Nuitka dejo un informe de fallo. Conservado en: $preservedCrashReport"
}

if ($deployExit -ne 0) {
    Write-Host "`n--- ultimas 60 lineas del log de construccion ---"
    Get-Content -LiteralPath $BuildLog -Tail 60 | ForEach-Object { Write-Host $_ }
    throw "pyside6-deploy fallo con codigo $deployExit. Log completo: $BuildLog"
}

$logText = Get-Content -LiteralPath $BuildLog -Raw
if ($logText -match "\[DEPLOY\] Exception occurred") {
    Write-Host "`n--- ultimas 60 lineas del log de construccion ---"
    Get-Content -LiteralPath $BuildLog -Tail 60 | ForEach-Object { Write-Host $_ }
    throw "pyside6-deploy informo de una excepcion. Log completo: $BuildLog"
}

$DeployedDist = Join-Path $DeployDir "Sirius.dist"
$DeployedExe = Join-Path $DeployDir "Sirius.dist\Sirius.exe"
if (-not (Test-Path -LiteralPath $DeployedExe)) {
    throw "La compilacion no produjo $DeployedExe. Log completo: $BuildLog"
}
# Si Nuitka aborta a medias, pyside6-deploy todavia puede copiar un .dist
# sobrante de una compilacion anterior. Un ejecutable mas antiguo que esta
# ejecucion significa exactamente eso, y jamas debe empaquetarse.
$exeWritten = (Get-Item -LiteralPath $DeployedExe).LastWriteTime
if ($exeWritten -lt $compileStart) {
    throw "Sirius.exe es anterior al inicio de esta compilacion ($exeWritten < $compileStart): seria un binario sobrante. Log completo: $BuildLog"
}
Write-Ok "Compilacion correcta en $compileSeconds s. Log: $BuildLog"

# pyside6-deploy intenta purgar su directorio intermedio, pero se traga el
# PermissionError y solo avisa, asi que puede dejar mas de 1 GB de restos DENTRO
# de src/. Eso ensucia el arbol de Git y, peor, deja archivos module.*.c rancios
# que hacen fallar la siguiente compilacion con "assert not os.path.isfile(...)".
# Se limpia aqui de forma explicita y con reintentos. Si la compilacion hubiera
# fallado no se llega a este punto, y el scratch se conserva para diagnostico.
Remove-Tree $NuitkaScratch
Write-Ok "Directorio intermedio de Nuitka eliminado de src/ (el arbol de Git queda limpio)."

# --------------------------------------------------------------------------
Write-Step "9/13 Montaje del artefacto"

New-Item -ItemType Directory -Force -Path $ArtifactDir | Out-Null
# Se copia entrada por entrada con -LiteralPath. Un comodin combinado con
# -LiteralPath no se expande y copiaria CERO archivos sin fallar.
foreach ($item in @(Get-ChildItem -LiteralPath $DeployedDist -Force)) {
    Copy-Item -LiteralPath $item.FullName -Destination $ArtifactDir -Recurse -Force
}
$stagedExe = Join-Path $ArtifactDir "Sirius.exe"
if (-not (Test-Path -LiteralPath $stagedExe)) {
    throw "El montaje no dejo Sirius.exe en $ArtifactDir."
}
$stagedCount = @(Get-ChildItem -LiteralPath $ArtifactDir -Recurse -Force -File).Count
if ($stagedCount -lt 50) {
    throw "El montaje solo dejo $stagedCount archivos en el artefacto. La copia de la salida de Nuitka esta incompleta."
}
Write-Ok "Salida de Nuitka copiada a $ArtifactName ($stagedCount archivos)"

# alembic.ini y migrations/ viajan JUNTO al ejecutable porque el resolvedor
# empaquetado (sirius.adapters.persistence.migrations._resource_root) los busca
# en Path(sys.executable).parent cuando detecta que corre compilado.
Copy-Item -LiteralPath (Join-Path $RepoRoot "alembic.ini") -Destination (Join-Path $ArtifactDir "alembic.ini") -Force

# Solo archivos realmente versionados en Git, conservando la estructura. Nunca
# una copia a ciegas del directorio: eso arrastraria __pycache__, .pyc y
# cualquier resto local.
Push-Location $RepoRoot
try {
    $migrationFiles = @(& git ls-files migrations)
    if ($LASTEXITCODE -ne 0) { throw "git ls-files migrations fallo." }
}
finally {
    Pop-Location
}
if ($migrationFiles.Count -eq 0) { throw "git ls-files no devolvio ningun archivo de migraciones." }

$copiedMigrations = 0
foreach ($relative in $migrationFiles) {
    if ([string]::IsNullOrWhiteSpace($relative)) { continue }
    $normalized = $relative.Replace("/", "\")
    $source = Join-Path $RepoRoot $normalized
    if (-not (Test-Path -LiteralPath $source)) { continue }
    $target = Join-Path $ArtifactDir $normalized
    $targetParent = Split-Path -Parent $target
    if (-not (Test-Path -LiteralPath $targetParent)) {
        New-Item -ItemType Directory -Force -Path $targetParent | Out-Null
    }
    Copy-Item -LiteralPath $source -Destination $target -Force
    $copiedMigrations++
}
Write-Ok "alembic.ini y $copiedMigrations archivos de migraciones versionados copiados junto a Sirius.exe"

# --------------------------------------------------------------------------
Write-Step "10/13 Comprobacion de contaminacion"

$forbiddenNames = @("*.db", "*.db-wal", "*.db-shm", ".env", ".env.*", "settings.json",
    "data_location.json", "application.log", "*.pfx", "*.p12", "*.keystore", "*.jks")
$contamination = New-Object System.Collections.Generic.List[string]

foreach ($pattern in $forbiddenNames) {
    $hits = @(Get-ChildItem -LiteralPath $ArtifactDir -Recurse -Force -File -Filter $pattern -ErrorAction SilentlyContinue)
    foreach ($hit in $hits) {
        $contamination.Add("archivo prohibido: " + $hit.FullName.Substring($ArtifactDir.Length + 1))
    }
}

# Certificados: lo que no puede viajar es material de clave PRIVADA. Un almacen
# publico de CA si es legitimo y ademas necesario -- certifi/cacert.pem es el que
# usa el cliente HTTPS para verificar al proveedor. Por eso no se juzga por la
# extension, sino por el contenido.
$certificateFiles = @(Get-ChildItem -LiteralPath $ArtifactDir -Recurse -Force -File -ErrorAction SilentlyContinue |
    Where-Object { @(".pem", ".crt", ".cer", ".key") -contains $_.Extension.ToLower() })
foreach ($certificate in $certificateFiles) {
    $relativeCertificate = $certificate.FullName.Substring($ArtifactDir.Length + 1)
    $certificateText = ""
    if ($certificate.Length -lt 8MB) {
        $certificateText = Get-Content -LiteralPath $certificate.FullName -Raw -ErrorAction SilentlyContinue
    }
    if ($null -ne $certificateText -and $certificateText -match "-----BEGIN [A-Z ]*PRIVATE KEY-----") {
        $contamination.Add("clave privada en: $relativeCertificate")
    }
    else {
        Write-Warn2 "Certificado publico incluido (sin clave privada): $relativeCertificate"
    }
}

foreach ($dirName in @("logs", "backups", "exports")) {
    $hits = @(Get-ChildItem -LiteralPath $ArtifactDir -Recurse -Force -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq $dirName })
    foreach ($hit in $hits) {
        $contamination.Add("carpeta prohibida: " + $hit.FullName.Substring($ArtifactDir.Length + 1))
    }
}

# Herramienta de desarrollo que no debe viajar en un artefacto de usuario.
# sqlalchemy.ext.mypy y pydantic.mypy la importan de forma estatica, asi que sin
# --nofollow-import-to=mypy se cuela entera y engorda el paquete 22 MB.
foreach ($devLeftover in @("mypy", "ast_serialize", "librt")) {
    $devPath = Join-Path $ArtifactDir $devLeftover
    if (Test-Path -LiteralPath $devPath) {
        $contamination.Add("herramienta de desarrollo incluida: $devLeftover")
    }
}
foreach ($mypycBinary in @(Get-ChildItem -LiteralPath $ArtifactDir -Force -File -Filter "*__mypyc.pyd" -ErrorAction SilentlyContinue)) {
    $contamination.Add("binario de mypyc incluido: " + $mypycBinary.Name)
}

# Nombres que delatan una ruta de usuario copiada como si fuera un archivo.
$userPathLike = @(Get-ChildItem -LiteralPath $ArtifactDir -Recurse -Force -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match "^[A-Za-z]:" -or $_.Name -match "Users" })
foreach ($hit in $userPathLike) {
    $contamination.Add("ruta de usuario copiada como archivo: " + $hit.FullName.Substring($ArtifactDir.Length + 1))
}

# Rastreo de posibles claves, limitado a archivos de texto razonables. Nunca se
# imprime el contenido: solo la ruta.
$textExtensions = @(".txt", ".json", ".ini", ".cfg", ".conf", ".log", ".md", ".py",
    ".mako", ".yaml", ".yml", ".toml", ".env", ".spec")
$secretPattern = "(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{20,}"
$textFiles = @(Get-ChildItem -LiteralPath $ArtifactDir -Recurse -Force -File -ErrorAction SilentlyContinue |
    Where-Object { $textExtensions -contains $_.Extension.ToLower() -and $_.Length -lt 2MB })
foreach ($file in $textFiles) {
    $content = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue
    if ($null -ne $content -and $content -match $secretPattern) {
        $contamination.Add("posible clave en: " + $file.FullName.Substring($ArtifactDir.Length + 1))
    }
}

if ($contamination.Count -gt 0) {
    Write-Host "`nEl artefacto esta contaminado:" -ForegroundColor Red
    foreach ($item in $contamination) { Write-Host "  - $item" -ForegroundColor Red }
    throw "Construccion detenida: el artefacto contiene datos, secretos o restos locales."
}
Write-Ok "Sin bases de datos, secretos, registros, copias, exportaciones ni configuracion personal."

# --------------------------------------------------------------------------
Write-Step "11/13 Manifiesto de construccion"

$BuildCommand = ".\scripts\build_windows.ps1"
$manifest = [ordered]@{
    product                 = "Sirius"
    app_version             = $AppVersion
    source_commit           = $SourceCommit
    source_commit_short     = $SourceCommitShort
    source_branch           = $SourceBranch
    source_dirty            = $SourceDirty
    source_origin_main      = $OriginMainCommit
    descends_from_origin_main = $DescendsFromOriginMain
    built_at_utc            = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    windows_version         = $WindowsVersion
    architecture            = "x64"
    python_version          = $PythonVersion
    uv_version              = $UvVersion
    pyside6_version         = $PySide6Version
    qt_version              = $QtVersion
    pyside6_deploy_version  = "incluido en PySide6 $PySide6Version"
    nuitka_version          = $NuitkaVersion
    compiler                = "MSVC (Visual Studio Build Tools 2022, Hostx64/x64)"
    compiler_version        = "cl $CompilerVersion (toolset MSVC $VcToolsVersion)"
    windows_sdk             = $WindowsSdk
    packaging_mode          = "standalone"
    entrypoint              = "src/sirius/__main__.py"
    artifact_directory      = "dist/windows/$ArtifactName"
    alembic_head            = $AlembicHead
    build_command           = $BuildCommand
    verification_status     = "pendiente: ejecuta .\scripts\verify_windows_package.ps1"
    reproducibility_note    = "No se afirma reproducibilidad binaria bit a bit. Dos construcciones del mismo commit NO tienen por que producir binarios ni ZIP con el mismo hash: la compilacion incorpora marcas temporales y rutas de construccion. Lo que B13 garantiza es el mismo commit de origen, dependencias bloqueadas por uv.lock, configuracion de despliegue versionada, un unico comando canonico, el mismo modo de Nuitka, la misma estructura de artefacto y las versiones exactas del toolchain registradas aqui."
}
$manifestPath = Join-Path $ArtifactDir "BUILD-MANIFEST.json"
Write-Utf8NoBom -Path $manifestPath -Content (($manifest | ConvertTo-Json -Depth 5) + "`n")
Write-Ok "BUILD-MANIFEST.json escrito."

# --------------------------------------------------------------------------
Write-Step "12/13 Inventario de hashes"

$manifestFileName = "FILE-MANIFEST.sha256"
$fileManifestPath = Join-Path $ArtifactDir $manifestFileName
$prefixLength = $ArtifactDir.Length + 1
$allFiles = @(Get-ChildItem -LiteralPath $ArtifactDir -Recurse -Force -File |
    Where-Object { $_.FullName -ne $fileManifestPath } |
    Sort-Object FullName)

$lines = New-Object System.Collections.Generic.List[string]
foreach ($file in $allFiles) {
    $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLower()
    $relative = $file.FullName.Substring($prefixLength).Replace("\", "/")
    $lines.Add("$hash  $relative")
}
Write-Utf8NoBom -Path $fileManifestPath -Content (($lines -join "`n") + "`n")
Write-Ok "$($lines.Count) archivos inventariados en FILE-MANIFEST.sha256"

# --------------------------------------------------------------------------
Write-Step "13/13 Comprimido y hash"

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $ArtifactDir, $ZipPath,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $true)

$zipHash = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash.ToLower()
Write-Utf8NoBom -Path $ZipShaPath -Content ("$zipHash  $ArtifactName.zip`n")

$distBytes = ($allFiles | Measure-Object -Property Length -Sum).Sum
$zipBytes = (Get-Item -LiteralPath $ZipPath).Length
$totalSeconds = [math]::Round(((Get-Date) - $BuildStart).TotalSeconds, 1)

Write-Host ""
Write-Host "================ B13: construccion completada ================" -ForegroundColor Green
Write-Host "  Artefacto     : dist\windows\$ArtifactName"
Write-Host "  ZIP           : dist\windows\$ArtifactName.zip"
Write-Host "  SHA-256 ZIP   : $zipHash"
Write-Host "  Tamano dist   : $([math]::Round($distBytes / 1MB, 1)) MB en $($allFiles.Count) archivos"
Write-Host "  Tamano ZIP    : $([math]::Round($zipBytes / 1MB, 1)) MB"
Write-Host "  Modo          : standalone (sin onefile, sin instalador, sin firma)"
Write-Host "  Compilacion   : $compileSeconds s   |   total: $totalSeconds s"
Write-Host "  Siguiente     : .\scripts\verify_windows_package.ps1"
Write-Host "=============================================================" -ForegroundColor Green
