# SIRIUS 0.2 — ADR-002 · Autorización para ejecutar la ronda primaria

**Versión:** 1.0
**Estado:** **AUTORIZADA · la ronda primaria puede ejecutarse**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**
**HEAD sobre el que se autoriza:** `c2907933dbddf0836db05440d9b0c6d47d227f05`

**Autoridad:** paso **11** del plan aprobado por
`SIRIUS_0.2_ADR_002_RESOLUCION_PREBENCHMARK_CONTRATO_COMUN_Y_FUENTE_RELACIONAL_v1.0_APROBADA.md`
§4, sobre el cierre previo declarado en
`SIRIUS_0.2_ADR_002_CIERRE_PREVIO_AL_BENCHMARK_v1.0.md`.

**Acto de autorización:** el usuario, directamente en el chat de trabajo, en
respuesta a la solicitud única del §12 del cierre previo:

> «**Sí, autorizo la ronda.**»

sobre la pregunta literal:

> «¿Autorizas ejecutar la ronda primaria de ADR-002 (`T0-control`, `A` v5,
> `B` v7, `C` v2 y `D` v2, sin reducción) bajo el plan ya congelado: 11
> sesiones exactas, 100 repeticiones, warm-up de 10 descartado, semilla
> `20260726`, reloj `time.perf_counter_ns` y orden intercalado y rotado?»

Con esta acta, la única precondición que `run_round --check` echaba en falta
queda satisfecha. **Ninguna otra cosa cambia**: el plan sigue siendo el
congelado, y este documento no lo modifica.

---

## 1. Lo autorizado, exactamente

| | |
|---|---|
| Participantes | `T0-control`, `ADR002-A` v5, `ADR002-B` v7, `ADR002-C` v2, `ADR002-D` v2 |
| Reducción | **ninguna**; retirar cualquiera bloquea la ejecución |
| Sesiones | **11 exactas**, cada una un proceso independiente del sistema operativo |
| Repeticiones | **100** por participante y magnitud |
| Warm-up | **10**, declarado y descartado íntegro |
| Semilla | `20260726` |
| Reloj | `time.perf_counter_ns` |
| Orden | intercalado y rotado por `(sesión + repetición) mod 5` |
| Percentiles | por rango más cercano, **nunca interpolados** |

Es literalmente lo que `experiments/adr002/round/round_protocol.py` congeló
**antes** de que existiera un solo resultado, que es lo que el §8.1 del
protocolo v0.2 prohíbe cambiar después de observarlos.

---

## 2. Lo que esta acta NO autoriza

- **No autoriza cambiar el plan.** Ni las sesiones, ni las repeticiones, ni el
  orden, ni la semilla, ni el reloj, ni los percentiles.
- **No autoriza reducir la ronda** ni retirar ningún participante.
- **No elige ganador.** La ronda produce evidencia; elegir es un acto
  posterior y separado del usuario.
- **No aprueba** `ADR-002` ni cierra la decisión.
- **No autoriza tocar Sirius 0.1 productivo**, ni fusionar el PR #117, ni
  abrir ningún eje contingente (`EJE-1`, `EJE-2`).
- **No autoriza remedir.** Si la corrida resulta inválida por sus controles
  funcionales, rige el §6.8 del protocolo —**una** repetición— y si esa
  también falla, el §6.9: **`NO_EVALUABLE`**, sin artefacto y sin cifras.

---

## 3. Dos precisiones que la ejecución obliga a declarar

Ninguna de las dos cambia el plan autorizado. Las dos se declaran **antes** de
medir, porque descubrirlas después de ver resultados sería exactamente lo que
el §8.1 prohíbe.

### 3.1 El sustrato de la medición es la proyección de la familia v0.6

El cierre previo fijó por blob el corpus de rendimiento
`performance_corpus_v0_2.json`, sobre el que se rederivó la línea base de `T0`.
Ese corpus **no puede alojar a los cuatro candidatos**, y no por una decisión
de diseño sino por dos hechos comprobables del repositorio:

1. sus identificadores tienen la forma `DEC-P-00001`, que la biyección de
   identidad canónica de la proyección (`^(MEM|DEC|MSG|DOC)-(\d+)$`) **no
   acepta**; y
2. no tiene canales de `subject_key` ni de `property_key` —los que existen
   cubren los 97 ítems de la familia de conformidad y ninguno de sus 550—, de
   modo que la proyección no es construible sobre él.

`ADR002-C` y `ADR002-D` leen su plano relacional **del plano `ejes_p2` de la
proyección**, que solo existe si la proyección existe.

La consecuencia es que los cinco se miden sobre **el mismo fichero**:
`entrada.sqlite3`, materializado desde la familia de conformidad **v0.6**, que
lleva el **esquema canónico de Sirius 0.1 sin DDL adicional** y por eso `T0`
—que es Sirius 0.1— corre sobre él igual que los candidatos. El §5.4 del
protocolo se cumple en su forma más estricta: no es «el mismo corpus», es **el
mismo fichero**.

**Lo que esto cuesta, dicho sin adornos:** las cifras de latencia de esta ronda
son comparables **entre los cinco participantes**, que es lo que elegir exige,
y **no** son comparables con los valores absolutos de la línea base rederivada
de `T0`, que se midió a otra escala. Es la incertidumbre 4 del §12 de la
especificación del benchmark —«escala del corpus»—, que sigue abierta y que
esta ronda **no cierra**.

### 3.2 La familia de conformidad se fija por blob, como todo lo demás

El cierre previo fijó por blob el corpus, la línea base, el perfil y el suelo,
pero **no la familia de conformidad**, que es la entrada que la ronda va a leer
de verdad. Era un hueco del cierre, y se tapa aquí **antes** de medir: la
ronda pasa a exigir byte a byte los cuatro congelables de la v0.6 y los tres
que hereda, con los blobs que `schema_v0_6.py` ya declara.

Añadir un control que **bloquea más** no altera el plan de medición ni favorece
a nadie: ningún participante gana o pierde porque la entrada esté verificada.

---

## 4. Estado tras esta acta

`run_round --check` deja de reportar precondiciones pendientes. La ejecución es
un acto distinto de la comprobación y ocurre en su propio recorrido, que
comprueba de nuevo **todo** antes de abrir la primera ventana cronometrada y
falla cerrado si algo cambió.

**La ronda no elige.** Produce evidencia auditable, y la elección vuelve al
usuario con esa evidencia delante.
