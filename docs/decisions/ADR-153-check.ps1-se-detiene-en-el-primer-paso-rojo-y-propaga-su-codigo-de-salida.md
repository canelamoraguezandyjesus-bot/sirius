# ADR-153 — check.ps1 se detiene en el primer paso rojo y propaga su código de salida

- Estado: PROPUESTO
- Fecha: 2026-09-06
- Aprobación: la fusión de esta PR por el propietario (ficha del operador; no
  toca `.github/**`: vive en `scripts/check.ps1` y en su guardián).

Esta es también la nota de arranque de la rama
`claude/adr-153-check-ps1-propaga-el-codigo-de-salida`, publicada antes del
primer cambio, con las cuatro preguntas de la disciplina de evidencia
(ADR-001).

## Contexto y problema

`scripts/check.ps1` es la validación obligatoria de este repositorio
(AGENTS.md; ADR-145: «una sola invocación de `pwsh -File scripts/check.ps1`
sobre el árbol final, con su código de salida transcrito»). Hasta hoy era
esto, literalmente:

```powershell
$ErrorActionPreference = "Stop"

uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
```

Y ese guion **no dice lo que todo el mundo creía que decía**:
`$ErrorActionPreference` gobierna los errores de PowerShell, no el código de
salida de un ejecutable nativo, así que un `ruff format --check` en rojo no
detiene nada; y `pwsh -File` devuelve el código de salida del ÚLTIMO comando
ejecutado. El «código de salida 0» del guion era el de `pytest`, y solo el de
`pytest`. Los tres primeros comandos podían estar en rojo y el guion terminar
en 0 igual.

Los datos, todos de la incidencia #545:

- Ronda 2 (run 34007489545): el corrector declaró «una sola invocación de
  `pwsh -File scripts/check.ps1`, código de salida 0, 4992 passed» y empujó
  `3380f09`; Quality lo tumbó en `Ruff format` a los 24 s (dos ficheros de
  prueba sin formatear).
- El operador formateó esos dos ficheros (`923202f`); Quality tumbó ese head
  en `Mypy` a los 21 s (`src/sirius_engine/reflect.py:484: Unsupported operand
  types for >= ("datetime" and "None")`).
- Ronda 3 (run 34009172673, `537a026`): el corrector encontró la causa y la
  dejó escrita en su commit: «`scripts/check.ps1` lo tapaba: encadena los
  cuatro comandos sin comprobar el código de salida de cada uno y PowerShell
  no propaga el de un ejecutable nativo, así que el código de salida del
  script es el de pytest y solo el de pytest. Quality no tiene ese
  amortiguador». Y no lo tocó, con razón: es la validación obligatoria de
  ADR-145, una decisión de otro sitio.

El primer dato de ADR-145 (bitácora, entrada 41: «la forma obedecida, la
verdad no») era el mismo defecto: el implementador de #546 declaró el guion en
0 y Quality dijo `ruff lint` en rojo. **No eran tres agentes declarando en
falso: era el termómetro.** Y, en consecuencia, todas las validaciones «en
verde» declaradas con este guion desde que existe solo demostraban `pytest`.

## Nota de arranque (cuatro preguntas, ADR-001)

1. **¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
   observar el fallo?** Vive en `scripts/check.ps1`, en la ausencia de
   comprobación del código de salida entre comandos. El arreglo va ahí:
   después de cada uno de los tres primeros comandos, `if ($LASTEXITCODE -ne
   0) { exit $LASTEXITCODE }`; después del último, `exit $LASTEXITCODE`. Se
   observa en el código de salida del guion, que es justo lo que ADR-145 pide
   transcribir.
2. **¿Qué NO garantiza esto?** No hace verdad ninguna declaración pasada. No
   impide que un agente declare un código que no obtuvo (eso lo cubre, si el
   propietario lo decide, la opción 4 de ADR-150: el guion como paso
   determinista del workflow tras el agente). No cambia qué comprueba el guion
   ni su orden. Y en el entorno del operador no hay `pwsh` (se intentó
   descargarlo y el entorno lo denegó), así que el guion corregido no se ha
   EJECUTADO aquí: se fija su forma y lo ejecuta por primera vez el siguiente
   rol en un runner.
3. **Criterio de parada (decidido antes de ver ningún resultado).** El
   guardián nuevo ve FALLAR el guion vigente de `main` y pasa con el cambio;
   los cuatro comandos siguen siendo los mismos y en el mismo orden (ADR-145
   los nombra); nada más ejecutable entra en el guion; la cadena completa
   termina en 0. En vivo: la primera ronda de un rol con el guion nuevo debe
   transcribir un código de salida que coincida con Quality sobre el mismo
   head (si el guion dice 0, Quality pasa los cuatro pasos; si Quality tumba
   `ruff`/`mypy`, el guion no pudo decir 0). Si un rol declarara 0 y Quality
   tumbara un paso anterior a `pytest` con el guion nuevo, el ADR está
   desmentido y el problema es otro.
4. **¿Qué hace esto imposible, en vez de improbable?** Que un rojo de `ruff
   format`, `ruff check` o `mypy` produzca un código de salida 0 del guion:
   cada comando comprueba el suyo antes de que corra el siguiente, y el
   guardián prohíbe que un comando quede sin comprobación o que el guion
   termine sin `exit $LASTEXITCODE`.

## Criterio de parada (escrito ANTES de decidir)

Ver punto 3 de la nota de arranque.

## Opciones consideradas

1. **Comprobar `$LASTEXITCODE` tras cada comando y terminar con `exit
   $LASTEXITCODE`** (elegida). Explícito, legible, válido en cualquier
   versión de PowerShell (incluida la máquina del propietario), y el guion
   sigue siendo los mismos cuatro comandos en el mismo orden.
2. **`$PSNativeCommandUseErrorActionPreference = $true`** (PowerShell 7.4+):
   convierte el código de salida distinto de cero de un nativo en error
   terminante bajo `Stop`. Descartada: depende de la versión de `pwsh` del
   sitio donde se ejecuta (el runner y la máquina del propietario no tienen
   por qué coincidir), y el fallo se presentaría como una excepción de
   PowerShell con su traza en vez de como el código del comando.
3. **Sustituir el guion por uno de bash.** Descartada: la máquina del
   propietario es Windows y ADR-145 nombra literalmente `pwsh -File
   scripts/check.ps1`.
4. **Ejecutar `check.ps1` como paso determinista del workflow tras el agente**
   (opción 4 de ADR-150). Complementaria, no alternativa: hace que el código
   de salida sea un hecho del workflow y no una declaración del agente, pero
   sigue necesitando que el guion propague el código. Espera decisión del
   propietario.

## Decisión

- `scripts/check.ps1`: tras cada uno de los tres primeros comandos, `if
  ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }`; tras `uv run pytest`, `exit
  $LASTEXITCODE`. Un comentario de cabecera dice por qué.
- Guardián nuevo, `tests/automation/test_check_ps1_se_detiene_en_el_primer_rojo.py`:
  los cuatro comandos en su orden; cada uno de los tres primeros seguido
  inmediatamente de la comprobación; el guion termina en `uv run pytest` +
  `exit $LASTEXITCODE`; nada más ejecutable.
- Ni AGENTS.md ni los prompts cambian: siguen exigiendo una sola invocación
  de `pwsh -File scripts/check.ps1` con su código de salida transcrito. Lo
  que cambia es que ese código vuelve a significar los cuatro comandos.

## Comprobación que la sostiene

- Rojo previo, visto fallar: el guardián contra el guion vigente de `main`
  (`f8cb429`) y su resultado con el cambio, transcritos en el cuerpo de la
  PR.
- Cadena completa como una sola invocación sobre el árbol final: transcrita
  en el cuerpo de la PR. En el contenedor no hay `pwsh`, así que la cadena se
  ejecuta con los mismos cuatro comandos bajo `bash -ec` con el código de
  salida capturado; Quality revalida en CI paso a paso.
- Lo que NO se ha medido: el guion corregido no se ha ejecutado con `pwsh`
  en el entorno del operador (criterio 2). Lo mide la primera ronda de un rol
  con el guion nuevo (criterio 3).

## Consecuencias

- «Código de salida 0 de `check.ps1`» vuelve a significar los cuatro
  comandos en verde. Las declaraciones de los roles pasan a ser comprobables
  contra Quality sobre el mismo head.
- Los tres datos de ADR-145 registrados en la bitácora (entradas 41 y 44) se
  releen: no fueron declaraciones falsas de los agentes, fue el guion. La
  opción 4 de ADR-150 sigue teniendo sentido por otra razón (que el código
  sea un hecho del workflow), pero ya no por esta.
- Un rojo de `ruff format` cuesta ahora segundos en la ronda del rol, no una
  vuelta entera de Quality → `repair-requested` → corrector.
- Deuda declarada: el guion no se ha ejecutado con `pwsh` en el entorno del
  operador; si la sintaxis fallara, la primera ronda de cualquier rol lo
  diría en su primera línea y el arreglo es inmediato.

## Alternativas descartadas y por qué

Ver «Opciones consideradas».
