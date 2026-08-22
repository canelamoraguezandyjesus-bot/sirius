# SIRIUS 0.2 — ADR-002 · Corpus ejecutable del benchmark

**Versión:** 0.1
**Estado:** **PROPUESTO** · no aprueba, no decide y no autoriza ejecutar nada
**Fecha:** 26 de julio de 2026
**Artefactos:** `experiments/adr002/benchmark/`
**Validación:** `artifacts/adr002_benchmark_preparation/validacion_corpus.json` · **33/33 comprobaciones OK**
**Matriz asociada:** `SIRIUS_0.2_ADR_002_MATRIZ_CANONICA_BENCHMARK_v0.1_PROPUESTO.md`
**No autoriza:** ejecutar T0 ni T1–T4, implementar candidatos, elegir realización técnica ni merge.

---

## 0. Qué se ha construido

El corpus sintético, los casos y las referencias con los que ADR-002 comparará después las realizaciones técnicas, **fijando las referencias antes de observar ningún resultado**. Esta ronda **no ejecuta nada y no mide nada**.

| Fichero | Bytes | Contenido |
|---|---|---|
| `corpus_v0_1.json` | 77.362 | Proyectos, entidades, elementos, historial, documentos y relaciones |
| `cases_v0_1.json` | 84.541 | 50 casos de nivel 1, 5 de nivel 2, 7 ablaciones |
| `references_v0_1.json` | 26.460 | 50 referencias congeladas, una por caso canónico |
| `schema.py` | — | Vocabularios canónicos de B04 y ADR-001; ningún valor inventado |
| `build_corpus.py` | — | Generador determinista, semilla `20260726` |
| `validate_corpus.py` | — | 33 comprobaciones de contrato; emite el informe legible por máquina |
| `test_corpus_contract.py` | — | 44 pruebas de contrato |
| `conftest.py`, `__init__.py` | — | Empaquetado; mismo patrón que `experiments/adr002/tolerances/` |

---

## 1. Estructura y tamaño del corpus

| Colección | Elementos | Papel |
|---|---|---|
| **Proyectos** | 7 | `PRJ-GLOBAL`, cuatro proyectos, un viaje contrastado y **una lista multi-proyecto cerrada** (`LISTA-CERRADA-AB`) |
| **Entidades** | 5 | Incluye **dos homónimos no fusionables** (`ENT-JUAN-TORRES`, `ENT-JUAN-MOLINA`) y alias confirmados |
| **Elementos de conocimiento** | **92** | 52 significativos, trazados a un CA concreto, y **40 de ruido determinista** |
| **Mensajes (historial)** | 6 | Evidencia no canónica de la etapa E4 |
| **Documentos** | 5 | Uno de ellos **inaccesible** (`DOC-004`), para CA-18 y la parada S7 |
| **Relaciones** | 9 | Apoyo, refutación, conflicto, corrección, sustitución, alias y origen de candidata |

**Por qué 40 elementos de ruido.** `B04-CA-31` exige cinco críticos dispersos entre alias, relación, historial y estructura: sin ruido real, encontrarlos es trivial y la métrica no demuestra nada. El ruido es reproducible —semilla fija— y está marcado como tal.

### 1.1 Modelo de cada elemento

Las **siete dimensiones canónicas de ADR-001 permanecen ortogonales**, cada una con su propio vocabulario y su propio campo. Ninguna se condensa en un enum monolítico —ADR-001 consecuencia 7—, que es exactamente lo que el spike 7 demostró que el enum heredado no puede representar sin pérdida:

| Dimensión | Vocabulario |
|---|---|
| Confirmación | `CONFIRMADA` · `CANDIDATA` · `RECHAZADA` · `SUPRIMIDA` |
| Validez | `VIGENTE` · `SUSTITUIDA` · `INVALIDADA` · `SIN_SOPORTE` |
| Disponibilidad | `DISPONIBLE` · `ARCHIVADA` · `ELIMINADA` · `PURGADA` · `NO_GUARDADA` |
| Sensibilidad | `ORDINARIA` · `RESTRINGIDA` |
| Temporalidad | `valid_from` · `valid_to` · `occurred_at` · `recorded_at`, **los cuatro separados** |
| Ámbito | `GLOBAL` · `PROYECTO` · `MULTI_PROYECTO_CERRADO` |
| Autoridad | `DOCUMENTO_CANONICO` · `ACTO_EXPLICITO_USUARIO` · `INFORMAL` · `FUENTE_EXTERNA` |

Además, cada elemento lleva polaridad, condición, marcas de `no_usar_como_memoria` y `no_consolidable`, procedencia y —cuando aplica— criticidad con **nivel, razón, fuente y regla**, conforme a B04 §6 y RF-23. Una prueba automática rechaza cualquier marca crítica incompleta: **el auto-marcado libre está prohibido y el corpus no puede expresarlo**.

### 1.2 Fenómenos exigidos, todos presentes

Verificado automáticamente, uno por uno:

negación · condición · apoyo · refutación · conflicto · corrección · sustitución · homónimos · alias ambiguos · eliminado/purgado · no guardado · archivado · restringido · «no usar como memoria» · no consolidable · sin soporte · candidata · rechazada · **fuente inaccesible** · separación explícita por proyecto · lista multi-proyecto cerrada · tiempo válido y tiempo de registro · **tres ejes temporales distintos en un mismo elemento** (`DEC-011`: evento en enero, validez en febrero, registro en marzo, para CA-47).

Casos **exactos, acotados y exhaustivos**: los tres presentes. Ausencia real (CA-17), no reportable (CA-37, CA-48) y fuente inaccesible (CA-18): las tres presentes y distinguidas.

---

## 2. Disciplina del corpus

| Regla | Cómo se cumple | Cómo se verifica |
|---|---|---|
| **Semilla fija** | `CORPUS_SEED = 20260726`, declarada en el JSON | prueba automática |
| **Sin aleatoriedad no sembrada** | Un único `random.Random(SEED)` para el ruido; el resto es literal | revisión + determinismo |
| **Sin dependencia de reloj** | El «ahora» es un dato declarado, `2026-06-15T00:00:00Z`. Ninguna llamada a la hora del sistema | prueba automática |
| **Ningún dato real** | Corpus sintético; se rechazan URLs, correos, `password`, `api_key`, `secret` | prueba automática sobre el JSON crudo |
| **Sin red** | Declarado y cierto: el generador no importa ningún cliente | revisión |
| **IDs estables** | Prefijos `PRJ-`, `ENT-`, `MEM-`, `DEC-`, `MSG-`, `DOC-`, `REL-`; sin duplicados | prueba automática |
| **Reproducible byte a byte** | Regenerar produce ficheros idénticos | el validador **reejecuta el generador** y compara bytes |
| **Trazabilidad de cada registro** | Cada elemento significativo lleva `traza` al CA que lo justifica | revisión + cobertura |

**El determinismo se comprueba ejecutando de verdad.** `validate_corpus.py` lanza el generador como subproceso y compara los bytes antes y después. No es una afirmación: es una comprobación.

---

## 3. Trazabilidad

Cada caso de nivel 1 traza a **cuatro** ejes canónicos a la vez, y el validador rechaza cualquier identificador que no exista en el canon:

| Eje | Cobertura | Verificación |
|---|---|---|
| `B04-CA-01`–`CA-50` | **50/50**, exactamente una vez cada uno | sin ausencias ni duplicados |
| `B04-RF-01`–`RF-32` | **32/32** | todo RF citado pertenece al rango |
| `B04-M01`–`M21` | **21/21** | toda métrica citada pertenece al rango |
| Familias PDP `F01`–`F25` | 18/25 en nivel 1, **20/25** con los tres niveles | toda familia citada pertenece al rango |
| `RED-027`–`RED-034` | **8/8** | delegaciones de B04 a ADR-002 |

**Anclajes corregidos durante la construcción.** Tres RF quedaban sin caso: `RF-03` (adjudicar modo), `RF-04` (aclaración mínima) y `RF-29` (plan reproducible). No se resolvieron por conveniencia sino **por evidencia canónica**:

- `RED-027` mapea RF-01–04 a CA-01/05/08/15 → `RF-03` se ancla en **CA-09 y CA-15**, donde el modo decide la elegibilidad.
- El texto canónico de **CA-07** («Parcial o **aclaración**») y **CA-14** («**Aclara** o devuelve grupos separados») nombra literalmente la aclaración → ahí se ancla `RF-04`.
- `RED-029` mapea RF-18/RF-29 a CA-40/44 → `RF-29` se ancla en **CA-40 y CA-44**.

**`RED-040` no se usa como requisito propio.** Pertenece a B05/ADR-003B; ADR-002 solo registra la interfaz. Una prueba automática verifica que ningún caso lo invoca.

---

## 4. Una violación del contrato detectada y corregida

Merece registro porque demuestra que el validador hace su trabajo.

La primera versión de la matriz marcaba **CA-02, CA-22, CA-39 y CA-47** como cardinalidad `EXHAUSTIVA` con parada `S1`. B04 §15.2 y §15.3 lo prohíben expresamente:

> `EXHAUSTIVA` — Busca todos los elementos que cumplen una condición. **S1 deshabilitado.** Deben agotarse los espacios autorizados o terminar por S2–S7 con estado parcial/explicado.

El validador lo detectó antes de cualquier publicación. Los cuatro casos pasan a **`S5` · agotamiento autorizado**, que es la parada correcta para una consulta exhaustiva que recorre todos los espacios permitidos. La comprobación queda **permanente**, en el validador y en una prueba de contrato: ninguna versión futura podrá reintroducir el error en silencio.

---

## 5. Separación de niveles y neutralidad

**Nivel 1 — referencia congelada.** Las 50 referencias declaran `"modificable": false` y `"congelada_por": "B04 v1.0 APROBADO §17 y §17.1"`. Cambiar una referencia tras observar la salida es lo que `RED-004` y `PDP-CA-02` prohíben, y lo que el §9 regla 1 del Registro de Tolerancias llama justificación a posteriori.

**No se ha cambiado ninguna referencia canónica para facilitar T0.** El reparto lo demuestra: 36 de 50 casos son no expresables por la línea base y 5 más producen fallo duro. Habría sido trivial ablandarlos; no se ha hecho.

**Nivel 2 — solo cuando ningún CA lo cubre.** Los cinco casos arquitectónicos declaran individualmente por qué B04 no puede contenerlos: B04 excluye expresamente «índices, embeddings, RAG, modelos, consultas físicas, servicios y almacenamiento» (§3). Ante la duda, el caso es de nivel 1.

**Nivel 3 — nunca produce conformidad.** Las siete ablaciones son instrumentos de medida. `AB-4` es la más informativa: separa lo que aporta la señal semántica de lo que aporta la validación de polaridad que RF-17 exige. Sin ella no puede saberse si un acierto en CA-20 o CA-21 procede de la señal o del control.

**Neutralidad tecnológica.** El corpus, los casos y las referencias trazan a `RF`, `CA`, `M`, `RED` y familias PDP. **No mencionan T1–T4 ni A–D, ni ningún motor, índice, modelo o extensión.** Un caso que solo una realización pudiera pasar por construcción sería un caso mal diseñado.

---

## 6. Cómo se reproduce

```
uv run python -m experiments.adr002.benchmark.build_corpus      # regenera los tres JSON
uv run python -m experiments.adr002.benchmark.validate_corpus   # 33 comprobaciones + informe
uv run pytest experiments/adr002/benchmark -q                   # 44 pruebas de contrato
uv run ruff format --check experiments/adr002/benchmark
uv run ruff check experiments/adr002/benchmark
```

**No se ha ejecutado la suite productiva completa**: no se ha tocado código productivo. `src/`, `tests/`, `migrations/`, `canonical_sources/` y la configuración quedan intactos.

---

## 7. Lo que falta antes de poder ejecutar

El corpus está construido y validado, pero el benchmark **sigue bloqueado**. De las cinco puertas de arranque del Registro v0.4:

| Puerta | Estado |
|---|---|
| `SRC-ADR002-01` · fuentes canónicas completas | **SATISFECHA** |
| `ADR002-TOL-207` · presupuesto absoluto de almacenamiento | **PROPUESTA** · pendiente de aprobación |
| `ADR002-TOL-208` · corpus congelado, T0 rederivada, comparación rederivada | **NO SATISFECHA** — el corpus es `v0.1 PROPUESTO`, no congelado, y **T0 no se ha ejecutado sobre él** |
| `ADR002-TOL-209` · protocolo común de medición | **NO SATISFECHA** — falta congelar el umbral de conmutación y la banda absoluta de TOL-107 con el entorno |
| `ADR002-TOL-210` · ficha de candidato | **NO SATISFECHA** — la plantilla existe; no hay candidato que fichar, y antes hay que resolver qué conjunto de candidatos se ejecuta |

**Cuestión abierta que precede a todo lo demás:** ARQ-00 §23 enuncia las alternativas de ADR-002 como A/B/C/D, particionadas por la señal (semántica, relacional o ambas); ADR-002 v0.2 §3 usa T1–T4, particionadas por sustrato léxico × relaciones. **No son la misma partición.** El corpus es neutral respecto de ambas, pero el número y la naturaleza de las fichas de candidato dependen de cuál se adopte. Se detalla en la §6 de la matriz canónica.

---

**Siguiente movimiento único:** que el usuario apruebe o corrija el corpus y el presupuesto `TOL-207`, y resuelva qué conjunto de candidatos se ejecuta. Hasta entonces el corpus no se congela, T0 no se rederiva y no se ejecuta ningún candidato.
