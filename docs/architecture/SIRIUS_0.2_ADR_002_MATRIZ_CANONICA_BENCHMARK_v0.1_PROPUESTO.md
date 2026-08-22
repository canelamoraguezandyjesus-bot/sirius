# SIRIUS 0.2 — ADR-002 · Matriz canónica del benchmark

**Versión:** 0.1
**Estado:** **PROPUESTO** · no aprueba, no decide y no autoriza ejecutar nada
**Fecha:** 26 de julio de 2026
**Fuentes canónicas:** `docs/architecture/canonical_sources/` — B04 v1.0 APROBADO, Plan de Pruebas + RED/PDP v1.0 APROBADO, ARQ-00 v1.0 APROBADO
**Puerta satisfecha:** `SRC-ADR002-01` (26 de julio de 2026)
**Materialización ejecutable:** `experiments/adr002/benchmark/cases_v0_1.json` y `references_v0_1.json`
**No autoriza:** ejecutar T0 ni T1–T4, implementar candidatos, elegir realización técnica, modificar Sirius 0.1 ni merge.

---

## 0. Qué es esta matriz y qué no es

Es la **extracción literal** del contrato canónico de B04 v1.0 APROBADO, instanciada como casos ejecutables. Los cincuenta casos de aceptación `B04-CA-01` a `B04-CA-50` aparecen **exactamente una vez cada uno**, con su riesgo, su entrada, su resultado esperado y su fallo observable **tomados del documento aprobado**, no reescritos.

**Regla dura aplicada.** Ningún texto ausente se ha reconstruido por analogía. Donde el canon no fija algo —el orden dentro de un conjunto, por ejemplo— la matriz lo declara como conjunto y no inventa una secuencia.

**Lo que la matriz añade** y el canon no contiene, porque son propios de la elección técnica: la asignación de datos sintéticos concretos del corpus, la etapa `E0–E5` esperada, la parada `S1–S7` esperada, la cardinalidad declarada y la clasificación de ejecutabilidad frente a T0. Todo ello es **nivel de instanciación**, no reinterpretación de la referencia.

### 0.1 Los tres niveles

| Nivel | Qué es | Quién manda sobre la referencia | Recuento |
|---|---|---|---|
| **1 · Canónicos reutilizados** | `B04-CA-01`–`CA-50` | **B04 v1.0 APROBADO.** El benchmark los ejecuta, no los reescribe | **50** |
| **2 · Arquitectónicos nuevos** | Comportamiento del índice, del ciclo y de la purga que B04 no cubre porque excluye almacenamiento (§3) | ADR-002 y ADR-001 | **5** |
| **3 · Ablaciones técnicas** | Instrumentos de medida; nunca producen veredicto de conformidad | ADR-002 | **7** |

---

## 1. Cobertura exacta

Comprobada automáticamente por `validate_corpus.py` y por 44 pruebas de contrato. El informe legible por máquina es `artifacts/adr002_benchmark_preparation/validacion_corpus.json`.

| Serie canónica | Cubierto | Denominador | Ausencias | Duplicados |
|---|---|---|---|---|
| **B04-CA-01 … CA-50** | **50** | 50 | **0** | **0** |
| **B04-RF-01 … RF-32** | **32** | 32 | **0** | — |
| **B04-M01 … M21** | **21** | 21 | **0** | — |
| **RED-027 … RED-034** (delegaciones de B04) | **8** | 8 | **0** | — |
| Familias PDP citadas por los CA de nivel 1 | 18 | 25 | 7 | — |
| Familias PDP con los tres niveles | **20** | 25 | 5 | — |

**Sobre las cinco familias restantes.** `F16` carga e interrupciones, `F17` continuidad, `F18` ciclo de vida, `F19` control y matriz de catorce operaciones, y `F20` exportación y reimportación **no pertenecen a B04**: son de B03, B06, B07 y B08. `PDP-M03` exige 25/25 para cerrar el **Plan de Pruebas completo**, no para el benchmark de ADR-002. Declararlas cubiertas aquí sería falsear la cobertura.

**RED-040** (reintento acotado B05→B04) **no se usa como requisito propio de selección técnica**: pertenece a B05/ADR-003B y ADR-002 solo registra la interfaz. Una prueba automática lo verifica.

---

## 2. Matriz de nivel 1 — los cincuenta casos canónicos

Cada fila cita la ficha completa de veinte campos en `cases_v0_1.json`. Aquí se resume; **el JSON es la fuente ejecutable**.

Leyenda de la columna T0: **Sí** = expresable y la línea base debería pasar · **fallo esperado** = expresable, la línea base falla · **fallo duro** = expresable y es uno de los tres hallazgos inseguros medidos · **No expresable** = la línea base carece del eje; se marca como **incapacidad de la línea base y no se elimina**.

| CA | Riesgo canónico | RF | Familia | Métrica | Modo | Ámbito | Etapa · parada | Card. | Crit. | T0 | RED |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **CA-01** | Preferencia actual directa | 01, 15, 22 | F01 | M02, M03, M14 | M1 | GLOBAL | E1 · S1 | EXAC | IMPO | Sí · **fallo esperado** | 027 |
| **CA-02** | Aislamiento de proyecto | 06, 09 | F08 | M06, M04 | M1 | MADEIRA | E1 · S5 | EXHA | CRIT | Sí · **fallo duro** | 010 |
| **CA-03** | Multi-proyecto cerrado | 06 | F08 | M06 | M1 | GAMMA | E1 · S5 | EXHA | CRIT | **No expresable** | 010 |
| **CA-04** | Archivado ordinario | 12 | F13, F01 | M05 | M1 | ALFA | E1 · S5 | EXAC | ORDI | **Sí** | 014 |
| **CA-05** | Histórico explícito | 08 | F04 | M11, M05 | M2 | ALFA | E1 · S1 | EXAC | ORDI | **No expresable** | 028 |
| **CA-06** | Fecha futura | 07 | F09 | M11 | M1 | ALFA | E1 · S1 | EXAC | ORDI | **No expresable** | 028 |
| **CA-07** | Fecha insuficiente | 04, 07 | F09 | M11, M09 | M1 | ALFA | E1 · S3 | EXAC | ORDI | **No expresable** | 028 |
| **CA-08** | Conflicto abierto | 21 | F06 | M08 | M1 | BETA | E1 · S6 | EXHA | CRIT | **No expresable** | 009 |
| **CA-09** | Candidata pendiente | 03, 12 | F05 | M04 | M1 | ALFA | E1 · S5 | EXAC | ORDI | **No expresable** | 013 |
| **CA-10** | Rechazada/suprimida | 12 | F05 | M04 | M1 | ALFA | E1 · S5 | EXAC | ORDI | **No expresable** | 022 |
| **CA-11** | Eliminada | 10 | F13 | M04 | M1 | ALFA | E0 · S5 | EXHA | CRIT | **Sí** | 015 |
| **CA-12** | Restringida | 12 | F11 | M04, M20 | M1 | ALFA | E0 · S2 | EXAC | CRIT | **No expresable** | 013 |
| **CA-13** | Alias resuelto | 05 | F07 | M02 | M1 | ALFA | E1 · S1 | EXAC | ORDI | **No expresable** | 012 |
| **CA-14** | Entidad ambigua | 04, 05 | F07 | M10, M13 | M1 | GLOBAL | E0 · S3 | EXHA | CRIT | **No expresable** | 012 |
| **CA-15** | Verificación literal | 03, 18 | F10 | M07 | M3 | ALFA | E4 · S1 | EXAC | ORDI | **No expresable** | 027 |
| **CA-16** | Fallback autorizado | 18 | F10 | M12 | M1 | GAMMA | E4 · S1 | EXAC | ORDI | **No expresable** | 034 |
| **CA-17** | Ausencia confirmada | 25 | F23 | M09 | M1 | ALFA | E4 · S5 | EXHA | CRIT | Sí · **fallo esperado** | 031 |
| **CA-18** | Fuente inaccesible | 32 | F23, F10 | M09 | M3 | ALFA | E4 · S7 | EXAC | CRIT | **No expresable** | 034 |
| **CA-19** | Duplicado multifuente | 20 | F10, F14 | M10, M07 | M1 | ALFA | E1 · S1 | EXAC | ORDI | Sí · **fallo esperado** | 030 |
| **CA-20** | Restricción negativa | 19 | F15 | M17 | M1 | ALFA | E3 · S1 | EXAC | CRIT | Sí · **fallo duro** | 011 |
| **CA-21** | Condición | 19 | F15 | M18 | M1 | ALFA | E3 · S1 | EXAC | CRIT | Sí · **fallo esperado** | 011 |
| **CA-22** | Intervalo temporal | 08 | F02 | M11 | M2 | BETA | E1 · S5 | EXHA | ORDI | **No expresable** | 028 |
| **CA-23** | Actual frente a anterior | 08 | F04 | M05, M11 | M2 | ALFA | E1 · S1 | EXAC | IMPO | **No expresable** | 028 |
| **CA-24** | Sin soporte | 10 | F10 | M04 | M1 | ALFA | E1 · S5 | EXAC | ORDI | **No expresable** | 015 |
| **CA-25** | Contaminación léxica | 06 | F08 | M06 | M1 | ALFA | E1 · S5 | EXHA | CRIT | Sí · **fallo duro** | 010 |
| **CA-26** | Límite objetivo | 24 | F14 | M21, M01 | M1 | ALFA | E5 · S1 | ACOT | CRIT | **No expresable** | 030 |
| **CA-27** | Autoridad por dominio | 21 | F06 | M08 | M5 | BETA | E1 · S6 | EXHA | CRIT | **No expresable** | 009 |
| **CA-28** | No persistencia | 10 | F12 | M04 | M3 | ALFA | E0 · S5 | EXHA | CRIT | **No expresable** | 025 |
| **CA-29** | Fuente externa ordinaria | 13 | F10 | M07 | M1 | ALFA | E3 · S1 | EXAC | ORDI | **No expresable** | 018 |
| **CA-30** | Explicación por resultado | 28 | F24, F01 | M14 | M1 | ALFA | E5 · S1 | ACOT | IMPO | Sí · **fallo esperado** | 029 |
| **CA-31** | Críticos dispersos | 23 | F14, F10 | M01 | M1 | ALFA | E4 · S5 | EXHA | CRIT | **No expresable** | 030 |
| **CA-32** | Corte de registro | 08 | F03 | M11 | M2 | BETA | E1 · S1 | EXAC | CRIT | **No expresable** | 028 |
| **CA-33** | Consulta interna autorizada | 30 | F01 | M15 | M1 | ALFA | E1 · S1 | EXAC | IMPO | **No expresable** | 027 |
| **CA-34** | Handoff de criticidad | 23, 27 | F14 | M19 | M1 | ALFA | E5 · S1 | ACOT | CRIT | **No expresable** | 030 |
| **CA-35** | Fallback marcado no usar | 11 | F12 | M12 | M1 | ALFA | E4 · S5 | EXAC | CRIT | **No expresable** | 025 |
| **CA-36** | Ausencias diferenciadas | 25 | F23 | M09 | M1 | ALFA | E4 · S5 | EXHA | CRIT | **No expresable** | 031 |
| **CA-37** | No revelación por traza | 26 | F11 | M20 | M1 | ALFA | E0 · S2 | EXAC | CRIT | **No expresable** | 032 |
| **CA-38** | Límite duro | 24 | F14 | M01, M21 | M1 | ALFA | E5 · S4 | ACOT | CRIT | **No expresable** | 030 |
| **CA-39** | Neutralidad de arnés | 31 | F22 | M16 | M1 | ALFA | E5 · S5 | EXHA | CRIT | **Sí** | 033 |
| **CA-40** | Parada tras etapa suficiente | 14, 29 | F01, F24 | M21, M15 | M1 | ALFA | E1 · S1 | EXAC | CRIT | Sí · **fallo duro** | 029 |
| **CA-41** | Expansión léxica controlada | 16 | F01, F07 | M02 | M1 | ALFA | E2 · S1 | EXAC | ORDI | Sí · **fallo esperado** | 029 |
| **CA-42** | Expansión semántica con polaridad | 17, 19 | F15 | M17 | M1 | ALFA | E3 · S1 | EXAC | CRIT | Sí · **fallo duro** | 029 |
| **CA-43** | Coordinación intra-etapa acotada | 14 | F01 | M15 | M1 | ALFA | E3 · S1 | EXAC | IMPO | **No expresable** | 029 |
| **CA-44** | Parada reproducible por límite | 24, 29 | F14, F24 | M21 | M1 | ALFA | E5 · S4 | ACOT | CRIT | **No expresable** | 030 |
| **CA-45** | Fallback anterior a sustitución | 18 | F10, F04 | M12 | M1 | ALFA | E4 · S1 | EXAC | CRIT | **No expresable** | 029 |
| **CA-46** | Propósito no autorizado | 02 | F11 | M13 | M1 | BETA | E0 · S2 | EXAC | CRIT | **No expresable** | 027 |
| **CA-47** | Fecha de evento distinta | 07, 08 | F02, F03 | M11 | M2 | BETA | E1 · S5 | EXHA | CRIT | **No expresable** | 028 |
| **CA-48** | Canal lateral diferencial | 26 | F11 | M20 | M1 | ALFA | E0 · S2 | EXAC | CRIT | **No expresable** | 032 |
| **CA-49** | Fallback enlaza candidata | 18 | F05, F10 | M12 | M3 | ALFA | E4 · S1 | EXAC | IMPO | **No expresable** | 029 |
| **CA-50** | Auto-marcado crítico controlado | 23 | F14 | M19 | M1 | ALFA | E1 · S1 | EXAC | CRIT | **No expresable** | 030 |

### 2.1 Campos que la tabla resume

La ficha completa de cada caso, en `cases_v0_1.json`, tiene los veinte campos exigidos: identificador canónico · riesgo · requisito verificado · familia PDP · métrica y umbral · datos sintéticos · consulta · modo · propósito · permiso · ámbito · tiempo objetivo · corte de registro · candidatos elegibles · **candidatos prohibidos** · resultado esperado · orden esperado · explicación esperada · etapa y parada · cardinalidad · criticidad · ejecutable por T0 · requiere T1–T4 · evidencia mínima · fallo observable · traza RED.

**El campo de prohibidos es lo que hace adversarial al benchmark**: un resultado prohibido es fallo duro aunque el orden del resto sea perfecto. Una prueba automática verifica que elegibles y prohibidos son disjuntos en los cincuenta casos.

**El orden esperado se declara con su tipo**: orden total cuando el canon lo fija, conjunto cuando no lo fija, y vacío cuando el resultado correcto es no devolver nada. No se inventa una secuencia donde el canon habla de conjunto.

---

## 3. Nivel 2 — casos arquitectónicos

Solo cinco, y cada uno declara **por qué ningún caso canónico lo cubre**. B04 es documento de producto y excluye expresamente «índices, embeddings, RAG, modelos, consultas físicas, servicios y almacenamiento» (§3): esos casos no pueden existir en B04 y no se están duplicando.

| ID | Qué mide | Por qué no lo cubre ningún CA | Puerta |
|---|---|---|---|
| **ARQ-CA-01** | Borrado y regeneración completos de todo índice derivado, desde el canon | B04 excluye almacenamiento; la obligación es de ADR-001 c.2 y c.3 | puerta 5 |
| **ARQ-CA-02** | **Purga física** sin fragmento recuperable en `.db`, `-wal`, `-shm` ni `-journal` | ADR-001 c.3 y c.4; ningún CA de B04 la prueba | puerta 5 |
| **ARQ-CA-03** | Estabilidad de orden y conjunto ante entradas **idénticas** | CA-39 mide equivalencia **entre** implementaciones; esta mide repetición de **la misma** | puerta 4 |
| **ARQ-CA-04** | Declaración congelada de tamaño y ciclo de todo índice adicional | Obligación de `TOL-104A` y `TOL-203`; no existe en B04 | puerta 7 |
| **ARQ-CA-05** | Coste incremental declarado por etapa E0–E5 | B04 fija las etapas pero no su coste | puerta 7 |

---

## 4. Nivel 3 — ablaciones

No son casos de conformidad. Aíslan la aportación de cada señal y de cada etapa, y **nunca producen un veredicto por sí solas**.

| Ablación | Qué se desactiva | Qué aísla |
|---|---|---|
| **AB-0** | Nada — línea base congelada de 0.1 (familia F25) | Punto de referencia |
| **AB-1** | Todo salvo E0/E1 estructurado y exacto | Aportación de la recuperación exacta sola |
| **AB-2** | Etapa léxica de RF-16 | Aportación de variantes y alias |
| **AB-3** | Etapa de significado/relaciones de RF-17 | Aportación de la señal tardía |
| **AB-4** | Validación de polaridad, condición y tiempo de RF-17, **manteniendo la señal** | Aportación específica de la validación frente a la señal cruda |
| **AB-5** | Puertas G1–G12, de una en una | Que ninguna puerta enmascare el efecto de otra |
| **AB-6** | Orden aleatorizado con semilla fija | Suelo de comparación |

---

## 5. Reparto frente a T0

`T0` es la línea base congelada de Sirius 0.1, identificada por el head de Alembic `61be4bb269bf`. **No es candidata**: es control de falsación (ADR-002 §3.1).

| Clase | Casos | Qué significa |
|---|---|---|
| **Ejecutable y debería pasar** | **3** — CA-04, CA-11, CA-39 | Archivado excluido, eliminado no recuperable y neutralidad del puerto: son los activos reales de la línea base |
| **Ejecutable con fallo esperado** | **6** — CA-01, CA-17, CA-19, CA-21, CA-30, CA-41 | El eje existe pero la línea base no lo satisface |
| **Ejecutable con fallo duro** | **5** — CA-02, CA-20, CA-25, CA-40, CA-42 | Los tres hallazgos inseguros medidos: ámbito (RF-06), negación (RF-19) y salto a recuperación amplia (RF-14) |
| **No expresable** | **36** | La línea base carece del eje entero: modos, propósito, permiso, criticidad, suficiencia, cardinalidad, corte de registro, taxonomía de ausencia, plan reproducible |
| **Total** | **50** | Ningún caso eliminado |

**Los 36 no expresables se conservan.** La Especificación de benchmark §3 principio 6 lo exige: se marcan como **incapacidad de la línea base**, no se borran. Comparar contra un 0.1 extendido exigiría autorización expresa, porque dejaría de ser la línea base congelada.

**Lectura honesta.** Solo 14 de 50 casos son ejecutables contra T0, y de esos 14 la línea base pasa 3. No es un defecto del corpus: es la medida de la distancia entre Sirius 0.1 y el contrato B04, y coincide con el inventario normativo —1 RF `EXISTENTE`, 11 `PARCIAL`, 17 `AUSENTE`, 3 `INSEGURO`.

---

## 6. Observación material sobre ARQ-00 §23

**No es un defecto del corpus y no bloquea esta ronda, pero debe registrarse.**

`ARQ-00 v1.0 APROBADO` §23 enuncia las alternativas mínimas de ADR-002 como **A, B, C y D**:

- **A**: escalonada solo léxica/estructurada en todas las etapas;
- **B**: léxica/estructurada con **señal semántica vectorial** en etapas tardías;
- **C**: léxica/estructurada con **señal relacional explícita** en etapas tardías;
- **D**: semántica **y** relacional en etapas tardías distintas y orden predefinido.

`SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.2_ABIERTO.md` §3 usa en cambio **T1–T4**, particionadas por *sustrato léxico* (FTS5 o alternativo) × *relaciones* (desde el canon o índice derivado), con señal semántica común a las cuatro.

**Las dos particiones no son la misma.** La de ARQ-00 hace de la señal semántica un eje de elección; la de ADR-002 v0.2 la hace obligatoria en las cuatro y abre en su lugar el eje de sustituir FTS5. La segunda es coherente con B04-RF-17, que impone la señal tardía; la primera es la aprobada en ARQ-00.

**Consecuencia práctica:** el corpus y esta matriz son **neutrales respecto de ambas particiones** —trazan a RF, CA, M y RED, no a T1–T4 ni a A–D—, así que ninguna decisión queda comprometida. Pero **antes de ejecutar el benchmark hay que resolver cuál es el conjunto de candidatos**, porque las fichas de candidato (`TOL-210`) se emiten por candidato y el número y la naturaleza cambian según la partición.

Se registra como cuestión abierta para el usuario. **No se resuelve aquí**: ADR-002 v0.2 §3 dice que el paquete admite ajustar la formulación «siempre que no reabra lo aprobado», y ARQ-00 es fuente canónica aprobada.

---

## 7. Lo que esta matriz no hace

- No ejecuta el benchmark, ni T0, ni T1–T4.
- **No sustituye B04-CA-01–50 ni el PDP**, y no crea referencias que los contradigan.
- No reabre B04-B, E0–E5, G1–G12 ni S1–S7.
- No elige entre candidatos ni propone modelos, extensiones ni fórmulas de fusión.
- No fija umbrales: los fija el Registro de Tolerancias v0.4, aprobado el 26 de julio de 2026.
- No modifica `src/`, `tests/`, `migrations/`, `canonical_sources/` ni configuración productiva.

---

**Siguiente movimiento único:** que el usuario revise la matriz y el corpus, apruebe o corrija el presupuesto `TOL-207`, y resuelva la cuestión de la §6 —qué conjunto de candidatos se ejecuta— antes de congelar el corpus definitivo y rederivar T0 sobre él (`ADR002-TOL-208`).
