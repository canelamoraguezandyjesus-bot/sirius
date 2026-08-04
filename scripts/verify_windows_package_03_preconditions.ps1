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
# DEVUELVE un booleano; por dentro, SecretStore.get_secret() si obtiene el
# valor para reducirlo a ese booleano, asi que Credential Manager se consulta
# de verdad y el secreto entra en memoria del proceso de la sonda. Lo que se
# garantiza: la sonda solo emite PRESENT, ABSENT o ERROR; el valor no se
# imprime, no se devuelve, no se registra, y la credencial no se modifica ni
# se elimina. No se usa cmdkey.
$CredentialProbe = Join-Path $SmokeRoot "probe_credential_presence.py"
$credentialProbeSource = @'
"""Precondicion de B13: existencia de la credencial de Sirius.

Consulta Credential Manager a traves del puerto de aplicacion. has_key()
devuelve un booleano, pero por dentro obtiene el valor para calcularlo, asi
que el secreto si entra en memoria de ESTE proceso; es el mismo acceso que
hace Sirius al arrancar. Lo que este script garantiza es la salida: imprime
unicamente PRESENT, ABSENT o ERROR <TipoDeExcepcion>. No devuelve el valor,
no lo imprime, no lo registra, no escribe y no borra la credencial.
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

# Puerta final: las comprobaciones de aislamiento, PATH, credencial y estado
# real del usuario son precondiciones de ejecucion. Si cualquiera falla, no se
# carga ni se arranca codigo procedente del paquete extraido.
if ($script:Failures.Count -gt 0) {
    throw ("Las precondiciones de ejecucion no se cumplen. " +
        "No se ejecutara codigo del paquete.")
}

# --------------------------------------------------------------------------
