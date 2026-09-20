# Nota de arranque — ¿Se puede derivar la cardinalidad de la forma del conjunto esperado?

Escrita **antes de mirar los datos**, 20-09-2026. ADR-001.

## Por qué

La entrada 117 dejó dos cosas: (a) el defecto del intérprete es que define la
cardinalidad por la **gramática de la pregunta** mientras el canon la define por
la **forma del conjunto de respuesta**; (b) **§15.2 no está en el repositorio**,
así que el criterio exacto del canon solo consta por dos fuentes secundarias:
«la instanciación cierra el conjunto sobre el universo declarado» y
«EXHAUSTIVA declaran dominio y cierre calculable».

Escribir una instrucción nueva **interpretando** una regla que no se puede leer
es la forma de quemar un encargo y una medición del propietario.

Pero la regla deja huella en los datos: si el criterio es sobre la forma del
conjunto de respuesta, entonces la cardinalidad de cada caso debería ser
**predecible desde su `resultado_esperado`**. Eso se comprueba aquí, gratis.

## Las cuatro preguntas

1. ¿Se puede predecir la cardinalidad de los 47 casos desde propiedades de
   `resultado_esperado` (tamaño, y poco más)?
2. Si se puede, ¿cuál es la regla más simple que lo consigue, y cuántos casos
   falla?
3. Los casos que falle, ¿tienen algo en común que apunte a la parte de §15.2
   que no consta?
4. ¿Esa regla es **enunciable a un modelo** que solo ve la pregunta, o solo
   funciona mirando la respuesta —que el intérprete no tiene?

La 4 es la que decide si esto sirve de algo: una regla que solo se puede
aplicar viendo la respuesta **no se le puede pedir al intérprete**.

## Criterio de parada

- Si aparece una regla simple que explica **>= 40 de 47**: se registra como la
  mejor reconstrucción disponible de §15.2, y se responde a la pregunta 4.
- Si ninguna regla simple pasa de **35/47**: se registra que la cardinalidad
  **no se deriva del conjunto esperado**, y el encargo sobre la instrucción
  queda bloqueado hasta que §15.2 entre en el repositorio o el propietario
  enuncie el criterio.
- Entre 35 y 40: se registra el número tal cual y **no se propone encargo**.

No se toca el corpus ni ninguna adjudicación. Solo se leen
`peticion_p2.cardinalidad` y `resultado_esperado`, que son públicos del banco.
No se lee `criticidad.razon_segura`.

## Predicción, escrita antes de mirar

ADR-111 menciona de pasada «los tres casos con cardinalidad `EXACTA` y más de
un elemento», lo que sugiere que `EXACTA` es casi siempre **un solo elemento
esperado**.

Predigo que la regla **«`EXACTA` si y solo si `len(resultado_esperado) == 1`»**
acierta **entre 38 y 43 de 47**, y que los fallos serán esos tres `EXACTA` de
varios elementos más algún `ACOTADA`.

Y predigo que la respuesta a la pregunta 4 será **NO**: que la regla necesita
ver la respuesta y por tanto **no es enunciable al intérprete tal cual**, lo que
dejaría el encargo bloqueado. Le doy un 65% a ese «no».

Si acierto en esto último, el resultado útil de la noche es **haber evitado el
encargo**, no haberlo lanzado.
