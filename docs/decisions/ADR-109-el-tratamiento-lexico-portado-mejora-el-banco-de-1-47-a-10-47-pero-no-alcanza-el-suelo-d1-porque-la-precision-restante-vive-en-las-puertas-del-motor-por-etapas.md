# ADR-109 — El tratamiento léxico portado mejora el banco de 1/47 a 10/47, pero no alcanza el suelo D1 porque la precisión restante vive en las puertas del motor por etapas

- Estado: PROPUESTO
- Fecha: 2026-08-30
- Aprobación: fusión de la PR por el propietario — este ADR documenta el
  diagnóstico que la propia incidencia #455 pide si, tras portar el
  tratamiento léxico, la cifra sigue por debajo del suelo D1. No es una
  decisión de arquitectura nueva: registra la investigación y deja la
  decisión de cómo cerrar la brecha restante al propietario, como el
  objetivo de la incidencia exige explícitamente.

## Contexto y problema

La incidencia #455 pide portar el tratamiento léxico de
`experiments/adr002/candidates/adr002_a/lexical.py` (rama
`evidence/adr001-spikes`, PR #117) — `VACIAS`, `plegar`, `tokenizar`, `raiz`
con `RAIZ_MINIMA=4`, `variantes` — a `sanitize_fts5_query`
(`src/sirius/adapters/persistence/sqlite_knowledge_search_repository.py`),
para cerrar el hallazgo bloqueante de ADR-108: `sanitize_fts5_query` unía
todos los tokens de la consulta con `OR`, incluidas las palabras vacías del
castellano, y casi cualquier consulta emparejaba con la mayoría del canon
(1/47 aciertos exactos, ~45 elementos de más por caso). El criterio de
aceptación es re-ejecutar `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`
y publicar las cuatro métricas; el suelo de D1 es aciertos exactos ≥ 29/47.

**El tratamiento se portó íntegro** en
`src/sirius/adapters/persistence/lexical_query_treatment.py` (mismo
algoritmo que el laboratorio, sin alterarlo) y `sanitize_fts5_query` ahora
limpia la consulta de `VACIAS` y la empareja por las variantes morfológicas
de cada término significativo — el mismo mecanismo, literal, que
`PuertoSqlite.por_termino_lexico` del laboratorio usa contra el mismo
`knowledge_fts` (`experiments/adr002/candidates/common/port.py:187-208`):
cada variante se cita como literal de FTS5 y se combinan con `OR`.

**Resultado medido**, `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`:

| métrica | antes (ADR-108) | después de este porte |
|---|---|---|
| aciertos_exactos | 1/47 | **10/47** |
| elementos_de_mas | 2141 | **218** |
| omisiones_criticas | 21 | 10 |
| cobertura | 51/81 (63.0%) | **57/81 (70.4%)** |

Mejora real y sustancial en las cuatro métricas — la causa raíz de ADR-108
era exactamente la que se diagnosticó, y cerrarla a nivel léxico cierra buena
parte de la brecha. **Pero 10/47 sigue por debajo del suelo D1 (≥ 29/47)**,
así que este ADR es el diagnóstico que el objetivo de la incidencia pide para
ese caso: "diagnostica QUÉ etapa del laboratorio falta todavía... nómbrala
con su fichero exacto".

## Diagnóstico: dónde vive la brecha restante, con evidencia caso a caso

Un desglose caso a caso del banco tras el porte (`obtenido` vs
`resultado_esperado` por `caso`, reproducible ejecutando `rank()` puro sobre
el pipeline de M7 para cada una de las 47 consultas) muestra que **la
cobertura ya es alta**: de los 37 casos que no logran acierto exacto, **27
encuentran el 100% de lo esperado** (`faltan=set()`) y fallan **solo** porque
`obtenido` contiene elementos de más. Solo 10 casos tienen algún elemento
esperado realmente ausente (`B04-CA-02`, `05`, `22`, `23`, `29`, `30`, `31`,
`32`, `33`, `34`). Ejemplos de los 27 casos de pura precisión:

- `B04-CA-03` («¿Qué reglas de calidad aplican a Gamma?», esperado `[]`):
  encuentra los 0 esperados, pero devuelve 15 elementos de más.
- `B04-CA-35` («¿Qué nota interna hay sobre la prueba?»): encuentra lo
  esperado, pero devuelve 43 elementos de más — el peor caso individual.
- `B04-CA-31` («Dame todas las restricciones esenciales que debo respetar.»):
  faltan 5 esperados y sobran 12 — el peor caso combinado.

`aciertos_exactos` exige igualdad de conjuntos exacta: un solo elemento de
más invalida un caso por lo demás perfecto. **La causa de que la mayoría de
los 37 casos fallidos no cierre no es falta de recuperación** (recall ya
`57/81`, `70.4%`): es que `sanitize_fts5_query`, incluso limpio de vacías y
con variantes, sigue siendo "cualquier término de la consulta cuenta como
acierto" (`OR` de FTS5), sin ningún mecanismo que descarte lo recuperado por
no encajar semánticamente con la consulta.

**Ese mecanismo de descarte existe en el laboratorio, pero no en
`lexical.py`.** Vive en tres piezas del motor por etapas, ninguna de ellas
el módulo que esta incidencia autoriza portar:

1. **Las doce puertas `G1-G12`** (`experiments/adr002/candidates/common/gates.py:41-56`),
   "no compensables": cada candidata debe pasar las diez primeras antes de
   exponerse, `G11` ("integridad semántica: negaciones, condiciones y
   relaciones no se pierden") antes de ordenar, y `G12` (criticidad y
   límite) antes de entregar. `G11` es exactamente donde
   `lexical.polaridad_negativa`/`lexical.condicion_declarada` — las dos
   funciones de `lexical.py` que **no** se portan en esta incidencia, por no
   ser necesarias para limpiar la consulta de vacías — se consultan para
   **rechazar** una candidata cuya polaridad o condición no encaja con la
   consulta, y es precisamente el paso que le falta a `sanitize_fts5_query`:
   sin él, un candidato negado o condicionado se recupera igual que uno
   afirmado sin condición, y cuenta como elemento de más.
2. **`G4` (ámbito) y `G8` (tiempo)** (`gates.py:47-54`), que exigen que un
   candidato coincida en ámbito (global/proyecto/lista cerrada) y en
   aplicabilidad temporal — ejes que el esquema real de Sirius 0.1 no
   persiste hoy para memorias/decisiones (no hay columna `ambito` ni
   `valid_from`/`valid_to`; el laboratorio los lee de un plano lateral,
   `ejes_p2`, que es dato sintético del corpus, no del canon real).
3. **La agrupación de equivalentes** (`experiments/adr002/candidates/common/grouping.py:33-56`):
   colapsa candidatas con identificador distinto pero sujeto, propiedad,
   clase, ámbito, polaridad, condición, tiempo, vigencia y disponibilidad
   *todos* coincidentes en un único grupo con un representante — de modo que
   dos formas de la misma información nunca cuentan dos veces como elemento
   de más. Sirius 0.1 no tiene noción de `property_key` ni de agrupación por
   equivalencia: cada `Memory`/`Decision` que hace `fts_match` cuenta por
   separado.

Las tres dependen de ejes (`ambito`, `sensibilidad`, `property_key`,
`polaridad`/`condición` por candidata, confirmación granular) que el esquema
canónico real de Sirius 0.1 no materializa hoy, y de un motor (`E0-E5`,
`experiments/adr002/candidates/common/engine.py`) que reemplaza por completo
la política actual de `sirius.domain.relevance.rank_relevant_knowledge`
("cualquier acierto FTS5 es relevante, ordenado por cuatro señales
estructurales") por una muy distinta ("recuperación dirigida por etapas,
filtrada por doce puertas no compensables, agrupada por equivalencia, con
parada explícita"). Cerrar la brecha de 10/47 a 29/47 exige, como mínimo,
portar `G11` (que a su vez exige portar las validaciones de polaridad y
condición completas de `lexical.py`, no solo las que esta incidencia porta)
y, muy probablemente, `G4`/`G8`/la agrupación — es decir, extender el
esquema canónico con los ejes que hoy solo existen en el corpus de
laboratorio y sustituir la política de relevancia de B6b. Eso es un
rediseño de B6a/B6b con decisiones de arquitectura y de esquema propias, no
"la pieza del tratamiento léxico de consultas" que autoriza el alcance de
esta incidencia.

## Criterio de parada (escrito ANTES de decidir)

Antes de medir tras portar `lexical_query_treatment`: si la cifra de
aciertos exactos quedara por debajo de 29/47, no forzaría la aserción dura
de D1 en la prueba del banco, no debilitaría ninguna prueba existente para
alcanzar verde, y en vez de seguir iterando sobre `sanitize_fts5_query`
dentro de esta incidencia, pararía a diagnosticar con evidencia caso a caso
qué mecanismo del laboratorio falta y en qué fichero exacto vive, dejando
esa decisión al propietario. Ocurrió: 10/47 medido, diagnóstico completo
arriba, publicado en este ADR, en la PR y en la incidencia.

## Opciones consideradas

1. **Seguir ampliando el tratamiento léxico** (más sufijos, listas de
   sinónimos, umbrales de similitud) hasta alcanzar 29/47 por fuerza bruta
   — descartada: el desglose caso a caso muestra que el problema dominante
   ya no es léxico (recall 70.4%, la mayoría de fallos son solo precisión);
   seguir tocando `lexical_query_treatment` sin las puertas de descarte
   semántico produciría, como mucho, ajustes marginales sobre el mismo
   mecanismo de "cualquier término cuenta", no una solución.
2. **Portar las puertas `G1-G12` y la agrupación de equivalentes dentro de
   esta misma incidencia** — descartada: exige extender el esquema
   canónico de `Memory`/`Decision` con ejes que Sirius 0.1 no persiste
   (`ambito`, `sensibilidad`, `property_key`, polaridad/condición por
   ítem) y sustituir la política de `rank_relevant_knowledge` por un motor
   por etapas distinto — una decisión de arquitectura y de esquema que el
   alcance permitido de esta incidencia ("el cambio en el código que pide
   el objetivo, con sus pruebas, y nada más"; "no rediseñes Sirius por
   iniciativa propia") no autoriza.
3. **Fabricar un filtro ad hoc que descarte selectivamente los elementos de
   más de cada caso hasta llegar a 29/47** — descartada por la misma razón
   que ADR-108 la descartó: codificar el resultado esperado dentro del
   filtro no mide nada real y falsea la evidencia.
4. **Detener aquí, dejar el porte del tratamiento léxico completo y medido,
   documentar el diagnóstico con su localización exacta, y no tocar el
   suelo D1 de la prueba** — elegida. El objetivo aprobado de esta
   incidencia es portar `lexical.py`, no rediseñar B6a/B6b; el resultado
   medido (1/47 → 10/47, 2141 → 218 elementos de más) es una mejora real y
   verificable, y el diagnóstico deja localizado, con fichero exacto, lo
   que falta para seguir.

## Decisión

Opción 4. El tratamiento léxico se deja portado y en uso en
`sanitize_fts5_query`, con las pruebas que fijan su comportamiento (ver PR).
La prueba del banco de 47 casos sigue reportando las cuatro métricas sin
afirmar el suelo D1 como aserción dura — igual que ya hacía antes de esta
incidencia, y por la misma razón: afirmar 29/47 dejaría `uv run pytest` en
rojo (la cifra medida es 10/47), y debilitar la aserción a 10 falsearía la
prueba declarando cumplido un suelo que D1 fija en 29, no en "lo que se
mida" (a diferencia de D2). Decisión que falta y que no corresponde a esta
incidencia: si el propietario quiere ordenar, como encargo aparte, portar
`G11` (con las validaciones de polaridad/condición completas de
`lexical.py`) y evaluar si eso solo basta, o si además hace falta `G4`/`G8`/
la agrupación de equivalentes y la ampliación de esquema que exigen.

## Comprobación que la sostiene

- `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`
  antes del porte (revirtiendo `sqlite_knowledge_search_repository.py` y
  `lexical_query_treatment.py`, que no existía): imprime
  `aciertos_exactos=1/47 elementos_de_mas=2141 omisiones_criticas=21
  cobertura=51/81 (63.0%)` — idéntico a la cifra que ADR-108 ya registró.
- La misma orden con el porte aplicado: imprime `aciertos_exactos=10/47
  elementos_de_mas=218 omisiones_criticas=10 cobertura=57/81 (70.4%)`.
- Desglose caso a caso (`rank()` puro, sin filtro de relevancia ni
  precedencia, sobre las 47 consultas sin `resultado_esperado`): confirma
  27 de los 37 casos fallidos con `faltan=set()` (cobertura completa,
  fallan solo por elementos de más) y 10 casos con algún elemento esperado
  ausente; los ejemplos citados arriba (`B04-CA-03`, `B04-CA-35`,
  `B04-CA-31`) son reproducibles con ese mismo desglose.
- Lectura de `experiments/adr002/candidates/common/gates.py:41-63` (tabla
  `PUERTAS`, `G1`-`G12`) y de `experiments/adr002/candidates/common/grouping.py:1-56`
  (mecanismo A/B de deduplicación y agrupación) en `evidence/adr001-spikes`:
  confirma que la política de descarte/agrupación que falta vive ahí, no en
  `lexical.py`, y que depende de ejes (`ambito`, `property_key`,
  `sensibilidad`) que `PuertoSqlite` (`experiments/adr002/candidates/common/port.py:169-193`)
  lee de un plano lateral (`ejes_p2`) ajeno al esquema canónico real de
  Sirius 0.1.
- `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src
  tests`, `uv run pytest`, `git diff --check`: ver PR para el resultado
  completo; ninguna prueba de este módulo queda en rojo porque ninguna
  afirma el suelo D1 que no se alcanza.

## Consecuencias

- Positivas: `sanitize_fts5_query` ya no empareja con palabras vacías del
  castellano — una propiedad estructural correcta en sí misma,
  independiente de si cierra D1 — y las cuatro métricas del banco mejoran
  de forma sustancial y verificable. El diagnóstico deja localizado, con
  fichero y línea, el trabajo que falta para quien continúe.
- Negativas/riesgos: D1 sigue sin poder declararse cumplido (10/47 < 29/47),
  así que PA-0.2-REC-01 sigue sin poder declararse superada por esta vía; el
  trabajo restante (`G11` como mínimo, posiblemente `G4`/`G8`/agrupación) es
  significativamente mayor que el tratamiento léxico y exige ampliar el
  esquema canónico, una decisión de arquitectura que le corresponde al
  propietario, no a esta incidencia.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba: las opciones 1-3 se descartaron porque
cada una, por una vía distinta, o no habría cerrado la brecha real (opción
1, que ataca un problema ya resuelto en su mayor parte) o habría tomado una
decisión de arquitectura/esquema fuera del alcance de esta incidencia
(opción 2) o habría falseado la evidencia (opción 3).
