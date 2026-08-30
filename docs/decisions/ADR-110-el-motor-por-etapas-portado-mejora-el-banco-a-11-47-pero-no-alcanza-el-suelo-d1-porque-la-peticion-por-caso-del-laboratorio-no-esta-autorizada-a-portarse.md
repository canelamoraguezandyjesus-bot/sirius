# ADR-110 — El motor por etapas portado mejora el banco a 11/47 pero no alcanza el suelo D1 porque la petición por caso del laboratorio no está autorizada a portarse

- Estado: PROPUESTO
- Fecha: 2026-08-30
- Aprobación: fusión de la PR por el propietario — este ADR documenta el
  diagnóstico que la propia incidencia #457 pide si, tras portar todo lo
  nombrado (tratamiento léxico restante, puertas `G1-G12`, agrupación de
  equivalentes, motor por etapas), la cifra sigue por debajo del suelo D1.
  No es una decisión de arquitectura nueva: registra la investigación y deja
  la decisión de cómo cerrar la brecha restante al propietario, tal como el
  objetivo de la incidencia exige explícitamente.

## Contexto y problema

La incidencia #453 (M11) se bloqueó (ADR-108, referenciado desde la
incidencia #455 al no existir ese ADR en el registro) porque el banco de 47
casos medía 1/47 sobre el pipeline de `main`. La incidencia #455/#456 portó
el tratamiento léxico de `experiments/adr002/candidates/adr002_a/lexical.py`
y subió la cifra a 10/47 (ADR-109), pero diagnosticó que la brecha restante
ya no era de cobertura sino de precisión, y que cerrarla exigía, como
mínimo, `G11` (con las validaciones de polaridad/condición completas de
`lexical.py`) y muy probablemente `G4`/`G8`/la agrupación de equivalentes —
el resto del motor por etapas del laboratorio.

La incidencia #453 recibió la decisión del propietario (30-08, transmitida
en su comentario a esa misma incidencia): el suelo de D1 (aciertos exactos
≥ 29/47) **se mantiene**, y el trabajo pendiente sale como encargo propio.
Ese encargo es la incidencia #457, cuyo objetivo autoriza portar, sin
alterarlos, cuatro piezas exactas del laboratorio (`evidence/adr001-spikes`,
PR #117):

1. las funciones de polaridad y condición de `lexical.py` que el porte
   anterior dejó fuera (`polaridad_negativa` con sus cuatro reglas,
   `condicion_declarada`, `marcadores`);
2. las puertas no compensables de
   `experiments/adr002/candidates/common/gates.py` que el diagnóstico
   nombra (`G11`, `G4`, `G8`, y las demás de `G1-G12` que el propio motor
   por etapas exija);
3. la agrupación de equivalentes de
   `experiments/adr002/candidates/common/grouping.py`;
4. el motor por etapas de `experiments/adr002/candidates/common/engine.py`
   que las orquesta.

Sobre los ejes (`ambito`, `sensibilidad`, `property_key`) que el esquema
real de Sirius 0.1 no persiste, la incidencia prohíbe expresamente añadir
migración o columnas: el motor portado los recibe como atributos opcionales
del candidato, el arnés del banco los suministra desde el propio corpus
congelado, y en el camino real del producto viajan como `None` (toda puerta
que los necesita falla abierta), detrás de la misma puerta de activación de
D7 punto 6 (`category_matching_enabled`) que ya gobierna la categoría.

**Las cuatro piezas se portaron íntegras**, citando su origen en cada
módulo:

- `sirius.adapters.persistence.lexical_query_treatment` — ampliado con
  `MARCADORES_NEGACION`, `MARCADORES_CONDICION`, `polaridad_negativa`,
  `condicion_declarada`, `sujeto_estructural`, `ordenar_estable`.
- `sirius.domain.staged_engine_contracts` — el vocabulario común
  (`Peticion`, `Candidata`, `ItemCanonico`, `EjesDeclarados`,
  `PuertoDeRecuperacion`, `SenalesDeCandidato`, ...), desde
  `experiments/adr002/candidates/common/contracts.py`.
- `sirius.domain.staged_engine_gates` — las doce puertas `G1-G12`, desde
  `experiments/adr002/candidates/common/gates.py`.
- `sirius.domain.staged_engine_grouping` — deduplicación por identidad y
  agrupación de equivalentes, desde
  `experiments/adr002/candidates/common/grouping.py`.
- `sirius.domain.staged_engine_stops`/`sirius.domain.staged_engine_trace` —
  los criterios de parada `S1-S7` y la traza minimizada, desde
  `experiments/adr002/candidates/common/stops.py`/
  `experiments/adr002/candidates/common/trace.py` (dependencias directas de
  `engine.py`, no nombradas por separado en el objetivo pero necesarias
  para que el motor funcione).
- `sirius.domain.staged_engine` (`recuperar`) — el motor `E0-E5`, desde
  `experiments/adr002/candidates/common/engine.py`.
- `sirius.adapters.persistence.staged_engine_candidate` — la fuente de
  candidatas léxico-estructurada (`ADR002-A` en el laboratorio), desde
  `experiments/adr002/candidates/adr002_a/candidate.py`.
- `sirius.adapters.persistence.staged_engine_port` — un puerto nuevo
  (`PuertoDeRecuperacion`) sobre el esquema real de Sirius 0.1, adaptado de
  `experiments/adr002/candidates/common/port.py` al estilo de acceso ya
  existente (`sqlalchemy.text` vía `session_scope`); no toca el contrato de
  `KnowledgeSearchRepository`.
- `sirius.application.rank_relevant_knowledge.RankRelevantKnowledgeUseCase`
  — cableado detrás de `category_matching_enabled`: cerrada (el estado por
  defecto de todo caller existente), `rank()` sigue el filtro-y-orden de
  siempre; abierta y con el puerto/candidato configurados, delega en
  `sirius.domain.staged_engine.recuperar`.
- `tests/acceptance/fixtures/evidence_bank_47_casos.json` — enriquecido con
  `ejes_p2` por ítem (polaridad, condición, sensibilidad, ámbito, autoridad,
  marcas de no uso, vigencia, procedencia, `property_key`) y
  `criticidad.fuente_de_politica`/`regla_de_politica`, portados sin
  modificar desde
  `experiments/adr002/benchmark/conformance_corpus_v0_6.json`,
  `experiments/adr002/benchmark/property_keys_v0_2.json` y
  `experiments/adr002/benchmark/applied_criticality_v0_1.json` (mismo
  commit `dfdcdaff04dcba10939cc0b0569c55b6a636296f` de
  `evidence/adr001-spikes` que ya citaba la nota de procedencia del
  fixture) — nunca el campo `criticidad.fuente` crudo del corpus, que la
  propia nota de procedencia ya declaraba que no se porta por contener un
  identificador de caso.

**Resultado medido**,
`uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`:

| métrica | M7 + léxico (ADR-109) | motor por etapas portado (este ADR) | objetivo #457 |
|---|---|---|---|
| aciertos_exactos | 10/47 | **11/47** | ≥ 29/47 |
| elementos_de_mas | 218 | **186** | ≤ 21 |
| omisiones_criticas | 10 | **9** | ≤ 1 |
| cobertura | 57/81 (70.4%) | **60/81 (74.1%)** | ≥ 63/81 |

Mejora real en las cuatro métricas, pero muy por debajo de los cuatro
objetivos. Este ADR es el diagnóstico que el objetivo de la incidencia pide
para ese caso.

## Diagnóstico: dónde vive la brecha restante, con evidencia caso a caso

El arnés del banco (`_ejecutar_banco_motor_portado`,
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`) interroga al motor
con una política **uniforme**: modo M1 (ordinario), ámbito el que cada caso
ya declaraba en el fixture (`caso["ambito"]`, portado por la incidencia
#456 desde `cases_v0_5.json` pero sin consumir hasta ahora), cardinalidad
EXHAUSTIVA (sin cuota — la semántica más fiel a como `rank()` ya se
comporta hoy, sin objetivo de resultados) y un límite que "no ata" (el
tamaño del canon, la misma convención que
`experiments/adr002/round/cases.py:101-103` usa para los casos sin límite
declarado).

Inspección directa de casos concretos (`rec.traza.puertas`,
`rec.traza.pasos`, sobre el arnés con esta política) muestra por qué:

- **`B04-CA-03`** («¿Qué reglas de calidad aplican a Gamma?», ámbito
  `PRJ-GAMMA`, esperado `[]`): `E1` (clave exacta + término léxico) aporta
  15 candidatas; `G4` descarta 7 por ámbito y `G8` 1 por tiempo, pero **12
  siguen pasando** — items del propio proyecto `PRJ-GAMMA` que comparten una
  palabra suelta con la consulta («reglas», «calidad») sin relación real con
  «Gamma».
- **`B04-CA-35`** («¿Qué nota interna hay sobre la prueba?», ámbito
  `PRJ-ALFA`, esperado `[]`): `E1` aporta 42 candidatas; `G4` descarta 29,
  pero **16 quedan** dentro del mismo proyecto.
- **`B04-CA-01`** («¿Cómo prefiero que redactes?», ámbito `GLOBAL`, esperado
  `[MEM-001]`): funciona exactamente — 1 candidata, 1 resultado.

Las puertas que dependen de ejes declarados (`G4`, `G8`, `G9`) **sí
funcionan** cuando el corpus los declara — descartan lo que está fuera de
proyecto o fuera de vigencia — pero no discriminan **dentro** del proyecto
autorizado: `G11` (integridad semántica) exige que la lectura declare
sujeto y medio, no que la polaridad o la condición de la candidata
coincidan con las de la consulta (`staged_engine_gates.aplicar_g11` solo
rechaza una lectura incompleta; comparar contra la consulta no es parte del
contrato que `gates.py` define en el laboratorio, se confirma leyendo
`experiments/adr002/candidates/common/gates.py:262-278` en
`evidence/adr001-spikes`). El ruido dominante que queda dentro de un mismo
proyecto es, con la política uniforme, indistinguible del ruido que ya
tenía `sanitize_fts5_query`: cualquier término compartido entre la consulta
y un ítem cuenta como coincidencia.

**Configuraciones probadas, con sus cifras** (ninguna alcanza los cuatro
objetivos a la vez):

| configuración | aciertos | de más | omisiones críticas | cobertura |
|---|---|---|---|---|
| EXHAUSTIVA (la elegida) | 11/47 | 186 | 9 | 60/81 |
| ACOTADA, límite_objetivo=1 | 18/47 | 67 | **20** | 45/81 |
| ACOTADA, límite_objetivo=3 | 11/47 | 158 | 9 | 56/81 |
| ACOTADA, límite_objetivo=5 | 11/47 | 168 | 9 | 56/81 |
| ACOTADA, límite_objetivo=8 | 11/47 | 185 | 9 | 60/81 |
| EXHAUSTIVA, sin `E2` (solo `E1`) | 19/47 | 56 | **26** | 39/81 |

Ninguna corta el ruido sin perder cobertura crítica: parar antes (cardinalidad
acotada, o desactivar `E2`) reduce elementos de más pero dispara las
omisiones críticas muy por encima del suelo de 1 (hasta 26), porque la
parada temprana no distingue un elemento crítico pendiente de uno ordinario
sin la cardinalidad **semántica** que el propio motor exige declarar por
consulta. Dejar todas las etapas activas (`EXHAUSTIVA`) es la única
configuración probada que no degrada las omisiones críticas por debajo de
lo ya medido con M7, pero por eso mismo tampoco corta el ruido.

**La causa raíz**: el 29/47 que PR #117 midió en el laboratorio no lo
alcanza una política uniforme. Lo alcanza una **petición por caso** —modo,
permiso, cardinalidad y límite, cada uno declarado por consulta— que
`experiments/adr002/round/cases.py:334-366` (`_traducir`) construye a partir
de dos ficheros: `experiments/adr002/benchmark/cases_v0_5.json`
(instanciación: permiso, modo, cardinalidad, límite, tiempo objetivo por
caso) y `experiments/adr002/benchmark/references_v0_5.json` (la adjudicación
que fija el límite duro/objetivo real de cada caso,
`referencia["adjudicacion"]["dominio"]["limite"]`, leído en
`cases.py:349-350`). **Ninguno de esos dos ficheros, ni el traductor que los
combina, está entre lo que el alcance permitido de la incidencia #457
autoriza portar** — el objetivo nombra el tratamiento léxico restante, las
puertas, la agrupación y el motor, no la familia de casos `cases_v0_5.json`/
`references_v0_5.json` ni `experiments/adr002/round/cases.py`. Sin esa
petición por caso, el arnés de esta incidencia solo puede construir una
política uniforme para las 47 consultas, y esa política —se pruebe la
configuración que se pruebe— no reproduce las cifras que una petición
ajustada caso a caso alcanzó.

## Criterio de parada (escrito ANTES de decidir)

Antes de medir tras portar las cuatro piezas nombradas: si la cifra de
aciertos exactos quedara por debajo de 29/47, no forzaría la aserción dura
de D1 en la prueba del banco, no debilitaría ninguna prueba existente para
alcanzar verde, probaría al menos dos configuraciones alternativas de la
política uniforme del arnés (cardinalidad acotada con distintos límites, y
con `E2` desactivada) para no quedarme con la primera cifra medida sin
comprobar si una configuración razonable y no ajustada al oráculo la
alcanzaba, y en vez de seguir iterando seguiría el mismo patrón de ADR-109:
pararía a diagnosticar con evidencia caso a caso qué falta y en qué fichero
exacto vive, dejando la decisión al propietario. Ocurrió exactamente eso:
11/47 con la configuración elegida, seis configuraciones medidas y
publicadas, diagnóstico completo con cita de fichero y línea, arriba.

## Opciones consideradas

1. **Portar también `cases_v0_5.json`/`references_v0_5.json` y el
   traductor `experiments/adr002/round/cases.py` para reproducir la
   petición por caso exacta del laboratorio** — descartada dentro de esta
   incidencia: el alcance permitido ("el cambio en el código que pide el
   objetivo, con sus pruebas, y nada más") nombra cuatro piezas concretas y
   no esos ficheros ni ese traductor; añadirlos sería ampliar el alcance
   por iniciativa propia, exactamente lo que `CLAUDE.md` prohíbe ("no
   rediseñes Sirius por iniciativa propia").
2. **Fabricar una cardinalidad por caso derivada de `len(resultado_
   esperado)`** — descartada: `resultado_esperado` es precisamente lo que
   la prueba adjudica; construir la petición a partir de la respuesta
   correcta falsearía la medición (el motor "sabría" cuántos resultados
   busca antes de buscarlos), y el objetivo de la incidencia exige no
   falsear ni debilitar nada para conseguir verde.
3. **Quedarme con la primera configuración medida (EXHAUSTIVA) sin probar
   alternativas** — descartada por el criterio de parada: antes de fijar el
   diagnóstico, el criterio exige probar al menos dos configuraciones
   razonables no ajustadas al oráculo, y así se hizo (seis configuraciones,
   tabla arriba).
4. **Detener aquí, dejar las cuatro piezas portadas y en uso detrás de la
   puerta D7 punto 6, documentar el diagnóstico con sus cifras y su
   localización exacta, y no tocar el suelo D1 de la prueba** — elegida. El
   objetivo aprobado de esta incidencia es portar las cuatro piezas
   nombradas del laboratorio, no reproducir la familia de casos completa
   del banco original; el resultado medido (10/47 → 11/47, 218 → 186
   elementos de más, 10 → 9 omisiones críticas, 57/81 → 60/81 cobertura) es
   una mejora real y verificable en las cuatro métricas, y el diagnóstico
   deja localizado, con fichero y línea, lo que falta para seguir.

## Decisión

Opción 4. Las cuatro piezas quedan portadas y en uso: el motor se ejecuta
en el arnés del banco (`_ejecutar_banco_motor_portado`) y está cableado en
el camino real del producto detrás de `category_matching_enabled`
(cerrada por defecto: `sirius.composition_root.build_conversation_
dependencies` construye el puerto y el candidato pero nunca abre la
puerta). La prueba del banco de 47 casos sigue reportando las cuatro
métricas del motor portado sin afirmar el suelo D1 como aserción dura —
igual que ya hacía con el pipeline M7 (ADR-109), y por la misma razón:
afirmar 29/47 dejaría `uv run pytest` en rojo (la cifra medida es 11/47), y
debilitar la aserción a 11 falsearía la prueba declarando cumplido un suelo
que D1 fija en 29.

Decisión que falta y que no corresponde a esta incidencia: si el
propietario quiere ordenar, como encargo aparte, portar la familia completa
de casos `cases_v0_5.json`/`references_v0_5.json` y el traductor de
`experiments/adr002/round/cases.py` para reproducir la petición por caso
exacta que el laboratorio usó, o si prefiere una vía distinta (ajustar la
política uniforme con más configuraciones, migrar el suelo D1 a "la cifra
que se mida" como ya hace D2, o cerrar la brecha con otro mecanismo no
explorado aquí).

## Comprobación que la sostiene

- `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`:
  imprime `aciertos_exactos=10/47 elementos_de_mas=218 omisiones_criticas=10
  cobertura=57/81 (70.4%)` para el pipeline M7 (sin cambios, ADR-109) y
  `aciertos_exactos=11/47 elementos_de_mas=186 omisiones_criticas=9
  cobertura=60/81 (74.1%)` para el motor por etapas portado.
- Las seis configuraciones de la tabla de diagnóstico, medidas ejecutando
  `_ejecutar_banco_motor_portado` con `Cardinalidad`/`espacios_autorizados`
  alternativos (script de exploración, no parte de la suite: las cifras
  quedan citadas en este ADR y en el mensaje de la PR).
- Inspección de `rec.traza.puertas`/`rec.traza.pasos` sobre `B04-CA-01`,
  `B04-CA-03`, `B04-CA-35` (arriba), confirmando que `G4`/`G8` descartan
  candidatas fuera de ámbito/tiempo pero que el ruido restante es intra-
  proyecto.
- Lectura de `experiments/adr002/candidates/common/gates.py:262-278`
  (`aplicar_g11`) en `evidence/adr001-spikes`: confirma que `G11` exige
  lectura completa, no coincidencia de polaridad/condición con la consulta.
- Lectura de `experiments/adr002/round/cases.py:334-366` (`_traducir`) y de
  `experiments/adr002/round/cases.py:101-103`
  (`CARDINALIDAD_SIN_DECLARAR`/convención de límite sin atar) en
  `evidence/adr001-spikes`: confirma que la petición por caso del
  laboratorio viene de `cases_v0_5.json`/`references_v0_5.json`, no
  derivable del fixture que esta incidencia (y la #456 anterior) portan.
- `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src
  tests`, `uv run pytest`, `git diff --check`: ver PR para el resultado
  completo; ninguna prueba de este módulo queda en rojo porque ninguna
  afirma el suelo D1 que no se alcanza.

## Consecuencias

- Positivas: las cuatro piezas nombradas por la incidencia #457 quedan
  portadas, citando su origen, con pruebas propias
  (`tests/unit/test_staged_engine.py`, `tests/unit/test_staged_engine_
  port.py`, `tests/unit/test_lexical_query_treatment.py` ampliado) y
  cableadas de extremo a extremo detrás de la puerta D7 punto 6 —
  demostrado en ambos estados (`tests/integration/
  test_rank_relevant_knowledge.py`: cerrada, resultado idéntico al de
  siempre; abierta, usa el motor). Las cuatro métricas del banco mejoran
  de forma real y verificable, y el diagnóstico deja localizado, con
  fichero y línea, el trabajo exacto que falta para seguir cerrando la
  brecha.
- Negativas/riesgos: D1 sigue sin poder declararse cumplido (11/47 <
  29/47), así que PA-0.2-REC-01 sigue sin poder declararse superada por
  esta vía; el trabajo restante (portar la familia completa de casos del
  laboratorio y su traductor, o una decisión distinta del propietario) cae
  fuera del alcance que esta incidencia autoriza.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba: la opción 1 habría ampliado el alcance
permitido por iniciativa propia; la opción 2 habría fabricado una petición
a partir de la respuesta correcta, falseando la medición; la opción 3
habría incumplido el criterio de parada al no probar alternativas antes de
fijar el diagnóstico.
