# SIRIUS 0.2 — ADR-002 · Acta de congelación de la familia sucesora de conformidad v0.6

**Versión:** 1.0
**Estado:** **CONGELADA · FAMILIA VIGENTE**
**Fecha:** 3 de agosto de 2026
**Rama:** `evidence/adr001-spikes`
**HEAD de partida:** `216182b2edb344dd9906d57419ff414670e8d061`
**PR:** #117, **abierto y sin fusionar**

**Alcance:** corregir **un solo defecto** —`B04-CA-19`— y cerrar definitivamente el **paso 1** del plan aprobado. Nada más.

> **No autoriza** la fe de erratas léxica, el arnés de conformidad de `T0`, la proyección experimental ejecutable, la corrección de `common`, fichas sucesoras de `A` o `B`, la implementación de `C` o `D`, el benchmark, ninguna medida de rendimiento, la elección de ganador, tocar Sirius 0.1 productivo ni fusionar el PR #117.

---

## 1. El defecto de la v0.5

`B04-CA-19` exige que **`DEC-006`, `DEC-007` y `DEC-008`** formen un **grupo con representante justificado y tres procedencias**.

En la familia v0.5 los tres:

- comparten el **texto literal** «La plataforma de despliegue aprobada es Nimbo.»;
- aportan **tres procedencias distintas**: `DOC-001`, `DOC-002` y `MSG-030`;
- pero **ninguno declara entidad**, de modo que la regla aprobada les asigna

```
subject_key_experimental = null
property_key             = null
```

La regla de agrupación aprobada **prohíbe agrupar cuando esos ejes son desconocidos** —la duda no fusiona—, de modo que `CA-19` **no era estructuralmente agrupable** sobre la v0.5.

**Consecuencia registrada:** la v0.5 **permanece congelada e intacta como identidad histórica**, y **queda SUSTITUIDA como familia vigente**. No se reescribe, no se corrige y no se borra.

---

## 2. La corrección, mínima

1. **Una entidad sintética**, y solo una:

| | |
|---|---|
| Identificador | `ENT-PLATAFORMA-DESPLIEGUE` |
| Nombre canónico | `plataforma de despliegue` |
| Alias | ninguno |
| Grupo homónimo | `null` |

   Sin alias **deliberadamente**: la regla de `property_key` resta del texto los tokens del sujeto, y un alias inventado cambiaría el predicado resultante sin que ninguna fuente lo justifique.

2. **Asignada exclusivamente** a `DEC-006`, `DEC-007` y `DEC-008`. La justificación es **el texto idéntico de los tres**, no su destino en el banco. El generador **aborta** si alguno de los tres no lleva ese texto.

3. **Los dos canales laterales se regeneran con la regla ya aprobada.** La regla **no se reescribe: se invoca.** `construir_subject_keys` y `construir_property_keys` de la v0.6 llaman literalmente a las funciones de `build_corpus_v0_5` y solo cambian la cabecera del artefacto.

4. **Resultado, producido por el generador determinista y no escrito a mano:**

| Ítem | `subject_key_experimental` | `property_key` | Procedencia |
|---|---|---|---|
| `DEC-006` | `plataformadedespliegue` | `PK-d291da76418f` | `DOC-001` |
| `DEC-007` | `plataformadedespliegue` | `PK-d291da76418f` | `DOC-002` |
| `DEC-008` | `plataformadedespliegue` | `PK-d291da76418f` | `MSG-030` |

**`CA-19` es ahora estructuralmente agrupable:** mismo sujeto no nulo, misma propiedad no nula, tres procedencias distintas conservadas.

---

## 3. Identidad de la familia

| | |
|---|---|
| **Versión de contrato** | **`0.6`** |
| **Hereda de** | familia v0.5 |
| **Familia vigente** | **`0.6`** |
| **Familia sustituida** | `0.5` — congelada, histórica, **no vigente** |
| **Semilla compartida** | `20260726`, sin cambio |
| **Ahora declarado** | `2026-06-15T00:00:00Z`, sin cambio |
| **Custodia** | **append-only** |
| **Generador** | `experiments/adr002/benchmark/build_corpus_v0_6.py` |
| **Commit de referencia** | `09a3282812abcc405b638666bd6f6ecf0b00bff7` |

---

## 4. Artefactos versionados y sus blobs

Solo cuatro. Todo lo demás se hereda.

| # | Artefacto (`experiments/adr002/benchmark/`) | Blob Git |
|---|---|---|
| 1 | `conformance_corpus_v0_6.json` | `561d9dee8f215e4692d22f194c5972b09b5d3027` |
| 2 | `subject_keys_v0_2.json` | `f6c0f49b4f084d8b5d364d7ec6e1ba7562a5e302` |
| 3 | `property_keys_v0_2.json` | `321383be53dc65859000cf557b5b78e8dafc1901` |
| 4 | `benchmark_manifest_v0_6.json` | `c709ecabe493ef4c6f6514edf31f9726823e1508` |

### 4.1 Generador, validador y pruebas

| Fichero | Blob Git |
|---|---|
| `experiments/adr002/benchmark/schema_v0_6.py` | `e42714ae04031c24da73bbcfd875c0f1af29a64c` |
| `experiments/adr002/benchmark/build_corpus_v0_6.py` | `92f17a89891187cad3d1fce47c8f62d1e228a2d8` |
| `experiments/adr002/benchmark/validate_corpus_v0_6.py` | `af952307c91d6b8b09b4a22de43de6c7190ef4dd` |
| `experiments/adr002/benchmark/test_corpus_contract_v0_6.py` | `54f4c5d753a7902cabce38dc75d89f7c9bc3f530` |
| `artifacts/adr002_benchmark_preparation/validacion_familia_v0.6.json` | `b4d4c47f6a1365139cef37714410bf3adfee369e` |

### 4.2 Heredados por blob, sin regenerar un byte

| Artefacto | Blob | Origen |
|---|---|---|
| `cases_v0_5.json` | `26919e1016c414697664f93455258cb6492ca48c` | v0.5 |
| `references_v0_5.json` | `4694ef3bba3a87cae0412895da992ce5e2b54f45` | v0.5 |
| `applied_criticality_v0_1.json` | `7dcbba0031e76d4f0763e0d0b853e59584fe3077` | v0.5 |
| `pdp_cases_v0_3.json` | `2eee45a04dee3d72f52ad00dfd46023d7c5e2199` | v0.4 |
| `pdp_harness_rules_v0_2.json` | `86e4f4ea6b4af3d445ec0f71c9772b46751a202b` | v0.4 |
| `performance_corpus_v0_2.json` | `4e9e2746e49b158a43eda7826b47c78c41b36e90` | v0.4 |

**Heredarlos solo es honesto porque el barrido de impacto lo permite:** los **66 dominios** se recalculan con y sin la entidad y dan **cero cambios**. Si alguna adjudicación hubiera cambiado, heredar casos y referencias sería mentir.

**Razón estructural registrada:** los únicos dominios que filtran por entidad lo hacen contra `ENT-PROY-ALFA`, `ENT-VEHICULO`, `ENT-POSTGRESQL` o el grupo homónimo `JUAN`. Una entidad nueva sin grupo homónimo no coincide con ninguno, y el resto de dominios no mira `entity_ids`.

---

## 5. La v0.4 y la v0.5 permanecen intactas

**v0.4**, siete blobs verificados:

| Artefacto | Blob |
|---|---|
| `conformance_corpus_v0_4.json` | `c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48` |
| `cases_v0_4.json` | `072753b96f4162fe88ce9c96660296349225c7be` |
| `references_v0_4.json` | `3fc9a63705144bf543266de129e17a17ab31c568` |
| `pdp_cases_v0_3.json` | `2eee45a04dee3d72f52ad00dfd46023d7c5e2199` |
| `pdp_harness_rules_v0_2.json` | `86e4f4ea6b4af3d445ec0f71c9772b46751a202b` |
| `performance_corpus_v0_2.json` | `4e9e2746e49b158a43eda7826b47c78c41b36e90` |
| `benchmark_manifest_v0_4.json` | `fa9a2f2b5d8d65aed811f039b2b279c5350d2132` |

**v0.5**, siete blobs verificados:

| Artefacto | Blob |
|---|---|
| `conformance_corpus_v0_5.json` | `324f2976f8d4f4aec1d7634a1e16dcc9782c53b0` |
| `subject_keys_v0_1.json` | `020c10ced48657f57e7fa85076992c6f950dd0fe` |
| `property_keys_v0_1.json` | `da8953d58a5c17bed7df83e80c5ba3a6b2a27e3f` |
| `applied_criticality_v0_1.json` | `7dcbba0031e76d4f0763e0d0b853e59584fe3077` |
| `cases_v0_5.json` | `26919e1016c414697664f93455258cb6492ca48c` |
| `references_v0_5.json` | `4694ef3bba3a87cae0412895da992ce5e2b54f45` |
| `benchmark_manifest_v0_5.json` | `d9f97a8153b65f0cedcfc242304fea24570599dd` |

**Ninguno cambió.** El validador de la v0.6 recalcula el blob Git de los catorce y una prueba lo repite.

`t0_preexecution_projection_v0_2.json` conserva su blob observado `3a241839b7eba84f12a3bbb3c643a17f7b0d0f91` y **sigue sin regenerarse**, por el mismo motivo que en la v0.5: hacerlo presupondría el arnés de conformidad de `T0`, que **no existe**.

---

## 6. Alcance del cambio en el corpus

| | v0.5 | **v0.6** |
|---|---|---|
| proyectos | 8 | 8 |
| **entidades** | 7 | **8** |
| ítems | 97 | 97 |
| recuerdos | 81 | 81 |
| decisiones | 16 | 16 |
| mensajes | 6 | 6 |
| documentos | 5 | 5 |
| relaciones | 10 | 10 |

**No se añade ni se quita un solo ítem.** No se toca ninguna relación, mensaje, documento ni proyecto. En los tres ítems de `CA-19` **lo único que cambia es `entity_ids`**, y ningún ítem ajeno a `CA-19` cambia un byte: ambas cosas las comprueba el validador comparando elemento a elemento contra la v0.5.

### 6.1 Canales laterales

| Canal | Cobertura | v0.5 con valor | **v0.6 con valor** | v0.5 `null` | **v0.6 `null`** | Valores distintos |
|---|---|---|---|---|---|---|
| `subject_key_experimental` | **97 / 97** | 9 | **12** | 88 | **85** | 7 → **8** |
| `property_key` | **97 / 97** | 9 | **12** | 88 | **85** | 9 → **10** |

Ninguna clave ajena a `CA-19` cambia respecto de la v0.5 — comprobado clave a clave. La ausencia sigue siendo `null` real, nunca cadena vacía, y ninguna clave de sujeto es prefijo de otra.

---

## 7. El discriminante relacional sigue en pie

`MEM-950` → `MEM-951`, relación `REL-010` de tipo `DERIVA_DE`.

Los dos extremos, la arista y sus claves de sujeto son **byte a byte idénticos** a los de la v0.5, el ámbito `PRJ-DELTA` sigue conteniendo exactamente esos dos ítems, y su intersección de tokens indexados sigue siendo **vacía** bajo el tokenizador real. Con entradas idénticas, el comportamiento de la recuperación es idéntico por determinismo, y la prueba funcional real sobre `ADR002-A` —`candidates/test_adr002_discriminante_relacional.py`— **sigue ejecutándose sin cambios y en verde**.

---

## 8. Pruebas

| # | Demostración | Resultado |
|---|---|---|
| 1 | `DEC-006/007/008` comparten sujeto | **sí**, `plataformadedespliegue` |
| 2 | `DEC-006/007/008` comparten propiedad | **sí**, `PK-d291da76418f` |
| 3 | `CA-19` es estructuralmente agrupable | **sí**, con sus tres procedencias |
| 4 | cambiar la entidad de uno rompe la agrupación | **sí** |
| 5 | cambiar la propiedad de uno rompe la agrupación | **sí** |
| 6 | los canales se generan sin leer casos ni referencias | **sí** — instrumentada la lectura de ficheros: **cero** aperturas |
| 7 | el discriminante `MEM-950` → `MEM-951` continúa | **sí** |
| 8 | v0.4 y v0.5 byte a byte intactas | **sí**, catorce blobs |
| 9 | `ADR002-TOL-208` intacta | **sí** |
| 10 | Quality verde sobre el HEAD final | **sí** |

Complementarias: que en la v0.5 ambos ejes **eran** nulos —sin lo cual la corrección no tendría objeto—; que las claves salen del generador y no están escritas a mano; que quitar la entidad de uno devuelve el defecto; que un texto distinto en uno de los tres **aborta** la construcción; y que la entidad en un cuarto ítem la detecta el validador.

**Validador v0.6: 75 comprobaciones, 0 fallos.** Acumula todos los fallos y no aborta en el primero.

---

## 9. Reglas de custodia posteriores a esta acta

1. Los cuatro artefactos versionados **no se modifican**.
2. La v0.4 y la v0.5 **permanecen idénticas**; la v0.6 vive **junto a** ellas.
3. **Cualquier defecto material obliga a una versión sucesora. No se arregla en silencio.**
4. Ninguna acta anterior se reescribe.
5. `common`, `ADR002-A`, `ADR002-B`, `src/`, `migrations/` y las pruebas productivas **no cambian**.
6. Reverificación en cualquier momento:

```
git rev-parse <commit>:experiments/adr002/benchmark/<artefacto>
uv run python -m experiments.adr002.benchmark.validate_corpus_v0_6
uv run pytest experiments/adr002 -q
```

---

## 10. Prohibición del benchmark

**El benchmark permanece BLOQUEADO, NO AUTORIZADO y NO EJECUTADO.** La ronda primaria sigue siendo `T0 + ADR002-A + ADR002-B + ADR002-C + ADR002-D`, **sin reducción**.

Esta acta no satisface ninguna puerta de arranque, no mide nada, no compara candidatos y no elige ganador. Sigue vigente la condición de la resolución v0.4 §9.5: **ningún benchmark podrá autorizarse con las fichas actuales mientras la discrepancia de identidad del sustrato léxico siga abierta**, y esa fe de erratas **no** se emite aquí.

---

## 11. Estado tras esta acta

| | |
|---|---|
| Familia v0.4 | **intacta** |
| Familia v0.5 | **intacta, congelada, HISTÓRICA y NO VIGENTE** |
| Familia v0.6 | **CONGELADA y VIGENTE** |
| `t0_preexecution_projection_v0_2.json` | intacto, no regenerado |
| `T0-control v1` | intacto; **sin cambio de ficha ni de estado** |
| `ADR002-A v3` | **PREPARADO PARA BENCHMARK**, sin cambio |
| `ADR002-B v5` | **PREPARADO PARA BENCHMARK**, sin cambio |
| `ADR002-C` | **no implementado** |
| `ADR002-D` | **no implementado** |
| `ADR002-TOL-208` | íntegra |
| Benchmark | **no ejecutado ni autorizado** |
| PR #117 | **abierto y sin fusionar** |

**El paso 1 del plan aprobado queda cerrado definitivamente.** El paso 2 —la fe de erratas amplia del sustrato léxico— **no** se ejecuta ni se autoriza aquí.
