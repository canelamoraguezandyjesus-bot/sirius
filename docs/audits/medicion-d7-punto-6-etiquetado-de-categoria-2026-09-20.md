# D7 punto 6 medido, y el desglose que lo explica — 20-09-2026

La cifra que D7 punto 6 exige desde el 29 de agosto y que **nunca se había
producido**. ADR-117 lo dejó dicho con estas palabras: «La cifra real de
coincidencia del etiquetado (D7 punto 6) sigue sin producirse: el umbral que el
propietario registre en `STATUS.md` no puede apoyarse todavía en un dato real».
CI no tiene Ollama y nadie la había corrido en la máquina del propietario.

Árbol: `main` en `66f11424`. Modelo: `qwen3:4b-instruct` (`0edcdef34593`),
el mismo `_CATEGORY_CLASSIFIER_MODEL` que usa producción. Adaptador real
`OllamaCategoryClassifierAdapter`, `/api/chat`, `num_ctx=8192`,
`temperature=0.1`, `think=false`. 95 elementos del banco con texto, contra
`evidence_bank_47_casos_categorias_canonicas.json`.

## La cifra

```
uv run pytest tests/acceptance/test_d7_punto_6_coincidencia_etiquetado.py -q -s
D7 punto 6 (mecanismo de la suite, doble determinista): coincidencia=92/95 (96.8%)
D7 punto 6 (medicion real, Ollama local):               coincidencia=49/95 (51.6%)
2 passed in 79.30s
```

El doble determinista da 96.8%: **el arnés mide bien**. El 51.6% es el modelo.

Una segunda pasada con un guion aparte que reproduce `_medir_coincidencia`
línea por línea dio **48/95 (50.5%)**, consistente con el jitter de ±2 que ya
se había registrado para esta familia de medidas a `temperature=0.1`.
**Cero elementos sin respuesta**: ni un fallo abierto en las dos corridas.

## El suelo contra el que hay que leerla

El canon reparte los 95 elementos en **6** categorías:

| categoría | elementos | |
|---|---|---|
| `trabajo` | 42 | 44.2% |
| `proyecto` | 21 | 22.1% |
| `personal` | 16 | 16.8% |
| `otros` | 8 | 8.4% |
| `finanzas` | 7 | 7.4% |
| `salud` | 1 | 1.1% |

Contestar siempre `trabajo`, sin leer nada, acertaría **42/95 (44.2%)**. El
modelo acierta 48-49. **El aporte sobre esa constante es de +6/+7 elementos.**

Leído así y sin más, el veredicto sería «apenas mejor que una constante». El
desglose dice otra cosa.

## El desglose, que es donde está el hallazgo

Qué contestó el modelo, frente a lo que el canon dice:

| etiqueta | la predice | el canon la usa |
|---|---|---|
| `proyecto` | **54** | 21 |
| `trabajo` | **16** | 42 |
| `personal` | 14 | 16 |
| `otros` | 7 | 8 |
| `finanzas` | 3 | 7 |
| `salud` | 1 | 1 |

Aciertos por categoría canónica:

| categoría | acierta | |
|---|---|---|
| `proyecto` (21) | **20/21** | 95.2% |
| `salud` (1) | 1/1 | 100% |
| `personal` (16) | 12/16 | 75.0% |
| `finanzas` (7) | 3/7 | 42.9% |
| `otros` (8) | 2/8 | 25.0% |
| **`trabajo` (42)** | **10/42** | **23.8%** |

**De los 47 fallos, 29 son una sola confusión: `trabajo` → `proyecto`.** El
62% de todo el error cabe en una casilla. El clasificador funciona en cinco de
las seis categorías y se hunde en una.

Techo si esa confusión se resolviera del todo: **77/95 (81%)**. Es un **techo,
no un pronóstico**: mover la frontera podría costar parte del 20/21 que hoy
acierta en `proyecto`.

## La causa candidata: la instrucción no define nada

`src/sirius/adapters/ollama_category_classifier.py:122-128`, entera:

```python
def _build_instruccion(categorias_ordenadas: list[str]) -> str:
    opciones = ", ".join(categorias_ordenadas)
    return (
        "Clasifica el siguiente contenido en exactamente una de estas "
        f"categorías: {opciones}. Responde solo con el nombre exacto de la "
        "categoría, en el formato pedido."
    )
```

Le entrega las siete palabras del vocabulario y **ninguna definición**. En
particular, nada que separe `trabajo` de `proyecto`, que en español corriente
se solapan. El canon traza una línea que la instrucción nunca enuncia, así que
al modelo se le está pidiendo que adivine un criterio que no consta.

**No está comprobado que ésa sea la causa.** Es la candidata, y es barata de
falsar: misma medición con una instrucción que sí enuncie la frontera. Si salta
hacia el 81%, confirmada; si no salta, la causa es otra.

Dato lateral: `_CATEGORY_VOCABULARY` tiene **7** palabras y el canon solo usa
**6**. `aprendizaje` no aparece en ninguna etiqueta canónica, y el modelo
tampoco la produjo ni una vez.

## Predicciones, publicadas antes de ver el desglose

| predicción | resultado |
|---|---|
| coincidencia entre 55% y 85% | **FALLADA** (51.6%) |
| `trabajo` sobre-representado en lo que predice: el modelo monta en la tasa base | **FALLADA** — predice `trabajo` 16 veces frente a 42 del canon; hace lo contrario |
| `salud` y `finanzas` muy flojas | **MEDIO FALLADA** — `finanzas` 3/7, flojo; `salud` 1/1, perfecta |
| en la segunda pasada, total de 49 ±2 | cumplida (48) |

Ninguna se ha retocado. La segunda es la que más enseña: si hubiera acertado,
el 50.5% no tendría arreglo; al fallar, aparece un defecto localizado y barato
de atacar.

## Estado en que queda D7 punto 6

Lo que bloqueaba el registro del umbral **era la ausencia de esta medición**, y
ya existe. El umbral **no se fija aquí**: D7 punto 6 dice que lo registra el
propietario «a la vista de esa medición».

Lo que esta evidencia añade a esa decisión: fijar un umbral hoy, sobre un 50.5%
cuya causa candidata es una instrucción vacía, sería fijarlo **contra un defecto
conocido** y no contra la capacidad real de la señal.

Y queda dicho, para que nadie lo lea de más: **esto destraba una de las dos
condiciones** que `STATUS.md` pone a `category_matching_enabled`. La otra —la
ola de paridad alcanzando su suelo— sigue abierta, y ADR-202 registra que M17,
la medición que la cerraba, no se hace y la razón no consta.
