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
        $visibleTitles = @([SiriusWindowProbe]::VisibleTitles([uint32]$process.Id))
        if ($visibleTitles.Count -gt 0) {
            $sawWindow = $true
            $titles = $visibleTitles
        }
    }

    # Ver una ventana demuestra que la interfaz llego a mostrarse, pero no que
    # el proceso sobrevivio al intervalo de observacion. Se sigue vigilando
    # hasta el plazo completo o hasta una salida real del proceso.
    $stillAlive = -not $process.HasExited
    if ($stillAlive) {
        $visibleTitles = @([SiriusWindowProbe]::VisibleTitles([uint32]$process.Id))
        if ($visibleTitles.Count -gt 0) {
            $sawWindow = $true
            $titles = $visibleTitles
        }
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
