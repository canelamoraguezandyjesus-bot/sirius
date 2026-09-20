# Nota de arranque — ¿De dónde sale el ruido del motor?

Escrita **antes de medir**, 20-09-2026. ADR-001.

## Por qué

La entrada 118 dejó el reparto de los elementos de más con petición declarada:
**motor 110 (67.9%)**, categoría/criticidad 44, siembra 8. La siembra queda
descartada por su propio criterio de parada, y el encargo sobre el intérprete
está **bloqueado** (entrada 119) hasta que el propietario enuncie el criterio
de §15.2.

Queda el motor, que es el mayor y está **desbloqueado**: se mide aquí, sin
Ollama, y un encargo sobre él **sí** lo puede juzgar el ciclo.

## Un dato que conviene tener delante antes de empezar

Con la petición declarada —la mejor petición posible, el techo de lo que un
intérprete perfecto puede comprar— la etapa de búsqueda da **17/47 exactos**.
El suelo de D1 es **29/47**.

O sea: **arreglar el intérprete es necesario pero no suficiente.** Aunque fuera
perfecto, faltarían 12 aciertos exactos. Tienen que salir de otro sitio, y el
motor es el único candidato grande que queda.

(Matiz honesto: ese 17/47 es SIN filtro. Qué da la petición declarada CON el
filtro real no se sabe, y no se puede saber aquí.)

## Las cuatro preguntas

1. De los 110 elementos de más que admite el motor con petición declarada,
   ¿qué señales traen? (`fts_match`, `category_match`,
   `subject_matches_query`, `project_matches_active`.)
2. ¿Hay un grupo dominante —por ejemplo, admitidos sin ninguna señal fuerte—
   que apunte a una puerta que admite de más?
3. ¿Cuántos de los 47 casos serían exactos si ese grupo no entrara?
4. Quitarlo, ¿pondría en riesgo alguna omisión crítica o algún elemento
   hallado?

La 4 manda sobre las otras tres.

## Criterio de parada

- Si un grupo explica **>= 60%** de los 110 **y** quitarlo no pierde ninguna
  crítica ni ningún hallado: hay propuesta concreta, se escribe y se puede
  lanzar encargo, porque esto lo juzga el ciclo sin Ollama.
- Si ningún grupo pasa del **40%**: se registra que el ruido del motor está
  repartido y **no hay palanca simple**; la línea se cierra aquí.
- Entre 40% y 60%: se registra el reparto y no se propone encargo.

**Regla dura, por encima de todo lo anterior**: no se propone nada que pierda
una omisión crítica o baje los 78/81 hallados. Los dos suelos alcanzados no se
tocan ni a cambio de aciertos exactos.

Determinista, sin Ollama, sin tocar `src/`, ni el corpus, ni
`criticidad.razon_segura`.

## Predicción, escrita antes de medir

Predigo que el grupo dominante serán los admitidos **solo por coincidencia
léxica** —`fts_match=True` y `category_match=False`—, y que serán entre el
**45% y el 75%** de los 110. La razón: la búsqueda léxica sobre texto libre es
la puerta más ancha que tiene el motor, y una palabra compartida basta.

Y predigo que la respuesta a la pregunta 4 será **que sí pone en riesgo
hallados**: que ese mismo grupo trae también elementos esperados, porque la
coincidencia léxica es la que encuentra lo que se pide. Le doy un **70%**.

Si acierto en eso segundo, la conclusión será que **no hay palanca simple en el
motor tampoco**, y la línea se cierra con un negativo medido — que es un
resultado, no un fracaso.
