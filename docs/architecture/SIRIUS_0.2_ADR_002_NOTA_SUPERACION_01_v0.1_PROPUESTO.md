# SIRIUS 0.2 — ADR-002 · Nota de superación 01

## Qué queda superado por el Registro de Tolerancias v0.4

**Versión:** 0.1
**Estado:** **PROPUESTO** · nota de coherencia documental, **no aprueba ni decide nada**
**Fecha:** 26 de julio de 2026
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_02D_CORRECCION_AUDITORIA_v0.1.md` §7
**No autoriza:** benchmark T1–T4, ejecución de T0, implementación, elección de alternativa ni merge.

---

## 0. Objeto y método

Cuatro documentos vigentes contienen afirmaciones que el Registro de Tolerancias v0.4 supera. **Ninguno se reescribe.** Esta nota registra, punto por punto, qué queda superado, por qué y desde dónde leerlo.

**Regla de lectura:** ante discrepancia entre un documento anterior y el Registro v0.4 en cualquiera de los puntos listados aquí, **prevalece el Registro v0.4**. En todo lo demás, los documentos anteriores siguen íntegros y vigentes.

**Lo que esta nota no hace:** no modifica ningún fichero, no reabre ninguna decisión canónica, no crea tolerancias nuevas y no rellena ninguna laguna de fuente.

---

## 1. Registro de Tolerancias v0.3 → superado íntegramente

| Documento | `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.3_PROPUESTO.md` |
|---|---|
| **Estado** | **SUPERADO** por `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md` |
| **Se conserva** | Sí, sin modificar, igual que la v0.2 y la v0.1 |

**Motivo.** La auditoría adversarial lo declaró **NO APROBABLE** por tres bloqueantes:

- **B-01** — declaró «sin cambios» ocho filas cuyo texto había alterado, suprimiendo contenido normativo y de neutralidad.
- **B-02** — presentó 150 ms como «techo de no regresión» de la línea base cuando esta llega a 173,20 ms de P95 en el escenario TOL-002.
- **B-03** — declaró un P95 observado de FTS5 de «0,209–0,730 ms» cuando el peor real es 1,0038 ms, y un valor, «0,209», que en la evidencia es un P99.

Los tres quedan cerrados en la v0.4.

**Identificadores retirados y no reutilizables:** `ADR002-TOL-101` (→ `TOL-101L` + `TOL-101A`) y `ADR002-TOL-102` (→ `TOL-102B` + `TOL-102C`). **No existen `TOL-101B` ni `TOL-102A`.**

**Umbrales retirados:** el objetivo P95 ≤ 150 ms y el límite duro P99 ≤ 250 ms del antiguo TOL-102. **No es una rebaja de umbral canónico** —nunca fueron canónicos, eran `PROPUESTA`—: es la retirada de un fundamento que la propia evidencia refutaba.

---

## 2. Inventario normativo v0.2

| Documento | `SIRIUS_0.2_ADR_002_INVENTARIO_NORMATIVO_v0.2_PROPUESTO.md` |
|---|---|
| **Estado** | **VIGENTE**, con dos puntos superados |

### 2.1 §10 incertidumbre 4 — «umbral operativo de cobertura de críticos» · **SUPERADA**

El Inventario dice: *«La criticidad está definida; el porcentaje que satisface la suficiencia, no. Es tolerancia, no definición.»*

**Ya no es una incertidumbre abierta.** `ADR002-TOL-204` fija el umbral en **0 críticos elegibles pendientes**, con estado `DERIVADA_CANÓNICA` y **sin margen**. No es una propuesta: se deduce sin margen del contrato de suficiencia y de B04-M01. El candidato decide **cómo** implementa y demuestra la comprobación; **nunca el umbral**.

Fue el paquete 02B quien lo corrigió, porque clasificarlo como valor por candidato **contradecía B04**. Ninguna versión posterior del Registro puede devolverlo a `REGLA_CONFIRMADA_VALOR_CANDIDATO`.

**Matiz importante, y no menor.** El umbral está **cerrado**, pero **no es medible** mientras no existan casos con criticidad de origen trazable, que dependen de B04-CA-01–50 y del Plan de Pruebas. Esa falta de medibilidad **no reabre el umbral**: bloquea el benchmark. Ver §5.

### 2.2 §10 incertidumbre 1 — «Registro de Tolerancias: no existe todavía» · **SUPERADA EN SU PREMISA**

El Registro existe desde la v0.1 y va por la v0.4. Lo que sigue abierto no es su existencia sino su **aprobación**, que requiere decisión explícita del usuario.

### 2.3 Lo que **no** queda superado y sigue abierto

- **§3, tabla de fuentes** — sigue siendo exacta: B04-CA-01–50, B04-M01–21, B04-D01–16, G1–G12, S1–S7, el detalle de E0–E5, las familias PDP y ARQ-00 **no están en el repositorio**. El Registro v0.4 **no afirma lo contrario en ningún punto** y convierte esa ausencia en la puerta de arranque `SRC-ADR002-01`.
- **§10 incertidumbre 2** — «tolerancias ya congeladas frente a delegadas» sigue **parcialmente abierta**. El Registro separa lo canónico (§2 y §3) de lo delegado, pero las tolerancias de **texto, estado, conteo y tiempo** que RF-26 menciona no pueden comprobarse sin la fuente canónica. `TOL-201` condición (1) impone **equivalencia exacta**, que es el lado seguro y no rebaja nada; **si B04/PDP fijan una tolerancia no nula, prevalece la canónica**. Registrado como dependencia de `SRC-ADR002-01`.
- **§10 incertidumbres 3, 5, 6, 7, 8, 9 y 10** — sin cambios.

---

## 3. Especificación del benchmark v0.2

| Documento | `SIRIUS_0.2_ADR_002_ESPECIFICACION_BENCHMARK_v0.2_PROPUESTO.md` |
|---|---|
| **Estado** | **VIGENTE**, con cuatro puntos superados y dos artefactos obligatorios añadidos |

### 3.1 §12 incertidumbre 4 — «umbral operativo de cobertura de críticos» · **SUPERADA**

Misma resolución que en §2.1: cerrado en **0** por `ADR002-TOL-204`, no medible hasta materializar las fuentes canónicas.

### 3.2 §12 incertidumbre 1 — «Registro de Tolerancias: no existe» · **SUPERADA EN SU PREMISA**

Existe. El §9 de la Especificación deja como «Pendiente» varias métricas que el Registro **ya cubre reproduciendo el canon**:

| Métrica del §9 | Umbral que la cubre |
|---|---|
| Recall crítico | **B04-M01**: 100 % por caso |
| Explicabilidad | **B04-M14**: 100 % de muestra auditada — *sujeto a §5.3 de esta nota* |
| Corrección de la ausencia | **B04-M09**: 100 % críticos, ≥95 % global, 0 falsos «no existe» |
| Estabilidad de orden | **B04-M16** + `TOL-001` + `ADR002-TOL-103` |
| Latencia, coste, tamaño de índice | `TOL-101L`, `TOL-101A`, `TOL-102B`, `TOL-102C`, `TOL-104L`, `TOL-104A`, `TOL-105`, `TOL-107`, `TOL-202`, `TOL-203`, `TOL-207` |

**Sigue pendiente**, y no lo resuelve el Registro: la **regla de muestreo de M14**. Ver §5.3.

### 3.3 §5 regla 2 y §10 — la ficha del caso **no** aloja los valores por candidato · **SUPERADO**

Hasta la v0.3, el Registro decía que «los valores congelados por candidato se registran en la ficha del caso antes de la primera ejecución». **La ficha del caso de la §5 de la Especificación no puede alojarlos**: sus trece campos describen el caso de prueba, no el candidato.

Desde la v0.4:

- los valores por candidato se registran en un artefacto propio, la **ficha de candidato** (`ADR002-TOL-210`), conforme a `SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.1_PROPUESTO.md`;
- **la ficha de candidato no se registra dentro de la ficha de cada caso**; cada ejecución la **referencia** por ID, versión y huella;
- la **Evidencia mínima por ejecución** de la §10 queda ampliada con dos elementos obligatorios: **(11) referencia a la ficha de candidato** y **(12) versión del protocolo de medición aplicado y toda desviación declarada de antemano**.

### 3.4 §3 principio 4 y §8 — protocolo común de medición · **AMPLIADO**

El principio 4 exige reproducibilidad y la §8 exige ejecutar cada realización a través de un puerto equivalente. **Ninguno fijaba el método de cronometraje.** Desde la v0.4 rige `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md`, exigido por `ADR002-TOL-209`: sin él, las cifras de dos candidatos no son comparables.

### 3.5 §4 y §12 incertidumbre 5 — corpus y escala · **CONDICIONADO**

La Especificación deja el tamaño del corpus sin fijar, y con razón: no había criterio. Ahora lo hay, y es una **condición de arranque**, no una tolerancia. `ADR002-TOL-208` exige, en este orden:

1. congelar el corpus definitivo del benchmark;
2. **ejecutar T0 sobre ese mismo corpus**;
3. **rederivar la comparación de línea base** antes de ejecutar T1–T4.

**Ninguna cifra `LAB-LINUX` del corpus 5.000/500 se aplica a otro volumen sin rederivarla.** Latencia extremo a extremo, tiempo de ciclo y tamaño de índice escalan con el corpus.

### 3.6 §6.1 y §9 — se añade una comprobación de fallo duro

Las cinco clases de fallo duro de la §6.1 y las cinco puertas booleanas de la §9 **se conservan íntegras**. Se les añade la purga física del derivado, `ADR002-TOL-206`: tras el borrado y la secuencia declarada de checkpoint, journal y `VACUUM`, **ningún fragmento recuperable del derivado permanece** en `.db`, `-wal`, `-shm` ni `-journal`. Deriva de ADR-001 c.3 y c.4 y **descarta por la puerta 5**.

Importa porque el derivado puede contener el original: `knowledge_fts` almacena una copia literal del texto canónico —57.344 B de sus 122.880 B—, y un índice semántico puede contener payload reversible.

### 3.7 Lo que **no** queda superado

- **§2 nivel 1 y §12 incertidumbre 3** — siguen exactas y ahora son **bloqueantes explícitas**. Ver §5.
- **§6, columnas «pendiente»** — siguen siendo pendientes. **Prohibido rellenarlas por analogía.**
- **§11** — íntegro: la Especificación sigue sin ejecutar nada, sin sustituir B04-CA-01–50 ni el PDP, y sin elegir entre T1–T4.

---

## 4. ADR-002 v0.2 abierto

| Documento | `SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.2_ABIERTO.md` |
|---|---|
| **Estado** | **VIGENTE**, con un punto precisado |

### 4.1 §7 método de cierre, paso 3 — «fijar el Registro de Tolerancias» · **EN CURSO, NO CERRADO**

El Registro existe y va por la v0.4, pero **sigue `PROPUESTO`**. El paso 3 exige además **aprobación explícita**, que no se ha producido. El paso 3 continúa siendo **bloqueante para los pasos 6 en adelante**.

### 4.2 §4 puerta 7 — «coste, latencia o complejidad incompatibles con el Registro» · **PRECISADA**

La puerta 7 sigue siendo la única que depende del Registro. Lo que la v0.4 precisa es **contra qué se evalúa**:

- **no** contra el tiempo de T0 —cuyo 99,85 % es el barrido que RF-14 prohíbe—;
- **sí** contra el límite que **el propio candidato declaró y congeló** antes de ejecutar (`TOL-102C`, `TOL-101A`, `TOL-104A`, `TOL-202`, `TOL-203`);
- **sí** contra el presupuesto absoluto del entorno de laboratorio (`TOL-207`), congelado antes del benchmark.

**Ningún candidato puede invocar el barrido prohibido de T0 como justificación de un coste alto propio.**

### 4.3 §4, nota sobre FTS5 — **reafirmada y reforzada**

*«La continuidad con FTS5 es un valor favorable, nunca una excepción a las puertas.»* La v0.4 añade el reverso, que la auditoría echó en falta: **tampoco es un patrón obligatorio**. Las cifras del FTS5 medido (`TOL-101L`, `TOL-104L`, tiempos de `TOL-105`) **no son límites universales para T3/T4**; un sustrato léxico alternativo declara y congela los suyos en `TOL-101A`, y su desviación respecto de FTS5 se informa como **comparación**, no como déficit automático.

### 4.4 §3.1 control de falsación T0 — **precisado**

T0 se ejecuta sobre el **corpus definitivo del benchmark** como paso 2 de `ADR002-TOL-208`. Eso es **rederivación de la comparación**, no una remedición de la línea base congelada de la §6, que permanece identificada por el head `61be4bb269bf` y los ficheros de la §3 de la Línea base FTS5. **Este paquete no ejecuta T0.**

---

## 5. Bloqueo de arranque del benchmark

Registrado como puerta `SRC-ADR002-01` en el Registro v0.4 §7. **No es una tolerancia: es una condición sin la cual el benchmark no puede comenzar.**

### 5.1 Fuentes que faltan

| Fuente | Estado en el repositorio |
|---|---|
| **B04 v1.0 APROBADO** íntegro: CA-01–50, M01–21, D01–16, detalle de E0–E5, G1–G12, S1–S7 | **AUSENTE.** Solo se conocen 16 CA por el mapeo RED; los de RED-032 se difieren al Plan canónico |
| **Plan de Pruebas + RED/PDP v1.0 APROBADO** | **AUSENTE.** Solo se conocen los identificadores de las familias |
| **ARQ-00 v1.0 APROBADO** | **AUSENTE** |

### 5.2 Qué bloquea exactamente

- **La materialización del nivel 1** —los casos canónicos reutilizados de la Especificación §2— y con ella **toda ejecución del benchmark**.
- **La medición de B04-M01–M21**, que carecen de casos instanciados.
- **La verificación de `ADR002-TOL-204`**, que necesita casos con criticidad de origen trazable.
- **La comprobación de las tolerancias de texto, estado, conteo y tiempo de RF-26** (§2.3).

### 5.3 Dependencias adicionales de la misma puerta

- **Regla de muestreo de B04-M14.** «100 % de muestra auditada» no es ejecutable sin saber el tamaño y el criterio de la muestra. **No se inventa aquí ninguna regla de muestreo.**
- **Mapeo exacto de RED-032**, expresamente diferido al Plan canónico.

### 5.4 Qué **no** bloquea

Nada de lo ya producido. El Registro v0.4, la plantilla de ficha de candidato y el protocolo de medición **pueden aprobarse antes** de que las fuentes se materialicen. Lo que no puede hacerse es **ejecutar el benchmark**, ni completo ni en parte.

### 5.5 Prohibiciones asociadas

1. **Prohibido rellenar por analogía** cualquier CA, M, D, G o S ausente. Las columnas «pendiente» son pendientes, no huecos.
2. **Prohibido afirmar que estas fuentes están en el repositorio.**
3. **Prohibido sustituir un caso canónico por una versión «arquitectónica»** (Especificación §2, nivel 1).
4. Ejecutar el benchmark sin estas fuentes produce un resultado **no válido para cerrar ADR-002**, porque su conformidad no sería trazable al canon.

---

## 6. Resumen de artefactos obligatorios añadidos

| Artefacto | Exigido por | Papel |
|---|---|---|
| `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md` | 02D §8 | Sustituye a la v0.3 |
| `SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.1_PROPUESTO.md` | `ADR002-TOL-210` | Congela los valores por candidato **antes** de ejecutar |
| `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md` | `ADR002-TOL-209` | Hace comparables las cifras entre candidatos |

Los tres están **`PROPUESTO`**. Ninguno aprueba nada por sí mismo.

---

## 7. Qué documentos siguen íntegros y sin superar

- `SIRIUS_0.2_ADR_001_MODELO_FISICO_v1.1_APROBADO.md` — **APROBADO**. Sus consecuencias 1–10 se conservan íntegras; las consecuencias 3 y 4 son ahora exigibles en el laboratorio vía `ADR002-TOL-206`, y la 5 vía `ADR002-TOL-205`.
- `SIRIUS_0.2_ADR_002_LINEA_BASE_FTS5_v0.2_PROPUESTO.md` — íntegro. **Ninguna medición se ha repetido y ninguna ha cambiado.**
- `INFORME_MEDICION_TOLERANCIAS_v0.2_PROPUESTO.md` y `mediciones_linea_base_v0.2.json` — íntegros y **no modificados**. Son la evidencia contra la que se corrigieron `TOL-101L` y `TOL-102B`.
- Registros de Tolerancias v0.1 y v0.2 — se conservan sin modificar, como referencia histórica y como fuente literal de la restauración de B-01.

---

**Siguiente movimiento único:** que el usuario apruebe, corrija o rechace el Registro v0.4 y sus dos artefactos asociados, y decida sobre las cinco puertas de arranque. Hasta entonces no se construye corpus de benchmark, no se implementa ningún prototipo, no se ejecuta T0 y no se ejecuta ningún candidato.
