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

- **Dos puertos nuevos** en `src/sirius/ports/local_voice.py`, junto al micro, el
  detector y el transcriptor de la pieza B: la voz, que convierte una frase en sonido
  (`say`), y el altavoz, que lo hace sonar sin esperar (`play`), dice si aún suena,
  también lo que espera en cola (`playing`), cuánto tarda en sonar lo que se le da
  (`latency`) y calla (`stop`), sin fallar.
- **El corte en frases** (`src/sirius/application/speech_cutter.py`): lo que la charla va
  escribiendo se acumula, y se corta detrás de un final de frase y su blanco, o de un
  salto de línea, solo si cortar no cambia nada. Lo de delante está cerrado: preparado
  con `prepare_speech_text`, sin marcas a medias. Lo de detrás ya dice algo y no empieza
  por una marca que al cerrarse pueda dejar a la vista una puntuación, que se pegaría a la
  frase de antes; un bloque de código seguro sí vale, para que la frase que lo presenta no
  espere al bloque. Y lo de delante y lo de detrás, preparados por separado, dan lo mismo
  que todo lo llegado preparado de una vez. Qué es código no lo deciden reglas propias
  (ronda 5): lo es lo que lo es para CommonMark, leído con un analizador de verdad,
  `markdown-it-py`, sobre toda la respuesta llegada, con sus citas, sus listas y sus
  sangrías, y lo que la ventana enseña como bloque con su propia regla, la de B8b en
  `message_view`, que no es CommonMark. Cada bloque se cambia por una marca indivisible
  que `prepare_speech_text` dice que queda en pantalla, y lo de dentro no llega a la
  preparación. Mientras la respuesta sigue, desde donde aún no se sabe qué es código no se
  corta: un bloque que llega a la última línea, que aún puede crecer; unas comillas que
  aún pueden abrir un bloque en la ventana; o una última línea a medias que, detrás de sus
  blancos, sus citas y sus viñetas, aún puede ser la raya de uno.
  Al acabar la charla se suelta lo que quede, y lo que se ha quedado a medias no se dice
  como código ni como marca (`final_speech_text`): las cuatro construcciones con cierre
  que quita `prepare_speech_text` se tratan como si se cerraran. Un bloque de código
  abierto es código hasta el final, como para CommonMark, y se dice que queda en
  pantalla; del enlace se cierra el destino donde acaba la dirección, y se dice su texto;
  y del código en línea y del énfasis se quita lo que queda suelto: comillas, corchetes,
  dos o más estrellas o guiones bajos seguidos, y uno solo que no esté entre dos letras o
  cifras ni entre dos blancos, donde puede ser una multiplicación o parte de un nombre. Lo
  dicho, unido, es lo que da `final_speech_text` con la respuesta entera, salvo los
  blancos y una frase de solo puntos, que no se dice. Lo que no puede ver es lo que aún no
  ha llegado: una marca que se empareja con otra de una frase posterior, como en
  `*a*. Hola 5*3`.
- **El oído habla** (`src/sirius/application/local_listening.py`): entrega cada turno a
  la charla con un `on_delta` que alimenta el corte, y cada frase cerrada se pide a la
  voz y suena en cuanto está. Antes de la primera cierra el micro, y lo vuelve a abrir
  cuando el altavoz dice que ha acabado; al cerrarse, el micro tira lo que captó y nadie
  leyó, como en la pieza B. Si la voz, el altavoz o el corte fallan, deja de hablar sin
  que el fallo salga a la charla, que acaba y guarda la respuesta entera, y después deja
  de oír con su aviso («No puedo hablarte: la voz ha fallado (…)» o «el altavoz»), sin la
  orden de instalar. Parar le calla. Si la voz no carga al arrancar, no abre el micro y
  aconseja la orden, como con el oído. Si al volver a escuchar aún suena lo último que
  dijo, no abre el micro hasta que calle.
- **La charla avisa cuando acaba** (`SendMessageUseCase.send_message`, `on_completed`):
  en cuanto la respuesta acaba bien y está guardada, antes de lo que la charla hace
  después del turno. El oído dice ahí lo que le quedaba. Esperar a que `send_message`
  volviera hacía esperar la última frase al resumen de la charla, que pide otra
  respuesta al modelo (abajo, la lección y H-243). Una orden de memoria avisa igual,
  después de dar su respuesta.
- **La voz de verdad** (`src/sirius/adapters/audio/local_speaking.py`): Piper 1.8, con
  `es_ES-davefx-medium`, una de las cuatro voces masculinas en español de España de
  ADR-241, cargada solo desde su fichero y su `.onnx.json`, en
  `modelos\voz\piper\es_ES-davefx-medium\`, una carpeta por voz. Piper apunta en DEBUG
  el texto de cada frase; su registrador queda en WARNING.
- **El altavoz de verdad**: un flujo de salida de `sounddevice`, mono, de 16 bits, a la
  frecuencia de la voz y en bloques de 512 muestras, que se abre al cargarla y sigue
  abierto. Da por acabado lo que dijo cuando ha salido lo último, con la latencia del
  flujo y un cuarto de segundo más, la cola de su voz en la habitación: hasta entonces el
  oído no abre el micro. Callar tira lo que esperaba; lo que PortAudio ya tiene sale
  igual y, hasta que sale, sigue sonando.
- **Los ajustes** ganan la voz como elección cerrada (`SpeakingVoice`); la instalación la
  mira, y la orden de instalar la baja con `download_voice` de Piper a una carpeta aparte,
  la pone en su sitio solo si trae sus dos ficheros, mira las bibliotecas de hablar y
  comprueba que la voz carga y el altavoz se abre. Es lo único que nombra
  `download_voice`, y la guarda de las descargas lo vigila.
- **Con qué oye y habla**, para PA-R03-08, lo da `voice_tools` en
  `src/sirius/adapters/audio/voice_libraries.py`, leído de los módulos que importan los
  cargadores. Los dos cargadores importan por `import_voice_library`, que antes era el
  `_import` privado del oído.
- **`sirius-oye`** dice las respuestas por el altavoz, además de escribirlas.
- **Lo que tarda, para E-R03-02.** Cada turno lleva cuánto pasó desde que el detector
  dejó de oír su voz hasta que sonó la primera frase, contando lo más que tarda el
  altavoz en sonar: lo que puede esperar al siguiente bloque y la latencia del flujo;
  el diario apunta la cifra y nada más, y `sirius-oye` dice al salir el P95 de los turnos
  de esa vez. La cifra empieza cuando Silero confirma que ha callado, 0,2 s después
  (`VAD_STOP_SECS` de Pipecat), y la consola lee el micro cada 0,03 s: por eso E-R03-02
  pasa si el P95 que dice queda por debajo de 1,25 s, que son los 1,5 s del plan contados
  desde que él calla.

## Comprobación que la sostiene

Medido el 15-10-2026 en el contenedor de la sesión, sobre la rama de esta PR.

- **Las seis pruebas de la pieza C**, en verde con el conductor de verdad
  (`tests/acceptance/test_robot_0_3_voz.py`): empieza a hablar con la primera frase antes
  de que el modelo acabe, dice lo que escribió sin marcas ni código, con una voz de Piper
  en español de España, su propia voz no empieza un turno, oye y habla con las
  herramientas del plan, y la tubería añade menos de 200 ms en el P95 de 20 turnos. El
  conductor dice ya que la pendiente es la D (`tests/acceptance/test_dobles_del_conductor.py`).
  La tabla de `docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md` pone en verde PA-R03-02, PA-R03-08
  y PA-R03-09; PA-R03-03 sigue pendiente porque también es de la E, con su prueba de la C
  en verde.
- **Que cierra el micro mientras habla**, como pide `PRUEBAS_0.3_DEL_ROBOT.md` («lo
  enseña su PR en su comprobación»): la prueba unitaria que sigue el orden de todo lo que pasa en un turno
  ve cerrarse el micro antes de la primera frase y abrirse después de la última, y la
  mutación que no lo cierra hace que su propio eco entre como un turno en PA-R03-03.
- **162 pruebas unitarias nuevas**: el servicio que oye y habla (16 más en
  `tests/unit/test_local_listening.py`, de 30 a 46), el corte en frases (115 en
  `tests/unit/test_speech_cutter.py`; entre ellas, lo mismo dicho que `final_speech_text`
  con el texto entero de 302 maneras de trocear 18 respuestas, 5 436 troceos, y de 12
  maneras de trocear 500 textos al azar hechos de palabras, puntuación, saltos, sangrías y
  marcas, en los que el corte de `e41ff85f` da otra cosa 373 veces; ninguna marca
  dicha al acabar, pare donde pare cada una de las 18 respuestas; lo que se hace a
  medias con cada construcción de `prepare_speech_text`; y que lo de dentro de un
  bloque no se dice nunca, con dieciséis bloques que no se cierran donde parece o van dentro
  de una cita, de una lista o de una regla de la ventana, cada uno troceado de 52
  maneras, y con 150 respuestas al azar con citas, listas y sangrías, enteras y a medias,
  en las que se pregunta qué es código a un analizador de CommonMark y a la ventana),
  Piper y el altavoz con
  módulos de mentira (15 en `tests/unit/test_local_speaking_adapters.py`), la
  instalación y la orden de instalar (12 más, de 24 a 36), `sirius-oye` y lo que tarda
  (3 más, de 13 a 16) y que el oído importa lo que dice `voice_tools` (1 más en
  `tests/unit/test_local_listening_adapters.py`). Y 4 de integración: la charla avisa de
  que acabó con la respuesta guardada y antes de resumir, no avisa si falla ni si se
  cancela (`tests/integration/test_send_message.py`), y una orden avisa también
  (`tests/integration/test_ordenes_de_memoria.py`). Una de `sirius-oye` con la charla de
  verdad mira además que una orden de olvido dicha por voz tampoco sale por el altavoz.
- **Mutación.** 78 mutaciones de la pieza C, cada una con la prueba que tiene que
  tumbarla: en la primera vuelta cayeron 74. Sobrevivieron cuatro, y las cuatro caen
  desde la revisión propia: volver a cargar la voz en cada arranque y parar sin olvidar
  que hablaba (la prueba de parar mientras habla no arrancaba otra vez ni seguía el micro
  después), cortar dentro de un bloque de código (la marca que deja un bloque abierto
  casi siempre lo paraba; no si una comilla de código suelta delante se empareja con
  él, y ahora hay prueba de eso) y un remedio adivinado en mayúscula, que la comprobación
  de la orden no veía. Las 85 mutaciones de la pieza B, puestas al día para el código
  nuevo, siguen cayendo las 85. Tras la ronda 1 de Codex y el corte nuevo son 92: las
  del corte se rehicieron para sus tres condiciones, 18, y caen las 92. Tras la ronda 2,
  100: 8 más para lo que se dice al acabar, y la de las tres comillas cambia, porque ya
  no hace falta que abran una línea. Tras la ronda 3, 104: las de lo que se dice al
  acabar se rehicieron para las cuatro construcciones, 12, y caen las 104. Tras la ronda
  4, 120: 20 para los bloques como los ve Markdown, dónde empieza una línea y el
  énfasis doble, y caen las 120. Sobrevivió la que quitaba no cortar dentro de un
  bloque abierto: esa comprobación sobraba, porque la comparación con lo llegado ya lo
  impide, y se quitó; y cuatro más hasta que hubo pruebas de unas comillas y unas
  virgulillas tras una frase. Una más no se
  cuenta porque es equivalente: quitar que lo de detrás tenga que decir algo no cambia
  nada, porque con lo de detrás vacío la frase y un blanco nunca dan lo llegado, que no
  acaba en blanco. Tras la ronda 5 y la raíz, 145: las 20 que miraban las reglas propias
  se fueron con ellas, y entran 45 para qué es código y hasta dónde se sabe; caen 142.
  Sobreviven tres, y las tres son equivalentes: juntar dos bloques que se tocan solo
  cambia cuántas veces se dice que queda en pantalla, igual trozo a trozo que entera; que
  el analizador lea también lo de dentro de las líneas solo cambia lo que tarda (1,38 ms
  frente a 0,43 ms con una respuesta de 2 730 caracteres); y mirar si un bloque trae su
  mapa de líneas solo lo pide el comprobador de tipos, porque todos lo traen. Hasta llegar
  ahí, la mutación quitó cuatro reglas que sobraban y dio una prueba a cada regla que no
  la tenía.
- **El corte, también en la sesión**: 8 000 textos al azar, la mitad con marcas, cada
  uno troceado de 42 maneras, sin una diferencia con el texto entero; y 3 000 bloques de
  código al azar, con líneas que parecen rayas sin serlo, cortados en siete sitios y
  troceados de seis maneras, sin que se dijera una vez el secreto de dentro. Tras la
  ronda 5, con respuestas al azar con citas, listas anidadas, sangrías, tabuladores,
  comillas a media línea, líneas de HTML y saltos de Windows: 32 000, cada una entera y en
  dos principios, troceada de cinco maneras, sin una diferencia con la entera y sin decir
  nada de lo que CommonMark o la ventana tienen por código.
- **Lo que tarda, con los dobles**: PA-R03-09 da un P95 por debajo de 200 ms en 20 turnos,
  con la charla de la 0.2 dentro; la cifra de verdad la da `sirius-oye` en E-R03-02.
- **Piper, en el contenedor**: `piper-tts` 1.8.0 se instala con el extra, importa y pasa
  español a fonemas sin red. La voz no se ha podido bajar ni cargar aquí
  (huggingface.co responde 403) ni hay altavoz: que suene lo mira E-R03-01 en su
  ordenador.
- **El candado**: `uv lock` añade `piper-tts` 1.8.0 y `pathvalidate` 3.3.1, del extra, y
  en la ronda 5 `markdown-it-py` 4.2.0 y `mdurl` 0.1.2, con licencia MIT, y no cambia
  ninguna versión que ya estuviera; Quality no instala el extra.

## Consecuencias

- **Mientras contesta no escucha**, desde que cierra el micro hasta que el altavoz calla,
  y al cerrarlo se tira lo que nadie leyó: lo que él diga desde que acaba su turno hasta
  que Sirius empieza a hablar también se pierde. Si Sirius no tiene nada que decir, el
  micro no se cierra y lo que llegó se atiende, como en la pieza B. Oírle mientras habla
  es la pieza E.
- **La charla gana `on_completed`**, que solo usa la voz; la ventana sigue igual. Lo que
  la charla hace después del turno, el resumen, sigue dentro de `send_message`: la voz ya
  no lo espera para hablar, pero el micro no se vuelve a abrir hasta que acaba.
- **El conductor de la 0.3** enchufa la voz y el altavoz de mentira por la raíz de
  composición de producción, que les da a cargar el modelo de la voz de los ajustes: el
  nombre de ese fichero es la voz con que suena. Pone también los dos ficheros de la voz
  donde los deja la orden de instalar, y `quita_los_modelos_de_voz` los quita.
- **La prueba de PA-R03-09**, escrita en la pieza A, contaba con que el turno n diría la
  respuesta n del modelo grabador. La charla de la 0.2 le pide un resumen en el turno 18,
  y el resumen se lleva una; ahora mira que dijo lo que escribió, con lo que guardó la
  charla. Lo que mide, del final de su voz al primer sonido, no cambia.
- **Una frase sale cuando asoma lo que la sigue**, no al llegar su blanco: el corte
  necesita verlo para saber que no la cambia. Troceadas como las da el modelo, palabra a
  palabra con su blanco delante, las 18 respuestas de la prueba sacan la primera frase
  igual que el corte de `e41ff85f` en 11 y un trozo más tarde en 7 (en 6 antes de la
  ronda 5): cuando lo que sigue es una viñeta, un guion con sangría, un número de lista,
  la línea que abre un bloque de código, una raya o una puntuación.
- **Una dependencia nueva**, `markdown-it-py`, para saber qué es código: pura en Python,
  sin red, y la voz lee con ella los bloques de toda la respuesta en cada trozo que llega;
  con una respuesta de 2 730 caracteres tarda 0,43 ms.
- **La voz y la ventana no leen el código igual en todo**, porque la ventana separa sus
  bloques con una regla que no es CommonMark. La voz no dice lo que cualquiera de las dos
  tiene por código: lo que sigue a una raya que para CommonMark abre un bloque sin cerrar
  no se dice aunque la ventana lo enseñe como texto, y lo que la ventana enseña como
  bloque tampoco, aunque CommonMark no lo vea. Que la ventana lea como CommonMark no es de
  esta vertical.
- Model Studio no cambia: `prepare_speech_text` se usa tal cual. Pero la voz ya no lee
  igual que él los bloques de código: Model Studio empareja tres comillas estén donde
  estén, y si una línea de código las trae, lee lo que sigue, como enseñó la ronda 4 de
  Codex. Es un fallo de Model Studio que esta pieza no arregla, porque no es de esta
  vertical.

## Alternativas descartadas y por qué

- **Decirla entera al acabar** (opción 1): incumple PA-R03-02.
- **La tubería de salida de Pipecat** (opción 3): su transporte no tiene rueda para
  Python 3.14 en Windows, y la pieza B ya decidió el bucle propio.
- **Decir la última frase cuando `send_message` vuelve**: es lo que había al principio, y
  la hacía esperar al resumen de la charla (H-243).
- **Guardar lo que llegó mientras pensaba y atenderlo después de hablar**: lo que había en
  el micro al cerrarlo puede ser un turno a medias, cortado al cerrar, y saldría a la
  charla una frase que él no acabó. Se tira, como hace el micro de la pieza B al cerrar.

## La lección

- familia: `modelo-dentro-del-turno`
- sin esto se repetiría: esperar a que `send_message` vuelva para hacer lo que toca en
  cuanto acaba la respuesta. Dentro del turno la charla aún resume la conversación con el
  mismo modelo, otra petición que tarda segundos, y la voz se habría callado ahí antes de
  su última frase cada pocos turnos, y las respuestas de una sola frase, enteras. La
  ventana no lo nota porque escribe lo que llega; la voz sí, y lo notarían la ventana que
  habla de la pieza D y cortarle de la E. Lo cazó la prueba de PA-R03-09 al pasar por
  primera vez: el resumen del turno 18 se llevaba una respuesta del modelo grabador (H-243).
- lo hace cumplir: `tests/integration/test_send_message.py`

## Revisión externa

Alcance, escrito antes de la primera petición: esta PR trae la pieza C y nada más. Mira
que diga lo que escribió desde la primera frase, con una voz de Piper en español de
España, sin marcas ni código; que su propia voz no abra un turno; que nada salga del
ordenador ni se baje solo; que lo que falle al hablar no tumbe a quien escucha; y que
`sirius-oye` hable. No trae la ventana ni a quién le hablan (D), ni cortarle (E).

**Revisión propia**, antes de la primera petición (regla del propietario del
13-10-2026):

- **Vuelta 1.** Encontró que la última frase de cada respuesta esperaba al resumen de la
  charla (H-243 y la lección, arriba), una línea que no hacía nada en `start`, dos
  pruebas que no miraban todo lo que decían mirar y las cuatro mutaciones que
  sobrevivían. Todo arreglado, cada cosa con la prueba que la ve.
- **Vuelta 2.** Nada que cambie lo que hace: dos descripciones de pruebas y un
  comentario del conductor, puestos al día con la pieza C.
- **Vuelta 3**, sobre los arreglos de la ronda 1 de Codex. Un caso nuevo de la prueba de
  los troceos falló con el código bueno: `Hola. ... Adiós.` entero da `Hola.. Adiós.`, y
  a trozos, `Hola. Adiós.`. Buscando por qué salieron más de la misma familia que el
  hallazgo del corte, un trozo preparado fuera de su sitio: una puntuación detrás de los
  blancos, que el texto entero pega a la frase de antes, y la sangría de una línea, que
  dice si un guion es una viñeta. Con tres de la misma familia no se parchea: la raíz va
  en la ronda 1, abajo. Y una lección de método: un caso nuevo de una prueba se pasa
  primero con el código bueno, no solo con las mutaciones.

**Ronda 1 de Codex**, sobre `e41ff85f`: tres P2, los tres ciertos y comprobados contra el
código antes de tocarlo.

- **Callar declaraba al altavoz callado con sonido aún en PortAudio**
  (`src/sirius/adapters/audio/local_speaking.py`): vaciaba la cola y daba por acabado lo
  que sonaba, aunque lo que PortAudio ya tenía siguiera saliendo, y un `start` justo
  después habría abierto el micro con su voz aún sonando. Ahora callar solo tira la cola,
  `playing` sigue diciendo que suena hasta que sale lo ya dado y su cola, y `start` no
  abre el micro mientras suene: escucha ya y lo abre al callar, como tras hablar. No se
  aborta el flujo: volver a arrancarlo puede fallar y dejar el altavoz mudo con la cola
  llenándose, y en `sirius-oye` parar es salir. Cortarle en el acto es de la pieza E.
- **La medida de E-R03-02 no contaba la espera al siguiente bloque**: la primera frase
  se daba por sonando al dejarla en la cola, más la latencia del flujo, y entra en
  PortAudio en la siguiente llamada. Ahora el flujo va en bloques fijos de 512 muestras y
  el altavoz dice lo más que tarda: un bloque más la latencia. La cifra no puede quedarse
  corta por eso; puede pasarse de un bloque, 23 ms.
- **El corte trataba como principio de línea lo que seguía a una frase**: con
  `Uno. ---` o `Uno. - dos`, la respuesta entera dice la raya o el guion, y a trozos se
  borraban como si fueran una raya horizontal o una viñeta. El primer arreglo preparaba
  el trozo con una letra delante, y la revisión propia encontró dos casos más de la misma
  familia (vuelta 3). Se fue a la raíz: el corte ya no imita dónde cae cada trozo, sino
  que comprueba que cortar no cambia nada, con las tres condiciones de «Decisión». La
  prueba de los troceos gana los ejemplos de la ronda y otros dos, y hay otra con 500
  textos al azar.

**Ronda 2 de Codex**, sobre `2825637e`, con la pregunta de si el enfoque de los tres
arreglos estaba mal: un P2, cierto y comprobado contra el código, que el propio revisor
marca como llegado tarde por goteo, porque ya estaba en la ronda 1.

- **Al acabar se decía lo que había quedado sin cerrar**: con
  ``Mira:\n```python\nprint('secreto')`` se oía `` `python. print('secreto') ``, porque
  `prepare_speech_text` solo quita bloques y marcas emparejados. Ahora, al acabar, un
  bloque abierto se cierra y se dice que queda en pantalla, y las marcas sueltas que
  abren o cierran una palabra se quitan (`final_speech_text`, en «Decisión»). No es de
  la familia de la ronda 1, un trozo preparado fuera de su sitio: aquí tampoco la
  respuesta entera se cerraba. Con esto, cortar delante de un bloque ya no pide que sea
  la línea que lo abre: cualquier bloque acaba diciendo que queda en pantalla. La nota de
  arranque lo daba por imposible y no lo era: al acabar, lo abierto se decía tal cual.

**Ronda 3 de Codex**, sobre `6d9f60ac`, con la misma pregunta: un P2, cierto y comprobado
contra el código. Con `Lee [la guía](https://ejemplo.org` se decía `Lee [la guía](un
enlace`, y con `Lee [la guía](` quedaba todo: el arreglo de la ronda 2 quitaba el corchete
solo si no había otro que lo cerrara.

**Rondas 2 y 3, la misma familia: se paró a buscar la raíz** (ADR-001, la regla de las
dos rondas). El patrón: al acabar, lo que se ha quedado a medias llega a la voz; la ronda
2 lo vio con un bloque de código y la 3 con un enlace. La raíz: el arreglo de la ronda 2
iba marca a marca, y lo que no estaba en la lista seguía pasando. La decisión: seguir,
con el arreglo en la raíz, que ya no es una lista de marcas sino las cuatro
construcciones con cierre que quita `prepare_speech_text`, cada una tratada como si se
cerrara (en «Decisión»). Lo hacen cumplir dos pruebas nuevas en
`tests/unit/test_speech_cutter.py`. Una para cada respuesta de la prueba en cada carácter,
como si el modelo acabara ahí, y mira que no se diga ninguna marca; la primera vez que
corrió encontró lo que ninguna ronda había visto, una marca de énfasis colgando al final
(`Mira **`, `Un _`). La otra falla si `prepare_speech_text` gana o pierde una
construcción, hasta que `final_speech_text` diga qué hace con ella a medias. Y la
comparación al azar con el texto entero encontró que una estrella al principio de lo que
queda se juzgaba sin el blanco que tiene delante en la respuesta entera; ya no.

**Ronda 4 de Codex**, sobre `5adbee3a`, con la misma pregunta: dos P2, ciertos y
comprobados contra el código. Tres comillas dentro de una línea de código cerraban el
bloque y se leía lo de después: con un bloque abierto que traía `print("``` dentro")` y
luego `password = "secreto"`, se oía la contraseña, al acabar y también a media charla. Y
dos estrellas entre letras, como en `Mira a**muy`, se quedaban por si eran una
multiplicación.

**Tercera ronda de la misma familia: la raíz de la ronda 3 no era toda la raíz.** El
patrón sigue: lo que la preparación no reconoce como una construcción llega a la voz.
Tratar las construcciones como si se cerraran estaba bien, pero se fiaba de cómo las
reconoce `prepare_speech_text`, que empareja tres comillas estén donde estén, y eso no es
Markdown: hasta con la respuesta entera y cerrada, Model Studio lee lo que sigue a unas
comillas dentro de un bloque. La raíz está en dónde se reconoce un bloque, y se arregla
ahí: la voz los reconoce como Markdown, por su raya al principio de línea, y lo de dentro
no llega nunca a la preparación. Lo hacen cumplir una prueba con cinco bloques que no se
cierran donde parece, cada uno troceado de 52 maneras, y en la sesión 3 000 bloques al
azar. La comparación al azar con el texto entero encontró dos desajustes del propio
arreglo, unas comillas a media línea tomadas por raya tras un corte y dos guiones bajos
dichos a media charla, y los dos tienen su prueba.

**Ronda 5 de Codex**, sobre `ab072f93`, con la misma pregunta: un P2, cierto y comprobado
contra el código, que la revisión propia había encontrado mientras tanto también con
listas. Un bloque dentro de una cita, con sus líneas empezando por `> `, no se reconocía
y se decía lo de dentro: ``> ```python\n> password = "secreto"\n> ``` `` daba
`python. password = "secreto".`, y en `5adbee3a` no. Lo mismo dentro de una lista
sangrada con cuatro blancos.

**Cuarta ronda de la misma familia: la raíz eran las reglas propias.** El patrón de las
rondas 2 a 5: lo que la voz no reconoce como código llega a la preparación. Cada arreglo
afinaba una regla escrita aquí, para el bloque cerrado, el abierto o la raya a media
línea, y la ronda siguiente encontraba la construcción de Markdown que la regla no veía:
Markdown tiene citas y listas, y con ellas sangrías que cambian de sentido. La decisión:
dejar de escribir reglas. Qué es código lo dicen un analizador de CommonMark de verdad,
`markdown-it-py`, sobre toda la respuesta llegada, y la regla con la que la ventana separa
sus bloques, que una prueba comprueba que es la misma; la voz no dice lo que cualquiera de
los dos tiene por código. Lo hacen cumplir una prueba con 150 respuestas al azar que
pregunta a los dos qué es código y compara con la respuesta entera, y en la sesión 32 000
textos al azar. Antes de darlo por bueno, el arreglo tuvo seis fallos propios, cinco
encontrados por esos textos y uno por una prueba que ya había, todos de cortar antes de
saber qué es código: delante de unas comillas que luego
no abrían nada; tras un «1. » cuya línea abría luego un bloque, o tras el primero de dos
números; entre las dos rayas de la marca de un bloque; con unas comillas sobrantes que
sumaban tres con las de otro bloque; y con un bloque entero por detrás que hacía parecer
seguro lo de delante. Cada uno tiene su prueba.

**Ronda 6 de Codex**, sobre `9a453efb`, con la misma pregunta: un P2 que no se acepta,
comprobado contra el código y contra lo aprobado. Pide que la voz calle también el código
en línea, como `` `rm -rf /` ``, porque CommonMark lo tiene por código. Pero la prueba de
aceptación de PA-R03-02 fija que lo dicho es lo escrito preparado por
`prepare_speech_text`, sin quitar ni añadir nada (`tests/acceptance/test_robot_0_3_voz.py`),
y esa función conserva a propósito lo de dentro del código en línea, porque es parte de la
frase: sin él, «Instálalo con `pip`.» se oiría «Instálalo con.». El «sin código» de
PA-R03-02 son los bloques, que la ventana enseña aparte y la voz dice que quedan en
pantalla. Callar el código en línea cambiaría lo que Sirius dice, una decisión de producto
que no es de esta pieza. No es de la familia de las rondas 2 a 5: no encuentra un caso
que el reconocimiento del código no vea, sino que pide cambiar qué se dice.
