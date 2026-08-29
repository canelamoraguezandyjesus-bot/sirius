# ADR-104 — Portar el banco de 47 casos de evidence/adr001-spikes al modelo real de Sirius

- Estado: PROPUESTO
- Fecha: 2026-08-29
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

## Contexto y problema

M7 (Arquitectura Técnica 0.2 §6.5 y §8-M7, encargo de la incidencia #441) pide
portar «el corpus de 47 casos y sus resultados esperados, sin modificarlos»
desde `evidence/adr001-spikes` (PR #117) a
`tests/acceptance/fixtures/evidence_bank_47_casos.json`, y ejecutar ese banco
contra el pipeline de recuperación real de `main`
(`RankRelevantKnowledgeUseCase.rank()` + la exclusión por precedencia que
`ContextBuilder` ya aplica), sin índice de categoría ni filtro de relevancia
todavía (eso es M8-M10), y sin exigir los suelos de D1/D2 (eso es M11).

El problema es que «el banco de 47 casos» no es un fichero único en
`evidence/adr001-spikes`: esa rama contiene toda la familia experimental
ADR-002 (motor común, candidatos A-D, corpus de conformidad versionado varias
veces). Además, el modelo de datos de esa familia (`Peticion`, `Ambito`,
`Cardinalidad`, confirmación/validez/disponibilidad, criticidad con
`fuente`/`razon`) no es el modelo real de `Memory`/`Decision` de Sirius (sin
ventana temporal, sin estados de confirmación, sin campo de categoría ni de
criticidad — eso lo añade M8). Portar el banco exige, por tanto, dos
decisiones separadas: (1) qué ficheros exactos de la rama de evidencia son
«el banco de 47 casos y sus resultados esperados», y (2) cómo traducir cada
item del canon a un `Memory`/`Decision` real sin inventar datos que la rama
de evidencia no declaró.

## Criterio de parada (escrito ANTES de decidir)

Si los ficheros de `evidence/adr001-spikes` no permitían reconstruir
exactamente 47 casos con exactamente 81 elementos esperados en total (las dos
cifras que tanto la Arquitectura Técnica como
`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` §2.2 citan de forma
literal), la conclusión correcta era `BLOCKED_BY_DECISION` — pedir al
propietario que señalara el fichero exacto — en vez de forzar una cifra
distinta o inventar una regla de filtrado ad hoc para cuadrar el total.
Igualmente, si algún item referenciado por un `resultado_esperado` no existiera
en el corpus del canon, la conclusión era la misma parada, no rellenar el
hueco con un dato inventado.

## Opciones consideradas

1. Portar `experiments/adr002/round/cases.py` + su motor común (`Peticion`,
   `engine.recuperar`, etc.) tal cual, y adaptar `RankRelevantKnowledgeUseCase`
   para aceptar ese contrato. Descartada: exigiría tocar código de producto
   (`src/sirius/application/rank_relevant_knowledge.py`) para aceptar un
   contrato que no es el suyo, y el encargo prohíbe explícitamente tocar
   producto en M7 («banco portado + prueba de medición»).
2. Tomar `experiments/adr002/benchmark/cases_v0_5.json` como única fuente de
   `resultado_esperado` (su bloque `adjudicacion`). Descartada tras medir: da
   47 casos pero 85 elementos esperados, no 81 (difiere en los 4 casos cuyo
   `resultado_esperado` nombra un `DOC-`/`MSG-` en vez de un `MEM-`/`DEC-`, y
   en los 2 casos multi-rama donde el nivel plano no coincide con lo que el
   propio arnés de la rama de evidencia ejecutó).
3. **(Elegida)** Reconstruir `resultado_esperado` exactamente como
   `experiments/adr002/round/cases.py:_traducir` lo calcula: consulta y ámbito
   desde `cases_v0_5.json` (bloque `instanciacion`), `resultado_esperado`
   desde la adjudicación ya calculada en `references_v0_5.json`, filtrado a
   identidades del canon (`MEM-`/`DEC-`) exactamente como
   `experiments/adr002/projection/contracts.py:referencia_canonica` filtra
   (`DOC-`/`MSG-` no son elementos del canon). Verificado contra
   `artifacts/adr002_round/ronda_primaria_v0.4_evidencia.json` (una ejecución
   ya publicada de ese mismo arnés sobre este mismo corpus): sus 47
   `veredictos` adjudicables suman exactamente 81 elementos esperados,
   coincidiendo caso a caso con el cálculo anterior.

## Decisión

Portar el banco reconstruyendo, sin modificar ningún valor, los 47 casos
adjudicables de nivel 1 (excluidos `B04-CA-37/39/48`, no adjudicables por el
propio canon — RED-032/RED-033 sin congelar) a partir de cuatro artefactos de
`evidence/adr001-spikes` (commit `dfdcdaff04dcba10939cc0b0569c55b6a636296f`):
`cases_v0_5.json` (consulta, ámbito), `references_v0_5.json` (adjudicación
calculada → `resultado_esperado`, filtrado a identidades del canon),
`conformance_corpus_v0_6.json` (los 97 items del canon: id, tipo, proyecto,
texto, y los tres estados `confirmacion`/`validez`/`disponibilidad`) y
`applied_criticality_v0_1.json` (la proyección ya seleccionada de
`criticidad.nivel`/`razon_segura` — un plano que la propia rama de evidencia
deriva del canon precisamente para no cruzar `criticidad.fuente`, que porta un
identificador de caso).

Traducción de cada item del canon a un `Memory`/`Decision` real (código en
`_load_canon_item`, `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`):

- «Vigente» (debe quedar CURRENT/APPROVED y ser buscable) si y solo si
  `confirmacion == CONFIRMADA and validez == VIGENTE and disponibilidad ==
  DISPONIBLE` — los tres estados explícitos del canon, sin mirar
  `criticidad`. 9 de los 97 items no cumplen las tres a la vez y se cargan
  como ARCHIVED (memorias) o se dejan PROPOSED sin aprobar (decisiones), que
  es exactamente lo que hoy excluye a un candidato de `list_current_*`.
- `PRJ-GLOBAL` se traduce como `project_id=None` (Memory lo admite; ninguna
  decisión del canon usa ese proyecto). Los demás seis proyectos del canon
  (`PRJ-ALFA/BETA/GAMMA/DELTA/MADEIRA/CANARIAS`) más `LISTA-CERRADA-AB` se
  crean como `Project` reales — siete filas — sin que el proyecto activo
  final importe: `rank_relevant_knowledge` nunca filtra por proyecto activo,
  solo lo usa como criterio de desempate en el orden, y ninguna de las cuatro
  métricas mira el orden.
- El `subject` de una `Decision` (obligatorio, y el único mecanismo de
  `main` que no existe en el canon de la rama de evidencia) se rellena con
  su propio `text`: no hay ningún campo de «asunto» distinto en el canon
  portado, e inventar uno introduciría un dato que la rama de evidencia no
  declaró. Efecto aceptado: puede producir coincidencias de asunto que el
  banco original no modelaba — ver Consecuencias.
- Dos memorias (`disponibilidad` `PURGADA`/`NO_GUARDADA`) llevan `text: ""`
  en el propio canon — nunca llegaron a existir como contenido real — y no
  se crean en absoluto (`SaveManualMemoryUseCase` rechaza contenido vacío
  igual que rechazaría cualquier guardado en blanco real). Ninguna de las
  dos aparece en ningún `resultado_esperado`; comprobado antes de tomar la
  decisión (`referenced ∩ {MEM-009, MEM-019} == ∅`).

`criticidad.nivel`/`razon_segura` viajan en el fixture (para el arnés de
evaluación de la métrica de omisiones críticas) pero el cargador que
construye los `Memory`/`Decision` reales nunca lee `criticidad` en absoluto;
`criticidad.fuente` (que porta un identificador de caso, p. ej. `B04-CA-01`)
no se porta en absoluto, ni siquiera al fixture.

## Comprobación que la sostiene

- `python3` sobre los cuatro artefactos descargados de
  `origin/evidence/adr001-spikes` confirma: 47 casos adjudicables, 81
  elementos esperados en total tras filtrar a identidades del canon (85 sin
  filtrar — los 4 elementos de diferencia son `DOC-005`/`MSG-011`/`MSG-010`/
  `MSG-020`, no items del canon), coincidiendo exactamente con los 47
  `veredictos` adjudicables de `ronda_primaria_v0.4_evidencia.json`
  (`ADR002-A`, cuya cifra de `esperado` es idéntica entre participantes por
  ser el oráculo, no el candidato).
- 19 de los 97 items del canon llevan `criticidad` no nula en
  `conformance_corpus_v0_6.json`; sus 19 valores de `criticidad.razon`
  coinciden carácter a carácter con `criticidad.razon_segura` en
  `applied_criticality_v0_1.json` (comprobado con un bucle que compara los
  19 pares) — confirma que ese plano no reescribe el texto, solo excluye
  `fuente`.
- `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py` en verde:
  `test_el_fichero_de_forma_tiene_47_casos_y_81_elementos_esperados`,
  `test_el_banco_se_ejecuta_contra_el_pipeline_actual_y_reporta_las_cuatro_metricas`
  (línea base medida: 1/47 aciertos exactos, 2141 elementos de más, 21
  omisiones críticas, 51/81 cobertura — coherente con que la búsqueda de hoy
  hace `OR` de cualquier término compartido, sin categoría ni filtro; ver
  `sirius/adapters/persistence/sqlite_knowledge_search_repository.py:sanitize_fts5_query`)
  y `test_el_cargador_no_lee_criticidad` (demuestra por construcción, con un
  espía que registra qué claves se piden, que el cargador nunca toca
  `criticidad` y que el arnés solo pide `criticidad.nivel`, nunca
  `criticidad.razon_segura`).
- `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src
  tests` y `uv run pytest` (4125 passed, 9 skipped) en verde sobre el árbol
  completo tras el cambio.

## Consecuencias

- La línea base medida es deliberadamente ruidosa (2141 elementos de más):
  es la medición honesta del `MATCH` `OR`-de-cualquier-término de hoy sobre
  frases naturales en español, no un defecto de esta prueba. M11 la
  reemplaza por la del pipeline con categoría y filtro ya integrados.
- `subject = text` en las decisiones puede introducir coincidencias de
  asunto (S7.5) que el banco original, pensado para un motor sin ese
  mecanismo, no anticipaba, empujando la cifra de «elementos de más» al
  alza. Aceptado porque M7 mide, no exige suelos; revisar si M9/M10 hacen
  que esta elección deje de ser neutral.
- Las siete filas de `Project` reales y el proyecto activo final no importan
  hoy (el ámbito no filtra en `rank()`), pero si un M8-M10 futuro empieza a
  filtrar por proyecto activo, esta fixture necesitará decidir, caso a caso,
  qué proyecto está activo — no lo intenta hoy.

## Alternativas descartadas y por qué

Ver «Opciones consideradas»: portar el motor común de la rama de evidencia
tal cual (tocaría producto, prohibido en M7) y tomar `cases_v0_5.json` como
única fuente sin cruzar `references_v0_5.json` (no reproduce 81, la cifra que
tanto la Arquitectura Técnica como el Producto citan).
