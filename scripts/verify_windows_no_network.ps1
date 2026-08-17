<#
.SYNOPSIS
    B14 - El paquete de Sirius no habla con nadie sin proveedor real.

.DESCRIPTION
    Primera tanda de B14 ("Windows sin clave"): monitorizacion de trafico sin
    proveedor real. Arranca el ejecutable EMPAQUETADO en un entorno desechable y
    vigila sus conexiones de red mientras vive. Ninguna conexion saliente puede
    aparecer: abrir Sirius no llama a nadie.

    Es una afirmacion de privacidad, no de rendimiento. B13 demostro que el
    paquete arranca; esto demuestra que al arrancar no telefonea a casa.

    No toca Credential Manager, no escribe ninguna clave y no necesita
    administrador. La credencial real del usuario puede existir o no: da igual,
    porque lo que se mide es el trafico, y el arranque no debe generar ninguno
    en ninguno de los dos casos.

.PARAMETER ArtifactPath
    Carpeta del artefacto ya extraido. Por omision se localiza el ZIP que
    corresponde al HEAD actual y se extrae en una raiz temporal privada.

.PARAMETER ObserveSeconds
    Segundos de vigilancia despues de que la ventana aparezca. Por omision 20.
#>

[CmdletBinding()]
param(
    [string]$ArtifactPath = "",
    [int]$ObserveSeconds = 20
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

$script:Checks = 0
$script:Failures = New-Object System.Collections.Generic.List[string]
$script:Skipped = New-Object System.Collections.Generic.List[string]

function Write-Step { param([string]$Text) Write-Host "`n=== $Text ===" -ForegroundColor Cyan }
function Write-Info { param([string]$Text) Write-Host "  $Text" -ForegroundColor DarkGray }
function Write-Ok { param([string]$Text) Write-Host "  [ok] $Text" -ForegroundColor Green }

function Test-Check {
    param([string]$Name, [bool]$Condition, [string]$Detail = "")
    $script:Checks++
    if ($Condition) {
        Write-Ok $Name
        return
    }
    $message = if ([string]::IsNullOrWhiteSpace($Detail)) { $Name } else { "$Name -> $Detail" }
    Write-Host "  [FALLO] $message" -ForegroundColor Red
    $script:Failures.Add($message)
}

function Add-Skip {
    param([string]$Name, [string]$Reason)
    Write-Host "  [OMITIDA] $Name -> $Reason" -ForegroundColor Yellow
    $script:Skipped.Add("$Name -> $Reason")
}

# --------------------------------------------------------------------------
Write-Step "Privilegios"

$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
$elevated = $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
if ($elevated) {
    throw "Ejecuta esta verificacion SIN elevar: Sirius no requiere administrador."
}
Write-Ok "PowerShell sin elevar."

# --------------------------------------------------------------------------
Write-Step "Localizacion del artefacto"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw ("No existe el interprete del entorno en $VenvPython. Ejecuta " +
        "'uv sync' antes de verificar.")
}

$SmokeRoot = Join-Path $env:TEMP ("Sirius B14 Sin Red " + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $SmokeRoot | Out-Null

if ([string]::IsNullOrWhiteSpace($ArtifactPath)) {
    # Misma regla de procedencia que B13: el artefacto del HEAD actual, nunca
    # "el mas reciente". Verificar el paquete de otro commit no demuestra nada
    # sobre el codigo que hay en el arbol.
    $provenance = Join-Path $PSScriptRoot "package_provenance.py"
    $distRoot = Join-Path $RepoRoot "dist\windows"
    $version = (& $VenvPython -c "import tomllib,pathlib;print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])")
    $headShort = (& git -C $RepoRoot rev-parse --short HEAD | Out-String).Trim()
    $selectionRaw = (& $VenvPython $provenance "select" $distRoot $version.Trim() $headShort | Out-String).Trim()
    $selection = $selectionRaw | ConvertFrom-Json
    if (-not $selection.ok) {
        throw ("No hay artefacto para el HEAD actual ($headShort): " + [string]$selection.error)
    }
    $inspector = Join-Path $PSScriptRoot "zip_package_inspector.py"
    $extractRoot = Join-Path $SmokeRoot "Paquete Extraido Del Zip"
    $extractionRaw = (& $VenvPython $inspector "extract" $selection.zip_path $extractRoot | Out-String).Trim()
    $extraction = $extractionRaw | ConvertFrom-Json
    if (-not $extraction.ok) {
        throw ("La extraccion del paquete fallo: " + [string]$extraction.error)
    }
    $PackageRoot = Join-Path $extractRoot $selection.artifact_name
}
else {
    # Una ruta relativa se resuelve contra $PWD, NUNCA con GetFullPath a secas.
    # .NET la resolveria contra el directorio con el que ARRANCO el proceso, que
    # en PowerShell no tiene por que ser donde esta el prompt: una sesion abierta
    # en otra carpeta y luego movida con "cd" conserva el de origen. Paso de
    # verdad: con el prompt en C:\dev\sirius, "dist\windows\..." se busco en
    # C:\Users\ASUS\OneDrive\Desktop\laboratorio sirius\sirius\dist\windows\...
    $PackageRoot = if ([System.IO.Path]::IsPathRooted($ArtifactPath)) {
        [System.IO.Path]::GetFullPath($ArtifactPath)
    }
    else {
        [System.IO.Path]::GetFullPath((Join-Path $PWD.Path $ArtifactPath))
    }
}

$ExePath = Join-Path $PackageRoot "Sirius.exe"
Test-Check "Existe el Sirius.exe a vigilar" (Test-Path -LiteralPath $ExePath) $ExePath
if ($script:Failures.Count -gt 0) {
    throw "No hay ejecutable que vigilar. No se arranca nada."
}
Write-Info "Ejecutable: $ExePath"

# --------------------------------------------------------------------------
Write-Step "Entorno desechable"

# Mismo aislamiento que B13: perfil, datos y temporales bajo la raiz temporal, y
# un PATH sin Python, sin py y sin uv, para que nada de la maquina de desarrollo
# pueda intervenir en lo que se mide.
$IsolatedHome = [System.IO.Path]::GetFullPath((Join-Path $SmokeRoot "Perfil De Usuario"))
$IsolatedData = Join-Path $SmokeRoot "Datos De Sirius"
$IsolatedTemp = Join-Path $SmokeRoot "Temporales"
$WorkingDirectory = Join-Path $SmokeRoot "Directorio De Trabajo"
$LocalAppData = Join-Path $IsolatedHome "AppData\Local"
$RoamingAppData = Join-Path $IsolatedHome "AppData\Roaming"
foreach ($directory in @($IsolatedHome, $IsolatedData, $IsolatedTemp, $WorkingDirectory, $LocalAppData, $RoamingAppData)) {
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
}

$configDir = Join-Path $LocalAppData "sirius"
New-Item -ItemType Directory -Force -Path $configDir | Out-Null
$locationPayload = [ordered]@{ version = 1; data_dir = $IsolatedData } | ConvertTo-Json
[System.IO.File]::WriteAllText(
    (Join-Path $configDir "data_location.json"),
    $locationPayload,
    (New-Object System.Text.UTF8Encoding($false)))

$MinimalPath = "$env:SystemRoot\system32;$env:SystemRoot\System32\Wbem;$env:SystemRoot\System32\WindowsPowerShell\v1.0"
$IsolatedHomeRoot = [System.IO.Path]::GetPathRoot($IsolatedHome)
$IsolatedHomeDrive = $IsolatedHomeRoot.TrimEnd([char[]]"\")
$IsolatedHomePath = $IsolatedHome.Substring($IsolatedHomeDrive.Length)

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
    "HOMEDRIVE"              = $IsolatedHomeDrive
    "HOMEPATH"               = $IsolatedHomePath
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
foreach ($banned in @("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME", "UV_PROJECT_ENVIRONMENT", "OPENAI_API_KEY")) {
    Test-Check "La variable $banned no se pasa al proceso" (-not $IsolatedEnv.ContainsKey($banned))
}
Test-Check "Los datos quedan fuera de la carpeta del paquete" (-not $IsolatedData.StartsWith($PackageRoot))

# --------------------------------------------------------------------------
Write-Step "Vigilancia de red"

function Get-ProcessTree {
    param([int]$RootId)
    $found = New-Object System.Collections.Generic.List[int]
    $pending = New-Object System.Collections.Generic.Queue[int]
    $pending.Enqueue($RootId)
    while ($pending.Count -gt 0) {
        $current = $pending.Dequeue()
        if ($found.Contains($current)) { continue }
        $found.Add($current)
        $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $current" -ErrorAction SilentlyContinue)
        foreach ($child in $children) { $pending.Enqueue([int]$child.ProcessId) }
    }
    # ToArray() y no la lista: PowerShell desenrolla lo que devuelve una
    # funcion, asi que quien llama tiene que envolver en @() de todas formas.
    return $found.ToArray()
}

# 0.0.0.0 y :: son el comodin de una escucha, no un destino; 127.x y ::1 son la
# maquina misma. Un destino real fuera de esos es trafico saliente.
$LocalOnly = @("0.0.0.0", "::", "::1")

function Get-OutboundConnections {
    param([int[]]$ProcessIds)
    $outbound = New-Object System.Collections.Generic.List[string]
    foreach ($processId in $ProcessIds) {
        $connections = @(Get-NetTCPConnection -OwningProcess $processId -ErrorAction SilentlyContinue)
        foreach ($connection in $connections) {
            $remote = [string]$connection.RemoteAddress
            if ($connection.RemotePort -eq 0) { continue }
            if ($LocalOnly -contains $remote) { continue }
            if ($remote.StartsWith("127.")) { continue }
            $outbound.Add("pid $processId -> $remote`:$($connection.RemotePort) [$($connection.State)]")
        }
    }
    return $outbound.ToArray()
}

$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $ExePath
$startInfo.WorkingDirectory = $WorkingDirectory
$startInfo.UseShellExecute = $false
$startInfo.EnvironmentVariables.Clear()
foreach ($key in $IsolatedEnv.Keys) {
    $startInfo.EnvironmentVariables[$key] = $IsolatedEnv[$key]
}

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $startInfo
$observed = New-Object System.Collections.Generic.List[string]
$samples = 0
$treeSize = 0
$cleanupFailure = ""

try {
    [void]$process.Start()
    Write-Info "Arrancado con PID $($process.Id). Vigilando $ObserveSeconds s..."

    $deadline = (Get-Date).AddSeconds($ObserveSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($process.HasExited) { break }
        # @() obligatorio: una funcion que devuelve UN elemento entrega un
        # valor suelto, no una coleccion, y pedirle .Count a un entero revienta
        # con Set-StrictMode. Sirius corre en un solo proceso sin hijos, que es
        # justo el caso de un elemento.
        $tree = @(Get-ProcessTree -RootId $process.Id)
        if ($tree.Count -gt $treeSize) { $treeSize = $tree.Count }
        foreach ($entry in @(Get-OutboundConnections -ProcessIds $tree)) {
            if (-not $observed.Contains($entry)) { $observed.Add($entry) }
        }
        $samples++
        Start-Sleep -Milliseconds 250
    }

    Test-Check "El proceso seguia vivo durante toda la vigilancia" (-not $process.HasExited) (
        $(if ($process.HasExited) { "salio con codigo $($process.ExitCode)" } else { "" }))
}
finally {
    # Ninguna excepcion de sondeo puede dejar el ejecutable del paquete activo.
    if (-not $process.HasExited) {
        try {
            [void]$process.CloseMainWindow()
            if (-not $process.WaitForExit(4000)) {
                $process.Kill()
                if (-not $process.WaitForExit(5000)) {
                    $cleanupFailure = "el proceso no termino despues de Kill()"
                }
            }
        }
        catch {
            $cleanupFailure = $_.Exception.Message
        }
    }
}

Test-Check "El proceso del paquete quedo terminado" ([string]::IsNullOrWhiteSpace($cleanupFailure)) $cleanupFailure
Test-Check "Hubo muestras de red que examinar" ($samples -gt 0) "muestras: $samples"
Write-Info "Muestras tomadas: $samples   |   procesos vigilados: $treeSize"

Test-Check "El paquete no abrio ninguna conexion saliente" ($observed.Count -eq 0) (
    $observed -join " | ")

# UDP es sin conexion: Get-NetUDPEndpoint solo expone el extremo local, asi que
# por este camino no se puede afirmar nada sobre destinos UDP -una consulta DNS,
# por ejemplo-. Capturar paquetes exigiria administrador, y Sirius no debe
# necesitarlo para nada. Se declara en vez de fingir que esta cubierto.
Add-Skip "Destinos UDP (incluido DNS)" (
    "UDP no expone el extremo remoto sin captura de paquetes, que exigiria administrador")

# --------------------------------------------------------------------------
Write-Step "Resultado"

Write-Host ""
if ($script:Failures.Count -eq 0 -and $script:Skipped.Count -eq 0) {
    Write-Host "======== B14/red: SUPERADA ========" -ForegroundColor Green
    Write-Host "  Pruebas : $($script:Checks) comprobaciones, 0 fallos, 0 omitidas"
    Write-Host "===================================" -ForegroundColor Green
    Write-Host "`n  Entorno temporal conservado: $SmokeRoot" -ForegroundColor DarkGray
    exit 0
}
elseif ($script:Failures.Count -eq 0) {
    Write-Host "==== B14/red: SUPERADA CON RESERVAS ====" -ForegroundColor Yellow
    Write-Host "  Paquete : $PackageRoot"
    Write-Host "  Pruebas : $($script:Checks) comprobaciones, 0 fallos, $($script:Skipped.Count) OMITIDAS"
    Write-Host "  NO se ha demostrado:" -ForegroundColor Yellow
    foreach ($skip in $script:Skipped) { Write-Host "   - $skip" -ForegroundColor Yellow }
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "`n  Entorno temporal conservado: $SmokeRoot" -ForegroundColor DarkGray
    exit 0
}
else {
    Write-Host "======== B14/red: NO SUPERADA ========" -ForegroundColor Red
    Write-Host "  Pruebas : $($script:Checks) comprobaciones, $($script:Failures.Count) fallos, $($script:Skipped.Count) omitidas"
    foreach ($failure in $script:Failures) { Write-Host "   - $failure" -ForegroundColor Red }
    Write-Host "=====================================" -ForegroundColor Red
    Write-Host "`n  Entorno temporal conservado: $SmokeRoot" -ForegroundColor DarkGray
    exit 1
}
