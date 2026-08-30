# ADR-111 — La petición por caso portada mejora el banco a 23/47 pero D1 exige además el índice de categoría y el filtro de relevancia Ollama

- Estado: PROPUESTO
- Fecha: 2026-08-30
- Aprobación: fusión de la PR por el propietario — este ADR documenta el
  diagnóstico que la propia incidencia #461 pide si, tras portar la petición
  por caso y su traductor, la cifra sigue por debajo del suelo D1.

## Contexto y problema

ADR-110 (incidencia #457) midió el motor por etapas portado (puertas
`G1-G12`, agrupación de equivalentes, motor `E0-E5`) con una política
**uniforme** para las 47 consultas del banco (modo M1, ámbito por caso,
cardinalidad EXHAUSTIVA, límite sin atar) y obtuvo 11/47, muy por debajo del
suelo de D1 (aciertos exactos ≥ 29/47). Su diagnóstico, con cita de fichero y
línea, fue que el 29/47 que PR #117 midió en el laboratorio depende de una
petición **por caso** (modo, permiso, cardinalidad y límite, cada uno
declarado por consulta) que `experiments/adr002/round/cases.py:334-366`
construye a partir de `cases_v0_5.json`/`references_v0_5.json`, y que ni
esos dos ficheros ni ese traductor estaban entre lo que el alcance permitido
de la incidencia #457 autorizaba portar.

La incidencia #461 autoriza exactamente ese porte: los campos de petición
por caso del fixture (`peticion_p2`: modo, propósito, permiso, cardinalidad,
límite, tiempo objetivo, corte de registro), el traductor de
`cases.py:334-366` (portado a
`tests/acceptance/staged_engine_case_translation.py`, citando su origen), y
el cableado del arnés del banco para construir la `Peticion` de cada caso
con esos campos en vez de la política uniforme de ADR-110.

**Las tres piezas se portaron**:

- `tests/acceptance/fixtures/evidence_bank_47_casos.json` — enriquecido con
  `peticion_p2` por caso (modo, propósito, permiso, tiempo_objetivo,
  corte_registro, cardinalidad, límite), portados sin modificar desde
  `cases_v0_5.json` (instanciación, por `identificador_canonico`) y
  `references_v0_5.json` (`adjudicacion.dominio.limite`) — mismo commit
  `dfdcdaff04dcba10939cc0b0569c55b6a636296f` de `evidence/adr001-spikes` que
  ya citaba la nota de procedencia del fixture. No se tocó ningún `caso`,
  `resultado_esperado` ni adjudicación existente.
- `tests/acceptance/staged_engine_case_translation.py` — módulo nuevo del
  arnés de aceptación, citando su origen
  (`experiments/adr002/round/cases.py:334-366`, `_traducir`), con las cuatro
  traducciones no obvias del original (permiso `NO_AUTORIZADO` → propósito
  vacío; límite no declarado → límite que no ata; tiempo en intervalo →
  extremo final; objetivos de cardinalidad `EXACTA` →
  `len(caso["resultado_esperado"])`, la cuota que `_suficiente`/
  `evaluar_suficiencia` exigen antes de detener la expansión). No porta la carga de los tres artefactos congelados
  (`cargar_artefactos`/`casos_ejecutables`): el fixture ya trae los campos
  verbatim, así que solo se porta la traducción.
- `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py` (`_ejecutar_banco_motor_portado`)
  — cableado para construir la `Peticion` de cada caso con
  `peticion_desde_caso(caso, ...)` en vez de la política uniforme
  (`Modo.M1_ORDINARIO`/`Cardinalidad.EXHAUSTIVA`/`tiempo_objetivo` fijo) que
  ADR-110 medía. El ámbito sigue resolviéndose igual que en ADR-110 (contra
  los `Project` reales que el propio arnés crea), porque esa parte del
  arnés ya no era uniforme desde ADR-110.

**Resultado medido**,
`uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`:

| métrica | política uniforme (ADR-110) | petición por caso (este ADR) | objetivo D1/D2 |
|---|---|---|---|
| aciertos_exactos | 11/47 | **23/47** | ≥ 29/47 |
| elementos_de_mas | 186 | **90** | ≤ 21 |
| omisiones_criticas | 9 | **10** | ≤ 1 |
| cobertura | 60/81 (74.1%) | **63/81 (77.8%)** | ≥ 63/81 |

Tres de las cuatro métricas mejoran de forma sustancial (aciertos_exactos
más que se duplica, elementos_de_mas baja a menos de la mitad, cobertura
alcanza exactamente el suelo de D2); la cuarta, omisiones_criticas, empeora
en una unidad (9 → 10) frente a la política uniforme. Ninguna de las cuatro
alcanza el suelo de D1/D2 que la incidencia pide afirmar como aserción
dura.

## Diagnóstico: por qué la petición por caso, ya idéntica a la del laboratorio, no basta

La petición por caso portada es la misma que
`experiments/adr002/round/cases.py:334-366` construye: mismo modo, mismo
propósito (vacío exactamente cuando el permiso es `NO_AUTORIZADO`, las
`B04-CA-12`/`B04-CA-46` del banco), misma cardinalidad, mismo límite (los
cinco casos que lo declaran —`B04-CA-26`, `B04-CA-30`, `B04-CA-34`,
`B04-CA-38`, `B04-CA-44`— reciben exactamente el objetivo/duro que
`references_v0_5.json` adjudica), mismo tiempo objetivo (con el mismo
extremo final para el único caso que lo declara como intervalo).

La revisión de esta incidencia detectó una diferencia real que sí quedaba
pendiente: los tres casos con cardinalidad `EXACTA` y más de un elemento
esperado (`B04-CA-19` con 3, `B04-CA-23` y `B04-CA-43` con 2) recibían
`Peticion.objetivos` en su valor por defecto (1) en vez de la cuota real
adjudicada, porque el porte inicial no la transportaba. Corregido —
`objetivos` toma ahora `len(caso["resultado_esperado"])` cuando la
cardinalidad es `EXACTA` (`tests/acceptance/staged_engine_case_translation.py`)—,
la medición no cambia: `uv run pytest
tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s` sigue
imprimiendo 23/47, 90, 10, 63/81, idéntico al porte inicial, porque en los
tres casos la etapa que ya satisfacía la cuota antigua (1) contenía, sin
necesidad de expansión adicional, los mismos elementos que la cuota
corregida permite seguir buscando. No hay ninguna otra diferencia de
traducción pendiente: `peticion_desde_caso` es `_traducir` línea a línea
sobre los mismos campos.

La diferencia que queda no está en el traductor ni en el arnés: está en
**qué mide el banco de 47 casos frente a qué mide D1**. El propio 29/47 que
la Definición de Producto registra no es la cifra de la búsqueda por sí
sola — es el **resultado conjunto** de tres piezas, ninguna de las cuales
es solo "el motor por etapas con petición por caso" que esta incidencia y
la #457 anterior autorizan portar:

> Medido sobre un banco congelado de 47 casos:
> - un índice de categoría derivado de la criticidad del canon
>   (determinista, sin modelo), que por sí solo baja las omisiones críticas
>   de 11 a 5;
> - un filtro de relevancia con modelo local vía Ollama que falla abierto;
> - una regla en código que impide al filtro descartar un elemento crítico
>   que la búsqueda trajo.
>
> Resultado conjunto: aciertos exactos de 24/47 a 29/47, elementos de más
> de 29 a 21, omisiones críticas de 11 a 1, cobertura 63/81 frente a 64/81
>
> (`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:63-74`)

La misma cifra, con la misma lectura ("24/47→29/47, elementos de más
29→21, omisiones críticas 11→1"), se repite en
`docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md:76`. Y
`docs/evolution/STATUS.md:156-166` (decisión D1) es explícito: la evidencia
de `evidence/adr001-spikes` se incorpora "**completa** — el índice de
categoría determinista **y** el filtro de relevancia con modelo local vía
Ollama —", no una de las dos piezas por separado. La propia rama de
laboratorio documenta el mecanismo del filtro
(`experiments/adr002/modelo_local/filtro.py:76-89`, en
`evidence/adr001-spikes`): "búsqueda sola" (sin el filtro) mide **24/47**
con 8/16 aciertos de ausencia; "más el filtro que elige" (el modelo local
vía Ollama decidiendo qué descartar) sube a **29/47**. El salto de 24/47 a
29/47 —el suelo exacto de D1— **es** el efecto del filtro de relevancia,
no del motor de búsqueda.

Este módulo, por diseño y desde su primera versión (ADR-109), mide
explícitamente **sin** esas dos piezas: el docstring del módulo lo declara
desde el principio ("sin índice de categoría (M8) ni filtro de relevancia
(M9/M10)", `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py:11`), y
la incidencia #461, igual que la #457 antes, autoriza portar el motor por
etapas y ahora su petición por caso — **no** el índice de categoría ni el
filtro de relevancia Ollama, que son objeto de encargos propios no abiertos
todavía (`docs/evolution/STATUS.md:202`: "se intentará cerrar dentro del
mismo paquete de incorporación de D1", sin fecha ni incidencia asignada
todavía).

Nuestro 23/47 (con petición por caso, sin índice de categoría ni filtro) es
consistente con esa lectura: queda por debajo incluso del 24/47 de
"búsqueda sola" del laboratorio (arquitecturas de candidato distintas — el
motor portado usa `ADR002-A`, léxico-estructural, mientras que la cifra de
"búsqueda sola" del laboratorio pertenece a un experimento diferente,
`modelo_local/filtro.py`, que no comparte necesariamente el mismo
candidato — de modo que 23 frente a 24 no es una regresión medible sobre
la misma base, sino dos mediciones de "solo búsqueda" con candidatos que no
se han comprobado idénticos). Lo que sí es concluyente, y no depende de esa
comparación fina, es que **ninguna** cifra de "solo búsqueda" en la
documentación de Sirius llega a 29/47: el salto final depende del filtro.

## Criterio de parada (escrito ANTES de decidir)

Antes de medir tras portar la petición por caso: si la cifra de aciertos
exactos quedara por debajo de 29/47 con la petición por caso ya idéntica a
la del laboratorio (no una política uniforme, como en ADR-110), no forzaría
la aserción dura de D1 en la prueba del banco, no debilitaría ninguna
prueba existente para alcanzar verde, y en vez de seguir buscando una
variación adicional de la política de petición (que el propio ADR-110 ya
demostró insuficiente como eje de búsqueda) compararía la composición
exacta del 29/47 documentado contra lo que este módulo mide, citando
fichero y línea de dónde sale la diferencia, y dejaría la decisión al
propietario. Ocurrió exactamente eso: 23/47 con la petición por caso
portada, comparación completa contra la documentación de Producto/Plan de
Pruebas/STATUS, diagnóstico con cita de fichero y línea de que el salto a
29/47 es el filtro de relevancia Ollama (M9/M10) más el índice de categoría
(M8), ninguno de los dos en el alcance de esta incidencia.

## Opciones consideradas

1. **Buscar una variación adicional de la petición por caso (más allá de la
   traducción literal de `cases.py:334-366`) para intentar acercarse a
   29/47** — descartada: la petición por caso ya es la traducción exacta
   del laboratorio; inventar una variante no documentada falsearía la
   comparación "mismo traductor, mismos campos, mismo corpus" que la
   incidencia exige, y ADR-110 ya estableció que ajustar la política de
   petición sin tocar las piezas de M8/M9/M10 no cierra la brecha de
   precisión.
2. **Afirmar el suelo D1 igualmente, redondeando o interpretando alguna
   métrica a favor** — descartada explícitamente por la incidencia ("no
   debilites ni falsees nada") y por `CLAUDE.md` (disciplina de evidencia).
3. **Portar también el índice de categoría (M8) y/o el filtro de
   relevancia Ollama (M9/M10) dentro de esta misma incidencia** —
   descartada: el alcance permitido de la incidencia #461 nombra
   exclusivamente los campos de petición por caso, el traductor de
   `cases.py` y el cableado del arnés; ninguno de los dos menciona el
   índice de categoría ni el filtro de relevancia. Ampliarlo por
   iniciativa propia es justo lo que `CLAUDE.md` prohíbe ("no rediseñes
   Sirius por iniciativa propia") y lo que esta incidencia pide evitar
   mediante `BLOCKED_BY_DECISION`/diagnóstico en vez de decidir por
   cuenta propia.
4. **Detener aquí, dejar la petición por caso portada y en uso en el
   arnés, actualizar las cotas de no regresión a la cifra medida (23/47,
   90, 10, 63/81), documentar el diagnóstico con sus cifras y su
   localización exacta, y no afirmar el suelo D1 en la prueba** —
   elegida. El objetivo aprobado de esta incidencia es portar la petición
   por caso y medir; el resultado (11/47 → 23/47, 186 → 90 elementos de
   más, 60/81 → 63/81 cobertura, con omisiones_criticas 9 → 10) es una
   mejora real y verificable en tres de las cuatro métricas, y el
   diagnóstico deja localizado, con fichero y línea, que la brecha
   restante hasta D1 no es de traducción sino de qué piezas del paquete D1
   mide este módulo.

## Decisión

Opción 4. La petición por caso queda portada y en uso en el arnés del
banco (`_ejecutar_banco_motor_portado`, vía `peticion_desde_caso` de
`tests/acceptance/staged_engine_case_translation.py`); el
camino real del producto no cambia (sigue detrás de `category_matching_
enabled`, como ya fijó ADR-110). Las cotas de no regresión de la prueba
del motor portado se actualizan a la cifra medida en este ADR (23/47, ≤90,
≤10, ≥63/81); el suelo D1 (≥29/47, ≤21, ≤1) **no** queda afirmado como
aserción dura, por la misma razón que ADR-109/ADR-110: afirmarlo dejaría
`uv run pytest` en rojo (la cifra medida es 23/47, no 29/47), y debilitarlo
falsearía la prueba. La cobertura sí alcanza el suelo de D2 (63/81)
exactamente con esta medición, pero D1 exige las cuatro cifras a la vez
(`docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md:146`: "por debajo
de 29/47 — cifra literal medida en la PR #117 para el paquete completo"),
así que no se afirma como aserción dura de forma aislada.

Decisión que falta y que no corresponde a esta incidencia: si el
propietario quiere ordenar, como encargos aparte, portar el índice de
categoría (M8, cuarta señal de `RankedKnowledge`,
`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md` §6.2) y
el filtro de relevancia con modelo local vía Ollama (M9/M10, segundo filtro
en `ContextBuilder._rank_related_knowledge`, §6.3) que D1 exige juntos con
el motor de búsqueda para alcanzar 29/47, o si prefiere una vía distinta.

## Comprobación que la sostiene

- `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`:
  imprime `aciertos_exactos=11/47 elementos_de_mas=186 omisiones_criticas=9
  cobertura=60/81 (74.1%)` para la política uniforme (ADR-110, sin cambios)
  y `aciertos_exactos=23/47 elementos_de_mas=90 omisiones_criticas=10
  cobertura=63/81 (77.8%)` para la petición por caso portada (este ADR).
- Lectura de `experiments/adr002/round/cases.py:334-366` (`_traducir`) en
  `evidence/adr001-spikes`, comparada línea a línea con `peticion_desde_caso`
  de `tests/acceptance/staged_engine_case_translation.py`:
  mismas cuatro traducciones no obvias (permiso, límite, tiempo, objetivos
  de `EXACTA`), mismos campos de entrada (`peticion_p2` del fixture,
  verbatim de `cases_v0_5.json`/`references_v0_5.json`, commit
  `dfdcdaff04dcba10939cc0b0569c55b6a636296f`).
- Tras cerrar el hallazgo de revisión sobre `objetivos` (ver «Diagnóstico»),
  se repitió `uv run pytest
  tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`: misma
  medición, `aciertos_exactos=23/47 elementos_de_mas=90
  omisiones_criticas=10 cobertura=63/81 (77.8%)`, con `git stash` del
  cambio y repetición para confirmar que el resultado no dependía de la
  corrección — no la mueve, así que las cotas de no regresión y la tabla de
  arriba no cambian.
- Lectura de
  `docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:63-74`,
  `docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md:76` y
  `docs/evolution/STATUS.md:156-166`: las tres coinciden en que 29/47 es el
  resultado conjunto del motor de búsqueda **con** el índice de categoría
  **y** el filtro de relevancia Ollama, no del motor de búsqueda aislado.
- Lectura de `experiments/adr002/modelo_local/filtro.py:76-89` en
  `evidence/adr001-spikes`: "búsqueda sola" mide 24/47; "más el filtro que
  elige" (el modelo local vía Ollama) sube a 29/47 — el salto exacto del
  suelo de D1 lo produce el filtro, no el motor.
- `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src
  tests`, `uv run pytest`, `git diff --check`: ver PR para el resultado
  completo.

## Consecuencias

- Positivas: la petición por caso queda portada, citando su origen, con
  módulo propio (`tests/acceptance/staged_engine_case_translation.py`) y
  cableada en el arnés del banco. Tres de las cuatro métricas mejoran de
  forma real y sustancial (11/47→23/47, 186→90 elementos de más, 60/81→
  63/81 cobertura — el suelo de D2 queda alcanzado exactamente), y el
  diagnóstico deja localizado, con fichero y línea, que la brecha restante
  hasta D1 no es un defecto de traducción ni de arnés sino la ausencia
  deliberada (por alcance de esta incidencia y de la #457 anterior) del
  índice de categoría y el filtro de relevancia Ollama que D1 exige juntos
  con el motor.
- Negativas/riesgos: D1 sigue sin poder declararse cumplido (23/47 <
  29/47) y omisiones_criticas empeora en una unidad frente a la política
  uniforme de ADR-110 (9 → 10); PA-0.2-REC-01 sigue sin poder declararse
  superada por esta vía. El trabajo restante (portar el índice de
  categoría y el filtro de relevancia Ollama, cada uno como encargo propio
  con su propia decisión del propietario sobre la dependencia de Ollama ya
  registrada en D1) cae fuera del alcance que esta incidencia autoriza.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba: la opción 1 habría inventado una
variante de petición no documentada, rompiendo la comparación exacta que
la incidencia exige; la opción 2 habría falseado la prueba; la opción 3
habría ampliado el alcance permitido por iniciativa propia.
