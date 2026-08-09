# SIRIUS · MODEL STUDIO · MÓDULO CAPTURA

## CÓMO EMPEZAR A PROBAR, SIN COMPRAR NADA

**Documento:** SIRIUS-MODEL-STUDIO-CAP-INV-002
**Versión:** 1.0
**Estado:** guía práctica de la ventana de verificación manual
**Fecha:** 7 de agosto de 2026
**Acompaña a:** `SIRIUS_MODEL_STUDIO_CAPTURA_INVESTIGACION.md`, que define las doce comprobaciones V-01 a V-12

> **De dónde sale esto y qué le falta**
>
> El entorno donde se redactó no tiene internet, ni Windows, ni OBS, así que
> aquí no se cita ninguna versión, ningún precio y ningún nombre de menú
> verbatim: se describe **qué buscar**, no dónde estará exactamente. Los nombres
> reales pueden variar según la versión instalada.
>
> Esta guía no demuestra nada por sí sola. Es el guion de la ventana de prueba
> manual que #127 exige antes de dar por buena la captura.

## La idea que ahorra dinero

Las seis primeras comprobaciones —conectar, autenticarse, preguntar el estado,
grabar, parar y cambiar de escena— **se hacen con la pantalla del ordenador
como única fuente**. No hace falta ninguna cámara.

Eso significa que se puede saber si todo el planteamiento funciona antes de
conectar nada y mucho antes de comprar nada. Y si falla la comprobación V-03
—que OBS diga la verdad sobre si está grabando— el planteamiento se cae entero
y no se habrá gastado un euro.

## Fase 0 · Hoy mismo, sin conectar nada

**Qué hace falta:** el ordenador y una descarga gratuita. Nada más.

1. **Instalar OBS Studio.** Es gratuito y de código abierto. Descargarlo solo
   de su web oficial.
2. **Activar el servidor local.** En los ajustes de OBS hay una sección de
   herramientas o de complementos con un servidor WebSocket. Hay que activarlo
   y ponerle contraseña. Anotar el **puerto** y la **contraseña**: son los dos
   datos que Sirius necesita. → cubre **V-01**.
3. **Crear dos escenas** que, de momento, sean las dos capturas de la pantalla:
   - `Pantalla` — el escritorio entero.
   - `Solo Sirius` — únicamente la ventana de Sirius.

   Con dos escenas ya se puede probar el cambio de plano, aunque las dos
   enseñen lo mismo. Lo que se está probando es el mecanismo, no la estética.
4. **Grabar treinta segundos a mano**, desde el propio OBS, y comprobar que
   aparece un archivo y se puede reproducir. Si esto falla, el problema es de
   OBS y no tiene nada que ver con Sirius.

Con la fase 0 hecha se pueden ejecutar **V-01 a V-06**. Ahí sabremos si OBS
sirve.

## Fase 1 · El móvil como segunda cámara

**Qué hace falta:** el móvil que ya se tiene y, como mucho, su cable.

Un móvil moderno hace de cámara mucho mejor que una webcam barata, así que es
el sitio por el que empezar. Hay tres caminos, de más a menos recomendable:

1. **Por cable, con lo que traiga el sistema.** Los sistemas operativos y los
   móviles recientes suelen permitir usar el teléfono como cámara conectándolo
   por USB, sin instalar nada. Es lo más estable y lo que menos retraso mete.
   Conviene mirar primero si el móvil concreto lo admite.

   > **Con iPhone y Windows.** La función que trae el propio iPhone para hacer
   > de cámara está pensada para ordenadores Apple, así que con Windows hará
   > falta una aplicación de terceros. Antes de instalar nada conviene
   > comprobar si la marca del ordenador o el propio Windows ya ofrecen algo, y
   > probar siempre por cable antes que por Wi-Fi.
2. **Con una aplicación de cámara por USB.** Existen aplicaciones que convierten
   el móvil en webcam por cable. Las hay gratuitas con marca de agua y de pago
   sin ella. Por cable siempre; ver el punto siguiente.
3. **Por Wi-Fi, solo si no queda otra.** Funciona, pero mete retraso y se corta
   cuando la red va justa. Para grabar un montaje con las manos ocupadas, un
   corte a mitad es muy molesto. Si se usa, que sea con la red de casa y nunca
   abierta a internet.

**Qué comprobar cuando el móvil ya se vea en OBS:**

- Que la imagen no llegue con retraso perceptible respecto al sonido.
- Que se pueda crear una escena `Cámara cenital` con el móvil apuntando a la
  protoboard desde arriba.
- Que se pueda alternar entre `Pantalla` y `Cámara cenital` sin que la
  grabación se corte. → cubre **V-07**.

**Truco para el montaje del Arduino:** el plano que de verdad se necesita es el
cenital, mirando la protoboard desde arriba. Cualquier soporte que sujete el
móvil boca abajo sobre la mesa sirve, incluidos los caseros. No hace falta
material de vídeo.

## Fase 2 · Solo si algo de lo anterior falla

Aquí sí puede aparecer una compra, y solo entonces. **No antes.**

| Si falla | Lo que probablemente haga falta | Cuándo decidirlo |
|---|---|---|
| El móvil no se puede usar por cable | Un cable de datos en condiciones, o una aplicación de pago sin marca de agua | Tras la fase 1 |
| El móvil por Wi-Fi se corta | Nada que comprar: pasar a cable | Tras la fase 1 |
| Hace falta un tercer plano | Una webcam corriente | Tras grabar de verdad y notar que falta |
| El ordenador se atasca al grabar | Bajar resolución o fotogramas antes de comprar nada | Tras **V-10** |

**Ninguna compra está justificada hasta terminar la fase 1.** El único gasto
que podría aparecer pronto es un soporte para el móvil, y sirve cualquiera.

## Lo mínimo para la primera grabación de HEAD-R1

Para cumplir la aceptación de #127 hacen falta dos ángulos físicos y la
pantalla. Pero para **la primera grabación útil** basta con:

- `Pantalla` — Sirius contestando.
- `Cenital` — el móvil mirando la protoboard.

Con esas dos escenas ya se puede grabar el montaje entero alternando entre lo
que se hace con las manos y lo que Sirius responde, que es exactamente el
objetivo. El segundo ángulo físico se añade después, cuando haga falta.

## Qué pasa cuando Sirius entre en escena

Terminada la fase 0, en Sirius hay que introducir dos datos: **puerto** y
**contraseña** del servidor de OBS. A partir de ahí, Sirius se conecta y
pregunta el estado; no supone nada.

### Cómo se hace, en un comando

```
python -m sirius.capture_setup
```

Pregunta el puerto y la contraseña —la contraseña no se ve al teclearla ni
aparece impresa en ninguna línea—, se conecta y hace por sí solo lo que esta
guía plantea a mano:

1. Se conecta y autentica (V-01, V-02).
2. Lee las escenas que existen en OBS y **escribe la lista blanca**, con un
   identificador estable por escena y los alias con los que se la puede llamar
   hablando. Un alias que valdría para dos escenas se descarta de las dos:
   ante una orden ambigua el registro no elige ninguna, así que dejarlo escrito
   sería configurar una orden que nunca funcionaría.
3. Cambia de plano y vuelve al que estaba (V-05).
4. **Graba tres segundos de verdad** y dice dónde quedó el archivo (V-03, V-04).
5. Termina enseñando las frases exactas que ya se pueden decir en voz alta.

Se puede repetir tantas veces como haga falta: cada ejecución vuelve a leer las
escenas de OBS y reescribe la lista. Es lo que hay que hacer después de crear,
renombrar o borrar una escena.

Si OBS ya está grabando cuando se lanza, **no toca esa grabación**: lo dice y
se detiene. Una prueba no puede llevarse por delante una toma real.

Conviene tener presentes tres comportamientos que están construidos a propósito:

- **Si OBS está cerrado, Sirius lo dice y sigue funcionando.** La conversación
  escrita y la voz no se enteran de que la captura no está.
- **Sirius no dice «grabando» hasta que OBS se lo confirma.** Mientras la orden
  va en camino dirá «iniciando». Si no llega respuesta, dirá que no lo sabe y
  volverá a preguntar. Es deliberado: es lo que evita hablar veinte minutos
  creyendo que se estaba grabando.
- **Una escena que no esté en la lista autorizada no cambia el plano.** Aunque
  exista en OBS. Y no se busca la más parecida.

## Orden recomendado

1. Fase 0 completa, con las seis primeras comprobaciones. **Sin gastar nada.**
2. Si V-03 falla, parar: hay que replantear el backend antes de seguir.
3. Fase 1 con el móvil.
4. Conectar Sirius y repetir las mismas órdenes desde la interfaz.
5. Grabación real de HEAD-R1 con tres cambios de escena y una marca (MS-018).

## Lo que esta guía no cubre

- Nombres exactos de menús, versiones y precios: no se han podido comprobar.
- Recomendación de una aplicación de cámara concreta: exige probarla en el
  móvil real.
- Iluminación, sonido ambiente, encuadre y montaje.
- Publicación o subida, fuera de alcance por decisión de #127.
