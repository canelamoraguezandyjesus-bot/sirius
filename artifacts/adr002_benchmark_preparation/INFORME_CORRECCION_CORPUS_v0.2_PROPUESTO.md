# SIRIUS 0.2 — ADR-002 · Informe de corrección del corpus

**Versión:** 0.2
**Estado:** **PROPUESTO** · informe de ejecución, no aprueba ni decide nada
**Fecha:** 26 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_03B_CORRECCION_CORPUS_CANONICO_v0.1.md`
**Entrada adicional:** auditoría adversarial independiente del corpus v0.1 · hallazgos B-01–B-04 y M-01–M-07
**Evidencia legible por máquina:** `artifacts/adr002_benchmark_preparation/validacion_corpus_v0.2.json`
**Código:** `experiments/adr002/benchmark/`
**Conserva sin modificar:** `INFORME_PREPARACION_CORPUS_v0.1_PROPUESTO.md` y `validacion_corpus.json`
**No autoriza:** congelar `ADR002-TOL-208`, ejecutar T0, implementar o ejecutar `ADR002-A/B/C/D`, aprobar `ADR002-TOL-207`, satisfacer `ADR002-TOL-209` o `ADR002-TOL-210`, ni merge.

---

## 1. Qué se ha hecho y qué no

**Hecho:** corregir los defectos de fidelidad canónica del corpus v0.1 **sin rehacerlo**, separar el corpus de conformidad del de rendimiento, y sustituir un validador de coherencia interna por uno que **lee las fuentes DOCX y compara**.

**No hecho, y deliberadamente:** ejecutar T0, ejecutar o implementar `ADR002-A/B/C/D`, congelar nada, aprobar `ADR002-TOL-207`, tocar `canonical_sources/`, tocar código productivo, o modificar cualquier artefacto v0.1.

---

## 2. Cierre de cada hallazgo

### B-01 · asignaciones `RED↔CA↔M↔F` del Anexo B · **CERRADO**

El Anexo B ya no se transcribe: **se lee del DOCX** en cada ejecución y se compara. Las cuatro asignaciones perdidas quedan restituidas, y con ellas las métricas canónicas que faltaban en los casos que el Anexo B les asigna:

| Fila | Restituido | Métrica canónica restituida |
|---|---|---|
| `RED-027` | `B04-CA-05`, `B04-CA-08` | `B04-M13`, `B04-M15` en CA-01, 05, 08, 15 |
| `RED-029` | `B04-CA-44` | `B04-M15` en CA-44 |
| `RED-030` | — | `B04-M10` en CA-31 y CA-38 |
| `RED-034` | `B04-CA-24` | `B04-M21` en CA-18 y CA-24 |
| `RED-028` | — | familias F02/F03 en CA-06 y CA-07 |

Las asociaciones que el arnés añade se conservan como `traza_red_adicional_derivada` y `metrica_adicional_derivada`. Una comprobación verifica que **los dos conjuntos no se solapan**. Veinte de los cincuenta CA están nombrados por el Anexo B; para ellos la asignación es obligatoria y el validador la exige caso por caso.

### B-02 · inferencias etiquetadas como canon · **CERRADO**

Cada caso y cada referencia tienen dos bloques. `canonico` contiene **solo** riesgo, entrada, resultado esperado y fallo observable, más su fuente y su sección exacta, y es `modificable: false`. `instanciacion` es `modificable: true`, declara `estado: PROPUESTO_NO_CONGELADO` y registra la **fuente individual de cada campo**.

Regla de marcado, comprobada contra el DOCX: un campo solo es `CANONICO` si el texto canónico de ese mismo caso **nombra literalmente el valor**. Resultado en los 50 casos: **6 modos, 6 etapas, 2 paradas y 1 cardinalidad**. Una comprobación rechaza cualquier campo `DERIVADO_PROPUESTO` cuya fuente cite `§17`.

### B-03 · clasificación T0 presentada como resultado · **CERRADO**

Desaparece `ejecutable_por_t0`. En su lugar, en los 50 casos y en los 8 `PDP-CA`:

```
estado_t0: "NO_MEDIDO"   ·   no_es_veredicto: true
expresabilidad_prevista + fundamento_de_prevision + estado_por_requisito
```

**Criterio único**, sin excepciones: alguna dimensión `AUSENTE` → `NO_EXPRESABLE_PREVISTO`; alguna `PARCIAL` → `PARCIALMENTE_EXPRESABLE_PREVISTO`; todas presentes → `EXPRESABLE_PREVISTO`. Los ejes `INSEGURO` se registran aparte.

| Previsión | v0.2 | Qué cambia respecto de la v0.1 |
|---|---|---|
| `EXPRESABLE_PREVISTO` | **5** | La v0.1 afirmaba «pasan 3»; ninguno de aquellos tres sobrevive al criterio único |
| `PARCIALMENTE_EXPRESABLE_PREVISTO` | **14** | **CA-11** baja: purgado y «no guardado» no existen en 0.1 |
| `NO_EXPRESABLE_PREVISTO` | **30** | **CA-04** baja: `RF-12` está `AUSENTE`, igual que en CA-09 y CA-10, que la v0.1 sí marcaba no expresables |
| `NO_EJECUTABLE_CON_UNA_SOLA_IMPLEMENTACION` | **1** | **CA-39**: exige «dos implementaciones distintas sobre el mismo corpus» |

Ninguna cifra es un resultado. **T0 no se ha ejecutado.**

### M-01 · ausencia de ramas `M4` · **CERRADO**

Dentro del mismo identificador canónico, sin crear ningún CA nuevo:

| Caso | Rama añadida | Cláusula canónica |
|---|---|---|
| `CA-09` | `M4`: la candidata es visible con su estado | «Fuera de M1; **visible en M4**» |
| `CA-10` | `M4`: muestra el estado `RECHAZADA` | «**M4 muestra estado si se pide**» |
| `CA-24` | `M4`: visible con validez `SIN_SOPORTE` | «visible en auditoría» + B04 §5 M4, que lista «sin soporte» |
| `CA-49` | `M4`: la candidata pendiente y su origen | «candidata pendiente **visible en M4**» |
| **`CA-35`** | `M3`: inspección autorizada del fragmento | «**M3 puede inspeccionarlo si se pide**» |

**`CA-35` no estaba en la lista del paquete.** La detectó el validador al comparar los modos que el canon nombra con los que el artefacto instancia — el resultado directo de validar contra el DOCX en vez de contra una lista escrita a mano.

`M4` pasa de **0** a **4** apariciones; los cinco modos `M1`–`M5` aparecen ahora al menos una vez.

### M-02 · casos multirrama aplanados · **CERRADO**

| Caso | Ramas | Por qué ahora es falsable |
|---|---|---|
| `CA-36` | 3 | Estados internos distintos: `SOLO_HISTORICO`, `SOLO_CANDIDATA`, `FUERA_DE_AMBITO`. Devolver «no hay nada» a las tres —el fallo canónico— ya no pasa |
| `CA-47` | 3 | Tres conjuntos esperados **distintos**: `{DEC-011, DEC-015}`, `{DEC-014}`, `{DEC-014, DEC-015}`. Ningún sistema que colapse los tres ejes puede producirlos |
| `CA-48` | 3 | Par diferencial autorizado/no autorizado **más** una rama de ausencia real, ambas con la misma tolerancia pendiente declarada |

Para `CA-47` se añaden dos anclajes —`DEC-014` y `DEC-015`— declarados en el corpus con su motivo. Es el único ajuste de datos de esta ronda, y el §3.1 del paquete lo autoriza expresamente.

### M-03 · ficha de caso frente al PDP §7 · **CERRADO**

Los **catorce campos** del PDP §7 se leen del DOCX y se comparan con el esquema. Cada caso los lleva todos, más la **condición de insuficiencia por transición** que la Especificación §5 campo 12 exige y la v0.1 no instanciaba. Los cuatro que faltaban —`objetivo`, `unidad_de_trabajo`, `tolerancias`, `senales_observables`— están presentes con fuente y estado.

**Las tolerancias que no existen se declaran pendientes, no se inventan:**

| Caso | Tolerancia | Dependencia |
|---|---|---|
| `CA-37`, `CA-48` | Banda de texto, estado, conteo y tiempo | `RED-032` · `B04-RF-26` · `TOL-209` |
| `CA-39` | Clase de equivalencia de orden | `RED-033` · `TOL-209` |

### M-04 · ausencia de `PDP-CA` aplicables · **CERRADO**

Los 28 casos transversales se extraen del DOCX y se clasifican sin hueco ni solapamiento, con dos criterios citables:

- **8 aplicables**, instanciados como nivel 1 con su texto literal: `PDP-CA-09` y `PDP-CA-22` por el Anexo B vía `RED-017` (`B04-CA-39`, `B04-M16`); `PDP-CA-02`, `03`, `06`, `16`, `17` y `18` porque un artefacto **aprobado** de ADR-002 importa su regla.
- **20 excluidos**, cada uno con las filas RED que lo asignan, sus familias, el responsable expandido desde ARQ-00 §20 y el motivo.

El artefacto declara expresamente que **ADR-002 no cubre los 304 casos** del Plan completo.

### M-05 · mezcla de conformidad y rendimiento · **CERRADO**

Dos corpus vinculados, con propósito declarado en cada artefacto y prohibición cruzada en el manifiesto.

| | Conformidad | Rendimiento |
|---|---|---|
| Elementos | 94 (79 recuerdos + 15 decisiones) | **550** (500 + 50) |
| Mensajes | 6 | **5.000** |
| Escala | densa y legible | **la de `ADR002-TOL-208`** |
| Uso | puertas y comportamiento | latencia, tamaño, ciclo, estabilidad |

Regla de proyección declarada: `recuerdos(N)=N · decisiones(N)=N//10 · mensajes(N)=N*10`. Con `N=500` produce exactamente la escala de referencia. Escalas proyectables: **500 / 5.000 / 50.000**.

Tres garantías comprobadas: los 94 anclajes viajan **byte a byte idénticos**; el relleno vive en `PRJ-VOLUMEN`; y ninguno de los 26 términos de anclaje aparece en ningún texto de volumen. Esta última rechazó **643 elementos** en la primera versión del generador, por contener «mantenimiento».

### M-07 · cardinalidad y parada inferidas como canónicas · **CERRADO**

Se retira la atribución canónica de `EXHAUSTIVA` y `S5` en `CA-02`, `CA-22`, `CA-39` y `CA-47`. Se conserva **solo** la regla que el canon fija literalmente y que el validador lee del DOCX:

> **B04 §15.2 · EXHAUSTIVA** — S1 deshabilitado.

`CA-39` pasa a `cardinalidad: null` y `parada: null`: es un arnés de equivalencia entre dos realizaciones, no una consulta de recuperación.

### Menores · **CERRADOS**

- **Literalidad.** Los cuatro campos canónicos se toman del DOCX y se comparan **carácter a carácter**. Las comillas tipográficas `“ ”` de `CA-17`, `18`, `21`, `29`, `36`, `37`, `45` y `47` quedan restauradas, y una prueba parametrizada lo verifica en los ocho.
- **Denominadores de familias.** Cuatro, sin agregarlos: **7** de destino directo (ARQ-00 §20), **13** de entradas declaradas, **20** tocadas sin atribuir cierre, **18** fuera de alcance con su responsable. Una comprobación impide que reaparezca `20/25` como cobertura de ADR-002.

### M-06 · **NO TRATADO, deliberadamente**

El presupuesto absoluto de almacenamiento (`ADR002-TOL-207`) **no se aprueba ni se modifica** en esta ronda. Sigue abierto y así lo declara el manifiesto.

### B-04 · partición de candidatos · **cerrado en la ronda anterior**

Resuelto por `SIRIUS_0.2_ADR_002_RESOLUCION_PARTICION_CANDIDATOS_v1.0_APROBADA.md` (commit `fe85786`). El corpus sigue siendo **neutral**: traza a `RF`, `CA`, `M`, `RED` y familias, y **no menciona ninguna alternativa ni ningún eje**.

---

## 3. Estructura final de ambos corpus

```
experiments/adr002/benchmark/
  canonical_source.py            # lector DOCX: huellas, CA, Anexo B, PDP §7, PDP-CA, ARQ-00 §20
  schema_v0_2.py                 # vocabularios, denominadores, escala, términos de anclaje
  build_corpus_v0_2.py           # generador: reutiliza el v0.1 y aplica las correcciones
  validate_corpus_v0_2.py        # 62 comprobaciones contra los DOCX
  test_corpus_contract_v0_2.py   # 77 pruebas de contrato v0.2

  conformance_corpus_v0_2.json   #  94 elementos ·   6 mensajes · 5 documentos · 9 relaciones
  performance_corpus_v0_1.json   # 550 elementos · 5.000 mensajes · misma base de anclajes
  cases_v0_2.json                # 50 B04-CA + 8 PDP-CA + 5 nivel 2 + 7 ablaciones · 17 ramas
  references_v0_2.json           # 50 referencias, canon e instanciación separados
  pdp_cases_v0_1.json            # 8 aplicables / 20 excluidos / 4 denominadores de familias
  benchmark_manifest_v0_2.json   # relación entre los dos corpus y estado de los hallazgos

  # v0.1, intactos y verificados de nuevo
  __init__.py · schema.py · build_corpus.py · validate_corpus.py · test_corpus_contract.py
  corpus_v0_1.json · cases_v0_1.json · references_v0_1.json
```

---

## 4. Funcionamiento del validador contra los DOCX

Abre los tres `.docx` con `zipfile` y `xml.etree` de la biblioteca estándar. **No añade ninguna dependencia** —ni productiva ni de desarrollo— y es reproducible y local. Verifica primero el SHA-256 de cada fichero contra el bloque de huellas del `MANIFEST.md`; si una huella no coincide, falla antes de comparar nada.

Después extrae del canon, sin resumirlo: los 50 casos de B04 §17/§17.1, la regla de cardinalidad §15.2, las paradas §15.3, las etapas §15.1, los modos §5, los 32 RF, las 21 métricas, las 79 filas del Anexo B, los 14 campos del PDP §7, las 25 familias del PDP §8, los 28 `PDP-CA` y los destinos de ARQ-00 §20. Comprueba que cada extracción tiene el tamaño que el canon declara: si el lector se rompiera, el validador lo detecta en vez de dar por buena una tabla vacía.

Las **62 comprobaciones** cubren los once puntos que el paquete §5 exige, más la conservación del contrato v0.1 y la regeneración doble.

**Prueba de que no es decorativo:** en su primera ejecución el validador rechazó tres cosas reales — la rama `M3` que faltaba en `CA-35`, una comprobación de denominadores mal formulada, y 643 elementos de volumen contaminados con un término de anclaje. Las tres se corrigieron antes de publicar.

---

## 5. Pruebas ejecutadas

| Comprobación | Resultado |
|---|---|
| **Validador v0.2 contra los DOCX** | **62 comprobaciones · 0 fallos · veredicto `VALIDO`** |
| **pytest** sobre `experiments/adr002/benchmark` | **121 pasan · 0 fallan** (44 del contrato v0.1 + 77 del v0.2) |
| **Ruff format** | **11 ficheros ya formateados** |
| **Ruff check** | **All checks passed!** |
| SHA-256 de las tres fuentes canónicas | **3/3 coinciden con `MANIFEST.md`** |
| CA-01–50, exactamente una vez | **OK** — 0 ausencias, 0 duplicados, 0 ajenos |
| Literalidad carácter a carácter | **OK** — 4 campos × 50 casos, en casos y en referencias |
| Asignaciones del Anexo B | **OK** — las 20 CA que el Anexo B nombra, con sus métricas y familias |
| Ramas canónicas | **OK** — 17 ramas; `M1`–`M5` presentes; `CA-47` con tres conjuntos distintos |
| Ficha del PDP §7 | **OK** — 14 campos + insuficiencia en los 50 casos |
| Ausencia de veredictos T0 | **OK** — `NO_MEDIDO` en los 58 casos de nivel 1 |
| Escala del corpus de rendimiento | **OK** — 5.000 / 500 / 50 exactos |
| Anclajes intactos entre corpus | **OK** — los 94 comparados uno a uno |
| Relleno sin términos de anclaje | **OK** — 4.994 mensajes y 456 elementos comprobados |
| **Regeneración doble byte a byte** | **OK** — tres lecturas idénticas de los seis ficheros |
| Contrato v0.1 intacto | **OK** — sus 33 comprobaciones y 44 pruebas siguen pasando |
| `git status` | **limpio salvo las rutas autorizadas** |

**La suite productiva completa no se ha ejecutado:** no se ha modificado código productivo.

---

## 6. Rutas tocadas

**Añadido:** siete ficheros de código y datos en `experiments/adr002/benchmark/`, dos documentos en `docs/architecture/`, y dos artefactos en `artifacts/adr002_benchmark_preparation/`.

**Sin cambios, verificado con `git diff`:** `docs/architecture/canonical_sources/`, los tres JSON v0.1, `build_corpus.py`, `schema.py`, `validate_corpus.py`, `test_corpus_contract.py`, `__init__.py`, `validacion_corpus.json`, `src/`, `tests/`, `migrations/` y toda la configuración productiva.

---

## 7. Estado de las puertas de arranque

| Puerta | Antes | Después |
|---|---|---|
| `SRC-ADR002-01` | SATISFECHA | **SATISFECHA** |
| `ADR002-TOL-207` | NO SATISFECHA | **NO SATISFECHA** — M-06 abierto; no se aprueba aquí |
| `ADR002-TOL-208` | NO SATISFECHA, **con defecto material** | **NO SATISFECHA** — el defecto material queda corregido, pero el corpus **no está congelado** y **T0 no se ha ejecutado** |
| `ADR002-TOL-209` | NO SATISFECHA | **NO SATISFECHA** — faltan los valores del entorno, incluidas las bandas que `CA-37`, `CA-39` y `CA-48` declaran pendientes |
| `ADR002-TOL-210` | NO SATISFECHA | **NO SATISFECHA** — no hay ninguna ficha emitida |

**El benchmark sigue bloqueado.** Esta ronda retira el obstáculo que impedía plantear `TOL-208`; **no satisface ninguna puerta.**

---

## 8. Reproducción

```
uv run python -m experiments.adr002.benchmark.build_corpus_v0_2
uv run python -m experiments.adr002.benchmark.validate_corpus_v0_2
uv run pytest experiments/adr002/benchmark -q
uv run ruff format --check experiments/adr002/benchmark
uv run ruff check experiments/adr002/benchmark
```

---

**Siguiente movimiento único:** que el usuario revise esta corrección y decida si el corpus de conformidad puede congelarse, y si se abre el paquete de `ADR002-TOL-207` que la auditoría dejó pendiente (**M-06**). Hasta entonces el corpus no se congela, T0 no se rederiva, no se emite ninguna ficha y no se ejecuta ningún candidato.
