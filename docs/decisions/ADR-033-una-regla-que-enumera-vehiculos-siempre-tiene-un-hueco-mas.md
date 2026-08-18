# ADR-033 — Una regla que enumera vehículos siempre tiene un hueco más: enunciar la propiedad

- Estado: PROPUESTO
- Fecha: 2026-08-18
- Aprobación: la fusión de la PR de esta rama por el propietario.
- Revisa la forma —no el fondo— de las reglas de [ADR-021](ADR-021-el-corrector-no-espera-nada-en-segundo-plano.md),
  [ADR-022](ADR-022-el-revisor-escribe-antes-de-revisar-no-espera-y-usa-el-entorno-que-hay.md) y
  [ADR-024](ADR-024-ninguna-regla-de-rol-puede-faltar-en-un-prompt.md).

## Contexto y problema

La ronda de corrección de A3 (incidencia #193, run 32166867844) murió sin sustituir su veredicto
provisional. Los números descartan las causas fáciles: el paso terminó en **`success`**, 9,5
minutos, **72 turnos de 120**, `terminal_reason: completed`. Ni turnos, ni tiempo, ni permisos.

El último mensaje del modelo, literal:

> «Sigo esperando la notificación del **Monitor** con el resultado de `pytest`. No emitiré más […]»

Es la **cuarta** vez, en los tres roles, y las cuatro con `terminal_reason: completed`:

| ronda | rol | run | mecanismo usado para esperar |
|---|---|---|---|
| #177 | corrector | 31953500564 | `pytest` en segundo plano |
| #180 | revisor | 31963233730 | tres subagentes en segundo plano |
| #182 | implementador | 31985897583 | `pytest` en segundo plano |
| **#193** | **corrector** | **32166867844** | **la herramienta Monitor** |

**Y esta vez la regla ya existía.** ADR-021 y ADR-022 la habían escrito, ADR-024 la había extendido
a los tres roles, y una prueba que recorre el directorio de prompts la vigilaba. No falló por
ausencia.

Falló por **redacción**. La regla decía:

> «Nada de lanzar `pytest` (ni ningún comando largo) en segundo plano»
> «No lances subagentes en segundo plano»

Eso es una **lista de vehículos**. El modelo usó un tercero que la lista no nombraba. Hizo
exactamente lo prohibido **sin incumplir ninguna frase**, y un lector honesto que solo tuviera esas
dos viñetas delante podría defender que una notificación no es «un comando largo» ni «un
subagente».

La prueba que la vigilaba tenía el mismo defecto de forma: comprobaba que aparecieran las palabras
de la lista (`segundo plano`, `No lances subagentes en segundo plano`), así que habría dado por
buena cualquier regla esquivable con el siguiente mecanismo que se inventara.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la nota de arranque
([#196](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/196)), antes del primer
commit. Alcance: la sección anti-espera de los tres prompts, la prueba que la vigila y este ADR.
**La regla nueva no puede ser otra lista**: si al escribirla acabo enumerando mecanismos como
definición, me he equivocado otra vez. **La prueba tiene que exigir la propiedad, no las palabras
de la lista.** Verificación por mutación incluyendo una que quite la propiedad y deje solo la
lista: debe fallar.

## Opciones consideradas

1. **Añadir «ni notificaciones» a la lista**: descartada, y es la reacción automática. Sería el
   cuarto parche de la misma familia y dejaría el hueco número cinco abierto. Es literalmente lo
   que la regla de las dos rondas de ADR-001 prohíbe: seguir parcheando síntomas.
2. **Prohibir por completo las herramientas que puedan esperar**: descartada. No se puede
   enumerar tampoco lo que hay que prohibir, y algunas son útiles usadas dentro del turno.
3. **Hacerlo imposible desde el workflow** —detectar que el veredicto sigue siendo el provisional
   y reintentar—: es la solución de mecanismo, y **es mejor que esta**. Pero cambia
   `sirius_apply_verdict.sh` y la máquina de estados, merece su propia decisión, y mezclarla aquí
   haría imposible saber cuál de las dos funcionó. **Queda registrada como pendiente.**
4. **Enunciar la propiedad y degradar la lista a ejemplos no exhaustivos**: elegida.

## Decisión

1. **La sección anti-espera de los tres prompts empieza por la propiedad**: cuando el turno
   termina, no puede quedar nada pendiente de llegar. **Da igual el mecanismo.** Si el siguiente
   paso depende de algo que tiene que venir de fuera, ese algo no va a llegar.
2. **Los ejemplos van después y se declaran explícitamente no exhaustivos**: «No son la lista
   completa y no lo serán nunca; si encuentras un mecanismo que no está nombrado aquí y te permite
   esperar, la regla lo prohíbe igual».
3. **El orden es parte de la decisión**, no estilo: lo que se lee primero es lo que se toma por la
   regla. La propiedad precede a los ejemplos, y la prueba lo comprueba por posición.
4. **El criterio de juicio queda escrito**: lo que se juzga no es qué herramienta se usó, sino si
   al terminar quedaba algo por llegar.
5. **Regla general que este caso deja escrita**: *cuando una prohibición se formula como lista de
   mecanismos, la lista es la superficie de escape*. Se enuncia la propiedad; los mecanismos son
   ilustración.

## Comprobación que la sostiene

- **Prueba por mutación (ADR-001 §3)**:

  | Mutación | Resultado |
  |---|---|
  | quitar la propiedad y dejar solo la lista (**la redacción vigente esta mañana**) | **fallan los 3 roles** |
  | quitar solo la frase de no-exhaustividad | **fallan los 3 roles** |
  | mover la propiedad detrás de la lista | **falla** ese rol |

  La primera es la que da sentido a todo: **el texto que teníamos antes de esta PR ya no pasa la
  prueba**. Si hubiera pasado, la prueba no estaría midiendo nada nuevo.
- Diagnóstico tomado del log del run 32166867844: `success`, 572 683 ms, 72 turnos de 120,
  `terminal_reason: completed`, y la cita literal del último mensaje.
- Suite completa: **2550 pasan, 3 se saltan**.

## Consecuencias

- Un mecanismo de espera nuevo —el quinto, el sexto— ya no tiene amparo literal: la regla no
  depende de nombrarlo.
- **Lo que esto NO garantiza, y hay que decirlo claro**: un prompt pide, no impide. Esta decisión
  cierra el hueco por el que se coló esta vez y le quita la excusa a la siguiente, pero **no puede
  hacer imposible** que un modelo termine el turno esperando algo. Lo único que lo haría imposible
  es un mecanismo, y ese mecanismo está identificado (opción 3) y **no implementado aquí**.
- **Lo que sí funcionó y se queda intacto**: el veredicto provisional de ADR-022 convirtió esta
  ronda perdida en un `FAILED_SAFELY` honesto en lugar de un `sin-veredicto` mudo. Es la primera
  vez que ese mecanismo se dispara en producción, y es la razón de que exista este diagnóstico.
- La ronda de corrección de A3 se perdió; la implementación de A3 (PR #194) sigue intacta con sus
  cinco hallazgos pendientes.

## Alternativas descartadas y por qué

Las cuatro de arriba. La 1 merece constar por lo tentadora que era: añadir «ni notificaciones» a
la lista habría cerrado este caso concreto en dos minutos, habría parecido un arreglo, y habría
dejado el sistema exactamente igual de frágil ante el siguiente mecanismo.
