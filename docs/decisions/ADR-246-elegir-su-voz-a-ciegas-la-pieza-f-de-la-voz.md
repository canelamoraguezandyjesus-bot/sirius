# ADR-246 — Elegir su voz a ciegas: la pieza F de la voz

- Estado: APROBADO
- Fecha: 2026-10-16
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). La pieza y su orden los aprobó el
  propietario con el plan (ADR-232) y con la tabla de piezas de ADR-241, que es la última
  de la 0.3.

Este ADR es además la **nota de arranque** de la rama de la pieza F (skill
`disciplina-evidencia`): las cuatro preguntas, el criterio de parada y el alcance de la
revisión están escritos antes del primer cambio de código de la pieza y antes de
cualquier revisión.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** Hoy Sirius habla con una sola voz,
   `es_ES-davefx-medium`, la que puso la pieza C (`SpeakingVoice` en
   `src/sirius/config/local_voice.py`), y no hay forma de elegir otra. Las tres pruebas de
   la pieza F esperan en `xfail` estricto (PA-R03-10): la hoja de voces, la voz elegida
   que queda para hablar y que no haya forma de clonar una voz. El arreglo va en cinco
   sitios:
   - **El catálogo de voces**, cerrado como todos los ajustes de la voz: las cuatro
     masculinas de Piper en español de España que nombra ADR-241 (`davefx`, `sharvard`,
     `carlfm` y una de `mls`) y la de personaje con Chatterbox, que es su voz de serie, sin
     audio de nadie. Cinco candidatas.
   - **La prueba de voces**, un caso de uso: cinco frases fijas, típicas suyas (cuatro
     respuestas de la semilla que escribió él, un saludo, una broma, una pregunta y una
     frase larga, y otra con un número y una fecha); cada candidata dice las cinco con su
     voz al abrir la hoja, y las muestras viven en memoria (PA-R03-05). Las candidatas van
     barajadas y con etiquetas sin nombre; escuchar una muestra la pone por el altavoz;
     elegir guarda la voz.
   - **La voz elegida**, en los ajustes, como un valor del catálogo: con ella se carga la
     voz al abrir Sirius, y desde el turno siguiente sin volver a abrirlo: el oído cierra el
     altavoz de la voz de antes y carga la nueva.
   - **La voz de personaje**: un adaptador de Chatterbox que carga su modelo de la carpeta
     de modelos de Sirius, habla en español y nunca recibe audio de referencia. Va en un
     extra aparte, `personaje`, y la orden de instalar baja sus pesos; Sirius no baja nada
     en marcha (PA-R03-08).
   - **La ventana**: un botón que abre la hoja, con un botón por muestra y otro para
     elegir cada voz. La juzga E-R03-06.

   **¿Puede el sitio del arreglo observar el fallo?** Que la hoja dé lo que piden las
   pruebas, sí: el caso de uso sabe qué voz hay tras cada etiqueta y qué muestra salió de
   cada una. Que una voz le suene masculina, de España y a Sirius, no: eso lo dice él, por
   su altavoz (E-R03-06).
2. **Qué NO garantiza.**
   - Cómo suena la voz de serie de Chatterbox. Desde el contenedor no se llega a Hugging
     Face (el proxy responde 403), así que no se ha bajado ni oído. Si no le suena a Sirius
     no la elegirá; una voz de personaje distinta sería producto, y se le preguntaría.
   - Que Chatterbox hable en vivo a tiempo. Con el torch de PyPI para Windows va por el
     procesador: las muestras de la hoja salen, despacio. Si la elige y no puede hablar en
     vivo con la charla cargada, se le dice con la cifra y se le pregunta (E-R03-06).
   - Que se instale en su Windows. Solo se ha resuelto: con el extra `voz` y Python 3.14,
     se resuelve; `spacy-pkuseg`, que solo sirve para el chino y Chatterbox importa dentro
     de un `try`, no tiene rueda para Windows con 3.14 y se deja fuera, con `gradio`, que
     es de sus demos.
   - Que las cuatro de Piper sean masculinas: lo dice ADR-241, y lo oye él.
   - Que la biblioteca no sepa clonar: sí sabe (`audio_prompt_path`). Lo que se garantiza
     es que ningún camino de Sirius se lo pide.
3. **Criterio de parada**, fijado antes de ver ninguna prueba ni ninguna revisión:
   - **La pieza está terminada** cuando sus tres pruebas corren y pasan con el conductor de
     verdad, sin `xfail`; la tabla de `PRUEBAS_0.3_DEL_ROBOT.md` lo dice de PA-R03-10; la
     batería entera y la cadena de comprobación están en verde; la revisión propia no
     encuentra nada; y hay una ronda limpia de Codex sobre el head de contenido con
     Quality en verde. Con ella acaba la 0.3 en máquina; quedan las evaluaciones del
     propietario.
   - **Revisión propia antes de pedir otra**, y dos rondas seguidas con hallazgos de la
     misma familia: se deja de parchear y se busca la raíz (ADR-001).
   - **Cada regla nueva, con una prueba que la tumbe** en mutación.
   - **Si la voz de personaje no se puede instalar o no habla en su ordenador**, se para y
     se le dice con la cifra: es producto.
   - Si algo pide dinero o cambia el producto, se para y se le pregunta.
4. **Qué lo haría imposible.**
   - Clonar: que ningún puerto ni adaptador tenga por dónde recibir un audio. La voz solo
     recibe texto, el adaptador de Chatterbox no expone el audio de referencia y los
     ajustes no tienen rutas; una prueba lo mira y una mutación que añada ese parámetro la
     tumba.
   - Que se guarde el audio de las muestras: viven en memoria, y el conductor mira el disco
     (PA-R03-05).

**Lo aprendido en las piezas B a E, aplicado desde el principio** (ADR-242 a ADR-245):

- Una garantía va en el único sitio por el que pasan todos los caminos.
- Lo que se decide de algo, con el estado de cuando pasó, no con el de cuando se atiende.
- Lo que se decide con las palabras no se apunta en el diario con ellas.
- Un dato nuevo va por todos los caminos que lo leen, no solo por el que se está mirando.

## Contexto y problema

ADR-241 dejó la 0.3 en seis piezas, con sus pruebas de aceptación escritas antes del
código; la B a la E ya han entrado. La pieza F es «Elegir su voz a ciegas, con las de Piper
y una de personaje con Chatterbox» (PLAN_DEL_ROBOT, «Lo que se hace», 7: «5 frases típicas
suyas con 4 a 6 voces, a ciegas, por el altavoz. Entre ellas Piper y una voz de personaje
propia con Chatterbox. Clonar a alguien, solo con su permiso por escrito»).

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

Para la voz de personaje:

1. **La voz de serie de Chatterbox**, sin audio de referencia: no imita a nadie conocido.
2. **Chatterbox con una de Piper de referencia**: imitaría al locutor de esa voz.
3. **Mezclar varias voces de referencia**: una voz nueva, pero hecha con las de otros.
4. **Grabar una voz propia**: es clonar a alguien, y el plan pide su permiso por escrito.

Para cuándo vale la voz elegida:

- **Desde el turno siguiente**, cerrando el altavoz de la de antes.
- **Al volver a abrir Sirius**: más simple, pero elegir no se notaría hasta reiniciar.

## Decisión

La opción 1: la voz de personaje es la voz de serie de Chatterbox, sin audio de nadie; y la
voz elegida vale desde el turno siguiente, sin volver a abrir Sirius. Cinco candidatas,
cuatro de Piper y la de personaje, dicen cinco frases suyas en una hoja barajada y sin
nombres, y la elegida queda en los ajustes. Lo que se decidió al escribir el código se
anota aquí con su porqué.

Lo que se decidió al escribir el código, con su porqué:

- **El catálogo, cerrado** (`SpeakingVoice` en `src/sirius/config/local_voice.py`):
  `es_ES-davefx-medium`, `es_ES-sharvard-medium`, `es_ES-carlfm-x_low`,
  `es_ES-mls_10246-low` y `chatterbox-multilingual`. De `mls` hay dos voces en español de
  España, la 10246 y la 9972: se cogió una, como dice ADR-241, sin poder oír ninguna
  («Consecuencias»). La de sharvard trae un hombre y una mujer, y Piper habla por defecto
  con el primero de su lista: se le pide el locutor «M» por su nombre, y si la voz no lo
  trae no carga, en vez de hablar con otro. La elegida se guarda en los ajustes por su
  nombre (`local_speaking_voice`), y lo que no sea una de las cinco deja la de siempre.
- **Las cinco frases** (`VOICE_TEST_PHRASES` en `src/sirius/domain/voice_test.py`): un
  saludo, una broma, una pregunta y una frase larga, que son respuestas que él escribió para
  la semilla (ADR-235), y una con un número y una fecha. Ninguna cambia al prepararla para
  hablar (`prepare_speech_text`), así que suenan como sonarían en la charla (revisión
  propia, abajo).
- **La hoja** (`VoiceTestUseCase` en `src/sirius/application/voice_test.py`): carga cada voz
  como la carga el oído, con su altavoz a su frecuencia, le pide las cinco frases y baraja
  las voces tras «Voz A» a «Voz E», otra vez en cada hoja. Las muestras viven en la hoja, en
  memoria. Lo que se ve es su vista (`VoiceTestView`): la explicación, cada frase con un
  botón por voz y un botón por voz para elegirla. La ventana la pinta tal cual
  (`src/sirius/presentation/voice_test_dialog.py`), y el conductor la lee de ahí.
- **Escuchar, con el micro cerrado.** Una muestra no es algo que le digan: `listen`, que es
  por donde pasa toda muestra que suena, cierra el micro y calla la muestra que sonara
  antes. La ventana, además, para el oído al abrir la hoja y lo vuelve a abrir al cerrarla,
  por `_listen`, como siempre; al cerrarla se sueltan las voces cargadas para la hoja.
- **Elegir vale desde el turno siguiente.** La voz se guarda en los ajustes y el oído suelta
  la suya con su altavoz (`LocalListening.reload_voice`, con `Speaker.close` nuevo en el
  puerto); la nueva se carga al volver a escuchar. El oído lee la voz de los ajustes cada
  vez que la carga (`ChosenVoiceInstallation`), así que vale también al volver a abrir
  Sirius.
- **La voz de personaje** (`src/sirius/adapters/audio/character_voice.py`):
  `ChatterboxMultilingualTTS.from_local` de su carpeta,
  `modelos/voz/chatterbox/chatterbox-multilingual`, en la gráfica si torch la ve y si no en
  el procesador; cada frase con `generate(texto, language_id="es")` y nada más, a 24 000 Hz
  y en 16 bits como Piper, para el mismo altavoz. Va en el extra `personaje`
  (`chatterbox-tts` 0.1.7), con `spacy-pkuseg` y `gradio` fuera por
  `override-dependencies` de uv.
- **Hugging Face, sin conexión en marcha.** Al leer el código de Chatterbox antes de
  escribir el adaptador salió que su tokenizador, al cargar, le pide a Hugging Face un
  fichero del chino aunque hable español (`MTLTokenizer`, dentro de un `try`): en marcha
  sería una conexión (PA-R03-08). La ventana y `sirius-oye` ponen a Hugging Face sin
  conexión al arrancar (`hugging_face_offline` en
  `src/sirius/adapters/audio/voice_libraries.py`), y el cargador de la voz de personaje lo
  vuelve a poner y no carga si no puede saber que lo está. huggingface_hub 1.33 mira esa
  constante en cada petición, así que vale aunque ya estuviera importado.
- **La orden de instalar** baja siempre las cuatro voces de Piper, y la de personaje si
  está su extra: sus cinco ficheros, de Hugging Face, a una carpeta aparte que solo se pone
  en su sitio entera. Sin el extra dice cómo ponerla (`uv run --extra voz --extra personaje
  sirius-instala-la-voz`). Comprueba que cada voz carga, y suelta su altavoz.
- **Ningún camino para clonar.** La voz solo recibe texto (`Voice.say`), los ajustes no
  tienen dónde poner la ruta de un audio, ninguna ventana deja abrir uno, y nada en `src/`
  nombra lo que usa Chatterbox para imitar (`audio_prompt_path`, `prepare_conditionals`).
  El conductor lo mira en el código (`caminos_para_clonar`), y una mutación de cada camino
  lo tumba (abajo).
- **El extra cambia también el de la voz.** uv resuelve todos los extras juntos, y
  Chatterbox fija `transformers` 5.2.0, que pide `huggingface-hub` menor que 2 y
  `tokenizers` menor que 0.23: en `uv.lock` bajan de 2.2.0 a 1.33.0 y de 0.23.3 a 0.22.2,
  también para faster-whisper, el oído de la pieza B.

## Comprobación que la sostiene

- **Las tres pruebas de la pieza F** (PA-R03-10) en verde con el conductor de verdad, sin
  `xfail`: la hoja, la voz elegida al volver a abrir Sirius y que no haya forma de clonar.
- **66 pruebas nuevas**, de 8 739 a 8 805: la hoja y su caso de uso, el catálogo y los
  ajustes, la voz de personaje y Hugging Face sin conexión, el locutor de sharvard y soltar
  el altavoz, cambiar de voz en el oído, la orden de instalar con las cinco voces, la
  ventana de la hoja, y la voz elegida en el turno siguiente con Sirius de verdad
  (`tests/integration/test_voz_elegida.py`).
- **Mutación**: 42 mutaciones, caen las 42. Nueve contra las pruebas de aceptación: sin
  barajar, escuchar otra muestra, elegir que no hace nada o no se guarda, la voz que acepta
  un audio, Chatterbox con audio, la hoja con un nombre, una voz para todas y la ventana que
  deja abrir un audio. Y 33 contra las demás, una por regla nueva.
- **La batería entera**: 8 787 en verde, 2 fallos, 14 omitidas y 2 `xfail`, en 28 min 11 s,
  con las mutaciones corriendo a la vez. Un fallo era una prueba nueva del diario, que solo
  pasaba sola: otra prueba de la batería migra la base, y la migración apaga los
  registradores; se reprodujo en ese orden y se arregló como en ADR-245. El otro, la guarda
  de rendimiento de construir el contexto, de 1 500 ms: sola mide 902 a 970 ms con este
  código y 868 a 920 ms con el de `main`.
- **ruff** limpio; **mypy** sin errores en 729 ficheros; **el comprobador de documentos**,
  sin defectos en ADR-246, `PRUEBAS_0.3_DEL_ROBOT.md` y `MEMORIA.md`.
- **uv lock** resuelve con el extra `personaje` en 6 s, y `gradio` y `spacy-pkuseg` quedan
  con un marcador que nunca se cumple.

## Consecuencias

- **Cómo suena la voz de serie de Chatterbox no se sabe hasta E-R03-06**: desde el
  contenedor Hugging Face responde 403, y no se ha bajado ni oído ninguna voz, tampoco las
  de Piper.
- **Que las de Piper sean masculinas** lo dice ADR-241 y lo oye él. La de mls se cogió sin
  oírla, y que sharvard traiga su locutor con el nombre «M» no se ha podido ver: si no lo
  trae, la orden de instalar lo dice y esa voz no carga.
- **Con el torch de PyPI para Windows, Chatterbox va por el procesador**: preparar la hoja
  tarda más con ella, y hablar en vivo con ella puede no llegar a tiempo. Si la elige, se
  mide y se le pregunta (E-R03-06). La gráfica pediría el índice de PyTorch para Windows, y
  no se ha puesto.
- **Elegir la de personaje la carga dos veces**, una para la hoja y otra al volver a
  escuchar, y esa segunda es en el hilo de la ventana, como la del oído al abrirse: mientras
  carga, la ventana espera.
- **Chatterbox sortea cada vez**: la misma frase no sale igual dos veces, y la hoja enseña
  la de esa vez. Y lleva la marca de agua de Perth en todo lo que dice.
- **Dos bibliotecas de la voz cambian de versión** (arriba): faster-whisper con
  `huggingface-hub` 1.33.0 y `tokenizers` 0.22.2 se prueba en su ordenador con la orden de
  instalar.
- **La orden de instalar baja cuatro voces de Piper** en vez de una, y con el extra
  `personaje` la de Chatterbox, varios GB que no se han podido medir desde aquí.

## Alternativas descartadas y por qué

- **Chatterbox con una voz de referencia** (opciones 2 y 3): imita, aunque sea a medias, a
  quien grabó esas voces.
- **Grabar una voz propia** (opción 4): es clonar, y necesita su permiso por escrito.
- **Chatterbox dentro del extra `voz`, con una sola orden**: si torch no se instala en su
  Windows, tampoco se instalaría la voz de Piper, que no lo necesita.
- **Un solo altavoz para todas las muestras**, pasándolas a una frecuencia común: cada voz
  sonaría en la hoja de otra forma que hablando. Cada voz trae su altavoz, como al hablar.
- **Poner a Hugging Face sin conexión solo al cargar Chatterbox**: no basta si faster-whisper
  ya lo importó con conexión; se pone al arrancar y, si ya estaba importado, se apaga.
- **Que la voz elegida valga al volver a abrir Sirius**: más simple, pero elegir no se
  notaría hasta reiniciar.

## Revisión propia

Antes de empujar se releyó el diff entero contra el código y la nota, y se escribió una
prueba por cada regla nueva. Encontró cinco cosas, arregladas:

- **La frase larga no sonaba en la hoja como en la charla.** Era la de «Pensando en mi
  existencia…», con puntos suspensivos, y `prepare_speech_text`, por donde pasa todo lo que
  dice en la charla, los deja en dos. La cazó la prueba de que ninguna frase cambia al
  prepararla, y se cambió por otra suya de la semilla. Esa preparación no se ha tocado: no
  es de esta pieza.
- **Cerrar la hoja a mitad de prepararla dejaba voces cargadas**: el hilo que prepara podía
  cargar una voz después de que la hoja soltara las suyas. Ahora el caso de uso cuenta los
  cierres, y lo que se carga tras uno se suelta.
- **La conversión de Chatterbox a 16 bits no se podía probar**: usaba numpy, que Quality no
  instala. Ahora es Python puro, y se prueba.
- **Al soltar un altavoz que no se deja cerrar**, el diario decía «el altavoz que no
  arrancó». Ahora dice lo que pasó.
- **La prueba de que la ventana se pone sin conexión antes de nada** no fallaba si se hacía
  después de abrir Qt. Ahora sí.

## La lección

- familia: `lo-que-un-hilo-carga-despues-de-cerrar`
- sin esto se repetiría: que un trabajo en segundo plano siga cargando después de que
  quien lo abrió lo cierre, y que lo que cargue se quede. La hoja prepara las voces en otro
  hilo; si se cerraba a medias, la voz que ese hilo cargaba después se quedaba cargada, con
  su altavoz abierto. Lo vio la revisión propia antes de empujar (H-246).
- lo hace cumplir: `tests/unit/test_voice_test.py`

Lo que salió al leer el código de Chatterbox, su petición a Hugging Face al cargar, no
llegó a estar en el código de Sirius: se leyó antes de escribir el adaptador («Decisión»).

## Revisión externa

Alcance, escrito antes de la primera petición: esta PR trae la pieza F y nada más. Mira que
la hoja dé cinco frases con cinco voces barajadas y sin nombre, que cada muestra salga de
su voz y suene por el altavoz, que la elegida quede para hablar, también la de personaje,
y que ningún camino de Sirius acepte un audio para imitar una voz.

- **Ronda 1, sobre `afc6787a`**: un hallazgo P2, cierto, verificado antes de tocar nada.
  La comprobación previa de la hoja miraba solo los ficheros de las voces: con los de
  Chatterbox puestos y su biblioteca no, como queda un entorno rehecho sin el extra
  `personaje`, se habilitaba «Preparar las voces», se cargaban las de Piper y el error salía
  sin la orden. Se reprodujo con los cinco juegos de ficheros puestos y `chatterbox-tts` sin
  instalar: la hoja decía que no faltaba nada. Ahora la comprobación mira también esa
  biblioteca cuando las voces las carga la de verdad (`voice_test_missing`), y que falte la
  instala la orden, así que no se adivina nada; y si una voz no carga por otra cosa, el
  aviso lleva la orden de instalar, como el del oído (ADR-242). Cuatro pruebas más, y
  cuatro mutaciones que caen.
