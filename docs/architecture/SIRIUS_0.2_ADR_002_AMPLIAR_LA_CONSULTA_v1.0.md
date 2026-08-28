# SIRIUS 0.2 — ADR-002 · Ampliar la consulta: la primera que funciona

**Versión:** 1.0
**Estado:** **RESULTADO POSITIVO** · mejora medida, ninguna regresión, sin tocar nada
**Fecha:** 8 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Alcance:** dentro de `ADR-002`. No se abre ningún ADR. No se toca el corpus, ni
`resultado_esperado`, ni las razones de criticidad, ni el motor, ni ningún
candidato. `ADR002-A/B/C/D` y la capa común quedan **byte a byte**.

---

## 1. Qué se probó

De las seis vías que quedaron sobre la mesa, la número 2: **ampliar la pregunta
con sinónimos naturales antes de buscar**, en vez de cambiar cómo se guarda nada.

Sirius no entiende que «límite de gasto» y «presupuesto máximo» son lo mismo.
Esta vía no le enseña a entenderlo: le hace **preguntar de varias formas a la vez**.

## 2. El resultado

| | exactos | omisiones críticas | contaminación | etapa |
|---|---|---|---|---|
| **base (sin ampliar)** | 24/47 | 11 | 3 | 32/46 |
| **con ampliación** | **26/47** | **7** | 3 | 32/46 |

* **+2 casos exactos**
* **−4 omisiones** (11 → 7)
* **contaminación igual**, ámbito igual, polaridad igual, etapa igual
* **cero casos empeoran**

Es la primera vía probada que mejora **sin degradar nada**. Todas las anteriores
—PPMI, vectores estáticos, transformer contextual, piso crítico— o no cambiaban
nada o empeoraban.

## 3. Qué arregla, y qué no

| caso | antes faltaba | ahora |
|---|---|---|
| `N1-02` «restricciones de transporte» | `MEMORIA:2` | ✅ **exacto** |
| `N1-33` «evidencia de límite de gasto» | `DECISION:3` | ✅ **exacto** |
| `N1-31` «todas las restricciones esenciales» | 5 elementos | quedan 3 |
| `N1-30` | `MEMORIA:1` | igual |
| `N1-34` | 3 elementos | igual |

Lo que arregla son los casos de **sinónimo**. Lo que queda son los de
**categoría**: `MEMORIA:14` («no vuelos con escala»), `MEMORIA:16` («acepta
escala solo si ahorra 200 €») y `MEMORIA:25` («el almacén requiere
autorización») no comparten palabra con «restricciones esenciales» ni la
compartirán por muchos sinónimos que se añadan. Lo único que las une es **ser
restricciones**, y eso no es parecido: es categoría.

**Esto confirma midiendo lo que el documento anterior sostenía en teoría: las
once omisiones no son un problema, son dos.** Ampliar la consulta resuelve la
mitad de sinonimia. La otra mitad necesita que Sirius anote *qué es* cada cosa
cuando la guarda.

## 4. El punto débil, cuantificado

Las ampliaciones las escribió el asistente, que **ya había visto las respuestas
esperadas** de rondas anteriores. No es una ampliación ciega, y eso podría
inflar el resultado.

Para acotarlo se repitió la medición **retirando las siete palabras que el
propio fichero congelado señalaba como sospechosas de estar dirigidas**
—`presupuesto`, `tope`, `maximo`, `limite`, `requisito`, `vehiculo`, `coche`—:

| | exactos | omisiones | contam. | etapa |
|---|---|---|---|---|
| base | 24/47 | 11 | 3 | 32/46 |
| ampliación completa | 26/47 | 7 | 3 | 32/46 |
| **sin las palabras sospechosas** | **25/47** | **10** | 3 | **33/46** |

**Aun bajo la crítica más dura, sigue mejorando** — y la conformidad de etapa
incluso sube. De modo que el efecto es **real**; lo que no está establecido es su
**tamaño**. Para eso hace falta que las ampliaciones las escriba quien no ha
visto el banco, que es exactamente lo que haría el modelo de Sirius en
producción.

Las ampliaciones se congelaron en el repositorio **antes** de medir
(`artifacts/adr002_round/ampliacion_de_consulta_v0.1.json`, commit `5f62f9a`),
de modo que «no las retoqué después de ver el resultado» es comprobable y no una
promesa.

## 5. Por qué esta vía es preferible a las otras cinco

| | ¿toca cómo se guarda? | ¿necesita permisos? | ¿necesita descargas? | ¿rompe el determinismo? |
|---|---|---|---|---|
| **2 · ampliar la consulta** | **no** | **no** | **no** | **no** (se guarda nada) |
| 1 · etiquetar al guardar | sí | no | no | sí, hay que decidirlo |
| 4 · embeddings | no | **sí** | **sí** | no |
| 3 · dárselo todo al modelo | no | no | no | no, pero no escala |

Es la única que mejora **sin pedir nada a nadie**. Se añade un paso antes de
buscar y se puede quitar igual de fácil.

## 6. Lo que NO se ha hecho

| | motivo |
|---|---|
| Implementarlo en Sirius | es un cambio de comportamiento; requiere aprobación explícita |
| Medir latencia y coste | añade una llamada al modelo por consulta: hay que medirlo antes de adoptarlo |
| Repetir la ronda oficial | el código del experimento no cambió; esto se midió en arnés aparte |
| Ampliación ciega | necesita que la escriba quien no vea el banco; es el siguiente paso natural |

## 7. Lo que propongo

1. **Repetir esto con ampliaciones ciegas** para establecer el tamaño real del efecto.
2. **Medir la mitad que falta** —etiquetar al guardar— con el mismo método.
3. Y solo entonces decidir si se implementa una, la otra, o las dos.

Las dos son complementarias y atacan mitades distintas del mismo problema.

---

**Reproducir:** `artifacts/adr002_round/ampliacion_de_consulta_v0.1.json` contiene
las ampliaciones íntegras, incluida la lista de cuáles cargan el peso del
resultado.
