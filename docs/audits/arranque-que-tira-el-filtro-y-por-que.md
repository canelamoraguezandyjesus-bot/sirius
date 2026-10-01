# Nota de arranque — ¿Qué tira el filtro, y qué le decimos que tire?

Escrita **antes de mirar**, 20-09-2026. ADR-001.

## Por qué

La entrada 125 dejó el filtro como línea prioritaria: techo 44/47 contra un
suelo de 29/47, y el hueco entero es precisión. Pero también dejó que el filtro
**tira 11 de los 70 esperados** que le llegan, un 15.7%, por encima de la línea
de seguridad del 10%.

Antes de proponer nada sobre el filtro hay que saber dos cosas: **qué tira**, y
**qué le estamos diciendo que tire**. La segunda porque el patrón de esta
noche —entradas 117 y 122— es que nuestras instrucciones parafrasean el canon y
pierden el matiz que se puntúa.

## Las cuatro preguntas

1. Los 11 esperados que el filtro descarta, ¿están repartidos por muchos casos
   o concentrados en pocos?
2. ¿Tienen algo en común: tipo de elemento, criticidad, tamaño del conjunto
   esperado del caso?
3. ¿Qué dice exactamente la instrucción del filtro de relevancia?
4. ¿Esa instrucción define la relevancia con el criterio del canon, o con una
   paráfrasis, como pasó con la cardinalidad y el modo?

## Criterio de parada

- Si los 11 están **concentrados** (en 5 casos o menos) **y** comparten una
  propiedad legible: hay un patrón, se escribe y puede fundamentar un encargo.
- Si están **repartidos** (7 casos o más) **sin** propiedad común: no hay
  patrón atacable desde aquí, se registra el negativo y la mejora del filtro
  tendrá que buscarse midiendo con modelo, no leyendo la grabación.
- Sobre la instrucción: si **reduce** el criterio del canon como pasó con la
  cardinalidad, es un hallazgo por sí solo, independiente de lo anterior.

**Regla dura**: no se propone nada que aumente la agresividad del filtro sin
mirar qué se lleva por delante. Ya paga 11 esperados por 64 de ruido.

No se toca el fixture, ni el corpus, ni `resultado_esperado`. No se lee
`criticidad.razon_segura`.

## Predicción, escrita antes de mirar

Predigo que los 11 están **concentrados en 5 casos o menos**: que hay unos
pocos casos donde el filtro se equivoca varias veces, y no un goteo de uno por
caso. Razón: si fuera goteo, el filtro sería uniformemente mediocre; que
alcance 84.3% sugiere que acierta casi siempre y falla en sitios concretos.

Y predigo que **la instrucción del filtro NO reduce el canon** —al revés que la
del intérprete—, porque M18a la portó **literal** del laboratorio que midió
29/47, y eso está registrado en su ADR. Le doy un 70%.

Si acierto la segunda, la línea de «alinear la instrucción con el canon» se
agota en #653 y el filtro hay que atacarlo por otro sitio.
