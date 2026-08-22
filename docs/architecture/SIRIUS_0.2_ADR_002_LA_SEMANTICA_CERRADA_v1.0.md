# Sirius 0.2 · ADR-002 · La señal semántica, cerrada

**Estado:** evidencia dentro de ADR-002. No abre ADR nuevo. PR #117 sigue abierta y sin fusionar.

**Cierra** la duda que dejó abierta `SIRIUS_0.2_ADR_002_SEMANTICA_REAL_FALSADA_v1.0.md`.

---

## La pregunta

`ARQ-00 §23` dejó deliberadamente sin decidir si Sirius necesita señal semántica densa. La
falsación anterior la puso a prueba con tres modelos locales —`md`, `lg` y un transformador— y las
once omisiones no se movieron en ninguno de los dieciocho puntos de operación.

Quedaba una objeción legítima, y la escribí yo mismo: **esos modelos no están entrenados para
recuperar**. Un vector promediado de palabras no es lo mismo que un modelo de recuperación. Podía
ser que el problema fuese el modelo y no la hipótesis.

Esa objeción ya está contestada.

---

## La medida

`text-embedding-3-small`, 512 dimensiones, ejecutada en la máquina que tiene la clave. Umbral
barrido entero y curva publicada completa: elegir el punto después de verlo sería fijar la medida
sobre el resultado, que es lo que el §8.1 prohíbe.

La línea base reproduce exacta —24/47, 11 omisiones, 3 contaminaciones—, así que la comparación
vale.

| corrida | exactos | omisiones | fuga real |
|---|---|---|---|
| **línea base (solo léxica)** | **24/47** | **11** | 0 |
| coseno ≥ 0,25 | 19/47 | 10 | 0 |
| coseno ≥ 0,35 | 20/47 | 10 | 0 |
| coseno ≥ 0,45 | 21/47 | 10 | 0 |
| coseno ≥ 0,55 | 24/47 | 11 | 0 |
| coseno ≥ 0,65 | 24/47 | 11 | 0 |

**Nunca supera la línea base.** Recupera **una** omisión de once —algo que ningún modelo local
consiguió, luego el modelo real sí es mejor que ellos— y lo paga con entre 3 y 5 aciertos exactos.
De 0,55 en adelante no propone nada: es inerte.

---

## Lo que decide el asunto: no se suma a lo que ya funciona

La ampliación de consulta es la vía aprobada. La pregunta útil no es «¿la semántica mejora la línea
base?» sino «¿aporta algo **encima de lo que ya tenemos**?».

| corrida | exactos | omisiones |
|---|---|---|
| **ampliación sola** | **26/47** | **7** |
| ampliación + semántica, coseno ≥ 0,25 | 20/47 | 7 |
| ampliación + semántica, coseno ≥ 0,35 | 21/47 | 7 |
| ampliación + semántica, coseno ≥ 0,45 | 23/47 | 7 |
| ampliación + semántica, coseno ≥ 0,55 | 25/47 | 7 |
| ampliación + semántica, coseno ≥ 0,65 | 26/47 | 7 |

**Las omisiones se quedan en 7 en los cinco puntos.** Ni una menos. Lo único que hace la semántica
por encima de la ampliación es **quitar aciertos**, hasta seis en el punto más bajo.

Las dos vías no se suman porque no son independientes: la ampliación ya se llevó esas cuatro
omisiones, y más. La semántica llega tarde a un sitio donde ya no queda nada que recoger.

---

## Conclusión binaria

**La señal semántica densa no resuelve el problema medido en ADR-002.** No es una cuestión de
modelo: se probó con tres modelos locales y con uno entrenado para recuperar, y el entrenado para
recuperar tampoco. La hipótesis queda falsada con la única variable que quedaba controlada.

**Lo que gana sigue siendo la ampliación de consulta: 26/47 exactos, 7 omisiones, sin ninguna
regresión** en contaminación, ámbito, polaridad ni etapa.

---

## Tres cosas más que la corrida dejó probadas

**1. La fusión `RRF` es inerte en este banco, ahora con señal real.** Concatenar y fusionar dan
cifras idénticas en los diez puntos del barrido. Es la tercera confirmación independiente, y la
más fuerte: las dos anteriores usaban señal nula o aleatoria, esta usa señal de verdad. Coincide
con lo ya medido —45 de 50 casos no declaran límite, y en 0 de los 21 que llegan a `E3` una
candidata añadida al final caería fuera—.

**2. El defecto del arnés se disparó de verdad.** Los tres puntos con `FUGA=1` son **todos** el
ítem global `MEMORIA:1`; el recuento de fuga real es **cero en las diecisiete corridas**. Sin el
desglose, esas tres filas se habrían leído como fallo duro del §6.1 y habrían descalificado a la
vía semántica por una razón falsa. La conclusión de arriba no depende de eso —la semántica pierde
igualmente por exactitud—, pero el aviso hizo exactamente el trabajo para el que se puso.

Sigue pendiente decidir cuál de las dos lecturas —la de `G4` o la de la métrica— es la correcta.
Es una decisión sobre el arnés congelado y no se toma sin acto.

**3. El puerto del codificador cumple lo que prometía.** Añadir un proveedor nuevo fue escribir una
clase de tres miembros. No se tocó el sidecar, ni el lector, ni ningún candidato, ni la capa común.
Eso es lo que `B04-RF-31` pide, comprobado y no prometido.

---

## Reproducir

```powershell
$env:PYTHONPATH = "src"
uv run python -m experiments.adr002.hibrido.medir_con_openai
```

Evidencia: `artifacts/adr002_round/semantica_real_openai_v0.1.json`, emitido por la máquina que
ejecutó la medición.

Lo que salió de la máquina: los 97 textos del canon experimental —un corpus inventado— y una
consulta por caso. Ninguna identidad, ninguna criticidad, ninguna anotación del banco, ningún
resultado esperado. Coste real: por debajo de un céntimo.

---

## Estado

- PR #117: **abierta y sin fusionar**.
- `ADR002-C`: congelado como línea base, intacto.
- Corpus, `resultado_esperado`, razones de criticidad y adjudicación: **sin tocar**.
- `criticidad.razon_segura`: **no leída**.
- Quality: verde.
