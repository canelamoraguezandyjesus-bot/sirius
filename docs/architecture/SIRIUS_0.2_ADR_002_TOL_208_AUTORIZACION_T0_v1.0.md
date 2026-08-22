# SIRIUS 0.2 — ADR-002 · Autorización de ejecución de T0 · pasos 2 y 3 de TOL-208

**Versión:** 1.0
**Estado:** **APROBADO** — autorización expresa e independiente de ejecución
**Fecha:** 31 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Autoridad:** Usuario / Proyecto Sirius
**Autorización literal del usuario:** **«Apruebo y autorizo»**
**Puerta que trabaja:** `ADR002-TOL-208`, pasos 2 y 3 — **esta acta NO la aprueba ni la satisface**
**Acto sucesor que la precede:** `SIRIUS_0.2_ADR_002_TOL_210_ACTO_SUCESOR_01_EXENCION_T0_v1.0.md` (commit `c881fce697009d294121c5b99d23ba6af5b8b173`)
**Ficha que ampara la ejecución:** `artifacts/adr002_cards/ficha_T0-control_v1.json` · huella `d47a767e61b30729e15f48c9924413f6fddc9429` · commit de entrada `95d00a1` (observado por el verificador)
**No autoriza:** aprobar `ADR002-TOL-208`, fijar límites nuevos, sustituir la línea base histórica, implementar o ejecutar candidatos, iniciar el benchmark, modificar Sirius 0.1 ni fusionar el PR #117.

---

## 0. Objeto

El paquete 10 dejó los pasos 2 y 3 de `ADR002-TOL-208` **preinscritos y
bloqueados** por dos guardas: la ausencia de esta acta y la ausencia de ficha
congelada de `T0-control`. La segunda quedó resuelta por el acto sucesor 01 y
el commit `95d00a1`. Esta acta resuelve la primera.

El usuario ha dicho, literalmente: **«Apruebo y autorizo»**, con este alcance:

1. Se aprueba la **opción (a)** sobre la ficha del control —materializada por
   el acto sucesor 01, que esta acta cita y no repite—.
2. **Se autoriza expresamente ejecutar T0 sobre el corpus congelado v0.4 y
   realizar la rederivación prevista en los pasos 2 y 3 de `ADR002-TOL-208`**,
   exactamente según el plan preinscrito del paquete 10.

Esta acta es el **documento del repositorio** cuya existencia la guarda de
`rederivation_protocol.fallos_de_autorizacion` comprueba. No es una bandera de
línea de órdenes: sin este fichero, el recorrido se bloquea; con él, la
ejecución queda autorizada **una sola vez y con el alcance exacto del §1**.

## 1. Alcance exacto de la autorización

| Concepto | Valor autorizado — ningún otro |
|---|---|
| Candidato | `T0-control` · head de Alembic `61be4bb269bf` · papel `CONTROL_DE_FALSACION` |
| Corpus | v0.4 congelado, citado por blob: `performance_corpus_v0_2.json` → `4e9e2746e49b158a43eda7826b47c78c41b36e90` · `conformance_corpus_v0_4.json` → `c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48` |
| Escenarios | `cero_resultados` · `un_resultado_exacto` · `muchos_candidatos` |
| Capas | `solo_indice_fts5` · `recuperacion_completa_rank` |
| Magnitudes | **6** — escenario × capa |
| Sesiones | **exactamente 11**, procesos independientes |
| Repeticiones por magnitud | **100** |
| Percentiles | nearest-rank, nunca interpolados |
| Protocolo | `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md` |
| Veredictos | delegados al perfil aprobado por el acta de TOL-209 (`SM = 17405 ns`, `U50 = 2685 ns`, `B50(U50) = 537 ns`) |
| Salida | `artifacts/adr002_tolerances/rederivacion_t0_v0.1.json` + muestras crudas + informe |
| Corrida inválida | **una única repetición** (§6.8 del protocolo); si reincide, **`NO_EVALUABLE`** (§6.9), sin artefacto y sin cifras |

**Prohibido cambiar tras observar cualquier resultado:** el esquema
`schema_rederivation_v0_1`, el protocolo, las magnitudes, las repeticiones,
las tolerancias, el criterio de veredicto, la ficha congelada y el corpus.
La regla 1 del §9 del Registro rige entera: ningún valor se fija después de
observar el resultado.

## 2. El arnés autorizado

La ejecución usa **exclusivamente** el arnés preinscrito en el mismo commit
que esta acta:

| Artefacto | Papel |
|---|---|
| `experiments/adr002/rederivation/execute_rederivation.py` | corrida real: precondiciones → base de referencia → once sesiones → controles → validación → escritura atómica |
| `experiments/adr002/rederivation/frozen_corpus.py` | materialización determinista del corpus congelado en el esquema de T0 y derivación cerrada de las consultas de control |
| `experiments/adr002/rederivation/rederivation_protocol.py` | **sin cambios** — guardas, plan y controles del paquete 10 |
| `experiments/adr002/rederivation/schema_rederivation_v0_1.py` | **sin cambios** — el esquema congelado antes de que exista la medición |
| `experiments/adr002/tolerances/floor_scale_probes.py::medir_ns` | **sin cambios** — el cronómetro congelado de los paquetes 06 y 07 |

Reglas del arnés, comprobadas por sus pruebas:

1. **La guarda no se relaja.** `execute_rederivation --execute` recomprueba
   las cinco precondiciones del paquete 10 y añade las suyas: árbol limpio,
   ficha con commit de entrada **ancestro estricto** de `HEAD`, perfil
   aprobado y su fuente intactos por blob, salidas inexistentes.
2. **Las consultas no se eligen: se derivan.** Regla cerrada sobre el corpus
   congelado, verificada funcionalmente contra el índice FTS5 real antes de
   cronometrar nada. Una discrepancia bloquea.
3. **La línea base histórica no se abre siquiera.** Su intangibilidad byte a
   byte es precondición y control final.
4. **El artefacto se valida con el esquema congelado antes de escribirse**, se
   escribe de forma atómica sin sobrescribir, y se relee y revalida.

## 3. Custodia del tránsito de estado

Ejecutar los pasos 2 y 3 cambia el estado observable del repositorio: aparece
la ficha congelada de T0 (commit `95d00a1`), aparece esta acta y —tras la
ejecución— aparecerá el artefacto de rederivación. Seis pruebas de estado de
los paquetes 09 y 10 afirmaban el estado anterior («no hay fichas», «el acta
no existe», «el recorrido se bloquea», «el artefacto no existe») y
**evolucionan en el mismo commit que esta acta** para afirmar el estado nuevo
con la misma severidad fail-closed, conforme al §8.5 del acta de TOL-210:

| Prueba | Antes afirmaba | Ahora afirma |
|---|---|---|
| `test_adr002_cards.py::test_el_repositorio_no_tiene_todavia_ninguna_ficha` | cero fichas | exactamente la ficha congelada de `T0-control` v1, conforme y con su huella |
| `test_adr002_cards.py::test_el_fixture_no_es_la_ficha_de_ningun_candidato_real` | carpeta vacía | ninguna ficha real coincide con la sintética de las pruebas |
| `test_adr002_rederivation.py::test_hoy_la_rederivacion_esta_bloqueada_por_falta_de_autorizacion` | el acta no existe y la guarda bloquea | la guarda bloquea **exactamente cuando** el acta falta, comprobado con un entorno sin acta, y no bloquea con ella presente |
| `test_adr002_rederivation.py::test_las_precondiciones_no_cortocircuitan` | ambos bloqueos visibles a la vez sobre el repositorio | la misma garantía, sobre un entorno sin acta y sin ficha: la propiedad de no cortocircuitar no depende del estado del repositorio |
| `test_adr002_rederivation.py::test_el_recorrido_real_bloquea_y_no_escribe` | `--check` bloqueado | `--check` responde según el estado real (bloqueado sin acta; conforme con ella) y **sigue sin escribir nada** |
| `test_adr002_rederivation.py::test_el_artefacto_previsto_no_existe_todavia` | el artefacto no existe | si no hay acta, no existe; si existe, **valida contra el esquema congelado** |

Ninguna de las seis relaja una regla: cambian el **estado esperado**, no el
criterio. El resto de los módulos citados por actas anteriores queda intacto
byte a byte.

## 4. Lo que esta acta no hace

- **No aprueba `ADR002-TOL-208`.** La puerta sigue **NO SATISFECHA** hasta que
  el usuario apruebe los resultados de la ejecución mediante su propia acta.
- No acepta de antemano ningún resultado: si la corrida es inválida dos veces,
  el resultado es `NO_EVALUABLE` y así se registra.
- No autoriza ninguna otra medición, ni de candidatos ni de T0 fuera del plan
  del §1.
- No fija límites nuevos ni convierte ninguna cifra observada en tolerancia.
- No sustituye la línea base histórica ni modifica Sirius 0.1 (`src/`,
  `tests/`, `migrations/`, configuración productiva).
- No inicia el benchmark ni fusiona el PR #117.

---

**Decisión final:** con el literal **«Apruebo y autorizo»** del usuario, la
ejecución de T0 sobre el corpus congelado v0.4 y la rederivación de los pasos
2 y 3 de `ADR002-TOL-208` quedan **expresamente autorizadas**, con el alcance
exacto del §1 y ninguna holgura más. `ADR002-TOL-208` permanece **NO
SATISFECHA** hasta el acta de aprobación de resultados. El benchmark y el PR
#117 continúan donde estaban: bloqueado el primero, abierto y sin fusionar el
segundo.
