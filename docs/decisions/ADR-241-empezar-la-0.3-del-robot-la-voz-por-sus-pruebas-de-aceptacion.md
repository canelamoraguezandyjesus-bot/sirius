# ADR-241 — Empezar la 0.3 del robot, la voz, por sus pruebas de aceptación

- Estado: APROBADO
- Fecha: 2026-10-13
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). El plan que ejecuta lo aprobó el
  propietario el 06-10-2026 (ADR-232). El 13-10-2026 pidió seguir con lo demás del plan
  mientras sus pruebas de la 0.2 esperan a que esté delante de su ordenador:
  «preferiría avanzar con todo lo demás que tenemos que hacer y dejar eso para después».

Este ADR es además la **nota de arranque** de la rama
`claude/la-0-3-del-robot-la-voz-empieza-por-sus-pruebas-de-aceptacion` y de la versión
0.3 de `docs/evolution/PLAN_DEL_ROBOT.md` (skill `disciplina-evidencia`): las cuatro
preguntas y el criterio de parada están escritos antes del primer cambio de código de la
voz y antes de cualquier revisión.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** Hoy la única voz de Sirius es la de
   Model Studio: por turnos, con un botón para hablar y por OpenAI
   (`src/sirius/application/studio_voice.py`, `src/sirius/adapters/audio/openai_speech.py`,
   `src/sirius/adapters/audio/openai_transcription.py`). Su puerto de captura lo dice en
   su propio contrato: «No existe escucha permanente ni palabra de activación»
   (`src/sirius/ports/audio_capture.py:9-10`). El plan pide lo contrario para el robot
   (§5): escucha siempre, todo en local, en tiempo real y dejándose cortar. El arreglo:
   una tubería de voz nueva para el robot, aparte de la de Model Studio, que se queda
   como está (§11 del plan). La tubería oye en local y entrega lo oído a la misma charla
   de la 0.2, la que monta la semilla, la memoria y los modos en cada turno, y dice la
   respuesta con Piper, frase a frase desde la primera. **¿Puede el sitio del arreglo
   observar el fallo?** Una parte sí: que lo oído llegue a la charla como un mensaje
   más, que nada salga ni se guarde, que espere al detector de turno y que se deje
   cortar lo ven las pruebas con dobles. La otra no: que le entienda, que no le corte a
   destiempo, que no conteste a la tele y que la voz le guste solo se oye en su
   ordenador, con su micro y su altavoz. Por eso cada «terminado cuando» de la 0.3
   tiene su evaluación del propietario, con el umbral fijado hoy.
2. **Qué NO garantiza.**
   - Las pruebas de máquina usan dobles que llevan escrito lo que suena. Demuestran
     dónde llega lo oído y qué se dice, no que el oído o la voz de verdad acierten.
   - En el contenedor de las sesiones no hay micrófono, altavoz ni gráfica. Los 1,5 s,
     el corte, los 20 minutos y la tele se miden en su ordenador.
   - Que todo quepa en sus 6 GB de gráfica. Es el riesgo del plan (§10,
     `docs/evolution/PLAN_DEL_ROBOT.md:324-325`): se mide el día uno y, si no cabe, el
     oído y la voz van al procesador.
   - Que Pipecat funcione en su Windows. Aquí se ha comprobado que se instala para
     Windows con Python 3.14 (abajo); que funcione se ve el día uno (§10,
     `docs/evolution/PLAN_DEL_ROBOT.md:329`).
   - Que la cancelación de eco por software baste para cortarle. Si no basta, el micro
     de unos 60 € del plan es dinero y se le pregunta.
   - Que la voz de personaje con Chatterbox pueda hablar en vivo con la charla cargada.
   - En 0.3 Sirius sabe que le hablan a él por su nombre y por el contexto. Reconocerle
     por la voz y saber si le miran llegan en 0.4.
3. **Criterio de parada**, fijado antes de ver ninguna medida ni ninguna revisión:
   - **Las evaluaciones**, E-R03-01 a E-R03-06, con sus umbrales en
     `docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md`, fijados hoy. Si el día uno la tubería no
     arranca en su Windows (E-R03-01), no se sigue con la pieza siguiente: se busca la
     raíz, otro transporte de audio o un proceso aparte, y se vuelve a medir. Si cortarle
     falla con la cancelación por software (E-R03-03), se para y se le pregunta por el
     micro, porque es dinero. Si la voz que elige no puede hablar en vivo (E-R03-06), se
     le dice la cifra y se le pregunta, porque es producto.
   - **Las PR de la 0.3**: cadena de comprobación verde, una ronda limpia de Codex sobre
     el head de contenido y Quality en verde. Dos rondas seguidas con la misma familia: se
     deja de parchear y se busca la raíz. Al escribirse esto decía además, copiado de
     ADR-233, «como mucho tres rondas por PR, y lo cierto de la tercera se corrige en un
     solo commit y se fusiona sin cuarta»; el propietario retiró ese tope el 13-10-2026,
     tras la ronda 3 de esta PR, y lo que rige desde entonces está en «Revisión externa»,
     en «El criterio cambia el 13-10-2026».
   - **El orden del plan.** La §2 dice que cada versión acaba con una prueba del
     propietario «y sin ella no se pasa a la siguiente»
     (`docs/evolution/PLAN_DEL_ROBOT.md:56`). La 0.3 empieza hoy por su palabra del
     13-10-2026, y las cinco evaluaciones de la 0.2 siguen debidas: ni la 0.2 ni la 0.3
     están terminadas hasta que pasen. Se le dan en lote cuando esté delante del
     ordenador, con las del día uno de la voz.
   - Si una pieza pide dinero o cambia el producto, se para y se le pregunta.
4. **Qué lo haría imposible.**
   - **Que el audio salga del ordenador.** Los ajustes de la voz del robot no tienen
     dónde poner una dirección: el oído y la voz son modelos dentro del proceso, y la
     única opción es este ordenador. Una prueba lo mira, y otra vigila que ningún turno
     de voz abra una conexión (PA-R03-08).
   - **Que guarde audio.** Los sonidos viven en memoria mientras se procesan y la base
     no tiene columna para ellos. Durante un turno de voz, un vigilante apunta cualquier
     fichero que algo abra para escribir que no sea la base, los ajustes o el diario, y
     cualquier conexión; al acabar se buscan además ficheros de audio nuevos y audio en
     la base (PA-R03-05 y PA-R03-08).
   - **Que lo que no es para él entre en su memoria.** Se descarta antes de llegar al
     modelo y antes de guardarse (PA-R03-05 y PA-R03-06).
   - **Que se oiga a sí mismo.** Lo que suena por el altavoz y vuelve por el micro no
     empieza un turno, ni antes de la cancelación de eco ni después (PA-R03-03).
   - **Lo que no se puede hacer imposible:** que entienda cada frase, que acierte cada
     final de turno y que tarde poco con su gráfica. Se hace improbable con Smart Turn,
     con el streaming frase a frase y con las medidas del propietario.

## Contexto y problema

La 0.2, «Sirius en texto: personalidad y memoria», está programada entera: sus 18 PA
están en verde desde la PR #685 (ADR-240) y lo que le queda son las cinco evaluaciones
del propietario, E-R02-01 a E-R02-05, que necesitan su ordenador. El 13-10-2026 dijo que
las deja para cuando llegue a casa y que prefiere avanzar con lo demás.

Lo siguiente del plan es la 0.3, «Voz» (§5): una tubería de voz en tiempo real con
Pipecat; oír en local con Silero, Smart Turn y faster-whisper; hablar en local con
Piper en español de España; escucha siempre, con indicador y botón de silencio y sin
guardar audio; saber cuándo le hablan a él; dejarse cortar, primero sin escuchar mientras
habla y después con cancelación de eco por software; y elegir su voz a ciegas. Termina
cuando tarda menos de 1,5 s, se le puede cortar, aguanta 20 minutos de charla y no
contesta a la tele.

La §3 del plan pide, antes de la primera línea de código de la versión, sus pruebas de
aceptación: con pytest lo que una máquina puede comprobar y, como evaluación humana, lo
que solo puede juzgar el propietario. La §10 añade tres riesgos que hay que mirar al
empezar: que las piezas de voz existan para Python 3.14, que Pipecat funcione en Windows
y qué cabe en los 6 GB de su gráfica. Y el plan mismo pide, antes de instalar una
herramienta, comprobar que sigue existiendo y cuál es su licencia
(`docs/evolution/PLAN_DEL_ROBOT.md:10-12`).

## Opciones consideradas

1. **Esperar a sus pruebas de la 0.2 antes de tocar la 0.3**, que es la letra de la §2.
   Deja las sesiones paradas los días que él tarde en sentarse al ordenador, y él pidió
   lo contrario.
2. **Empezar la 0.3 como se empezó la 0.2**: comprobar primero que las herramientas
   existen, su licencia y que se instalan con nuestro Python en un Windows, y después la
   nota de arranque y las pruebas de aceptación, antes del código. Las evaluaciones de
   la 0.2 quedan debidas y se le dan en lote.
3. **Hacer antes lo que queda de la 0.2 sin él**: retirar el banco de 47 casos y el
   código muerto del etiquetado por categorías, que ADR-238 dejó para cuando el banco
   de 100 pase en su ordenador. Es limpieza, no avanza el plan, y espera a E-R02-04.

## Decisión

Se adopta la opción 2.

**Las herramientas del plan, comprobadas el 13-10-2026** contra PyPI, con sus ficheros
de distribución y una resolución de dependencias para Windows x86_64 con Python 3.14 y
con 3.13 (`uv pip compile --python-platform x86_64-pc-windows-msvc`):

| Pieza del plan | Qué hay | Licencia | Con Python 3.14 en Windows |
|---|---|---|---|
| Pipecat | `pipecat-ai` 1.12.0, Python puro, `requires-python >= 3.11`, con marcadores propios para 3.14. Trae dentro Silero VAD y Smart Turn v3.2 como modelos ONNX, sin descargas | BSD-2-Clause | Se resuelve entero: 69 paquetes con rueda, `onnxruntime` 1.24.4, `numba` 0.68, `llvmlite` 0.50 incluidos |
| Silero VAD | El ONNX que lleva Pipecat. El paquete `silero-vad` 6.2.3 de PyPI exige `torch`, y no hace falta | MIT | Dentro de Pipecat |
| Smart Turn v3 | El modelo `smart-turn-v3.2-cpu.onnx` que lleva Pipecat | BSD-2-Clause | Dentro de Pipecat |
| faster-whisper | 1.2.1, el extra `whisper` de Pipecat; `ctranslate2` 4.8.3 y `av` 19 | MIT | Ruedas cp314 y abi3 |
| Piper | `piper-tts` 1.8.0, del proyecto `piper1-gpl`, el extra `piper` de Pipecat. Voces es_ES masculinas: `davefx`, `sharvard`, `carlfm`, `mls` | **GPL-3.0-or-later**; cada voz declara la suya en su ficha | Rueda abi3 para Windows |
| Chatterbox | `chatterbox-tts` 0.1.7. Con 3.14 pide `torch >= 2.9` y fija `transformers` 5.2, `diffusers` 0.29 y `gradio` 6.8 | MIT | Pesado y con la gráfica: solo para generar la voz de personaje aparte |

Dos cosas que salen de esa comprobación y que el plan no sabía:

- **El transporte de audio de Pipecat no sirve.** Su extra `local` es `pyaudio` 0.2.14,
  que no tiene rueda para Python 3.14 en Windows (las últimas son cp312): instalarlo
  obligaría a compilar PortAudio en su ordenador. La entrada y la salida de audio las
  pone Sirius: con QtMultimedia, que ya usa para Model Studio, o con `sounddevice` 0.5.6
  (MIT, rueda `py3-none-win_amd64` con PortAudio dentro). Lo decide la pieza B midiendo
  las dos; la tubería no cambia.
- **Piper es GPL.** Sirius no se distribuye: su licencia es de lectura pública y uso
  reservado (`LICENSE:3`), así que la GPL no obliga a nada hoy. Queda escrito: si algún
  día se distribuyera, Piper iría en un proceso aparte o se cambiaría de voz. Las
  voces se eligen a ciegas de todos modos (pieza F).

**El orden de la 0.3**, una PR por pieza, cada una con sus pruebas de aceptación pasando
de esperadas a verdes:

| Pieza | Qué trae |
|---|---|
| A | Esta nota y las pruebas de aceptación de toda la 0.3, antes del código |
| B | Oír en local: la tubería con Silero, Smart Turn y faster-whisper; lo oído entra en la charla como un mensaje más; nada sale del ordenador; si falta un modelo, dice qué orden ejecutar. Con ella, el día uno del propietario (E-R03-01) |
| C | Hablar en local con Piper en español de España, frase a frase desde la primera; su propia voz no se toma por suya |
| D | Escucha siempre: el indicador y el botón de silencio en la ventana, nada de audio guardado, y cuándo le hablan a él |
| E | Cortarle: la cancelación de eco por software y la interrupción |
| F | Elegir su voz a ciegas, con las de Piper y una de personaje con Chatterbox |

**Las pruebas de aceptación** se llaman `PA-R03-NN` y viven en
`docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md`: 10, con 27 pruebas de máquina y seis
evaluaciones del propietario, E-R03-01 a E-R03-06, con sus umbrales fijados antes de
medir. Salieron del §5 cláusula a cláusula, también de «Con qué», «No se usa», «Dinero»
y los riesgos del §10, que es la lección de las rondas 2 y 3 de ADR-233; lo que ninguna
prueba puede ver está en «Lo que estas pruebas no garantizan».

- **Hablan como el plan.** Las pruebas de máquina, en `tests/acceptance/test_robot_0_3_*.py`,
  dicen «el propietario dice por voz», «Sirius se calla», «la tele». Solo el conductor,
  `tests/acceptance/conductor_robot_0_3.py`, sabe cómo se hace cada cosa en el código.
  Es el conductor de la 0.2 con el oído y la voz encima: hereda la charla, la semilla, la
  memoria y la ventana, montadas como en producción, y pone dobles solo donde iría el
  micro, el oído, el transcriptor, la voz y el altavoz; el modelo de la charla es el
  grabador de la 0.2 con reloj. Los dobles llevan escrito lo que suena, en vez de ondas,
  y un reloj de mentira mide cuánto hace que acabó la charla.
- **Los dobles hacen algo, y apuntan lo que hacen.** El micro lee, el oído dice cuándo
  acaba el turno, el transcriptor transcribe, la voz dice, el altavoz suena y el modelo
  contesta; cada uno apunta lo que hizo, con su momento, en el acto de hacerlo, y esos
  registros solo se leen. Quien implementa una pieza escribe también su parte del
  conductor, así que un registro que rellenara el conductor no probaría nada. Lo que la
  tubería recibe del micro no dice quién habló ni con qué voz, como en un micro de verdad:
  el eco de Sirius solo se aparta cerrando el micro mientras habla o cancelándolo contra
  lo que suena, nunca por una etiqueta. Lo que el conductor ya sabe hacer, leer la charla
  y el audio de la base y la charla de la ventana, se lee de la base y de la ventana de
  verdad, no se le pide a la pieza. `tests/acceptance/test_dobles_del_conductor.py` lo
  comprueba hoy, con el conductor construido de verdad, porque una prueba en `xfail`
  estricto no ejecuta ni una línea de él.
- **El mecanismo de las piezas se comparte.** ADR-233 decía que la versión siguiente
  copiaría el conductor con el arreglo dentro. En vez de copiarlo, el mecanismo sale a
  `tests/acceptance/piezas_del_robot.py` y la comprobación de la tabla a
  `tests/acceptance/trazabilidad_del_robot.py`; el conductor y la comprobación de la 0.2
  los usan sin cambiar de comportamiento, y las tablas rotas a propósito de la 0.2 siguen
  alimentando la misma comprobación, con una más: una prueba de una pieza que no es de la
  versión.
- **El inventario aprobado no se reduce**: 10 PA, 27 pruebas y seis evaluaciones viven en
  `tests/acceptance/test_robot_0_3_trazabilidad.py`, como en la 0.2.
- **Lo que las pruebas fijan y el código tendrá que cumplir**: lo que se ve en la ventana
  («Escuchando», «En silencio», el botón de silencio y la charla por voz con sus dos
  botones); los nombres de las herramientas (`silero`, `smart-turn`, `faster-whisper`,
  `piper`) y una voz `es_ES-`; que la tubería de Sirius añada menos de 200 ms en el P95
  de 20 turnos con dobles instantáneos; que se calle en menos de medio segundo; que lo
  que no es para él no llegue al modelo ni a la base; y que sin su nombre solo le hable
  mientras dura la charla, con los segundos que fije la pieza D y que la prueba lee del
  código.

**Lo que sigue debido de la 0.2**, en lote para cuando esté delante del ordenador:
E-R02-05 y E-R02-04 con sus dos órdenes, E-R02-01 con los modelos de la charla y la
prueba a ciegas, E-R02-02 con sus 50 marcas y E-R02-03 con las 40 preguntas trampa. La
ronda 3 de Codex sobre la PR #685 fue limpia, sobre `a7c1f959`, y ADR-240 lo recogerá en
la misma PR que anote sus cifras.

## Comprobación que la sostiene

- La única voz de hoy es por turnos y por OpenAI: `sed -n 5,13p src/sirius/ports/audio_capture.py`
  enseña la frase citada en la nota, y
  `ls src/sirius/adapters/audio/` da `openai_transcription.py`, `openai_speech.py`,
  `qt_capture.py`, `qt_playback.py`, `winsound_playback.py`, `fake.py` y
  `unconfigured.py`: ningún oído ni voz local.
- Las herramientas: consultas a `https://pypi.org/pypi/<paquete>/json` el 13-10-2026,
  con la versión, la licencia, las dependencias y los ficheros de cada una, y
  `uv pip compile --python-version 3.14 --python-platform x86_64-pc-windows-msvc` sobre
  `pipecat-ai[whisper,piper,local]==1.12.0`: 69 paquetes, con `pyaudio` resuelto solo
  como fuente (sus ruedas para Windows llegan hasta cp312). Lo mismo con 3.13. Los
  ficheros de Pipecat 1.12.0 que lo dicen, leídos de su repositorio:
  `services/piper/tts.py` (carga `piper-tts` en el proceso y avisa de su GPL),
  `services/whisper/stt.py` (`faster-whisper` en el proceso, `device` y `compute_type`
  configurables), `transports/local/audio.py` (`pyaudio`),
  `audio/turn/smart_turn/local_smart_turn_v3.py` (modelo ONNX dentro del paquete) y
  `audio/vad/silero.py` (`silero_vad.onnx` dentro del paquete).
- Nadie más trabaja en estos ficheros: el 13-10-2026 la API de GitHub devolvió 0 PR
  abiertas, y `main` no se había movido desde la PR #685 del 08-10-2026.
- Las 27 pruebas de máquina se ven fallar por la razón esperada:
  `uv run --no-sync pytest -q tests/acceptance/test_robot_0_3_voz.py tests/acceptance/test_robot_0_3_ventana.py`
  da 27 xfailed, cada una con su pieza; ruff y mypy pasan sobre sus cuerpos.
- La comprobación de la tabla: `tests/acceptance/test_robot_0_3_trazabilidad.py` pasa
  con el documento como está, y las 13 pruebas de `test_robot_0_2_trazabilidad.py`, diez
  de ellas con tablas rotas a propósito, siguen pasando sobre el módulo compartido.
- La batería entera. Sobre `7209d783`, el primer head: 8 194 pasan, 16 saltadas y 28 `xfail`, los 26 de la 0.3 de entonces y los 2 que ya estaban, en 24 min 29 s. Sobre `main` (`d545ff17`) eran 8 181 pasan y 2 `xfail`: entran las esperadas y 13 que pasan, las dos de la trazabilidad de la 0.3, la tabla rota nueva de la 0.2 y las que los guardas de documentos añaden por cada ADR y documento nuevo. Sobre el head de la ronda 1: 8 194 pasan, 16 saltadas y 29 `xfail`, los 27 de la 0.3 y los 2 que ya estaban, en 25 min 40 s. Sobre el head de la ronda 2: 8 198 pasan, 16 saltadas y 29 `xfail`, en 23 min 44 s; las 4 que entran son las 3 del vigilante y la que los guardas añaden por el fichero nuevo. Sobre el árbol de la ronda 3 y H-241, `56017da1`: 8 199 pasan, 16 saltadas y 29 `xfail`, en 23 min 10 s. Sobre el árbol de la revisión propia, con sus cinco pasadas: 8 211 pasan, 16 saltadas y 29 `xfail`, en 22 min 49 s; las 12 que entran son las 10 de los dobles, la cuarta del vigilante y la que los guardas añaden por el fichero nuevo. Sobre el árbol de la ronda 4 y su mirada propia: 8 212 pasan, 16 saltadas y 29 `xfail`, en 21 min 34 s; la que entra es la del eco mezclado con la voz. Sobre el árbol de la ronda 5 y su mirada propia: 8 212 pasan, 16 saltadas y 29 `xfail`, en 21 min 23 s. Sobre el árbol de la ronda 6, sus ojos frescos y su mirada propia: 8 214 pasan, 16 saltadas y 29 `xfail`, en 20 min 4 s; las 2 que entran son la del vigilante sobre las sentencias y la de las filas de los dobles. Sobre el árbol de la ronda 7: 8 215 pasan, 16 saltadas y 29 `xfail`, en 20 min 44 s; la que entra es la del diario de los dobles. Sobre el árbol de la ronda 8: 8 215 pasan, 16 saltadas y 29 `xfail`, en 20 min 13 s. Y la línea base de la charla escrita, `di()` solo, en la nube el 13-10-2026: 34 ms en el P95 de 20 turnos, 25,7 ms la mediana y 57,7 ms el máximo.

## Consecuencias

- La batería lleva 27 pruebas `xfail` estrictas de la 0.3 hasta que entre cada pieza. Se
  suman a las dos de M11, que siguen como estaban.
- Las pruebas fijan nombres que todavía no existen en el código: los del conductor, los
  de la ventana y los de las herramientas. Si una pieza necesita cambiar una prueba, el
  cambio se dice en su PR, y nunca para aflojarla.
- El propietario tiene por delante, cuando esté en el ordenador, las cinco evaluaciones
  de la 0.2 y, cuando entre la pieza B, el día uno de la voz: instalar la tubería, bajar
  los modelos una vez y medir qué cabe en su gráfica.
- La pieza B decide entre QtMultimedia y `sounddevice` para el micro y el altavoz, con una
  medida, y trae la orden que instala y mide.
- La voz del robot no toca Model Studio: dos voces, una por turnos y por OpenAI para
  grabar, y otra local y siempre escuchando para el robot.

## Alternativas descartadas y por qué

- **Voz a voz en la nube.** El plan lo descarta: ata a un proveedor y no deja meter su
  memoria ni sus gestos. Las pruebas lo miran como comportamiento, no como guarda
  (PA-R03-08).
- **El transporte de audio de Pipecat.** Sin rueda de `pyaudio` para Python 3.14 en
  Windows, obligaría a compilar en su ordenador.
- **El paquete `silero-vad` de PyPI.** Trae `torch`; Pipecat ya lleva el mismo modelo en
  ONNX.
- **Esperar a las evaluaciones de la 0.2.** Son suyas, no de las sesiones, y él pidió
  avanzar. Quedan debidas, no olvidadas.
- **Copiar el conductor de la 0.2 entero.** Dos copias del mismo mecanismo se separan a
  la primera corrección; se comparte lo que es igual y se hereda lo demás.

## La lección

- familia: `prueba-que-no-puede-ver-lo-que-vigila`
- sin esto se repetiría: escribir las pruebas de aceptación de una versión antes del
  código mirando el resultado final, lo guardado y lo contestado, y aceptando las cifras
  y los recuentos que da el propio conductor; una pieza que atajara las pasaba. Trece
  hallazgos ciertos en tres rondas sobre la PR #686, todos de esa familia, y ADR-233 ya
  había tenido cuatro iguales en su ronda 3. La pregunta que las caza, antes de la
  primera ronda y prueba a prueba: «¿pasaría con una pieza que hiciera trampa?». Y las
  dos reglas que salen de ella: cada prueba mira el camino por los dobles, el sonido por
  el micro, el texto por el transcriptor, la petición por el modelo y la frase por el
  altavoz; y toda cifra la dan los relojes y los recuentos de los dobles, nunca un campo
  que rellene el conductor. Y la raíz que la revisión propia encontró debajo: un doble
  que no hace nada es un cuaderno que rellena el conductor, y el conductor lo escribe la
  pieza; un doble tiene que hacer lo que la tubería le pide y apuntarlo él. Y lo que el
  conductor ya hace necesita una prueba que corra hoy: una en `xfail` estricto no
  ejecuta ni una línea de él, y el conductor de esta PR no se podía ni construir
  durante tres rondas. Y la ronda 6 lo repitió sobre la base, dos veces: una foto del
  final no ve lo que pasó por el camino, y el texto de las sentencias no es lo que se
  escribió; lo que se vigila se vigila mientras pasa, y en las filas, no en lo que se
  dice de ellas. Y la ronda 7 enseñó lo que había debajo de las rondas 4 a 7: la
  pregunta «¿pasaría con una pieza que hiciera trampa?» caza pruebas que miran el
  resultado y no el camino, pero aplicada a una negación sin borde, que nada esconda
  audio en ninguna parte, no tiene final; ahí se escribe el alcance, error y no engaño,
  y el engaño va a la revisión del código de cada pieza.
- lo hace cumplir: ninguna prueba mide la fuerza de una prueba; lo que hay es
  `tests/acceptance/test_vigilante_del_conductor.py`, que impide que el vigilante pase
  en vacío, `tests/acceptance/test_dobles_del_conductor.py`, que construye el conductor
  y comprueba que cada doble apunta en el acto de hacer, y esta lección para quien
  escriba las de la 0.4.

## Revisión externa

- **Ronda 1 de Codex**, sobre `7209d783`: tres hallazgos P2, los tres ciertos y los tres de
  una misma familia: una prueba que no mira lo que dice mirar, y que una pieza podría
  pasar sin cumplirlo.
  - PA-R03-03 decía «ni antes ni después de la cancelación de eco» con una sola prueba de
    la pieza C: al entrar la C, la fila quedaría en verde sin que nadie mirase la E. Ahora
    la fila es de C y E, con una segunda prueba que, con la cancelación de eco y la
    interrupción activas, comprueba que su propio eco no empieza un turno ni le corta, y
    que el propietario sí. El inventario pasa de 26 a 27.
  - PA-R03-10 aceptaba una hoja con `lo_que_ve_el_propietario` vacío: solo miraba que no
    aparecieran los nombres de las voces. Ahora exige cada etiqueta y cada frase en lo que
    se ve, y un botón de escuchar por voz y frase.
  - PA-R03-05 comparaba dos fotos del disco: una captura escrita en un temporal y borrada
    antes de acabar el turno no se veía. Ahora el conductor pone un gancho de auditoría
    de Python que apunta cada fichero de audio, o temporal fuera de la base, que algo abra
    para escribir durante un turno de voz, aunque lo borre después, y la foto del disco se
    mira además al final. Lo que escriba Qt sin pasar por Python no lo ve, y queda escrito
    en «Lo que estas pruebas no garantizan».
  - Familia: nueva en esta PR. Si la ronda 2 la repite, se para y se repasan las 27
    pruebas una a una contra «¿pasaría sin su pieza?», no solo las que señale.
- **Ronda 2 de Codex**, sobre `894cb616`: seis hallazgos P2, los seis ciertos y los seis de
  la familia de la ronda 1; tres de ellos sobre líneas que la ronda 1 ya tenía delante, y
  el propio revisor lo dice.
  - **Regla de las dos rondas.** Se dejó de parchear hallazgo a hallazgo y se buscó la
    raíz: las pruebas miraban el resultado final (lo guardado, lo contestado) y no el
    camino por los dobles, así que una pieza que atajara, metiendo el texto en la charla
    sin oírlo, contestando sin hablar, o contando botones sin que suenen, las pasaba.
    Se repasaron las 27 una a una con la pregunta «¿pasaría sin su pieza, o con una pieza
    que hiciera trampa?», y se endurecieron 21, no solo las seis señaladas: cada una
    comprueba ahora que el sonido pasó por el micro, el texto por el transcriptor, la
    petición por el modelo y la frase por el altavoz, en lo que le toque.
  - Los seis señalados: el vigilante de escrituras excluía todo el directorio de la base,
    y un temporal junto a `sirius.db` se le escapaba; ahora solo deja pasar la base y lo
    que SQLite pone a su lado, los ajustes y el diario, se llame como se llame y esté
    donde esté lo demás. La hoja de voces contaba botones con un entero del propio
    objeto; ahora la prueba pulsa cada botón y comprueba que por el altavoz suena esa
    frase con esa voz. La prueba de la cancelación de eco no demostraba que el micro
    siguiera abierto ni que el eco entrara; ahora exige el micro abierto mientras habla,
    el eco leído por el micro y solo la voz del propietario transcrita, con las dos a la
    vez. «Olvida eso» por voz comprueba antes que lo dicho se guardó. La charla por voz y
    la escrita tienen que llevar los mismos tres ejemplos, como conjunto. Y la locución
    entera se compara con `prepare_speech_text` de lo escrito, no tres trozos.
  - El vigilante ve también cada `socket.connect` durante un turno, así que
    `conexiones_de_red` ya no depende de la pieza B. Que el vigilante ve lo que dice ver
    lo comprueban tres pruebas nuevas fuera de la tabla,
    `tests/acceptance/test_vigilante_del_conductor.py`, con un wav temporal borrado, un
    `os.open`, una lectura que no cuenta, una conexión y una escritura fuera del turno.
  - El inventario sigue en 27. Si la ronda 3 trae la misma familia, se corrige en un
    commit y se fusiona sin cuarta, como fijaba entonces el criterio de parada.
- **Ronda 3 de Codex**, sobre `1b792492`: cuatro hallazgos P2, los cuatro ciertos y los
  cuatro de la misma familia. Se corrigieron en un solo commit, `e5f2a1b5`, y la PR iba
  a fusionarse sin cuarta ronda, como fijaba entonces el criterio de parada. No se
  fusionó, por lo que sigue.
  - La lista de escrituras permitidas comparaba solo el nombre: un `settings.json` o un
    `sirius.db` en otra carpeta pasaba por permitido. Ahora `Permitidas` guarda las
    rutas de verdad de la base, los ajustes y el diario, las compara resueltas, y el
    mismo nombre en otra carpeta cuenta como escritura. Es un defecto que nació del
    arreglo de la ronda 2.
  - E-R03-05 dejaba la llamada de teléfono como opcional, y el plan dice que la tele y el
    teléfono no son órdenes. Ahora la llamada es obligatoria, de al menos 2 minutos y con
    manos libres, dentro de los 10 minutos.
  - Los 200 ms de PA-R03-09 y el medio segundo de PA-R03-07 los daba el conductor, y
    quien implementa la pieza escribe también el conductor. Ahora el micro apunta cuándo
    leyó cada sonido y el altavoz cuándo sonó y cuándo paró, y las pruebas calculan las
    dos cifras con esos relojes; `TurnoDeVoz` ya no lleva tiempos.
  - PA-R03-02 comparaba la locución entera solo con el resumen del turno; ahora también
    con lo que se le pidió a la voz y con lo que sonó por el altavoz.
  - Trece hallazgos ciertos en tres rondas, los trece de la misma familia. De ahí la
    lección de arriba.
- **Revisión propia**, sobre el árbol de `56017da1`, antes de pedir la cuarta ronda y por
  la regla nueva del propietario. Dos pasadas: la mía, prueba a prueba, y la de otro par
  de ojos que no había escrito nada, con la misma pregunta y sin permiso para ejecutar.
  Veintitrés hallazgos del segundo, uno P1, catorce P2 y ocho P3, todos verificados
  contra el código antes de aceptarlos; la mía había llegado antes a la raíz de los P2.
  - **El P1.** El conductor no se podía construir: tomaba la foto del disco antes de que
    el conductor de la 0.2 pusiera la carpeta, y `ConductorDeVoz(tmp_path)` levantaba
    `AttributeError`. Nada en la PR lo ejecutaba: las 27 pruebas sustituyen su cuerpo por
    la pieza pendiente, y las del vigilante usan un testigo. «27 `xfail` por la razón
    esperada», repetido en tres rondas, no decía nada del conductor. Comprobado
    ejecutándolo. Desde ahora `test_dobles_del_conductor.py` lo construye, escribe, reabre
    y cierra de verdad, y comprueba que `oye` levanta la pieza B.
  - **La raíz de los P2, debajo de los trece hallazgos de las tres rondas.** Los dobles
    eran cuadernos sin comportamiento: ni el micro leía, ni el oído decidía, ni la voz
    decía; quién pasaba un sonido de pendiente a leído, qué significaban los silencios
    del detector y con qué reloj se sellaba cada momento lo decidía quien implementara la
    pieza, que escribe también el conductor. «Los relojes de los dobles» de la ronda 3
    los escribía la pieza. Ahora cada doble tiene el método que la tubería llama, apunta
    en él con un solo reloj, y los registros son de solo lectura; la tubería recibe del
    micro un `Audio` sin quién lo dijo, así que el eco no se puede descartar por su
    etiqueta; la voz y el sonido llevan `voz` aparte de `de_quien`, que las dos
    convenciones de PA-R03-02 y PA-R03-10 no cabían juntas; el modelo de mentira apunta
    cuándo acabó y contesta a trozos; `charla_guardada`, `audio_en_la_base` y
    `mensajes()` se leen hoy de la base y de la ventana de verdad; la orden de instalar
    no puede ser vacía; el medio segundo se mide con la respuesta nueva lenta, para que
    callarse no espere a tenerla; la charla sin nombre dura entre 5 s y 2 min; el eco no
    empieza un turno tampoco en los silencios de después; cinco frases distintas y cada
    muestra es la de la hoja; cada candidata, también la de personaje, queda para hablar.
  - **El vigilante** vigila desde que el conductor se construye hasta que cierra, no solo
    dentro de `oye`; ve también los envíos sin conexión y los procesos lanzados; no
    cuenta la pareja de tomas que Python se fabrica en Windows ni escribe bytecode
    mientras existe, porque un `.pyc` de una importación tardía sería una escritura más y
    la regla es no excluir nada por su nombre; y mira el diario, que sí puede escribirse,
    para que lo que no era para él y lo olvidado no acaben ahí.
  - **Lo que se dejó escrito y no se endureció**, porque antes del código no se puede:
    `herramientas()` y `destinos_posibles_de_la_voz()` son lo que declare la pieza, y van
    en «Lo que estas pruebas no garantizan» con E-R03-01 con el wifi apagado; la línea
    base de la charla escrita, `di()` solo, es 34 ms en el P95 de 20 turnos en la nube el
    13-10-2026, así que los 200 ms de PA-R03-09 tienen sitio.
  - **Segunda pasada**, de otro par de ojos frescos sobre el árbol ya corregido, con
    permiso para ejecutar: veintidós hallazgos, uno P1, ocho P2 y trece P3, todos
    verificados. El P1: las dos pruebas de PA-R03-03 no las pasaba a la vez una pieza
    honesta, porque la de la C exigía el eco perdido con el micro cerrado y la de la E el
    eco leído con el micro abierto, y las dos corren cuando entra la E; ahora la de la C
    vale en los dos regímenes, el eco perdido o leído no se transcribe ni empieza un
    turno, y «mientras habla no escucha» queda como lo que la C hace hasta que la E lo
    sustituye, escrito en «Lo que estas pruebas no garantizan». Los demás: el corte se
    mide con el detector tardío y la respuesta nueva lenta, para que callarse no espere
    ni al fin del turno ni a tener la respuesta; «lo que iba a decir queda escrito
    entero» se prueba cortándole con el modelo aún escribiendo, con un gancho del modelo
    de mentira, y exigiendo que el corte llegue antes de que el modelo acabe; «olvida
    eso» mira las peticiones del turno sin el contador privado de `di`; el diario se
    configura como en producción, y se vio de paso que la configuración de Alembic
    (`migrations/env.py`, `fileConfig`) apaga el registrador `sirius` que ya existía, así
    que `sirius.main`, que configura el diario antes de iniciar la persistencia, puede
    tener el diario apagado; queda para una PR aparte con su prueba. Cada muestra de la
    hoja sale de la voz; la voz elegida se comprueba en otro conductor sobre la misma
    base; el indicador y el botón de silencio leen `listening_label` y `mute_button`; el
    vigilante empieza antes de montar Sirius y ve también los procesos de `os`; las
    extensiones genéricas no se buscan en la temporal del sistema; y el `conftest`
    suelta a los vigilantes al acabar cada prueba.
  - **Tercera pasada**, de otro par de ojos sobre el árbol con lo anterior corregido:
    once hallazgos, uno P1, dos P2 y ocho P3, todos verificados. El P1 era mío y de la
    segunda pasada: la prueba de la voz elegida recorría las etiquetas de la primera
    hoja sobre conductores nuevos que nunca la habían preparado, así que la pieza
    perfecta no la pasaba; ahora cada vuelta abre su hoja en el Sirius vivo y busca la
    voz por su nombre. Los P2: del diario solo se reencendía el registrador padre, y la
    migración apaga también cada `sirius.*` de módulo, que es por donde escribe el
    código de producción, así que ahora se encienden todos, también al reabrir, y la
    prueba de los dobles lo mira por un hijo antes y después de reabrir; y el gancho
    del corte disparaba con el primer trozo entregado, no sonado, y una tubería
    concurrente honesta podía fallar según quién llegara antes, así que la prueba
    espera en un hilo aparte, sin retener al modelo, a que la primera frase suene, y
    lo comprueba. Los P3: `acaba()` queda como mando de la prueba, no de Sirius; `Audio` y
    `Sonido` ya no llevan duración, porque el micro de mentira es instantáneo y una
    tubería que le diera ritmo no bajaría de los 200 ms; el bytecode se guarda una
    sola vez; el gancho calla también si el conjunto de vigilados cambia desde otro
    hilo; la hoja exige al menos dos voces de Piper, como dice la fila; y «lo que iba
    a decir queda escrito entero aunque le corten» no está en el plan y es producto:
    se le pregunta al propietario y, hasta que conteste, la prueba fija «entero»,
    escrito en `docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md`.
  - **Cuarta pasada**, solo sobre esas correcciones: dos P2 y dos P3, ciertos. La
    espera del gancho retenía al modelo, así que un cortador de frases que confirma
    con el trozo siguiente no podía sonar hasta que la espera se agotara; y reabrir
    Sirius vuelve a migrar y apagaba el diario otra vez. Corregidos: la espera va en un
    hilo y se comprueba que la frase sonó antes del corte; `reabre` vuelve a encender
    los registradores; las dos voces de Piper se cuentan sin las de Chatterbox.
  - **Mutación**: once mutaciones del conductor, y las once las caza
    `test_dobles_del_conductor.py`: el micro que no apunta lo leído, el oído que acaba en
    el primer silencio, el transcriptor y la voz que no apuntan, el altavoz que no apunta
    el corte y el que no devuelve el eco, el modelo que no apunta cuándo acabó, y la
    charla, el audio y el diario que no se leen de la base y del disco, y la ventana que
    no lee su lista; y una más, el diario que solo enciende al padre.
  - El inventario sigue en 27. Los arreglos van en el commit que trae esta sección; su
    sha queda en H-241 del registro de defectos, que se amplía con esta raíz en el
    commit siguiente: desde ADR-192 cada ADR tiene un solo defecto, el de su número.
- **Ronda 4 de Codex**, sobre `0cc12cdb`, la primera después de la revisión propia: tres
  hallazgos P2, los tres ciertos, dos del vigilante y uno del eco.
  - `audio_en_la_base` solo veía BLOB con cabecera de fichero: una onda cruda, una
    matriz o audio en base64 pasaban, y la base es justo una ruta que el vigilante
    permite. Ahora el conductor toma una foto de la base al arrancar Sirius y compara:
    cuenta un BLOB con cabecera donde sea, un BLOB donde al arrancar no había ninguno,
    también en tablas o columnas nuevas, un texto de más de 16 KiB donde no los había, y
    una tabla virtual nueva; las tablas virtuales del arranque y sus sombras, los
    índices de SQLite, no se miran, porque lo que guarda Sirius está en la tabla real.
    Lo que no ve queda en «Lo que estas pruebas no garantizan».
  - Resolver un nombre ya es una consulta que sale del ordenador, aunque la conexión de
    después no llegue: el vigilante apunta ahora `socket.getaddrinfo`, `gethostbyname` y
    `gethostbyaddr`, salvo las direcciones numéricas, que no se resuelven.
  - En la prueba del corte con cancelación de eco, el eco de la respuesta anterior ya se
    había leído antes de que el propietario hablara: las dos señales no circulaban a la
    vez. Ahora, mientras el altavoz sigue sonando y devuelve eco, el micro capta una
    copia de lo que suena delante de cada cosa que entra, la voz del propietario y cada
    silencio, y la cancelación tiene que apartarlo con la voz mezclada.
  - Los tres son de la familia de siempre, el vigilante o la prueba que no ve lo que
    dice vigilar, y ninguno de las cinco pasadas propias lo vio: la revisión externa
    sigue haciendo falta, y se repite sobre el head nuevo hasta que vuelva limpia.
  - **Mirada propia a estos arreglos**, antes de empujarlos: un P2 y cinco P3, ciertos
    y medidos; quedaron en `dd0b2ab9`, y la ronda 5 enseñó que seguían siendo parches. La foto de la base eximía toda columna declarada BLOB, también la que
    trajera la migración de la propia pieza, y en las pruebas la columna de las
    huellas está vacía al arrancar: ahora solo se exime la columna que ya guardaba
    BLOB. Una tabla virtual nueva era un escondite en sus sombras: ahora cuenta. La
    resolución inversa y enlazar a un nombre no se veían: ahora sí. La copia del eco
    que va detrás de la voz puede leerse con el altavoz ya parado, y queda dicho. Y
    una pieza que descartara todo lo que Sirius dijo alguna vez pasaba: ahora el
    propietario repite «Vale, vale.» con el altavoz callado y tiene que oírse.
- **Ronda 5 de Codex**, sobre `dd0b2ab9`: tres hallazgos P2, los tres ciertos, los tres
  sobre los arreglos de la ronda 4. Segunda ronda seguida con la misma familia, así que
  rige la regla de las dos rondas: se dejó de parchear y se buscó la raíz.
  - **La raíz.** `audio_en_la_base` adivinaba qué era audio por su forma, cabeceras,
    BLOB donde no los había, textos largos, tablas virtuales nuevas, y cada regla
    dejaba un hueco que la siguiente ronda encontraba: la foto tomada después de montar
    Sirius daba por buenas las escrituras del arranque de la propia pieza; una tabla
    `audio(sample INTEGER)` con las muestras como filas no tenía cabecera ni BLOB ni
    texto largo; y una columna que ya guardaba algún BLOB admitía PCM crudo. La
    propiedad que hay que afirmar no es «esto no parece audio», es «la base solo cambia
    como cambia charlando con la 0.2». Ahora el conductor lo comprueba contra el estado
    permitido conocido: las tablas son las de la 0.2, un inventario escrito en el
    conductor (`TABLAS_DE_LA_0_2`), y sus columnas las del modelo de producción; un
    BLOB solo en la columna de las huellas, no mayor que una huella y sin cabecera de
    audio; ningún texto de más de 16 KiB; y ninguna tabla, sombras de los índices
    incluidas, crece más de mil filas desde antes de arrancar Sirius, que es menos que
    un segundo de muestras. Si una pieza necesita una tabla, la añade al inventario y su
    revisión lo ve; el inventario se compara con la base en los dos sentidos cada vez
    que corre `test_dobles_del_conductor.py`, así que una migración que añada o quite
    una tabla lo rompe a la vista. Lo que queda fuera, audio troceado en huellas
    pequeñas o en textos cortos y lo sobrescrito en filas que ya existían, está en «Lo
    que estas pruebas no garantizan».
  - **Mirada propia a estos arreglos**, antes de empujarlos: un P2 y cuatro P3, medidos
    sobre una base real. Las sombras de los dos índices quedaban fuera de todas las
    reglas y cabía audio sin límite: ahora se cuentan y se miran, binarias pero ni
    grandes ni con cabecera; el inventario traía una sombra fantasma y se comparaba en
    un solo sentido; una tabla virtual de un módulo no cargado reventaba la
    comprobación en vez de señalarse; y la convención del eco, por sucesos y no por
    tiempo, quedó escrita en vez de un «un rato» que no la pasaba.
  - **El eco.** El micro recibía el eco y la voz del propietario como dos audios
    seguidos, y una pieza podía descartar el bloque igual a la última locución y
    aceptar el siguiente sin cancelar nada. Ahora, con el altavoz sonando y devolviendo
    eco, lo que el propietario dice llega en un mismo audio con el eco encima, como en
    un micrófono de verdad, y cada silencio llega como eco solo: la cancelación tiene
    que apartar el eco de dentro del audio y dejar pasar solo la voz. Un `Sonido`
    mezclado es de los dos (`de("propietario")` y `de("sirius")`), y la prueba de la
    cancelación exige verlo leído.
- **Ronda 6 de Codex**, sobre `12630472`: dos hallazgos P2, los dos ciertos, los dos sobre
  la base, que es la familia de las rondas 4 y 5: tercera ronda seguida. Lo que se escribe
  en la base y se borra antes de acabar no lo veía nadie, porque `sirius.db` es una ruta
  permitida para el vigilante y la foto final solo ve lo que queda; y la columna de las
  huellas admitía PCM troceado en BLOB de menos de 16 KiB sin cabecera, cuando PA-R03-05
  promete que la base solo guarda texto.
  - **La raíz, esta vez, en dos pasos.** Mirar el estado final no ve el tránsito: la
    propiedad sigue siendo «la base solo cambia como cambia charlando con la 0.2», pero
    hay que mirarla también mientras pasa. El primer arreglo trazó cada sentencia SQL de
    cada conexión abierta mientras el conductor vive, con sus valores puestos, y leyó en
    su texto los BLOB, los textos largos y las filas. Una revisión con ojos frescos sobre
    ese arreglo, antes de empujarlo, lo tumbó con un P1: todo lo que miraba era el texto
    de la sentencia, y con la API corriente de `sqlite3` se escribe sin que el valor esté
    en ese texto: un hueco de `zeroblob` que se rellena a trozos con `blobopen`, una
    función de Python que devuelve el audio dentro de un `INSERT … SELECT`, y una función
    que inserta desde dentro de otra sentencia, que SQLite entrega anidada y sin valores.
    La raíz debajo: mirar las sentencias es mirar lo que se dice que se escribe; hay que
    mirar las filas. Ahora, al acabar de arrancar Sirius, el conductor pone en cada tabla
    de la 0.2 un disparador por insertar, actualizar y borrar, que apunta en una tabla
    del arnés todo BLOB y todo texto de más de 16 KiB con su tamaño y su cabecera,
    también lo que había en la fila al actualizarla o borrarla (que es como se ve lo que
    entró con `blobopen`), y cuenta por tabla las filas insertadas y el texto escrito. Se
    escriba como se escriba, el disparador lo ve; vive en la base, no en una conexión,
    así que ve también lo que escriba una conexión que el trazador no sigue; y quitarlo
    es un cambio de esquema, que el trazador ve. El trazador queda para la estructura:
    cambios de esquema fuera del arranque, otra base escrita, enganchar una base o abrir
    el esquema a mano, tocar las tablas del arnés, apagar los disparadores, una sentencia
    anidada fuera de las sombras de los índices y la conexión que no pasó por
    `sqlite3.connect`. Y en estas pruebas el modelo de huellas no da ninguna
    (`_SinHuellas`), así que ningún BLOB es charla, ni en tránsito ni al final: la
    columna de las huellas deja de estar eximida.
  - **Cómo se engancha, y lo que costó verlo.** El evento de auditoría
    `sqlite3.connect/handle` parecía el sitio: entrega la conexión, pero antes de que
    termine de construirse, así que `set_trace_callback` ahí lanza `ProgrammingError`
    y, aunque no lanzara, el constructor lo borra después; lo vio fallar la primera
    versión de la prueba. El trazador se pone envolviendo `sqlite3.connect`, que es por
    donde conectan `sqlite3` y SQLAlchemy (`sqlite3.dbapi2.connect`, comprobado), con
    una clase de conexión cuyo `set_trace_callback` conserva al vigilante aunque la pieza
    ponga el suyo o lo quite, y cuyo `setconfig` apunta si apaga los disparadores; el
    evento de auditoría queda para lo contrario: una conexión que no pase por ahí se
    apunta como no seguida y cuenta, y una fábrica que no sea una clase de conexión,
    también. Las sentencias que SQLite ejecuta dentro de otra llegan sin valores y con
    `-- ` delante, porque SQLite no expande una sentencia anidada, y repite la sentencia
    al arrancar cada disparador, una vez por fila: la prueba de construcción dio
    dieciséis hallazgos en un turno de charla hasta que las del índice de texto sobre
    sus sombras se toleraron, y solo esas; y la prueba de las filas tardó 133 s hasta
    que la repetición seguida dejó de guardarse. El índice cita las tablas como
    `'main'.'message_fts_data'`, y el analizador de la tabla lo lee.
  - **Ojos frescos sobre el primer arreglo**: cinco hallazgos, los cinco ciertos. El P1
    de arriba. Un P2: una fábrica que no fuese una clase, o el método de la clase base
    sin ligar, quitaban el trazador sin rastro; la fábrica se apunta, y el método sin
    ligar queda en lo que no se garantiza, porque ya no es una pieza que ataja. Tres P3:
    el recuento por sentencias contaba tres veces cada `INSERT` de `messages`, por los
    disparadores del índice (los 15 912 caracteres medidos en veinte turnos eran ese
    recuento triplicado; los disparadores cuentan 5 590 en los mismos turnos) y un
    `INSERT … SELECT` de 5 000 filas contaba una; el ADR eximía a `reabre()` cuando el
    código ya no lo hacía; y `UPDATE OR REPLACE` daba `OR` como tabla. Y dos huecos míos
    de antes de esa revisión: una pieza podía quitar el trazador de su conexión con
    `set_trace_callback(None)`, y la foto del disco solo buscaba extensiones de audio,
    así que una base aparte al lado de la de Sirius, que SQLite crea en C sin pasar por
    `open`, era invisible; ahora en las carpetas de Sirius cuenta cualquier fichero nuevo
    que no sea su base, sus ajustes o su diario (`ficheros_nuevos`), y en la temporal del
    sistema, solo los de audio.
  - **Mutación**: diecinueve mutaciones nuevas, las diecinueve cazadas por
    `test_dobles_del_conductor.py` y `test_vigilante_del_conductor.py`: los disparadores
    sin poner, sin la regla del BLOB, sin la del texto largo, sin mirar lo que había al
    borrar, las filas, el texto total, el esquema, lo anidado, la vigilancia tocada, la
    estructura a mano, otra base, la conexión sin vigilar, los disparadores apagados sin
    apuntar, la fábrica rara sin apuntar, el arranque sin marcar, la foto final sin la
    regla del BLOB, la clase sin conservar al vigilante, la clase envuelta dos veces y la
    foto del disco solo con audio. Una más, el arranque sin marcar al reabrir, sobrevivió
    porque reabrir no escribe ninguna sentencia, y esa marca se quitó: lo que no se puede
    ver fallar no se queda.
  - **Lo que no cubre** queda en «Lo que estas pruebas no garantizan»: texto corto, de
    menos de 16 KiB por valor y 512 KiB en total; hasta mil filas por tabla; lo que una
    extensión en C escriba por una conexión suya, sin pasar por Python; y una pieza que
    llame a los métodos de `sqlite3.Connection` sin ligar para saltarse su propia clase.
- **Ronda 7 de Codex**, sobre `6e74b7b1`: cuatro hallazgos P2, los cuatro ciertos y de la
  familia de las rondas 4, 5 y 6: un sitio donde una pieza podría guardar audio sin que la
  comprobación lo viera. Tres piden una pieza escrita para burlar al arnés: muestras PCM
  en una columna numérica que se reescribe una y otra vez, escrituras directas en una
  sombra del índice de texto, y escribir y borrar durante el arranque, antes de que
  existan los disparadores. El cuarto, el diario, es un error que una pieza honesta sí
  puede cometer: volcar el audio en un mensaje del registro.
  - **La raíz, la de verdad.** Cuatro rondas seguidas de la misma familia, y la regla de
    las dos rondas tenía que haberlo parado en la quinta. No lo paró porque en cada ronda
    se buscó la raíz dentro del mismo enfoque, un detector mejor, y no se preguntó si la
    propiedad pedida se puede afirmar. «Una pieza hecha para engañar a la prueba no puede
    esconder audio» es una negación sin borde: dentro del mismo proceso, quien quiera
    esconder datos siempre tiene otro escondite, y cada petición a Codex le pedía
    buscarlo («¿pasaría con una pieza que hiciera trampa?»). Esa pregunta sirvió en las
    rondas 1 a 3, cuando las pruebas miraban el resultado y no el camino; aplicada al
    almacenamiento, no tiene final. Es la segunda familia de la PR #136: una garantía
    puesta donde no puede cumplirse.
  - **La decisión.** Las pruebas de PA-R03-05 vigilan que una pieza no guarde audio por
    error: ficheros en las carpetas de Sirius, audio en la temporal, cualquier binario o
    texto largo en la base aunque se borre, filas y texto de más, el esquema y, desde
    esta ronda, el diario. Una pieza escrita para burlar al arnés queda fuera de las
    pruebas y dentro de la revisión de su código, la propia y la de Codex, y está escrito
    en «Lo que estas pruebas no garantizan». Los tres hallazgos de esa clase se contestan
    con esto y no se parchean. La decisión es de la sesión, por la regla de las dos
    rondas (ADR-001, §2), aplicada tarde, y la petición de la ronda 8 lleva el alcance
    escrito en vez de la pregunta de la trampa.
  - **El diario.** `audio_en_el_diario` mira el diario de producción, rotaciones
    incluidas: una línea de más de 4 KiB, un tramo de más de 512 caracteres sin espacios
    o más de 256 KiB nuevos desde antes de arrancar Sirius cuentan. Veinte turnos de
    charla escriben 5 080 bytes, con la línea más larga de 126 caracteres y el tramo sin
    espacios más largo de 32, medido el 14-10-2026; un segundo de audio a 16 kHz y 16 bits son 32 000 bytes. La
    prueba de PA-R03-05 lo exige y la de los dobles lo ve con cada regla por separado.
  - **Mutación**: tres mutaciones, una por regla del diario, las tres cazadas por
    `test_dobles_del_conductor.py`.
- **Ronda 8 de Codex**, sobre `7c924cf1`, la primera con el alcance escrito: un hallazgo
  P2, cierto y dentro del alcance, sobre el detector del diario de la ronda 7. Un audio en
  base64 partido en líneas de 76 caracteres, como lo escribe `base64.encodebytes`, pasaba
  por debajo de los tres límites: ninguna línea larga, ningún tramo largo, y los 256 KiB
  de crecimiento eran más de lo que dejan tres turnos.
  - **La raíz.** El detector buscaba la forma del volcado, otra vez, y la forma no tiene
    fin: líneas, tramos, codificaciones. Lo que no depende de la forma es el tamaño: un
    audio escrito en cualquier codificación de texto ocupa al menos lo que el audio. Y
    con los dobles no había tamaño que medir: el micro de mentira daba solo un texto, y
    una pieza que volcara lo que lee habría escrito una frase corta.
  - **El arreglo.** Cada lectura del micro de mentira lleva ahora sus `muestras`: un
    segundo a 16 kHz y 16 bits, 32 000 bytes de ruido que sale del texto, siempre el
    mismo para el mismo texto y que no se comprime (comprimido con zlib sigue por encima
    de 31 900). El tope de crecimiento del diario baja de 256 KiB a 16 KiB, menos de lo
    que ocupa una sola lectura en cualquier codificación, 42 668 bytes en base64; veinte
    turnos de charla escriben 5 080. La línea larga y el tramo largo se quedan para un
    volcado más pequeño en un solo mensaje. La prueba de los dobles escribe una lectura
    entera con `base64.encodebytes` y la ve solo por el crecimiento.
  - **Mutación**: cinco mutaciones, las cinco cazadas: cada regla del diario quitada, el
    micro sin bytes, y el tope de antes, 256 KiB, que es el hallazgo de Codex
    reproducido.
  - **Lo que no cubre** queda escrito: un trozo de audio de menos de 16 KiB en total en
    el diario.
- **El criterio cambia el 13-10-2026, tras la ronda 3.** El propietario, al ver la
  tercera ronda seguida con la misma familia, retiró el tope de rondas que ADR-233 había
  sacado de su «nada de cinco rondas» del 07-10-2026: «No nos podemos limitar a solo tres
  rondas. Yo en ningún momento te he dicho que me pongas tres rondas. Yo necesito trabajo
  bien y bien hecho. El mismo que implementa, al acabar, revisa su trabajo. Si hay algún
  error, corrige, vuelve a revisar. Y así hasta que no haya ninguno y pasa a revisión de
  pruebas». Desde entonces, en esta PR y en las que vengan: quien implementa revisa su
  propio trabajo al acabar, con la pregunta de la lección y con otro par de ojos que no
  haya escrito el código, corrige, vuelve a revisar, y solo cuando no encuentra nada pide
  la revisión externa; la externa se repite sobre cada head nuevo hasta que una ronda
  vuelva limpia, sea la que sea. La regla de las dos rondas sigue: misma familia dos
  veces, raíz antes que parche. El tope de tres de ADR-233 queda sin efecto.
