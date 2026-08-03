# SIRIUS 0.2 — ADR-002 · Reaprobación conjunta de `ADR002-A v5` y `ADR002-B v7`

**Versión:** 1.0
**Estado:** **APROBADA**
**Fecha:** 3 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **HEAD aprobado:** `decf73e8dda0a1cdd93bb3010a538bb7903bf71c`
**PR:** #117, **abierto y sin fusionar**

**Autoridad:** pasos **6 y 7** del plan aprobado por `..._RESOLUCION_PREBENCHMARK_..._v1.0_APROBADA.md` §4 — «emitir fichas sucesoras de `ADR002-A` y `ADR002-B`» y «repetir pruebas y obtener reaprobación explícita de A y B».

**Acto de aprobación:** el usuario, directamente en el chat de trabajo, respondió **«Sí, reaprobar A v5 y B v7»** a la solicitud conjunta presentada sobre este HEAD.

---

## 1. Lo aprobado

| Ficha | Estado | Huella canónica | Sustituye a |
|---|---|---|---|
| `ficha_ADR002-A_v5.json` | **CONGELADA · PREPARADO PARA BENCHMARK** | `b5549a5a8e0f2fa4e791f64fbdb1c769938949be` | v4 |
| `ficha_ADR002-B_v7.json` | **CONGELADA · PREPARADO PARA BENCHMARK** | `33a7617dc8713d7dc29fce1877b7c41d689f25d7` | v6 |

Ambas declaran `commit_de_referencia` `4bb58c7a96f21ea601c28ff57caf67e4ee002a89` y el árbol `92df027fdefe048f574d20acb1305657ec97f113` de `experiments/adr002/candidates`, con subárboles `30984c1f054fc47b12f708fad23ddf617a46645c` (`common`), `ceb4247c9fee913ae86d5203f199b19341f1c833` (`adr002_a`) y `43eaa374d6eef827599472588a54494be9704565` (`adr002_b`).

**`T0-control v1` no se ve afectada** y conserva su estado: su identidad está atada al árbol de `src/sirius`, que sigue en `6d8558ef1fe4994cb15a12967525bf3496b3c0b8`.

---

## 2. Por qué hubo cuatro versiones y no dos

La solicitud de reaprobación se presentó primero sobre `A v4` y `B v6`. El usuario **amplió el alcance del paso 5** y ordenó corregir antes las cinco puertas que seguían leyendo el estado colapsado. Hecha esa corrección, el árbol de `common` volvió a cambiar y las v4 y v6 quedaron **SUSTITUIDAS antes de que ninguna aprobación las amparase**.

Ninguna de las cuatro se borra. Las cuatro siguen presentes y conformes, y su contenido congelado permanece íntegro en el historial.

---

## 3. La identidad del sustrato léxico, corregida en origen

Las dos fichas declaran ahora:

> tabla `knowledge_fts` creada por la migración `61be4bb269bf` **sin cláusula `tokenize`**, de modo que rige el tokenizador por defecto `unicode61` con `remove_diacritics 1`.

Es la primera vez que se declara correctamente **en origen**. La fe de erratas 05 lo rectificó para la evidencia ya emitida; estas fichas ya no lo heredan mal. Las versiones anteriores decían `items_fts` y `remove_diacritics 2`, y siguen diciéndolo: son historia y no se reescriben.

---

## 4. Que ninguna señal nueva beneficia ilegítimamente a un candidato

| Comprobación | Resultado |
|---|---|
| Subárbol propio de `A` | **byte a byte** igual que en la v4 |
| Subárbol propio de `B` | **byte a byte** igual que en la v5 |
| Señal tardía de `A` | `ninguna_adicional`, sin cambio |
| Señal tardía de `B` | `semantica_vectorial`, sin cambio |
| Neutralidad de la capa común | `fallos_de_neutralidad` == `[]` sobre los ocho módulos |
| `property_key` | `SOLO_CAPA_COMUN`; ningún candidato la recibe, comprobado sobre `ContextoDeEtapa` y la firma del motor |
| Criticidad aplicada | fuera de `ItemCanonico`; ningún candidato la ve |
| Plano reservado | se abre en `ro`; los cuatro candidatos fallan al pedirlo |
| Ejes P2 | `ENTRADA_DE_CANDIDATO` por §5.7, disponibles **por igual** para los cuatro |

---

## 5. Pruebas ejecutadas sobre el HEAD aprobado

- **1616 pruebas experimentales, todas en verde, cero omitidas.** Las de identidad, corrupción y apertura corren con las fichas como ancestros estrictos, que es la condición de `TOL-210` regla 3.
- **40 invariantes** propios de la corrección de `common`, uno por punto aprobado y uno por puerta corregida.
- **47 pruebas** de la proyección experimental.
- `verify_cards --check`: **13 fichas conformes**, una `CONGELADA` por candidato, **14/14 controles bloqueantes**, ninguna puerta de arranque pendiente.
- Ruff format, Ruff lint y mypy en verde.
- **Quality verde** sobre el HEAD aprobado (run 305, intento 2).

### 5.1 El fallo de Quality del intento 1, adjudicado

El intento 1 falló en `tests/gui/test_conversation_ui.py::test_streaming_message_grows_without_overlapping_neighbours`, con `assert 24 >= 54` sobre la altura de un `QRect`.

**No procede de esta rama, y no se declara inestable sin prueba:**

1. Ese test **no existía** en el `main` contra el que fusionaban los runs 300 y 304; entró con `3077158` (PR #118) cuando `main` avanzó de `24fc9d5` a `cb45b78` durante la sesión.
2. La rama **no toca ni un byte** de `src/` ni de `tests/`: `git diff --name-only ... -- src/ tests/` devuelve vacío entre los commits verde y rojo.
3. `tests/gui` tiene el **mismo árbol** `4dfdb12a…` en el commit verde y en el rojo.
4. El **intento 2 sobre el mismo commit de fusión** pasó entero.
5. Localmente, `tests/gui/test_conversation_ui.py` da **44 passed**.

Es una aserción de disposición Qt sensible al entorno, propiedad de `main`. Corregirla sería alterar Sirius 0.1 productivo sin decisión aprobada que lo exija, y esta acta no lo hace.

---

## 6. Estado de gobierno tras esta acta

- `T0-control v1`: **CONGELADA**, intacta.
- `ADR002-A v5`: **PREPARADO PARA BENCHMARK**.
- `ADR002-B v7`: **PREPARADO PARA BENCHMARK**.
- `ADR002-C`: **no implementado** — paso 8, siguiente.
- `ADR002-D`: **no implementado** — paso 9.
- Ronda primaria: `T0 + A + B + C + D`, **sin reducción**.
- Benchmark: **BLOQUEADO, NO AUTORIZADO y NO EJECUTADO**.
- PR #117: **abierto y sin fusionar**. `main` no se modifica.

---

## 7. Lo que esta reaprobación no hace

- **No** autoriza el benchmark ni ninguna medición.
- **No** aprueba `C` ni `D`.
- **No** traslada las aprobaciones históricas de `A v3` ni de `B v5`, que permanecen en sus propias actas referidas a sus propias versiones.
- **No** fusiona `PR #117` ni toca `main`.
