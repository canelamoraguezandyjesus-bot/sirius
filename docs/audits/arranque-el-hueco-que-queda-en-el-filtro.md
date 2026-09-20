# Nota de arranque — El hueco que queda en el filtro: ¿exceso o defecto?

Escrita **antes de mirar**, 20-09-2026, 17:40 UTC. ADR-001.

## Por qué

`hallazgo-el-techo-esta-en-el-filtro-no-en-la-busqueda.md` dejó el mapa
ordenado y un número que nadie ha desglosado todavía:

| | casos exactos |
|---|---|
| techo con filtro perfecto (petición declarada) | **44/47** |
| alcanzado por la grabación congelada | **32/47** |
| suelo D1 | 29/47 |

**Doce casos** separan lo que el filtro real consigue de lo que un filtro
perfecto conseguiría con la misma búsqueda. Esos doce son, hoy, **todo lo que
queda por ganar en la línea prioritaria del proyecto**. Nadie ha mirado caso
por caso qué les pasa.

Y hay una razón concreta para mirarlo **ahora**: el encargo preparado
(`encargo-preparado-modo-y-corte.md`) deja la instrucción del filtro **fuera
de alcance** a propósito, porque está portada literal del laboratorio y
tocarla es decisión del propietario. Si resulta que el hueco **no** se explica
por la instrucción, esa decisión se le puede ahorrar: no habría nada que
decidir.

## Las cuatro preguntas

1. De los 47 casos, ¿en cuántos el veredicto de la grabación coincide
   **exactamente** con el conjunto esperado? (re-derivar el 32, no heredarlo).
2. De los que fallan, ¿cuántos fallan **solo por exceso** (conserva ruido),
   cuántos **solo por defecto** (tira esperado) y cuántos por las dos cosas?
3. El ruido conservado, ¿está concentrado en pocos casos o repartido? ¿Los
   elementos comparten una propiedad legible?
4. ¿Hay alguna regla de la instrucción del filtro que explique ese ruido
   conservado — o es ruido que la instrucción **ya manda tirar** y el modelo
   no tira?

## Criterio de parada

- Si el exceso está **concentrado** (6 casos o menos) **y** los elementos
  comparten una propiedad legible: hay patrón atacable, se escribe, y puede
  fundamentar un encargo sobre el filtro.
- Si está **repartido** (10 casos o más) **sin** propiedad común: no hay
  patrón atacable leyendo; se registra el negativo y se dice que mejorar el
  filtro exige medir con modelo, no reescribir prosa.
- Si **más de la mitad** de los casos que fallan lo hacen **por defecto** y no
  por exceso: la prioridad se invierte — el problema no es que el filtro sea
  permisivo sino que es agresivo, y cualquier propuesta de apretarlo está mal
  planteada.
- **Pregunta 4 con respuesta «la instrucción ya lo manda tirar»**: entonces la
  línea de «alinear instrucciones con el canon» **no alcanza al filtro**, y
  hay que decirlo con todas las letras en vez de dejar al propietario una
  decisión que no cambia nada.

**Regla dura**: no se propone nada que aumente la agresividad del filtro sin
contar qué se lleva por delante. No se toca el fixture, ni el corpus, ni
`resultado_esperado`, ni las adjudicaciones. No se lee `criticidad.razon_segura`.

## Predicción, escrita antes de mirar

1. **Dominan los fallos por exceso**: >= 70% de los casos que fallan lo hacen
   **solo por exceso**. Razón: la entrada 127 ya contó solo **4** descartes
   reales de esperado en todo el banco, y 35 elementos de ruido conservados.
2. **El exceso está repartido, no concentrado**: 10 casos o más. Razón: 35
   elementos entre una docena larga de casos son dos o tres por caso; para que
   estuviera concentrado haría falta que un caso se llevara la mitad, y el
   caso que podría hacerlo —`CA-34`, el de cuota— ya sabemos que va al revés
   (allí el filtro tira, no conserva). Le doy un **60%**.
3. **La propiedad del ruido conservado será «mismo tema, no responde»** — que
   es exactamente lo que la séptima regla de la instrucción **ya prohíbe**:
   «Una frase que habla del mismo tema pero no responde a la pregunta no
   cuenta». Le doy un **65%**.

**Si acierto la tercera, el resultado es un cierre, no una palanca**: la
instrucción del filtro no reduce el canon (entrada 127) y tampoco omite la
regla que haría falta; el hueco sería del modelo obedeciendo mal una regla que
ya está escrita. Eso **cierra** la línea de prosa sobre el filtro y deja como
únicas salidas medir con modelo, cambiar de modelo, o un mecanismo distinto
del texto de la instrucción.

Si fallo la tercera y el ruido conservado tiene otra propiedad —una que la
instrucción no nombra—, entonces sí hay encargo, y esta nota dice de antemano
que tendrá que declarar **qué se lleva por delante**.
