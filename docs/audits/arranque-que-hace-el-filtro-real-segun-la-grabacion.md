# Nota de arranque — ¿Qué hace el filtro real, según la corrida congelada?

Escrita **antes de mirar el fixture**, 20-09-2026. ADR-001.

## Por qué, y por qué esto corrige algo que dije

La entrada 120 cerró la línea del motor con un negativo medido y concluyó que
**el filtro de relevancia es la única pieza capaz de separar lo que la búsqueda
no puede** — y que su medición «solo se puede hacer con Ollama», o sea en la
máquina del propietario.

**Eso era incompleto.** Existe
`tests/acceptance/fixtures/relevance_filter_frozen_run.json`: una **grabación
de una corrida real** del filtro, con, por cada caso, qué identidades
`entraron_al_filtro` y cuáles `conservados_por_el_modelo`. Es el doble que usa
el arnés de examen —el que alcanza 29/47— y es determinista.

Así que el comportamiento del filtro real **sí se puede estudiar aquí**, sobre
una corrida que de verdad ocurrió. No es lo mismo que medir hoy con Ollama
—esa grabación es de un árbol y un momento concretos—, pero es evidencia real y
no un doble inventado.

## Las cuatro preguntas

1. ¿Cuánto descarta? De lo que entra al filtro, qué proporción conserva.
2. ¿Tira cosas que se esperaban? De los elementos **esperados** que entraron,
   cuántos sobrevivieron. Es la pregunta que decide si el filtro es seguro.
3. ¿Cuánto ruido quita? De lo que entró y **no** se esperaba, cuánto descartó.
4. Con eso: ¿qué precisión y qué recuperación tiene el filtro sobre lo que se
   le pone delante?

## Criterio de parada

- Si el filtro conserva **>= 95%** de los esperados que entran **y** descarta
  **>= 50%** del ruido que entra: queda demostrado que **es la pieza que
  separa**, y eso convierte «mejorar el filtro» en la línea de trabajo
  prioritaria, por delante de tocar el motor.
- Si tira **más del 10%** de los esperados: el filtro **no es seguro** tal cual,
  y cualquier plan que descanse en él tiene que decirlo primero.
- Si descarta **menos del 25%** del ruido: el filtro no está separando gran
  cosa y el problema de precisión no se resuelve por ahí.

**Lo que no se hace pase lo que pase**: no se toca el fixture, ni el corpus, ni
`resultado_esperado`. No se lee `criticidad.razon_segura`. Solo se leen las dos
listas de la grabación y el `resultado_esperado` del banco.

## Predicción, escrita antes de mirar

El diagnóstico de `medir_banco_con_ollama_real.py --diagnostico` ya dijo que el
laboratorio pierde **4 críticas y las cuatro por `NO_ENTRO`** —ninguna
`TIRADO_POR_EL_FILTRO`—. O sea que sobre las críticas el filtro no tiró nada.

Predigo que eso se extiende a los esperados en general: **conserva >= 95% de
los esperados que entran**. Y predigo que **descarta entre el 50% y el 80% del
ruido**, porque ésa es la palanca que separa el `7/47` sin filtro del `22/47`
con filtro que el propietario midió el 02-09.

Si acierto las dos, el filtro queda demostrado como la pieza buena, y la línea
de trabajo del proyecto cambia de sitio con evidencia detrás.
