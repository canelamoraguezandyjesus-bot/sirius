<#
    Verificación por mutación de los hallazgos graves de AUDITOR-V0-RUN-001 (#154).

    QUÉ HACE
    Para cada hallazgo: ejecuta su prueba con el código actual (debe pasar) y
    luego otra vez tras devolver SOLO el fichero de producción a como estaba
    antes del arreglo (debe fallar). Si sin el arreglo falla, el defecto era
    real. Si pasa las dos veces, el hallazgo era un falso positivo.

    POR QUÉ SOLO CUATRO
    El criterio de parada de ADR-010 solo se dispara con un falso positivo
    GRAVE: confianza Alta y gravedad P0 o P1. Los demás hallazgos no pueden
    parar el piloto, así que no hace falta revisarlos para decidir.

    POR QUÉ NO COMPARA CONTRA `main`
    La primera versión de este script tomaba el código viejo de `origin/main`.
    Eso funcionaba solo mientras las correcciones estaban sin fusionar. Una vez
    fusionadas —14 de agosto de 2026, PR #156 a #160— `main` YA CONTIENE los
    arreglos, así que la comparación habría sido el arreglo contra sí mismo:
    las cuatro pruebas habrían pasado dos veces y el script habría gritado
    «FALSO POSITIVO» sobre cuatro defectos reales, deteniendo el piloto por un
    fallo suyo. Ahora cada caso lleva escrito el commit exacto anterior a su
    arreglo, que no se mueve.

    SEGURIDAD
    - Se niega a arrancar si tienes cambios sin guardar.
    - NO cambia de rama ni crea, mueve o borra ninguna: solo devuelve ficheros
      sueltos a una versión anterior y los restaura.
    - Restaura SIEMPRE, incluso si algo revienta o lo cortas con Ctrl+C.

    USO
        .\scripts\verificar_hallazgos.ps1
        .\scripts\verificar_hallazgos.ps1 -Repo C:\ruta\a\sirius

    ─────────────────────────────────────────────────────────────────────────
    NOTA DE ARRANQUE (ADR-001), escrita antes de ver los resultados

    Va aquí y no en `.claude/evidencia/` porque ese directorio no es escribible
    en el entorno donde se trabajó, ni en `docs/decisions/`, reservado a
    ficheros `ADR-NNN` por su propio README.

    Qué se afirma
      Que este script produce el veredicto correcto sobre los cuatro hallazgos
      graves ahora que las correcciones ya están fusionadas.

    Qué podría desmentirlo
      Que mis supuestos sobre los códigos de salida de pytest sean falsos, y el
      script clasifique como «defecto real» un fallo que en realidad es una
      incompatibilidad entre el fichero viejo y la prueba nueva.

    Criterio de parada
      Si al comprobar los supuestos sobre pytest fallan DOS o más, no se parchea
      la clasificación caso a caso: se reescribe leyendo la documentación de
      códigos de salida en vez de deducirlos.

    Comprobación hecha (14 de agosto de 2026, sobre `main` en e3bd33e)
      - Los cuatro objetivos pasan con el arreglo puesto: exit=0 los cuatro.
      - Caso 1 mutado a fcc3e17: exit=1, sin «errors during collection», y
        AssertionError sobre `StudioCaptureState.GRABANDO`, que es el defecto
        descrito y no un accidente de importación.
      - Un objetivo inexistente da exit=4, que este script clasifica como
        «entorno» y NO como defecto.
      Ningún supuesto resultó falso, así que el criterio de parada no se disparó.

    Lo que esto NO demuestra
      Que el script funcione en PowerShell: aquí no hay PowerShell y no se pudo
      ejecutar. Se ha protegido a ciegas el único fallo conocido de esa clase
      (`$PSNativeCommandUseErrorActionPreference`, comentado abajo), pero la
      primera ejecución real sigue siendo en la máquina del propietario. Es
      exactamente el patrón «pruebas que dependen del entorno del que las
      escribe» de `patrones.md`, declarado en vez de disimulado.
    ─────────────────────────────────────────────────────────────────────────
#>

[CmdletBinding()]
param(
    [string]$Repo = "."
)

$ErrorActionPreference = "Stop"

# Imprescindible. En PowerShell 7.4+ esta preferencia vale $true por defecto y
# hace que un comando nativo que sale con código distinto de cero lance una
# excepción bajo ErrorActionPreference=Stop. Aquí hay dos comandos cuyo código
# distinto de cero es una RESPUESTA, no un error: `pytest` sale con 1 cuando
# una prueba falla —que es justo lo que este script quiere ver— y
# `git merge-base --is-ancestor` sale con 1 para decir «no lo es». Sin esta
# línea el script reventaría en la primera mutación que funciona.
$PSNativeCommandUseErrorActionPreference = $false

# Cada caso fija el commit ANTERIOR a su arreglo. Son fijos a propósito: si
# aquí pusiera una rama, el script volvería a caducar en cuanto esa rama se
# moviera, que es exactamente el fallo que tuvo la primera versión.
$casos = @(
    @{
        Id       = "1"
        Gravedad = "P0"
        Titulo   = "Sirius dice «no estoy grabando» mientras OBS graba"
        Base     = "fcc3e17"   # padre de 0dcd48e (PR #156)
        Codigo   = "src/sirius/adapters/capture/obs_websocket.py"
        Prueba   = "tests/integration/test_obs_websocket_backend.py::test_una_peticion_que_se_rinde_no_desplaza_las_siguientes"
        Arreglo  = "0dcd48e"
    },
    @{
        Id       = "2"
        Gravedad = "P1"
        Titulo   = "Un clic en «Detener voz» la apaga el resto de la sesión"
        Base     = "0dcd48e"   # padre de b6f532b (PR #157)
        Codigo   = "src/sirius/presentation/main_window.py"
        Prueba   = "tests/gui/test_model_studio_integration.py::test_detener_la_voz_no_deja_la_cola_bloqueada_para_el_resto_de_la_sesion"
        Arreglo  = "b6f532b"
    },
    @{
        Id       = "3"
        Gravedad = "P1"
        Titulo   = "Timeout falso de Codex: 20 min y un diagnóstico que miente"
        Base     = "cdd103d"   # padre de 92bb21f (PR #159)
        Codigo   = "scripts/automation/sirius_codex_review.py"
        Prueba   = "tests/automation/test_sirius_codex_review.py::test_una_respuesta_por_comentario_del_conector_no_es_un_timeout"
        Arreglo  = "92bb21f"
    },
    @{
        Id       = "4"
        Gravedad = "P1"
        Titulo   = "«implementing» y «completed» no te notifican nunca"
        Base     = "cdd103d"   # padre de 92bb21f (PR #159)
        Codigo   = ".github/workflows"
        Prueba   = "tests/automation/test_sirius_notifications.py"
        Arreglo  = "92bb21f"
    }
)

function Invoke-Pytest([string]$objetivo) {
    $salida = & uv run pytest $objetivo -q 2>&1 | Out-String
    return [pscustomobject]@{
        Codigo = $LASTEXITCODE
        Salida = $salida
    }
}

# Un fallo solo cuenta como evidencia si la prueba llegó a EJECUTARSE y su
# aserción falló. Si pytest ni siquiera pudo recogerla —porque el fichero
# viejo no tiene un símbolo que la prueba nueva importa— eso no demuestra el
# defecto: demuestra que las dos versiones son incompatibles, que es otra cosa.
# Códigos de pytest: 0 todo pasó · 1 falló una prueba · 2 interrumpido
# (recogida) · 3 error interno · 4 mal uso · 5 no recogió nada.
function Get-TipoFallo($resultado) {
    switch ($resultado.Codigo) {
        0       { return "pasa" }
        1       { if ($resultado.Salida -match "errors? during collection") { return "recogida" } else { return "asercion" } }
        2       { return "recogida" }
        5       { return "sin-pruebas" }
        default { return "entorno" }
    }
}

Push-Location $Repo
$tocados = @()
try {
    if (-not (Test-Path ".git")) {
        throw "No parece un repositorio git: $((Get-Location).Path). Usa -Repo con la ruta de Sirius."
    }

    $sucio = & git status --porcelain
    if ($sucio) {
        throw "Tienes cambios sin guardar. Guárdalos o descártalos antes: este script toca ficheros del árbol y no quiero llevármelos por delante."
    }

    Write-Host "Trayendo el historial..." -ForegroundColor DarkGray
    & git fetch origin --quiet

    # Sin los arreglos delante no hay nada que mutar. Mejor decirlo aquí que
    # dejar que las cuatro pruebas fallen y parezca otra cosa.
    foreach ($caso in $casos) {
        & git merge-base --is-ancestor $caso.Arreglo HEAD 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Tu copia no contiene el arreglo $($caso.Arreglo) (PR del caso $($caso.Id)). Ponte en main actualizado: git checkout main; git pull origin main"
        }
    }

    $resultados = @()

    foreach ($caso in $casos) {
        Write-Host ""
        Write-Host "── $($caso.Gravedad) · $($caso.Titulo)" -ForegroundColor Cyan

        Write-Host "   1/2 con el arreglo puesto..." -NoNewline
        $conArreglo = Invoke-Pytest $caso.Prueba
        Write-Host $(if ($conArreglo.Codigo -eq 0) { " pasa" } else { " FALLA (no deberia)" })

        # Solo el código de producción. La prueba se queda intacta.
        $tocados += $caso.Codigo
        & git checkout $caso.Base -- $caso.Codigo

        # Si esto tocó algo bajo tests/, la comparación no vale.
        $modificados = & git diff --name-only
        $pruebasTocadas = @($modificados | Where-Object { $_ -like "tests/*" })

        Write-Host "   2/2 con el codigo viejo..." -NoNewline
        $sinArreglo = Invoke-Pytest $caso.Prueba
        $tipo = Get-TipoFallo $sinArreglo
        Write-Host " $tipo"

        & git checkout HEAD -- $caso.Codigo
        $tocados = @($tocados | Where-Object { $_ -ne $caso.Codigo })

        $veredicto = if ($pruebasTocadas.Count -gt 0) {
            "NO CONCLUYENTE"
        } elseif ($conArreglo.Codigo -ne 0) {
            "NO CONCLUYENTE"
        } elseif ($tipo -eq "asercion") {
            "DEFECTO REAL"
        } elseif ($tipo -eq "pasa") {
            "FALSO POSITIVO"
        } else {
            "NO CONCLUYENTE"
        }

        $resultados += [pscustomobject]@{
            N         = $caso.Id
            Gravedad  = $caso.Gravedad
            Veredicto = $veredicto
            Detalle   = $tipo
            Hallazgo  = $caso.Titulo
        }
    }

    Write-Host ""
    Write-Host "═══════════════════ RESULTADO ═══════════════════" -ForegroundColor White
    $resultados | Format-Table -AutoSize

    $falsos = @($resultados | Where-Object { $_.Veredicto -eq "FALSO POSITIVO" })
    $raros  = @($resultados | Where-Object { $_.Veredicto -eq "NO CONCLUYENTE" })

    if ($falsos.Count -gt 0) {
        Write-Host "PARA EL PILOTO." -ForegroundColor Red
        Write-Host "Hay $($falsos.Count) falso(s) positivo(s) grave(s). Por el criterio que aprobaste"
        Write-Host "en ADR-010, el Auditor v0 se detiene y hay que revisar el metodo antes de"
        Write-Host "darle mas autonomia. Pasale esta tabla a Claude."
    } elseif ($raros.Count -gt 0) {
        Write-Host "REVISAR A MANO." -ForegroundColor Yellow
        Write-Host "Algo no salio como ninguna de las dos opciones previstas. Mira la columna"
        Write-Host "Detalle: 'recogida' o 'entorno' significa que la prueba ni siquiera llego a"
        Write-Host "ejecutarse, y eso no demuestra el defecto ni lo desmiente. Pasale la tabla."
    } else {
        Write-Host "EL PILOTO PASA SU CRITERIO." -ForegroundColor Green
        Write-Host "Los cuatro defectos graves eran reales: cero falsos positivos graves."
        Write-Host "El Auditor v0 se queda."
    }
    Write-Host ""
    Write-Host "Esto demuestra que el defecto EXISTIA. No demuestra que el arreglo se comporte"
    Write-Host "bien contra OBS real ni en Windows real: eso sigue necesitando tu maquina."
}
finally {
    # Si algo reventó a mitad, el fichero mutado sigue mutado. Devolverlo.
    foreach ($pendiente in $tocados) {
        & git checkout HEAD -- $pendiente 2>$null
    }
    if ($tocados.Count -gt 0) {
        Write-Host ""
        Write-Host "Ficheros restaurados: $($tocados -join ', ')" -ForegroundColor DarkGray
    }
    Pop-Location
}
