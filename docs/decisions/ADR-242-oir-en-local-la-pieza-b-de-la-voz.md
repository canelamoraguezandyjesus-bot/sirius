# ADR-242 — Oír en local: la pieza B de la voz

- Estado: APROBADO
- Fecha: 2026-10-14
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). La pieza y su orden los aprobó el
  propietario con el plan (ADR-232) y con la tabla de piezas de ADR-241; el 14-10-2026,
  fusionada la PR de las pruebas, pidió seguir con el código: «ahora tendrás que hacer
  el código, digo yo».

Este ADR es además la **nota de arranque** de la rama `claude/la-0-3-pieza-b-oir-en-local`
(skill `disciplina-evidencia`): las cuatro preguntas, el criterio de parada y el alcance
de la revisión están escritos antes del primer cambio de código de la pieza y antes de
cualquier revisión.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** Hoy Sirius no puede oír en local: la
   única voz es la de Model Studio, por OpenAI, por turnos y con un botón
   (`src/sirius/application/studio_voice.py`), y su puerto de captura lo dice en su
   contrato: «No existe escucha permanente ni palabra de activación»
   (`src/sirius/ports/audio_capture.py:9-10`). Las siete pruebas de la pieza B
   (`tests/acceptance/test_robot_0_3_voz.py`, marcadas `@pieza("B", ...)`) esperan en
   `xfail` estricto. El arreglo va en código nuevo, aparte de Model Studio, que no se
   toca: tres puertos (el micro, el detector de turno y el transcriptor), un servicio
   que lee el micro, pregunta al detector por cada trozo, transcribe el turno cuando el
   detector lo da por acabado y entrega el texto a la misma charla que la ventana
   (`send_message`), y los adaptadores de verdad detrás de un extra opcional. **¿Puede
   el sitio del arreglo observar el fallo?** El servicio sí ve lo que las pruebas
   miran: dónde acaba el turno, que lo oído entra por la misma charla, y que sin modelos
   no abre el micro ni contesta. No ve si el micro, Silero, Smart Turn y faster-whisper
   funcionan en su Windows: en el contenedor no hay micro, y eso solo lo ve él, con la
   orden de consola que trae esta pieza y con E-R03-01.
2. **Qué NO garantiza.**
   - Que los adaptadores de verdad funcionen en su Windows con Python 3.14. Aquí se
     instalan en Linux y se prueban sin micro; sus pruebas de máquina ponen módulos de
     mentira en lugar de las bibliotecas, y miran el cableado, no el sonido.
   - Que le entienda bien ni que acierte el final de cada turno. Lo miden sus
     evaluaciones, E-R03-04 sobre todo.
   - Que tarde poco. El oído va en el procesador (abajo); los 1,5 s se miden con la
     pieza C, en E-R03-02.
   - Lo que la pieza B no trae: hablar (C), la ventana con su indicador y su botón de
     silencio, y saber si le hablan a él (D), y cortarle (E). En la pieza B todo lo oído
     es para él.
   - Que `.\scripts\bootstrap.ps1` no quite la voz: hace `uv sync --all-groups`, que
     deja el entorno exacto y quita el extra. Entonces Sirius vuelve a decir qué orden
     ejecutar.
   - Que ninguna biblioteca escrita en C abra la red. El vigilante de las pruebas ve la
     red de Python; por eso lo que podría bajar algo se cierra por construcción (punto
     4), no se vigila.
   - Que un turno que nunca acaba no crezca en memoria. Smart Turn lo cierra a los 3 s
     de silencio; un ruido continuo sin pausas no tiene tope en esta pieza.
3. **Criterio de parada**, fijado antes de ver ninguna prueba ni ninguna revisión:
   - **La pieza está terminada** cuando sus siete pruebas corren y pasan con el
     conductor de verdad, sin `xfail`; PA-R03-01 dice «en verde» en la tabla; la
     batería entera y la cadena de comprobación están en verde; la revisión propia no
     encuentra nada; y hay una ronda limpia de Codex sobre el head de contenido con
     Quality en verde.
   - **Revisión propia antes de pedir otra**: quien implementa revisa, corrige y vuelve
     a revisar hasta que no hay nada, y solo entonces pide a Codex (regla del
     propietario del 13-10-2026). Dos rondas seguidas con hallazgos de la misma familia:
     se deja de parchear y se busca la raíz (ADR-001).
   - **Si las bibliotecas no se instalan o no cargan con Python 3.14** en el contenedor,
     se para antes de escribir los adaptadores y se busca otra pieza o un proceso
     aparte. Si el extra rompe `uv sync --locked --all-groups` de Quality, se para.
   - **Después de fusionar**, en su ordenador: si la orden de consola no le oye, la
     pieza C no empieza hasta encontrar la raíz (§10 del plan: «Pipecat en Windows. Se
     comprueba el primer día de 0.3»).
   - Si algo pide dinero o cambia el producto, se para y se le pregunta.
4. **Qué lo haría imposible.**
   - **Que el audio salga del ordenador.** Los ajustes de la voz del robot no tienen
     ningún campo de texto libre, así que no hay dónde poner un servidor, una dirección
     ni una clave; cada opción es una elección cerrada de lo instalado aquí. Lo mira
     PA-R03-08, y una prueba del conductor comprueba que esa lectura sí ve un campo de
     servidor cuando lo hay.
   - **Que Sirius baje un modelo por su cuenta.** faster-whisper baja el modelo si se le
     pide por nombre y no lo tiene, y si falta su `tokenizer.json` lo pide a internet
     desde Rust, donde el vigilante no llega. Por eso el oído carga el modelo solo desde
     una carpeta, con `local_files_only=True`, y no arranca si falta cualquiera de sus
     ficheros, `tokenizer.json` incluido. La única descarga vive en la orden de
     instalar, que ejecuta él; una prueba recorre `src/` y falla si cualquier otro
     módulo nombra una función que baje modelos.
   - **Que guarde audio.** Los trozos del turno viven en una lista en memoria que se
     vacía al cerrarlo, y el servicio no escribe en el diario nada de lo oído: «olvida
     eso» no podría borrarlo de ahí.
   - **Lo que no se puede hacer imposible:** que le entienda y que acierte el final del
     turno. Se hace improbable con los modelos del plan y lo miden sus evaluaciones.

## Contexto y problema

ADR-241 dejó la 0.3 en seis piezas y escritas, antes del código, sus pruebas de
aceptación; la PR #686 las fusionó el 14-10-2026 (`d72f20b4`). La pieza B es la
primera de código: «Oír en local: la tubería con Silero, Smart Turn y faster-whisper; lo
oído entra en la charla como un mensaje más; nada sale del ordenador; si falta un
modelo, dice qué orden ejecutar». Sus siete pruebas son de PA-R03-01 (lo dicho por voz
entra en la charla, por la misma semilla y la misma memoria que lo escrito, y el turno
acaba cuando el detector lo dice) y de PA-R03-08 (nada sale, solo puede ir a este
ordenador, y sin modelos dice la orden y no baja nada).

`docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md` deja a este ADR una decisión que ninguna
prueba mira: «Que la tubería sea de Pipecat. Es una decisión del plan («Con qué»), no un
comportamiento: lo dirá el ADR de la pieza B y lo verá su revisión».

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

1. **La tubería entera de Pipecat**: su `Pipeline` asíncrono con un transporte de audio
   propio (el suyo, `pyaudio`, no tiene rueda para Python 3.14 en Windows, ADR-241), su
   estrategia de fin de turno, faster-whisper como servicio de Pipecat y un procesador
   propio que llame a la charla de Sirius.
2. **Un bucle de Sirius con las piezas de Pipecat dentro**: Sirius lee el micro y, por
   cada trozo, pregunta a los analizadores de Pipecat, Silero y Smart Turn v3, con sus
   modelos ONNX de dentro del paquete y con el mismo orden en que los encadena la
   estrategia de fin de turno de Pipecat; al acabar el turno lo transcribe con
   faster-whisper y lo entrega a la charla.
3. **Sin Pipecat**: Silero y Smart Turn con `onnxruntime` a mano.

## Decisión

Se adopta la opción 2. Lo decide la sesión (ADR-204: no es dinero, ni salud, ni cambia
lo que el propietario ve u oye).

- **Por qué no la tubería entera.** De Pipecat solo quedaría la tubería: el transporte lo
  pone Sirius porque el suyo no se instala en Windows con Python 3.14, y el modelo de la
  charla también, porque la charla de Sirius ya monta la semilla, la memoria y los modos
  en cada turno. Lo que el plan pide de Pipecat, «saber cuándo ha terminado de hablar el
  propietario» sin programarlo desde cero, son sus dos analizadores, y se usan tal cual.
  Un `Pipeline` asíncrono en otro hilo, además, se coordina por tiempo, y los dobles de
  las pruebas no tienen tiempo: son instantáneos a propósito (ADR-241). Cuando entren
  hablar frase a frase (C) y cortarle (E), sus PR deciden con sus pruebas si el bucle
  basta o se pasa a la tubería; los puertos de esta pieza no cambian con eso.
- **El micro: `sounddevice`**, con PortAudio dentro de su rueda para Windows, a 16 kHz,
  mono, 16 bits y trozos de 512 muestras, que es lo que piden Silero y Smart Turn.
  ADR-241 dejaba a esta pieza elegir entre él y QtMultimedia midiendo los dos; desde la
  nube no se puede medir un micro, así que se elige `sounddevice` porque no necesita el
  bucle de eventos de Qt y la orden de consola puede usarlo sin ventana, y lo mide
  E-R03-01. Si allí falla, se cambia el adaptador del micro, no el resto.
- **El oído: faster-whisper `small`** en el procesador, con `int8` y en español. El plan
  ya decía que, si no cabe todo en sus 6 GB de gráfica, el oído y la voz van al
  procesador (§10); se empieza ahí porque en Windows la gráfica le pide a faster-whisper
  bibliotecas de CUDA que su rueda no trae. Si E-R03-02 dice que tarda demasiado, se
  mide en la gráfica con esas bibliotecas y se decide con la cifra.
- **Dónde viven los modelos.** En `modelos\voz`, dentro de la carpeta de datos de
  Sirius de siempre (en Windows, `%LOCALAPPDATA%\sirius`), fija como la de los ajustes y
  aunque él haya movido sus datos a otro sitio: así la orden de instalar y Sirius la
  encuentran sin mirar nada más, y unos 500 MB no acaban en OneDrive.
- **Cómo se instalan.** Un extra opcional, `voz`, en `pyproject.toml`; Quality no lo
  instala (`uv sync --locked --all-groups` no toca los extras). La orden, una sola, en
  PowerShell y en la carpeta de Sirius: `uv run --extra voz sirius-instala-la-voz`.
  Instala las bibliotecas, baja el modelo a una carpeta aparte y solo la pone en su
  sitio cuando está entera, y comprueba que el oído carga. `uv run sirius` no quita lo
  instalado: `uv run` solo añade lo que falta.
- **La orden para probarlo:** `uv run --extra voz sirius-oye`, en consola, sin ventana:
  le oye, escribe lo que oyó y lo que contesta Sirius, en la misma charla de la ventana,
  hasta Ctrl+C. Es la mitad de E-R03-01 que no depende de la pieza C.
- **Los ajustes de la voz del robot** son un modelo propio con una sola elección
  cerrada, el modelo del oído, que hoy es uno. No tienen texto libre (punto 4).

## Comprobación que la sostiene

Pendiente: se rellena con los comandos y sus cifras antes de pedir la revisión.

## Consecuencias

- La charla de la ventana y la de la consola son la misma; la ventana todavía no oye
  (pieza D).
- El conductor de la 0.3 enchufa sus dobles donde iría el micro, el detector y el
  transcriptor, a través de la raíz de composición de producción, como el de la 0.2
  enchufa el modelo de la charla. La comprobación de los modelos es la de verdad, sobre
  la carpeta de verdad del arranque de prueba.
- Model Studio no cambia.

## Alternativas descartadas y por qué

- **La tubería entera de Pipecat** (opción 1): en la decisión.
- **Sin Pipecat** (opción 3): sería programar desde cero el encadenado de Silero con
  Smart Turn, que el plan dice que no se programa, y repetir el cálculo de las
  características de audio de Smart Turn que Pipecat ya trae.

## La lección

- ninguna: todavía no hay revisión ni resultado; si los hay, se escriben aquí.

## Revisión externa

Alcance escrito antes de la primera petición, para que la revisión no lo descubra ronda
a ronda: esta PR trae la pieza B y nada más; mira que lo oído llegue a la charla por el
mismo camino que lo escrito, que el turno acabe donde dice el detector, que nada salga
del ordenador ni se baje solo, y que sin modelos diga la orden y no haga nada más. No
trae hablar, ni la ventana, ni a quién le hablan, ni cortarle; lo que no se puede ver
sin su micro está en «Qué NO garantiza».
