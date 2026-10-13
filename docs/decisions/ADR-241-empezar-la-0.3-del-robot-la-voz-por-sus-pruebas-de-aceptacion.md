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
   - **Las PR de la 0.3**, como las de la 0.2 (ADR-233): cadena de comprobación verde,
     una ronda limpia de Codex sobre el head de contenido y Quality en verde; como mucho
     tres rondas por PR, y lo cierto de la tercera se corrige en un solo commit y se
     fusiona sin cuarta. Dos rondas seguidas con la misma familia: se deja de parchear y
     se busca la raíz.
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
     no tiene columna para ellos. Una prueba busca ficheros de audio nuevos y audio en la
     base después de varios turnos (PA-R03-05).
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
  micro, el oído, el transcriptor, la voz y el altavoz. Los dobles llevan escrito lo que
  suena, en vez de ondas, y un reloj de mentira mide cuánto hace que acabó la charla.
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
- La batería entera. Sobre `7209d783`, el primer head: 8 194 pasan, 16 saltadas y 28 `xfail`, los 26 de la 0.3 de entonces y los 2 que ya estaban, en 24 min 29 s. Sobre `main` (`d545ff17`) eran 8 181 pasan y 2 `xfail`: entran las esperadas y 13 que pasan, las dos de la trazabilidad de la 0.3, la tabla rota nueva de la 0.2 y las que los guardas de documentos añaden por cada ADR y documento nuevo. Sobre el head de la ronda 1: 8 194 pasan, 16 saltadas y 29 `xfail`, los 27 de la 0.3 y los 2 que ya estaban, en 25 min 40 s.

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

- ninguna: el repaso cláusula a cláusula del §5 antes de la primera ronda es la lección
  de ADR-233, aplicada; comprobar las herramientas antes de instalarlas es lo que pide el
  plan. Nada mordió que alguien pudiera repetir a partir de este ADR.

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
