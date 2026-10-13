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
- La batería entera. Sobre `7209d783`, el primer head: 8 194 pasan, 16 saltadas y 28 `xfail`, los 26 de la 0.3 de entonces y los 2 que ya estaban, en 24 min 29 s. Sobre `main` (`d545ff17`) eran 8 181 pasan y 2 `xfail`: entran las esperadas y 13 que pasan, las dos de la trazabilidad de la 0.3, la tabla rota nueva de la 0.2 y las que los guardas de documentos añaden por cada ADR y documento nuevo. Sobre el head de la ronda 1: 8 194 pasan, 16 saltadas y 29 `xfail`, los 27 de la 0.3 y los 2 que ya estaban, en 25 min 40 s. Sobre el head de la ronda 2: 8 198 pasan, 16 saltadas y 29 `xfail`, en 23 min 44 s; las 4 que entran son las 3 del vigilante y la que los guardas añaden por el fichero nuevo. Sobre el árbol de la ronda 3 y H-241, `56017da1`: 8 199 pasan, 16 saltadas y 29 `xfail`, en 23 min 10 s. Sobre el árbol de la revisión propia, con sus cinco pasadas: 8 211 pasan, 16 saltadas y 29 `xfail`, en 22 min 49 s; las 12 que entran son las 10 de los dobles, la cuarta del vigilante y la que los guardas añaden por el fichero nuevo. Sobre el árbol de la ronda 4 y su mirada propia: 8 212 pasan, 16 saltadas y 29 `xfail`, en 21 min 34 s; la que entra es la del eco mezclado con la voz. Y la línea base de la charla escrita, `di()` solo, en la nube el 13-10-2026: 34 ms en el P95 de 20 turnos, 25,7 ms la mediana y 57,7 ms el máximo.

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
  durante tres rondas.
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
    y medidos. La foto de la base eximía toda columna declarada BLOB, también la que
    trajera la migración de la propia pieza, y en las pruebas la columna de las
    huellas está vacía al arrancar: ahora solo se exime la columna que ya guardaba
    BLOB. Una tabla virtual nueva era un escondite en sus sombras: ahora cuenta. La
    resolución inversa y enlazar a un nombre no se veían: ahora sí. La copia del eco
    que va detrás de la voz puede leerse con el altavoz ya parado, y queda dicho. Y
    una pieza que descartara todo lo que Sirius dijo alguna vez pasaba: ahora el
    propietario repite «Vale, vale.» con el altavoz callado y tiene que oírse.
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
