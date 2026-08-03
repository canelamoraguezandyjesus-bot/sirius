# SIRIUS 0.2 — ADR-002 · Adjudicación del arnés de conformidad de `T0`

**Versión:** 1.0
**Estado:** **ADJUDICADO**
**Fecha:** 3 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **HEAD de partida:** `50a6acf6c8bbfb2efa3b78cb41a00cf6cf71a15e`
**PR:** #117, **abierto y sin fusionar**

**Autoridad:** paso **3** del plan aprobado por `..._RESOLUCION_PREBENCHMARK_..._v1.0_APROBADA.md` §4, que la resolución v0.4 §8.3 dejó expresamente abierto: «**No se decide aquí.** El paso 4 del plan lo trata como **adjudicación separada, con el coste a la vista**.»

---

## 1. La cuestión adjudicada

`T0` debe poder responder a los **mismos casos funcionales de conformidad** que `ADR002-A`, `B`, `C` y `D`. El arnés que lo permite **no existía**.

La resolución v0.4 §8.3 declaró el **coste previsto** de construirlo:

> «Construirlo **es un cambio de implementación de `T0`**. […] la ficha congelada declara que «cualquier modificación posterior obligará a nueva versión de ficha **y a repetir las ejecuciones ya realizadas**» […]. Por tanto, **construir un arnés de conformidad para `T0` obligaría a ficha sucesora de `T0` y a repetir sus ejecuciones.**»

Esa frase enunciaba un **coste condicional**, no un hecho verificado. La adjudicación consiste en comprobar si la condición se cumple.

---

## 2. Adjudicación

> ### El arnés de conformidad de `T0` **NO** es una modificación de la implementación de `T0`.
> ### **No** obliga a ficha sucesora de `T0`. **No** obliga a repetir la rederivación.

### 2.1 Fundamento, verificado y no argumentado

La ficha congelada `ficha_T0-control_v1.json` ata la identidad de `T0` a un objeto Git concreto:

```
huella_candidato.hash_del_arbol_de_fuentes:
  "arbol Git 6d8558ef1fe4994cb15a12967525bf3496b3c0b8 de src/sirius en el
   commit del prototipo; sin cambios desde el commit auditado del corpus v0.4"
```

Comprobado sobre el árbol:

| Referencia | `git rev-parse …:src/sirius` |
|---|---|
| Declarado por la ficha | `6d8558ef1fe4994cb15a12967525bf3496b3c0b8` |
| Commit del prototipo `c881fce6…` | `6d8558ef1fe4994cb15a12967525bf3496b3c0b8` |
| **HEAD tras construir el arnés** | `6d8558ef1fe4994cb15a12967525bf3496b3c0b8` |

`git diff --name-only c881fce6..HEAD -- src/ migrations/` devuelve **vacío**.

**La huella de fuentes de `T0` no cambia**, porque el arnés vive íntegramente en `experiments/adr002/candidates/t0_control/` y **no toca `src/sirius` ni `migrations/`**.

### 2.2 El precedente que lo confirma

La propia ficha declara como medio de reproducción:

```
huella_candidato.reproduccion:
  "uv run python -m experiments.adr002.rederivation.run_rederivation --check; …"
```

El **arnés de rendimiento de `T0` ya existe**, vive en `experiments/`, y **la ficha lo cita sin considerarlo parte de la implementación de `T0`**: se congeló la ficha y **después** se ejecutó la rederivación con ese arnés, sin ficha sucesora.

El arnés de conformidad es **idéntico en naturaleza**: observa a `T0` desde fuera. Si el de rendimiento no es implementación de `T0`, el de conformidad tampoco. Sostener lo contrario obligaría a declarar retroactivamente inválida la rederivación ya emitida.

### 2.3 Qué habría activado la cláusula, y no ocurre

La declaración de congelación dice: «los valores de esta ficha […] cualquier **modificación posterior** obligará a nueva versión de ficha y a repetir las ejecuciones ya realizadas».

**Ningún valor de la ficha cambia.** No cambian el sustrato léxico declarado, ni la materialización de relaciones, ni el puerto de acceso, ni los incumplimientos conocidos, ni la huella, ni el árbol de fuentes, ni el head de Alembic, ni las exenciones. La ficha `T0-control v1` permanece **CONGELADA e intacta**.

---

## 3. Solución mínima técnicamente válida

`experiments/adr002/candidates/t0_control/conformance.py`

| Decisión | Por qué |
|---|---|
| Recibe la **misma `Peticion`** que los candidatos | es la condición para responder a los mismos casos |
| Traduce a `rank(query_text)` y **descarta el resto** | es la firma real del caso de uso productivo; T0 no acepta más |
| **Declara los diez campos descartados** como resultado | la pérdida *es* lo que el control mide |
| **No** implementa `SenalesDeCandidato` | implementarlo permitiría pasarlo al motor común y convertir el control en un quinto candidato |
| **No** aplica `G1-G12`, etapas ni paradas | `T0` no las tiene; añadirlas mediría el arnés, no la línea base |
| **No** filtra por ámbito de la petición | filtrar ocultaría `RF-06`, que es un incumplimiento declarado |
| **No** trunca por límite duro | truncar inventaría una capacidad inexistente |
| Envuelve los repositorios en **contadores de solo lectura** | permite **medir** el barrido de `RF-14` sobre lo ejecutado en vez de deducirlo del código |
| Devuelve `RespuestaDeControl`, **no** `Recuperacion` | devolver la estructura del motor obligaría a inventar campos que `T0` no produce |

### 3.1 Los incumplimientos salen como resultado, no se corrigen

Verificado por ejecución sobre el fixture técnico:

| Incumplimiento | Cómo se exhibe |
|---|---|
| **`RF-14`** barrido completo | recorre **el canon vigente entero** para devolver un subconjunto; el contador lo mide |
| **`RF-06`** sin aislamiento de ámbito | **entrega un ítem de un proyecto ajeno** que la petición no autoriza y que `ADR002-A` descarta en `G4` |
| **`RF-19`** sin validación semántica | `capacidades_ausentes` lo declara; no hay lectura de sujeto, polaridad, condición ni tiempo |

---

## 4. Custodia

| | |
|---|---|
| `src/sirius` | **intacto**, árbol `6d8558ef…` |
| `migrations/` | **intacto** |
| `ficha_T0-control_v1.json` | **intacta y CONGELADA**; sin sucesora |
| Rederivaciones `v0.1` y `v0.2` | **válidas**; no se repiten |
| `ADR002-TOL-208` | **íntegra** |
| Familias v0.4, v0.5 y v0.6 | intactas |
| Benchmark | **BLOQUEADO, NO AUTORIZADO y NO EJECUTADO** |

**Regla posterior:** si en el futuro se modificara `src/sirius`, `migrations/` o cualquier valor de la ficha, la cláusula de congelación **sí** se activaría y exigiría ficha sucesora de `T0` y repetición de sus ejecuciones. Esta adjudicación **no** levanta esa regla: comprueba que aquí no se cumple su condición.

---

## 5. Lo que esta adjudicación no hace

- **No** ejecuta `T0` ni ninguna medición.
- **No** modifica Sirius 0.1.
- **No** convierte a `T0` en candidato ni altera su papel de control de falsación.
- **No** satisface ninguna puerta de arranque.
- **No** autoriza el benchmark.
