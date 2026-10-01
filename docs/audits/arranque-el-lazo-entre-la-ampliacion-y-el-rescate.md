# Nota de arranque — El lazo entre la ampliación por criticidad y el rescate

Escrita **antes de medir**, 20-09-2026, 18:55 UTC. ADR-001.

## Por qué

La entrada 134 dejó que el techo de todo el sistema son ~32-34/47 y que lo fija
el rescate RF-25. La conclusión que saqué —«si el objetivo está por encima, la
conversación es sobre el candado»— **da por supuesto que la única salida es
proteger menos**. Antes de dejarle esa decisión al propietario hay que
comprobar si la hay mejor.

Porque leyendo el motor aparece un segundo paso que no miré:
`rank_relevant_knowledge.py:550-600`. Cuando el texto de la consulta activa el
**vocabulario de criticidad**, el motor mete `solo_por_criticidad`: **todas** las
identidades no ordinarias del ámbito, una por una, marcadas
`fts_match=False`, `subject_matches_query=False`, `criticality_match=True`. No
las trae porque respondan: las trae porque son críticas y la pregunta sonó a
crítica.

Y después RF-25 **las protege del filtro**. Los dos mecanismos juntos forman un
lazo:

> el motor **inyecta** toda protegida del ámbito → el filtro intenta tirar las
> que no responden → el rescate **las devuelve todas**.

El filtro no puede deshacer el paso 1 por construcción. Si el ruido forzado
viene de ahí, el problema no es cuánto se protege: es **qué se inyecta**.

## Las cuatro preguntas

1. Con la ampliación por criticidad **apagada**, ¿cuál es el techo real (con
   RF-25 puesto igual) de `--peticion` y `--ejes --peticion`?
2. ¿Cuántos casos deja de bloquear el rescate?
3. ¿Cuánto **cuesta**: en cuántos casos se pierde algo esperado que hoy solo
   entra por esa ampliación?
4. ¿Los casos bloqueados son sobre todo los de «restricciones esenciales», o
   están repartidos?

## Criterio de parada

- Si apagarla sube el techo real **>= 5 casos** **y** pierde esperado en **<= 3**:
  existe una palanca que **no toca el nivel de protección**, y se escribe como
  decisión para el propietario, mejor fundada que la deuda 42.
- Si lo sube **< 3 casos** o pierde esperado en **>= 5**: la ampliación es
  portante, la deuda 42 es la única salida y se registra el negativo.
- En medio: se publican los dos números y se dice que no hay veredicto.

**Regla dura**: esto **mide**, no cambia nada. La ampliación se apaga por parche
en la medición y se restaura. No se toca el corpus, ni el fixture, ni
`resultado_esperado`. No se lee `criticidad.razon_segura`. Y no se propone nada
que pierda una crítica sin contar cuántas.

## Predicción, escrita antes de medir

1. **La mayor parte del ruido forzado viene de la ampliación.** Apagarla sube el
   techo real de `--peticion` de 32/47 a **>= 40/47**. Razón: `CA-44` se lleva
   ocho identidades forzadas de golpe (`MEM-001`, `MEM-106`…`MEM-112`), que es
   exactamente la forma de «me han metido el bloque entero», no la de «la
   búsqueda encontró ocho cosas parecidas». Le doy un **70%**.
2. **Cuesta poco**: pierde esperado en **<= 3** casos. Razón: la entrada 120 ya
   midió que las críticas que el laboratorio pierde son todas por `NO_ENTRO`,
   ninguna por el filtro; si la ampliación fuera la que las trae, ese número
   sería otro. Le doy un **55%** — es la que menos me fío.
3. **Los bloqueados son los de «restricciones esenciales»**: `CA-02`, `CA-25`,
   `CA-26`, `CA-31`, `CA-33`, `CA-34`, `CA-44`. Le doy un **80%**.

**Si acierto la 1 y la 2**, la entrada 134 se queda a medias: el techo no lo fija
«el candado» sino **el lazo**, y hay una salida que no pide aflojar la seguridad.
**Si fallo la 2** —si la ampliación sí trae esperado que nadie más trae—, el lazo
es el precio de no perder críticas y la deuda 42 se queda como está.
