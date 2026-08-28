# Lanza la medicion del modelo local sin tener que acordarse de nada.
#
# Uso:   .\scripts\medir_memoria.ps1
#
# Existe porque casi todas las corridas de estos dias murieron por lo mismo, y
# no era el codigo: era el entorno. El PYTHONPATH que hay que poner en cada
# ventana nueva, el --no-sync que hace falta porque OneDrive bloquea .venv, el
# nombre de salida que ya estaba cogido, Ollama apagado. Nada de eso es la
# medicion, y todo eso la paraba. Aqui se comprueba antes y se dice en
# castellano que hacer.

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Push-Location $raiz

try {
    Write-Host "== comprobando antes de medir ==" -ForegroundColor Cyan

    # 1. Ollama. Sin esto la corrida tarda lo mismo y no mide nada: el filtro
    #    falla abierto en los 47 casos y las cifras salen identicas a la
    #    busqueda sola, que se lee igual que «el modulo no sirve».
    try {
        $null = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
        Write-Host "   Ollama responde" -ForegroundColor Green
    } catch {
        Write-Host "   Ollama NO responde en http://localhost:11434" -ForegroundColor Red
        Write-Host ""
        Write-Host "   Abre la aplicacion Ollama y espera a ver la llama en la barra de abajo."
        Write-Host "   Luego vuelve a lanzar esto mismo."
        exit 1
    }

    # 2. El paquete del proyecto. OneDrive deja `.venv` a medias cada dos por
    #    tres y entonces `import sirius` falla. Apuntar al codigo fuente lo
    #    esquiva sin reinstalar nada y sin pelearse con el bloqueo.
    $env:PYTHONPATH = Join-Path $raiz "src"
    uv run --no-sync python -c "import sirius" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   el paquete sirius NO se importa" -ForegroundColor Red
        Write-Host ""
        Write-Host "   Prueba, en este orden:"
        Write-Host "     1) cierra VS Code entero y vuelve a abrirlo"
        Write-Host "     2) pausa OneDrive 2 horas (clic derecho en la nubecita)"
        Write-Host "     3) uv sync"
        exit 1
    }
    Write-Host "   el paquete sirius se importa" -ForegroundColor Green

    Write-Host ""
    Write-Host "== midiendo (tarda unos minutos; no cierres la ventana) ==" -ForegroundColor Cyan
    Write-Host ""

    # El nombre de salida lo elige el arnes solo, cogiendo el primer hueco libre.
    uv run --no-sync python -m experiments.adr002.modelo_local.medir @args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host ""
    Write-Host "== que mirar ==" -ForegroundColor Cyan
    Write-Host "   omis=    los datos criticos que se pierden. Cuanto mas bajo, mejor."
    Write-Host "   exacto=  las respuestas que salen clavadas, de 47."
    Write-Host "   Y la linea 'el filtro se llevo N correctos, de ellos N criticos'."
    Write-Host ""
    Write-Host "Para guardar el resultado:" -ForegroundColor Cyan
    Write-Host '   git add resultado_modelo_local_v0.*.json'
    Write-Host '   git commit -m "New measurement"'
    Write-Host '   git push -u origin evidence/adr001-spikes'
}
finally {
    Pop-Location
}
