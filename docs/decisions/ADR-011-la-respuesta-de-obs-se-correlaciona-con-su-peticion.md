# ADR-011 — Correlacionar cada respuesta de OBS con su petición, en vez de desconectar ante un plazo agotado

- Estado: PROPUESTO
- Fecha: 2026-08-14
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario

## Contexto y problema

FINDING-001 de AUDITOR-V0-RUN-001 (incidencia #154), sostenido por un
verificador independiente que reprodujo el fallo: **un plazo agotado deja a
Sirius afirmando que no está grabando mientras OBS sigue grabando.**

El mecanismo, verificado línea a línea:

1. `_request()` envía todas las peticiones con el mismo identificador
   (`_REQUEST_ID = "sirius"`, constante) y acepta como propia la primera
   respuesta `op=7` que llegue, sin comprobar de quién es
   (`obs_websocket.py:189-215`).
2. Cuando una petición no obtiene respuesta a tiempo, `TimeoutWebSocketError`
   sale hacia arriba y las seis ramas TIMEOUT del adaptador devuelven el error
   **sin desconectar** —a diferencia de las ramas `WebSocketError`, que sí
   desconectan—. El búfer del cliente queda intacto
   (`websocket_client.py:213-241`).
3. La respuesta atrasada sigue encolada. La siguiente petición la lee y la toma
   por suya. A partir de ahí las respuestas van desplazadas una posición, para
   siempre, sin que nada lo detecte.
4. La respuesta de `StopRecord` no lleva `outputActive`, así que
   `_grabando({})` es `False` y el estado se reconstruye como `PREPARADO`.

La reconciliación que #127 exige no rescata nada: `refresh_status()` solo
reconecta `if not self._backend.is_connected()`, y `is_connected()` sigue
siendo `True` porque el timeout no desconectó.

Consecuencia observada en la reproducción: Sirius dice en voz alta «No, no
estoy grabando», el indicador rojo se apaga, y al volver a pulsar parar
`StudioCaptureUseCase.stop_recording` corta en el estado falso y **no envía
`StopRecord`** — el botón de parar queda inerte mientras la cámara graba.

Esto contradice dos afirmaciones vigentes: `studio_capture.py:7-12` («el estado
lo dice el backend… si la confirmación no llega, el estado es INCIERTO y se
pide reconciliación, jamás se supone éxito») y ADR-009, que declara «Estado de
grabación inventado → **Imposible** por diseño del puerto».

El verificador encontró además un **segundo disparador de la misma raíz que no
necesita ningún plazo agotado**: `_MAXIMUM_HANDSHAKE_MESSAGES = 8` acota
cuántos mensajes lee `_request`, así que un OBS que emita nueve eventos entre
la petición y su respuesta produce exactamente el mismo desfase.

## Criterio de parada (escrito ANTES de decidir)

Si el arreglo no puede demostrarse con una prueba que **falle con el código
actual y pase con el nuevo**, no se entrega. Y si al escribirlo aparece que el
desfase puede ocurrir por una tercera vía distinta de las dos conocidas, se
para y se revisa el enfoque entero en vez de añadir un tercer parche: dos
disparadores de la misma familia ya son la señal de la regla de las dos rondas.

## Opciones consideradas

1. **Desconectar cuando se agota el plazo**, para que la siguiente llamada
   reconecte con un socket limpio.
2. **Correlacionar petición y respuesta** por un identificador único, y
   descartar toda respuesta que no sea la esperada.
3. Drenar el socket tras un plazo agotado, leyendo hasta vaciarlo.

## Decisión

**Opción 2.** Cada petición lleva un identificador único y creciente
(`sirius-1`, `sirius-2`, …) y `_request()` **ignora toda respuesta cuyo
`requestId` no coincida** con el de la petición en curso.

La pregunta que decide es la del método: *¿qué haría el fallo imposible en vez
de improbable?* Consumir la respuesta de otro deja de ser posible, porque una
respuesta ajena ya no puede identificarse como propia. Las dos vías conocidas
—plazo agotado y exceso de eventos— quedan cerradas por la misma comprobación,
y una hipotética tercera también: cualquiera que sea la razón por la que una
respuesta se quede encolada, la siguiente petición la descarta.

La opción 1 se descarta porque trata el síntoma y cobra un precio alto: OBS se
atasca por diseño —para eso existe `SETTLE_TIMEOUT_SECONDS`— y tirar la sesión
en cada atasco pasajero convertiría un tropiezo recuperable en una reconexión a
mitad de grabación. Además no cierra el segundo disparador, que no pasa por
ningún timeout.

La opción 3 se descarta porque «vaciar el socket» no tiene final definido: sin
correlación no se puede distinguir una respuesta atrasada de la que se está
esperando, y leer hasta que no llegue nada es exactamente el cuelgue que el
plazo existía para evitar.

Lo que **no** cambia: el timeout sigue devolviendo `TIMEOUT` y no desconecta; el
estado sigue saliendo del backend y sigue siendo INCIERTO cuando no se sabe.

## Comprobación que la sostiene

- Prueba nueva `test_una_peticion_que_se_rinde_no_desplaza_las_siguientes`, con
  un servidor de mentira que emite nueve eventos antes de responder: fuerza el
  desfase sin depender del reloj.
- **Mutación verificada en las dos direcciones**: con la comprobación de
  `requestId` retirada, la prueba falla y el estado observado es `PREPARADO`
  con el servidor grabando; con la comprobación puesta, pasa y el estado es
  `GRABANDO`.
- El servidor de mentira pasa a **devolver el `requestId` que recibe**, como
  hace OBS real, en vez de escribir `"sirius"` fijo. Un doble que no distingue
  identificadores no puede exhibir este defecto: esa era la razón por la que 21
  pruebas de integración convivían con él.

## Consecuencias

- Una respuesta atrasada ya no puede confundirse con la siguiente. Si se
  acumulan tantas que agotan el presupuesto de mensajes, el resultado es un
  `TIMEOUT` honesto —fallo seguro—, nunca un estado falso.
- El identificador es un contador por instancia del adaptador: determinista,
  reproducible en pruebas y sin dependencia del reloj ni del azar.
- Queda sin cerrar, y se dice: no se ha observado contra OBS Studio real ni en
  Windows. La reproducción usa el mismo tipo de servidor de mentira que el
  resto de pruebas del repositorio, y la advertencia de `obs_websocket.py`
  sobre lo que la verificación real no cubrió sigue vigente.

## Alternativas descartadas y por qué

Ver §Opciones: desconectar ante el plazo agotado (síntoma, precio alto, no
cierra el segundo disparador) y drenar el socket (sin criterio de final sin
correlación previa).
