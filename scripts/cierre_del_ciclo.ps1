# ADR-216: cierra los cuatro trabajos del motor que llevan parados desde el 3,
# el 12 y el 13-09-2026 y publica el diario. Un solo comando para el
# propietario, porque un lote pegado a mano no puede pararse a sí mismo: las
# rondas 2 y 3 de la revisión externa sobre la PR #663 encontraron tres formas
# distintas de que ese lote hiciera daño (la rama local adelantada, un `0 1`
# impreso que nadie lee, y un `git add -A` que publica lo que hubiera suelto en
# la carpeta). La raíz era la misma: las salvaguardas estaban escritas en prosa
# debajo del bloque, no en el código.
#
# TRES DECISIONES DE FORMA, y conviene decirlas:
#
# 1. NO se cambia de rama en su repositorio. `estado-del-motor` es una rama
#    huérfana con CUATRO ficheros (`git ls-tree` del 24-09-2026: DESENLACES.md,
#    diario.jsonl, diario-despacho.jsonl, racha_siete_dias.jsonl). Un
#    `git switch` ahí deja el árbol sin `pyproject.toml` y sin `src/`, así que
#    el `uv run` siguiente no encontraría el proyecto. El workflow nunca hizo
#    eso: clona la memoria aparte (`reflejar-desenlace.yml`) y ejecuta desde el
#    repositorio. Esto hace lo mismo.
# 2. Se clona limpio en una carpeta nueva fuera de OneDrive. Un clon recién
#    hecho ES el remoto: no hay rama local atrasada, ni adelantada, ni
#    divergente que comprobar. El `push` con refspec explícita se rechaza solo
#    si el remoto se movió mientras tanto, que es justo lo que debe pasar.
# 3. Cada comando nativo comprueba su `$LASTEXITCODE` (ADR-153, como
#    `scripts/check.ps1`): `$ErrorActionPreference` no alcanza a los
#    ejecutables, y sin esto el guion seguiría adelante sobre un fallo.

$ErrorActionPreference = "Stop"

# El guion se ejecuta desde la raíz del repositorio pase lo que pase: `uv run`
# necesita el `pyproject.toml`, y él pega el comando desde donde tenga abierta
# la consola.
Set-Location (Split-Path -Parent $PSScriptRoot)

$Origen = git config --get remote.origin.url
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Memoria = Join-Path $env:TEMP ("memoria-sirius-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
Write-Host "Carpeta de trabajo: $Memoria"

git clone --branch estado-del-motor --single-branch $Origen $Memoria
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Diario = Join-Path $Memoria "diario.jsonl"
if (-not (Test-Path $Diario)) {
    Write-Host "No hay diario en el clon. No se toca nada."
    exit 1
}

# Los cuatro trabajos parados. `sirius-decidir` se niega solo si alguno no
# estuviera en `needs_decision`, y entonces el guion para aquí: el dominio es
# la última guarda, no la primera.
uv run sirius-decidir WI-20260903-030529 --diario $Diario --ejecutar --terminar
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run sirius-decidir WI-20260903-095428 --diario $Diario --ejecutar --terminar
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run sirius-decidir WI-20260912-235558 --diario $Diario --ejecutar --terminar
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run sirius-decidir WI-20260913-142937 --diario $Diario --ejecutar --terminar
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# La vista legible se deriva del diario, y el workflow la regenera tras cada
# reflejo (ADR-171). Sin esto, el diario diría una cosa y DESENLACES.md otra.
uv run sirius-memoria desenlaces --diario $Diario
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Se añaden los DOS ficheros por su nombre. Nunca `-A`: en esta carpeta no
# debería haber nada más, y si lo hubiera, no es asunto del diario.
git -C $Memoria add diario.jsonl DESENLACES.md
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

git -C $Memoria commit -m "Cierre del ciclo: los cuatro trabajos parados quedan terminados (ADR-216)"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Refspec explícita, como hace el workflow. Si el remoto se movió desde el
# clon, git rechaza el avance y el guion sale en rojo sin forzar nada.
git -C $Memoria push origin HEAD:refs/heads/estado-del-motor
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Listo. Los cuatro trabajos quedan terminados y el diario esta publicado."
Write-Host "El recuento del motor pasa a 59 entregados / 31 cancelados / 0 esperando / 1 apartado."
exit 0
