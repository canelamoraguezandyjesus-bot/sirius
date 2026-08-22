# SIRIUS 0.2 — ADR-002 · Acta de congelación del corpus v0.4

**Versión:** 1.0
**Estado:** **APROBADO · CONGELADO**
**Fecha:** 27 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Autoridad:** Usuario / Proyecto Sirius
**Commit auditado:** `d27352b9f03dfc6a4d939b855474ce0ad1c2fc86`
**Autorización explícita del usuario:** «Sí, venga»
**Alcance:** exclusivamente el **paso 1 de `ADR002-TOL-208`** — congelar el corpus del benchmark. Los pasos 2 (ejecutar T0 sobre el corpus congelado) y 3 (rederivar la comparación de línea base) **no** quedan ejecutados ni autorizados por esta acta.
**No autoriza:** ejecutar T0, implementar o ejecutar `ADR002-A/B/C/D`, aprobar `ADR002-TOL-207`, declarar satisfechas `ADR002-TOL-208/209/210`, modificar Sirius 0.1, abrir otro PR ni fusionar el PR #117.

---

## 0. Objeto

Materializar la aprobación explícita del usuario para **congelar la familia de corpus ADR-002 v0.4**, tras la auditoría adversarial final independiente ejecutada sobre el commit `d27352b9f03dfc6a4d939b855474ce0ad1c2fc86`, cuyo veredicto fue **APROBABLE CON CORRECCIONES NO BLOQUEANTES** con **cero hallazgos bloqueantes** según la matriz cerrada de bloqueo (criterios 1–6).

Esta acta **no modifica ningún archivo existente**. Los siete artefactos congelados conservan en su interior las etiquetas históricas `PROPUESTO` o `PROPUESTO_NO_CONGELADO`: son instantáneas previas a esta aprobación, exactamente igual que en los casos ya descritos por `docs/canonical/STATUS.md`. **Esta acta prevalece sobre esas etiquetas sin reescribir los ficheros**: reescribirlos destruiría la identidad que aquí se congela.

## 1. Identidad vinculante

**La identidad vinculante de cada artefacto congelado se fija por su blob Git**, calculado sobre el contenido exacto presente en el commit auditado. Cualquier cambio de un solo byte produce un blob distinto e **invalida la congelación** de ese artefacto. Para `performance_corpus_v0_2.json` se registra además su SHA-256, ya congelado en `schema_v0_4.py` y en el manifiesto.

## 2. Artefactos congelados

Los siete congelables declarados por `CONGELABLES_V0_4` (`schema_v0_4.py`), todos bajo `experiments/adr002/benchmark/`:

| # | Artefacto | Blob Git |
|---|---|---|
| 1 | `conformance_corpus_v0_4.json` | `c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48` |
| 2 | `cases_v0_4.json` | `072753b96f4162fe88ce9c96660296349225c7be` |
| 3 | `references_v0_4.json` | `3fc9a63705144bf543266de129e17a17ab31c568` |
| 4 | `pdp_cases_v0_3.json` | `2eee45a04dee3d72f52ad00dfd46023d7c5e2199` |
| 5 | `pdp_harness_rules_v0_2.json` | `86e4f4ea6b4af3d445ec0f71c9772b46751a202b` |
| 6 | `performance_corpus_v0_2.json` | `4e9e2746e49b158a43eda7826b47c78c41b36e90` |
| 7 | `benchmark_manifest_v0_4.json` | `fa9a2f2b5d8d65aed811f039b2b279c5350d2132` |

**SHA-256 adicional del artefacto 6:** `c5a161cbdaa7ee150c08e663fa72663324375aa6654f3216a73e90d6b182666b` — idéntico byte a byte al introducido por el paquete 03C y verificado de nuevo en esta congelación.

### 2.1 Excluido de la congelación

| Artefacto | Blob observado | Estado |
|---|---|---|
| `experiments/adr002/benchmark/t0_preexecution_projection_v0_2.json` | `3a241839b7eba84f12a3bbb3c643a17f7b0d0f91` | **`NO_NORMATIVO_NO_CONGELABLE`** |

La proyección T0 queda **expresamente fuera** del paquete congelado, conforme a `CONGELABLES_V0_4`/`NO_CONGELABLES_V0_4`. Es sustituible íntegramente por la ejecución real de T0 y su blob se registra solo como observación, sin valor vinculante.

## 3. Correcciones no bloqueantes registradas

Ninguna exige rehacer artefactos; ninguna reabre el corpus.

**CNB-A · Convención de fronteras temporales.** Se declara como instanciación, con el comportamiento verificado en ambos motores:

- `SOLAPA_INTERVALO`: **cerrado en ambos extremos**;
- `VIGENTE_EN_INSTANTE`: **semiabierto** `[valid_from, valid_to)`;
- `OCCURRED_EN_INTERVALO`: **semiabierto** `[desde, hasta)`;
- `REGISTRADO_HASTA`: **inclusivo**;
- un **extremo desconocido no descalifica por sí solo**.

Ningún elemento del corpus congelado pisa una frontera que distinga convenciones (verificado en la auditoría).

**CNB-B · Semántica del recuento de PDP-CA-09.** El futuro adjudicador debe contar la independencia de consumidores mediante **componentes conexos (union-find)**: **compartir al menos una dependencia específica une consumidores**. Las referencias congeladas actuales **no cambian**: sobre sus datos (conjuntos idénticos) ambas semánticas coinciden en el recuento 2.

**CNB-C · Premisa de CA-25.** El corpus conserva **dos** usos textuales materializados de «Atlas» (PRJ-ALFA y PRJ-GAMMA), no tres. Se acepta como **limitación de instanciación** porque el resultado `{MEM-011}` y la protección de ámbito (MEM-018 como decoy) permanecen correctos.

**CNB-D · Endurecimiento opcional del validador.** Fijar en el validador los conjuntos literales de los trece casos EXHAUSTIVA (como ya hace con CA-47 R1/R2/R3) queda como endurecimiento **opcional**. **No reabre el corpus.**

## 4. Limitaciones conocidas registradas

De la auditoría adversarial final (LC-A a LC-G) y de las limitaciones declaradas que permanecen vigentes (LC-H, LC-I):

- **LC-A** — La **fidelidad dominio↔canon** no la verifica el validador (que verifica coherencia corpus↔dominio declarado): queda controlada mediante la **auditoría independiente** ya ejecutada y la **congelación por huella** de esta acta; toda regeneración posterior cambia blobs y es detectable.
- **LC-B** — Existen **constantes compartidas** entre esquema, generador y validador (`schema_v0_4.py`: premisas 5/6/11/12, SHA del corpus de rendimiento, cotas, vocabularios); una alteración coherente exige editar código y se controla por revisión de diffs, no por el validador.
- **LC-C** — El **escaneo anti-T0 es léxico e incompleto**: no cubre la zona no-`reglas` de `pdp_harness_rules_v0_2.json` (LC-02 del constructor) ni redacciones fuera del vocabulario cerrado.
- **LC-D** — Las **magnitudes escritas con palabras** («doscientos cincuenta milisegundos») no se detectan; sí todas las formas numéricas probadas, incluidos dígitos Unicode.
- **LC-E** — Las **correlaciones parciales débiles** del corpus de rendimiento pueden quedar bajo las cotas de las guardas (p. ej. marcado de ~10 % de los textos: IM 0,0076 < 0,01); el escenario pleno sí dispara la guarda.
- **LC-F** — Los **validadores históricos v0.1/v0.2 pueden cambiar mtime sin cambiar bytes** (reescritura determinista idéntica, LC-01 del constructor); v0.3 y v0.4 no tocan nada.
- **LC-G** — Diferencia **latente** en la frontera `valid_to == inicio del intervalo`: `SOLAPA_INTERVALO` incluye un elemento que `VIGENTE_EN_INSTANTE` ya no consideraría vigente en ese instante. Ningún elemento congelado la ejercita; ligada a CNB-A.
- **LC-H** — La **neutralidad experimental plena entre `ADR002-A/B/C/D`** solo podrá verificarse cuando existan candidatos ejecutables; la neutralidad léxica y las guardas sintéticas están verificadas.
- **LC-I** — La **paráfrasis semántica sin solapamiento léxico** no es detectable automáticamente por el léxico protegido ni por las guardas actuales.

## 5. Estado de las puertas de arranque tras esta acta

| Puerta | Estado |
|---|---|
| `SRC-ADR002-01` · fuentes canónicas completas | **SATISFECHA** |
| `ADR002-TOL-207` · presupuesto absoluto de almacenamiento | **NO SATISFECHA** |
| `ADR002-TOL-208` · **paso 1: corpus congelado** | **COMPLETADO** — por esta acta |
| `ADR002-TOL-208` · global (pasos 2 y 3) | **NO SATISFECHA** |
| `ADR002-TOL-209` · protocolo común de medición | **NO SATISFECHA** |
| `ADR002-TOL-210` · ficha de candidato | **NO SATISFECHA** |

**El benchmark sigue bloqueado.** Esta acta completa un paso de una puerta; no satisface ninguna puerta completa.

## 6. Lo que esta acta no autoriza

- **No** ejecutar T0.
- **No** implementar ni ejecutar `ADR002-A`, `ADR002-B`, `ADR002-C` ni `ADR002-D`.
- **No** modificar ninguno de los siete JSON congelados.
- **No** modificar la proyección T0.
- **No** aprobar `ADR002-TOL-207`.
- **No** declarar satisfechas `ADR002-TOL-208`, `ADR002-TOL-209` ni `ADR002-TOL-210`.
- **No** tocar Sirius 0.1 (`src/`, `tests/`, `migrations/`, configuración productiva).
- **No** abrir otro PR.
- **No** fusionar el PR #117.

## 7. Reglas de custodia

1. **Los siete artefactos congelados no se modifican.** Cualquier cambio de byte produce un blob distinto e invalida esta congelación.
2. Una versión posterior del corpus se materializa **junto a** la v0.4, con nueva acta y nuevos blobs; **no se sobrescribe** ningún congelado.
3. Los pasos 2 y 3 de `ADR002-TOL-208` deben ejecutarse **sobre exactamente estos blobs**; toda cifra que produzcan queda vinculada a ellos.
4. Las etiquetas internas `PROPUESTO`/`PROPUESTO_NO_CONGELADO` de los JSON son historia congelada y no se corrigen.
5. Reverificación en cualquier momento:

```
git rev-parse <commit>:experiments/adr002/benchmark/<artefacto>   # debe devolver el blob de §2
sha256sum experiments/adr002/benchmark/performance_corpus_v0_2.json
```

---

**Siguiente movimiento único:** con el corpus congelado, el trabajo autorizado siguiente es preparar la decisión del usuario sobre las puertas restantes (`ADR002-TOL-207`, `ADR002-TOL-209`, `ADR002-TOL-210`) y, cuando se autorice expresamente, ejecutar los pasos 2 y 3 de `ADR002-TOL-208` sobre estos blobs. Nada de eso queda autorizado por esta acta.
