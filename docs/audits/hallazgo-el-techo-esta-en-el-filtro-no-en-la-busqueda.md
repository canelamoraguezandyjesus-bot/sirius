# El techo está en el filtro, no en la búsqueda — 20-09-2026

Responde a `arranque-que-hace-el-filtro-real-segun-la-grabacion.md`, escrita
antes de mirar. Determinista, sin Ollama, sobre `main` en `66f11424`.

## Lo primero: una corrección de la entrada 120

La entrada 120 dijo que medir el filtro «solo se puede hacer con Ollama». **Es
falso.** `tests/acceptance/fixtures/relevance_filter_frozen_run.json` es una
**grabación de una corrida real** del filtro: por cada caso, qué identidades
`entraron_al_filtro` y cuáles `conservados_por_el_modelo`. Es el doble que usa
el arnés de examen que alcanza 29/47, y es determinista.

Segunda vez en la misma noche que afirmo «no se puede» sin haber mirado en
todos los sitios (la primera, §15.2 en la entrada 121).

## Qué hace el filtro real

```
ENTRARON al filtro ............ 169
CONSERVADOS ................... 94   (55.6% de lo que entro)

ESPERADOS que entraron ........ 70
  conservados ................. 59   (84.3%)   <- recuperacion
  TIRADOS por el filtro ....... 11

RUIDO que entro ............... 99
  descartado .................. 64   (64.6%)
  conservado .................. 35

PRECISION de lo conservado .... 59/94 = 62.8%
```

**El filtro tira 11 de los 70 elementos esperados que le llegan**: un 15.7%.

El criterio de parada, escrito antes, decía: *si tira más del 10% de los
esperados, el filtro **no es seguro** tal cual, y cualquier plan que descanse
en él tiene que decirlo primero.* **Queda dicho.**

Con un matiz que lo hace vivible: el diagnóstico de
`medir_banco_con_ollama_real.py` ya mostró que las críticas que el laboratorio
pierde son **todas por `NO_ENTRO`**, ninguna `TIRADO_POR_EL_FILTRO`. Es decir,
**de los 11 que tira, ninguno es crítico**. El rescate por criticidad (M19b,
ADR-128) es lo que lo garantiza, y es exactamente para lo que existe.

## Y lo que de verdad ordena el proyecto: el techo

Un filtro perfecto conserva exactamente lo esperado que le llega. Así que un
caso sería exacto **si y solo si la búsqueda le trae todo su
`resultado_esperado`**. Eso acota lo que se puede ganar mejorando el filtro,
sin tocar el motor:

| configuración de la búsqueda | hoy, sin filtro | **techo con filtro perfecto** | esperados que la búsqueda no trae |
|---|---|---|---|
| **petición declarada** | 17/47 | **44/47** | **3**, en 3 casos |
| petición fija (hoy) | 0/47 | **42/47** | 9, en 5 casos |
| la del laboratorio (grabación) | — | 42/47 | 11, en 5 casos |

Suelo de D1: **29/47**. Los tres techos lo superan, y el mejor por **quince
casos**.

**La búsqueda no es el problema.** Ya trae el conjunto esperado **completo** en
44 de los 47 casos. Los que faltan son tres elementos en tres casos:
`B04-CA-22`, `B04-CA-29` y `B04-CA-30`, uno en cada uno.

**Todo el hueco entre el `8/47` que se mide hoy y el suelo de `29/47` es
precisión.** Y la precisión, como ya dejó dicho la entrada 120 por otro camino,
solo la puede poner el filtro: el motor no distingue ruido de señal porque
ambos le entran por la misma puerta.

## Contraste con la predicción

| predicción (escrita antes de mirar) | resultado |
|---|---|
| el filtro conserva **>= 95%** de los esperados que entran | **FALLADA** — 84.3%, tira 11 de 70 |
| descarta entre el **50% y el 80%** del ruido | **ACERTADA** — 64.6% |

La fallada vuelve a ser la que enseña: si el filtro fuera tan seguro como
predije, «mejorar el filtro» sería subir su agresividad sin más. No lo es: ya
paga 11 esperados por 64 de ruido, y cualquier plan que lo haga más agresivo
tiene que mirar ese lado de la balanza.

## Dónde queda el mapa, y esta vez con un camino

| línea | estado |
|---|---|
| **el filtro de relevancia** | **la línea prioritaria, con 44/47 de techo y 32/47 alcanzado en la grabación** |
| intérprete / cardinalidad | en el ciclo, #653. Sube el techo de 42 a 44 y lo alcanzado de 0 a 17 |
| ranking del motor | cerrada — no separa (entrada 120) |
| siembra | cerrada — no es el problema (entrada 118) |

**Lo que este hallazgo NO dice.** No dice que el filtro pueda llegar a
perfecto: el techo es una cota, no un pronóstico. La grabación muestra un
filtro real en 84.3% de recuperación y 64.6% de rechazo, y no hay aquí
evidencia de cuánto de esa brecha es cerrable.

Y medir **una mejora** del filtro sigue exigiendo Ollama, porque hay que correr
el adaptador de verdad. Lo que ya no hace falta es Ollama para saber **dónde
está el techo**, ni para caracterizar el filtro que hay.
