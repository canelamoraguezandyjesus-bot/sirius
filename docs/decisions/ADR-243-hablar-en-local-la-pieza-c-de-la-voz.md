# ADR-243 — Hablar en local: la pieza C de la voz

- Estado: APROBADO
- Fecha: 2026-10-15
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). La pieza y su orden los aprobó el
  propietario con el plan (ADR-232) y con la tabla de piezas de ADR-241; el 14-10-2026
  pidió seguir con el código de la 0.3 («ahora tendrás que hacer el código, digo yo»).

Este ADR es además la **nota de arranque** de la rama
`claude/la-0-3-pieza-c-hablar-en-local` (skill `disciplina-evidencia`): las cuatro
preguntas, el criterio de parada y el alcance de la revisión están escritos antes del
primer cambio de código de la pieza y antes de cualquier revisión.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** Desde la pieza B (ADR-242) Sirius
   oye en local y lo oído entra en la charla, pero nadie lo dice: el turno acaba en lo
   escrito. Las seis pruebas de la pieza C (`tests/acceptance/test_robot_0_3_voz.py`,
   marcadas `@pieza("C", ...)`) esperan en `xfail` estricto. El arreglo va en el oído
   de la B y en piezas nuevas a su lado, sin tocar Model Studio: dos puertos, la voz
   (de texto a sonido) y el altavoz; un corte en frases que, mientras la charla
   escribe, saca las que ya están cerradas y las prepara para leerse con la misma
   función que Model Studio (`prepare_speech_text`), y el oído que las dice una a una
   desde la primera, con el micro cerrado mientras habla; y los adaptadores de verdad,
   Piper y `sounddevice`, detrás del extra `voz`. **¿Puede el sitio del arreglo
   observar el fallo?** El oído ve lo que miran las pruebas: qué se dice, cuándo
   empieza a decirse, con qué voz, y que su propia voz no abre un turno. No ve si
   Piper suena bien en su Windows ni cuánto tarda de verdad: en el contenedor no hay
   altavoz y huggingface.co está cerrado, así que no hay voz que cargar. Eso lo ven él,
   con `sirius-oye`, que ahora también habla, y E-R03-02.
2. **Qué NO garantiza.**
   - Que la voz le guste ni que suene bien. La elige él a ciegas en la pieza F; hasta
     entonces, una de las cuatro voces masculinas en español de España de ADR-241.
   - Que tarde menos de 1,5 s de verdad. PA-R03-09 mide lo que añade la tubería con
     dobles instantáneos; lo de verdad lo mide E-R03-02.
   - Que se le pueda cortar. Mientras habla no escucha: el micro está cerrado y lo que
     él diga entonces se pierde. Cortarle, con la cancelación de eco, es la pieza E.
   - Que lo que suena por el altavoz no vuelva por el micro cuando el micro se abre de
     nuevo: se abre cuando el altavoz dice que ha acabado; si un altavoz lo dijera antes
     de tiempo, la cola del eco entraría como un turno.
   - Que diga bien lo que escribe fuera de las marcas que conoce `prepare_speech_text`.
     Se usa la de Model Studio tal cual, sin cambiarla.
   - Lo que no trae la pieza C: la ventana (D) y cortarle (E).
3. **Criterio de parada**, fijado antes de ver ninguna prueba ni ninguna revisión:
   - **La pieza está terminada** cuando sus seis pruebas corren y pasan con el
     conductor de verdad, sin `xfail`; la tabla de `PRUEBAS_0.3_DEL_ROBOT.md` lo dice
     de PA-R03-02, PA-R03-03, PA-R03-08 y PA-R03-09 en lo que toca a la C; la batería
     entera y la cadena de comprobación están en verde; la revisión propia no encuentra
     nada; y hay una ronda limpia de Codex sobre el head de contenido con Quality en
     verde.
   - **Revisión propia antes de pedir otra**: quien implementa revisa, corrige y vuelve
     a revisar hasta que no hay nada, y solo entonces pide a Codex (regla del
     propietario del 13-10-2026). Dos rondas seguidas con hallazgos de la misma familia:
     se deja de parchear y se busca la raíz (ADR-001).
   - **Si Piper no se instala o no carga con Python 3.14 en el contenedor**, se para
     antes de escribir su adaptador. Comprobado el 15-10-2026: `piper-tts` 1.8.0
     resuelve con el extra (añade solo `pathvalidate`), se instala, importa en 3,57 s y
     pasa español a fonemas sin red con el espeak-ng que trae dentro.
   - **Después de fusionar**, en su ordenador: si `sirius-oye` no le habla, la pieza D
     no empieza hasta encontrar la raíz.
   - Si algo pide dinero o cambia el producto, se para y se le pregunta.
4. **Qué lo haría imposible.**
   - **Que la voz salga del ordenador.** Piper carga la voz solo desde su fichero; lo
     único suyo que baja algo, `download_voice`, lo llama solo la orden de instalar, y
     la guarda que recorre `src/` (`test_solo_la_orden_de_instalar_baja_modelos.py`)
     pasa a vigilarlo también. Los ajustes de la voz siguen sin texto libre: la voz es
     una elección cerrada de lo que baja esa orden.
   - **Que diga código o marcas.** Solo se dice lo que pasa por `prepare_speech_text`,
     y solo trozos cerrados: un bloque de código abierto, o un trozo que aún enseña
     marcas sin cerrar, espera a que se cierre o a que la charla acabe.
   - **Que se oiga a sí mismo y se conteste.** Desde la primera frase hasta que el
     altavoz acaba, el micro está cerrado: el eco se pierde, no se lee.
   - **Lo que no se puede hacer imposible:** que la voz suene natural y que tarde poco
     de verdad. Lo miden sus evaluaciones.

**Lo aprendido en las dieciséis rondas de la pieza B, aplicado desde el principio**
(ADR-242, «Revisión externa»):

- Lo que devuelve cada paso llega entero al siguiente: el turno sigue llevando el
  resultado de la charla, y lo que se dijo por el altavoz se cuenta desde lo que sonó,
  no desde lo que se quería decir.
- Lo que falla dentro de un turno no tumba a quien escucha: si la voz o el altavoz
  fallan, el oído deja de hablar, lo dice y sigue la charla escrita, que ya está
  guardada.
- La orden de instalar se aconseja solo para lo que ella toca, y dice la causa.
- El diario no se queda con nada de lo dicho ni de lo oído: solo tipos de fallo.
- La comprobación de que la charla se queda en este ordenador sigue donde se envía
  (ADR-242, rondas 9 y 10).

## Contexto y problema

ADR-241 dejó la 0.3 en seis piezas, con sus pruebas de aceptación escritas antes del
código, y la pieza B (ADR-242, PR #687, `2f15ee27`) trajo el oído. La pieza C es
«Hablar en local con Piper en español de España, frase a frase desde la primera; su
propia voz no se toma por suya». Sus seis pruebas son de PA-R03-02 (habla con una voz
de Piper en español de España, empieza con la primera frase antes de que el modelo
acabe y dice todo lo que escribió y nada más, sin marcas ni código), de PA-R03-03 (su
propia voz, de vuelta por el micro, no empieza un turno), de PA-R03-08 (oye y habla con
las herramientas locales del plan) y de PA-R03-09 (con todo instantáneo, la tubería
añade menos de 200 ms en el P95 de 20 turnos).

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

1. **Decir la respuesta cuando la charla acaba**, entera. Es lo más simple y lo que hace
   Model Studio, pero incumple PA-R03-02: la primera frase tiene que sonar antes de que
   el modelo acabe.
2. **Decirla frase a frase mientras la charla escribe**, con un corte que solo suelta
   trozos cerrados y los prepara con la función de Model Studio. Cumple PA-R03-02 sin
   cambiar `prepare_speech_text`.
3. **La tubería de salida de Pipecat** (su `PiperTTSService` y su transporte). Su
   transporte local es `pyaudio`, sin rueda para Python 3.14 en Windows (ADR-241), y la
   pieza B ya descartó su tubería entera (ADR-242, «Decisión»).

## Decisión

Se adopta la opción 2.

- **Dos puertos nuevos** en `src/sirius/ports/local_voice.py`: la voz, que convierte
  una frase en sonido con una voz con nombre, y el altavoz, que lo hace sonar y dice si
  sigue sonando. Van junto al micro, el detector y el transcriptor de la pieza B.
- **El corte en frases**: lo que la charla va escribiendo se acumula, y se suelta un
  trozo cuando acaba en un final de frase o de párrafo, fuera de un bloque de código, y
  preparado con `prepare_speech_text` ya no enseña marcas sin cerrar. Al acabar la
  charla se suelta lo que quede. Lo dicho, unido, es lo que da `prepare_speech_text`
  con la respuesta entera, salvo los blancos.
- **El oído habla**: entrega cada turno a la charla con un `on_delta` que alimenta el
  corte; cada trozo se pide a la voz y suena por el altavoz en cuanto está cerrado. Al
  empezar a hablar cierra el micro, y lo vuelve a abrir cuando el altavoz ha acabado,
  con el detector y lo de antes del turno vaciados.
- **La voz de verdad**: Piper, con una de las voces de ADR-241, en español de España,
  cargada solo desde la carpeta de los modelos de la voz. Los ajustes ganan la voz como
  elección cerrada; la orden de instalar la baja y la instalación la mira, como el
  modelo de oír.
- **El altavoz de verdad**: `sounddevice`, como el micro de la pieza B.
- **`sirius-oye`** dice las respuestas por el altavoz, además de escribirlas.
- **Con qué oye y habla**, para PA-R03-08, se lee de los módulos que importan los
  cargadores de producción, no de una constante.

## Comprobación que la sostiene

Se completa al cerrar la pieza.

## Consecuencias

Se completa al cerrar la pieza.

## Alternativas descartadas y por qué

- **Decirla entera al acabar** (opción 1): incumple PA-R03-02.
- **La tubería de salida de Pipecat** (opción 3): su transporte no tiene rueda para
  Python 3.14 en Windows, y la pieza B ya decidió el bucle propio.

## La lección

- ninguna: al arrancar, la pieza C no ha encontrado todavía ningún error que otro pudiera repetir; si lo encuentra, se escribe aquí al cerrarla.

## Revisión externa

Alcance, escrito antes de la primera petición: esta PR trae la pieza C y nada más. Mira
que diga lo que escribió desde la primera frase, con una voz de Piper en español de
España, sin marcas ni código; que su propia voz no abra un turno; que nada salga del
ordenador ni se baje solo; que lo que falle al hablar no tumbe a quien escucha; y que
`sirius-oye` hable. No trae la ventana ni a quién le hablan (D), ni cortarle (E).
