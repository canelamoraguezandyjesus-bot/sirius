# ADR-078 — Tres rondas consecutivas sobre el mismo archivo son la familia repetida, medido antes de fijarlo

- Estado: APROBADO
- Fecha: 2026-08-23
- Aprobación: fusión de la PR por el propietario
- Contexto: bloque M1 del plan del Work Engine, incidencia #277
- Relacionadas: ADR-001 (la regla de las dos rondas y la disciplina de
  evidencia que exige medir antes de fijar un criterio), incidencia #251
  (diagnosticar la causa raíz, fuera de este bloque), incidencia #267
  (mecanizar el método), `scripts/automation/sirius_convergence.py`
  (la política de convergencia real, que este bloque complementa sin tocar)

## Contexto y problema

La regla de las dos rondas está escrita en ADR-001 desde hace meses y hasta
este bloque la aplicaba una persona leyendo el hilo de la incidencia. La
noche del 22 al 23 de agosto de 2026 hizo falta aplicarla tres veces y se
detectó tarde dos de ellas. El objetivo del bloque M1 es una función
determinista que, dados los registros de ronda de una incidencia, diga si
las rondas recientes están dando vueltas sobre la misma familia de defecto
-y con qué evidencia lo dice-, sin diagnosticar la causa raíz (#251) ni
tocar la política de convergencia real.

El riesgo declarado en la nota de arranque de la incidencia #277 no es no
detectar: es **detectar de más**. Un detector que grite en cuanto dos rondas
tocan el mismo archivo convierte en alarma el caso normal -corregir un
fichero y que la revisión vuelva a mirarlo es lo esperable-, y una alarma
que salta siempre se ignora, que es peor que no tener detector.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la nota de arranque de la incidencia #277, antes de medir nada:

- (a) El criterio candidato se mide contra las incidencias reales del
  repositorio con más de una ronda: se cuenta cuántas señala, cuántas de
  esas eran de verdad la misma familia (comprobado a mano) y cuántas se le
  escaparon. Si los falsos superan a los ciertos, el criterio se cambia o el
  bloque se para.
- (b) Si hace falta red o un modelo para decidir si dos hallazgos son de la
  misma familia, se para.
- (c) Si hace falta tocar `sirius_convergence.py`, se para.
- (d) Cualquier edición de `.github/**` es criterio de parada (ADR-002).

Ninguno de los cuatro se disparó: la medición se hizo sobre datos ya leídos
con `gh issue view --json body,comments`, sin tocar `sirius_convergence.py`
ni `.github/**`, y sin consultar ningún modelo para juzgar similitud.

## Opciones consideradas

Las señales que la propia incidencia #277 declara, con lo que cada una
valía **antes de medir**:

1. **`fingerprint` idéntico entre rondas.** Señal fuerte en teoría, pero la
   huella incluye el texto del problema (`sirius_convergence.fingerprint`),
   así que un defecto persistente que el revisor describe con otras
   palabras nunca produce la misma huella. `sirius_convergence.decide` ya
   usa esta señal para su propio bloqueo por "reaparición", pero esa
   función solo la ve cuando un hallazgo **dado por resuelto** vuelve
   idéntico -no cuando persiste sin desaparecer nunca-, que es el caso que
   este bloque necesita cubrir.
2. **Mismo archivo en dos rondas consecutivas.** Es exactamente el falso
   positivo que la nota de arranque advierte: corregir un archivo y que la
   revisión lo mire una vez más es el patrón normal, no el patético.
3. **Mismo archivo en tres o más rondas, consecutivas o no.** Reduce los
   falsos frente a la opción 2, pero no los elimina: una incidencia real
   (#177) toca el mismo archivo en las rondas 1, 2 y 5 con progreso real -y
   una decisión humana de por medio- entre la 2 y la 5, y esta variante la
   habría señalado igual que un bucle de verdad.
4. **Mismo archivo en tres o más rondas CONSECUTIVAS** (sin hueco). Es la
   opción elegida; ver medición abajo.
5. **Severidad total que no baja entre apariciones del mismo archivo.**
   Medida como complemento de la opción 4 (ver abajo): no discrimina sobre
   los datos reales disponibles, así que no entra.

## Decisión

El criterio es: **un archivo que recibe hallazgos en 3 o más rondas
consecutivas** (mismo número de ronda, sin huecos) es evidencia de familia
repetida. La ubicación se normaliza igual que la huella de
`sirius_convergence.fingerprint` (se recorta el sufijo de línea, que se
desplaza con cualquier edición anterior del archivo), reutilizando
`sirius_engine.round_history._normalize_location` en vez de reinventar la
normalización.

Implementado en `src/sirius_engine/round_family_detector.py`
(`detectar_familia_repetida`, `EvidenciaFamiliaRepetida`,
`DeteccionFamiliaRepetida`) y su punto de entrada
`src/sirius_engine/round_family_detector_cli.py` (`sirius-familia-repetida`),
que opera sobre un historial ya leído -nunca llama a `gh` ni a la red él
mismo-.

## Comprobación que la sostiene

Datos: las 87 incidencias del repositorio (`gh issue list --state all`, del
#8 al #282), leídas con `gh issue view <n> --json body,comments` y filtradas
por contener al menos un marcador `sirius-round:`. 19 incidencias tenían
registros de ronda; tras `history_after_last_resume` (el mismo corte que usa
la convergencia real), **14 tenían más de una ronda vigente**: #148, #177,
#182, #186, #193, #202, #206, #211, #232, #240, #246, #247, #265, #268.

Con el criterio elegido (archivo en 3+ rondas consecutivas) aplicado a esas
14, se disparó en exactamente 4: **#182, #186, #211, #246**. Verificación a
mano, leyendo el texto de la revisión de cada una (no solo el bloque
`RONDA_HALLAZGOS`):

- **#246** (C3a): seis rondas, todas con hallazgos en
  `scripts/automation/sirius_check_docs.py`. Es el caso que la propia
  incidencia #277 cita como conocido.
- **#211**: la revisora lo confirma en su propio texto, ronda 3
  (`CLAUDE-REVISOR-001`): «Es la misma familia de defecto que CODEX-001
  (rondas 1 y 2 de esta misma PR): parseo heurístico y parcial de la
  gramática de banderas de `gh`». Confirmación directa, no inferida.
- **#182**: rondas 2-4 sobre `durable_journal.py`, con títulos "Evita
  truncar eventos válidos tras una corrupción interna" → "No trunques una
  última línea completa corrupta" → "Actualiza el criterio publicado de
  cola truncada": la misma familia (truncado del diario durable),
  refinándose ronda a ronda.
- **#186**: rondas 3-6 sobre `adapters/durable/store.py`, con títulos
  "Aísla las claves internas de las claves proporcionadas" → "Migra las
  claves internas ya persistidas" → "Conserva las claves públicas de
  cancelación al reabrir": la misma familia (aislamiento de claves
  internas), con casos límite nuevos en cada ronda.

**4 aciertos, 0 falsos, sobre las 4 incidencias señaladas.** El requisito 2
de la incidencia #277 exige acertar en #268 o #246; el criterio acierta en
#246 (y, con evidencia más explícita todavía, en #211).

Las 10 incidencias restantes con más de una ronda no dispararon el
criterio, y ninguna debía hacerlo: en particular #268 (rondas 1-2 comparten
`seven_day_streak_cli.py`, pero solo 2 consecutivas, nunca 3) y #177
(`memory_store.py` en las rondas 1, 2 y 5 -no consecutivas-, con progreso
real y una decisión humana de por medio) son justo los casos que un umbral
más laxo (2 consecutivas, o 3 sin exigir consecutividad) habría señalado de
más.

Complemento medido y descartado: `severidad_total` no decreciente entre
apariciones consecutivas del mismo archivo, sobre los 6 archivos que llegan
a 3+ apariciones totales (consecutivas o no). Resultado: 6 de 6 tienen al
menos un paso sin bajada, así que la señal no discrimina sobre los datos
reales disponibles y no aporta nada sobre el criterio de consecutividad
elegido - no entra.

Comandos ejecutados (reproducibles con acceso a este repositorio):

```
gh issue list --repo canelamoraguezandyjesus-bot/sirius --state all --limit 300 --json number
gh issue view <n> --repo canelamoraguezandyjesus-bot/sirius --json body,comments -q '...'
uv run python3 -c "from sirius_engine.round_history import parse_round_records, history_after_last_resume; ..."
```

Suite del bloque: `tests/engine/test_round_family_detector.py` (fija el
umbral, replica #246 y #211 con datos reales, y fija que #268 y el patrón de
#177 NO se señalan) y `tests/engine/test_round_family_detector_cli.py`
(costura del comando). `uv run pytest tests/automation/test_sirius_convergence.py`
sigue en verde sin modificar ese archivo (requisito 6).

## Consecuencias

- El detector puede no señalar una familia repetida real cuando el mismo
  defecto se manifiesta en archivos distintos (caso #268) o cuando una
  ronda "de paso" sobre otro archivo rompe la consecutividad. Es una
  limitación conocida y aceptada: el objetivo del bloque es no gritar de
  más, no atrapar cada caso posible; #251 puede ampliar la cobertura con
  otra señal, si la mide.
- Un archivo grande y activo durante muchas rondas seguidas (p. ej. un
  spike experimental) puede disparar el criterio aunque cada hallazgo sea
  distinto en sustancia; la medición sobre datos reales no encontró ningún
  caso así entre los 4 disparados, pero el diseño no lo descarta por
  construcción -es el motivo por el que el resultado incluye la evidencia
  concreta (qué rondas, qué archivo) en vez de un booleano solo.
- El detector no cambia ningún comportamiento existente: no lo llama nada
  todavía (cablearlo al flujo de revisión es `.github/**` y queda fuera de
  este bloque, ADR-002).

## Alternativas descartadas y por qué

- **Mismo archivo en 2 rondas consecutivas**: descartada por la nota de
  arranque antes de medir -es el caso normal declarado en el requisito 3- y
  confirmada como mala elección por los datos (#268 la habría disparado).
- **Mismo archivo en 3+ rondas sin exigir consecutividad**: descartada tras
  medir -#177 la habría disparado sobre un caso de progreso real-.
- **`severidad_total` no decreciente como señal adicional**: medida y
  descartada por no discriminar (6 de 6 candidatos la cumplían, aciertos y
  no-aciertos por igual).
- **Consultar un modelo para juzgar si dos hallazgos son la misma
  familia**: es el criterio de parada (b) de la nota de arranque; ni se
  intentó.
