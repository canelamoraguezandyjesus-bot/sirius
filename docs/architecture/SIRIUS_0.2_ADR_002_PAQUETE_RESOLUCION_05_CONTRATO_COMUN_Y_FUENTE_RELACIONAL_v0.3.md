# SIRIUS 0.2 · ADR-002 · Paquete de resolución 05 · v0.3

## Contrato común experimental y fuente relacional admisible de ADR002-C

**Estado:** PREINSCRITO · **Versión:** v0.3
**Sustituye documentalmente a:** `..._PAQUETE_RESOLUCION_05_..._v0.1.md` (blob `7eb3e2fafaef80be75ca1a7c3cd1b2132c96ac74`) y `..._v0.2.md` (blob `58161cdf0815947cf5085fc263f8ce59ee514024`). **Ambos se conservan íntegros** y no se reescriben
**Rama de trabajo:** `claude/adr002-tol209-forensic-audit-i0ui8k` · **HEAD de partida:** `d44ade894c1cc453d3ded0fa703362e8b608571d`
**Documento resuelto por:** `..._RESOLUCION_PREBENCHMARK_..._v0.3_PROPUESTA.md`

---

## 1. Por qué existe esta versión

La revisión de la v0.2 encontró que el paquete preinscribía correctamente la frontera de oráculo pero **dejaba fuera el contrato aprobado de criticidad de extremo a extremo**, no exigía custodia para los datos experimentales que la propia resolución introducía, y confundía la proyección de sujeto de una sonda con la proyección definitiva del banco.

Un paquete que no pregunta por esas cosas no puede detectar que la resolución las omita. Se emite versión sucesora.

**Las v0.1 y v0.2 se conservan.** No se reescriben, no se borran y no se declaran erróneas en su totalidad.

---

## 2. Materia cerrada, que esta versión NO reabre

**`ADR002-C` · fuente relacional: ADMISIBLE PERO FUNCIONALMENTE INSUFICIENTE en el corpus v0.4.**

La conclusión quedó demostrada **mediante ejecución de `ADR002-A` completo `E0-E5`**, con proyección de sujeto declarada de antemano, sobre las cinco aristas ítem↔ítem. **Permanece vigente y no se reinvestiga.** Ninguna pregunta de este paquete la reabre.

---

## 3. Qué corrige esta versión respecto de la v0.2

| # | Defecto de la v0.2 | Corrección preinscrita |
|---|---|---|
| **C-1** | Recuento de criticidad inexacto (decía 17 `CRITICO`) | Se exige el recuento exacto **y una comprobación reproducible que falle cerrada** (§5 Bloque G) |
| **C-2** | Separó el oráculo bruto pero dejó **incompleto el contrato aprobado de `B04`**: `RF-23` obliga a propagar **nivel, razón, fuente y regla aprobada** hasta B05, no solo el nivel | Se exigen **tres planos** distintos y el handoff completo (§5 Bloque G) |
| **C-3** | Adoptó `property_key` sin definir su **origen ni su custodia** | Se exige fuente de asignación, versión de vocabulario, regla de validación y validadores (§5 Bloque H) |
| **C-4** | Podía leerse que `P-SUJETO-01` era la proyección definitiva del banco | Se exige separar **sujeto de sonda** y **sujeto definitivo**, sin contradecir la definición canónica de `A` (§5 Bloque H) |
| **C-5** | Regla de cardinalidad de grupos incompleta | Se exigen **dos cardinalidades**, semántica y documental (§5 Bloque B) |
| **C-6** | La familia sucesora solo cerraba el discriminante de `C` | Debe cerrar **todos** los datos experimentales nuevos (§5 Bloque I) |
| **C-7** | La discrepancia `items_fts`/`knowledge_fts` quedaba mezclada con la aprobación | Se exige tratarla como **fe de erratas separada**, no emitida todavía (§5 Bloque J) |

---

## 4. Regla de precedencia y de no reescritura

1. Ningún documento aprobado se modifica, reescribe ni anula retroactivamente.
2. `ADR002-A v3` y `ADR002-B v5` **conservan íntegra su validez**.
3. Las fichas congeladas no se tocan y no reciben estados nuevos. `T0-control` intacto.
4. El corpus v0.4 y sus siete artefactos congelados **no se modifican**.
5. La comparación primaria sigue siendo `T0 + A + B + C + D`. **No se reduce.**
6. Los documentos **v0.1 y v0.2** de este paquete y de su resolución **se conservan**.
7. Los commits `4a686c3` y `d44ade8` **se conservan**. **Prohibido** rebase, squash, amend y force-push.

---

## 5. Preguntas cerradas que la resolución debe responder

Se conservan los bloques A, C, D, E y F de la v0.2 —con `P-E3` ya respondida y **cerrada**— y se reemplaza el bloque B. Se añaden los bloques G, H, I y J.

### Bloque A · Contrato experimental *(sin cambios)*
### Bloque C · Puertas *(sin cambios)*
### Bloque D · Proyección y frontera *(sin cambios)*
### Bloque E · Fuente relacional *(CERRADO: veredicto B; no se reabre)*
### Bloque F · Plan *(se actualiza el orden, §5.F)*

### Bloque B · Deduplicación, agrupación y **las dos cardinalidades** *(REEMPLAZA)*

- **P-B0** a **P-B5**: como en la v0.2.
- **P-B6 (reformulada).** ¿Cuál es el efecto de **cada mecanismo por separado** sobre cardinalidad, suficiencia, orden, `G12`, explicaciones, traza y criticidad?
- **P-B7 (nueva).** ¿Se distinguen **`cardinalidad_semantica`** y **`cardinalidad_documental`**? La respuesta debe derivarse y citarse desde `B04-Q10`, `Q13`, `RF-20`, `RF-24`, `RF-25` y el contrato de grupos de salida, y debe cubrir: qué cuenta un grupo para suficiencia y parada; qué cuenta para recall, auditoría, procedencia, trazabilidad, criticidad, explicación y handoff; atomicidad del grupo frente al límite; y por qué equivalentes repetidos **no** pueden satisfacer artificialmente una cardinalidad que pide necesidades semánticas distintas.

### Bloque G · Criticidad de extremo a extremo *(nuevo)*

- **P-G1.** ¿Cuál es el **recuento exacto** de criticidad sobre los ítems del blob congelado, recomputado de forma independiente? ¿Existe una **comprobación reproducible** que verifique el blob y falle cerrada si la suma total, el número de no nulos, la distribución por nivel o el inventario de niveles se desvían de lo recomputado? ¿Se acompaña de **controles negativos** que demuestren que no es vacua? ¿Se declara expresamente que sus constantes son **específicas de la v0.4** y que la familia sucesora necesita las suyas?
- **P-G2.** ¿Qué campos del objeto `criticidad` portan realmente identificadores de caso, **verificado campo a campo** sobre el blob? Una prohibición más amplia de lo que la evidencia sostiene rompería un requisito canónico sin necesidad.
- **P-G3.** ¿Quedan definidos **tres planos distintos**: metadato bruto del arnés (prohibido), criticidad aplicada segura (contrato común) y handoff a B05?
- **P-G4.** ¿Satisface el diseño, **por separado**, `B04-RF-23` —nivel, razón, fuente y regla aprobada—, `B04-M19` —fuente/regla aprobada y razón intactas B04→B05—, `B04-D05` y el requisito de `B04-Q21` de que la marca venga **«con ID y evidencia»**, todo ello **sin exponer el oráculo bruto**?
- **P-G5.** `B04` enumera la procedencia de la criticidad en más de un lugar y las enumeraciones **no coinciden**. ¿Cuál se adopta, con qué justificación, y se **declara la divergencia** en vez de ocultarla?
- **P-G6.** ¿Quedan enumerados los usos permitidos y los prohibidos de la criticidad aplicada, **incluido el desempate y la razón de orden**, que `B04` exige con la criticidad como primera clave?
- **P-G7.** ¿Es implementable el nivel propuesto sobre el vocabulario de criticidad **hoy vigente en `common/`**, o el plan debe incluir su ampliación?

### Bloque H · Custodia de los datos experimentales nuevos *(nuevo)*

- **P-H1.** ¿De dónde sale `property_key`, con qué fuente de asignación, versión de vocabulario y regla de validación? ¿Qué validadores lo demuestran?
- **P-H2.** ¿Queda declarado que `P-SUJETO-01` fue **únicamente** la proyección conservadora de las sondas de `C`, y **no** automáticamente la definitiva del banco?
- **P-H3.** ¿Queda definido `subject_key_experimental` con fuente congelada, asignación independiente del oráculo, tratamiento de `null` y prohibición de uso como señal no declarada?
- **P-H4.** ¿Queda separado el uso **común para agrupación** del uso **permitido como señal estructurada de `ADR002-A`**, sin contradecir la definición canónica de `A`?

### Bloque I · Alcance de la familia sucesora *(nuevo)*

- **P-I1.** ¿Cierra la familia sucesora **todos** los datos experimentales nuevos —`property_key`, `subject_key_experimental`, criticidad aplicada segura o su regla cerrada, vocabularios P2, arista discriminante y sus extremos, caso, referencia independiente, validadores, manifiesto, auditoría y acta— y no solo el discriminante de `C`?
- **P-I2.** ¿Queda intacto el corpus v0.4, intacto `performance_corpus_v0_2.json` e intacta la rederivación T0 de `TOL-208` mientras ese corpus de rendimiento no cambie?
- **P-I3.** ¿Participa `T0` en los casos funcionales de la familia sucesora **mediante su arnés real**, sin adquirir el motor común ni las dimensiones de los candidatos, y **sin** que se emita ficha `T0 v2` solo por cambiar la familia de conformidad?

### Bloque J · Discrepancia documental de T0 *(nuevo)*

- **P-J1.** ¿Se mantiene la discrepancia `items_fts`/`knowledge_fts` como **hallazgo separado**, sin modificar la ficha de `T0`, resoluble por **fe de erratas específica no emitida todavía**, sin mezclarse con esta aprobación, sin invalidar retroactivamente la medición real, y **cerrable antes** de autorizar la comparación primaria?

### 5.F · Plan de una sola ola *(orden actualizado)*

La resolución debe recoger este orden exacto: aprobar la resolución v0.3 → materializar y congelar la familia sucesora → **cerrar la fe de erratas documental de T0** → construir la proyección experimental → corregir `common/` una sola vez → fichas sucesoras de `A` y `B` → repetir pruebas completas → reaprobación explícita de `A` y `B` → implementar, congelar, probar y aprobar `C` → ídem `D` → solicitar **aparte** la autorización del benchmark.

---

## 6. Criterios de adjudicación

Los once de la v0.2, más estos cuatro:

12. **Cifras verificables por ejecución.** Ningún recuento se publica sin una comprobación reproducible que **falle cerrada** ante desviación, y sin controles negativos que demuestren que no es vacua.
13. **Contrato canónico completo.** Una separación de oráculo que rompa un requisito aprobado de `B04` no es admisible: hay que satisfacer **ambos**.
14. **Custodia de lo nuevo.** Todo dato experimental que la resolución introduzca debe traer fuente, versión, regla de validación y validador. No se introduce un dato sin custodia.
15. **No contradicción con las fichas vigentes.** Ninguna regla puede contradecir la definición canónica de un candidato ya congelado y aprobado.

---

## 7. Prohibiciones

Las de la v0.2, y además:

- ❌ **Reabrir la suficiencia de `C`** o repetir las sondas relacionales.
- ❌ Rebase, squash, amend o force-push sobre `4a686c3` y `d44ade8`.
- ❌ Modificar la ficha de `T0-control`.
- ❌ Emitir todavía la fe de erratas de `T0`.
- ❌ Mover `evidence/adr001-spikes`.
- ❌ Abrir otro PR.
- ❌ Marcar la resolución como APROBADA.

---

## 8. Cambio autorizado

Exclusivamente **dos documentos nuevos** —este paquete y su resolución— en la rama `claude/adr002-tol209-forensic-audit-i0ui8k`, y **un único commit documental**. No se tocan código, pruebas, corpus, fichas, actas, `experiments/`, `artifacts/`, `src/`, `tests/` ni `migrations/`.

---

## 9. Auditoría adversarial obligatoria antes de publicar

Los catorce puntos de la v0.2, más estos once:

15. que el recuento de criticidad sea exacto y su verificador **no sea vacuo**, con controles negativos ejecutados;
16. que la criticidad aplicada segura **satisfaga `RF-23`, `M19`, `D05` y el «con ID y evidencia» de `Q21`**, y no solo evite el oráculo;
17. que la prohibición de campos brutos **no sea más amplia que la evidencia**: prohibir de más rompe un requisito canónico sin necesidad;
18. que `property_key` no pueda derivarse, ni siquiera indirectamente, del oráculo, y que su control sea **fallo-cerrado** y no fallo-abierto;
19. que la separación entre sujeto de sonda y sujeto definitivo **no contradiga la ficha de `A`**, y que la caracterización de la proyección de sonda sea **verdadera**;
20. que los requisitos sobre la ausencia de sujeto se contrasten **contra lo que el árbol hace hoy**, no solo se enuncien;
21. que las dos cardinalidades no permitan ocultar un crítico, y que toda regla de límite se contraste contra **`CA-44`**, que ordena truncar y declarar parcial;
22. que exista **regla de precedencia** entre `S1` y `PARCIAL`, sin la cual el contrato no es ejecutable;
23. que toda cita entrecomillada sea **literal**, con las elisiones marcadas y las secciones existentes;
24. que la familia sucesora cierre **todo** lo nuevo —incluida la proyección `T0`— y no solo el discriminante de `C`;
25. que ninguna afirmación sobre la participación de `T0` presuponga un arnés que **no existe**.

---

## 10. Validación exigida

Blobs de todas las fuentes citadas; descendencia lineal desde `a074eb5`; v0.1 y v0.2 intactas; únicamente dos documentos v0.3 nuevos; corpus, fichas, actas y código intactos; `ruff format --check`; `ruff check`; `mypy`; suite completa; push a la rama temporal; **no se afirma Quality verde sin una corrida real**; `evidence/adr001-spikes` sin mover; PR #117 abierto, sin fusionar y con cabeza en `a074eb5`.

---

## 11. Estado

**PREINSCRITO.** No autoriza implementar nada. La resolución que lo acompaña **requiere aprobación explícita del usuario**.
