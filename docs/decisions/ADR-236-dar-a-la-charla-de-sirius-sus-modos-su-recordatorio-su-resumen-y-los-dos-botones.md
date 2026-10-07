# ADR-236 — Dar a la charla de Sirius sus modos, su recordatorio, su resumen y los dos botones

- Estado: APROBADO
- Fecha: 2026-10-07
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Es la pieza D de ADR-233; lo que hace
  sale de los pasos 4, 5 y 6 de la personalidad en la 0.2 del plan del robot, aprobado por
  el propietario el 06-10-2026.

## Nota de arranque

Escrita antes del primer commit de la rama que lleva la pieza D. El criterio de parada de
las rondas es el de ADR-233.

1. **Dónde vive el fallo y dónde va el arreglo.** Sirius no tenía modos, no recordaba la
   semilla al final de cada turno, no resumía las charlas largas y no dejaba marcar sus
   respuestas. Todo va en el camino de cada mensaje, `SendMessageUseCase.send_message`,
   que es lo que llaman la ventana y el conductor de las pruebas. Lo observan PA-R02-04,
   PA-R02-05 y PA-R02-06, que miran lo que recibe el modelo y lo que queda en la base.
2. **Qué NO garantiza.** Que el modelo obedezca el modo serio o el recordatorio: eso lo
   miden E-R02-02 y el juez de la pieza E. Que las órdenes se reconozcan dichas de
   cualquier manera: se reconocen por reglas, y lo que no encaje no cambia el modo, que
   siempre se puede quitar con el botón.
3. **Criterio de parada.** El de ADR-233.
4. **Qué lo haría imposible.** Que el modo serio se olvide a mitad de charla: no depende de
   que el modelo se acuerde, está guardado y se añade en cada turno hasta que se suelta.
   Que se le entrene por «me gusta»: esa marca no existe.

## Contexto y problema

El paso 4 pide que «ponte serio» le cambie de modo, que vacile al entrar y luego vaya al
grano, y que «para» corte el pique. El paso 5, dos botones en cada respuesta. El paso 6,
recordarle la semilla en cada turno y resumir la charla larga cada 15 a 20 turnos, porque
sin eso se desdibuja a las ocho rondas.

## Opciones consideradas

1. **Que el modelo entienda las órdenes solo**, con la semilla que ya las explica. Un
   modelo pequeño no se acuerda diez turnos después de que le pidieron estar serio.
2. **Órdenes por reglas y el modo guardado por conversación**, añadido a las
   instrucciones mientras dura.
3. **Resumir en otro hilo, cuando el ordenador esté libre.** Es lo que hará el «sueño» de
   la pieza G con los hechos; para la charla viva, el resumen tiene que estar antes del
   turno siguiente.

## Decisión

Se adopta la opción 2, y el resumen se hace al acabar el turno que lo dispara.

- **Los modos**, en `src/sirius/domain/conversation_mode.py`:
  - «ponte serio» en cualquier sitio del mensaje.
  - «para» solo al empezar el mensaje y seguido de nada, de una coma o un signo, de «ya»
    o de «de». «Para mañana…» no es una orden.
  - «volver a ser tú» suelta el modo, y gana si el mismo mensaje pide las dos cosas.
  - Valen desde ese mismo turno. El vacile, «vale, jefe», solo en el turno en que entra
    el modo serio.
  - El modo se guarda por conversación en la tabla nueva `conversation_modes`. La ventana
    lo enseña, «Modo serio» o «Sin pique», con un botón para quitarlo.
- **El recordatorio**: `ROBOT_SEED_REMINDER` es lo último de cada petición, también
  detrás de lo que añade Model Studio al grabar.
- **El resumen**, en `src/sirius/domain/conversation_summary.py`:
  - Con 18 turnos sin resumir, dentro de los 15 a 20 del plan, se resume todo menos los
    cuatro últimos.
  - Lo resume el mismo modelo que conversa, así que la charla no sale del ordenador.
  - El resumen sustituye en las peticiones a los mensajes que cubre, que siguen guardados
    en la tabla `conversation_summaries`. Lo usa el constructor del contexto.
  - Si resumir falla, la charla sigue y se intenta en el turno siguiente.
- **Los dos botones**:
  - «Eso es Sirius» y «Eso no» en cada respuesta completa. Marcar otra vez cambia la
    marca.
  - Cada respuesta apunta al darla con qué modelo se dio, en la tabla `reply_marks`, para
    que las marcas sirvan después para entrenarle.
  - La cuenta de las últimas 50 marcadas la da `MarkReplyUseCase.count`.
- **Tres tablas nuevas y ninguna columna nueva** en las de siempre, con su migración
  `7a3e9c2d4b10`. Todo lo nuevo es opcional en `SendMessageUseCase` y `ContextBuilder`:
  sin ello, hacen lo de antes.

## Comprobación que la sostiene

- PA-R02-04, PA-R02-05 y PA-R02-06 en verde: sus nueve pruebas de aceptación, dos de
  ellas sobre la ventana de verdad.
- Vistas fallar con el código estropeado a propósito:
  - Con el modo sin guardar, fallan «ponte serio» y «para».
  - Sin el recordatorio, falla el de la charla de 40 turnos.
  - Sin resumir nunca, falla el del resumen.
  - Sin sacar lo resumido de los mensajes recientes, falla una prueba nueva de
    integración. La de aceptación no lo veía, porque con 25 turnos lo viejo ya se sale
    de la ventana de 20 mensajes.
  - Con una marca que no cambia al volver a pulsar, falla la de las marcas.
- Unitarias: 21 de las órdenes de modo, 4 del cuándo resumir, 12 de integración sobre
  SQLite y el camino de cada mensaje, y 3 de los botones.

## Consecuencias

- La ventana enseña los dos botones en cada respuesta y el modo cuando no es el normal.
- Las marcas empiezan a juntarse para E-R02-02 y para entrenarle en 0.5.

## Alternativas descartadas y por qué

- **Una columna `mode` en `conversations` y `model` en `messages`.** Habría obligado a
  tocar el contrato del repositorio de conversación, que implementan ocho dobles de
  prueba, y la prueba que fija las columnas de esas tablas.

## La lección

- ninguna: el único hueco, que la prueba de aceptación no veía el resumen fuera de la
  ventana de mensajes, se cerró con una prueba de integración antes del primer commit de
  la rama.
