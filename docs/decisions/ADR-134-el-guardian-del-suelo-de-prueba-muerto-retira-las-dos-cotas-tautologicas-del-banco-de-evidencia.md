# ADR-134 — El guardián del suelo de prueba muerto retira las dos cotas tautológicas del banco de evidencia

- Estado: PROPUESTO
- Fecha: 2026-09-04
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

Este ADR registra G2, la propuesta 2 de
`docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09.md` (rama
`claude/adr002-tol209-forensic-audit-i0ui8k`, secciones 4, 6 y 8), aprobada
por el propietario el 04-09-2026, incidencia #526.

## Asignación del número

Este ADR ocupa **ADR-134**, número asignado directamente por la incidencia
#526 en vez de calculado con `scripts/siguiente_adr.py`. El máximo real en
`main` en el momento de escribir esto es ADR-132 (G1, incidencia #522,
fusionado en `9fd2666`), así que el guion habría propuesto 133 — pero ADR-133
ya existe, sin fusionar, en la rama de la incidencia #523 (en vuelo a la vez
que esta). Usar «el siguiente» habría repetido, esta misma mañana, la
colisión de dos ADR con el mismo número que ya obligó a renumerar una vez
(bitácora del ciclo, entrada 24) — el guion solo ve los ADR del árbol de
trabajo y las ramas que el clon conoce, y una rama hermana en vuelo con la
que no hay `git fetch` no cuenta. Se asigna 134, un hueco por encima del 133
en vuelo, para no volver a colisionar.

## Contexto y problema

«Prueba que no puede fallar» es la familia de defecto más extendida de la
ola de criticidad medida por la mina (7 hallazgos en 4 de 8 encargos, §4). Su
caso más simple y mecánicamente detectable es el suelo muerto: una constante
o una aserción escritas con forma de cota, pero cuyo valor hace que la
comparación sea cierta para cualquier entrada posible. En `main` hay hoy
exactamente dos, los dos en
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`:

1. la constante `_MINIMO_ACIERTOS_EXACTOS_PAQUETE_COMPLETO: Final[int] = 0`
   (línea 258), con su aserción `assert paquete_completo.aciertos_exactos >=
   _MINIMO_ACIERTOS_EXACTOS_PAQUETE_COMPLETO` (línea 2334);
2. la aserción suelta `assert paquete_completo.elementos_de_mas >= 0` (línea
   2335).

Las dos nacieron en M20 (incidencia #516, ADR-129), cuando la siembra en
contexto bajó `aciertos_exactos` a su nuevo suelo medido (0/47) y dejó esa
cota tautológica. CODEX-001 (incidencia #516, r3924271714) señaló la
tautología y corrigió AL LADO, añadiendo dos suelos vivos nuevos
(`_MAXIMO_OMISIONES_CRITICAS_PAQUETE_COMPLETO = 0` como techo, y
`_MINIMO_ELEMENTOS_HALLADOS_PAQUETE_COMPLETO = 72`), pero dejó los dos
muertos puestos: la corrección añadió guarda real sin quitar la guarda falsa.
`docs/audits/mina-2026-09-medicion-de-guardianes.md` registra, con comandos
literales, la medición que confirma que esas dos formas son las únicas que
aparecen hoy en el corpus real (§6 del informe), la misma medición que este
ADR repite más abajo (ver "Comprobación que la sostiene").

## Nota de arranque (ADR-001, disciplina-evidencia, publicada antes del primer commit de código)

**1. ¿Dónde vive el fallo y dónde voy a poner el arreglo? ¿Puede el sitio del
arreglo observar el fallo que arregla?**

El fallo vive en `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`:
una constante y una aserción con forma de cota que ninguna ejecución puede
incumplir.

El guardián se pone en un fichero nuevo,
`tests/automation/test_suelo_de_prueba_muerto.py`, fuera del fichero que
vigila — recorre por glob `tests/acceptance/*.py` y busca, línea por línea,
las dos formas textuales descritas en el encargo. No depende de ejecutar el
banco de evidencia (que tarda segundos y necesita SQLite/migraciones) ni de
que una prueba tautológica se autodiagnostique: una aserción que siempre pasa
no puede informar de que siempre pasa, pero un fichero de texto sí puede
leerse sin ejecutarlo.

El arreglo se pone en el mismo fichero que falla. Que el arreglo viva "dentro
de lo que falla" no es un problema aquí porque quien certifica que el arreglo
es correcto no es el propio fichero, sino el guardián externo (a) y la
comprobación de que las cifras del banco no cambian (e), que se ejecutan por
separado y ya vieron fallar el estado viejo.

**2. ¿Qué NO va a garantizar esto?**

- No detecta cualquier forma de prueba vacua: solo las dos formas textuales
  exactas que el encargo describe (`_MINIMO_*: Final[int] = 0` y
  `assert <expresión> >= 0` como línea completa). Una tautología escrita de
  otra manera (por ejemplo `assert x == x`, o un suelo `_MINIMO_*` en un
  valor distinto de 0 que en la práctica nunca se alcanza) queda fuera de
  esta regla estrecha a propósito — ampliarla es una decisión de producto
  futura, no de este encargo.
- No juzga una comparación encadenada (`assert 0 <= x <= y`): ahí la mitad
  izquierda es la misma tautología, pero la mitad derecha sí puede fallar, y
  decidir cuál mitad importa es un juicio del propietario. El guardián deja
  ese caso pasar a propósito (caso adversario, ver mutación 3 más abajo).
- No mira `src/`: un suelo muerto es un defecto de la prueba, nunca del
  código que prueba; el guardián recorre únicamente `tests/acceptance/*.py`.
- No cambia ninguna adjudicación del banco, ningún caso del corpus, ni
  `criticidad.razon_segura` (prohibición dura del encargo): solo retira dos
  aserciones que nunca podían fallar.

**3. Criterio de parada, decidido antes de ver ningún resultado**

- El guardián recién escrito debe fallar sobre EXACTAMENTE un fichero
  (`test_pa_0_2_rec_01_banco_evidencia.py`) y sobre exactamente dos casos
  (la constante de la línea 258 y la aserción de la línea 2335), antes de la
  retirada; tras la retirada, verde sobre todo `tests/acceptance/`.
- Si el guardián encuentra un tercer caso en cualquier fichero de
  `tests/acceptance/`, PARO con `BLOCKED_BY_DECISION`: el encargo predice
  exactamente dos y amplía el alcance decidir qué hacer con un tercero no
  anticipado.
- Si retirar la constante o las dos aserciones tautológicas hace fallar
  cualquier otra prueba (incluida `test_el_guardia_del_paquete_completo_ya_no_es_tautologico`),
  PARO con `BLOCKED_BY_DECISION` en vez de tocar los suelos vivos de M20 para
  compensar.
- Si `uv run python scripts/medir_variantes_de_criticidad.py` o las cifras de
  `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py` cambian respecto a
  las de hoy en `main` (0 omisiones críticas, 72/81; 28 passed, 1 skipped, 1
  xfailed), PARO con `BLOCKED_BY_DECISION`: solo se retiran aserciones que no
  podían fallar, así que ninguna métrica del banco debería moverse; si se
  mueve, la premisa está mal y no es mío decidir cómo seguir.
- Dos rondas de validación (`ruff`/`mypy`/`pytest`) seguidas fallando por la
  misma causa → paro a diagnosticar la raíz en vez de seguir parcheando.

**4. ¿Qué haría el fallo imposible en vez de improbable?**

El guardián recorre `tests/acceptance/*.py` por glob, no por una lista
mantenida a mano: un fichero de aceptación nuevo que reintroduzca cualquiera
de las dos formas queda cubierto sin tocar la prueba, lo que convierte
"alguien reintroduce un suelo muerto sin que nadie lo note" en imposible en
vez de improbable, para estas dos formas concretas. No hace imposible el
residual descrito en la pregunta 2 (otras formas de tautología, la mitad
muerta de una cadena `0 <= x <= y`): ese riesgo queda explícitamente
aceptado, no eliminado — es exactamente el trade-off que ya validó
`test_contrato_http_de_ollama.py` (G1, ADR-132) para el mismo estilo de
guardián textual.

## Criterio de parada (escrito ANTES de decidir)

Ver "Nota de arranque" arriba, punto 3: es el mismo criterio, publicado antes
de ejecutar el guardián por primera vez.

## Opciones consideradas

1. **Guardián por glob sobre el texto de `tests/acceptance/*.py`, dos
   patrones por línea** (elegida). Barata, determinista, cubre ficheros
   futuros sin tocar la prueba; mismo estilo que `test_citas_de_los_adr.py` y
   `test_contrato_http_de_ollama.py`, ya aceptado en este repositorio.
2. Guardián por AST (parsear cada módulo y recorrer las asignaciones y
   aserciones como árbol de sintaxis). Más preciso ante formato exótico
   (una aserción partida en varias líneas, por ejemplo), pero bastante más
   código para un patrón que hoy es siempre de una sola línea en el corpus
   real. Descartada por complejidad no pedida por el encargo — si el
   corpus real desarrolla asserts multilínea, el mismo residual que acepta
   `test_contrato_http_de_ollama.py` para su propio barrido textual aplica
   aquí igual.
3. Ampliar la regla para cubrir también la mitad muerta de una comparación
   encadenada (`0 <= x <= y`). Descartada explícitamente por el encargo:
   decidir qué mitad de una cadena importa es un juicio del propietario, no
   mecánico — el guardián que lo intentara se equivocaría en casos donde la
   cota de 0 sea la que de verdad importa (por ejemplo, una métrica que
   pudiera ser negativa por error de cálculo).

## Decisión

Se implementa el guardián por glob sobre texto (opción 1) en
`tests/automation/test_suelo_de_prueba_muerto.py`, y se retiran en
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`:

- la constante `_MINIMO_ACIERTOS_EXACTOS_PAQUETE_COMPLETO: Final[int] = 0`;
- `assert paquete_completo.aciertos_exactos >= _MINIMO_ACIERTOS_EXACTOS_PAQUETE_COMPLETO`;
- `assert paquete_completo.elementos_de_mas >= 0`.

Se conservan intactos los dos suelos vivos de M20
(`_MAXIMO_OMISIONES_CRITICAS_PAQUETE_COMPLETO` y
`_MINIMO_ELEMENTOS_HALLADOS_PAQUETE_COMPLETO`, con sus dos aserciones), la
cota superior `elementos_hallados <= elementos_esperados_total`, y la cifra
de `aciertos_exactos` — que sigue IMPRESA como evidencia adicional (nunca
afirmada: el porqué está en ADR-129 y en el comentario `#:` que precede a
`_MAXIMO_OMISIONES_CRITICAS_PAQUETE_COMPLETO`). Se actualiza
`test_el_guardia_del_paquete_completo_ya_no_es_tautologico`, que nombraba la
constante retirada: su docstring y su cuerpo se reescriben para explicar la
retirada (la prueba de forma que fija — que el caso degenerado del hallazgo
sigue cayendo por las dos cotas vivas — sigue vigente sin la cota muerta que
antes también "cumplía"). El docstring del módulo que explica que
`aciertos_exactos` dejó de ser afirmable con la siembra (M20) se conserva,
reescrito para dejar de referirse a una constante que ya no existe y para
contar la retirada de G2.

**No se toca** la prueba `xfail(strict=True)`
`test_el_suelo_del_criterio_de_m11_aciertos_exactos_29_47_en_el_paquete_completo`
(prohibición dura del encargo): su docstring menciona en prosa
`_MINIMO_ACIERTOS_EXACTOS_PAQUETE_COMPLETO` (línea 2402 antes de la
retirada) como referencia histórica a "la cota de no regresión de arriba"; se
deja tal cual, ahora como mención a una constante ya retirada, porque
tocarla exigiría tocar la prueba que el encargo prohíbe tocar. No es una cita
que ningún guardián verifique (no es una ruta de fichero, así que
`test_citas_de_los_adr.py` no la mira), así que queda como texto histórico
inerte, igual que cualquier otro comentario que envejece.

## Comprobación que la sostiene

**(a) El guardián, en rojo sobre `main`, exactamente como predijo el
encargo.** `tests/automation/test_suelo_de_prueba_muerto.py` recorre por
glob `tests/acceptance/*.py` y busca, en cada línea recortada de espacios,
las dos formas descritas. Sobre el árbol antes de la retirada:

```
$ uv run pytest tests/automation/test_suelo_de_prueba_muerto.py -q
.................F.
=================================== FAILURES ===================================
_______ test_no_hay_suelo_muerto[test_pa_0_2_rec_01_banco_evidencia.py] ________
E       AssertionError: test_pa_0_2_rec_01_banco_evidencia.py:258 (constante _MINIMO_*: Final[int] = 0); test_pa_0_2_rec_01_banco_evidencia.py:2335 (assert <expresión> >= 0) -- ...
1 failed, 18 passed in 0.12s
```

Exactamente un fichero falla, con exactamente los dos casos predichos (línea
258 y línea 2335) — la predicción exacta del encargo y del criterio de parada
de la nota de arranque; no se disparó.

**(b) La retirada, verde sobre todo `tests/acceptance/`:**

```
$ uv run pytest tests/automation/test_suelo_de_prueba_muerto.py -q
...................
19 passed in 0.04s
```

(19 en vez de 18: la retirada de las dos aserciones tautológicas del banco
de evidencia hace que también pase, ahora, el caso parametrizado que antes
fallaba — un caso nuevo verde, no una prueba nueva del guardián.)

**Cifras del banco, sin cambio.** Antes y después de la retirada:

```
$ uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q
.........................s...x
28 passed, 1 skipped, 1 xfailed in ~5s
```

Idéntico a antes de tocar nada (mismo recuento que registró ADR-132: 28
passed, 1 skipped, 1 xfailed).

```
$ uv run python scripts/medir_variantes_de_criticidad.py
  variante            exactos  de mas  crit perdidas  cobertura
  hoy                    0/47     487              0      72/81
```

Idéntico a lo medido por ADR-132 sobre `main`: 0 omisiones críticas, 72/81.
Ninguna métrica del banco se movió, tal como predecía la nota de arranque:
solo se retiraron aserciones que no podían fallar, así que no hay pipeline
que cambiar para que sigan sin fallar.

**(c) Las tres mutaciones, cada una vista fallar (o no fallar) exactamente
donde predice el encargo**, aplicadas temporalmente sobre
`test_pa_0_2_rec_01_banco_evidencia.py` ya retirado, y revertidas después de
cada una:

1. **Reintroducir `_MINIMO_ALGO_MUTACION_1: Final[int] = 0`** (junto a
   `_MAXIMO_OMISIONES_CRITICAS_PAQUETE_COMPLETO`, línea 266 tras la
   inserción):

   ```
   $ uv run pytest tests/automation/test_suelo_de_prueba_muerto.py -q -k test_no_hay_suelo_muerto
   E       AssertionError: test_pa_0_2_rec_01_banco_evidencia.py:266 (constante _MINIMO_*: Final[int] = 0) -- ...
   1 failed, 3 passed, 15 deselected in 0.05s
   ```

   El guardián falla y nombra el fichero y la línea exactos.

2. **Reintroducir un `assert x >= 0` suelto**
   (`assert paquete_completo.elementos_de_mas >= 0`, línea 2343 tras la
   inserción):

   ```
   $ uv run pytest tests/automation/test_suelo_de_prueba_muerto.py -q -k test_no_hay_suelo_muerto
   E       AssertionError: test_pa_0_2_rec_01_banco_evidencia.py:2343 (assert <expresión> >= 0) -- ...
   1 failed, 3 passed, 15 deselected in 0.05s
   ```

   El guardián falla y nombra el fichero y la línea exactos.

3. **Convertir una cota viva en comparación encadenada**
   (`assert 0 <= paquete_completo.omisiones_criticas <=
   _MAXIMO_OMISIONES_CRITICAS_PAQUETE_COMPLETO`) — el caso adversario que el
   guardián debe dejar pasar:

   ```
   $ uv run pytest tests/automation/test_suelo_de_prueba_muerto.py -q -k test_no_hay_suelo_muerto
   ....
   4 passed, 15 deselected in 0.03s
   ```

   El guardián NO falla: la mitad derecha de la cadena (`<=
   _MAXIMO_OMISIONES_CRITICAS_PAQUETE_COMPLETO`) sí puede fallar, así que la
   aserción entera sigue siendo una prueba viva — exactamente el
   comportamiento que la nota de arranque (pregunta 2) fija a propósito.

Las tres mutaciones se aplicaron con un script Python puntual y se
revirtieron con `git checkout --` inmediatamente después de capturar cada
salida; el árbol de trabajo entre mutaciones estaba limpio (`git status
--short` vacío) antes de aplicar la siguiente.

**Validaciones obligatorias, en verde sobre el árbol final:**

```
$ uv run ruff format --check .    # 596 files already formatted
$ uv run ruff check .             # All checks passed!
$ uv run mypy src tests           # Success: no issues found in 564 source files
$ uv run pytest -q                # 4697 passed, 15 skipped, 2 xfailed in 423.87s
$ git diff --check                # limpio
```

(`test_toda_ruta_citada_por_un_adr_existe` exigió registrar las dos citas de
este ADR a `docs/audits/` en `RAMA_DE_ORIGEN_NO_FUSIONADA` de
`tests/automation/test_citas_de_los_adr.py`, mismo patrón ya usado por
ADR-132 para las mismas dos rutas: ambas viven solo en la rama
`claude/adr002-tol209-forensic-audit-i0ui8k`, que a propósito nunca se
fusiona entera.)

## Consecuencias

- `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py` ya no contiene
  ninguna aserción que no pueda fallar: las dos formas de suelo muerto
  medidas por la mina para este fichero quedan retiradas, y el guardián
  nuevo hace que reintroducir cualquiera de las dos formas en cualquier
  fichero de `tests/acceptance/` (presente o futuro) falle de inmediato en
  vez de colar otra ronda de "prueba que no puede fallar".
- Ninguna métrica del banco de evidencia cambia: la retirada es puramente de
  aserciones tautológicas, no de comportamiento medido.
- La regla del guardián es deliberadamente estrecha (dos formas, cero falsos
  positivos medidos hoy) y deja pasar a propósito la mitad muerta de una
  comparación encadenada: un residual aceptado, no una laguna descubierta
  después.
- `test_el_suelo_del_criterio_de_m11_aciertos_exactos_29_47_en_el_paquete_completo`
  (la prueba `xfail(strict=True)`, intocada por prohibición dura) queda con
  una mención en prosa a una constante ya retirada
  (`_MINIMO_ACIERTOS_EXACTOS_PAQUETE_COMPLETO`) en su docstring: texto
  histórico inerte, sin verificación automática que dependa de él.
- Patrón a vigilar en futuros encargos de este repositorio (mismo tipo que
  registró ADR-132 para la prosa entre comillas invertidas): una corrección
  que añade guarda real "al lado" de una guarda muerta, sin retirar la
  muerta, dejará el defecto vivo hasta que un guardián dedicado lo mida — la
  mina de 2026-09 lo encontró exactamente así en M20/CODEX-001.

## Alternativas descartadas y por qué

Ver "Opciones consideradas".
