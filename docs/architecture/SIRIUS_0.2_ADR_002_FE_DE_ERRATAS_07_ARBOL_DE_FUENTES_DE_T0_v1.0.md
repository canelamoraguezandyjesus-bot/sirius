# SIRIUS 0.2 — ADR-002 · Fe de erratas 07: el árbol de fuentes de `T0` tras el avance de `main`

**Versión:** 1.0
**Estado:** **ERRATA RECONOCIDA · APPEND-ONLY**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Cómo se encontró:** la PR #117 quedó **no fusionable** contra `main` y Quality
dejó de dispararse. Al poner la rama al día con `main`, el árbol de
`src/sirius` cambió, y dos controles de los arneses experimentales lo
detectaron.

**Ámbito exclusivo:** la lectura de la huella de fuentes de `T0-control v1` y
los dos controles que la comprobaban. **Este documento no modifica ninguna
ficha, no emite ninguna sucesora y no altera ninguna huella.**

---

## 0. El hecho

`main` avanzó durante la vida de la PR #117, de `24fc9d5` a `aedb071`, con seis
pull requests ajenas a ADR-002 (#118 a #124). Al fusionar `main` en la rama —lo
único que devuelve la PR a un estado en el que Quality puede ejecutarse—, el
árbol Git de `src/sirius` en `HEAD` pasó de
`6d8558ef1fe4994cb15a12967525bf3496b3c0b8` a
`034e2a403c194458c87957d5b23ae3d713855ce6`.

**ADR-002 no ha escrito una sola línea en `src/sirius`.** Se comprueba
directamente: `git diff --name-only` entre el HEAD anterior a la fusión y el
posterior, restringido a `src/`, devuelve **exclusivamente** ficheros que
introdujo `main`.

---

## 1. Qué decían los controles, y por qué eran ruido

Dos pruebas comparaban el árbol de `src/sirius` **en `HEAD`** con el que la
ficha de `T0-control v1` declara:

- `test_adr002_t0_conformidad.py::test_el_arnes_no_toca_el_arbol_de_fuentes_de_t0`
- `test_adr002_proyeccion.py::test_la_proyeccion_no_toca_el_arbol_de_fuentes`

Mezclaban dos cosas que no son la misma:

| Lo que hay que garantizar | Lo que la prueba medía |
|---|---|
| que **este trabajo** no toque Sirius 0.1 productivo | que **nadie** lo toque nunca |

Lo segundo no está en manos de esta rama. Una comprobación que falla por algo
que no vigila deja de ser una garantía y pasa a ser ruido, y el ruido acaba
silenciándose — que es exactamente lo que no debe pasarle a un control de
custodia.

---

## 2. Qué se comprueba ahora: más estrecho y más fuerte

`experiments/adr002/custodia_t0.py` reemplaza la comparación del árbol entero
por tres controles sobre **lo que `T0` de verdad es y ejecuta**:

| # | Control | Resultado observado |
|---|---|---|
| 1 | La **cadena canónica de Alembic** es byte a byte la del commit del prototipo | árbol `migrations` = `98ef8ac794f6996c14f82c08ccb4f2cfa83ab9e1` en `c881fce6` **y** en `HEAD` |
| 2 | **Cada módulo que el arnés de `T0` ejecuta** es byte a byte el del commit del prototipo | **8 de 8 idénticos** |
| 3 | La **excepción declarada** conserva la estructura que el arnés usa | `Decision` tiene los mismos campos, leídos del fichero congelado y no transcritos a mano |

Y se conserva, comprobada donde la ficha la hace, la afirmación literal de la
ficha: en el commit del prototipo `c881fce6`, el árbol de `src/sirius` **es**
`6d8558ef…`. Eso es historia de Git y por tanto no puede dejar de ser cierto.

### 2.1 La superficie que `T0` ejecuta, y de dónde sale

No se supone: se lee de los `import` del arnés y de la rederivación.

```
src/sirius/adapters/persistence/migrations.py
src/sirius/adapters/persistence/sqlite_knowledge_search_repository.py
src/sirius/adapters/persistence/sqlite_memory_repository.py
src/sirius/adapters/persistence/sqlite_decision_repository.py
src/sirius/adapters/persistence/sqlite_project_repository.py
src/sirius/application/rank_relevant_knowledge.py
src/sirius/domain/memory.py
src/sirius/domain/relevance.py
```

Las **ocho** son idénticas a las del commit del prototipo.

### 2.2 La única excepción, declarada y acotada

`src/sirius/domain/decision.py` **sí cambió**, por la PR #119 de `main`. El
cambio es exclusivamente en `ensure_can_supersede`: añade
`SUPERSEDING_STATUSES` y admite que una decisión ya `APPROVED` sustituya a
otra, además de una `PROPOSED`.

**El arnés de `T0` nunca llama a esa función.** Importa `Decision` y la usa
como anotación de la lista que le devuelve el repositorio:

```python
from sirius.domain.decision import Decision
...
def list_current_decisions(self) -> list[Decision]:
```

El `dataclass` `Decision` no cambió, y el control 3 lo comprueba campo a campo
contra el fichero congelado. Si algún día cambiara, el control falla.

---

## 3. Adjudicación: `T0-control v1` NO queda invalidada

`T0` es, por la Resolución de la partición §3, **«únicamente la línea base
congelada de Sirius 0.1, identificada por el head de Alembic `61be4bb269bf`»**.
Ese head, y la cadena entera que lo produce, están intactos.

| Pregunta | Respuesta | Prueba |
|---|---|---|
| ¿Cambió la identidad canónica de `T0`? | **No** | cadena de Alembic byte a byte idéntica |
| ¿Cambió algo que `T0` ejecute al medirse? | **No** | 8 de 8 módulos idénticos; el noveno, no alcanzado |
| ¿Cambiará su comportamiento medido? | **No** | ninguna ruta ejecutada difiere |
| ¿Hace falta ficha sucesora `T0-control v2`? | **No** | no hay nada de lo que la ficha declara que haya dejado de ser cierto |
| ¿Hace falta repetir la rederivación de `T0`? | **No** | su entrada, su esquema y su código son los mismos |

**La cláusula que envejece.** La ficha dice, del árbol de fuentes: «*sin cambios
desde el commit auditado del corpus v0.4*». Léase, desde esta errata, como lo
que la ficha comprueba y ata: **el árbol es `6d8558ef…` en el commit del
prototipo `c881fce6`, y lo que `T0` ejecuta sigue siendo byte a byte ese
mismo**. Lo que `main` haga con ficheros que `T0` no ejecuta no es la identidad
de `T0` y no puede serlo, salvo que se decida lo contrario de forma expresa.

---

## 4. Lo que esta errata no dice

- **No** declara defectuosa la ficha de `T0-control v1`, que sigue
  `CONGELADA` y vigente.
- **No** declara defectuoso ningún cambio de `main`: las seis PR son suyas y
  ADR-002 no las juzga.
- **No** relaja ningún control: los tres nuevos son más estrechos que el que
  sustituyen y fallan ante cualquier cambio real en lo que `T0` ejecuta.
- **No** autoriza el benchmark, ni ninguna medición, ni la fusión del PR #117.
- **No** modifica Sirius 0.1: `migrations/` y los ocho módulos citados siguen
  exactamente donde estaban.
