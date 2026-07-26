# SIRIUS 0.2 — ADR-002 · Corpus ejecutable del benchmark

**Versión:** 0.2
**Estado:** **PROPUESTO · NO CONGELADO**
**Fecha:** 26 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_ADR_002_CORPUS_BENCHMARK_v0.1_PROPUESTO.md`, que **se conserva sin modificar**
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_03B_CORRECCION_CORPUS_CANONICO_v0.1.md`
**Código:** `experiments/adr002/benchmark/`
**Evidencia legible por máquina:** `artifacts/adr002_benchmark_preparation/validacion_corpus_v0.2.json`
**No autoriza:** congelar `ADR002-TOL-208`, ejecutar T0, implementar o ejecutar `ADR002-A/B/C/D`, aprobar `ADR002-TOL-207`, satisfacer `ADR002-TOL-209` o `ADR002-TOL-210`, ni merge.

---

## 0. Qué se ha construido

**Dos corpus vinculados**, no uno. La auditoría demostró que un solo corpus no puede servir a dos objetivos incompatibles: 92 elementos son suficientes para adjudicar comportamiento y ridículos para medir latencia, y las cifras `LAB-LINUX` del Registro de Tolerancias se midieron sobre **5.000 mensajes, 500 recuerdos y 50 decisiones**.

| Artefacto | Fichero | Bytes |
|---|---|---|
| Corpus de **conformidad** | `conformance_corpus_v0_2.json` | 79.558 |
| Corpus de **rendimiento** | `performance_corpus_v0_1.json` | 1.896.950 |
| Casos, con ramas y ficha PDP §7 | `cases_v0_2.json` | 529.119 |
| Referencias, canon e instanciación separados | `references_v0_2.json` | 163.758 |
| `PDP-CA` aplicables y matriz de exclusión | `pdp_cases_v0_1.json` | 15.117 |
| Manifiesto que declara la relación | `benchmark_manifest_v0_2.json` | 4.948 |

**Los tres artefactos v0.1 se conservan intactos** y su contrato sigue verificándose: el validador v0.2 lo comprueba expresamente.

---

## 1. Corpus de conformidad

**Propósito declarado en el propio artefacto:** adjudicar puertas, exactitud, contaminación, negación, ámbito, tiempo, conflicto, ausencia y explicación. **No se usa para fijar cifras de rendimiento absoluto.**

| Colección | v0.1 | **v0.2** |
|---|---|---|
| Proyectos | 7, con lista multi-proyecto cerrada | **7** |
| Entidades | 5, con dos homónimos y alias | **5** |
| Elementos de conocimiento | 92 | **94** = 79 recuerdos + 15 decisiones |
| Mensajes (evidencia de E4) | 6 | **6** |
| Documentos | 5, uno inaccesible | **5** |
| Relaciones | 9 | **9** |

### 1.1 Los dos anclajes añadidos, y por qué

El §3.1 del paquete 03B autoriza ajustar el corpus «para hacer falsables las ramas canónicas». Se añaden **dos decisiones y solo dos**, declaradas en el propio artefacto con su motivo:

| Id | Motivo |
|---|---|
| `DEC-014` | `B04-CA-47` exige que las consultas por `occurred_at`, tiempo válido y `recorded_at` devuelvan resultados **distintos**. Con un solo elemento, el fallo canónico «colapsa las tres fechas en "más reciente"» es indetectable por construcción |
| `DEC-015` | Ídem: hacen falta tres elementos con ejes cruzados para que los tres conjuntos esperados sean distintos |

**Ningún elemento existente se ha modificado ni eliminado.** El artefacto declara `items_heredados_v0_1: 92` y `items_anadidos_v0_2: 2`, y una prueba comprueba que los añadidos son exactamente esos dos.

### 1.2 Fenómenos exigidos

Los veintitrés fenómenos que el validador v0.1 exigía siguen presentes y se vuelven a comprobar con el mismo código: negación, condición, apoyo, refutación, conflicto, corrección, sustitución, homónimos, alias ambiguos, eliminado/purgado, no guardado, archivado, restringido, no usar como memoria, no consolidable, sin soporte, candidata, rechazada, fuente inaccesible, separación por proyecto, lista multi-proyecto cerrada, tiempo válido frente a registro y tres ejes temporales distintos.

---

## 2. Corpus de rendimiento

**Propósito declarado:** latencia, tamaño, construcción, reconstrucción y estabilidad **a la escala del corpus que produjo las cifras `LAB-LINUX`**. No crea referencias funcionales y no sustituye al corpus de conformidad.

### 2.1 Escala alcanzada

| Magnitud | Escala de referencia de `ADR002-TOL-208` | **Alcanzada** |
|---|---|---|
| Mensajes | 5.000 | **5.000** |
| Recuerdos | 500 | **500** |
| Decisiones | 50 | **50** |
| Elementos totales | 550 | **550** |
| Longitud media del texto | — | 85,11 caracteres (mín. 34 · máx. 105) |

### 2.2 Regla de proyección, declarada y reproducible

```
recuerdos(N)  = N
decisiones(N) = N // 10
mensajes(N)   = N * 10
```

Con `N = 500` produce **exactamente** la escala de referencia: el corpus de referencia es un punto de la curva, no un caso especial. Las escalas proyectables declaradas son **500 / 5.000 / 50.000**, las tres que `ADR002-TOL-104A` obliga a reportar. El generador acepta la escala como parámetro; **solo se materializa la de referencia**, porque ninguna cifra de rendimiento está autorizada todavía.

### 2.3 Por qué el volumen no altera ninguna respuesta canónica

Tres garantías, las tres comprobadas automáticamente:

1. **Los anclajes viajan sin alterar.** Los 94 elementos del corpus de conformidad están en el de rendimiento **byte a byte idénticos**. Una prueba compara cada uno.
2. **El relleno vive en un proyecto reservado**, `PRJ-VOLUMEN`, que no aparece en el ámbito de ningún caso canónico.
3. **El relleno usa vocabulario disjunto.** Ninguno de los 26 términos de anclaje —`atlas`, `juan`, `coche`, `presupuesto`, `escala`, `nimbo`, `aforo`, `nómina`, `almacén`, `migración`, `faro`…— aparece en ningún texto de volumen. El validador lo comprueba sobre los 4.994 mensajes y los 456 elementos de relleno.

**Esta comprobación no es decorativa:** la primera versión del generador usaba el tema «programación de mantenimiento menor» y el validador rechazó **643 elementos** por contener «mantenimiento», que es un anclaje de `CA-07`.

### 2.4 Prohibición cruzada

El manifiesto la declara literalmente: **prohibido fijar cifras de rendimiento sobre el corpus de conformidad y prohibido adjudicar conformidad sobre el corpus de rendimiento.** Los dos comparten versión de contrato `0.2`, semilla `20260726` y anclajes; cambiar cualquiera exige nueva versión explícita de ambos.

---

## 3. Disciplina del corpus

Sin cambios respecto de la v0.1, y verificada de nuevo:

- **Sintético y determinista.** Ningún dato real, ningún secreto, ninguna URL, ninguna llamada de red.
- **Semilla fija** `20260726`, compartida por los dos corpus.
- **Sin dependencia del reloj.** El «ahora» es el dato declarado `2026-06-15T00:00:00Z`.
- **Siete dimensiones ortogonales** de ADR-001, ninguna condensada en un enum.
- **Toda marca crítica** lleva nivel, razón, fuente y regla aprobada (B04 §6).
- **Regeneración doble byte a byte idéntica**, comprobada en cada ejecución del validador.

---

## 4. Trazabilidad · el Anexo B manda

| Eje | Cobertura | Cómo se verifica |
|---|---|---|
| `B04-CA-01`–`CA-50` | **50/50**, exactamente una vez | contra la tabla §17/§17.1 del DOCX |
| `B04-RF-01`–`RF-32` | **32/32** | pertenencia y presencia |
| `B04-M01`–`M21` | **21/21** | canónicas del Anexo B + adicionales del arnés, separadas |
| `RED-027`–`RED-034` | **8/8** | asignación exacta del Anexo B, no solo cita |
| `PDP-CA` | **8 aplicables / 20 excluidos / 28 totales** | extracción del DOCX y clasificación sin hueco |
| Familias PDP | **cuatro denominadores**, sin agregar | ARQ-00 §20 del DOCX |

Las cuatro asignaciones canónicas que la v0.1 perdió —`CA-05` y `CA-08` de `RED-027`, `CA-44` de `RED-029`, `CA-24` de `RED-034`— quedan restituidas, junto con las métricas `M13`, `M15`, `M10` y `M21` que faltaban en los casos que el Anexo B les asigna. Lo que el arnés añade se etiqueta `..._adicional_derivada` y **no cuenta como cumplimiento del Anexo B**.

---

## 5. Separación de niveles, canon e instanciación

**Nivel 1 · canónico y no reescrito.** Los cuatro campos que B04 §17/§17.1 fija —riesgo, entrada, resultado esperado y fallo observable— se leen del DOCX y se comparan **carácter a carácter**. El bloque `canonico` es `modificable: false` y contiene **solo esos cuatro** más su fuente y su sección exacta.

**Nivel 1 · instanciación declarada.** Cardinalidad, consulta, modo, propósito, permiso, ámbito, tiempos, etapa, parada, orden, elegibles, prohibidos y explicación viven en `instanciacion`, cada uno con su **fuente individual** y su estado. Solo se marca `CANONICO` lo que el texto canónico del propio caso nombra: **6 modos, 6 etapas, 2 paradas y 1 cardinalidad** de los 50 casos.

**Ninguna referencia canónica se ha cambiado para facilitar T0.** El reparto de previsión lo demuestra: **30 de 50** casos se prevén no expresables y **1** no ejecutable con una sola implementación. Habría sido trivial ablandarlos; no se ha hecho. Y ahora, además, **no hay ningún veredicto**: `estado_t0` es `NO_MEDIDO` en los cincuenta.

**Nivel 2 · sin cambios.** Los cinco casos arquitectónicos de la v0.1 se conservan tal cual: B04 excluye almacenamiento (§3) y esos casos no pueden existir en él.

**Nivel 3 · sin cambios y sin ficha.** Las siete ablaciones no llevan ficha de caso del PDP §7: el canon dice que nunca producen veredicto de conformidad. `AB-4` sigue siendo la más informativa —separa la señal de la validación de polaridad—, y `AB-3`/`AB-4` **no aplican a `ADR002-A`**, sin que eso lo penalice.

---

## 6. El validador lee los DOCX

La diferencia de fondo con la v0.1. El validador v0.1 comprobaba **coherencia interna**: los identificadores pertenecían a una lista blanca escrita en `schema.py`. Los cuatro defectos bloqueantes de la auditoría **pasaban sus 33 comprobaciones sin inmutarse**.

El validador v0.2 abre los tres `.docx` con `zipfile` y `xml.etree` de la biblioteca estándar —**sin añadir ninguna dependencia**— y comprueba:

| # | Comprobación |
|---|---|
| 1 | SHA-256 de las tres fuentes contra `MANIFEST.md`, y tamaño del canon extraído |
| 2 | Los 50 CA, exactamente una vez, sin ausencias, duplicados ni ajenos |
| 3 | Riesgo, entrada, resultado esperado y fallo observable **carácter a carácter**, en casos y en referencias |
| 4 | Asignaciones `RED↔CA↔M↔F` del Anexo B, y que lo derivado no se solape con lo canónico |
| 5 | Ramas canónicas: todo modo que el canon nombra, las cuatro ramas `M4` exigidas, `M1`–`M5` presentes, tres ramas distinguibles en `CA-36`/`47`/`48`, tres conjuntos distintos en `CA-47`, par diferencial en `CA-48` |
| 6 | Los catorce campos del PDP §7 más la condición de insuficiencia, y tolerancias pendientes declaradas sin inventarlas |
| 7 | Separación canon/instanciación y que ningún campo derivado se atribuya a §17 |
| 8 | La regla `EXHAUSTIVA → S1 deshabilitado` leída del DOCX, y que nada se marque `CANONICO` sin estar nombrado |
| 9 | Ausencia de todo veredicto frente a T0 y criterio de expresabilidad único |
| 10 | `PDP-CA` clasificados sin hueco, con criterio o responsable, y literales |
| 11 | Fenómenos, dimensiones y criticidad del corpus de conformidad |
| 12 | Consistencia entre los dos corpus: escala exacta, anclajes intactos, relleno aislado, prohibición cruzada |
| 13 | Contrato v0.1 intacto y **regeneración doble byte a byte** |

**62 comprobaciones · 0 fallos · veredicto `VALIDO`.**

Las **121 pruebas** de `experiments/adr002/benchmark/` incluyen las 44 del contrato v0.1, sin cambios, y 77 nuevas del contrato v0.2.

---

## 7. Cómo se reproduce

```
uv run python -m experiments.adr002.benchmark.build_corpus_v0_2      # los seis artefactos v0.2
uv run python -m experiments.adr002.benchmark.validate_corpus_v0_2   # 62 comprobaciones contra los DOCX
uv run pytest experiments/adr002/benchmark -q                        # 121 pruebas de contrato
uv run ruff format --check experiments/adr002/benchmark
uv run ruff check experiments/adr002/benchmark
```

El generador v0.1 sigue funcionando y produciendo sus mismos bytes:

```
uv run python -m experiments.adr002.benchmark.build_corpus
uv run python -m experiments.adr002.benchmark.validate_corpus       # 33 comprobaciones, sin cambios
```

**No se ha ejecutado la suite productiva completa**: no se ha tocado código productivo. `src/`, `tests/`, `migrations/`, `canonical_sources/`, los artefactos v0.1 y la configuración quedan intactos.

---

## 8. Lo que falta antes de poder ejecutar

| Puerta | Estado |
|---|---|
| `SRC-ADR002-01` · fuentes canónicas completas | **SATISFECHA** |
| `ADR002-TOL-207` · presupuesto absoluto | **NO SATISFECHA** — hallazgo **M-06** abierto; esta ronda no la aprueba ni la modifica |
| `ADR002-TOL-208` · corpus congelado y T0 rederivada | **NO SATISFECHA** — el corpus está corregido pero **no congelado**, y **T0 no se ha ejecutado** |
| `ADR002-TOL-209` · protocolo común | **NO SATISFECHA** — faltan los valores del entorno, entre ellos las bandas que `CA-37`, `CA-39` y `CA-48` declaran pendientes |
| `ADR002-TOL-210` · ficha de candidato | **NO SATISFECHA** — no hay ninguna ficha emitida |

**El benchmark sigue bloqueado.** Esta ronda retira el **defecto material** que impedía plantear `TOL-208`; no satisface la puerta.

### 8.1 Dependencias que el propio corpus declara

Tres casos no son adjudicables hasta que `ADR002-TOL-209` congele los valores del entorno, y lo declaran en su ficha en vez de inventar la banda:

| Caso | Qué falta | Dependencia |
|---|---|---|
| `CA-37`, `CA-48` | Banda de texto, estado, conteo y tiempo entre ausencia real y no reportable | `RED-032` · `B04-RF-26` · `TOL-209` |
| `CA-39` | Clase de equivalencia de orden entre implementaciones | `RED-033` · `TOL-209` |

Y una dependencia **sin fuente conocida**: la regla de muestreo de `B04-M14` («100 % de la muestra auditada») **no consta en ninguna de las tres fuentes canónicas**. El corpus no la inventa.

---

**Siguiente movimiento único:** que el usuario revise la corrección y decida si el corpus de conformidad puede congelarse. Hasta entonces el corpus no se congela, T0 no se rederiva, no se emite ninguna ficha de candidato y no se ejecuta ningún candidato.
