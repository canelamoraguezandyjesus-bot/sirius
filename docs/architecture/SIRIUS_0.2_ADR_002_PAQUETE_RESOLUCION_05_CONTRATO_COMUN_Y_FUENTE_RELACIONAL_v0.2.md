# SIRIUS 0.2 · ADR-002 · Paquete de resolución 05 · v0.2

## Contrato común experimental y fuente relacional admisible de ADR002-C

**Estado:** PREINSCRITO · **Versión:** v0.2
**Sustituye documentalmente a:** `SIRIUS_0.2_ADR_002_PAQUETE_RESOLUCION_05_CONTRATO_COMUN_Y_FUENTE_RELACIONAL_v0.1.md` (blob `7eb3e2fafaef80be75ca1a7c3cd1b2132c96ac74`), que **se conserva íntegro** en la historia y no se reescribe
**Rama de trabajo:** `claude/adr002-tol209-forensic-audit-i0ui8k` · **HEAD de partida:** `4a686c37dcf78c89bda3c08a4817737451248377`
**Documento resuelto por:** `SIRIUS_0.2_ADR_002_RESOLUCION_PREBENCHMARK_CONTRATO_COMUN_Y_FUENTE_RELACIONAL_v0.2_PROPUESTA.md`

---

## 1. Por qué existe esta versión sucesora

La revisión de la v0.1 encontró **premisas defectuosas en el propio paquete**, no solo en la resolución. Un paquete que preinscribe con una premisa falsa no puede juzgar honestamente la resolución que preinscribe, así que se emite versión sucesora en lugar de corregir la v0.1 en el sitio.

**La v0.1 se conserva íntegra.** No se reescribe, no se borra y no se declara errónea en su totalidad: lo que cambia son los tres puntos del §2.

---

## 2. Qué corrige esta versión respecto de la v0.1

| # | Premisa defectuosa de la v0.1 | Corrección |
|---|---|---|
| **C-P1** | El criterio de neutralidad decía «Toda regla se aplica igual **a los cuatro y al control**». **Falso:** `T0-control` no usa el motor común, ni las etapas `E0-E5`, ni las puertas comunes, ni el puerto lógico de los candidatos. `T0` es Sirius 0.1 tal cual | El criterio se reformula: las reglas de la capa común se aplican igual **a los cuatro candidatos**; `T0` comparte **fuente congelada, identificadores, textos e índice léxico comparable**, y nada más (§7 criterio 2) |
| **C-P2** | La alternativa `S2` de sustrato describía «mismos identificadores, mismo FTS5, **mismo motor, mismas puertas y mismo puerto lógico**» sin distinguir a quién aplica | Se acota expresamente a `A/B/C/D`. `T0` queda fuera de esa descripción (§6.2) |
| **C-P3** | La pregunta `P-E3` admitía responderse por análisis textual | Se exige responderla **por ejecución**: sondas reproducibles con `ADR002-A` completo `E0-E5`, con proyección de sujeto **fijada de antemano**. El solapamiento de vocabulario **no** es prueba suficiente (§5 Bloque E, §7 criterio 10) |

Se añaden además dos exigencias nuevas que la v0.1 no contenía: la auditoría de la lista blanca **campo a campo dentro de cada objeto anidado** (§7 criterio 11) y la separación explícita entre deduplicación e agrupación (§5 Bloque B).

---

## 3. Regla de precedencia y de no reescritura

1. Ningún documento aprobado se modifica, reescribe ni anula retroactivamente.
2. Las actas vigentes de `ADR002-A v3` y `ADR002-B v5` **conservan íntegra su validez**.
3. Las fichas congeladas no se tocan y no reciben estados nuevos.
4. El corpus v0.4 y sus siete artefactos congelados **no se modifican**. Toda versión posterior se materializa **junto a** ellos, conforme a la propia acta de congelación §111.
5. La comparación primaria aprobada sigue siendo `T0 + A + B + C + D`. **No se reduce.**
6. Los documentos v0.1 de este paquete y de su resolución **se conservan**.

---

## 4. Fuentes de inspección obligatoria

Idénticas a las de la v0.1 —cuyos blobs siguen siendo válidos— con estas adiciones obligatorias:

| Fuente | Por qué se añade |
|---|---|
| `experiments/adr002/candidates/adr002_a/candidate.py` y `lexical.py` | Ninguna afirmación sobre lo que `A` alcanza puede hacerse sin leer y **ejecutar** sus etapas |
| `artifacts/adr002_cards/ficha_T0-control_v1.json` y su plantilla | Toda redacción sobre `T0` debe contrastarse contra su ficha vigente |
| `experiments/adr002/rederivation/frozen_corpus.py` | Fija `RUTA_CORPUS` y las reglas de traducción preinscritas |

---

## 5. Preguntas cerradas que la resolución debe responder

Se conservan los bloques A, C, D y F de la v0.1. Se **reemplazan** el bloque B y la pregunta `P-E3`.

### Bloque A · Contrato experimental *(sin cambios respecto de v0.1)*

`P-A1` a `P-A5`.

### Bloque B · Deduplicación y agrupación *(REEMPLAZA al bloque B de la v0.1)*

- **P-B0.** ¿Son **deduplicación exacta por identidad** y **agrupación de equivalentes** dos mecanismos distintos? Si lo son, se definen por separado y **ninguna frase puede decir que el mismo identificador es el único caso de agrupación** mientras se permitan grupos de identidades distintas.
- **P-B1.** Deduplicación exacta: ¿qué la dispara, qué fusiona, qué conserva y qué **no** decide?
- **P-B2.** Agrupación de equivalentes: ¿cuándo procede, qué conserva y cómo se justifica el representante?
- **P-B3.** ¿Qué diferencias impiden agrupar? Casos: asunto desconocido, identidades distintas, sustituida frente a sucesora, apoyo frente a refutación, condiciones, tiempos, ámbitos, posturas, vigencia y disponibilidad distintas.
- **P-B4.** ¿Qué estructura de salida conserva representante, miembros, procedencias adicionales, diferencias materiales, relaciones entre miembros, razón del representante y estado histórico por miembro?
- **P-B5.** ¿Cuál es la regla de representante y en qué orden?
- **P-B6.** **Para cada uno de los dos mecanismos por separado:** ¿qué efecto tiene sobre cardinalidad, suficiencia, orden, `G12`, explicaciones, traza y criticidad?

### Bloque C · Puertas *(se modifica `P-C4`)*

- `P-C1` a `P-C3` y `P-C5`: sin cambios.
- **P-C4 (reformulada).** ¿Qué debe comprobar realmente `G5`? La respuesta **no puede convertir la ausencia de sujeto en causa automática de descarte**: `B04` no contiene esa obligación. Debe distinguir identidad inválida o ambigua, entidad solicitada no resuelta, y sujeto ausente.

### Bloque D · Proyección experimental y frontera *(se amplía)*

- `P-D1` a `P-D3`: sin cambios.
- **P-D4 (nueva).** Para cada objeto anidado de la lista blanca, ¿son entrada **todos** sus campos, o solo algunos? No se autoriza un objeto completo cuando solo parte de sus campos es entrada legítima.
- **P-D5 (nueva).** ¿Transporta la proyección `mensajes[].project_id`? Si sí, ¿con qué naturaleza declarada y con qué usos permitidos y prohibidos?

### Bloque E · Fuente relacional de ADR002-C *(se reemplaza `P-E3`)*

- `P-E1`, `P-E2`, `P-E4`, `P-E5`: sin cambios.
- **P-E3 (reformulada).** ¿Permiten las aristas congeladas un caso discriminante honesto para `C`? **Debe responderse por ejecución.** Método obligatorio en §6.

### Bloque F · Plan *(sin cambios)*

`P-F1`, `P-F2`.

---

## 6. Método obligatorio para responder `P-E3`

**El solapamiento de vocabulario entre extremos NO demuestra que `A` alcance ambos.** Es indicio, no prueba. La v0.1 concluyó a partir de ese indicio, y eso es un defecto de método.

Método exigido:

1. **Fijar de antemano** —y declararlo en la resolución antes de mostrar resultados— la **proyección de sujeto** que utilizaría el banco.
2. Construir la sonda **fuera del repositorio**, sin ejecutar el benchmark oficial y sin medir rendimiento.
3. Usar **exclusivamente** `tipo`, `origen`, `destino` y los campos de entrada permitidos. **Prohibido** leer `relaciones[].nota`, casos, referencias, resultados esperados, trazas y adjudicaciones.
4. Usar el comportamiento **real** de `ADR002-A` completo `E0-E5`.
5. Construir la consulta **exclusivamente con términos propios del origen que no aparezcan en el destino**.
6. Comprobar por ejecución, para cada arista y para cada ámbito relevante:
   1. `A` alcanza la semilla;
   2. `A` **no** alcanza el destino;
   3. una expansión relacional de **un salto** sí podría alcanzarlo;
   4. `G4` y el resto de puertas **permitirían** el destino.
7. Cubrir **como mínimo** `REL-002` (`CONFLICTO_CON`, MEM-006 → DEC-005) y `REL-004` (`REFUTA`, MEM-015 → MEM-014).

**Resultados válidos, y solo estos dos:**

- **A · SUFICIENTE** — al menos una arista congelada produce un discriminante honesto. Se declara el corpus v0.4 suficiente para implementar `C`, se identifican relación, consulta y resultado técnico, **no se propone corpus v0.5**, y sus notas y toda información de oráculo siguen prohibidas.
- **B · ADMISIBLE PERO INSUFICIENTE** — ninguna lo produce. Se fundamenta **con las ejecuciones**, no con solapamiento textual, y se propone una **familia sucesora** coherente.

---

## 7. Criterios de adjudicación

Una propuesta solo es admisible si cumple **todos**:

1. **Anclaje literal.** Toda regla se deriva de una línea citable de fuente aprobada.
2. **Neutralidad, correctamente formulada.** Las reglas de la capa común se aplican igual **a los cuatro candidatos** `A/B/C/D`. **`T0-control` no usa la capa común**: comparte con ellos la fuente congelada, los identificadores, los textos y un índice léxico comparable, y **nada más**. Ninguna redacción puede presentar como capacidad de `T0` algo que solo tiene la infraestructura experimental.
3. **Frontera entrada/oráculo.** Ningún campo consumible codifica el resultado esperado.
4. **No invención.** No se fijan vocabularios productivos que las fuentes aprobadas no determinen.
5. **Sirius 0.1 intacto.** Cero cambios en `src/`, `migrations/` y `tests/`.
6. **Una sola ola.** No obliga a corregir `common/` dos veces.
7. **Reversibilidad.** Todo derivado experimental es descartable y reconstruible desde blobs congelados.
8. **Custodia.** Toda identidad citada es verificable por blob o SHA.
9. **Benchmark bloqueado.** Nada autoriza medir, ni por omisión ni por implicación.
10. **Prueba por ejecución.** Ninguna conclusión sobre lo que un candidato alcanza o deja de alcanzar se sostiene sobre análisis textual: se demuestra ejecutando.
11. **Auditoría campo a campo.** La lista blanca se audita **dentro de cada objeto anidado**. No se autoriza un objeto completo cuando solo parte de sus campos es entrada legítima.

---

## 8. Prohibiciones

- ❌ Modificar Sirius 0.1 (`src/`, `migrations/`, `tests/`).
- ❌ Modificar el corpus v0.4 o cualquiera de sus siete artefactos congelados.
- ❌ Modificar fichas o actas de `T0-control`, `ADR002-A` o `ADR002-B`.
- ❌ Inventar estados nuevos de ficha.
- ❌ Ejecutar el benchmark oficial, medir rendimiento o publicar métricas.
- ❌ Reducir la comparación primaria `T0 + A + B + C + D`.
- ❌ Usar casos, referencias, adjudicaciones, resultados esperados, elegibles, prohibidos, etapas o paradas esperadas como entrada.
- ❌ Convertir la proyección experimental en DDL productivo.
- ❌ Escribir código, pruebas funcionales o migraciones **en el repositorio** por este paquete.
- ❌ Reescribir o forzar el commit `4a686c3`.
- ❌ Mover `evidence/adr001-spikes`.
- ❌ Abrir otro PR.
- ❌ Marcar la resolución como APROBADA.

---

## 9. Cambio autorizado

Exclusivamente los **documentos sucesores de propuesta**, en la rama `claude/adr002-tol209-forensic-audit-i0ui8k`, sin tocar los v0.1. Ninguna ficha. Ningún código. Ninguna prueba. Ningún corpus. Ningún resultado.

---

## 10. Auditoría adversarial obligatoria antes de publicar

Los diez puntos de la v0.1, más estos cuatro:

11. que la conclusión sobre `C` se sostenga **por ejecución** y no por solapamiento textual;
12. que la redacción sobre `T0` sea contrastable contra su ficha vigente;
13. que ningún objeto anidado de la lista blanca cuele campos de oráculo;
14. que deduplicación y agrupación queden definidas como mecanismos **distintos**, sin frases contradictorias entre sí.

---

## 11. Validación exigida

Blobs de todas las fuentes citadas; corpus congelado intacto; fichas y actas intactas; `src/`, `tests/`, `migrations/`, `experiments/` y `artifacts/` intactos; `ruff format --check`; `ruff check`; `mypy`; suite completa; push a la rama temporal; **no se afirma Quality verde sin una corrida real**; `evidence/adr001-spikes` sin mover; PR #117 abierto, sin fusionar y con cabeza todavía en `a074eb5`.

---

## 12. Estado

**PREINSCRITO.** No autoriza implementar nada. La resolución que lo acompaña **requiere aprobación explícita del usuario**.
