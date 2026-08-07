# SIRIUS 0.2 — ADR-002 · Orden congelado de las etapas tardías de `ADR002-D`

**Versión:** 1.0
**Estado:** **CONGELADO · anterior a toda implementación y a toda ejecución**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Autoridad:** paso **9** del plan aprobado por
`..._RESOLUCION_PREBENCHMARK_..._v1.0_APROBADA.md` §4, y restricción **2** de
las tres acumulativas que
`..._RESOLUCION_PARTICION_CANDIDATOS_v1.0_APROBADA.md` §7 impone a
`ADR002-D`: el orden de sus etapas tardías debe estar **declarado y congelado
antes de ejecutar**.

**Por qué este documento existe y va solo en su commit.** La restricción no
se cumple escribiéndola en la ficha a la vez que el código: se cumple si el
orden es **anterior comprobable** a la implementación. Este commit precede al
de la implementación y al de la ficha, y esa anterioridad se verifica contra
el grafo de Git, no contra una fecha.

**No implementa nada. No ejecuta nada. No mide nada.**

---

## 1. El orden congelado

| Puesto | Etapa | Señal tardía | Naturaleza |
|---|---|---|---|
| 1.º | **`E3`** | **`relacional_explicita`** | arista declarada del corpus, nombrada, dirigida, de un salto |
| 2.º | **`E4`** | **`semantica_vectorial`** | similitud distribucional de segundo orden sobre el índice local |

> **`E3` relacional, `E4` vectorial.** En ese orden y sólo en ése.

Ninguna de las dos señales actúa fuera de su puesto. En `E0`, `E1`, `E2` y
`E5` **no actúa ninguna**: `ADR002-D` es ahí exactamente `ADR002-A`.

---

## 2. Por qué las dos etapas son `E3` y `E4`, y no dos sub-pasos de `E3`

Las etapas normativas son las seis de `B04 §15.1`, y las que aportan
candidatas son cuatro: `E1`, `E2`, `E3` y `E4`. **Las tardías son `E3` y
`E4`**, y son las únicas dos que hay.

Partir `E3` en dos sub-pasos no satisfaría la restricción 1, la satisfaría en
apariencia y violaría la 3:

- `B04 CA-43` describe exactamente ese caso —«dos señales del mismo espacio
  `E3` aportan coincidencia y relación; **se combinan dentro de `E3`**»— y lo
  llama **coordinación intra-etapa**. Es decir: dos señales dentro de `E3` es,
  por definición canónica, coordinación, no separación.
- `..._RESOLUCION_PARTICION_...` §7 dice que `ADR002-D` existe precisamente
  para **impedir** que la política escalonada derive hacia «recuperación
  coordinada», la alternativa C de `B04 §14.1`, clasificada **«RESERVA
  TÉCNICA, NO POLÍTICA PRINCIPAL»**.
- El nombre canónico de la alternativa es **«Semántica y relacional
  separadas»**. Dos sub-pasos de la misma etapa no están separados: comparten
  el mismo espacio, la misma puerta de suficiencia y la misma transición.

Por tanto: **una señal en `E3`, la otra en `E4`.** No hay tercera lectura
compatible con el corpus aprobado.

---

## 3. Por qué la relacional va primero, y no la vectorial

La decisión **no es de gusto ni de conveniencia**: sale de tres reglas ya
aprobadas que apuntan todas en el mismo sentido.

### 3.1 La autoridad decrece de `E1` a `E4`, y el motor la usa para ordenar

El desempate del motor común es, literalmente,
`ETAPAS_DE_EXPANSION.index(candidata.etapa)`: **`E3` es más autoritativa que
`E4`**. Colocar una señal en `E3` es declararla más autoritativa que la de
`E4`, con efecto observable en el orden de la salida. La pregunta «¿cuál va
primero?» es, en este motor, la pregunta «¿cuál de las dos es más
autoritativa?».

### 3.2 `B04 §15.1` ya contesta cuál es más autoritativa

| Etapa | Lo que `B04 §15.1` dice de ella |
|---|---|
| `E1` | «Consultar afirmaciones, **relaciones** y campos explícitos elegibles; coincidencia literal» → **Resultados de máxima autoridad y trazabilidad** |
| `E3` | «paráfrasis, dependencias, apoyo/refutación y **relaciones**» → «Mejora recall **sin convertir similitud en identidad**» |
| `E4` | «documentos/fuentes y, sólo si procede, historial bruto» → **«Fallback controlado»** |

La **relación explícita** aparece nombrada ya en `E1`, la etapa de máxima
autoridad, porque es un dato declarado del canon: tiene identificador, tipo y
dirección, y se puede auditar arista a arista. La **similitud** no aparece en
`B04` antes de `E3`, y su propia salida normativa está redactada como una
advertencia: no convertirla en identidad.

Una arista nombrada es evidencia declarada. Una similitud distribucional es
una conjetura de forma. Ponerlas al revés colocaría la conjetura por encima
de la evidencia declarada.

### 3.3 La política aprobada obliga a empezar por lo más autorizado

`B04 §15` fija la política adoptada: «comienza por el espacio **más autorizado
y preciso**, amplía **sólo** cuando falta suficiencia». `B04-RF-14` lo hace
exigible. Ejecutar la señal vectorial antes que la relacional invertiría esa
regla dentro del tramo tardío: ampliaría por parecido de forma antes de haber
agotado lo que el canon **ya declara** como relacionado.

**Conclusión:** el orden `E3` relacional → `E4` vectorial es el único
coherente con `B04 §15`, `§15.1`, `RF-14` y con la escala de autoridad que el
propio motor común aplica. Queda congelado.

---

## 4. Consecuencias declaradas de este orden, que no se ocultan

1. **La señal vectorial de `ADR002-D` rankea por debajo de la de
   `ADR002-B`.** Con los mismos elementos alcanzados, `B` los aporta en `E3`
   y `D` en `E4`, y el desempate del motor sitúa `E4` después. Es un efecto
   real del orden congelado, no un defecto: es exactamente lo que la
   separación cuesta.
2. **`E4` aporta en `ADR002-D` elementos canónicos**, no sólo evidencia
   atribuida, porque la señal vectorial materializa por identidad canónica
   exacta a través del puerto. La consecuencia es que una recuperación de `D`
   que llegue a `E4` puede dejar de ser `SOLO_HISTORICO` y pasar a `PARCIAL`
   o `COMPLETA`. Se declara aquí porque es una diferencia observable frente a
   `A`, `B` y `C`.
3. **Si `E3` satisface, la señal vectorial no se ejecuta jamás.** No es una
   optimización: es la política escalonada. El índice vectorial no se abre, no
   se lee y no se verifica, y eso se comprueba por instrumentación.
4. **El orden no es configurable en ejecución.** No hay parámetro, ni variable
   de entorno, ni argumento que lo cambie. Los únicos interruptores de
   `ADR002-D` son los de **ablación**, que **apagan** una señal para poder
   falsarla, y nunca la **mueven** de etapa.

---

## 5. Lo que este documento congela, en términos verificables

| # | Compromiso | Cómo se comprobará |
|---|---|---|
| 1 | La señal relacional sólo actúa en `E3` | invariante en el propio candidato, que falla cerrado si se le pide en otra etapa |
| 2 | La señal vectorial sólo actúa en `E4` | igual invariante |
| 3 | Nunca dos señales tardías en la misma etapa | registro por ejecución de `(etapa, señal)`, con unicidad de etapa comprobada |
| 4 | El orden observado es el congelado | el registro de cada ejecución debe ser **prefijo** de `(E3 relacional, E4 vectorial)` |
| 5 | El orden es anterior a la implementación | este commit es ancestro estricto del commit que implementa `ADR002-D` |
| 6 | El orden es anterior a la ficha | este commit es ancestro estricto del commit que congela `ficha_ADR002-D_v1.json` |

---

## 6. Lo que este documento no hace

- **No** implementa `ADR002-D`.
- **No** aprueba `ADR002-D` ni su ficha.
- **No** autoriza el benchmark, el corpus oficial ni ninguna medición.
- **No** modifica Sirius 0.1, `T0-control`, la capa común, `ADR002-A`,
  `ADR002-B` ni `ADR002-C`.
- **No** fusiona el PR #117.
