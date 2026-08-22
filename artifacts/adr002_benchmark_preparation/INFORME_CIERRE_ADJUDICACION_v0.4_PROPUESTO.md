# Informe de cierre de adjudicación · Corpus v0.4

**Paquete:** 03D · SIRIUS 0.2 — ADR-002 · Cierre de adjudicación del corpus v0.4
**Rama:** `evidence/adr001-spikes`
**Estado:** PROPUESTO · NO CONGELADO — la familia v0.4 pasa a una nueva auditoría independiente.

---

## 1. Matriz fija de aceptación

| # | Criterio | Resultado |
|---|---|---|
| 1 | Los 13 casos EXHAUSTIVA declaran dominio y su cierre se calcula; el generador aborta ante cualquier discrepancia con los conjuntos prescritos | **CUMPLIDO** — 47 casos + 19 ramas con adjudicación calculada; `ESPERADOS`/`ESPERADOS_RAMA` verificados en construcción |
| 2 | El validador recalcula las adjudicaciones sin importar `evaluar_universo` ni ninguna función de cierre del generador | **CUMPLIDO** — `oraculo_universo` propio (iteración plana, parser de fechas real, tokenizador propio, reglas leídas de los JSON); 66 adjudicaciones recalculadas |
| 3 | Universo crítico reconciliado y derivable (5/6/11/12) con censo directo sobre el corpus | **CUMPLIDO** — `MEM-101…112` en PRJ-GAMMA con `valid_from` escalonado; censo en corpus en cada `t_obj` |
| 4 | Barrido de impacto de `DEC-016`: solo `B04-CA-36/R1` cambia | **CUMPLIDO** — 66 adjudicaciones recalculadas sin `DEC-016`; cambios = `["B04-CA-36/R1"]`; cualquier otro cambio aborta |
| 5 | Guardas de neutralidad dentro de cota, calculadas con código independiente, sin regenerar ni relajar | **CUMPLIDO** — las cinco guardas dentro de cota (§5); el corpus de rendimiento quedó byte a byte idéntico |
| 6 | Solo los 16 ficheros autorizados en el diff; versiones anteriores intactas | **CUMPLIDO** — `git status` muestra exactamente los 16 ficheros nuevos; validadores v0.1/v0.2/v0.3 en verde sobre artefactos conservados |

## 2. Cierre de hallazgos de la auditoría v0.3

| Hallazgo | Cierre en v0.4 |
|---|---|
| BLOQ-01 | Dominio + cierre calculado para los 13 EXHAUSTIVA; doble motor (generador/oráculo) |
| BLOQ-02 | CA-22 por `SOLAPA_INTERVALO` 2026-01-10/2026-03-20 (intervalo instanciado conservado); CA-25 por ancla «atlas»; CA-31 por criticidad; CA-36-R1 re-anclada a `DEC-016` (`SOLO_HISTORICO`) |
| BLOQ-03 | Universo crítico en PRJ-GAMMA, textos «…del expediente Gamma», sin traza a CA-31, puente 5/6/11/12 censado sobre el corpus |
| MAT-01 | `operacion_y_modo` clasifica cada modo individualmente (CA-10, CA-24, CA-49 corregidos) |
| MAT-02 | Censo global de cabeceras en `canonical_source_v0_4.py` (más la comprobación contextual del v0.3) |
| MAT-03/04 | Guardas absolutas con cotas fijas y oráculo independiente |
| MAT-05 | `etapa_de_la_rama`; M3/M4 sin escalera E0→E5 (`NO_APLICA` motivado); vocabulario cerrado |
| MAT-06 | PDP-CA-09/22 con `RECUENTO_INDEPENDENCIA_DE_CONSUMIDORES` falsable; sin campos de recuperación |
| MAT-07 | Expansión estricta de métricas: forma desconocida = error, prefijo heredado en continuaciones |
| MAT-08 | `magnitud_inventada()`: ninguna cifra bajo `PENDIENTE_TOL209` salvo identificadores |

## 3. Valores medidos de las guardas

| Guarda | Cota | Medido | Dentro |
|---|---|---|---|
| `im_tema_proyecto_bits` | ≤ 0.01 | 0.002858 | sí |
| `exceso_estado_palabra_max` (n ≥ 40) | ≤ 0.25 | 0.1336 | sí |
| `proyectos_minimos_por_entidad_con_alias` | ≥ 2 | 2 | sí |
| `cuota_maxima_tipo_relacion` | ≤ 0.40 | 0.1667 | sí |
| `relaciones_intra_proyecto` | 0.35–0.65 | 0.5222 | sí |

## 4. Validación ejecutada

| Batería | Resultado |
|---|---|
| Construcción v0.4 (doble ejecución) | Bytes idénticos — determinista |
| `validate_corpus_v0_4.py` | 50 comprobaciones, 0 fallos |
| `validate_corpus_v0_3.py` | 98 comprobaciones, 0 fallos |
| `validate_corpus_v0_2.py` | 62 comprobaciones, 0 fallos |
| `validate_corpus_v0_1` (v0.1) | 33 comprobaciones, 0 fallos |
| `pytest` (suite completa) | 1195 pruebas en verde (290 bajo `experiments/`; 59 nuevas v0.4, 15 funciones negativas) |
| `ruff format` + `ruff check` | Sin hallazgos |

### Pruebas negativas obligatorias (14/14 escenarios, 15 funciones de prueba)

1. Retirar `MEM-006` de la declaración de CA-08 → oráculo falla. 2. Retirar `DEC-014` de CA-22 → oráculo falla. 3. Crítico coherente `MEM-113` en ALFA → oráculo y puente fallan. 4. Pendiente de CA-44 movido a prohibidos → invariante falla. 5. Séptimo crítico coherente en GAMMA → censo en corpus falla. 6. Traza `B04-CA-31` restaurada en `MEM-101` → falla. 7. Variable de insuficiencia inventada → falla. 8. «250 ms» bajo `PENDIENTE_TOL209` → falla. 9. Anexo B duplicado bajo otro contexto → v0.3 ciego (79 filas), censo v0.4 lanza error. 10. Sintaxis de métrica desconocida → error inmediato. 11. Previsión T0 copiada al manifiesto → escaneo falla. 12. Corpus de rendimiento alterado → SHA falla. 13. Correlación tema↔proyecto / alias confinado / relaciones concentradas → guardas fallan. 14. Caso filtrado `DEC-017` y `DEC-016` en BETA → barrido falla.

## 5. Registro de no bloqueantes

### CORRECCIÓN_NO_BLOQUEANTE

- **CNB-01** · Premisa de CA-30 reconciliada con el canon: «Tres resultados con señales distintas» — el cierre pasa de 2 a 3 elementos (incluye `MEM-001`) con consulta instanciada nueva. Declarado en la instanciación.
- **CNB-02** · Premisa de CA-34 reconciliada con el canon: «B04 entrega tres críticos y siete ordinarios» — partición 3+7 con 1 ordinario pendiente vía `OBJETIVO 10` + `CRITICOS_PRIMERO_LUEGO_ID`.
- **CNB-03** · `RX_IDENTIFICADORES_PERMITIDOS` amplía `B\d{2}\b` (bloque a secas) para no marcar como magnitud el texto «Orden y equivalencia B04/B05».

### LIMITACIÓN_CONOCIDA

- **LC-01** · `validate_corpus_v0_2` reescribe (determinísticamente) los artefactos v0.2 al ejecutarse. **Documentado, no corregido**: modificar v0.2 está prohibido por el paquete. Orden recomendado: ejecutar los validadores históricos antes de congelar huellas.
- **LC-02** · El escaneo anti-T0 de `pdp_harness_rules_v0_2.json` se limita a `artefactos[nombre]["reglas"]`: la palabra «expresabilidad_prevista» aparece legítimamente dentro de la propia declaración de campos prohibidos.
- **LC-03** · Las guardas de neutralidad son del arnés (GUARDAS_DERIVADAS_DE_NEUTRALIDAD_SINTETICA), no canon: sus cotas derivan del análisis de la auditoría v0.3, no de un DOCX aprobado.

### TRABAJO_POSTERIOR

- **TP-01** · Auditoría independiente de la familia v0.4 (obligatoria antes de cualquier congelación).
- **TP-02** · Decisión sobre TOL-207/208/209/210 — fuera del alcance de este paquete; siguen NO SATISFECHAS.
- **TP-03** · Ejecución de T0 y de ADR002-A/B/C/D — no autorizadas en esta ronda.

## 6. Alcance del diff

16 ficheros nuevos, cero modificados, cero borrados: 12 en `experiments/adr002/benchmark/` (5 módulos Python + 7 JSON), 2 en `docs/architecture/`, 2 en `artifacts/adr002_benchmark_preparation/`. Las familias v0.1/v0.2/v0.3 quedan intactas byte a byte (verificado por `_conservacion` del validador: 17 artefactos anteriores con huella idéntica).
