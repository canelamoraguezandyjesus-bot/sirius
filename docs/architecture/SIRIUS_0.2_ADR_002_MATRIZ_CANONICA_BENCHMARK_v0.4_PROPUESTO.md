# SIRIUS 0.2 — ADR-002 · Matriz canónica del benchmark

**Versión:** 0.4
**Estado:** PROPUESTO · NO CONGELADO
**Rama:** `evidence/adr001-spikes`
**Paquete ejecutado:** 03D · Cierre de adjudicación del corpus v0.4
**Fuentes canónicas:** los tres DOCX de `docs/architecture/canonical_sources/`, verificados por SHA-256 contra `MANIFEST.md`
**No autoriza:** congelar el corpus, aprobar `ADR002-TOL-207`, ejecutar T0, implementar o ejecutar `ADR002-A/B/C/D`, satisfacer `ADR002-TOL-208`, `ADR002-TOL-209` o `ADR002-TOL-210`, abrir otro PR ni merge.

Las versiones v0.1, v0.2 y v0.3 de esta matriz se conservan íntegras. Esta v0.4 **no las corrige en su sitio**: es un delta declarado sobre la v0.3 que cierra los hallazgos de la auditoría independiente del corpus v0.3 (BLOQ-01/02/03 y MAT-01…08).

---

## 1. Qué cierra esta versión

| Hallazgo v0.3 | Problema | Corrección v0.4 |
|---|---|---|
| **BLOQ-01** cierre EXHAUSTIVA no verificado | La comprobación de cardinalidad del validador v0.3 solo alcanzaba a `CA-47`; los otros 12 casos EXHAUSTIVA declaraban conjuntos sin dominio que los cerrara | Los 13 casos EXHAUSTIVA declaran un **dominio de adjudicación** y su cierre se calcula con `evaluar_universo`; el validador recalcula las **66 adjudicaciones** (47 casos + 19 ramas) con un oráculo que no importa el motor |
| **BLOQ-02** conjuntos incoherentes con el corpus | `CA-22` mezclaba criterios, `CA-25` y `CA-31` no cerraban sobre los ítems reales, `CA-36-R1` carecía de ancla | `CA-22` cierra por `SOLAPA_INTERVALO` 2026-01-10/2026-03-20 sobre `CON_LISTAS_CERRADAS`; `CA-25` cierra por ancla «atlas»; `CA-31` por criticidad en fase de candidatos; `CA-36-R1` re-anclada a la decisión de aforo `DEC-016` con `SOLO_HISTORICO` |
| **BLOQ-03** universo crítico contradictorio | `MEM-101…112` vivían en PRJ-ALFA con textos de otro expediente y trazas a `B04-CA-31`, y los recuentos 5/6/11/12 no eran derivables | Los 12 críticos sintéticos se trasladan a **PRJ-GAMMA** («…del expediente Gamma»), con `valid_from` escalonado (101-106: 2026-01-05; 107-111: 2026-03-01; 112: 2026-05-01), `recorded_at = valid_from`, traza final `CA-26/38/44`, y el puente 5/6/11/12 se verifica por censo directo del corpus en cada `t_obj` |
| **MAT-01** `operacion_y_modo` en bloque | Modos etiquetados CANONICO por arrastre | Cada modo se clasifica individualmente; solo es CANONICO si el canon lo nombra (`CA-10`, `CA-24`, `CA-49` corregidos); la operación de campo es siempre `DERIVADO_PROPUESTO` |
| **MAT-02** cabecera duplicable invisible | Una tabla con cabecera reclamada bajo *otro* contexto no fallaba | `canonical_source_v0_4.py` añade el **censo global de cabeceras**: cualquier tabla de más con una cabecera reclamada es error, esté donde esté; la comprobación contextual del v0.3 se mantiene y se aplican ambas |
| **MAT-03/04** neutralidad sin cota | Distribuciones publicadas pero sin guardas absolutas | `GUARDAS_DERIVADAS_DE_NEUTRALIDAD_SINTETICA` (guardas del arnés, no canon) con cotas fijas, recalculadas por un oráculo independiente del generador |
| **MAT-05** insuficiencia heredada | Toda rama arrastraba la escalera E0→E5 aunque su modo no la recorra | Cada rama declara `etapa_de_la_rama`; `M3`/`M4` no heredan la escalera (`NO_APLICA` con razón verificable); vocabulario cerrado de variables observables en el esquema |
| **MAT-06** PDP-CA disfrazados de recuperación | `PDP-CA-09/22` llevaban M1/E1/S1, cardinalidad de recuperación y elegibles/prohibidos | Referencia propia `RECUENTO_INDEPENDENCIA_DE_CONSUMIDORES` con registros sintéticos de consumidores falsables; los campos de recuperación quedan a `NO_APLICA` |
| **MAT-08** magnitudes bajo tolerancia pendiente | Textos `PENDIENTE_TOL209` con cifras («250 ms») | `magnitud_inventada()` rechaza cualquier dígito tras retirar los identificadores permitidos (`TOL-\d`, `RED-\d{3}`, `B\d{2}-…`, `PDP-…`, `CRIT-\d`, `§\d`, `v\d.\d`) |
| **M12** previsiones de T0 dispersas | El escaneo anti-T0 no cubría el manifiesto | Lista explícita `CONGELABLES_V0_4` (la proyección T0 **no** está en ella) y escaneo recursivo de todos los congelables, incluido `benchmark_manifest_v0_4.json` |

---

## 2. Modelo de tres capas

La v0.4 separa explícitamente lo que las versiones anteriores mezclaban:

| Capa | Contenido | Regla |
|---|---|---|
| `canonico` | Texto literal de los DOCX aprobados | Nunca se reescribe ni se parafrasea; se cita con documento y sección |
| `instanciacion` | Decisiones sintéticas declaradas (ámbitos, consultas, tiempos, ítems) | Cada campo lleva `fuente`, `seccion`, `estado` y `justificacion`; estado `DERIVADO_PROPUESTO` salvo que el canon lo nombre |
| `adjudicacion` | Cierre **calculado** desde el dominio declarado | No se escribe a mano: `evaluar_universo(corpus, dominio)` en el generador y un oráculo independiente en el validador deben coincidir |

### 2.1 Modelo de adjudicación (claves exactas)

Cada adjudicación registra: `dominio`, `candidatos_considerados`, `elegibles_semanticos`, `resultado_esperado`, `pendientes_por_limite`, `excluidos_por_estado` (lista de `{id, dimension, valor, razon}`), `prohibidos_entre_candidatos`, `decoys_fuera_de_ambito`, `estado`, `justificacion`.

Invariantes (verificadas por generador, validador y pruebas):

1. **EXHAUSTIVA:** `resultado_esperado == elegibles_semanticos`.
2. **ACOTADA:** `resultado_esperado ∪ pendientes_por_limite == elegibles_semanticos`, disjuntos.
3. Un pendiente por límite **nunca** aparece como prohibido.
4. `prohibidos_entre_candidatos` incumplen una puerta declarada (`PUERTA_PROPOSITO_NO_AUTORIZADO`, `PUERTA_NO_USAR_COMO_MEMORIA`, `PUERTA_MARCA_EN_CONTENIDO`, `DISTRACTOR_RUIDO`).
5. `decoys_fuera_de_ambito` no forman parte del complemento interno del dominio.

### 2.2 Dominio de adjudicación

Un dominio declara: colecciones, `kinds`, `ambito` + `regla_multiproyecto` (`SOLO_PROYECTO` / `CON_GLOBAL` / `CON_LISTAS_CERRADAS` / `GLOBAL_TODOS`), sobrescrituras de estados sobre `ESTADOS_ELEGIBLES_DEFECTO`, `criticidad` (filtro en fase de candidatos), `ancla` `{todas, alguna}` por prefijo sobre tokens normalizados, `entidad`, operador de `tiempo` (`SIN_FILTRO` / `VIGENTE_EN_INSTANTE` / `SOLAPA_INTERVALO` / `OCCURRED_EN_INTERVALO` / `REGISTRADO_HASTA`), `limite` `{n, tipo DURO|OBJETIVO, desempate ID|CRITICOS_PRIMERO_LUEGO_ID}`, `incluir_sin_texto`, `prohibiciones_declaradas`, `ruido_es_distractor` y `decoys`. Un límite `OBJETIVO` se expande para los críticos (`n = max(n, nº de críticos)`); un `DURO` corta siempre.

---

## 3. Cierre de los 13 casos EXHAUSTIVA

| Caso | Dominio (resumen) | `resultado_esperado` calculado |
|---|---|---|
| `B04-CA-02` | PRJ-MADEIRA, vigente 2026-06-15, ancla de transporte | `{MEM-002}` (decoy declarado: `MEM-003`) |
| `B04-CA-03` | PRJ-GAMMA sin herencia de LISTA-CERRADA-AB | `∅` (decoy: `DEC-001`) |
| `B04-CA-08` | Propósito autorizado sobre pareja DEC/MEM | `{DEC-005, MEM-006}` |
| `B04-CA-11` | Ítem destruido, `incluir_sin_texto` | `∅` (1 excluido por disponibilidad) |
| `B04-CA-14` | Par de recuerdos de entregables | `{MEM-012, MEM-013}` |
| `B04-CA-17` | Fuente inaccesible | `∅` |
| `B04-CA-22` | PRJ-BETA, `CON_LISTAS_CERRADAS`, DECISION, `SOLAPA_INTERVALO` 2026-01-10 → 2026-03-20 | `{DEC-001, DEC-005, DEC-009, DEC-011, DEC-014, DEC-015}` (excluye `DEC-012` por validez y `DEC-013` por tiempo válido) |
| `B04-CA-25` | Ancla «atlas» en ámbito propio | `{MEM-011}` (decoy: `MEM-018`, «Atlas» en PRJ-GAMMA) |
| `B04-CA-27` | Repetición estable de CA-08 | `{DEC-005, MEM-006}` |
| `B04-CA-28` | Destruido + marca en contenido | `∅` (2 excluidos) |
| `B04-CA-31` | PRJ-ALFA, criticidad en fase de candidatos | `{DEC-003, DEC-010, MEM-014, MEM-016, MEM-025}` (decoy: `MEM-002`, crítico de PRJ-MADEIRA) |
| `B04-CA-36` | Tres ramas EXHAUSTIVA; R1 re-anclada a `DEC-016` (aforo) con `SOLO_HISTORICO` | R1/R2/R3 → `∅` con exclusiones motivadas por rama |
| `B04-CA-47` | Tres ramas EXHAUSTIVA sobre las decisiones de PRJ-BETA | R1 `{DEC-011, DEC-015}` · R2 `{DEC-005, DEC-009, DEC-014}` · R3 `{DEC-005, DEC-014, DEC-015}` |

El intervalo de `CA-22` se conserva tal como está instanciado (2026-01-10/2026-03-20): no existe fuente canónica que ordene meses completos, así que el cierre se corrige vía semántica `SOLAPA_INTERVALO`, no moviendo las fechas.

---

## 4. Nuevo ancla `DEC-016` y barrido de impacto

`DEC-016` (PRJ-ALFA, texto de aforo de la sala de reuniones, `valid_from` 2026-01-05, `valid_to` 2026-03-01, `recorded_at ≤ valid_from`, traza únicamente `B04-CA-36`) da a `CA-36-R1` un objetivo real: la consulta de aforo devuelve `∅` **porque** la única decisión pertinente está fuera de vigencia (`SOLO_HISTORICO`), no porque no exista nada.

Barrido automático: al retirar `DEC-016` del corpus y recalcular las 66 adjudicaciones, **solo `B04-CA-36/R1` cambia**. Cualquier otro cambio bloquea la construcción (el generador aborta) y el commit. Resultado registrado en `benchmark_manifest_v0_4.json → barrido_impacto_dec016`.

---

## 5. Universo crítico reconciliado

| Caso | Ámbito | `t_obj` | Elegibles | Devueltos | Pendientes | Límite |
|---|---|---|---|---|---|---|
| `B04-CA-31` | PRJ-ALFA | vigente | 5 | 5 | 0 | — |
| `B04-CA-44` | PRJ-GAMMA | 2026-02-01 | 6 | 5 | 1 | DURO 5 |
| `B04-CA-26` | PRJ-GAMMA | 2026-04-01 | 11 | 11 | 0 | OBJETIVO 10 → 11 (expansión por críticos, documentada) |
| `B04-CA-38` | PRJ-GAMMA | 2026-06-15 | 12 | 10 | 2 | DURO 10 |

Los recuentos son **derivables**: 6 críticos vigentes desde 2026-01-05, 11 desde 2026-03-01 y 12 desde 2026-05-01, más los 5 críticos de ALFA que nunca se mezclan (ámbitos distintos). El validador censa los críticos vigentes directamente sobre el corpus en cada `t_obj`, además de comprobar las adjudicaciones declaradas.

---

## 6. Lector canónico v0.4

`canonical_source_v0_4.py` **extiende** el v0.3 sin sustituirlo:

1. **Censo global de cabeceras** — para cada cabecera reclamada por una identidad se cuentan las tablas reales del documento que la llevan; `n_reales ≠ n_identidades` es `TablaCanonicaError`. Cierra el hueco del duplicado bajo otro contexto que el v0.3 no veía.
2. **Expansión estricta de métricas** — `expandir_metricas_estricta` solo acepta las formas observadas en las 79 filas del Anexo B (`B04-M16`, `B08-M12/M25` con herencia de prefijo, `B04-M21/B05-M16`, `PDP-M01–M17`); una pieza no reconocida es error inmediato, nunca texto crudo. Se verifica además que la expansión estricta coincide con la laxa del v0.3 en todas las filas.

---

## 7. PDP-CA-09 y PDP-CA-22

Dejaron de fingir ser casos de recuperación: sin modo M1, sin etapa E1, sin S1, sin cardinalidad de recuperación, sin elegibles/prohibidos de contenido, sin `recuperacion_b04`. Su referencia es `tipo_referencia: RECUENTO_INDEPENDENCIA_DE_CONSUMIDORES` con registros sintéticos de consumidores que hacen el recuento **falsable** (PDP-CA-09: `CONS-A/B` comparten dependencia específica y `CONS-C` no → recuento 2; PDP-CA-22: `CONS-D/E` mismo intérprete con configuración distinta y `CONS-F` aparte → recuento 2).

`references_v0_4.json` contiene **52 referencias**: 50 de recuperación B04 + 2 de recuento PDP, con esquemas separados.

---

## 8. Estado

Todo lo anterior queda **PROPUESTO y sin congelar**. `ADR002-TOL-207/208/209/210` siguen NO SATISFECHAS. La familia v0.4 se somete a una nueva auditoría independiente antes de cualquier congelación.
