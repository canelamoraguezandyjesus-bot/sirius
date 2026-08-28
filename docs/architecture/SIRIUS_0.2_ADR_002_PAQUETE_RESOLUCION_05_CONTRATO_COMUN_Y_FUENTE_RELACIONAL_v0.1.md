# SIRIUS 0.2 · ADR-002 · Paquete de resolución 05

## Contrato común experimental y fuente relacional admisible de ADR002-C

**Estado:** PREINSCRITO · **Versión:** v0.1
**Rama:** `evidence/adr001-spikes` · **HEAD de partida:** `a074eb5effda760833fe7de1bd6e1b16984c982c`
**Documento resuelto por:** `SIRIUS_0.2_ADR_002_RESOLUCION_PREBENCHMARK_CONTRATO_COMUN_Y_FUENTE_RELACIONAL_v0.1_PROPUESTA.md`

---

## 1. Por qué existe este paquete

Una auditoría previa al benchmark encontró que la capa común experimental de ADR-002 no puede representar sin pérdida lo que `B04` exige medir, y que la fuente relacional que `ADR002-C` necesita no está resuelta. Los dos problemas comparten causa y no pueden resolverse por separado sin cambiar `common/` dos veces.

Este paquete **preinscribe** el trabajo antes de escribirlo: fija la misión, las fuentes, las preguntas cerradas que hay que responder, las alternativas admisibles, los criterios de adjudicación y las prohibiciones. Su función es impedir que la resolución se escriba a medida del resultado.

**Este paquete no decide nada.** La decisión vive en el documento de resolución, y esa resolución **no queda aprobada** hasta que el usuario la apruebe de forma explícita.

---

## 2. Regla de precedencia y de no reescritura

1. Ningún documento aprobado se modifica, reescribe ni anula retroactivamente por este paquete.
2. Las actas vigentes de `ADR002-A v3` y `ADR002-B v5` **conservan íntegra su validez**. Ninguna aprobación se transfiere ni se retira.
3. Las fichas congeladas no se tocan, no cambian de estado y no reciben estados nuevos.
4. El corpus v0.4 y sus siete artefactos congelados **no se modifican**. Toda versión posterior se materializa **junto a** ellos, conforme a la propia acta de congelación §111.
5. La comparación primaria aprobada sigue siendo `T0 + A + B + C + D`. Este paquete **no la reduce** y no contiene autorización para reducirla.

---

## 3. Fuentes de inspección obligatoria

Cada fuente se cita por su identidad Git verificable. Los blobs se calcularon sobre el árbol de `a074eb5`.

### 3.1 Normativa aprobada

| Fuente | Identidad |
|---|---|
| `ARQ-00 · Marco rector` v1.0 APROBADO | fuente `.docx` canónica externa al repositorio |
| `B04 · Búsqueda y recuperación` v1.0 APROBADO | fuente `.docx` canónica externa al repositorio |
| `PDP · Plan de pruebas y registro externo` v1.0 APROBADO | fuente `.docx` canónica externa al repositorio |
| `SIRIUS_0.2_ADR_001_MODELO_FISICO_v1.1_APROBADO.md` | `a759e5f7ad30fb592bd19f31225b1b9b9f11f10e` |
| `SIRIUS_0.2_ADR_002_RESOLUCION_PARTICION_CANDIDATOS_v1.0_APROBADA.md` | `269e960ee00834a74c1171c1edda094e85042acf` |
| `SIRIUS_0.2_ADR_002_NOTA_SUPERACION_02_PARTICION_CANDIDATOS_v1.0_APROBADA.md` | `b93ab9fc59ff16af1e1bfa62a987d8b278b08c73` |
| `SIRIUS_0.2_ADR_002_CONGELACION_CORPUS_v0.4_APROBADA.md` | `414a2b3764f40461ead754b98945efcbe6345fae` |

### 3.2 Corpus congelado (los siete artefactos del acta)

| Artefacto | Blob registrado en el acta | Blob observado en `a074eb5` | ¿Intacto? |
|---|---|---|---|
| `conformance_corpus_v0_4.json` | `c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48` | `c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48` | **sí** |
| `cases_v0_4.json` | `072753b96f4162fe88ce9c96660296349225c7be` | `072753b96f4162fe88ce9c96660296349225c7be` | **sí** |
| `references_v0_4.json` | `3fc9a63705144bf543266de129e17a17ab31c568` | `3fc9a63705144bf543266de129e17a17ab31c568` | **sí** |
| `benchmark_manifest_v0_4.json` | `fa9a2f2b5d8d65aed811f039b2b279c5350d2132` | `fa9a2f2b5d8d65aed811f039b2b279c5350d2132` | **sí** |
| `performance_corpus_v0_2.json` | `4e9e2746e49b158a43eda7826b47c78c41b36e90` | *(sustrato de T0; no se toca en este paquete)* | — |

### 3.3 Capa común experimental y candidatos

| Fichero | Blob |
|---|---|
| `experiments/adr002/candidates/common/contracts.py` | `a13946b923b1ee6adf77ab46ed2fda4fb89ef64f` |
| `experiments/adr002/candidates/common/port.py` | `72041ab76d28de53d161e98172ea20c0ef1a0e2a` |
| `experiments/adr002/candidates/common/gates.py` | `b4361fc87f6a08a65700fe4495a692ef64e4bd48` |
| `experiments/adr002/candidates/common/engine.py` | `95cb4a4f62bbbd55f2c417a0a9b94ba21c111038` |
| `experiments/adr002/candidates/common/trace.py` | `6e0a0822ad3536b06fdc8735c7def3a34ee934d6` |
| `artifacts/adr002_cards/ficha_ADR002-A_v3.json` | `b3ce920e6dc0ee62a0358f8bfb9762dcac0d64d7` |
| `artifacts/adr002_cards/ficha_ADR002-B_v5.json` | `b9ddf6de393e21bebdd3d0eab1e182aa069053e3` |
| `SIRIUS_0.2_ADR_002_ADR002_A_V3_..._REAPROBACION_v1.0.md` | `f2babe06a8c883924a464df6fc96d14f52da367d` |
| `SIRIUS_0.2_ADR_002_ADR002_B_V5_..._APROBACION_v1.0.md` | `ba3dfafa13fbe663608355b49450e035f6233366` |
| `SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.4_PROPUESTO.md` | `88094328925c12eb379b281ccada4f92e01b1c65` |

### 3.4 Sirius 0.1 (solo lectura; no se modifica)

`src/sirius/domain/{memory,decision,precedence}.py`, `src/sirius/adapters/persistence/models.py`, `migrations/versions/`.

---

## 4. Los cuatro planos que no se pueden confundir

Toda afirmación de la resolución debe declarar en qué plano vive. Confundirlos es el error que este paquete existe para evitar.

| Plano | Qué es | Qué NO es |
|---|---|---|
| **P1 · Decisión de producto** | Lo que Sirius debe hacer, fijado por B01–B08/ARQ-00 aprobados | No lo decide una implementación experimental |
| **P2 · Arquitectura experimental del benchmark** | Cómo se representa el corpus para poder medir A/B/C/D de forma comparable | **No es diseño productivo.** Es andamiaje descartable |
| **P3 · Futura arquitectura productiva** | Lo que ADR-001 §6 remitió a la arquitectura consolidada | No se anticipa aquí |
| **P4 · Implementación** | El código de `common/`, `adr002_a/`, `adr002_b/`, … | No crea norma |

**Prohibición explícita:** la proyección experimental de P2 **no se convierte en DDL productivo** ni en insumo de P3. `ADR-001` consecuencia obligatoria 10 ya fijó que el código experimental «no se convierte automáticamente en diseño, DDL o código productivo».

---

## 5. Preguntas cerradas que la resolución debe responder

Cada pregunta admite una respuesta y solo una. La resolución debe responderlas todas o declarar expresamente cuál queda abierta y por qué.

### Bloque A · Contrato experimental

- **P-A1.** ¿Qué campos necesita el contrato común para representar sin pérdida lo que `B04` y `ADR-001` exigen?
- **P-A2.** Para cada campo: ¿pertenece al dato canónico, a la lectura semántica o a la petición?
- **P-A3.** Para cada campo: ¿existe en Sirius 0.1? ¿existe en el corpus congelado? ¿cómo se transporta durante el benchmark?
- **P-A4.** ¿Qué campos quedan expresamente **pendientes para producción** y no se resuelven aquí?
- **P-A5.** ¿Hay algún eje de `B04-Q13` que las fuentes aprobadas **nombren pero no definan**? Si lo hay, se identifica la decisión exacta del usuario y **no se propone implementación**.

### Bloque B · Agrupación y salida

- **P-B1.** ¿Cuándo son equivalentes dos elementos, según la letra de `B04`?
- **P-B2.** ¿Qué diferencias impiden agrupar?
- **P-B3.** ¿Qué se hace con asunto desconocido, identidades distintas, sustituida frente a sucesora, apoyo frente a refutación, condiciones distintas, tiempos distintos, ámbitos distintos, posturas distintas, vigencia o disponibilidad distintas, y duplicado real de una misma identidad?
- **P-B4.** ¿Qué estructura de salida conserva representante, miembros, procedencias adicionales, diferencias materiales, relaciones entre miembros, razón del representante y estado histórico de cada miembro?
- **P-B5.** ¿Cuál es la regla de representante, y en qué orden?
- **P-B6.** ¿Qué efecto tiene la agrupación sobre cardinalidad, suficiencia, `G12`, criticidad, orden, explicaciones, privacidad, traza e indistinguibilidad externa?

### Bloque C · Puertas

- **P-C1.** ¿Se elimina `Peticion.admite_no_vigentes`?
- **P-C2.** ¿Necesita algún modo distinto de M1 un campo equivalente?
- **P-C3.** ¿Cómo se distinguen en la traza propuesta, rechazada, archivada, sustituida, invalidada, sin soporte, eliminada y purgada?
- **P-C4.** ¿Qué debe comprobar realmente `G5`, y cómo se impide agrupar elementos sin sujeto resuelto?
- **P-C5.** ¿Qué dimensiones pertenecen a `G6` y cuáles a `G7`?

### Bloque D · Proyección experimental y frontera

- **P-D1.** ¿Debe el benchmark usar una proyección experimental separada del esquema productivo?
- **P-D2.** ¿Qué lista blanca de campos puede consumir un candidato?
- **P-D3.** ¿Qué queda expresamente prohibido consumir?

### Bloque E · Fuente relacional de ADR002-C

- **P-E1.** ¿Cuál es el censo exacto de relaciones del corpus congelado, por clase de extremo?
- **P-E2.** Para cada arista: tipo, clase de origen, clase de destino, dirección, recuperabilidad de ambos extremos, condición de entrada u oráculo, usabilidad en E3, y si A ya alcanza ambos extremos sin recorrerla.
- **P-E3.** ¿Permiten las aristas congeladas un caso discriminante honesto para C? Solo tres respuestas: **A · SUFICIENTE**, **B · ADMISIBLE PERO INSUFICIENTE**, **C · NO ADMISIBLE**.
- **P-E4.** Si la respuesta es B: ¿cuál es el delta mínimo de un corpus sucesor, sin modificar v0.4?
- **P-E5.** ¿Abre por sí sola la elección de una realización concreta para C el `EJE-2`?

### Bloque F · Plan

- **P-F1.** ¿Cuál es la única ola de corrección posterior, y en qué orden?
- **P-F2.** ¿Qué impacto exacto tiene sobre `ADR002-TOL-208` y sobre las fichas?

---

## 6. Alternativas admisibles

La resolución debe evaluar explícitamente, para cada bloque, al menos estas alternativas, y justificar la elegida frente a las descartadas.

### 6.1 Contrato experimental

| # | Alternativa | Nota |
|---|---|---|
| **A1** | Mantener el contrato actual (dos booleanos) y medir con pérdida | Barata; imposibilita los casos que `B04` mide sobre estados |
| **A2** | Ampliar el contrato experimental con las dimensiones que el corpus ya declara | Requiere transporte; no toca Sirius 0.1 |
| **A3** | Modificar el esquema de Sirius 0.1 para llevar las dimensiones | **Prohibida** por el alcance |
| **A4** | Aplazar ADR-002 hasta que la arquitectura consolidada fije los vocabularios | Congela la vertical entera |

### 6.2 Sustrato del benchmark

| # | Alternativa | Nota |
|---|---|---|
| **S1** | Reutilizar tal cual el cargador de T0 | Colapsa dimensiones; es el sustrato del hallazgo |
| **S2** | Proyección experimental separada, con mismos identificadores, mismo FTS5, mismo motor, mismas puertas y mismo puerto lógico | A evaluar como recomendada |
| **S3** | Sidecar anexo al esquema productivo | A evaluar |
| **S4** | Cargar el corpus en el esquema productivo ampliado | **Prohibida** |

### 6.3 Fuente relacional de C

| # | Alternativa | Nota |
|---|---|---|
| **R1** | `decisions.supersedes_decision_id` desde el canon | Existe y es real; hay que probar si discrimina |
| **R2** | Aristas `relaciones[]` del corpus congelado | Hay que probar si discriminan y si son entrada |
| **R3** | Corpus sucesor con arista neutral añadida | Solo si R1 y R2 resultan insuficientes |
| **R4** | Índice relacional derivado | Realización admisible por ficha; su relación con `EJE-2` debe declararse |
| **R5** | Declarar C inviable | Reduciría la ronda; **no autorizado** |

---

## 7. Criterios de adjudicación

Una propuesta solo es admisible si cumple **todos**:

1. **Anclaje literal.** Toda regla se deriva de una línea citable de fuente aprobada, no de inferencia.
2. **Neutralidad.** No favorece a `A`, `B`, `C` ni `D`. Toda regla se aplica igual a los cuatro y al control.
3. **Frontera entrada/oráculo.** Ningún campo consumible codifica el resultado esperado.
4. **No invención.** No fija vocabularios que las fuentes aprobadas no determinen.
5. **Sirius 0.1 intacto.** Cero cambios en `src/`, `migrations/` y `tests/` productivos.
6. **Una sola ola.** No obliga a corregir `common/` dos veces ni a emitir dos generaciones de fichas por la misma causa.
7. **Reversibilidad.** Todo derivado experimental es descartable y reconstruible desde blobs congelados.
8. **Custodia.** Toda identidad citada es verificable por blob o SHA.
9. **Benchmark bloqueado.** Nada del plan autoriza medir, ni por omisión ni por implicación.

---

## 8. Prohibiciones de este paquete

- ❌ Modificar Sirius 0.1 (`src/`, `migrations/`, `tests/`).
- ❌ Modificar el corpus v0.4 o cualquiera de sus siete artefactos congelados.
- ❌ Modificar fichas o actas de `T0-control`, `ADR002-A` o `ADR002-B`.
- ❌ Inventar estados nuevos de ficha.
- ❌ Ejecutar candidatos, benchmark o medición de rendimiento.
- ❌ Reducir la comparación primaria `T0 + A + B + C + D`.
- ❌ Usar `cases_v0_4.json`, `references_v0_4.json`, adjudicaciones, resultados esperados, elegibles, prohibidos, etapas o paradas esperadas como entrada de diseño.
- ❌ Convertir la proyección experimental en DDL productivo.
- ❌ Escribir código, pruebas funcionales o migraciones en este paquete.
- ❌ Marcar la resolución como APROBADA.

---

## 9. Cambio autorizado por este paquete

Exclusivamente **dos ficheros nuevos** en `docs/architecture/` y **un solo commit documental**:

1. este paquete;
2. el documento de resolución propuesta.

Ninguna ficha. Ningún código. Ninguna prueba. Ningún corpus. Ningún resultado.

---

## 10. Auditoría adversarial obligatoria antes de publicar

La resolución no se publica sin intentar refutar, como mínimo:

1. que `B04` determine realmente la agrupación;
2. que la proyección experimental no sea una modificación encubierta de Sirius 0.1;
3. que los campos permitidos sean entrada y no oráculo;
4. que el censo relacional sea correcto;
5. que un índice derivado no abra automáticamente `EJE-2`;
6. que las relaciones existentes basten o no basten para `C`;
7. que la solución no favorezca a `A`, `B`, `C` ni `D`;
8. que no se requieran dos generaciones innecesarias de fichas;
9. que ningún documento anterior quede reescrito;
10. que el plan no autorice silenciosamente el benchmark.

Los defectos encontrados se corrigen **antes** de publicar, y el resultado de la refutación se registra en la propia resolución.

---

## 11. Validación exigida

- Blobs de todas las fuentes citadas, verificados contra el árbol.
- Corpus congelado intacto, contrastado contra el acta de congelación.
- Fichas y actas de `A` y `B` intactas.
- `src/`, `tests/` y `migrations/` sin cambios.
- `ruff format --check`, `ruff check`, `mypy`, suite completa.
- Push a la rama de trabajo, Quality verde, PR #117 abierto y sin fusionar.

---

## 12. Estado

**PREINSCRITO.** Este paquete no autoriza implementar nada. La resolución que lo acompaña **requiere aprobación explícita del usuario** antes de que se escriba una sola línea de código.
