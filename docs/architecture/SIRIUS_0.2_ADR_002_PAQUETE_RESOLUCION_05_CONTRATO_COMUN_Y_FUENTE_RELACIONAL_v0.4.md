# SIRIUS 0.2 · ADR-002 · Paquete de resolución 05 · v0.4

## Contrato común experimental y fuente relacional admisible de ADR002-C

**Estado:** PREINSCRITO · **Versión:** v0.4
**Sustituye documentalmente a:** `..._v0.1.md` (blob `7eb3e2fafaef80be75ca1a7c3cd1b2132c96ac74`), `..._v0.2.md` (`58161cdf0815947cf5085fc263f8ce59ee514024`) y `..._v0.3.md` (`0361f654ea910fdfb03206d65c6bc655ce1e7c68`). **Las tres se conservan íntegras** y no se reescriben.
**Rama de trabajo:** `claude/adr002-tol209-forensic-audit-i0ui8k` · **HEAD de partida:** `71e759b19ceb00d5e7c22f609ded974e86d08bc5`
**Documento resuelto por:** `..._RESOLUCION_PREBENCHMARK_..._v0.4_PROPUESTA.md`

---

## 1. Por qué existe esta versión

La revisión adversarial de la v0.3 —ejecutada sobre los documentos **ya publicados**, no sobre borradores— encontró que la v0.3 **se contradecía a sí misma en dos puntos**: certificaba en su tabla de auditoría una regla que retiraba en su cuerpo, y reintroducía en la tabla de la familia sucesora la custodia por ítem que acababa de eliminar. Un documento que se contradice no es aprobable.

Encontró además cuatro defectos materiales de contenido y nueve menores de coherencia, atribución y cita.

La v0.4 **sanea los quince** y no introduce ninguna decisión de diseño nueva, salvo la adjudicación del remedio documental que la Fase 2 de esta misión exigía resolver **por auditoría dirigida y no por criterio**.

**Las v0.1, v0.2 y v0.3 se conservan.** No se reescriben, no se borran y no se declaran erróneas en su totalidad.

---

## 2. Materia que esta versión NO reabre

**`ADR002-C` · fuente relacional: ADMISIBLE PERO FUNCIONALMENTE INSUFICIENTE sobre el corpus v0.4.**

Se conserva **provisionalmente**. No se repiten las sondas generales de suficiencia relacional. **La única vía por la que esta conclusión puede condicionarse** es el cambio futuro de `subject_key_experimental`, ya registrado en la v0.3 y conservado en la v0.4.

---

## 3. Qué corrige esta versión respecto de la v0.3

| # | Defecto | Naturaleza |
|---|---|---|
| **B1** | La tabla de auditoría certificaba «el grupo es atómico», regla que el cuerpo retiraba | **contradicción interna** |
| **B2** | La tabla de la familia reintroducía la custodia «por ítem agrupable» que el cuerpo eliminaba | **contradicción interna** |
| **M1** | La lista negra remitía en bloque a una clasificación obsoleta de la v0.2, reimportando una prohibición ya levantada | material |
| **M2** | Publicaba un rango de identificadores inexistente | material |
| **M3** | Atribuía a la v0.2 un control fallo-abierto que la v0.2 no contiene | material |
| **M4** | Confinaba la discrepancia del sustrato léxico a `T0`, cuando alcanza a fichas **aprobadas** de `A` y `B` | material |
| **H1–H9** | Categorías por campo que no expresan consumidor ni uso; handoff a B05 sin categoría; origen del mapeo mal descrito; numeración huérfana; instancias frente a valores distintos; control redundante; semántica del verificador sin declarar; elisiones no marcadas; y un arnés de conformidad **presupuesto** | menores de coherencia |

**Criterio transversal que la v0.3 incumplía y esta versión impone:** distinguir siempre **comportamiento actual verificado** de **requisito aprobado para la futura corrección**. Ninguna afirmación en presente sin anclaje en el árbol vigente.

---

## 4. Regla de precedencia y de no reescritura

1. Ningún documento aprobado se modifica, reescribe ni anula retroactivamente.
2. `ADR002-A v3` y `ADR002-B v5` **conservan íntegra su validez como aprobación**. Ver §7, que fija la única condición que esa validez no cubre.
3. Las fichas congeladas no se tocan y no reciben estados nuevos. `T0-control v1` intacto.
4. El corpus v0.4 y sus siete artefactos congelados **no se modifican**.
5. La comparación primaria sigue siendo `T0 + A + B + C + D`. **No se reduce.**
6. Los documentos **v0.1, v0.2 y v0.3** de este paquete y de su resolución **se conservan**.
7. Los commits `4a686c3`, `d44ade8` y `71e759b` **se conservan**. **Prohibido** rebase, squash, amend y force-push.

---

## 5. Fuentes de inspección obligatoria

Las de la v0.3, y **de forma directa, no por descripción secundaria**:

| Fuente | Por qué |
|---|---|
| `migrations/versions/61be4bb269bf_create_fts5_search_indexes.py` | Es la única autoridad sobre el DDL real del índice léxico |
| `artifacts/adr002_cards/ficha_T0-control_v1.json` | Declara el sustrato léxico del control |
| `artifacts/adr002_cards/ficha_ADR002-A_v3.json` y `ficha_ADR002-B_v5.json` | Declaran el mismo sustrato y **están aprobadas** |
| `experiments/adr002/rederivation/frozen_corpus.py` | Es el único punto del código que asume explícitamente un valor de `remove_diacritics` |
| Documentos v0.1, v0.2 y v0.3 | Ninguna atribución a una versión anterior se admite sin abrirla |

**Regla de método:** ningún hallazgo de un informe se da por verdadero sin reproducirlo.

---

## 6. Preguntas cerradas que la resolución debe responder

Se conservan los bloques A a J de la v0.3, con `P-E3` **cerrada** y no reabierta. Se reemplazan `P-I3` y se añade el bloque K.

### Bloques A, B, C, D, E, F, G, H *(sin cambios respecto de la v0.3)*

### Bloque I · Alcance de la familia sucesora *(se reemplaza `P-I3`)*

- `P-I1`, `P-I2`: sin cambios.
- **`P-I3` (reformulada).** ¿**Existe** un arnés de conformidad para `T0`? Si no existe, ¿qué coste tiene construirlo y qué consecuencias tiene sobre su ficha congelada y sobre la evidencia ya emitida? La respuesta **no puede presuponer** que `T0` pueda participar «mediante su arnés real». Debe distinguir: **control productivo real**; **arnés de rendimiento existente**; **adaptador o arnés de conformidad aún inexistente**; **cambio que requeriría implementación**; y **efecto posible sobre ficha y evidencia**.

### Bloque J · Discrepancia del sustrato léxico *(se amplía)*

- **`P-J1` (reformulada).** ¿Cuál es el **inventario completo** de artefactos que declaran el sustrato léxico, y cuáles de ellos contienen una declaración falsa?
- **`P-J2` (nueva).** ¿Es la discrepancia **exclusivamente documental** o **material para resultados, comparabilidad, huellas, pruebas o evidencia ya emitida**? Debe responderse por **auditoría dirigida ejecutable**, no por criterio.
- **`P-J3` (nueva).** Según la respuesta a `P-J2`, ¿cuál es el remedio, y qué obligaciones genera sobre `T0-control v1`, `ADR002-A v3` y `ADR002-B v5`?

### Bloque K · Coherencia interna *(nuevo)*

- **`P-K1`.** ¿Reaparece alguna regla retirada en tablas, resúmenes, auditoría o plan?
- **`P-K2`.** ¿Contradice alguna clasificación de campo a sus consumidores declarados?
- **`P-K3`.** ¿Se acusa a alguna versión anterior de un defecto que no contiene?
- **`P-K4`.** ¿Hay algún hecho futuro escrito en presente, o alguna afirmación de comportamiento actual sin anclaje en el árbol vigente?
- **`P-K5`.** ¿Coinciden paquete y resolución en todo lo que ambos afirman?

---

## 7. Método obligatorio de la auditoría del sustrato léxico

`P-J2` **no se responde por lectura**. Método exigido, sin modificar el repositorio y sin ejecutar el benchmark ni medir rendimiento:

1. Construir una base mínima con el **DDL real** de la migración.
2. Leer `sqlite_master` y registrar el **SQL efectivo**.
3. Ejecutar una sonda que **discrimine** `remove_diacritics 1` de `2` con caracteres para los que el comportamiento documentado difiere.
4. **Escanear** corpus congelados, fixtures y consultas empleadas en las evidencias de `T0`, `A` y `B`, buscando codepoints cuyo comportamiento pueda diferir.
5. Inspeccionar si `lexical.py`, `vectores.py`, generadores o validadores **asumen explícitamente** un valor de `remove_diacritics`.
6. Adjudicar: **A · exclusivamente documental** o **B · material**.

**REGLA DE PARADA.** Si se encuentra efecto material sobre resultados o evidencia ya emitida: **no se emite la v0.4**, **no se hace commit**, se entrega un informe de bloqueo con el caso reproducible exacto, **no se declaran intactas** las aprobaciones de `A` y `B`, y **no se propone una corrección cosmética**.

---

## 8. Criterios de adjudicación

Los quince de la v0.3, más estos cinco:

16. **Coherencia mecánica.** Toda reescritura se propaga a tablas, resúmenes, auditoría y plan. Una regla retirada que reaparece invalida el documento.
17. **Tiempo verbal fiel.** «Actualmente» exige anclaje en el árbol; «deberá» se identifica como requisito futuro. No se escribe un hecho futuro en presente.
18. **Atribución justa.** No se imputa a una versión anterior un defecto que no contiene. Los defectos del propio borrador se declaran como propios.
19. **Listas efectivas y autocontenidas.** Una prohibición no se cierra remitiendo en bloque a una clasificación que la propia versión ha modificado.
20. **Cita literal o marcada.** Toda elisión lleva `[…]`, o el texto deja de presentarse como cita.

---

## 9. Prohibiciones

Las de la v0.3, y además:

- ❌ Reabrir la suficiencia de `C` o repetir sus sondas generales.
- ❌ Emitir la fe de erratas, cualquier ficha sucesora o cualquier artefacto de la familia sucesora.
- ❌ Modificar los documentos v0.1, v0.2 o v0.3.
- ❌ Rebase, squash, amend o force-push sobre `4a686c3`, `d44ade8` y `71e759b`.
- ❌ Mover `evidence/adr001-spikes`, abrir otro PR o autorizar el fast-forward.
- ❌ Afirmar que una aprobación vigente permite ejecutar el benchmark mientras la discrepancia de identidad siga abierta.
- ❌ Marcar la resolución como APROBADA.

---

## 10. Cambio autorizado

Exclusivamente **dos documentos nuevos** —este paquete y su resolución— y **un único commit documental**, en la rama `claude/adr002-tol209-forensic-audit-i0ui8k`. No se tocan código, pruebas, corpus, fichas, actas, `experiments/`, `artifacts/`, `src/`, `tests/`, `migrations/` ni los documentos anteriores.

---

## 11. Auditoría adversarial obligatoria antes de publicar

Los veinticinco puntos de la v0.3, más estos cinco:

26. que **ninguna regla retirada** reaparezca en ningún punto del documento;
27. que la adjudicación del sustrato léxico se sostenga **en la sonda ejecutada** y no en el criterio;
28. que el inventario de artefactos afectados sea **completo**, incluidas las fichas sustituidas;
29. que ninguna categoría de campo contradiga a sus consumidores declarados;
30. que paquete y resolución **no discrepen** en nada que ambos afirmen.

---

## 12. Validación exigida

Blobs de todas las fuentes citadas; descendencia lineal desde `a074eb5`; v0.1, v0.2 y v0.3 intactas; exactamente dos documentos v0.4 nuevos; diff **vacío** sobre código, pruebas, corpus, fichas, actas y migraciones; `ruff format --check`; `ruff check`; `mypy`; suite completa; push **únicamente** a la rama temporal; **no se afirma Quality verde sin una corrida real**; `evidence/adr001-spikes` sin mover; PR #117 abierto, sin fusionar y con cabeza en `a074eb5`.

---

## 13. Estado

**PREINSCRITO.** No autoriza implementar nada. La resolución que lo acompaña **requiere aprobación explícita del usuario**.
