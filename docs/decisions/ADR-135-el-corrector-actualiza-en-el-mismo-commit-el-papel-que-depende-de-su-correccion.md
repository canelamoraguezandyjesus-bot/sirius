# ADR-135 — El corrector actualiza en el mismo commit el papel que depende de su corrección

- Estado: PROPUESTO
- Fecha: 2026-09-04
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Número asignado a mano: `scripts/siguiente_adr.py` propuso 134 tras esquivar
  el 133 (lo vio cogido en la rama sin fusionar de la incidencia #523), pero el
  134 también viaja sin fusionar, en la rama de la incidencia #526, que este
  clon no tenía traída — el propio guion avisa de ese límite («haz `git fetch`
  antes si sospechas que faltan»). Se toma el 135, el primero libre contando
  las dos ramas en vuelo (bitácora del ciclo, entrada 24).

Este ADR es además la nota de arranque de su rama: las predicciones de abajo
quedaron escritas antes del primer commit y antes de observar ninguna ronda
posterior al cambio.

## Contexto y problema

Medido el 04-09-2026 sobre las dos incidencias de la mina v2 en vuelo
(bitácora del ciclo, entradas 27 y 28):

- En #526 (G2), la ronda 1 de revisión encontró defectos reales; las rondas
  2, 3, 4 y 5 fueron TODAS sobre el papel del ADR-134 (un comando de
  evidencia, la cifra 4697/4698, y una duración de suite copiada entre
  versiones). En #523 (G3), tras la ronda con tres defectos reales del
  parser, las dos siguientes fueron: el ADR-133 describía el algoritmo de
  antes del arreglo, y al sincronizarlo, un recuento actualizado (39→42) y
  otro olvidado (4660 cuando el árbol da 4663).
- El mecanismo es constante: la revisión limita la corrección a «únicamente
  lo señalado», el corrector obedece y no refresca el papel que depende de lo
  que tocó, y la ronda siguiente encuentra ese papel desfasado. Cada
  corrección fabrica el hallazgo de la siguiente.
- El caso agravado (entrada 28): la evidencia del ADR-134 conservó la
  duración `in 423.87s` idéntica carácter a carácter en cuatro versiones del
  documento mientras los mensajes de commit afirmaban re-ejecuciones reales y
  separadas de la suite — cifras editadas a mano dentro de una captura vieja,
  cazadas por la revisión en la ronda 5.

Es la reproducción en vivo, el mismo día y dentro del propio ciclo, de dos
familias que la mina v2 midió sobre la ola de criticidad
(`docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09.md`, §4): «prosa
desincronizada» (7 hallazgos en 3 encargos) y «cifras a mano» (4 en 2).

El propietario pidió el 04-09-2026, en sesión, atacar esto por el prompt del
corrector, dejando para más adelante la otra palanca hablada (fijar un modelo
más capaz en los workflows de los agentes).

## Criterio de parada (escrito ANTES de decidir)

- Si el cambio exigiera tocar `.github/**`, parar: esa parte es del
  propietario (ADR-002). No hizo falta: el workflow del corrector hace
  checkout de `main` y lee el prompt con
  `cat scripts/automation/prompts/corrector.md`
  (`.github/workflows/repair-sirius-work.yml`, paso `build_prompt`), así que
  el cambio vive fuera de `.github/**`.
- Si el cambio exigiera alterar la semántica de los veredictos, los límites
  de corrección que escribe la revisión, o darle al corrector autoridad
  nueva, parar y hablarlo: esto es una regla de coherencia del trabajo ya
  autorizado, no una ampliación de poderes.
- Después del cambio: si en los dos siguientes encargos del motor vuelve a
  haber dos o más rondas consecutivas solo de papel tras una corrección de
  código, la frase no basta — parar y buscar la raíz siguiente (candidata:
  los «límites de corrección» del revisor, que a veces prohíben tocar el ADR)
  en vez de añadir más frases.

## Opciones consideradas

1. Añadir al prompt del corrector la obligación de actualizar, en el mismo
   commit, el ADR y la evidencia que dependan de lo corregido, y de citar
   solo evidencia recién capturada.
2. Fijar un modelo más capaz para implementador y corrector en los workflows.
3. Un guardián nuevo que detecte evidencia repetida entre commits que afirman
   ejecuciones separadas.

## Decisión

**Opción 1 ahora; la 2 queda hablada y aplazada por el propietario; la 3 como
candidata a medir antes de proponer.** Dos viñetas nuevas en
`scripts/automation/prompts/corrector.md`, colocadas inmediatamente después de
la regla «corrige únicamente lo señalado» porque son su matización:

> - Actualizar lo que **depende** de tu corrección no es ampliar el alcance:
>   si tu corrección cambia código, pruebas o cifras, actualiza en el mismo
>   commit el ADR de la incidencia y toda evidencia que describa lo que has
>   cambiado (algoritmo, recuentos de pruebas, salidas citadas), salvo que
>   los límites de corrección de la observación lo prohíban explícitamente.
>   Un ADR que sigue describiendo el código de antes de tu corrección es un
>   defecto nuevo que la siguiente ronda encontrará (ADR-135; bitácora del
>   ciclo, entradas 27-28).
> - Toda evidencia que cites (recuentos, duraciones, salidas de comandos)
>   debe ser salida recién capturada del comando real sobre el árbol actual
>   de la rama. Nunca edites una cifra a mano dentro de una captura vieja.
>   Si por un motivo legítimo reutilizas una captura anterior, dilo
>   explícitamente donde la cites.

La cláusula «salvo que los límites de corrección lo prohíban explícitamente»
mantiene la jerarquía existente: la revisión sigue mandando sobre el alcance
de cada ronda; la viñeta solo elimina la lectura de «únicamente lo señalado»
como excusa para dejar papel desfasado.

## Comprobación que la sostiene

- El desglose ronda a ronda que motiva el cambio está citado, con
  identificadores de hallazgo y heads, en la bitácora del ciclo (entradas 27
  y 28, rama `claude/adr002-tol209-forensic-audit-i0ui8k`) y en los
  comentarios de #523 y #526 del 04-09-2026 (13:06–13:56 UTC).
- Que el cambio no toca `.github/**`: `git diff --stat` de esta rama contra
  `main` lista solo `scripts/automation/prompts/corrector.md`, este ADR y
  `tests/automation/test_citas_de_los_adr.py` (ver punto siguiente).
- El guardián de citas de ADRs falló primero sobre este mismo documento
  (`test_toda_ruta_citada_por_un_adr_existe[ADR-135-...]`: el informe de la
  mina vive en la rama de auditoría que a propósito nunca se fusiona), y se
  resolvió por el cauce que el propio guardián ofrece: registrar la ruta en
  `RAMA_DE_ORIGEN_NO_FUSIONADA` junto al ADR-132, que ya la cita por el
  mismo motivo. Ese rojo previo es la mutación natural de este cambio.
- Las pruebas que sí vigilan los prompts de rol
  (`tests/automation/test_prompts_de_rol.py`) pasan con las dos viñetas
  añadidas: no fijan el contenido literal del prompt del corrector, solo su
  estructura y cableado.
- Validaciones obligatorias sobre el árbol final, salida real capturada el
  04-09-2026:
  - `uv run ruff format --check .` → `595 files already formatted`
  - `uv run ruff check .` → `All checks passed!`
  - `uv run mypy src tests` → `Success: no issues found in 563 source files`
  - `uv run pytest -q` → `1 failed, 4679 passed, 14 skipped, 2 xfailed in
    712.73s`. El fallo es
    `tests/gui/test_conversation_ui.py::test_streaming_message_grows_without_overlapping_neighbours`,
    la prueba de GUI dependiente del estado de Qt ya registrada como deuda 7
    de la bitácora del ciclo (entrada 16), sin relación con este cambio:
    reejecutada aislada sobre el mismo árbol → `1 passed in 2.89s`.
  - `git diff --check` → limpio.

PREDICCIÓN (fijada antes de observar rondas posteriores): en los dos
siguientes encargos del motor, las rondas de reparación cuyo único hallazgo
sea papel desfasado por una corrección anterior caen de las 2-4 de hoy a 0-1
por encargo; se medirá en la bitácora con el mismo desglose ronda a ronda que
en las entradas 27-28.

## Consecuencias

- Surte efecto en la primera ronda de corrección que arranque después de que
  esta PR se fusione en `main` (el workflow lee el prompt de `main` en cada
  ejecución; no hay que reiniciar nada).
- No cambia veredictos, etiquetas, autoridad del corrector ni el formato de
  la revisión. No es una garantía: es una instrucción — si el corrector la
  ignora, la revisión seguirá cazándolo, y esa reincidencia es exactamente lo
  que el criterio de parada de arriba convierte en señal de buscar otra raíz.
- La palanca del modelo (opción 2) queda decidida como «más adelante» por el
  propietario, con las líneas exactas anotadas en la bitácora (entrada 27):
  `implement-sirius-work.yml:138`, `repair-sirius-work.yml:175`,
  `review-sirius-work.yml:122`.

## Alternativas descartadas y por qué

- **Solo el modelo más capaz (opción 2 en solitario):** ataca la frecuencia
  de defectos, no el mecanismo — con la regla actual, hasta un corrector
  perfecto que cambie código deja el ADR desfasado si entiende «únicamente lo
  señalado» al pie de la letra. Además el propietario la aplazó a propósito
  para medir una palanca cada vez.
- **El guardián de evidencia repetida (opción 3) ya:** sin medición previa de
  falsos positivos sería un guardián nacido al revés de como este repositorio
  los construye (G1 y G2 se midieron antes de escribirse). Queda como
  candidata con su medición pendiente.
- **Cambiar los «límites de corrección» que escribe el revisor:** tocaría el
  formato de la revisión (`.github/**` y sus prompts) — es del propietario, y
  antes de pedirlo hay que ver si la viñeta basta (criterio de parada).
