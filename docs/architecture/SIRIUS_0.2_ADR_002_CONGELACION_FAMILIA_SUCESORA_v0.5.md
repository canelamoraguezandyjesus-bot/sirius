# SIRIUS 0.2 — ADR-002 · Acta de congelación de la familia sucesora de conformidad v0.5

**Versión:** 1.0
**Estado:** **CONGELADA**
**Fecha:** 3 de agosto de 2026
**Rama:** `evidence/adr001-spikes`
**PR:** #117, **abierto y sin fusionar**

**Autoridad que habilita esta congelación:**

| Documento | Identidad |
|---|---|
| `SIRIUS_0.2_ADR_002_RESOLUCION_PREBENCHMARK_..._v1.0_APROBADA.md` | acta de aprobación, §4 paso 1 |
| `SIRIUS_0.2_ADR_002_RESOLUCION_PREBENCHMARK_..._v0.4_PROPUESTA.md` | blob `191edb43df37a6cd9220212815ee52a1c4b0397e` |
| `SIRIUS_0.2_ADR_002_PAQUETE_RESOLUCION_05_..._v0.4.md` | blob `8e583876aac9f40144ec2a7db2c2270008bf4320` |
| `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_13_FAMILIA_SUCESORA_DE_CONFORMIDAD_v0.1.md` | blob `41482cf363ea5e61e3d90a7b32788af563b98f63` |

**Alcance:** exclusivamente el **paso 1** del plan aprobado — materializar y congelar la familia sucesora de conformidad.

> **No autoriza** la fe de erratas léxica, el arnés de conformidad de `T0`, la proyección experimental ejecutable, la corrección de `common`, fichas sucesoras de `A` o `B`, la implementación de `C` o `D`, el benchmark, ninguna medida de rendimiento, la elección de ganador, tocar Sirius 0.1 productivo ni fusionar el PR #117.

---

## 0. Objeto

Congelar la **familia sucesora de conformidad `v0.5`**, materializada **junto a** la v0.4 conforme al principio append-only, tras una auditoría adversarial independiente de quince puntos con **cero tesis refutadas**.

Esta acta **no modifica ningún fichero existente**. Los artefactos congelados conservan en su interior la etiqueta histórica `PROPUESTO_NO_CONGELADO`: son instantáneas previas a esta aprobación, exactamente igual que en la congelación de la v0.4. **Esta acta prevalece sobre esa etiqueta sin reescribir los ficheros**, porque reescribirlos destruiría la identidad que aquí se congela.

---

## 1. Identidad de la familia

| | |
|---|---|
| **Versión de contrato** | **`0.5`** |
| **Hereda de** | familia v0.4, congelada por `SIRIUS_0.2_ADR_002_CONGELACION_CORPUS_v0.4_APROBADA.md` |
| **Semilla compartida** | `20260726` — la misma de la v0.4, sin cambio |
| **Ahora declarado** | `2026-06-15T00:00:00Z`, sin cambio |
| **Custodia** | **append-only** |
| **Generador** | `experiments/adr002/benchmark/build_corpus_v0_5.py` |
| **Commit de referencia** | `e650b2a` |

**La identidad vinculante de cada artefacto se fija por su blob Git.** Cualquier cambio de un solo byte produce un blob distinto e **invalida la congelación** de ese artefacto.

---

## 2. Artefactos sucesores congelados

Los siete de `CONGELABLES_V0_5` (`schema_v0_5.py`), todos bajo `experiments/adr002/benchmark/`:

| # | Artefacto | Blob Git |
|---|---|---|
| 1 | `conformance_corpus_v0_5.json` | `324f2976f8d4f4aec1d7634a1e16dcc9782c53b0` |
| 2 | `subject_keys_v0_1.json` | `020c10ced48657f57e7fa85076992c6f950dd0fe` |
| 3 | `property_keys_v0_1.json` | `da8953d58a5c17bed7df83e80c5ba3a6b2a27e3f` |
| 4 | `applied_criticality_v0_1.json` | `7dcbba0031e76d4f0763e0d0b853e59584fe3077` |
| 5 | `cases_v0_5.json` | `26919e1016c414697664f93455258cb6492ca48c` |
| 6 | `references_v0_5.json` | `4694ef3bba3a87cae0412895da992ce5e2b54f45` |
| 7 | `benchmark_manifest_v0_5.json` | `d9f97a8153b65f0cedcfc242304fea24570599dd` |

### 2.1 Artefactos heredados sin cambiar un byte

| Artefacto | Blob Git | Papel |
|---|---|---|
| `pdp_cases_v0_3.json` | `2eee45a04dee3d72f52ad00dfd46023d7c5e2199` | el delta no toca PDP |
| `pdp_harness_rules_v0_2.json` | `86e4f4ea6b4af3d445ec0f71c9772b46751a202b` | idem |
| `performance_corpus_v0_2.json` | `4e9e2746e49b158a43eda7826b47c78c41b36e90` | la familia **no mide rendimiento** |

**SHA-256 adicional de `performance_corpus_v0_2.json`:** `c5a161cbdaa7ee150c08e663fa72663324375aa6654f3216a73e90d6b182666b`.

**El manifiesto sucesor cierra la familia completa**: los diez artefactos —siete sucesores y tres heredados— quedan declarados por blob en un único documento, incluidos los que no cambian.

### 2.2 Generadores, validadores y pruebas

| Fichero | Blob Git |
|---|---|
| `experiments/adr002/benchmark/schema_v0_5.py` | `ce395ac30f2131fa2d9971605abe4b0852792081` |
| `experiments/adr002/benchmark/build_corpus_v0_5.py` | `c34d3e5a191a1984c2448e8ea5e3195227f9a6d6` |
| `experiments/adr002/benchmark/validate_corpus_v0_5.py` | `6dfb8d0f2ed84b23873cfb1194f951918ce81665` |
| `experiments/adr002/benchmark/test_corpus_contract_v0_5.py` | `58c52a5507f2964f56c4a61a9faffb4348ec0af0` |
| `experiments/adr002/candidates/test_adr002_discriminante_relacional.py` | `f15d7a4cfee2222651fdff5df819dc805e458834` |
| `artifacts/adr002_benchmark_preparation/validacion_familia_v0.5.json` | `19ca0b2ac1a43d7a32fe958709fca2a1af853ae8` |

---

## 3. La v0.4 permanece intacta

Los siete blobs congelados por el acta de la v0.4, **verificados sobre este HEAD y byte a byte**:

| Artefacto | Blob |
|---|---|
| `conformance_corpus_v0_4.json` | `c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48` |
| `cases_v0_4.json` | `072753b96f4162fe88ce9c96660296349225c7be` |
| `references_v0_4.json` | `3fc9a63705144bf543266de129e17a17ab31c568` |
| `pdp_cases_v0_3.json` | `2eee45a04dee3d72f52ad00dfd46023d7c5e2199` |
| `pdp_harness_rules_v0_2.json` | `86e4f4ea6b4af3d445ec0f71c9772b46751a202b` |
| `performance_corpus_v0_2.json` | `4e9e2746e49b158a43eda7826b47c78c41b36e90` |
| `benchmark_manifest_v0_4.json` | `fa9a2f2b5d8d65aed811f039b2b279c5350d2132` |

**Ninguno cambió.** El propio validador de la v0.5 lo comprueba recalculando el blob Git de cada fichero, y una prueba lo repite.

---

## 4. Orden de materialización y anterioridad

```
1. conformance_corpus_v0_5.json     (corpus + delta)
2. subject_keys_v0_1.json           (dimensiones declaradas del propio ítem)
3. property_keys_v0_1.json          (contenido y sujeto del propio ítem)
4. applied_criticality_v0_1.json    (plano privado, dentro del arnés)
5. cases_v0_5.json
6. references_v0_5.json
7. benchmark_manifest_v0_5.json
```

**La anterioridad no se declara: se comprueba.** Las tres funciones de canal lateral reciben por firma el corpus y **nada más** —verificado con `inspect.signature`—, de modo que no pueden leer casos ni referencias porque no los tienen. La auditoría lo confirmó además por observación directa: instrumentando `Path.read_bytes` y `Path.read_text` durante su ejecución, **los tres canales no abrieron ningún fichero**.

---

## 5. Censos congelados

**Recomputados sobre esta familia. Las constantes `95 / 76 / 19 / 18 / 1` son específicas de la v0.4 y no se copian.**

### 5.1 Corpus

| | v0.4 | **v0.5** |
|---|---|---|
| proyectos | 7 | **8** |
| entidades | 5 | **7** |
| ítems | 95 | **97** |
| recuerdos | 79 | **81** |
| decisiones | 16 | 16 |
| mensajes | 6 | 6 |
| documentos | 5 | 5 |
| relaciones | 9 | **10** |

### 5.2 Criticidad aplicada segura

| | |
|---|---|
| Ítems | **97** |
| Sin criticidad | **78** |
| Con criticidad | **19** |
| `CRITICO` | **18** |
| `IMPORTANTE` | **1** |
| `ACTO_EXPLICITO` | **4** |
| `REQUISITO_O_DECISION_APROBADA` | **2** |
| `ETIQUETA_DE_ESCENARIO` | **12** |
| `REGLA_OPERATIVA_APROBADA` | **1** |
| Razones seguras **distintas** | **8** sobre 19 instancias |
| Reglas de política **distintas** | **7** |

### 5.3 Canales laterales

| Canal | Cobertura | Con valor | `null` | Valores distintos |
|---|---|---|---|---|
| `subject_key_experimental` | **97 / 97** | 9 | 88 | 7 |
| `property_key` | **97 / 97** | 9 | 88 | 9 |

**La ausencia es `null` real, nunca cadena vacía**, y **no elimina el ítem**: impide agruparlo.

---

## 6. Custodia de los canales laterales

`fuente_de_asignacion`, `version_del_vocabulario` y `regla_de_validacion` viven **una sola vez en el manifiesto**. **Por ítem existe únicamente el valor**, `null` incluido: repetir la custodia por ítem la correlacionaría con la partición que la clave induce y entregaría esa partición por una puerta trasera.

### 6.1 `property_key`

- **Origen admitido:** el texto del propio ítem, su sujeto declarado, su clase y su ámbito. **Nada más.**
- **Frontera estructural:** valor no nulo **si y solo si** el ítem declara exactamente una entidad **y** conserva al menos una raíz discriminante tras retirar palabras funcionales y tokens del propio sujeto.
- **Valor:** `PK-<sha256 de las raíces ordenadas>[:12]`. **Opaco**, estable, congelado; **no se calcula durante la consulta**.
- **Legible solo por `common`.** Ningún candidato la recibe.
- **Limitación declarada:** **no reconoce paráfrasis**. Dos ítems equivalentes con vocabulario distinto reciben claves distintas y **no se agrupan**. Es fallo cerrado deliberado: la duda no fusiona.

### 6.2 `subject_key_experimental`

- **Origen:** las entidades que el propio ítem declara en `entity_ids`.
- **Regla:** 0 entidades → `null`; 1 entidad → slug del nombre canónico; 2 o más → `null` (dos sujetos no son un sujeto).
- **El slug no lleva separador.** Es la garantía estructural que impide familias artificiales: `A` calcula su familia de `E3` como `plegar(subject_key).split("-")[0]`, de modo que **sin guion la familia es la clave entera y coincide exactamente con la entidad**. Un validador comprueba además que **ninguna clave es prefijo de otra**.
- **`P-SUJETO-01` (`subject_key := id`) queda expresamente descartada**: fue la proyección de las sondas y es la **más permisiva** para `E3`, no la más conservadora.
- **Legible por `common` y por `ADR002-A`, y por nadie más.**

### 6.3 Criticidad segura

`criticidad.fuente` **bruta permanece privada del arnés y no cruza**: la auditoría lo comprobó buscando cada valor bruto en el artefacto común y no halló ninguno. Cruzan únicamente `nivel`, `razon_segura`, `fuente_de_politica` y `regla_de_politica`, **los cuatro íntegros hasta B05**.

---

## 7. Relación discriminante y frontera entrada/oráculo

| | |
|---|---|
| Proyecto | `PRJ-DELTA`, nuevo, tipo `PROYECTO` |
| Extremos | `MEM-950` (origen) y `MEM-951` (destino), sujetos distintos, mismo proyecto |
| Relación | `REL-010`, tipo **`DERIVA_DE`**, explícita, tipada y dirigida |
| Tipos excluidos | `SUSTITUYE_A` y `CONFLICTO_CON` |
| Condición léxica | **cero tokens indexados compartidos**, medidos con FTS5 `unicode61` `remove_diacritics=1` |

**La condición léxica es más fuerte de lo exigido:** la auditoría midió la intersección con `remove_diacritics` **0, 1 y 2** y con la configuración por omisión, y es **vacía en las cuatro**. La propiedad no depende del ajuste diacrítico.

**Impacto nulo sobre lo heredado:** el barrido recalcula los **66 dominios** con y sin delta y exige **cero cambios**; los obtiene. Hay además una razón estructural registrada: 64 de los 66 están acotados a proyectos existentes y no pueden ver un proyecto nuevo; los dos con `GLOBAL_TODOS` son `B04-CA-01`, anclado al prefijo `redact` que el delta no contiene, y `B04-CA-14`, restringido al grupo homónimo `JUAN` que las entidades del delta no declaran.

**Los bloques heredados de casos y referencias no cambian**, comprobado por igualdad estructural contra `cases_v0_4.json` y `references_v0_4.json`.

### 7.1 Frontera entrada/oráculo

El caso `N4-01` separa los dos planos en **bloques distintos y disjuntos**:

| ENTRADA | ORÁCULO |
|---|---|
| petición | alcance léxico-estructurado |
| extremos | aportado por un salto relacional |
| relación `tipo`/`origen`/`destino` | comportamiento sin la arista |
| consulta propia del destino | estado y justificación |

La referencia se calcula por un **camino independiente**: FTS5 `MATCH` sobre un índice en memoria, no conjuntos de tokens en Python. **Ambos caminos coinciden.**

---

## 8. Demostración funcional del discriminante

Ejecutada sobre una base con el **esquema canónico de Sirius 0.1** —cadena de Alembic hasta `61be4bb269bf`, sin DDL adicional— con `ADR002-A` **sin modificar ni una línea**:

| # | Condición | Resultado |
|---|---|---|
| 1 | una consulta legítima alcanza la semilla | **sí**, por `E1` (clave de sujeto exacta) |
| 2 | `ADR002-A` completo `E0-E5` **no** alcanza el destino | **confirmado**; la escalera recorre `E1`, `E2`, `E3` y `E4` y la parada **no** es `S1` |
| 3 | el destino supera las puertas comunes | **sí**: `G1-G10` sin descartes, `G11` sin descartes, dentro de `G12` |
| 4 | el destino es recuperable por una consulta legítima propia | **sí** |
| 5 | un salto relacional explícito aportaría su identificador | **sí** |
| 6 | borrar la arista elimina ese alcance | **sí** |
| 7 | ningún campo de oráculo participa | **confirmado**: la base no materializa `traza`, `criticidad` ni `procedencia`, y la traza no filtra ningún texto |

**El límite no es la causa.** La cardinalidad es `EXHAUSTIVA` —la escalera se recorre entera—, el límite duro es más ancho que todo el ámbito, no hay desbordamiento y no hay críticos omitidos.

**Control positivo registrado:** una consulta que nombra el sujeto del destino (`"rotor bitacora"`) **sí lo alcanza**. Es la prueba de que el destino no está escondido: es inalcanzable **para `A` desde esa semilla**, no inalcanzable. Esa consulta no es legítima para el caso, porque nombra el destino.

---

## 9. Proyección `T0`

**La familia v0.5 NO regenera la proyección `T0`.**

| | |
|---|---|
| Fichero no regenerado | `t0_preexecution_projection_v0_2.json` |
| Blob observado | `3a241839b7eba84f12a3bbb3c643a17f7b0d0f91` |
| Estado | `NO_NORMATIVO_NO_CONGELABLE` |
| Valor | **observación sin valor vinculante**; no es evidencia congelada |

**Motivo:** regenerarla exigiría proyectar el caso discriminante sobre `T0`, y esa proyección **presupondría el arnés de conformidad de `T0`, que NO EXISTE** y cuya adjudicación es un paso separado del plan aprobado. El acta de la v0.4 §6 prohíbe además modificar el fichero original, y no se ha tocado.

**La regla del manifiesto se cumple declarando la ausencia**: el manifiesto cierra la familia completa registrando expresamente que **no lleva proyección `T0`**. La futura adjudicación del arnés **podrá** usar esta familia sin que nada aquí presuponga que dicho arnés existe. La auditoría lo verificó: **ningún fichero nuevo lleva `t0` en su nombre**.

---

## 10. Integridad de `ADR002-TOL-208`

`rederivation_protocol.CORPUS_CONGELADO` declara **dos** rutas —`conformance_corpus_v0_4.json` y `performance_corpus_v0_2.json`—, ambas verificadas contra su blob esperado, y la línea base histórica `mediciones_linea_base_v0.2.json` conserva su blob `f9f051332d9833fb7e10b27f4820849f00b6fe6c`.

**`TOL-208` permanece íntegra**, porque la familia es append-only y ninguno de esos ficheros cambia un byte.

> **Corrección registrada.** La resolución v0.4 §8.2 afirma que ese arnés «recorre todos los blobs de `CORPUS_CONGELADO` —los siete de v0.4—». Verificado sobre el árbol, `rederivation_protocol.py:77-84` declara **dos**, no siete. La conclusión no cambia y de hecho se refuerza; el dato se registra correctamente en vez de repetirse.

---

## 11. Auditoría adversarial independiente

Ejecutada **intentando refutar** cada tesis, no confirmarla. **Cero refutadas de quince.**

| # | Tesis | Veredicto |
|---|---|---|
| 1 | append-only real | **resiste** — ningún congelado tocado, ningún blob desviado |
| 2 | independencia del oráculo | **resiste** — los tres canales no abren fichero alguno |
| 3 | cobertura total de canales laterales | **resiste** — 0 ítems sin entrada en los tres |
| 4 | ausencia de IDs de casos en campos comunes | **resiste** — 0 coincidencias del patrón |
| 5 | `property_key` ilegible desde candidatos | **resiste** — 0 atributos vetados en las estructuras que un candidato recibe |
| 6 | uso autorizado de `subject_key_experimental` | **resiste** — exactamente `common` y `ADR002-A` |
| 7 | discriminante honesto de `C` | **resiste** — 5 consultas legítimas distintas, ninguna alcanza el destino |
| 8 | cero tokens compartidos | **resiste** — intersección vacía con `rd` 0, 1, 2 y por omisión |
| 9 | paso de puertas del destino | **resiste** — sin descartes en `G1-G10`, `G11` ni `G12` |
| 10 | reproducibilidad | **resiste** — regeneración byte a byte idéntica |
| 11 | consistencia del manifiesto | **resiste** — declara los diez artefactos de la familia |
| 12 | criticidad segura completa | **resiste** — 0 entradas incompletas o espurias |
| 13 | ausencia de benchmark | **resiste** — 0 señales de medición en los siete artefactos |
| 14 | integridad de `TOL-208` | **resiste** — 0 desajustes; línea base intacta |
| 15 | inexistencia presumida del arnés `T0` | **resiste** — 0 ficheros nuevos de `T0` |

**Validador de la familia: 97 comprobaciones, 0 fallos.** Su informe acumula todos los fallos y no aborta en el primero; los dos puntos en los que la construcción **sí** aborta —fuente bruta fuera de la tabla cerrada y campo sin terna asignada— se **provocan** en la validación y en las pruebas, porque un control que nadie ejercita es una promesa.

**Pruebas negativas por mutación: 20**, cada una sobre copias en memoria; el árbol no se toca.

---

## 12. Reglas de custodia posteriores a esta acta

1. **Los siete artefactos sucesores no se modifican.** Cualquier cambio de byte produce un blob distinto e invalida esta congelación.
2. Los siete de la v0.4 **permanecen idénticos**; la v0.5 vive **junto a** ellos.
3. **Cualquier defecto material obliga a una versión sucesora.** **No se arregla en silencio.**
4. Ninguna acta anterior se reescribe.
5. `common`, `ADR002-A`, `ADR002-B`, `src/`, `migrations/` y las pruebas productivas **no cambian**.
6. Reverificación en cualquier momento:

```
git rev-parse <commit>:experiments/adr002/benchmark/<artefacto>
uv run python -m experiments.adr002.benchmark.validate_corpus_v0_5
uv run pytest experiments/adr002 -q
```

---

## 13. Lo que esta acta NO autoriza

- **No** emitir la fe de erratas léxica.
- **No** construir el arnés de conformidad de `T0`.
- **No** construir la proyección experimental ejecutable.
- **No** corregir `common`.
- **No** emitir fichas sucesoras de `ADR002-A` ni `ADR002-B`.
- **No** implementar `ADR002-C` ni `ADR002-D`.
- **No** ejecutar el benchmark ni medir rendimiento.
- **No** elegir ganador.
- **No** reducir la ronda primaria.
- **No** tocar Sirius 0.1 productivo.
- **No** fusionar el PR #117.

---

## 14. Estado tras esta acta

| | |
|---|---|
| Familia sucesora de conformidad v0.5 | **CONGELADA** |
| Familia v0.4 | **intacta**, siete blobs verificados |
| `t0_preexecution_projection_v0_2.json` | intacto, no regenerado, `NO_NORMATIVO_NO_CONGELABLE` |
| `T0-control v1` | intacto; **sin cambio de ficha ni de estado** |
| `ADR002-A v3` | **PREPARADO PARA BENCHMARK**, sin cambio de ficha ni de estado |
| `ADR002-B v5` | **PREPARADO PARA BENCHMARK**, sin cambio de ficha ni de estado |
| `ADR002-C` | **no implementado** |
| `ADR002-D` | **no implementado** |
| `ADR002-TOL-208` | íntegra |
| Benchmark | **BLOQUEADO, NO AUTORIZADO y NO EJECUTADO** |
| Ronda primaria | `T0 + A + B + C + D`, **sin reducción** |
| PR #117 | **abierto y sin fusionar** |

Sigue vigente la condición de la resolución v0.4 §9.5: **ningún benchmark podrá autorizarse con las fichas actuales mientras la discrepancia de identidad del sustrato léxico siga abierta.** Esa fe de erratas es el **paso 3** del plan y **no** se emite aquí.

**Siguiente movimiento del plan aprobado, que esta acta no ejecuta ni autoriza:** paso 2 — emitir la fe de erratas amplia del sustrato léxico.
