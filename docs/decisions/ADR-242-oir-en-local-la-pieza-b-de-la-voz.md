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

Medido el 14-10-2026 en el contenedor de la sesión, sobre la rama de esta PR.

- **Las siete pruebas de la pieza B**, en verde con el conductor de verdad
  (`tests/acceptance/test_robot_0_3_voz.py`), y el conductor dice ya que la pendiente es
  la C (`tests/acceptance/test_dobles_del_conductor.py`). La tabla de
  `docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md` pone PA-R03-01 en verde; PA-R03-08 sigue
  pendiente de la C.
- **75 pruebas unitarias nuevas**: el servicio (`tests/unit/test_local_listening.py`), los
  adaptadores de verdad con módulos de mentira (`tests/unit/test_local_listening_adapters.py`),
  la instalación y la orden de instalar (`tests/unit/test_local_voice_installation.py`), la
  orden de consola (`tests/unit/test_listen_console.py`) y la guarda de las descargas
  (`tests/unit/test_solo_la_orden_de_instalar_baja_modelos.py`).
- **Mutación: 56 de 56 caen.** Quitar lo que suena antes de la voz, no mirar la
  instalación, escribir lo oído en el diario, mandar un turno vacío, no vaciar el turno,
  leer el micro parado, empezar un turno o transcribir con un fin de turno sin voz
  delante, decir que no es para él, dar por local cualquier ajuste, no pedir
  `tokenizer.json`, cargar sin `local_files_only`, dejar que Smart Turn guarde audio,
  nombrar una descarga en el oído, que Smart Turn no decida, que el silencio largo no
  acabe el turno, poner en su sitio un modelo a medias y dejar en el disco una descarga
  cortada: cada una la tumba al menos una prueba. La de `tokenizer.json` solo cayó
  cuando la prueba dejó de copiar la lista de ficheros de Sirius y escribió la suya, y la
  del fin de turno suelto, cuando la prueba miró también con qué empieza el turno. Las
  cuatro de la ronda 1 de Codex, abajo, también caen: parar sin reiniciar el detector,
  reiniciarlo sin cargar analizadores nuevos, sin soltar los viejos, y un oído de mentira
  que no olvida al reiniciarse. Y las siete de la ronda 2: parar sin limpiar el estado
  antes, no soltar las piezas cuando parar falla, sustituir el par del detector antes de
  tenerlo entero, no soltar el nuevo a medias, no cerrar el micro que no arranca ni el que
  no para, y no volver a bajar un modelo que está pero no carga. Y las nueve de la raíz
  de la ronda 3: un import que no traduce `OSError`, un import suelto en el oído, un micro
  que acepta trozos de cualquier apertura o que no cambia de apertura al cerrar, cerrar el
  micro o soltar un analizador propagando el fallo, parar sin apuntar el detector sin
  reiniciar, volver sin reintentarlo, y soltar las piezas si el micro falla al cerrar.
  Y las dieciocho de la ronda 4: leer sin mirar la generación del trozo, etiquetarlo con
  la generación del momento y no con la de su flujo, encolar lo de un micro ya cerrado,
  importar atrapando solo `ImportError` y `OSError`, prometer la orden por cualquier
  `ImportError`, no mirar la causa del error o mirar solo las causas, nombrar el módulo
  importado en vez del que falta, prometer la orden con una biblioteca que está pero no
  carga, atrapar solo tres tipos de error al arrancar Silero y Smart Turn o prometer ahí
  la orden, atrapar solo tres tipos al cargar el modelo, comprobar las bibliotecas sin
  faster-whisper o sin las demás, que la orden no las mire antes que el modelo, que no
  diga que repetirla no lo arregla o que lo diga cuando sí lo arregla, y dejar abierto el
  bucle de eventos de un detector que no arranca. La de etiquetar con la generación del
  momento sobrevivió a la prueba que reproduce el caso de Codex, que para el hilo dentro
  de `bytes(data)`, donde las dos coinciden; cayó con otra que lo para justo después de
  comprobar.
- **Las bibliotecas de verdad**, en un entorno aparte con el extra (`uv sync --frozen
  --extra voz`, Linux y Python 3.14.6, sin micro): Silero y Smart Turn cargan en 0,26 s y
  tardan 0,91 ms por trozo de 32 ms. Con la voz grabada que trae Pipecat
  (`pipecat/services/aws/nova_sonic/ready.wav`, 0,73 s, con medio segundo de silencio
  delante y cuatro detrás), el detector da voz a los 0,90 s y el turno por acabado a los
  1,09 s; con un tono de 220 Hz no da voz. Sin modelo, el oído no carga y lo dice, sin
  intentar ninguna conexión: con la carpeta que no existe, faster-whisper rechaza el
  nombre (`HFValidationError`); con ficheros que no son un modelo, CTranslate2 no los lee
  (`RuntimeError`). Con un modelo roto, el Silero de verdad falla con `InvalidProtobuf`
  de onnxruntime, y tokenizers, con un `tokenizer.json` cortado, con un `Exception`
  pelado: los dos heredan directamente de `Exception`, no de `RuntimeError`, y con el
  cargador de antes de la ronda 4 habrían tumbado a Sirius. La orden de instalar, con las
  bibliotecas de verdad y sin PortAudio, dice «sounddevice no carga (PortAudio library
  not found)», sale con error y no intenta bajar nada.
- **Lo que no se ha podido probar aquí:** que faster-whisper transcriba. La política de
  red del contenedor no deja llegar a huggingface.co (403), así que no hay modelo que
  cargar. Lo hace E-R03-01 en su ordenador.
- **La prueba con las bibliotecas de verdad encontró un fallo** que las de los módulos de
  mentira no veían: sin PortAudio, `import sounddevice` falla con `OSError`, no con
  `ImportError`, y el cargador del oído se caía en vez de decir qué falta. Arreglado, con
  su prueba (H-242).
- **El candado**: `uv lock` añade 967 líneas y no cambia ninguna versión que ya estuviera;
  `uv sync --locked --all-groups`, lo que hace Quality, no instala nada de la voz.

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

- familia: `doble-mas-permisivo-que-la-herramienta-que-dobla`
- sin esto se repetiría: un adaptador que carga una biblioteca con código nativo solo
  atrapa `ImportError`, porque así fallan los módulos de mentira de sus pruebas, y se cae
  cuando la biblioteca de verdad no encuentra lo suyo y falla con `OSError`; a Piper, en la
  pieza C, le puede pasar lo mismo. En esta misma PR mordió cuatro veces: el detector de
  mentira de las pruebas no guardaba el turno entre trozos, Silero y Smart Turn sí
  (ronda 1 de Codex); el import con `OSError` volvió en la ronda 3, porque el arreglo
  de la ronda 2 movió el import de faster-whisper a una función nueva que solo atrapaba
  `ImportError`; y en la ronda 4 los dobles de Silero y del modelo de oír fallaban con
  `RuntimeError`, mientras onnxruntime y tokenizers fallan con excepciones que heredan
  directamente de `Exception`. La raíz es la misma: un doble que no tiene el estado ni
  los fallos de la herramienta. Lo cierra que los tres sitios donde el oído carga algo de
  fuera atrapen cualquier `Exception`, que todos los imports pasen por `_import`, con una
  prueba que falla si una función del módulo importa por su cuenta, y que los dobles
  fallen con los tipos medidos en las bibliotecas de verdad.
- lo hace cumplir: `tests/unit/test_local_listening_adapters.py`

## Revisión externa

Alcance escrito antes de la primera petición, para que la revisión no lo descubra ronda
a ronda: esta PR trae la pieza B y nada más; mira que lo oído llegue a la charla por el
mismo camino que lo escrito, que el turno acabe donde dice el detector, que nada salga
del ordenador ni se baje solo, y que sin modelos diga la orden y no haga nada más. No
trae hablar, ni la ventana, ni a quién le hablan, ni cortarle; lo que no se puede ver
sin su micro está en «Qué NO garantiza».

**Ronda 1** (`921a3289`, 14-10-2026): un hallazgo P2, cierto. Al parar a media frase y
volver a escuchar, el servicio olvidaba su turno pero el detector no: Silero seguía
creyendo que había voz y Smart Turn guardaba el audio del turno viejo. Comprobado con las
bibliotecas de verdad y la voz grabada de Pipecat: sin reiniciar, en el silencio de
después el detector da el turno viejo por acabado; reiniciado, solo silencio, y tras
cinco reinicios sigue habiendo un hilo vivo, no seis. Arreglo: el detector tiene
`reset()`, el servicio lo llama al parar, y el de verdad carga un Silero y un Smart Turn
nuevos y suelta los viejos con su `cleanup()`. La prueba que lo pide usa un detector de
mentira con memoria, como Silero; la anterior no podía verlo porque el suyo no tenía.

**Ronda 2** (`294a44be`, 14-10-2026): dos hallazgos P2, ciertos los dos y de otra familia
que la ronda 1, así que no salta la regla de las dos rondas.

- **La orden de instalar no arreglaba un modelo que está pero no carga.** Sirius decía
  que se ejecutara, la orden veía los ficheros, no bajaba nada y volvía a fallar: un
  bucle. Ahora la orden comprueba que el modelo carga (`load_listening_model`, la misma
  carga que usa el oído) y, si no, lo baja otra vez; si no puede bajarlo, dice además
  que se cierre Sirius, que en Windows retiene el modelo abierto.
- **El reinicio del detector no era atómico.** Si cargar el par nuevo fallaba, `stop()`
  se cortaba a medias y el servicio seguía diciendo que escuchaba con el micro cerrado.
  Ahora `stop()` limpia su estado antes y, si cerrar el micro o reiniciar el detector
  falla, suelta las piezas para que el siguiente `start` las cargue de nuevo; el
  detector construye el par nuevo entero antes de sustituir el viejo, y si no puede,
  suelta lo que llegó a crear y se queda con el que tenía.

Antes de arreglarlo se repasaron los caminos de fallo vecinos para no recibirlos de uno en
uno, y salieron dos más del mismo código, arreglados en el mismo commit: el micro que no
arranca dejaba su flujo sin cerrar, y si pararlo fallaba no se cerraba. Con las bibliotecas
de verdad, el reinicio sigue dando solo silencio tras parar a media frase, y un hilo vivo
tras cinco reinicios.

**Ronda 3** (`a2cd39db`, 14-10-2026): dos hallazgos P2, ciertos los dos.

- **El import de faster-whisper solo atrapaba `ImportError`.** CTranslate2 carga sus DLL
  con `ctypes` y puede fallar con `OSError`; el arreglo de la ronda 2 había movido ese
  import a `load_listening_model` sin el `OSError` que ya tenía el cargador. Es la familia
  de H-242, la tercera vez en esta PR.
- **Si el micro fallaba al cerrar, el servicio soltaba la única referencia al flujo.** El
  flujo podía seguir captando mientras Sirius decía que estaba parado, y el siguiente
  `start` abría otro. Este hallazgo nace del arreglo de la ronda 2.

**La regla de las dos rondas salta aquí.** Las rondas 2 y 3 traen la misma familia: un
fallo a medias que deja a Sirius diciendo una cosa y al hardware haciendo otra. Cada
parche añadía otro camino de fallo que el revisor encontraba en la ronda siguiente, así
que se dejó de parchear y se cerró por construcción:

- **El micro numera cada apertura.** Al cerrar pasa a la siguiente, y ningún trozo de una
  apertura pasada entra ya en la cola, pare bien o mal PortAudio: cerrado el micro, a
  Sirius no le llega audio aunque el hardware siga encendido. Cerrar no falla nunca; lo
  que PortAudio no puede hacer se apunta en el diario.
- **Parar no suelta ninguna pieza.** Si el detector no se puede reiniciar, se apunta; el
  siguiente `start` lo vuelve a intentar y, si sigue sin poder, lo dice como aviso y no
  abre el micro. Soltar un analizador viejo que no se libera tampoco rompe el reinicio.
- **Todos los imports del oído pasan por `_import`**, que traduce `ImportError` y
  `OSError` en el mismo aviso, con una prueba que mira el árbol del módulo y falla si una
  función importa por su cuenta.

Las nueve mutaciones de la raíz caen. Con las bibliotecas de verdad, el reinicio sigue
dando solo silencio y un hilo vivo, y sin PortAudio o sin modelo el oído lo dice sin
caerse.

**Ronda 4** (`4b1b1b85`, 14-10-2026): dos hallazgos P2, ciertos los dos, y los dos sobre
la raíz de la ronda 3.

- **Una carrera en el micro.** El hilo de PortAudio miraba la generación y después
  encolaba; si entre medias se cerraba y se volvía a abrir el micro, el trozo viejo
  entraba con la apertura nueva. Codex lo reprodujo parando el hilo en `bytes(data)`.
- **El aviso prometía un remedio que no remedia.** Con una biblioteca que está pero no
  carga (`OSError`), Sirius decía que se ejecutara la orden de instalar, y la orden no
  la repara; con faster-whisper, además, volvía a bajar el modelo.

**La regla de las dos rondas vuelve a saltar, por las dos familias**, y se para a buscar
la raíz de cada una antes de arreglar nada:

- **La carrera** es de la familia de las rondas 2 y 3, y nace del agujero de su propia
  raíz: la comprobación vivía en el hilo que no manda. Ahora cada trozo va a la cola con
  la generación de su flujo, y quien la compara es `read`, en el hilo de Sirius, que es
  el único que cambia de generación: no hay comprobación que se adelante a un cierre. Lo
  que mira el hilo de PortAudio queda solo para que un micro que no se deja cerrar no
  llene la memoria. La prueba que lo pide para el hilo en el peor punto, justo después
  de comprobar, además del de Codex.
- **El remedio que no remedia** es la segunda vez, tras la ronda 2. Se buscaron los
  demás sitios con la misma suposición, que se sabe con qué falla una biblioteca y qué
  significa, y salieron tres que el revisor no había visto: en Windows, una DLL que no
  carga da `ImportError`, igual que un módulo que no está, y la orden tampoco lo
  arregla; Silero y Smart Turn, con un modelo roto, fallan con excepciones de
  onnxruntime, y el modelo de oír, con un `tokenizer.json` roto, con una de tokenizers,
  que no heredan de `RuntimeError` y habrían tumbado a Sirius. La raíz: cargar algo de
  fuera no tumba a Sirius, falle como falle, y la orden de instalar solo se promete donde
  arregla, si falta un módulo (`ModuleNotFoundError`, suelto o como causa, que es como lo
  envuelve Pipecat) o si el modelo de oír no carga, que la orden vuelve a bajar. La orden
  mira las bibliotecas antes que el modelo y, si lo que falla no lo arregla ella, dice
  que repetirla no servirá.

Se sigue con lo construido: cada familia queda cerrada por construcción y no caso a caso,
y las dieciocho mutaciones de la ronda caen. Con las bibliotecas de verdad, el detector
da lo mismo que antes (voz a los 0,90 s, turno acabado a los 1,09 s, solo silencio tras
parar a media frase y reiniciar, un hilo tras cinco reinicios).
