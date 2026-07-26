# SIRIUS 0.2 — ADR-002 · Informe de preparación del corpus

**Versión:** 0.1
**Estado:** **PROPUESTO** · informe de ejecución, no aprueba ni decide nada
**Fecha:** 26 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Evidencia legible por máquina:** `artifacts/adr002_benchmark_preparation/validacion_corpus.json`
**Código:** `experiments/adr002/benchmark/`
**No autoriza:** ejecutar T0 ni T1–T4, implementar candidatos, elegir realización técnica ni merge.

---

## 1. Qué se ha hecho y qué no

**Hecho:** extraer literalmente el contrato canónico de las tres fuentes materializadas el 26 de julio de 2026, instanciar los cincuenta casos de aceptación como corpus ejecutable determinista, validarlo contra el contrato y medir el entorno de laboratorio para proponer `TOL-207`.

**No hecho, y deliberadamente:** ejecutar T0, ejecutar T1–T4, implementar ningún candidato, modificar Sirius 0.1, medir rendimiento alguno o tocar `canonical_sources/`.

### 1.1 Fuentes usadas

Leídas íntegras desde `docs/architecture/canonical_sources/`, cuyas huellas verifica el `MANIFEST.md`:

| Fuente | Aportó |
|---|---|
| **B04 v1.0 APROBADO** | RF-01–32 · **CA-01–50 con riesgo, entrada, resultado esperado y fallo observable** · M01–21 con fórmula y umbral · D01–16 · modos M1–M5 · etapas E0–E5 · puertas G1–G12 · paradas S1–S7 · cardinalidad · taxonomía de ausencia · contrato de criticidad |
| **Plan de Pruebas + RED/PDP v1.0 APROBADO** | RED-001–079, incluidas **RED-027–034** y RED-040 · **familias F01–F25 con su cobertura mínima** · ficha obligatoria de caso · protocolo de ejecución · puertas absolutas · PDP-M01–M17 |
| **ARQ-00 v1.0 APROBADO** | §10 campos obligatorios del Registro de Tolerancias · **§23 alternativas de ADR-002** · mapa de decisiones |

**Ningún texto ausente se ha reconstruido por analogía.** Donde el canon no fija algo, la matriz lo declara como no fijado.

---

## 2. Cobertura exacta obtenida

| Serie | Cubierto | Denominador | Ausencias | Duplicados |
|---|---|---|---|---|
| **B04-CA-01 … CA-50** | **50** | 50 | **0** | **0** |
| **B04-RF-01 … RF-32** | **32** | 32 | **0** | — |
| **B04-M01 … M21** | **21** | 21 | **0** | — |
| **RED-027 … RED-034** | **8** | 8 | **0** | — |
| Familias PDP · nivel 1 | 18 | 25 | 7 | — |
| Familias PDP · los tres niveles | **20** | 25 | 5 | — |

**Las cinco familias restantes no son una laguna de ADR-002.** `F16` (carga e interrupciones), `F17` (continuidad), `F18` (ciclo de vida), `F19` (control y matriz de catorce operaciones) y `F20` (exportación y reimportación) pertenecen a B03, B06, B07 y B08. `PDP-M03` exige 25/25 para cerrar el **Plan de Pruebas completo**, no el benchmark de ADR-002. Contarlas como cubiertas aquí sería falsear la cobertura.

**`RED-040` no se usa como requisito propio de selección técnica**, conforme al Inventario normativo §7 y al propio Plan: pertenece a B05/ADR-003B. Una prueba automática lo verifica.

### 2.1 Tres anclajes corregidos por evidencia canónica

Tras la primera construcción, `RF-03`, `RF-04` y `RF-29` quedaban sin ningún caso. No se resolvió inventando casos ni forzando etiquetas, sino localizando el anclaje que el canon ya fija:

| RF | Anclaje | Fuente del anclaje |
|---|---|---|
| `RF-03` · adjudicar modo antes de recuperar | **CA-09, CA-15** | `RED-027` mapea RF-01–04 a CA-01/05/08/15; en ambos casos el modo decide la elegibilidad |
| `RF-04` · aclaración mínima ante ambigüedad material | **CA-07, CA-14** | Texto canónico: «Parcial o **aclaración**» y «**Aclara** o devuelve grupos separados» |
| `RF-29` · plan reproducible | **CA-40, CA-44** | `RED-029` mapea RF-18/RF-29 a CA-40/44 |

---

## 3. Estructura y tamaño del corpus

| Colección | Elementos |
|---|---|
| Proyectos | 7, incluida una **lista multi-proyecto cerrada** |
| Entidades | 5, con **dos homónimos no fusionables** y alias confirmados |
| Elementos de conocimiento | **92** = 52 significativos + 40 de ruido determinista |
| Mensajes (historial, evidencia de E4) | 6 |
| Documentos | 5, **uno inaccesible** |
| Relaciones | 9 (apoyo, refutación, conflicto, corrección, sustitución, alias, origen de candidata) |
| Casos | **50** nivel 1 · **5** nivel 2 · **7** ablaciones |
| Referencias congeladas | **50**, una por caso canónico, todas `"modificable": false` |

| Fichero | Bytes |
|---|---|
| `corpus_v0_1.json` | 77.362 |
| `cases_v0_1.json` | 84.541 |
| `references_v0_1.json` | 26.460 |
| Paquete completo `experiments/adr002/benchmark/` | 476.560 |

---

## 4. Casos ejecutables y no ejecutables por T0

| Clase | Casos | CA |
|---|---|---|
| **Ejecutable y debería pasar** | **3** | CA-04, CA-11, CA-39 |
| **Ejecutable con fallo esperado** | **6** | CA-01, CA-17, CA-19, CA-21, CA-30, CA-41 |
| **Ejecutable con fallo duro** | **5** | CA-02, CA-20, CA-25, CA-40, CA-42 |
| **No expresable por la línea base** | **36** | los 36 restantes |
| **Total** | **50** | ninguno eliminado |

**Los 36 no expresables se conservan y se marcan como incapacidad de la línea base**, conforme al principio 6 de la Especificación de benchmark. Los 5 de fallo duro son exactamente los tres hallazgos inseguros ya medidos: **ámbito** (RF-06, CA-02 y CA-25), **negación** (RF-19, CA-20 y CA-42) y **salto a recuperación amplia** (RF-14, CA-40).

**Lectura honesta:** 14 de 50 casos son ejecutables contra T0 y la línea base pasa 3. No es un defecto del corpus: es la distancia medida entre Sirius 0.1 y el contrato B04, y coincide con el inventario normativo (1 `EXISTENTE`, 11 `PARCIAL`, 17 `AUSENTE`, 3 `INSEGURO`).

---

## 5. Validación ejecutada

### 5.1 Resultados

| Comprobación | Resultado |
|---|---|
| **Validador del corpus** — 33 comprobaciones | **33 OK · 0 fallos · veredicto `VALIDO`** |
| **pytest** sobre `experiments/adr002/benchmark` | **44 pasan · 0 fallan** |
| **Ruff format** | **6 ficheros sin cambios** |
| **Ruff check** | **All checks passed!** |
| CA-01–50 sin ausencias ni duplicados | **OK** — 50 exactamente una vez |
| Trazabilidad a RF, M, familia y RED | **OK** — ningún identificador fuera del canon |
| Regeneración determinista byte a byte | **OK** — el validador reejecuta el generador y compara |
| `git status` | **limpio salvo las rutas autorizadas** |

**La suite productiva completa no se ha ejecutado**: no se ha modificado código productivo.

### 5.2 Una violación del contrato detectada antes de publicar

La primera versión marcaba **CA-02, CA-22, CA-39 y CA-47** como `EXHAUSTIVA` con parada `S1`. B04 §15.2 lo prohíbe expresamente —«`EXHAUSTIVA`: **S1 deshabilitado**»—. El validador lo detectó; los cuatro pasan a **`S5` · agotamiento autorizado**. La comprobación queda permanente en el validador y en una prueba de contrato.

Se registra porque es la prueba de que la validación no es decorativa.

---

## 6. Propuesta TOL-207 · resumen

Medición del entorno **antes** de proponer ninguna cifra. Detalle completo en `SIRIUS_0.2_ADR_002_TOL_207_PRESUPUESTO_ALMACENAMIENTO_v0.1_PROPUESTO.md`.

### 6.1 Entorno medido

| Magnitud | Bytes |
|---|---|
| Sistema de ficheros total (`/dev/vda`, ext4) | 270.553.174.016 |
| **Disponible para el proceso** (`f_bavail`) | **31.304.323.072** (29,15 GiB) |
| Escritura real verificada | 67.108.864, sin error |
| Repositorio sin `.venv` | 7.032.692 |
| Contenido versionado (412 ficheros) | 3.990.571 |
| `experiments/` · `artifacts/` | 713.773 · 231.261 |
| **Derivados experimentales existentes** (2 índices FTS5) | **364.544** |
| Densidad léxica medida | **223,83 B por elemento** |

`df` induce a error en este entorno: la cuota es por sesión. La cifra que gobierna es `f_bavail`, confirmada con una escritura real de 64 MiB.

### 6.2 Cifra propuesta

| Nivel | Presupuesto | Bytes | % del disponible |
|---|---|---|---|
| **Por candidato** | **1,5 GiB** | 1.610.612.736 | 5,15 % |
| **Agregado** (T0 + T1–T4 co-residentes) | **8 GiB** | 8.589.934.592 | 27,43 % |

**Derivación:** de los 31.304.323.072 B disponibles se reserva el **50 % intocable** (15.652.167.680) y **6 GiB operativos** (repositorio, artefactos, evidencia, `.venv` y las copias limpias que exigen las ≥30 repeticiones del ciclo). Quedan 8 GiB asignables. 1,5 GiB × 5 candidatos = 8.053.063.680 B, que caben con 536 MB de holgura. **Se reserva el 70,58 % y se asigna el 29,42 %: no se usa todo el espacio libre.**

**El presupuesto es común y no lo elige el candidato.** `TOL-104A` permite que cada uno declare un límite **más estricto**, nunca más laxo; los dos techos son acumulativos.

### 6.3 Proyección común

| | 500 | 5.000 | 50.000 |
|---|---|---|---|
| Sustrato léxico FTS5, bytes | 111.913 | 1.119.126 | 11.191.257 |
| % del presupuesto por candidato | 0,007 % | 0,069 % | 0,695 % |
| Índices semánticos y relacionales | *a declarar* | *a declarar* | *a declarar* |

La fila léxica es **extrapolación lineal de una medición**, declarada como tal. Para índices semánticos y relacionales **no se rellena ninguna casilla**: no existe medición y no se inventa una aritmética que pareciera evidencia.

### 6.4 Consecuencia de superarlo

Incumplir el presupuesto propio o el común **descarta por la puerta 7** vía §5.1 criterios 1 y 3 del Registro. Superar el agregado co-residente **invalida la ejecución** y obliga a repetir. Ajustar el presupuesto **después** de observar resultados está prohibido por el §9 regla 1.

### 6.5 Alcance y advertencia

**`LAB-LINUX`. No es aceptación Windows.** Cuánto puede ocupar Sirius en el equipo del usuario pertenece a `ADR002-TOL-205` y sigue sin fijarse.

**Advertencia honesta:** con 29 GiB disponibles, 1,5 GiB por candidato es ~4.400 veces los derivados medidos hoy. **En el laboratorio el almacenamiento casi no separará candidatos.** `TOL-207` cierra el vacío y hace operativo el criterio 3, pero **no debe presentarse como prueba de que el coste de almacenamiento es aceptable**: esa prueba es la de `TOL-205` sobre Windows, previsiblemente uno o dos órdenes de magnitud más estricta, y es la que morderá.

---

## 7. Cuestión abierta que precede a la ejecución

**ARQ-00 §23 y ADR-002 v0.2 §3 no usan la misma partición de candidatos.**

- **ARQ-00 v1.0 APROBADO** §23: **A** solo léxica · **B** con señal **semántica** tardía · **C** con señal **relacional** tardía · **D** ambas en etapas distintas.
- **ADR-002 v0.2 ABIERTO** §3: **T1–T4** por *sustrato léxico* (FTS5 o alternativo) × *relaciones* (desde el canon o índice derivado), con señal semántica **común a las cuatro** porque B04-RF-17 la impone.

La segunda es coherente con RF-17; la primera es la aprobada en ARQ-00. **El corpus es neutral respecto de ambas** —traza a RF, CA, M y RED, nunca a T1–T4 ni a A–D—, así que ninguna decisión queda comprometida. Pero el número y la naturaleza de las **fichas de candidato** (`TOL-210`) dependen de cuál se adopte, y esa decisión precede a la ejecución.

**No se resuelve aquí.** Se registra para el usuario.

---

## 8. Estado de las puertas de arranque

| Puerta | Antes | Después |
|---|---|---|
| `SRC-ADR002-01` · fuentes canónicas | SATISFECHA | **SATISFECHA** |
| `ADR002-TOL-207` · presupuesto absoluto | NO SATISFECHA | **PROPUESTA · pendiente de aprobación** |
| `ADR002-TOL-208` · corpus congelado y T0 rederivada | NO SATISFECHA | **NO SATISFECHA** — el corpus es `v0.1 PROPUESTO`, no congelado; **T0 no se ha ejecutado** |
| `ADR002-TOL-209` · protocolo común | NO SATISFECHA | **NO SATISFECHA** — falta congelar con el entorno el umbral de conmutación y la banda absoluta de TOL-107 |
| `ADR002-TOL-210` · ficha de candidato | NO SATISFECHA | **NO SATISFECHA** — plantilla lista; sin candidato y sin partición decidida |

**El benchmark sigue bloqueado.** Esta ronda avanza una puerta a estado propuesto y deja construido lo que `TOL-208` necesitará.

---

## 9. Rutas tocadas

**Añadido:** `experiments/adr002/benchmark/` · `artifacts/adr002_benchmark_preparation/` · tres documentos en `docs/architecture/`.

**Sin cambios, verificado:** `src/`, `tests/`, `migrations/`, configuración productiva, `docs/architecture/canonical_sources/` y todos los documentos anteriores.

---

## 10. Reproducción

```
uv run python -m experiments.adr002.benchmark.build_corpus
uv run python -m experiments.adr002.benchmark.validate_corpus
uv run pytest experiments/adr002/benchmark -q
uv run ruff format --check experiments/adr002/benchmark
uv run ruff check experiments/adr002/benchmark
```

---

**Siguiente movimiento único:** que el usuario revise la matriz, el corpus y la propuesta `TOL-207`, y resuelva la partición de candidatos de la §7. Hasta entonces el corpus no se congela, T0 no se rederiva y no se ejecuta ningún candidato.
