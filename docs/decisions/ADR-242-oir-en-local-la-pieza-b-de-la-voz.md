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
  Instala las bibliotecas, baja el modelo a una carpeta aparte si falta y solo la pone
  en su sitio cuando está entera, y comprueba que el oído carga. Lo que ya está no lo
  vuelve a bajar (ronda 5, abajo), y si falta el modelo lo baja antes de mirar lo demás.
  Sirius la aconseja para lo que ella toca y dice lo que hace (ronda 8, abajo). `uv run sirius` no quita lo instalado: `uv run` solo
  añade lo que falta.
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
- **104 pruebas unitarias nuevas**: el servicio (`tests/unit/test_local_listening.py`), los
  adaptadores de verdad con módulos de mentira (`tests/unit/test_local_listening_adapters.py`),
  la instalación y la orden de instalar (`tests/unit/test_local_voice_installation.py`), la
  orden de consola (`tests/unit/test_listen_console.py`) y la guarda de las descargas
  (`tests/unit/test_solo_la_orden_de_instalar_baja_modelos.py`). Y tres de integración en
  `tests/integration/test_send_message.py`: pedida la charla solo en este ordenador, no
  guarda ni envía nada a un modelo de fuera, envía con el modelo que comprobó aunque cambie
  mientras prepara el turno, y con uno de aquí envía. Una más en
  `tests/integration/test_memory_suggestion_automatic_trigger.py`: un turno de voz deja
  pendiente lo que el modelo propone recordar, con la charla y la base de verdad. Y dos
  del conductor en `tests/acceptance/test_dobles_del_conductor.py`: lo contestado solo
  cuenta si la charla acabó bien, y varios turnos cerrados de una vez lo hacen fallar. Y
  tres en `tests/integration/test_oir_en_consola.py`, que pasan por `sirius-oye` con la
  charla y la base de verdad: una orden de olvido dicha por voz no sale por la consola,
  una respuesta que falla a medias sale como en la ventana, y una charla que se rompe
  después de guardar lo suyo se cuenta desde lo guardado y sale con error, sin volcado.
- **Mutación: todas caen en su ronda.** Quitar lo que suena antes de la voz, no mirar la
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
  no para, y no volver a bajar un modelo que está pero no carga; esta última se retiró
  en la ronda 5 con lo que vigilaba, y hoy cae la contraria. Y las nueve de la raíz
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
  bucle de eventos de un detector que no arranca. Y las cuatro de la ronda 5: prometer la
  orden con un modelo que está y no carga, volver a bajar un modelo que ya está, no bajar
  el que falta, y que la orden no diga, con una biblioteca rota, que repetirla no lo
  arregla. Y las cinco de la ronda 6: prometer la orden aunque una distribución
  instalada traiga el módulo que falta, buscar la distribución por el módulo entero y no
  por su paquete, dar todo por instalado, prometerla con los metadatos ilegibles, y que
  la orden no diga cómo escribirla cuando falta algo. Y las diez de la ronda 7: contar
  como ausente una distribución ilegible o no contar ninguna, que lo que falta no mire
  las distribuciones, que el oído de verdad no las pida o que se pidan también con
  motores de fuera, que la orden no las mire o no diga cómo escribirse, que un fallo al
  cargar prometa la orden o que lo que falta no la prometa, y olvidar una distribución
  del extra. Al cerrar la ronda 7 se han vuelto a pasar las 23 de las rondas 4 a 7 que
  siguen vigilando algo, y caen todas; las 14 que vigilaban la promesa desde el fallo se
  retiran con lo que vigilaban. Y las ocho de la ronda 8: que un fallo al cargar o lo que
  falta no aconsejen la orden, que la aconsejen el micro o el detector sin reiniciar, que
  el aviso no diga lo que hace la orden, que la orden mire las bibliotecas antes de bajar
  el modelo, que mande cerrar Sirius y repetir cuando faster-whisper no carga, y traer la
  descarga atrapando solo `ImportError`. Al cerrar la ronda 8 se han vuelto a pasar las 26
  de las rondas 4 a 8 que siguen vigilando algo, y caen todas; las cuatro de la ronda 7
  que vigilaban lo que se retira en la 8 se retiran con ello. Y las diez de la ronda 9:
  oír con la charla en un modelo de fuera, entregar el turno aunque la charla se haya
  ido fuera, seguir leyendo el micro después de dejar de oír, no decir por qué, que el
  proveedor que no dice dónde corre cuente como de aquí, que Ollama no lo diga, que
  OpenAI lo diga, que el modelo de mentira del conductor no lo diga, y que la orden vuelva
  a mandar cerrar Sirius y repetir o a decir que repetirla no lo arreglará. Al cerrar la
  ronda 9 se han vuelto a pasar las 35 de las rondas 4 a 9 que siguen vigilando algo, y
  caen todas; la de la ronda 8 que pedía decir que repetirla no lo arregla se retira con
  lo que vigilaba. Y las seis de la ronda 10: que la charla no compruebe el modelo, que
  envíe con el de ese momento y no con el que comprobó, que la voz no pida que el turno
  no salga, que no atrape que la charla se fue, y que entonces siga oyendo o no diga por
  qué. Al cerrar la ronda 10 se han vuelto a pasar las 41 de las rondas 4 a 10, y caen
  todas. Antes, una sobrevivió sin deber: el corredor de mutaciones de la sesión
  reutilizaba el código compilado de la anterior cuando las dos dejaban el fichero del
  mismo tamaño en el mismo segundo. Se arregló, sin guardar código compilado y con una
  fecha distinta en cada escritura, y las 41 se repitieron con el arreglo. Y las cuatro
  de la ronda 11: que la orden de consola ignore el aviso de que dejó de oír, que salga
  sin decirlo, que salga como si todo fuera bien, y que lo diga antes de contar lo que ya
  oyó. Al cerrar la ronda 11 se han vuelto a pasar las 45 de las rondas 4 a 11, y caen
  todas. Y las doce de la ronda 12: que el conductor dé lo escrito aunque la charla falle
  o se quede con el último turno, que el turno no diga por qué no acabó, que el oído no
  proponga lo que el modelo quiere recordar (vista también en la base de verdad), que lo
  proponga aunque la charla no acabe bien, que un fallo al proponer tumbe el turno, que
  el diario guarde lo propuesto, que el turno no diga qué se propuso, que la propuesta no
  se ligue a su respuesta, que la consola adivine el remedio y que calle lo propuesto. Al
  cerrar la ronda 12 se han vuelto a pasar las 57 de las rondas 4 a 12, y caen todas. Y
  las doce de la ronda 13: que el turno diga que acabó bien aunque fallara o no lleve lo
  que escribió, que la consola calle lo escrito si la charla falla, no marque cómo acabó,
  adivine el remedio, no dé la referencia del fallo, no diga que se canceló o deje un
  hueco si no escribió nada, que cambie la marca de fallido o el texto de cancelado,
  vistos desde la consola y desde la ventana, y que la ventana deje de usar el texto
  compartido. Y las tres de la ronda 14: que la consola enseñe lo oído y no lo guardado,
  vista también con la charla de verdad, y que calle lo escrito si falla, vista también
  así. Y las quince de la ronda 15: que la charla rota tumbe el oído, que el oído no pase
  su operación a la charla o que el turno roto no la lleve, que el diario guarde la
  excepción entera, que el modelo de oír o el detector rotos tumben el oído o que tras
  fallar siga oyendo, que la consola calle el envío roto, enseñe lo oído de él, no
  filtre por su operación (vista también con la charla de verdad), no salga con error,
  calle los turnos que venían con él o se caiga si no puede leer lo guardado, y que
  cambie el texto del historial que no carga. Al cerrar la ronda 15 se han vuelto a pasar
  las 85 de las rondas 4 a 15, y caen todas; las dos de la ronda 12 que vigilaban el porqué traducido a mano y el
  aviso de la consola se retiran con lo que vigilaban. La de etiquetar con la generación
  del
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

**Ronda 5** (`126045bd`, 14-10-2026): un hallazgo P2, cierto, y nacido del cierre de la
ronda 4. Un modelo que está y no carga seguía prometiendo la orden de instalar, y la orden
lo volvía a bajar. Pero el constructor de faster-whisper arranca CTranslate2 con el
dispositivo y el tipo de cálculo
(`faster_whisper/transcribe.py:689`, versión 1.2.1), y un ordenador sin memoria o con un
motor que no admite el cálculo falla con los mismos tipos de error que un fichero roto:
la orden gastaba unos 500 MB y volvía a fallar.

**La regla de las dos rondas salta otra vez**: es la tercera vez del remedio que no
remedia (rondas 2, 4 y 5), y la segunda seguida. El patrón, escrito: cada arreglo
adivinaba por el tipo de error si la orden lo arreglaría, y el tipo de error no lo dice.
La raíz es dejar de adivinar. La orden solo se promete cuando falta algo, porque eso es
lo único que pone con seguridad: un módulo que no está (`ModuleNotFoundError`) o un
fichero del modelo que no está. Todo lo que está y no carga se dice tal cual, sin
prometer nada. Se decide **retirar lo construido en la ronda 2**: la orden ya no vuelve a
bajar un modelo que está, porque no puede distinguir uno roto de un ordenador que no puede
cargarlo, y cuando falla algo que ella no arregla, dice que repetirla no servirá, también
con una biblioteca rota. Así el bucle de la ronda 2 no puede volver: Sirius no promete la
orden en ese caso.

Lo que queda sin arreglo automático, a propósito: un modelo que se estropea en el disco
después de instalarlo. Sirius dice que no carga y por qué, y no promete nada; se arregla
borrando su carpeta y volviendo a ejecutar la orden, guiado en su ordenador. Es raro: la
orden solo pone el modelo en su sitio cuando la descarga está entera, y el antivirus que
borra un fichero lo deja como «falta», que sí promete la orden.

**Ronda 6** (`bc2902a9`, 14-10-2026): un hallazgo P2, cierto. El revisor dice que llega
tarde por goteo, y cuenta como ronda igual. Una distribución instalada a la que le falta
un módulo (onnxruntime, con sus metadatos pero sin su módulo compilado) también da un
`ModuleNotFoundError`, y Sirius prometía la orden. Pero `uv run --extra voz` solo añade
lo que no está instalado; reinstalar lo que está es `--reinstall` (`uv run --help`, uv
0.8.17). Reproducido con las bibliotecas de verdad: «falta
onnxruntime.capi._pybind_state», con la orden prometida.

**La regla de las dos rondas salta otra vez**: cuarta vez de la misma familia (rondas 2,
4, 5 y 6), segunda seguida. El patrón: cada arreglo comparaba con algo que se parece a lo
que hace la orden (primero el tipo de error, después que falte un módulo), y no con lo
que hace. La orden añade las distribuciones del extra que no están instaladas y baja los
ficheros del modelo que faltan, y uv decide lo primero por los metadatos de lo instalado.
La raíz es mirar lo mismo que mira uv: la orden se promete solo si falta un módulo y
ninguna distribución instalada trae su paquete (`importlib.metadata.packages_distributions`),
y si los metadatos no se pueden leer, no se promete. Cuando la orden falla por algo que
falta, dice cómo escribirla; si no lo arregla ella, que repetirla no servirá. Se sigue
con lo construido: el criterio ya es el mismo que usa la herramienta que lo cumple.

Lo que queda, a propósito: si la cadena de imports pidiera un módulo que no trae ninguna
distribución del candado, uv no lo pondría y la promesa fallaría. Con el candado de hoy no
pasa (la cadena entera carga en el entorno con el extra), pero en Windows no se ha podido
mirar desde aquí.

**Ronda 7** (`ec829788`, 14-10-2026): un hallazgo P2, cierto, y nacido del arreglo de la
ronda 6. `packages_distributions()` sale de RECORD y de top_level.txt: una distribución
dañada que conserva su METADATA y los pierde no aparece en el mapa, y Sirius volvía a
prometer la orden aunque uv la ve instalada. Comprobado en Python 3.14.6: sin RECORD ni
top_level.txt, `packages_distributions()` no la ve y `importlib.metadata.distribution()`
sí, porque encuentra la distribución por su carpeta de metadatos.

**La regla de las dos rondas salta por quinta vez en la familia** (rondas 2, 4, 5, 6 y 7),
la segunda seguida. El patrón ya no es de un caso: desde la ronda 2, cada arreglo
adivinaba a partir del fallo si la orden lo arreglaría, y cada adivinanza tenía un borde
que el revisor encontraba en la ronda siguiente. Se decide **retirar lo construido para
adivinar** (de las rondas 4 a 6: el `ModuleNotFoundError` como causa y el mapa de
paquetes) y **sacar la promesa del camino del fallo**: `VoiceUnavailable` ya no dice si
lo arregla la orden. La orden solo se promete por lo que falta, y eso lo mira la
instalación antes de cargar nada: las distribuciones del extra por su nombre, por su
carpeta de metadatos, que es como uv sabe si están, y los ficheros del modelo. Un fallo
al cargar ya no puede prometerla, porque no tiene con qué.

Lo que eso deja, a propósito: solo se miran las distribuciones que pide el extra, no las
que piden ellas. Si falta una de esas (onnxruntime, por ejemplo), el aviso dice qué no
carga y no promete la orden, aunque uv la pondría: es quedarse corto, nunca prometer de
más. Con los dos entornos de verdad: sin el extra, faltan las cuatro y la orden dice cómo
escribirla; con el extra y sin PortAudio, no falta ninguna, y la orden dice que
sounddevice no carga y que repetirla no lo arreglará.

**Ronda 8** (`faba32f0`, 14-10-2026): dos hallazgos P2, ciertos, y los dos de la misma
familia, ahora por los dos lados.

- **Prometía de más.** Con el modelo sin instalar y una biblioteca que está pero no carga
  (sounddevice sin PortAudio, ya medido), Sirius aconsejaba la orden por el modelo, y la
  orden se paraba en la biblioteca sin bajarlo.
- **Prometía de menos.** Con una distribución en una versión vieja (pipecat-ai 1.11.0
  frente al `>=1.12,<1.13` del extra), Sirius la daba por instalada y no aconsejaba la
  orden, que sí la pondría al día.

**La regla de las dos rondas, sexta vez en la familia** (rondas 2, 4, 5, 6, 7 y 8). Que el
revisor encuentre bordes en las dos direcciones dice cuál es la raíz: Sirius intentaba
predecir qué harían uv y el ordenador, y eso no se puede sin hacer lo que hace uv. Se
decide **dejar de predecir**:

- La orden se aconseja para lo que ella toca, lo que falta y lo que no carga, y no para
  lo que no toca: el micro y el estado del detector.
- El aviso dice lo que la orden hace siempre: instala o pone al día lo que falte de la voz
  y, si el problema es otro, dice cuál. Es cierto por construcción, porque es lo que la
  orden hace, y una prueba lo mira.
- La orden baja el modelo antes de mirar las demás bibliotecas: lo que falta lo pone
  aunque otra cosa esté rota. Cuando falla algo, dice que repetirla, escrita como la da
  Sirius, no lo arreglará: uv ya puso al día lo que podía antes de empezar. Si es
  faster-whisper lo que no carga, lo dice así, sin mandar cerrar Sirius y repetir.
- Se retira lo de la ronda 7 en Sirius: antes de cargar vuelve a mirar solo los ficheros
  del modelo. Las distribuciones del extra las mira la orden, para decir cómo escribirla
  si se ejecutó sin el extra.

Lo que eso deja, a propósito: la orden se aconseja también cuando no lo va a arreglar (una
DLL que no carga, un ordenador sin memoria); entonces él la ejecuta, ve qué es y sabe que
repetirla no sirve. Con las bibliotecas de verdad, sin PortAudio y sin modelo, la orden
intenta bajar el modelo antes de decir nada de sounddevice (en el contenedor,
huggingface.co da 403).

**Ronda 9** (`ad8fb320`, 14-10-2026): dos hallazgos, ciertos los dos.

- **P1: lo dicho por voz podía salir del ordenador.** Configuración sigue ofreciendo
  OpenAI (ADR-234), y la charla puede cambiar de modelo en marcha (`set_llm_provider`).
  Con OpenAI elegido, el texto de lo oído iba a OpenAI al contestar, contra PA-R03-08
  («ninguna petición sale durante un turno de voz»). La prueba de aceptación no lo veía
  porque el conductor pone su modelo de mentira. Ahora cada proveedor dice si se queda en
  este ordenador (`runs_on_this_computer`: Ollama, que solo va a `localhost`, el de
  mentira y el sin configurar; OpenAI no), y el que no lo dice cuenta como de fuera. El
  oído no arranca con una charla de fuera, y al cerrar cada turno, antes de transcribirlo,
  lo vuelve a mirar: si la charla se fue fuera mientras escuchaba, el turno no sale, deja
  de escuchar y lo dice. Lo que queda fuera, a propósito: si después él elige OpenAI
  para escribir, la charla lleva consigo lo que se dijo antes por voz, como lleva lo
  escrito. Eso es la charla, no un turno de voz, y lo decide él al elegir el modelo.
- **P2: la orden aconsejaba cerrar Sirius y repetir ante cualquier fallo de descarga.**
  Es la séptima vez del remedio que no remedia, y viene de un consejo de la ronda 2 que el
  barrido de la ronda 8 no vio, como el «repetirla no lo arreglará» que esa misma ronda
  añadió. Se barre lo que quedaba: la orden dice la causa y nada más, sin adivinar
  remedios, y una prueba mira que ninguna de sus salidas de fallo los adivine. Lo único
  que sigue diciendo de lo que hace es lo cierto por construcción: cómo escribirla si se
  ejecutó sin el extra, porque así uv instala lo que falta.

**Ronda 10** (`d92151e7`, 14-10-2026): un hallazgo P1, cierto.

- **P1: el modelo podía cambiar entre la comprobación y el envío.** La comprobación de la
  ronda 9 miraba el modelo de la charla antes de transcribir, y la charla lo vuelve a
  leer al enviar. Si Configuración lo cambiaba mientras faster-whisper transcribe, que
  tarda, lo oído salía con el modelo nuevo; Codex lo reprodujo con «mi secreto» y un
  proveedor de fuera.

**La regla de las dos rondas** (9 y 10, la misma familia: lo oído puede salir del
ordenador). La raíz es el sitio de la comprobación: el oído no puede ver con qué modelo
se envía, porque ese modelo lo lee la charla al enviar. Se pone donde sí se ve:
`send_message(..., only_on_this_computer=True)` lee el modelo una sola vez, comprueba ese
y envía con ese; si es de fuera, no guarda ni envía nada y levanta
`ChatLeavesThisComputer`. El oído entrega así cada turno, y si la charla se fue, el turno
no sale, deja de escuchar y lo dice. Mirar antes de transcribir se queda solo para no
transcribir en balde. Lo demás que toca el turno después de esa lectura no cambia de
modelo: la respuesta, la frase de una orden de memoria y el resumen usan el mismo, las
huellas de la búsqueda van a Ollama en `localhost` y el juez usa el modelo local elegido.
Una prueba de integración cambia el modelo por uno de fuera mientras se prepara el turno,
ya comprobado, y el de fuera no recibe nada. Lo que queda fuera es lo de la ronda 9: la
charla, si después él elige OpenAI para escribir.

**Ronda 11** (`1c948bd7`, 15-10-2026): un hallazgo P2, cierto. El revisor dice que llega
tarde por goteo; cuenta como ronda.

- **P2: `sirius-oye` no decía que había dejado de oír.** Cuando la charla se va a un
  modelo de fuera mientras oye, el oído para y devuelve su aviso, pero la orden de
  consola no lo miraba: sin turnos, volvía a esperar para siempre a un micro cerrado.
  Ahora, si llega un aviso, la orden cuenta lo que ya oyó, dice el aviso y sale con
  error.

Es una familia nueva, así que no salta la regla de las dos rondas. De dónde viene: la
orden se escribió antes de que el oído pudiera parar solo, que llegó en la ronda 9, y
entonces no se miró a quien lo usa. Lo atienden dos: la orden y el conductor de las
pruebas de aceptación, que ya leía el aviso.

**Ronda 12** (`eb969154`, 15-10-2026): un hallazgo P2, cierto. El revisor dice que llega
tarde por goteo; cuenta como ronda.

- **P2: el conductor daba por contestado un turno que la charla no acabó bien.** Si el
  modelo falla a medias, el oído devuelve lo que llegó a escribir con `answered=False`, y
  el conductor lo pasaba como `contestado`: una prueba de aceptación que solo mirara eso
  lo habría dado por respuesta.

**La regla de las dos rondas** (11 y 12, la misma familia: quien usa lo que devuelve el
oído pierde parte por el camino). En la ronda 11 se arregló un sitio y se dijo que el
otro ya leía el aviso; era verdad del aviso, pero no se miró lo demás. La raíz: lo que
devuelve cada paso se traduce a mano en el siguiente, y lo que no se traduce se pierde
sin que nadie lo vea. Se repasa cada paso entero, campo a campo:

- **De la charla al oído.** El oído pasaba si la charla acabó bien y lo escrito, y perdía
  por qué no acabó y lo que el modelo proponía recordar, que Ollama también propone. Con
  lo escrito, esa propuesta la deja pendiente la ventana al acabar el turno; con la voz
  la dejaba nadie. Ahora la deja el oído, que es quien envía, con el mismo caso de uso
  que la ventana, y el turno lleva por qué no acabó y qué se propuso. Un fallo al
  proponer no deshace el turno, y el diario apunta solo el tipo de fallo.
- **Del oído a la orden de consola.** Contaba lo oído, lo contestado y, desde la ronda 11,
  el aviso. Ahora, si la charla no acabó bien, dice el mismo aviso que la ventana para
  ese fallo, en vez de «mira que su modelo esté abierto», que adivinaba el remedio: con
  el modelo sin configurar, por ejemplo, no lo es. Y si el modelo propuso algo, dice
  dónde confirmarlo. Si era para él no lo mira: en la pieza B siempre lo es, y la pieza
  D, que lo decide, tendrá que contarlo.
- **Del oído al conductor.** Lo contestado solo cuenta si la charla acabó bien, y si se
  cerraron varios turnos de una vez, falla en vez de quedarse con el último. Lo propuesto
  y el porqué no van en `TurnoDeVoz`: ninguna prueba de aceptación los pide, y están en
  la base.

**Ronda 13** (`b0d7c160`, 15-10-2026): un hallazgo P2, cierto.

- **P2: `sirius-oye` callaba lo que Sirius llegó a escribir si la charla fallaba.** Ollama
  puede escribir y después fallar, y la ventana enseña ese texto con su marca antes del
  aviso; la consola enseñaba solo el aviso. En la ronda 12 se había decidido así, a
  propósito, y la prueba construía el texto a medias sin mirar que saliera.

**Tercera ronda seguida de la familia** (11, 12 y 13). El repaso de la ronda 12 fue campo a
campo, pero a juicio: cada campo se traducía a mano y se decidía si hacía falta, y ese
juicio dejó pasar uno. Se decide **dejar de traducir**:

- El turno lleva lo que devolvió la charla, entero: el mismo resultado que recibe la
  ventana con lo escrito. Si acabó bien y lo que escribió se leen de él, no se copian.
- La consola enseña cada respuesta con lo mismo que usa la ventana al acabar un turno
  escrito: el texto con la marca de cómo acabó, que pasa de la ventana a una función
  compartida sin Qt (`sirius/presentation/message_text.py`), y el mismo aviso de fallo,
  con su referencia, o el mismo «Envío cancelado.», que también pasa a esa función. La
  referencia de lo que enseña es la ventana, no un juicio sobre qué hace falta.

Lo que queda fuera, a propósito: los botones que la ventana pone en cada respuesta (las
dos marcas, proponer un recuerdo a mano y reintentar) son para tocar, no texto; los trae
la pieza D con la ventana. El juez no se pierde: puntúa desde la base las respuestas que
no tienen nota, también las dichas por voz, cuando la ventana está abierta.

**Ronda 14** (`fb3b1e3b`, 15-10-2026): un hallazgo P2, cierto. El revisor dice que llega
tarde por goteo; cuenta como ronda.

- **P2: tras «olvida lo de…» dicho por voz, `sirius-oye` seguía enseñando lo que había que
  olvidar.** La orden guarda «Olvida lo de…», sin el tema, y la ventana enseña lo
  guardado precisamente para quitarlo de la pantalla; la consola escribía lo oído, con el
  tema entero.

**Cuarta ronda de la familia** (11 a 14). La 13 dijo que la referencia era la ventana,
pero copió la mitad de `_on_finished`: la respuesta, no lo suyo (`_settle_user_item`).
Ahora se recorre `_on_finished` entero, llamada a llamada, y cada una queda en la consola
o fuera con su porqué:

- **Lo suyo, como quedó guardado**: en la consola, con el mismo texto que la ventana. Lo
  oído tal cual sigue en el turno (`heard`), y el turno dice que para enseñarlo está lo
  guardado.
- **La respuesta con su marca, el aviso del fallo con su referencia y «Envío
  cancelado.»**: en la consola desde la ronda 13, con las funciones de la ventana.
- **Lo que el modelo propone recordar**: lo deja pendiente el oído, y la consola dice
  dónde confirmarlo.
- **Fuera, con su porqué.** Los botones de cada mensaje (las marcas, proponer a mano y
  reintentar) son para tocar y los trae la pieza D. El modo de la charla y el aviso de
  gasto la ventana los enseña en etiquetas fijas, no en el turno: la respuesta a «ponte
  serio» ya sale seria, y la voz solo va a un modelo de este ordenador, que no gasta. La
  página de Model Studio y su voz son otra cosa. Y el juez puntúa desde la base.

**Ronda 15** (`a624ff8e`, 15-10-2026): un hallazgo P2, cierto. El revisor dice que llega
tarde por goteo; cuenta como ronda.

- **P2: si la charla lanzaba una excepción, `sirius-oye` se caía con un volcado.** Por
  ejemplo, al guardar la respuesta después de haber guardado lo suyo. Con lo escrito, la
  ventana la para en la frontera (`SendMessageWorker`), vuelve a leer la charla guardada
  y enseña el aviso de siempre con su referencia (`_on_crashed`).

**Quinta ronda de la familia** (11 a 15). La 14 recorrió `_on_finished` entero, pero un
turno escrito acaba por dos sitios, y el otro es `_on_crashed`. Ahora se recorren los dos:

- **El oído** pone la operación de cada envío, como la ventana, y para en su frontera
  cualquier excepción de la charla: el turno sale sin resultado y con su operación, el
  diario apunta solo el tipo, y se sigue oyendo.
- **`sirius-oye`**, con un envío roto, hace lo de `_on_crashed`: vuelve a leer la charla
  guardada y cuenta lo de esa operación, con el mismo aviso y la misma referencia. Si no
  puede leerla, lo dice con el texto de la ventana, que pasa también a la función
  compartida. Cuenta los demás turnos que venían con él y sale con error.
- **Lo que la ventana no tiene**, con la misma regla: si el detector o el modelo de oír
  fallan a mitad, el oído deja de oír y lo dice, sin aconsejar la orden de instalar.

Una prueba de integración rompe la charla de verdad después de guardar lo suyo: la
consola cuenta lo guardado y el aviso, y sale con error, sin volcado.
