# ADR-105 — Añadir RAMA_DE_ORIGEN_NO_FUSIONADA al guardián de citas de los ADR

- Estado: PROPUESTO
- Fecha: 2026-08-29
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

## Contexto y problema

La incidencia #445 (M7, Arquitectura Técnica 0.2 §6.5 y §8-M7) sustituye a la
#441, cerrada sin fusionar porque `tests/automation/test_citas_de_los_adr.py`
(`test_toda_ruta_citada_por_un_adr_existe`) falló: ADR-104 —que documenta cómo
se portó el banco de 47 casos desde `evidence/adr001-spikes` a
`tests/acceptance/fixtures/evidence_bank_47_casos.json`— cita, dentro de su
sección «Opciones consideradas», cuatro rutas del árbol experimental ADR-002
para explicar de qué fichero exacto de la rama de origen salió cada dato
portado.
Esas cuatro rutas no existen en `main` y el encargo de M7 prohíbe explícitamente
copiar código de producto o de `experiments/` a `main` (solo se porta el
fixture congelado y la prueba de medición).

El guardián solo conocía dos categorías de excepción para una cita que no
resuelve: `BORRADOS_A_PROPOSITO` (existió en `main`, se borró a propósito, el
ADR la cita como historia) y `TODAVIA_NO_EXISTEN` (nunca ha existido, el ADR
cita su ausencia como la propia afirmación). Ninguna de las dos describe este
caso: las cuatro rutas SÍ existen, hoy mismo, pero en otra rama que nunca se
fusiona entera a `main` a propósito (decisión D1: el corpus se porta intocable,
sin arrastrar la familia experimental ADR-002 completa).

## Criterio de parada (escrito ANTES de decidir)

Si alguna de las cuatro rutas citadas por ADR-104 existiera en `main` en algún
momento (verificado con `(RAIZ / ruta).exists()`), la exclusión estaría mal
planteada — la cita no describe una rama sin fusionar, sino un fichero que se
movió o se borró de verdad, y tocaría usar `BORRADOS_A_PROPOSITO` o corregir la
cita. Si las cuatro rutas no se pudieran verificar como existentes en
`evidence/adr001-spikes` (la rama de origen que ADR-104 nombra), la conclusión
correcta era `BLOCKED_BY_DECISION`, no inventar una excepción para una cita que
ni siquiera describe su procedencia real.

## Opciones consideradas

1. Añadir las cuatro rutas a `BORRADOS_A_PROPOSITO`. Descartada: ese diccionario
   documenta «existió en `main` y se borró a propósito» (su comentario cita
   ADR-027/028/052 exactamente en ese sentido); estas rutas nunca estuvieron en
   `main`, así que la etiqueta mentiría sobre la historia del árbol.
2. Añadir las cuatro rutas a `TODAVIA_NO_EXISTEN`. Descartada: ese diccionario
   documenta una ausencia que **es** la afirmación del ADR (ADR-055: «no existe
   todavía la puerta…»); aquí la ausencia en `main` no es lo que ADR-104
   afirma — afirma cómo se calculó un dato citando su rama de origen, y la
   ruta sí existe, solo que en otro sitio.
3. Reescribir ADR-104 para no citar las cuatro rutas, sustituyéndolas por prosa
   sin `código en línea`. Descartada: la propia sección «Opciones consideradas»
   necesita nombrar el fichero exacto de la rama de origen para que la
   comprobación posterior («Comprobación que la sostiene») sea verificable —
   quitarlo debilitaría la evidencia que ADR-001 exige, no el guardián.
4. **(Elegida)** Añadir una tercera categoría, `RAMA_DE_ORIGEN_NO_FUSIONADA`,
   con semántica propia: «esta ruta existe en otra rama nombrada, que a
   propósito nunca se fusiona entera a `main`; el ADR la cita para contar de
   dónde vino un dato, no para exigir que viva aquí». Con la lista cerrada de
   `(ruta, [ADR que puede citarla])`, igual que las otras dos categorías, y sus
   propias dos pruebas espejo (no resucitó en `main`; la excepción sigue
   citada de verdad por quien dice citarla) para que no se quede obsoleta en
   silencio.

## Decisión

Se añade `RAMA_DE_ORIGEN_NO_FUSIONADA: dict[str, list[str]]` a
`tests/automation/test_citas_de_los_adr.py`, con las cuatro rutas exactas que
`ADR-104-portar-el-banco-de-47-casos-de-evidence-adr001-spikes-al-modelo-real-de-sirius.md`
cita (fuera de bloque de código aquí, a propósito, para que este mismo ADR no
las presente como una cita que el guardián deba resolver — la única cita que
importa exigir es la de ADR-104):

```
experiments/adr002/round/cases.py
experiments/adr002/round/cases.py:_traducir
experiments/adr002/benchmark/cases_v0_5.json
experiments/adr002/projection/contracts.py:referencia_canonica
```

`_rotas()` excluye una ruta rota cuando el ADR que la cita está en la lista
cerrada de `RAMA_DE_ORIGEN_NO_FUSIONADA.get(ruta, [])`, exactamente con el
mismo patrón ya usado para las otras dos categorías. Ningún otro fichero del
repositorio queda afectado: el guardián sigue exigiendo, sin excepción, que
cualquier otra cita de cualquier otro ADR resuelva en `main`.

## Comprobación que la sostiene

Antes del cambio, sobre `ADR-104` ya copiado a este árbol (commit de origen
`c5cb112`, rama `feature/441-banco-evidencia-47-casos-m7`):

```
$ uv run python3 -c "
import sys; sys.path.insert(0, 'tests/automation')
import test_citas_de_los_adr as m
from pathlib import Path
adr = Path('docs/decisions/ADR-104-portar-el-banco-de-47-casos-de-evidence-adr001-spikes-al-modelo-real-de-sirius.md')
print(m._rotas(adr))
"
['experiments/adr002/round/cases.py', 'experiments/adr002/benchmark/cases_v0_5.json',
 'experiments/adr002/round/cases.py:_traducir', 'experiments/adr002/projection/contracts.py:referencia_canonica']
```

Las cuatro coinciden, carácter a carácter, con las cuatro rutas que la
incidencia #445 nombra como causa exacta del fallo de #441.

Verificado que las cuatro existen en la rama de origen que ADR-104 nombra:

```
$ git cat-file -e origin/evidence/adr001-spikes:experiments/adr002/round/cases.py && echo ok
ok
$ git cat-file -e origin/evidence/adr001-spikes:experiments/adr002/benchmark/cases_v0_5.json && echo ok
ok
```

(Las dos rutas con sufijo de símbolo, `:_traducir` y `:referencia_canonica`,
nombran una función dentro de esos mismos dos ficheros — no un fichero
adicional — y por eso no se comprueban con `git cat-file -e` por separado.)

Después del cambio: `uv run pytest tests/automation/test_citas_de_los_adr.py
-q` → 130 passed (incluye
`test_toda_ruta_citada_por_un_adr_existe[ADR-104-...]`,
`test_lo_fijado_como_rama_de_origen_no_fusionada_sigue_sin_existir_en_main` y
`test_lo_fijado_como_rama_de_origen_no_fusionada_lo_cita_de_verdad_quien_dice_citarlo`).
Suite completa (`uv run pytest`) en verde tras el cambio — ver el resumen de la
PR de la incidencia #445.

## Consecuencias

- El guardián sigue siendo estricto para el resto del repositorio: la nueva
  categoría es una lista cerrada de cuatro pares `(ruta, ADR)`, no un
  interruptor general.
- Si cualquiera de las cuatro rutas del árbol experimental ADR-002 llegara a
  fusionarse a `main` alguna vez (ninguna orden de M7-M11 lo pide),
  `test_lo_fijado_como_rama_de_origen_no_fusionada_sigue_sin_existir_en_main`
  fallaría de inmediato, señalando que la excepción ya sobra.
- Si ADR-104 se reescribiera para no citar ya esas rutas,
  `test_lo_fijado_como_rama_de_origen_no_fusionada_lo_cita_de_verdad_quien_dice_citarlo`
  fallaría, señalando la misma obsolescencia desde el otro lado.

## Alternativas descartadas y por qué

Ver «Opciones consideradas»: reutilizar `BORRADOS_A_PROPOSITO` o
`TODAVIA_NO_EXISTEN` habría etiquetado mal la historia del árbol (ninguna de
las cuatro rutas existió nunca en `main`, y su ausencia no es lo que ADR-104
afirma), y reescribir ADR-104 para no citarlas habría debilitado la evidencia
que su propia sección «Opciones consideradas» necesita para ser verificable.
