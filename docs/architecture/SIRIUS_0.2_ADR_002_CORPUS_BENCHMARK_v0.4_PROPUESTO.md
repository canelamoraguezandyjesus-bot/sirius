# SIRIUS 0.2 — ADR-002 · Corpus del benchmark

**Versión:** 0.4
**Estado:** PROPUESTO · NO CONGELADO
**Rama:** `evidence/adr001-spikes`
**Paquete ejecutado:** 03D · Cierre de adjudicación del corpus v0.4
**No autoriza:** congelar, aprobar tolerancias, ejecutar T0, implementar `ADR002-A/B/C/D`, abrir otro PR ni merge.

Los artefactos v0.1, v0.2 y v0.3 se conservan byte a byte. La v0.4 es un **delta sobre la v0.3**: solo añade ficheros nuevos.

---

## 1. Artefactos de la familia v0.4

| Fichero | Contenido | Congelable |
|---|---|---|
| `conformance_corpus_v0_4.json` | 95 ítems (16 decisiones), 31 colisiones controladas, universo crítico reconciliado, `DEC-016`, cierre verificado de CA-47 | Sí (no congelado) |
| `cases_v0_4.json` | 50 casos nivel 1 B04 + 2 PDP + 5 nivel 2 + 7 nivel 3; 19 ramas canónicas; **47 casos y 19 ramas con adjudicación calculada** | Sí (no congelado) |
| `references_v0_4.json` | 52 referencias: 50 de recuperación B04 + 2 de recuento PDP | Sí (no congelado) |
| `pdp_cases_v0_3.json` | Casos PDP con motivo exacto para PDP-CA sin fila RED («ninguna fila RED del Anexo B asigna este PDP-CA») y nota `responsable_de_familia ≠ ejecutor_del_caso` | Sí (no congelado) |
| `pdp_harness_rules_v0_2.json` | Reglas de arnés con `estado_de_la_fuente` (`APROBADO` / `PROPUESTO` / `PUERTA_NO_SATISFECHA`) por regla | Sí (no congelado) |
| `t0_preexecution_projection_v0_2.json` | Proyección T0 **no normativa y no congelable**; los congelables solo llevan `estado_t0 = NO_MEDIDO` + referencia externa | No, por diseño |
| `benchmark_manifest_v0_4.json` | Huellas, censo de cabeceras, congelables, alcance del corpus de rendimiento, guardas, universo crítico, barrido `DEC-016` | Sí (no congelado) |

Módulos: `schema_v0_4.py` (contrato), `canonical_source_v0_4.py` (lector, extiende v0.3), `build_corpus_v0_4.py` (generador + `evaluar_universo`), `validate_corpus_v0_4.py` (oráculo independiente), `test_corpus_contract_v0_4.py` (59 pruebas; 15 funciones negativas para las 14 mutaciones obligatorias).

---

## 2. Corpus de conformidad

- **95 ítems**: los 94 del v0.3 con dos modificaciones declaradas (traslado de `MEM-101…112` a PRJ-GAMMA y textos «…del expediente Gamma»; `valid_from` escalonado con `recorded_at = valid_from`) más el ancla nueva `DEC-016`.
- `MEM-101…112` ya no llevan traza a `B04-CA-31`; su traza final es `CA-26/38/44` y la criticidad se declara como instanciación compartida. `CA-31` queda íntegramente en PRJ-ALFA con exactamente cinco críticos (`DEC-003`, `DEC-010`, `MEM-014`, `MEM-016`, `MEM-025`).
- `DEC-016`: PRJ-ALFA, texto de aforo, `valid_from` 2026-01-05, `valid_to` 2026-03-01, `recorded_at ≤ valid_from`, traza únicamente `B04-CA-36`. El generador ejecuta un barrido de impacto: retirar `DEC-016` solo puede cambiar `B04-CA-36/R1`; cualquier otro cambio aborta la construcción.

### Puente del universo crítico (5 / 6 / 11 / 12)

| Instante | PRJ-ALFA | PRJ-GAMMA |
|---|---|---|
| vigente (CA-31) | 5 | — |
| 2026-02-01 (CA-44) | — | 6 |
| 2026-04-01 (CA-26) | — | 11 |
| 2026-06-15 (CA-38) | — | 12 |

El validador y una prueba independiente censan los críticos vigentes **directamente sobre el corpus** en cada instante, además de verificar las adjudicaciones declaradas.

---

## 3. Adjudicación calculada

Cada caso funcional declara un dominio y su cierre se **calcula**, nunca se escribe a mano:

- Generador: `evaluar_universo(corpus, dominio)` + `adjudicar()`; el módulo aborta si el cierre calculado difiere del esperado registrado en `ESPERADOS`.
- Validador: oráculo propio (`oraculo_universo`) que **no importa** ninguna función de cierre del generador — iteración plana del corpus, parser de fechas real, tokenizador propio, reglas leídas de los artefactos JSON. Recalcula las 66 adjudicaciones (47 casos + 19 ramas).
- Campos heredados: `instanciacion.elegibles = resultado_esperado`; `instanciacion.prohibidos = excluidos ∪ prohibidos ∪ decoys` (ordenados); en los casos multirrama sin dominio propio (`CA-36`, `CA-47`) los conjuntos de nivel caso son la unión de los de sus ramas.

## 4. Insuficiencia y modos

- Cada rama declara `etapa_de_la_rama`; los modos `M3`/`M4` no recorren la escalera E0→E5 (su insuficiencia es `NO_APLICA` con razón verificable). `CA-49-R1` (M3) mantiene E4 porque el canon la nombra.
- Vocabulario cerrado de variables observables de insuficiencia en `schema_v0_4.py` (`VARIABLES_INSUFICIENCIA`, 11 entradas).
- Ningún texto bajo `PENDIENTE_TOL209` puede contener magnitudes numéricas; los identificadores (`TOL-…`, `RED-…`, `B04-…`, `§9`, `v0.4`, …) están exentos vía `RX_IDENTIFICADORES_PERMITIDOS`.
- `operacion_y_modo`: la operación de campo es siempre `DERIVADO_PROPUESTO`; cada modo se clasifica individualmente (`CA-10` → M4 canónico / M1 derivado; `CA-24` → M1 canónico / M4 derivado; `CA-49` → M4 canónico / M3 derivado; `CA-09` ambos canónicos).

## 5. Corpus de rendimiento

`performance_corpus_v0_2.json` queda **byte a byte idéntico** (SHA-256 `c5a161cbdaa7ee150c08e663fa72663324375aa6654f3216a73e90d6b182666b`, registrado en el manifiesto y verificado por el validador con su propio cálculo).

**Alcance delimitado** — mide: coste, almacenamiento, latencia, construcción, reconstrucción, estabilidad, escalabilidad sintética. **No mide**: calidad funcional, exactitud semántica, comparación de señales entre ADR002-A/B/C/D, validación de los tres ejes temporales.

**Guardas** (`GUARDAS_DERIVADAS_DE_NEUTRALIDAD_SINTETICA`, del arnés, no canon), calculadas por un oráculo independiente; si el corpus congelado incumpliera una, se informa sin regenerar ni relajar:

| Guarda | Cota | Medido |
|---|---|---|
| IM tema↔proyecto | ≤ 0.01 bits | 0.002858 |
| Exceso estado↔palabra (n ≥ 40) | ≤ 0.25 | 0.1336 |
| Proyectos por entidad con alias | ≥ 2 | 2 |
| Cuota máxima por tipo de relación | ≤ 0.40 | 0.1667 |
| Relaciones intraproyecto | 0.35 – 0.65 | 0.5222 |

## 6. Validación

- `validate_corpus_v0_4.py`: **50 comprobaciones, 0 fallos** → `artifacts/adr002_benchmark_preparation/validacion_corpus_v0.4.json`.
- Validadores históricos intactos y en verde: v0.3 (98), v0.2 (62, con su comportamiento mutante **documentado, no corregido**), v0.1 (33).
- `pytest`: suite completa del repositorio en verde (1195 pruebas; 290 bajo `experiments/`); 59 pruebas nuevas de la v0.4, de ellas 15 funciones negativas que cubren las 14 mutaciones obligatorias (el escenario 13 se reparte en dos funciones).
- Construcción determinista: doble ejecución del generador produce bytes idénticos.

## 7. Estado

PROPUESTO. Nada se congela con este paquete. La familia v0.4 será sometida a una nueva auditoría independiente; `ADR002-TOL-207/208/209/210` siguen NO SATISFECHAS.
