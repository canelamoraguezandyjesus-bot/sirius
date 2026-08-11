# ADR-008 — Cargar en lote las revisiones vigentes al listar recuerdos y decisiones

- Estado: PROPUESTO
- Fecha: 2026-08-11
- Aprobación: la fusión de la PR por el propietario

## Contexto y problema

ADR-007 (B12c) midió y localizó, sin corregirlo, un riesgo de producto:
construir el contexto consumía entre el 89 % y el 100 % de los 300 ms que le
concede RNF-003, y la causa estaba en `SqliteMemoryRepository`:

```python
def _load_memory(session: Session, model: MemoryModel) -> Memory:
    revision_model = _get_current_revision_model(session, model.id)   # una consulta por recuerdo
    return _to_domain_memory(model, revision_model)
```

`list_current_memories()` recorre los modelos vigentes y llama a
`_load_memory()` por cada uno: 501 consultas para 500 recuerdos.
`SqliteDecisionRepository` tiene la misma forma en `_load_decision()`.

La incidencia #148 (B12e) autoriza corregir exactamente esto, sin ampliar el
alcance: mismos objetos de dominio, mismo orden, misma exclusión de
archivados/eliminados. Es una corrección de coste, no de comportamiento.

## Criterio de parada (escrito ANTES de medir)

Publicado antes de tocar código:

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en
   `_load_memory`/`_load_decision`, llamada una vez por elemento desde los
   métodos `list_current_*`/`list_archived_*`. El arreglo va en esos mismos
   métodos `list_*`, porque son el único punto que decide cuántas veces se
   invoca la carga de una revisión — sí pueden observar el fallo que
   corrigen.
2. **¿Qué NO va a garantizar esto?** No es el mínimo teórico de consultas (un
   `JOIN` bajaría de dos a una); no cambia el esquema ni añade índices; no
   declara PA-025 superada; no toca `ContextBuilder`, el ranking de
   relevancia ni el presupuesto de contexto.
3. **Detenerse y devolver `BLOCKED_BY_DECISION` si:** la corrección exige
   esquema/índice/migración; no se puede eliminar la consulta por elemento
   sin cambiar qué devuelve el método; aparece cualquier diferencia de orden
   o contenido; la mejora medida resulta inapreciable (entonces la causa no
   era esta).
4. **¿Qué hace el fallo imposible en vez de improbable?** Una prueba nueva
   que fija, por conteo real de sentencias SQL, que `list_current_memories()`,
   `list_archived_memories()`, `list_current_decisions()` y
   `list_archived_decisions()` ejecutan el mismo número de consultas para 3
   elementos que para 25. Verificada por mutación: con el N+1 restaurado, las
   cuatro fallan; con el arreglo, pasan.

## Opciones consideradas

- **Carga ansiosa de SQLAlchemy (`selectinload`/`joinedload`) sobre una
  relación ORM `MemoryModel.current_revision`.** Descartada sin tocar el
  esquema: no existe hoy una relación declarada entre `MemoryModel` y "su
  revisión vigente" (la vigencia la decide `is_current`, no una clave
  foránea directa), y declararla exigiría tocar `models.py` más allá de lo
  que el alcance permitido de la incidencia autoriza a título de "cambiar el
  esquema".
- **Una única consulta `IN (...)` sobre `MemoryRevisionModel`/
  `DecisionRevisionModel` filtrada por los ids del lote y `is_current`,
  indexada en un diccionario por id de padre.** Elegida: no toca el esquema,
  no añade índices, no cambia una sola línea de lo que los métodos devuelven,
  y baja de N+1 a 2 consultas por lista, independientemente de N.

## Decisión

`_load_memories(session, models)` y `_load_decisions(session, models)`
sustituyen la construcción por comprensión de lista que llamaba a
`_load_memory`/`_load_decision` elemento a elemento, solo dentro de
`list_current_memories()`, `list_archived_memories()`,
`list_current_decisions()` y `list_archived_decisions()`. El resto de
métodos (`get_memory`, `correct_memory`, `archive_memory`, `delete_memory` y
sus pares de decisión) siguen usando `_load_memory`/`_load_decision`: operan
sobre un único elemento, así que el N+1 no les aplica y tocarlos estaba fuera
del alcance permitido.

## Comprobación que la sostiene

**Prueba de conteo, con mutación (obligatoria por la incidencia):**
`tests/integration/test_memory_decision_list_query_count.py` mide el número
de sentencias SQL (evento `before_cursor_execute` de SQLAlchemy) que cada uno
de los cuatro métodos ejecuta para 3 elementos frente a 25. Mutación
verificada restaurando el N+1 en los cuatro métodos (`git stash` sobre los
dos ficheros de repositorio, dejando la prueba nueva intacta):

```
$ uv run pytest tests/integration/test_memory_decision_list_query_count.py -q
FAILED ...test_list_current_memories_no_crece...    26 == 4 → falla
FAILED ...test_list_archived_memories_no_crece...    26 == 4 → falla
FAILED ...test_list_current_decisions_no_crece...    26 == 4 → falla
FAILED ...test_list_archived_decisions_no_crece...   26 == 4 → falla
4 failed in 1.08s
```

Restaurado el arreglo, las cuatro pasan en 2 consultas por lista, constante
frente a 3 y frente a 25 elementos.

**Regresión de comportamiento — pruebas existentes sin tocar, todas en
verde:** `test_sqlite_memory_repository.py`,
`test_sqlite_decision_repository.py`,
`test_memory_archive_delete_lifecycle.py`, `test_decision_lifecycle.py`,
`test_decision_archive_lifecycle.py`.

**Rendimiento antes y después**, mismo conjunto de referencia del Plan de
Pruebas (5.000 mensajes, 500 recuerdos, 100 decisiones, 10 proyectos; 30
repeticiones), misma máquina, `main` en `97676e1` como "antes":

| Operación | P95 antes | P95 después | Límite |
|---|---|---|---|
| listar recuerdos vigentes | 104,7 ms | 9,3 ms | 300 ms |
| listar decisiones vigentes | 20,3 ms | 2,2 ms | 300 ms |
| resumen de conocimiento | 125,4 ms | 12,6 ms | 300 ms |
| cargar historial completo | 87,9 ms | 94,2 ms | 300 ms |
| **construir contexto** | **239,8 ms** | **120,9 ms** | **300 ms** |

`cargar historial completo` no usa ninguno de los cuatro métodos corregidos
(lista mensajes de conversación) y su variación de 87,9 a 94,2 ms es ruido de
runner, no una regresión — queda registrado para que no se lea como tal.

`uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src
tests`, `uv run pytest` y `git diff --check`: todos en verde (ver la fila de
B12e en el registro de evidencia de `V8_EXECUTION.md` para el conteo exacto
de pruebas).

## Consecuencias

- Construir el contexto deja de estar pegado a su presupuesto de 300 ms en
  este runner: pasa del 80 % al 40 %. El margen que quedaba, entre el 89 % y
  el 100 % medido por B12c, desaparece.
- El comportamiento observable no cambia: mismos objetos de dominio, mismo
  orden, misma exclusión de archivados/eliminados. Las pruebas de ciclo de
  vida existentes, sin tocar, lo confirman.
- La prueba de conteo deja el N+1 imposible de reintroducir en silencio: un
  cambio futuro que vuelva a llamar `_load_memory`/`_load_decision` por
  elemento dentro de un método `list_*` hace que el número de consultas
  vuelva a depender de N, y la prueba lo detecta sin depender de un umbral de
  tiempo (que sería intermitente en CI).
- PA-025 sigue sin declararse superada: este runner es Linux compartido, no
  el Windows del usuario. El criterio de ADR-007 sobre cuándo se afirma el
  límite del plan en CI no cambia.

## Alternativas descartadas y por qué

Ver «Opciones consideradas»: la carga ansiosa vía relación ORM se descartó
por exigir un cambio de esquema no autorizado por el alcance de la
incidencia, no por ser peor en rendimiento — de hecho sería equivalente o
mejor. Queda anotada aquí como la opción a revisar si en el futuro se
autoriza tocar `models.py`.
