# Nota de arranque — ¿La cardinalidad del banco es un juicio o una regla mecánica?

Escrita **antes de mirar nada**, 20-09-2026. Disciplina de ADR-001.

## Por qué esta investigación existe

La medición de la palanca 1 (20-09, entrada 114) dejó el error entero
concentrado en un campo: `cardinalidad` 30/47 en dos corridas independientes,
con `ACOTADA` nunca producida. El paso siguiente obvio sería atacarla.

Pero ese mismo día, D7 punto 6 enseñó que **el patrón contra el que se mide
puede no ser lo que parece**: las etiquetas canónicas de categoría resultaron
ser la salida de una regla de palabras clave (ADR-116), no un juicio, y el
experimento que iba a lanzarse quedó cancelado por inútil antes de correrse.

Así que antes de gastar un encargo: **¿de dónde salen los valores de
`cardinalidad` de las 47 `peticion_p2`?**

## Las cuatro preguntas

1. ¿Salen de un criterio declarado por una persona caso por caso, o de una
   regla mecánica aplicada al texto de la consulta?
2. Si hay regla, ¿está escrita en algún ADR, como ADR-116 escribió la suya?
3. ¿Se puede reproducir la etiqueta de cada caso desde el texto de su consulta
   con una regla simple? (Si se puede, es mecánica aunque nadie la escribiera.)
4. De los 17 fallos de cardinalidad del modelo, ¿cuántos caen en casos cuya
   etiqueta viene de una regla y no de un juicio?

## Criterio de parada, decidido ahora

- Si aparece un ADR que declare una **regla mecánica** para la cardinalidad:
  la investigación termina en «es mecánica, **no se ataca**», se registra, y no
  se lanza ningún encargo sobre ese campo.
- Si aparece que son **adjudicaciones caso por caso** de una persona: termina
  en «es juicio, **se puede atacar**», y se pasa a diseñar el encargo.
- Si **no consta** ni una cosa ni otra tras una búsqueda dirigida: se registra
  como «no consta», igual que ADR-202 hizo con la razón de M17, y **no se
  inventa una respuesta verosímil**. Una razón que nadie tomó se lee después
  como si constara.

No se toca el corpus, ni `resultado_esperado`, ni ninguna adjudicación. No se
lee `criticidad.razon_segura`.

## Predicción, escrita antes de mirar

Creo que la cardinalidad **sí es un juicio** y no una regla de palabras clave,
porque `EXACTA`/`ACOTADA`/`EXHAUSTIVA` dependen de la intención de la pregunta
y no de que aparezca tal o cual palabra.

Con una excepción que espero encontrar: que **`ACOTADA` se asignara donde la
consulta trae un número explícito** («máximo duro 5», «las tres cosas»,
«enumera»). Si es así, esa parte sí sería mecánica.

Probabilidad que le doy a «es mecánica entera»: **30%**.

Si acierto, el encargo sobre cardinalidad tiene sentido. Si fallo, se cancela
igual que se canceló el de D7 punto 6, y habré ahorrado el encargo en vez de
gastarlo.
