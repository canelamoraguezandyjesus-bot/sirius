# medir_de_noche.ps1 - Mediciones de Sirius con Ollama real, sin nadie delante.
#
# Solo lee, mide y empuja texto a una rama de mediciones. No ejecuta nada que
# venga de fuera. NUNCA hace force-push, NUNCA toca main mas alla de un
# fast-forward, y SE ABORTA si el arbol de trabajo tiene cambios sin guardar
# en vez de destruirlos.
#
# Uso:  powershell -NoProfile -ExecutionPolicy Bypass -File medir_de_noche.ps1

$ErrorActionPreference = "Stop"

$repo  = "C:\Users\ASUS\OneDrive\Desktop\laboratorio sirius\sirius"
$rama  = "mediciones/maquina-del-propietario"
$modelo = "qwen3:4b-instruct"

Set-Location $repo

# --- 0) No destruir nada ------------------------------------------------------
$sucio = git status --porcelain
if ($sucio) {
    Write-Host "ABORTADO: hay cambios sin guardar en el arbol. No se mide ni se toca nada."
    Write-Host $sucio
    exit 1
}
$ramaOriginal = git rev-parse --abbrev-ref HEAD

try {
    # --- 1) Traer main sin destruir ------------------------------------------
    git fetch origin main $rama 2>$null
    git checkout main
    git pull --ff-only origin main
    $sha   = git rev-parse --short HEAD
    $fecha = Get-Date -Format "yyyy-MM-dd-HHmm"

    # Los resultados se escriben FUERA del repo y se copian al final.
    $tmp = Join-Path $env:TEMP "sirius-mediciones-$fecha"
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null

    # --- 2) Precalentar con los MISMOS parametros del adaptador --------------
    # Sin esto Ollama recarga el modelo en la primera llamada real (el num_ctx
    # no coincide) y esa llamada se pierde por timeout: medicion contaminada.
    $cuerpo = @{
        model      = $modelo
        messages   = @(@{ role = "user"; content = "ok" })
        stream     = $false
        think      = $false
        keep_alive = "60m"
        options    = @{ temperature = 0.1; num_ctx = 8192 }
    } | ConvertTo-Json -Depth 5
    try {
        Invoke-RestMethod -Uri http://localhost:11434/api/chat -Method Post `
            -Body $cuerpo -ContentType "application/json" -TimeoutSec 300 | Out-Null
    } catch {
        "Ollama no responde en localhost:11434. No se mide nada." |
            Out-File (Join-Path $tmp "$fecha-$sha-FALLO.txt") -Encoding utf8
        throw "Ollama no disponible"
    }

    # --- 3) Las tres mediciones ----------------------------------------------
    function Medir([string]$nombre, [scriptblock]$bloque) {
        $f = Join-Path $tmp "$fecha-$sha-$nombre.txt"
        try { & $bloque 2>&1 | Out-File $f -Encoding utf8 }
        catch { "FALLO al ejecutar: $_" | Out-File $f -Encoding utf8; return }
        $t = Get-Content $f -Raw
        $aviso = $null
        if ($t -match "Rendiciones del filtro\.*\s*(\d+)" -and $Matches[1] -ne "0") {
            $aviso = "CONTAMINADA: rendiciones=$($Matches[1])"
        }
        if ($t -match "no disponible, se falla abierto") {
            $aviso = "CONTAMINADA: el adaptador fallo abierto al menos una vez"
        }
        if ($aviso) { "$aviso`n`n$t" | Out-File $f -Encoding utf8 }
    }

    Medir "banco-completo" { uv run python scripts/medir_banco_con_ollama_real.py --diagnostico }
    Medir "interprete"     { uv run python scripts/medir_interprete_de_peticion.py }
    Medir "d7-punto-6"     { uv run pytest tests/acceptance/test_d7_punto_6_coincidencia_etiquetado.py -q -s }

    # Cuarta, opcional: el techo real (peticion declarada + filtro real).
    # Solo si el guion esta presente en la raiz del clon; se copia a mano
    # desde la rama de auditoria. Es la pregunta abierta mas valiosa.
    if (Test-Path (Join-Path $repo "medir_techo_con_filtro_real.py")) {
        Medir "techo-con-filtro" { uv run python medir_techo_con_filtro_real.py }
    }

    # --- 4) Empujar los resultados a la rama de mediciones -------------------
    # Sin force: el historico de noches anteriores se conserva.
    $existe = git ls-remote --heads origin $rama
    if ($existe) { git checkout -B $rama "origin/$rama" } else { git checkout -B $rama }

    $destino = Join-Path $repo "mediciones"
    New-Item -ItemType Directory -Force -Path $destino | Out-Null
    Copy-Item (Join-Path $tmp "*") $destino -Force

    git add mediciones
    git commit -m "Mediciones con Ollama real sobre $sha ($fecha)"
    git push -u origin $rama
    Write-Host "OK: mediciones de $sha empujadas a $rama"
}
finally {
    # Devolver el clon a donde estaba, pase lo que pase.
    if ($ramaOriginal) { git checkout $ramaOriginal 2>$null }
}
