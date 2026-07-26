# SIRIUS 0.2 — ADR-002 · Matriz canónica del benchmark

**Versión:** 0.3
**Estado:** PROPUESTO · NO CONGELADO
**Rama:** `evidence/adr001-spikes`
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_03C_ENDURECIMIENTO_CORPUS_v0.1.md`
**Fuentes canónicas:** los tres DOCX de `docs/architecture/canonical_sources/`, verificados por SHA-256 contra `MANIFEST.md`
**No autoriza:** congelar el corpus, aprobar `ADR002-TOL-207`, ejecutar T0, implementar o ejecutar `ADR002-A/B/C/D`, satisfacer `ADR002-TOL-208`, `ADR002-TOL-209` o `ADR002-TOL-210`, abrir otro PR ni merge.

Las versiones v0.1 y v0.2 de esta matriz se conservan íntegras. Esta v0.3 **no las corrige en su sitio**: las sustituye para el trabajo siguiente y declara qué cambia y por qué.

---

## 1. Qué cierra esta versión

| Hallazgo | Estado v0.2 | Corrección v0.3 |
|---|---|---|
| **B-01** selección frágil de tablas DOCX y aprobación en vacío | Las tablas se elegían por número de columnas y forma de fila. El Plan de Pruebas tiene **dos** tablas de seis columnas con `RED-\d{3}` en la primera —el Registro RED del §4 y el Anexo B del §23— y ambas caían en el mismo diccionario. Que el resultado fuese correcto dependía del orden físico del fichero | `canonical_source_v0_3.py` selecciona **por cabecera literal + contexto canónico**. Cero o más de una candidata es `TablaCanonicaError`. Cada identidad declara su número exacto de filas y el patrón de su primera columna |
| **B-02** corpus de rendimiento degenerado | Relleno uniforme con número de secuencia como única variedad, alojado en un octavo proyecto artificial declarado como «2 proyectos» | Corpus sintético independiente: **5.000 mensajes, 500 recuerdos, 50 decisiones y 2 proyectos reales**, con vocabulario aproximadamente Zipf y distribuciones publicadas y verificadas sobre los datos |
| **B-03** cierre incorrecto de `CA-47` | Conjuntos escritos a mano y llamados `EXHAUSTIVA` | El cierre se **rederiva del corpus** bajo filtros declarados y el validador lo recalcula por su cuenta |
| **B-04** seis `PDP-CA` de disciplina tratados como casos funcionales | Ocho `PDP-CA` instanciados como nivel 1 | Solo `PDP-CA-09` y `PDP-CA-22` —los únicos anclados por el Anexo B vía `RED-017`— siguen siendo casos funcionales. Los otros seis pasan a `pdp_harness_rules_v0_1.json` |

---

## 2. Lectura del canon por identidad de tabla

Catorce identidades, cada una con cabecera, contexto, número de filas y patrón de la primera columna. Ninguna usa la posición física.

| Identidad | Documento | Cabecera | Filas |
|---|---|---|---|
| `b04_casos_17` | B04 | `ID · Riesgo · Entrada · Resultado esperado · Fallo observable` | 39 |
| `b04_casos_17_1` | B04 | *idéntica a la anterior* | 11 |
| `b04_modos` | B04 | `Modo · Finalidad · Elegibilidad` | 5 |
| `b04_etapas` | B04 | `Etapa · Comportamiento · Salida` | 6 |
| `b04_cardinalidad` | B04 | `Cardinalidad · Definición · Regla de parada` | 3 |
| `b04_paradas` | B04 | `ID · Condición` | 7 |
| `b04_requisitos` | B04 | `ID · Requisito` | 32 |
| `b04_metricas` | B04 | `ID · Métrica · Cálculo / qué mide · Umbral / puerta` | 21 |
| `pdp_ficha_7` | PDP | `Campo · Definición · Cuándo se congela` | 14 |
| `pdp_familias_8` | PDP | `ID · Familia · Cobertura mínima` | 25 |
| `pdp_casos_transversales` | PDP | `ID · Entrada adversarial · Resultado esperado` | 28 |
| `pdp_registro_red` | PDP | `ID · Fuente · Localizador · Delegación obligatoria · Artefacto del Plan · Estado` | 79 |
| `pdp_anexo_b` | PDP | `RED · Familia · Caso(s) exactos · Métrica / puerta · Evidencia mínima · Estado` | 79 |
| `arq00_destinos_20` | ARQ-00 | `ID · Familia canónica · Cobertura mínima literal · Área responsable · Destino` | 25 |

`b04_casos_17` y `b04_casos_17_1` comparten cabecera y se distinguen **solo** por contexto (`17. Casos de aceptación finales` frente a `17.1 Casos añadidos y corregidos…`). `pdp_registro_red` y `pdp_anexo_b` comparten forma y se distinguen por cabecera.

### 2.1 Invariantes mínimas

El lector falla entero —nunca produce un PASS parcial— si no encuentra: 50 `B04-CA`; 79 filas de Anexo B; 79 filas de Registro RED; **al menos 20** `B04-CA` nombrados por el Anexo B (hoy son exactamente 20); 25 familias PDP con su texto de cobertura; 28 `PDP-CA`; **exactamente los 14** campos canónicos de la ficha del PDP §7; 32 `B04-RF`; 21 `B04-M`; 25 destinos de ARQ-00 §20.

Además rechaza identificadores inexistentes: `RED-099`, `B04-M99`, `F99`, `B04-CA-51`, `PDP-CA-29`.

---

## 3. Anexo B en ambas direcciones

1. **canon → artefacto**: toda asignación `RED → CA / métrica / familia` del Anexo B está presente en la traza canónica del caso.
2. **artefacto → canon**: ninguna asignación marcada canónica existe fuera del Anexo B.
3. Las trazas derivadas viven en campos separados (`*_adicional_derivada`) y no se solapan con las canónicas.
4. **No se filtran métricas de otros bloques.**

### 3.1 Métricas abreviadas y métricas externas

El v0.2 partía la celda `B08-M12/M25` en `B08-M12` y `M25`: un identificador que no existe en ningún bloque. El v0.3 arrastra el prefijo y expande rangos:

- `B08-M12/M25` → `B08-M12`, **`B08-M25`**
- `B04-M21/B05-M16` → `B04-M21`, **`B05-M16`**
- `PDP-M01–M17` → las diecisiete métricas del rango

`B05-M16` (citada por `RED-034` y `RED-041`) y `B08-M25` (citada por `RED-017`) quedan **conservadas y declaradas** como referencias canónicas externas del Anexo B, junto con `B01-M06` y `B07-M20`. El manifiesto las publica en `metricas_del_anexo_b.externas_canonicas`; no cuentan como métricas propias de B04.

---

## 4. Ramas canónicas · **19 ramas**, no 17

| Caso | Ramas | Motivo canónico |
|---|---|---|
| `B04-CA-09` | 2 | `M1` excluye la candidata; `M4` la muestra |
| `B04-CA-10` | 2 | igual, sobre una rechazada |
| `B04-CA-24` | 2 | igual, sobre un resumen sin soporte |
| `B04-CA-35` | 2 | `M1` excluye el fragmento «no usar»; `M3` puede inspeccionarlo |
| `B04-CA-49` | 2 | `E4` devuelve evidencia atribuida; `M4` muestra la candidata enlazada |
| `B04-CA-36` | 3 | histórico / candidata / fuera de ámbito, con estados internos distintos |
| `B04-CA-47` | 3 | `occurred_at` / `valid_time` / `recorded_at`, con conjuntos distintos |
| `B04-CA-48` | 3 | autorizado / no autorizado / ausencia real |
| **Total** | **19** | |

El v0.2 declaraba 17 en su documentación mientras el artefacto contenía 19: la cifra publicada aquí es la calculada sobre el artefacto (`cases_v0_3.json → conteos.ramas_canonicas`).

## 4.1 Literalidad · **21 casos con comillas tipográficas**, no 8

Veintiún casos de `B04 §17/§17.1` contienen comillas tipográficas (`«» “” ‘’`) en alguno de sus cuatro campos canónicos. La comparación carácter a carácter cubre los 50, no una muestra; la cifra 8 de la v0.2 era un recuento parcial.

---

## 5. Cierre exhaustivo de `B04-CA-47`

Filtro base declarado: `kind = DECISION`, `project_id = PRJ-BETA`, `confirmacion = CONFIRMADA`, `validez = VIGENTE`, `disponibilidad = DISPONIBLE`, `sensibilidad = ORDINARIA`, `no_usar_como_memoria = false`.

Universo en ámbito: `DEC-005, DEC-009, DEC-011, DEC-013, DEC-014, DEC-015`.

| Rama | Filtro temporal | Elegibles (calculados) | Prohibidos (complemento) |
|---|---|---|---|
| `R1` | `occurred_at ∈ [2026-01-01, 2026-02-01)` | `DEC-011`, `DEC-015` | `DEC-005`, `DEC-009`, `DEC-013`, `DEC-014` |
| `R2` | `valid_from ≤ 2026-01-20 < valid_to` (o `valid_to` abierto) | **`DEC-005`, `DEC-009`, `DEC-014`** | `DEC-011`, `DEC-013`, `DEC-015` |
| `R3` | `recorded_at ≤ 2026-02-15` | **`DEC-005`, `DEC-014`, `DEC-015`** | `DEC-009`, `DEC-011`, `DEC-013` |

Tres conjuntos distintos: ningún sistema que colapse los tres ejes en «más reciente» puede producirlos. Los prohibidos son **exactamente el complemento** dentro del ámbito, no una lista escogida.

El generador calcula el cierre; el validador lo **vuelve a calcular por su cuenta** desde los filtros declarados en el artefacto y compara. Un subconjunto escrito a mano falla.

---

## 6. `PDP-CA` · clasificación en tres clases disjuntas

| Clase | Cuántos | Criterio | Dónde vive |
|---|---|---|---|
| Caso funcional de nivel 1 | **2** | El Anexo B lo asigna en una fila que cita un caso `B04-CA` o una métrica `B04-M` | `cases_v0_3.json → nivel_1_pdp` |
| Regla de protocolo del arnés | **6** | Disciplina de congelación importada expresamente por un artefacto aprobado de ADR-002 | `pdp_harness_rules_v0_1.json` |
| Fuera de alcance | **20** | Ninguna fila que lo asigna cita B04 y ADR-002 no importa su regla | `pdp_cases_v0_2.json → casos_fuera_de_alcance` |

**Casos funcionales:** `PDP-CA-09` y `PDP-CA-22`, ambos anclados por `RED-017` (`F22`; casos `B04-CA-39`, `PDP-CA-09`, `PDP-CA-22`; métricas `B04-M16` y `B08-M25`). Llevan la ficha completa de PDP §7 y consulta funcional.

**Reglas del arnés:** `PDP-CA-02`, `PDP-CA-03`, `PDP-CA-06`, `PDP-CA-16`, `PDP-CA-17` y `PDP-CA-18`. Cada una registra texto canónico, fuente PDP, regla de ejecución, evidencia requerida, consecuencia y estado de aplicabilidad. **No tienen consulta, ni conjunto elegible, ni etapa, ni parada, ni previsión frente a T0.**

---

## 7. Canon frente a instanciación en los catorce campos

Los catorce campos de la ficha del PDP §7 —`ID y familia`, `Objetivo`, `Entrada`, `Unidad de trabajo`, `Operación y modo`, `Ámbito`, `Tiempo y corte`, `Referencia`, `Criticidad`, `Tolerancias`, `Señales observables`, `Fallo`, `Evidencia`, `Resultado`— más la condición de insuficiencia registran los cinco atributos: `valor`, `fuente`, `seccion`, `estado`, `justificacion`.

Solo tres campos pueden ser `CANONICO`, y solo cuando el texto literal del propio caso los fija: `Entrada` y `Fallo` (columnas del DOCX) y `Operación y modo` cuando el texto canónico nombra un modo `M1–M5`. El validador comprueba cada `CANONICO` contra el texto del propio caso.

### 7.1 Condición de insuficiencia, por rama

Cada rama declara sus transiciones con `etapa_actual`, `variables_observadas`, `predicado`, `umbral_o_condicion_logica`, `siguiente_etapa_permitida`, `fuente` y `estado`. Cuando no aplica —`E0`, o un caso sin vocabulario de expansión como `B04-CA-39`— se declara `NO_APLICA` con una razón verificable. No se acepta una lista vacía sin explicación ni una frase genérica repetida.

### 7.2 Tolerancia frente a valor pendiente

| Caso | `tolerancia_id` | `valor_pendiente_en` | Estado |
|---|---|---|---|
| `B04-CA-37` | `ADR002-TOL-201` | `ADR002-TOL-209` | `PENDIENTE_TOL209` |
| `B04-CA-48` | `ADR002-TOL-201` | `ADR002-TOL-209` | `PENDIENTE_TOL209` |
| `B04-CA-39` | `ADR002-TOL-001` | `ADR002-TOL-209` | `PENDIENTE_TOL209` |
| resto | `ADR002-TOL-201` condición (1) | — | `DERIVADO_PROPUESTO` |

La **regla** está identificada y es canónica; lo que falta es su **valor**. Confundir ambas cosas era el defecto: se declaraba una tolerancia inexistente o se dejaba el campo sin identificar. `tolerancia_id` nunca es igual a `valor_pendiente_en`.

---

## 8. Familias PDP · cuatro denominadores, con fuente expresa

No existe una sola cifra de «cobertura de familias de ADR-002». Se reportan cuatro y **no se agregan**:

| Denominador | Fuente | Familias | De |
|---|---|---|---|
| 1 · destino directo ADR-002 | ARQ-00 v1.0 APROBADO §20 | 7 (`F01 F02 F03 F10 F15 F22 F23`) | 25 |
| 2 · entradas obligatorias declaradas | `SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.3_ABIERTO.md` §2 | 13 | 25 |
| 3 · tocadas por casos, sin atribuir cierre | Matriz/corpus ADR-002 v0.3 PROPUESTO | 20 | 25 |
| 4 · fuera de alcance de ADR-002 | ARQ-00 v1.0 APROBADO §20 | 18 | 25 |

Que un caso canónico **toque** una familia no cierra esa familia: el mínimo canónico del PDP §8 exige ejecutar todos sus casos asignados del banco de 304. `pdp_cases_v0_2.json` publica además el texto literal de cobertura mínima de las 25 familias, comparado carácter a carácter con el DOCX.

---

## 9. T0

Los artefactos congelables —`cases_v0_3.json`, `references_v0_3.json`, `pdp_harness_rules_v0_1.json`— contienen **únicamente** `estado_t0: NO_MEDIDO` y un puntero al fichero de previsión. Ninguna clave de previsión (`expresabilidad_prevista`, `fundamento_de_prevision`, `estado_por_requisito`, `ejecutable_por_t0`, `requiere_t1_t4`) sobrevive en ellos; los casos de nivel 2 y 3 pierden también el veredicto heredado del v0.1.

`t0_preexecution_projection_v0_1.json` es **no normativo, no congelable y sustituible íntegramente** por la ejecución real. Aplica un criterio único y automático a los 52 casos funcionales:

| Previsión | Casos |
|---|---|
| `NO_EXPRESABLE_PREVISTO` | 30 |
| `PARCIALMENTE_EXPRESABLE_PREVISTO` | 14 |
| `EXPRESABLE_PREVISTO` | 5 |
| `NO_EJECUTABLE_CON_UNA_SOLA_IMPLEMENTACION` | 3 (`B04-CA-39`, `PDP-CA-09`, `PDP-CA-22`) |

Las 6 reglas del arnés no reciben previsión. Los 12 casos de nivel 2 y 3 se declaran **no proyectados** con su motivo: no trazan a ningún `B04-RF` y proyectarlos exigiría inventar un estado que nadie ha medido.

---

## 10. Neutralidad

El validador comprueba que ni el corpus de rendimiento, ni las reglas del arnés, ni la matriz de `PDP-CA`, ni el fichero de previsión nombran `ADR002-A/B/C/D` ni ningún descriptor de candidato (`vectorial`, `embedding`, `relacional explícita`, `RRF`, `grafo`, `RDF`, `SPARQL`) ni ninguna tecnología concreta (26 productos y motores).

En los casos y las referencias, un término solo cabe donde **el texto canónico del propio caso lo fija**. Hoy la única mención es `PostgreSQL` en `B04-CA-42` («No usar PostgreSQL» frente a «¿usar PostgreSQL?»), que el canon nombra literalmente: el alias `Postgres` de `ENT-POSTGRESQL` queda respaldado por la misma raíz. Cualquier otra tecnología en cualquier campo neutral falla.

Las cuatro alternativas mínimas de ARQ-00 §23 siguen siendo cuatro y ninguna se prejuzga.

---

## 11. Independencia de los dos corpus

El corpus de conformidad y el de rendimiento son **artefactos independientes**. Comparten versión de contrato, semilla y vocabulario de estados. El de rendimiento **no reproduce los 94 anclajes byte a byte** y no crea referencias funcionales; su léxico es disjunto del léxico protegido del corpus de conformidad por token exacto, singular/plural o sufijo, raíz común de seis caracteres, nombre o alias de entidad y n-grama.

Prohibido fijar cifras de rendimiento sobre el corpus de conformidad y prohibido adjudicar conformidad sobre el corpus de rendimiento.

---

## 12. Puertas

| Puerta | Estado |
|---|---|
| `SRC-ADR002-01` | SATISFECHA |
| `ADR002-TOL-207` | **NO SATISFECHA** · no se aprueba ni se modifica en esta ronda |
| `ADR002-TOL-208` | **NO SATISFECHA** · el corpus no está congelado y T0 no se ha ejecutado |
| `ADR002-TOL-209` | **NO SATISFECHA** |
| `ADR002-TOL-210` | **NO SATISFECHA** |

T0 no se ha ejecutado. `ADR002-A/B/C/D` no se han implementado ni ejecutado.
