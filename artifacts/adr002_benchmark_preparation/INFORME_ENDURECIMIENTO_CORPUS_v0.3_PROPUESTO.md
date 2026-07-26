# SIRIUS 0.2 — ADR-002 · Informe de endurecimiento del corpus, el validador y la distribución

**Versión:** 0.3
**Estado:** PROPUESTO · NO CONGELADO
**Rama:** `evidence/adr001-spikes`
**Paquete ejecutado:** `docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_03C_ENDURECIMIENTO_CORPUS_v0.1.md`
**No autoriza:** congelar el corpus, aprobar `ADR002-TOL-207`, ejecutar T0, implementar o ejecutar `ADR002-A/B/C/D`, satisfacer `ADR002-TOL-208`, `ADR002-TOL-209` o `ADR002-TOL-210`, modificar `canonical_sources/`, `src/`, `tests/`, `migrations/` ni configuración productiva, abrir otro PR ni fusionar el PR #117.

Todos los artefactos v0.1 y v0.2 se conservan íntegros. Ninguno se ha modificado para hacerlo pasar: los tres validadores se ejecutan en la misma rama y los tres terminan sin fallos.

---

## 1. Cierre de los bloqueantes

### B-01 · lector canónico frágil y aprobación en vacío — **CERRADO**

El defecto era real y demostrable: el Plan de Pruebas contiene **dos** tablas de seis columnas cuya primera columna es `RED-\d{3}` —el Registro RED del §4 y el Anexo B del §23—. El lector v0.2 filtraba por `len(celdas) == 6` y por el patrón del identificador, de modo que **las dos** entraban en el mismo diccionario y la segunda sobrescribía a la primera. Que el resultado final fuese el Anexo B dependía del orden físico de las tablas en el fichero, no de ninguna comprobación.

`canonical_source_v0_3.py` corrige:

- **Selección por identidad.** Catorce identidades, cada una con cabecera literal y contexto canónico. `tabla(identidad)` recoge las candidatas y **falla si hay cero o más de una** (`TablaCanonicaError`). Nunca usa la posición física. `b04_casos_17` y `b04_casos_17_1` comparten cabecera y se separan solo por contexto; `pdp_registro_red` y `pdp_anexo_b` comparten forma y se separan por cabecera.
- **Invariantes de contenido.** Cada identidad declara su número exacto de filas y el patrón de su primera columna; una fila añadida, perdida o duplicada falla. `Canon.comprobar_minimos()` exige 50 `B04-CA`, 79 filas de Anexo B, 79 de Registro RED, ≥20 `B04-CA` nombrados por el Anexo B, 25 familias con su texto de cobertura, 28 `PDP-CA`, exactamente los 14 campos canónicos del PDP §7, 32 `B04-RF`, 21 `B04-M` y 25 destinos de ARQ-00 §20. Una tabla vacía o equivocada **no puede producir un PASS parcial**: la carga del canon aborta.
- **Anexo B en ambas direcciones.** `canon → artefacto` (toda asignación presente) y `artefacto → canon` (ninguna inventada). Las trazas derivadas viven en campos separados y el validador comprueba que no se solapan.
- **Identificadores inexistentes rechazados.** `RED-099`, `B04-M99`, `F99`, `B04-CA-51` y `PDP-CA-29` fallan tanto en el lector como en el validador.

Corrección adicional descubierta al leer el Anexo B con rigor: la celda `B08-M12/M25` producía en el v0.2 un identificador suelto `M25`, que no existe en ningún bloque. `_expandir_metricas` arrastra el prefijo y expande rangos, con lo que **`B05-M16` y `B08-M25` quedan conservadas y declaradas** como referencias canónicas externas en lugar de filtrarse en silencio.

### B-02 · corpus de rendimiento degenerado — **CERRADO**

El corpus v0.1 de rendimiento era un relleno uniforme (`"Mensaje 00042 de la serie de volumen sobre …"`) alojado en un octavo proyecto artificial, mientras se declaraba una escala de «2 proyectos». Medir sobre él no habría medido nada.

`performance_corpus_v0_2.json` es un corpus sintético independiente con **exactamente 5.000 mensajes, 500 recuerdos, 50 decisiones y 2 proyectos reales**, contados sobre los datos. Sin proyecto de volumen. Distribución medida en §5 de este informe. Sin dato real y sin red.

### B-03 · cierre incorrecto de `CA-47` — **CERRADO**

Los conjuntos ya no se escriben: se **derivan**. El artefacto declara el filtro base y el filtro temporal de cada rama; el generador calcula el cierre y el validador lo **vuelve a calcular por su cuenta** desde la declaración y compara. Bajo los datos actuales:

- `R1` `occurred_at` en enero → `DEC-011`, `DEC-015`
- `R2` tiempo válido a 20 de enero → **`DEC-005`, `DEC-009`, `DEC-014`**
- `R3` `recorded_at` hasta 15 de febrero → **`DEC-005`, `DEC-014`, `DEC-015`**

Tres conjuntos distintos; los prohibidos son exactamente el complemento del universo en ámbito. El v0.2 declaraba `R2 = {DEC-014}`: omitía `DEC-005` y `DEC-009`, que el filtro declarado sí selecciona. `DEC-012` queda fuera por `validez = SUSTITUIDA`, no por elección.

### B-04 · seis `PDP-CA` mal clasificados — **CERRADO**

Solo `PDP-CA-09` y `PDP-CA-22` conservan la condición de caso funcional de nivel 1, y no por criterio propio: son los **únicos** que el Anexo B ancla en una fila que cita B04 (`RED-017` → `B04-CA-39`, `B04-M16`, `B08-M25`, `F22`). El validador comprueba que el conjunto instanciado coincide exactamente con el conjunto anclado, calculado del DOCX.

`PDP-CA-02`, `-03`, `-06`, `-16`, `-17` y `-18` pasan a `pdp_harness_rules_v0_1.json` como **reglas canónicas de protocolo del arnés**, con texto canónico, fuente PDP, regla que las importa, regla de ejecución, evidencia requerida, consecuencia y estado de aplicabilidad. No tienen consulta funcional, ni conjunto elegible, ni etapa, ni parada, ni previsión T0; el validador comprueba la ausencia de cada campo prohibido.

---

## 2. Cierre de los defectos materiales

Los identificadores `M-01`–`M-11` se toman de la sección **MATERIALES** del encargo, que el paquete 03C referencia sin enumerar. Se reproducen agrupados tal como allí aparecen.

| ID | Defecto | Cierre | Dónde se comprueba |
|---|---|---|---|
| **M-01** | Contar la escala directamente sobre los datos, no comparar declaración contra declaración | `medir_distribucion()` cuenta items, recuerdos, decisiones, mensajes, documentos, relaciones, entidades y proyectos **referenciados** recorriendo las colecciones. El validador compara lo publicado con lo recalculado y además con la escala de `ADR002-TOL-208` | `_rendimiento`, `_conformidad` |
| **M-02** | Ampliar contaminación a tokens normalizados, raíces, singular/plural, alias, entidades y n-gramas; detectar `turno/turnos` y `registro/registrado` | `LexicoProtegido` con cinco mecanismos y normalización NFKD sin acentos. `turnos` se detecta por sufijo; `registrado` por raíz de 6 caracteres. 0 textos contaminados de 6.194 | `_contaminacion`, pruebas parametrizadas de pares mínimos |
| **M-03** | Resolver 8 proyectos frente a 2: el corpus debe contener realmente 2 | El corpus de rendimiento tiene **2 proyectos y 2 proyectos referenciados**, sin proyecto de volumen. La comprobación cuenta `project_id` distintos en items y mensajes, no la declaración | `_rendimiento` |
| **M-04** | Comprobar identidad de items, mensajes, documentos y relaciones | `identidad_de_colecciones()` publica huella SHA-256 por colección y por elemento en los dos corpus; el validador las recalcula. Alterar un mensaje, un documento o una relación falla | `_conformidad`, `_rendimiento`, negativa 10 |
| **M-05** | Aplicar `CANONICO`/`DERIVADO` a los 14 campos completos de la ficha PDP | Los catorce campos más la condición de insuficiencia llevan `valor`, `fuente`, `seccion`, `estado` y `justificacion`. Solo `Entrada`, `Fallo` y `Operación y modo` pueden ser `CANONICO`, y solo contra el texto literal del propio caso | `_ficha_14_campos`, negativa 5 |
| **M-06** | Comprobar Anexo B `canon → artefacto` y `artefacto → canon`; conservar `B05-M16` y `B08-M25` | Dos comprobaciones separadas, más el registro expreso de métricas B04 propias y externas canónicas | `_anexo_b`, negativa 3 |
| **M-07** | Leer la tabla completa de PDP §7 y fallar ante filas añadidas, perdidas o duplicadas; seleccionar bien la tabla de familias PDP y verificar también sus textos | `pdp_ficha_7` exige 14 filas y `CAMPOS_PDP7_CANONICOS` exactos; `pdp_familias_8` exige 25 filas con nombre y texto de cobertura, y `pdp_cases_v0_2.json` publica los 25 textos comparados carácter a carácter con el DOCX | `_canon`, `_separacion_arnes`, negativa 1, negativa 14 |
| **M-08** | Aplicar el criterio de proyección T0 a **todos** los casos funcionales | `construir_proyeccion_t0()` recorre los 50 `B04-CA` y los 2 `PDP-CA` funcionales y aplica un criterio único de cuatro reglas ordenadas. No hay lista manual. Los 12 casos de nivel 2 y 3 se declaran **no proyectados** con motivo | `_t0` |
| **M-09** | Estructurar la condición de insuficiencia por rama; declarar `NO_APLICA` con razón | Cada rama declara sus transiciones con etapa actual, variables observadas, predicado, umbral, siguiente etapa permitida, fuente y estado. `E0` y `B04-CA-39` declaran `NO_APLICA` con razón verificable. No se acepta lista vacía ni frase genérica | `_insuficiencia` |
| **M-10** | Distinguir `tolerancia_id` de `valor_pendiente_en` en `CA-37`, `CA-48` (TOL-201/TOL-209) y `CA-39` (TOL-001/TOL-209) | El campo `tolerancias` es una estructura con `tolerancia_id`, `valor_pendiente_en`, `regla` y `condicion_aplicada`. `tolerancia_id` nunca es igual a `valor_pendiente_en`; el estado `PENDIENTE_TOL209` es equivalente a tener valor pendiente | `_tolerancias` |
| **M-11** | Añadir una comprobación real de neutralidad tecnológica y entre `ADR002-A/B/C/D` | 26 tecnologías concretas, 10 descriptores de candidato y los 4 identificadores de candidato. Prohibición absoluta en corpus de rendimiento, reglas, matriz PDP y previsión; en casos y referencias, un término solo cabe donde el canon del propio caso lo fija | `_neutralidad`, negativa 12 |

Defectos menores cerrados en la documentación nueva: **19 ramas** (no 17), **21 casos con comillas tipográficas** (no 8), **cuatro denominadores de familias** con fuente expresa, filtro y conservación de `B05-M16` y `B08-M25`, independencia declarada entre los dos corpus, y `TOL-207/208/209/210` expresamente no satisfechas.

---

## 3. Clasificación final de `PDP-CA` y reglas del arnés

Tres clases disjuntas que cubren los 28 casos transversales sin hueco ni solape.

**Casos funcionales de nivel 1 (2)** — ficha completa del PDP §7, consulta funcional, previsión T0 en el fichero no normativo:

| ID | Anclaje | Previsión T0 |
|---|---|---|
| `PDP-CA-09` | `RED-017` · `B04-CA-39` · `B04-M16` / `B08-M25` · `F22` | `NO_EJECUTABLE_CON_UNA_SOLA_IMPLEMENTACION` |
| `PDP-CA-22` | `RED-017` · `B04-CA-39` · `B04-M16` / `B08-M25` · `F22` | `NO_EJECUTABLE_CON_UNA_SOLA_IMPLEMENTACION` |

**Reglas de protocolo del arnés (6)** — sin consulta, sin recuperación, sin T0:

| ID | Regla que la importa | Estado |
|---|---|---|
| `PDP-CA-02` | Registro de Tolerancias v0.4 §9 regla 1 y Especificación §3 principio 2 | `APLICABLE_TRAS_CONGELACION` |
| `PDP-CA-03` | Protocolo de medición v0.1 §6.5, §6.6 y prohibición 8 | `APLICABLE_TRAS_CONGELACION` |
| `PDP-CA-06` | `ADR002-TOL-210` · congelación antes de la primera ejecución | `APLICABLE_TRAS_CONGELACION` |
| `PDP-CA-16` | Protocolo de medición v0.1 §7 · registro obligatorio | `APLICABLE_TRAS_CONGELACION` |
| `PDP-CA-17` | Registro de Tolerancias v0.4 §9 reglas 1 y 10 | `APLICABLE_TRAS_CONGELACION` |
| `PDP-CA-18` | `ADR002-TOL-107` · NO EVALUABLE permanece en el denominador | `APLICABLE_TRAS_CONGELACION` |

**Fuera de alcance (20)** — con la fila RED que los asigna, sus familias y su responsable según ARQ-00 §20. No se afirma cobertura.

---

## 4. Cierre exacto de `CA-47`

```
filtro base   kind=DECISION · project_id=PRJ-BETA · confirmacion=CONFIRMADA
              validez=VIGENTE · disponibilidad=DISPONIBLE · sensibilidad=ORDINARIA
              no_usar_como_memoria=false
universo      DEC-005 DEC-009 DEC-011 DEC-013 DEC-014 DEC-015
```

| Rama | Predicado | Elegibles | Prohibidos |
|---|---|---|---|
| `R1` | `occurred_at ∈ [2026-01-01, 2026-02-01)` | `DEC-011 DEC-015` | `DEC-005 DEC-009 DEC-013 DEC-014` |
| `R2` | `valid_from ≤ 2026-01-20 < valid_to` o abierto | `DEC-005 DEC-009 DEC-014` | `DEC-011 DEC-013 DEC-015` |
| `R3` | `recorded_at ≤ 2026-02-15` | `DEC-005 DEC-014 DEC-015` | `DEC-009 DEC-011 DEC-013` |

Cardinalidad `EXHAUSTIVA` justificada: la instanciación cierra el conjunto sobre el universo declarado, y la parada `S1` está prohibida por B04 §15.2 (comprobado). El validador reimplementa los tres predicados y exige igualdad exacta, complemento exacto y tres conjuntos distintos.

---

## 5. Distribución medida del corpus de rendimiento

Calculada sobre los datos por `medir_distribucion()` y verificada por el validador.

| Magnitud | Valor |
|---|---|
| mensajes / recuerdos / decisiones / proyectos | 5.000 / 500 / 50 / **2** |
| documentos / relaciones / entidades | 120 / 180 / 24 |
| textos analizados | 6.194 |
| longitud: media · mediana · p95 · desviación · min · max | 86,66 · 82 · 169 · 43,55 · 24 · 220 |
| longitudes distintas | **186** |
| vocabulario informativo | **236** palabras, 55.219 tokens |
| frecuencia relativa máxima | **2,55 %** (`junto`, 1.408) |
| pendiente Zipf log-log | **−0,796** |
| textos distintos | 6.194 / 6.194 = **100 %** |
| fechas distintas · meses | 457 · 15 (`2025-03-01` … `2026-05-31`) |
| reparto por proyecto | 53,51 % / 46,49 % |
| confirmación | CONFIRMADA 61,6 · CANDIDATA 19,3 · RECHAZADA 12,0 · SUPRIMIDA 7,1 |
| validez | VIGENTE 66,0 · SUSTITUIDA 15,6 · INVALIDADA 10,2 · SIN_SOPORTE 8,2 |
| disponibilidad | DISPONIBLE 73,5 · ARCHIVADA 12,4 · ELIMINADA 5,8 · PURGADA 5,3 · NO_GUARDADA 3,1 |
| sensibilidad | ORDINARIA 82,0 · RESTRINGIDA 18,0 |
| polaridad | AFIRMATIVA 79,6 · NEGATIVA 20,4 |
| condición presente | 18,4 % |
| temporalidad cerrada (`valid_to`) | 28,7 % |
| items con entidades / procedencia / criticidad | 36,6 % / 40,9 % / 22,0 % |
| entidades con alias | 33,3 % |
| relaciones: tipos · densidad | 6 tipos · 0,327 por item |
| familias temáticas · estructuras gramaticales | 9 · 12 (1.028–1.127 usos cada una) |
| dígitos en el texto | **ninguno**: la variedad no viene de un contador |
| contaminación del léxico protegido | **0 de 6.194** |

Se declara expresamente como **corpus sintético de estrés neutral**. No representa producción.

---

## 6. Pruebas negativas y resultado

Catorce mutaciones sobre copias en memoria de los artefactos, más dos sustituciones del lector canónico. Las catorce se detectan; ninguna toca el árbol de trabajo.

| # | Mutación | Comprobación que la detecta | Resultado |
|---|---|---|---|
| 1 | Tabla DOCX movida o equivocada: la identidad del Anexo B apuntada al contexto del Registro RED, y una identidad ambigua que casa con dos tablas | `TablaCanonicaError: 0 tablas candidatas` y `2 tablas candidatas` | **DETECTADA** |
| 2 | Anexo B vacío | `cargar_canon()` aborta con `filas_anexo_b: 0 (esperado 79)` | **DETECTADA** |
| 3 | Asignación canónica inventada (`RED-099`) | `artefacto -> canon: ninguna asignación marcada canónica fue inventada` + `no se acepta ningún identificador inexistente` | **DETECTADA** |
| 4 | Carácter canónico cambiado en `entrada` | `los cuatro campos canónicos coinciden carácter a carácter con el DOCX` | **DETECTADA** |
| 5 | Campo derivado marcado `CANONICO` (`objetivo`) | `ningún campo de la ficha se marca CANONICO sin texto literal que lo fije` | **DETECTADA** |
| 6 | Rama `M4` eliminada de `CA-09` | `CA-09, CA-10, CA-24 y CA-49 conservan su rama M4` | **DETECTADA** |
| 7 | `CA-47` colapsado (`R2 = R1`) y `CA-47` no cerrado (`R2 = {DEC-014}`) | `el conjunto esperado es exactamente el conjunto elegible calculado`, `las tres ramas producen tres conjuntos distintos y no colapsan`, `R2 incluye DEC-005, DEC-009 y DEC-014…` | **DETECTADA** |
| 8 | Veredicto T0 anticipado en un caso congelable | `ningún artefacto congelable contiene previsión normativa sobre T0` | **DETECTADA** |
| 9 | Conteo real alterado (declaración a 999; un mensaje menos) | `los conteos … se cuentan sobre los datos`; `5.000 mensajes, 500 recuerdos, 50 decisiones y 2 proyectos, contados sobre los datos` | **DETECTADA** |
| 10 | Mensaje, documento y relación ancla alterados (tres mutaciones) | `identidad de items, mensajes, documentos y relaciones intacta` | **DETECTADA** (3/3) |
| 11 | Contaminación por raíz, por sufijo, por alias de entidad y por n-grama (tres textos) | `ningún texto del corpus de rendimiento contamina el léxico protegido` | **DETECTADA** (3/3) |
| 12 | Candidato y tecnología en campo neutral (`ADR002-B`, `vectorial`; `sqlite`, `faiss`) | `ningún campo neutral de un caso nombra tecnología o candidato sin canon que lo fije`; `ni el corpus de rendimiento ni las reglas ni la previsión nombran tecnología o candidato` | **DETECTADA** |
| 13 | Distribución degenerada: todos los textos iguales con número de secuencia | fallan a la vez `textos prácticamente todos distintos`, `vocabulario aproximadamente Zipf`, `longitudes con variación material` y `ningún texto usa un número de secuencia` | **DETECTADA** (4 comprobaciones) |
| 14 | Campo del PDP §7 añadido y eliminado, en el artefacto y en el canon (13 filas) | `cada caso funcional lleva los catorce campos del PDP §7 y la insuficiencia`; `cargar_canon()` aborta con `campos_ficha_pdp7: 13 (esperado 14)` | **DETECTADA** |

---

## 7. Defectos todavía no cubiertos

Se declaran expresamente, sin presentarlos como cerrados.

1. **`ADR002-TOL-207` sigue sin presupuesto.** El paquete lo prohíbe expresamente y la razón material persiste: el presupuesto absoluto de almacenamiento solo puede calcularse midiendo sobre este corpus de rendimiento, y T0 no se ha ejecutado.
2. **`ADR002-TOL-208`, `-209` y `-210` siguen NO SATISFECHAS.** El corpus no está congelado, el protocolo común de medición no fija valores y no hay ficha de candidato congelada.
3. **La neutralidad se comprueba por léxico, no por semántica.** Un caso podría favorecer a un candidato sin nombrar ninguna tecnología —por ejemplo, exigiendo una capacidad que solo una familia de señales puede satisfacer—. Detectarlo exige un análisis de expresabilidad por candidato que este paquete no autoriza y que solo puede hacerse cuando `ADR002-A/B/C/D` existan como especificaciones ejecutables.
4. **La previsión T0 sigue apoyada en una medición registrada, no canónica.** Los estados `AUSENTE/PARCIAL/INSEGURO/EXISTENTE` proceden del Inventario normativo v0.2 §4 del propio repositorio. El fichero de previsión lo declara y es sustituible íntegramente, pero mientras nadie ejecute T0 su fundamento no es verificable contra una fuente aprobada.
5. **Los 12 casos de nivel 2 y 3 no reciben previsión.** Se declaran no proyectados con motivo, porque no trazan a ningún `B04-RF`. Cerrar esto exige un criterio de expresabilidad para obligaciones de ADR-001 y de tolerancias, que no existe todavía.
6. **La cobertura de familias del PDP sigue abierta.** Los cuatro denominadores se reportan sin agregarse porque el mínimo canónico por familia del PDP §8 exige ejecutar los casos asignados del banco de 304, y ADR-002 no los ejecuta. Ninguna cifra de este trabajo debe leerse como cobertura de familia.
7. **El corpus de conformidad conserva 29 colisiones por raíz entre anclajes de proyectos distintos.** Están declaradas y verificadas por igualdad exacta, pero son léxicamente reales: si un candidato usara una raíz de 6 caracteres como unidad de indexación, algunas podrían producir recuperación cruzada legítima que el corpus no distingue de un fallo. Resolverlo exige rediseñar anclajes canónicos, que este paquete no autoriza.
8. **La banda de Zipf es una comprobación de forma, no de identidad.** La pendiente `−0,796` cae dentro de `[−1,45, −0,55]`; la banda es amplia a propósito y no demuestra que la distribución sea la de un corpus real. No se afirma que lo sea.
9. **La independencia de los dos corpus no se ha medido.** Se comprueba que no comparten léxico y que el de rendimiento no crea referencias funcionales; no se ha demostrado experimentalmente que añadir volumen no altere ninguna respuesta canónica, porque eso exige ejecutar recuperación y no está autorizado.

---

## 8. Archivos creados

**Código y artefactos** (`experiments/adr002/benchmark/`)

| Fichero | Qué es |
|---|---|
| `canonical_source_v0_3.py` | lector canónico por identidad de tabla, invariantes y Anexo B bidireccional |
| `schema_v0_3.py` | contrato v0.3: campos, tolerancias, distribución, contaminación, neutralidad |
| `build_corpus_v0_3.py` | generador: léxico protegido, corpus de conformidad, corpus de rendimiento sintético, casos, referencias, reglas del arnés, previsión T0 y manifiesto |
| `validate_corpus_v0_3.py` | validador no mutante, con 98 comprobaciones |
| `test_corpus_contract_v0_3.py` | 50 pruebas, de las que 14 son las mutaciones negativas del §7.3 |
| `conformance_corpus_v0_3.json` | 94 anclajes, cierre de `CA-47`, identidad por elemento, colisiones declaradas |
| `performance_corpus_v0_2.json` | 5.000 mensajes, 500 recuerdos, 50 decisiones, 2 proyectos, distribución observada |
| `cases_v0_3.json` | 50 `B04-CA` + 2 `PDP-CA` funcionales, ficha de 14 campos, 19 ramas |
| `references_v0_3.json` | 50 referencias con fuente por campo, tolerancias y cierre exhaustivo |
| `pdp_cases_v0_2.json` | clasificación de los 28 `PDP-CA` y cuatro denominadores de familias |
| `pdp_harness_rules_v0_1.json` | las 6 reglas canónicas de protocolo del arnés |
| `t0_preexecution_projection_v0_1.json` | previsión no normativa, no congelable, sustituible |
| `benchmark_manifest_v0_3.json` | manifiesto v0.3 con huellas, inventario de tablas y distribución |

**Documentación**

- `docs/architecture/SIRIUS_0.2_ADR_002_MATRIZ_CANONICA_BENCHMARK_v0.3_PROPUESTO.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_CORPUS_BENCHMARK_v0.3_PROPUESTO.md`
- `artifacts/adr002_benchmark_preparation/validacion_corpus_v0.3.json`
- `artifacts/adr002_benchmark_preparation/INFORME_ENDURECIMIENTO_CORPUS_v0.3_PROPUESTO.md` (este documento)

No se ha modificado ningún fichero de `docs/architecture/canonical_sources/`, `src/`, `tests/`, `migrations/` ni configuración productiva. Ningún artefacto v0.1 o v0.2 ha cambiado.

---

## 9. Pruebas ejecutadas

| Comprobación | Resultado |
|---|---|
| `validate_corpus_v0_3` | **98 comprobaciones, 0 fallos** |
| `validate_corpus_v0_2` (conservación histórica) | **62 comprobaciones, 0 fallos** |
| `validate_corpus` (v0.1) | **33 comprobaciones, 0 fallos** |
| `pytest experiments/adr002/benchmark/` | **171 pruebas, 0 fallos** (50 nuevas del contrato v0.3) |
| `ruff format experiments/adr002/benchmark/` | sin cambios pendientes |
| `ruff check experiments/adr002/benchmark/` | **All checks passed** |
| Doble regeneración en directorio temporal | byte a byte idéntica entre sí y con lo comprometido |
| Validador no mutante | instantánea de bytes y fechas idéntica antes y después |
| Pruebas negativas | **14 de 14 detectadas** |
| Análisis de distribución | §5 de este informe |

La suite productiva no se ejecuta: este trabajo no toca código productivo.
