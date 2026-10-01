# Nota de arranque — ¿De dónde salen los elementos de más?

Escrita **antes de medir nada**, 20-09-2026. Disciplina de ADR-001.

## Por qué

De los tres suelos de D1, dos están alcanzados (0 omisiones críticas, 70/81 de
cobertura) y falta el tercero: 8/47 aciertos exactos contra 29/47. La causa
está registrada y es deliberada: **la respuesta trae de más, no de menos**
(ADR-129 aceptó el precio por escrito antes de medirlo).

«Podar» no es un plan. Antes hay que saber **qué** podar.

`rank_relevant_knowledge.py:680` compone el resultado de cuatro fuentes:
el motor (`ranked`), la ampliación por categoría (`solo_por_categoria`), el
rescate por criticidad (`solo_por_criticidad`, M19b/ADR-128) y la siembra
(`siembra`, M20/ADR-129). Los de la siembra llevan `seeded=True`.

## Las cuatro preguntas

1. De los elementos de más de cada caso, ¿cuántos vienen de la **siembra** y
   cuántos de las otras tres fuentes?
2. ¿Cuántos casos tienen elementos de más **solo** por siembra —es decir,
   cuántos se arreglarían podando únicamente ahí?
3. La siembra existe para no perder lo crítico. De lo que siembra, ¿cuánto
   **acaba siendo esperado** y cuánto es puro ruido?
4. ¿Hay casos donde la siembra sea la **única** razón de que no haya acierto
   exacto —o sea, casos que serían exactos sin ella?

## Criterio de parada, decidido ahora

- Si la siembra explica **más de la mitad** de los elementos de más: hay una
  palanca concreta y se diseña el encargo sobre ella.
- Si explica **menos de un tercio**: la siembra **no es el problema**, se
  registra así y NO se toca — el ruido está en el ranking y es otra
  investigación.
- Entre un tercio y la mitad: se registra el reparto y **no se propone nada**
  sin un segundo dato, porque podar la siembra tocaría la pieza que sostiene
  las 0 omisiones críticas, que es lo único que el propietario declaró
  intocable.

**En ningún caso se propone podar algo que haga perder una crítica.** Las 0
omisiones son el suelo alcanzado; un encargo que las ponga en riesgo no se
lanza aunque suba los exactos.

Medición determinista, con el doble del filtro, sin Ollama. No se toca el
corpus, ni `resultado_esperado`, ni `src/`. No se lee `criticidad.razon_segura`.

## Predicción, escrita antes de medir

Creo que **la siembra explica la mayor parte**: entre el **55% y el 80%** de
los elementos de más. La razón: la siembra mete *todo* lo no ordinario del
ámbito en *cada* consulta, sin mirar la pregunta —el `subject_matches_query` y
el `fts_match` van a `False` por construcción—, así que su aportación no
depende del caso y debería dominar.

Y predigo que **su precisión es muy baja**: menos del 15% de lo sembrado
estará en el `resultado_esperado` del caso.

Si acierto, la palanca existe pero es peligrosa, porque es la misma pieza que
compra las 0 críticas. Si fallo —si la siembra aporta poco—, el ruido viene del
ranking y esta línea de trabajo se cierra aquí.
