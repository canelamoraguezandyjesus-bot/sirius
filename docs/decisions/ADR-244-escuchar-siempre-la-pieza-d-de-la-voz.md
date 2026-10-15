# ADR-244 — Escuchar siempre: la pieza D de la voz

- Estado: APROBADO
- Fecha: 2026-10-15
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). La pieza y su orden los aprobó el
  propietario con el plan (ADR-232) y con la tabla de piezas de ADR-241; el 14-10-2026
  pidió seguir con el código de la 0.3 («ahora tendrás que hacer el código, digo yo»).

Este ADR es además la **nota de arranque** de la rama
`claude/la-0-3-pieza-d-escucha-siempre` (skill `disciplina-evidencia`): las cuatro
preguntas, el criterio de parada y el alcance de la revisión están escritos antes del
primer cambio de código de la pieza y antes de cualquier revisión.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** Desde la pieza C (ADR-243) Sirius oye y
   habla en local, pero solo con `sirius-oye`, en una consola: la ventana no escucha, y
   el oído entrega a la charla todo lo que oye, sea para él o no, también la tele. Las
   ocho pruebas de la pieza D, tres de la ventana
   (`tests/acceptance/test_robot_0_3_ventana.py`) y cinco de voz
   (`tests/acceptance/test_robot_0_3_voz.py`), esperan en `xfail` estricto. El arreglo
   va en tres sitios:
   - **En el oído** (`LocalListening`), antes de entregar nada a la charla: decide si lo
     oído es para él, con su nombre, o sin él mientras dura la charla, que empieza cuando
     Sirius calla. Lo que no es para él se descarta ahí, como hoy un turno sin palabras:
     no llega a la charla, que es lo único que escribe en la base. La charla se mide con
     un reloj que se le pasa; el conductor le pasa el suyo.
   - **En la ventana**: el indicador, «Escuchando» o «En silencio»; el botón de silencio,
     que cierra el micro y lo vuelve a abrir; la escucha, que empieza al abrirse sin
     pulsar nada; y los turnos de voz, pintados como la charla escrita, con sus dos
     botones. El oído le pregunta a la ventana antes de entregar cada turno y le avisa al
     acabarlo, lo atienda quien lo atienda. Un turno de voz es para ella como uno
     escrito: mientras dura, no empieza nada más, ni lo escrito, ni una copia, ni el
     cambio de proyecto, y lo de segundo plano se para como para un turno escrito; y si
     está con otra cosa, ese turno no va a la charla y lo dice.
   - **Fuera de la ventana**, el bucle que atiende al oído una y otra vez, en un hilo
     propio, para que la ventana no se congele mientras contesta. Lo arranca
     `sirius.main` y lo para al salir. El conductor no lo arranca y sigue atendiendo él,
     como hasta ahora: no hay dos que lean el mismo micro. Como la ventana y el bucle
     tocan el oído desde dos hilos, el oído se guarda con un cerrojo, que suelta mientras
     transcribe y contesta: el botón de silencio no espera a que acabe un turno.

   **¿Puede el sitio del arreglo observar el fallo?** El oído es el único sitio que tiene
   a la vez las palabras y el momento en que Sirius calló: decide ahí. La ventana se lee
   de verdad en las pruebas, su indicador, su botón y su lista de mensajes. Lo que no ven
   las pruebas es si el transcriptor de verdad escribe «Sirius» cuando él lo dice, ni si
   la tele y el teléfono le hacen contestar: eso lo mide E-R03-05, en su ordenador.
2. **Qué NO garantiza.**
   - Que reconozca su nombre siempre. Depende de que faster-whisper lo escriba «Sirius»,
     con mayúsculas o minúsculas y signos alrededor; si lo escribe de otra forma, no es
     para él. Lo mide E-R03-05, que le llama por su nombre cinco veces.
   - Que no conteste a la tele mientras dura la charla: en esos segundos, lo que suene
     sin su nombre se toma por él. La charla es corta para que pase poco, y nada lo mide:
     E-R03-05 pone la tele sin hablarle, fuera de la charla, y E-R03-04 charla con la tele
     apagada.
   - Que no oiga lo que no es para él: para saberlo hay que pasarlo a texto. Lo que no es
     para él solo se descarta, en memoria, sin escribirlo en ningún sitio.
   - «Hablando» en el indicador: las pruebas no lo piden, y mientras habla el micro ya
     está cerrado (pieza C).
   - Que la ventana se abra igual de rápido: carga el oído y la voz antes de enseñarse,
     la primera vez. Cuánto tarda no se mide aquí; se ve en E-R03-01.
   - Lo que no trae la pieza D: cortarle (E) ni elegir su voz (F).
3. **Criterio de parada**, fijado antes de ver ninguna prueba ni ninguna revisión:
   - **La pieza está terminada** cuando sus ocho pruebas corren y pasan con el conductor
     de verdad, sin `xfail`; la tabla de `PRUEBAS_0.3_DEL_ROBOT.md` lo dice de PA-R03-04,
     PA-R03-05 y PA-R03-06; la batería entera y la cadena de comprobación están en verde;
     la revisión propia no encuentra nada; y hay una ronda limpia de Codex sobre el head
     de contenido con Quality en verde.
   - **Revisión propia antes de pedir otra**: quien implementa revisa, corrige y vuelve a
     revisar hasta que no hay nada (regla del propietario del 13-10-2026). Dos rondas
     seguidas con hallazgos de la misma familia: se deja de parchear y se busca la raíz
     (ADR-001).
   - **Cada regla nueva, con una prueba que la tumbe** en mutación; si una mutación
     sobrevive, o se escribe por qué es equivalente o el código sobra y se quita.
   - **Si la ventana no puede escuchar sin congelarse**, se para y se replantea antes de
     seguir.
   - Si algo pide dinero o cambia el producto, se para y se le pregunta.
4. **Qué lo haría imposible.**
   - **Que se guarde lo que no era para él.** Se decide antes de la charla, que es lo
     único que escribe en la base, y el diario no lleva el texto de lo oído (ya hoy, desde
     la pieza B).
   - **Que se guarde audio.** Nada de la tubería escribe ficheros, y el conductor de las
     pruebas apunta cada fichero que algo abre para escribir desde que Sirius arranca
     hasta que cierra (PA-R03-05).
   - **Que conteste a la tele sin su nombre fuera de la charla.** No llega a la charla.
   - **Lo que no se puede hacer imposible:** que la tele caiga dentro de la charla. Solo
     se hace improbable, con una charla corta.

**Lo aprendido en las piezas B y C, aplicado desde el principio** (ADR-242 y ADR-243,
«Revisión externa»):

- Lo que se decide con las palabras no se apunta en el diario con ellas.
- Una regla, una prueba que la tumbe en mutación, y textos al azar donde haya forma de
  hacerlos.
- Cuando dos rondas traen lo mismo, la raíz; y a la tercera, otra vez, sin dar la anterior
  por buena.

## Contexto y problema

ADR-241 dejó la 0.3 en seis piezas, con sus pruebas de aceptación escritas antes del
código; la pieza B (ADR-242, PR #687) trajo el oído y la C (ADR-243, PR #688,
`7c88a66b`), la voz. La pieza D es «Escucha siempre: el indicador y el botón de silencio
en la ventana, nada de audio guardado, y cuándo le hablan a él». Sus ocho pruebas son de
PA-R03-04 (al abrir la ventana escucha sin pulsar nada y lo dice; el silencio cierra el
micro y lo dice, y lo que sonó en silencio se pierde; lo oído y lo contestado se ven como
la charla escrita, con sus dos botones), de PA-R03-05 (no guarda audio, y lo que no era
para él no se guarda ni como texto) y de PA-R03-06 (con su nombre, siempre; sin él, solo
mientras dura la charla, entre 5 s y 2 min después de que Sirius calle; lo demás no llega
al modelo).

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

Para quién atiende al oído cuando está la ventana:

1. **Un temporizador en la ventana**, en su hilo. Es lo más simple, pero cada turno con
   respuesta y voz tarda segundos, y la ventana se congelaría mientras tanto.
2. **Un hilo que arranca la ventana al abrirse.** No se congela, pero en las pruebas
   habría dos que leen el mismo micro, ese hilo y el conductor.
3. **Un hilo que arranca `sirius.main`.** La ventana solo arranca la escucha, enseña su
   estado y hace de portera de cada turno: el oído le pregunta antes de entregarlo y le
   avisa al acabar.

Para cuánto dura la charla, dentro de lo que fija PA-R03-06, entre 5 s y 2 min: corta,
para que la tele entre poco, y larga lo bastante para contestarle sin su nombre.

## Decisión

Se adopta la opción 3, y la charla dura 10 s, desde que Sirius calla hasta que empieza a
oírse la voz del turno siguiente. Los turnos de voz no despiertan al juez: puntúa en
segundo plano las respuestas que aún no tienen nota (PA-R02-08), así que las de voz las
puntúa la próxima vez que corra, sin hacer esperar al turno de voz siguiente.

Lo que se decidió al escribir el código, con su porqué:

- **A quién le hablan** va aparte, en `Addressing` (`src/sirius/application/addressing.py`):
  su nombre, sin distinguir mayúsculas, como palabra suelta, siempre; sin él, si su voz
  empieza a oírse a 10 s o menos de que Sirius calle. Sirius calla cuando el altavoz acaba
  o, si no dijo nada, al acabar el turno. Se mide desde que empieza a oírse su voz, no
  desde que acaba el turno: lo que empezó a decir dentro de la charla es para él aunque
  acabe fuera. Cada vez que Sirius calla empieza otra charla. La hora es la del micro al
  captar el trozo en que el detector oye su voz, no la del oído al leerlo: el micro dice
  cuánto esperó cada trozo en su cola (`Captured`), y lo que empezó antes de que Sirius
  callara no es de esa charla (ronda 1 de Codex, abajo).
- **Lo que no es para él** se transcribe, porque sin el texto no se sabe, y se descarta
  ahí: no va a la charla, el diario solo apunta que no era para él, y vuelve como turno con
  `addressed` falso, que ni la ventana ni `sirius-oye` enseñan.
- **El botón de silencio** (`mute`) cierra el micro, olvida el turno a medias y lo que
  se había oído y aún no había ido a la charla, y nada lo abre hasta quitarlo, ni
  `start`. No calla lo que está diciendo: el silencio es para el micro.
- **El oído se guarda con un cerrojo** para el micro, el detector y su estado, que suelta
  mientras transcribe y contesta. Se prueba con dos hilos de verdad: el silencio no espera
  a que acabe un turno, sí a que el detector acabe con su trozo, y parar espera a que el
  altavoz tome la frase que estaba tomando y después la calla. Parar calla también lo que
  la charla siga escribiendo: ninguna frase se cuela después.
- **La ventana es la portera** (`ListeningWatcher`, y `ListeningBridge` para cruzar de
  hilo): el oído le pregunta antes de entregar cada turno para él y le avisa al acabar.
  Un turno de voz es para ella como uno escrito: «pensando», lo escrito, las copias, la
  exportación y el cambio de proyecto quietos, y lo de segundo plano parado y esperado,
  como para un turno escrito. La espera la hace el hilo del oído, con un aviso que cada
  trabajo de segundo plano pone al acabar (`done`), porque las señales de la ventana no le
  llegan. Si la ventana está con otra cosa, el turno no va y lo dice. Sin «Cancelar»:
  cortarle es la pieza E. Al cerrarse, deja de oír ya, y si hay un turno de voz en marcha
  se cancela y espera a que acabe, como uno escrito.
- **El bucle** (`ListeningLoop`) es de cada ventana de verdad: `sirius.main` se lo da a
  la que monta al arrancar y a la que abre al crear el proyecto, la ventana lo arranca al
  abrirse y lo para al cerrarse, sin esperarlo: si estuviera preguntándole por un turno,
  esperarlo desde ella la colgaría. Las pruebas montan la ventana sin él y atienden al
  oído ellas.
- **El reloj de la charla** es el mismo con el que el oído mide lo que tarda en hablar:
  `build_conversation_dependencies` lo recibe, y el conductor de la 0.3 le pasa el suyo.
- **Las órdenes de memoria con su nombre detrás**, tras una coma («olvida eso, Sirius»), o
  con «oye» o «eh» delante, son órdenes. Fuera de la charla hay que llamarle, y una orden
  que no se reconoce llega al modelo, que puede decir que olvida sin olvidar. Sin coma no
  se quita: «¿qué sabes de Sirius?» pregunta por él.
- **Si abrir el oído falla de una forma que no se espera**, la ventana se abre igual y lo
  dice, con el tipo de fallo; el botón vuelve a intentarlo.
- **Model Studio y el oído no se pisan** (ronda 2 de Codex, abajo). Model Studio tiene su
  micro y su voz: mientras está abierto, el oído no oye y lo que estaba diciendo se calla,
  o la voz de Model Studio volvería por el micro como un turno y los dos micros captarían
  a la vez. Al salir, el oído vuelve a oír si oía al entrar: si estaba en silencio sigue
  así, si había dejado de oír por un fallo lo reabre el botón, y si la ventana se está
  cerrando no se abre, porque ya nadie haría de portera. Y no vuelve a oír hasta que la voz
  de Model Studio calla del todo, sin ningún trabajador de la voz en marcha y nada
  sonando: lo que aún sintetizaba al salir suena después, como sin esta pieza, y el oído
  no lo oye (ronda 5). La espera está en el único sitio por el que la ventana abre el
  oído, al abrirse, con el botón y al salir de Model Studio: ningún camino se la salta, el
  botón se ve apagado mientras tanto, y lo que se pida entonces se hace cuando calle
  (ronda 6). La voz de Model Studio, sus reproductores y su cola quedan como estaban: esta
  pieza no los toca.

## Comprobación que la sostiene

Medido el 15-10-2026 en el contenedor de la sesión, sobre la rama de esta PR.

- **Las ocho pruebas de la pieza D**, en verde con el conductor de verdad: las tres de la
  ventana (`tests/acceptance/test_robot_0_3_ventana.py`) y las cinco de voz
  (`tests/acceptance/test_robot_0_3_voz.py`). Con las de B y C, 21 en verde y 6 `xfail`,
  las de E y F. El conductor dice ya que la pendiente con un método suyo es la F
  (`tests/acceptance/test_dobles_del_conductor.py`, 19 en verde), y la tabla de
  `docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md` pone en verde PA-R03-04, PA-R03-05 y
  PA-R03-06, como pide su guarda de trazabilidad.
- **96 pruebas nuevas**: la regla de a quién le hablan (16 en
  `tests/unit/test_addressing.py`); el oído (27 más en `tests/unit/test_local_listening.py`,
  de 46 a 73: la regla con el servicio entero, el silencio, la portera, que no se cuele
  ninguna frase al parar, y tres con dos hilos de verdad para el cerrojo); `sirius-oye`
  con lo que no era para él (1 más, de 16 a 17); las órdenes con su nombre detrás o con
  «oye» delante (8 más, de 26 a 34); el bucle (7 en `tests/unit/test_listening_loop.py`);
  el puente entre hilos (8 en `tests/gui/test_listening_bridge.py`); la ventana con el
  oído, la portera, el cierre a mitad de un turno y el bucle de producción (23 en
  `tests/gui/test_escucha_en_la_ventana.py`); y que lo de segundo plano avisa al acabar
  aunque falle (6 en `tests/gui/test_trabajos_de_segundo_plano_avisan_al_acabar.py`). Dos
  de integración llaman ahora a Sirius por su nombre, con la regla de verdad. Con todas
  las de la voz, la ventana, el arranque y las órdenes, 311 en verde y 6 `xfail`.
- **Mutación**, cada mutación con la prueba que tiene que tumbarla: 45 en el oído y la
  regla, y caen las 45; 6 en las órdenes de memoria, y caen las 6; 54 en la ventana, el
  puente, el bucle, el arranque y los trabajos de segundo plano, y caen las 54. Una de
  ellas, preguntar a la ventana con la conexión que espera también desde su propio hilo,
  no hace fallar la prueba sino que la deja colgada, que tampoco pasa: se cuenta como
  caída y se dice aparte. Las tres tandas se repitieron sobre lo confirmado (`fb2784b` y
  `7b8e796`), tras perder en un reinicio del contenedor el árbol en que corrieron la
  primera vez, con el mismo resultado.
- **mypy** sobre `src` y `tests`, sin errores en 717 ficheros; **ruff**, limpio.
- **La batería entera**, sobre `ec0395ad`: 8 632 en verde, 14 omitidas y 8 `xfail`, en
  25 min 9 s. Sobre el último head de la pieza C, `dcdf08e6`, eran 8 521 en verde, 16
  omitidas y 16 `xfail`: las 8 de la pieza D ya no esperan.
- **Tras la ronda 1 de Codex** (abajo), 6 pruebas más: la que reproduce el hallazgo, que
  fallaba con el código de antes, y tres del oído en `tests/unit/test_local_listening.py`
  (de 73 a 77), una de la regla (de 16 a 17) y una del micro de verdad en
  `tests/unit/test_local_listening_adapters.py`. Las de la voz, la consola y la ventana,
  193 en verde; las de aceptación de la 0.3 y los dobles, 42 en verde y 6 `xfail`. 9
  mutaciones del arreglo, y caen las 9. mypy, sin errores en 717 ficheros; ruff, limpio.
  La batería entera sobre `ff8a0b5f`: 8 638 en verde, 14 omitidas y 8 `xfail`, en 24 min
  22 s; sobre `ec0395ad` eran 8 632, 14 y 8: entran las 6 nuevas.
- **Tras la ronda 2 de Codex** (abajo), 7 pruebas más: una del oído con el detector lento
  (de 77 a 78), cinco de la ventana con Model Studio (de 23 a 28) y una de Model Studio
  en `tests/gui/test_model_studio_integration.py` (de 38 a 39). Las del oído y las dos
  ventanas, 145 en verde. 10 mutaciones de los arreglos, y caen las 10; las 9 de la ronda
  1, repetidas sobre el código nuevo, caen las 9. mypy, sin errores en 717 ficheros; ruff,
  limpio. La batería entera sobre `df8de8d6`: 8 645 en verde, 14 omitidas y 8 `xfail`, en
  22 min 11 s; sobre `ff8a0b5f` eran 8 638, 14 y 8: entran las 7 nuevas.
- **Tras la ronda 3 de Codex** (abajo), 3 pruebas más y una que cambia: callar la voz de
  Model Studio mientras sintetiza (`tests/unit/test_studio_voice.py`), los dos
  reproductores con una orden de sonar que espera en la cola cuando se para
  (`tests/gui/test_qt_playback.py` y `tests/gui/test_winsound_playback.py`), y la de salir
  de Model Studio, que ahora exige que no suene nada. Los reproductores y Model Studio, 90
  en verde. 9 mutaciones del arreglo, y caen las 9. mypy, sin errores en 717 ficheros;
  ruff, limpio. La batería entera sobre `667cf41b`: 8 648 en verde, 14 omitidas y 8
  `xfail`, en 22 min 47 s; sobre `df8de8d6` eran 8 645, 14 y 8.
- **Tras la ronda 4 de Codex** (abajo), una prueba más con tres casos en
  `tests/gui/test_model_studio_integration.py`: lo que devuelve la voz callada acaba
  bien, falla o revienta, y no toca la voz de ahora. Con el código de antes fallaba en
  los tres. La ventana, Model Studio, los reproductores y la voz, 206 en verde. 4
  mutaciones del arreglo, y caen las 4. mypy, sin errores en 717 ficheros; ruff, limpio.
  La batería entera sobre `78d856a7`: 8 651 en verde, 14 omitidas y 8 `xfail`, en 21 min
  58 s; sobre `667cf41b` eran 8 648, 14 y 8.
- **Tras la ronda 5 de Codex** (abajo), lo de las rondas 3 y 4 se retira con sus pruebas:
  la voz de Model Studio, sus dos reproductores y sus pruebas vuelven a ser los de `main`,
  y la ventana pierde la cuenta de la ronda 4. Entran 3 pruebas en
  `tests/gui/test_escucha_en_la_ventana.py` (de 28 a 31): al salir, el oído espera a que
  calle lo que suena después; vuelve cuando lo que sintetizaba no llega a sonar; y
  dentro de Model Studio, que su voz acabe no lo abre. La ventana, Model Studio, los
  reproductores y la voz, 117 en verde (aquí ponía 115: vuelto a contar en la ronda 6 con
  los ficheros de `3363af57`, son 117). 14 mutaciones de Model Studio y el oído tal como
  quedan, y caen las 14. mypy, sin errores en 717 ficheros; ruff, limpio.
- **Tras la ronda 6 de Codex** (abajo), la espera pasa al único sitio por el que la ventana
  abre el oído. Entran 3 pruebas en `tests/gui/test_escucha_en_la_ventana.py` (de 31 a
  34): con la voz de Model Studio a medias al salir, el botón se ve apagado y ni
  pulsándolo se abre el oído hasta que calla; en silencio, el botón vuelve cuando calla y
  sigue en silencio; y lo que se pida mientras tanto se hace cuando calla. Con la ventana
  de la ronda 5 fallan las tres. 20 mutaciones de Model Studio y el oído: en la primera
  pasada sobrevivió una, porque la comprobación que hacía la ventana al salir de Model
  Studio repetía la de la puerta; se quitó del código, y de las 19 que quedan caen las 19.
  La ventana, Model Studio, los reproductores y la voz, 120 en verde. mypy, sin errores en
  717 ficheros; ruff, limpio.

## Consecuencias

- **Con la tele hablando sin pausa, cada respuesta abre otra charla**: si Sirius le
  contesta una vez dentro de la charla, puede seguir contestándole mientras la tele no
  calle 10 s. Lo que de verdad lo evita es saber si le miran, en la 0.4. E-R03-05 no lo
  mide: pone la tele sin hablarle, fuera de la charla.
- **Lo que se dice mientras atiende un turno para él no es de ninguna charla**, salvo con
  su nombre: si contesta en voz alta, el micro cerrado lo pierde, como en la pieza C; si
  no dice nada, empezó antes de que callara.
- **La charla cuenta desde el trozo en que el detector oye su voz**, un poco después de
  que empiece de verdad: lo que Silero necesita oír para darla por empezada; no se ha
  medido. Con su voz empezando justo al final de los 10 s, puede quedar fuera. No se adelanta con lo
  que el oído guarda de antes de la voz (`PRE_ROLL_CHUNKS`, medio segundo con el micro de
  verdad): la charla ganaría hasta ese medio segundo, y en los dobles, donde un silencio
  no dura nada, lo guardado puede ser de mucho antes.
- **En Model Studio no se le habla con el oído**: allí se usa su micro, el de pulsar.
  Entrar en Model Studio mientras Sirius habla con la voz local lo calla. Al salir, si
  Model Studio aún tenía voz en marcha, el oído y su botón esperan lo que ella tarde en
  callar. Si su síntesis se colgara, esperan lo que tarde en fallar: Model Studio la pide
  a OpenAI sin reintentos y con el plazo por defecto de su cliente, 600 s sin recibir
  nada (openai 2.45.0). Hasta la ronda 6 el botón no esperaba (abajo).
- **La voz de Model Studio sigue como estaba**, con lo que ya hacía antes de esta pieza:
  lo que sintetizaba al salir suena después, ya fuera; y con «Repetir» o «Leer todo»
  durante una síntesis puede haber dos peticiones a la vez, y lo que devuelve la
  primera cambia el estado de la segunda. No lo arregla esta pieza (ronda 5, abajo).
- La ventana tarda más en abrirse la primera vez con la voz instalada: carga el oído y la
  voz antes de enseñarse. No se ha medido; se ve en E-R03-01.
- El botón de silencio reinicia el detector en el hilo de la ventana, como parar desde la
  pieza B: Silero y Smart Turn nuevos, unas décimas de segundo en las que la ventana no
  responde.
- Mientras contesta por voz, lo escrito espera, como con un envío escrito; y si le hablan
  mientras la ventana está con lo escrito, una copia, una exportación o el cambio de
  proyecto, ese turno se pierde y la ventana lo dice.
- El juez puntúa las respuestas dichas por voz más tarde, cuando corre tras lo escrito o
  al abrir Sirius.
- El silencio no se guarda: al volver a abrir Sirius, escucha.
- Con la ventana abierta hay un hilo más, que mira el micro cada 30 ms; sin la voz
  instalada, cada vuelta no hace nada.
- Las órdenes de memoria con su nombre detrás, tras una coma, o con «oye» delante son
  órdenes también por escrito.

## Alternativas descartadas y por qué

- **Un temporizador en la ventana** (opción 1): la congelaría mientras contesta.
- **Un hilo que arranca la ventana** (opción 2): dos lectores del mismo micro en las
  pruebas.

## La lección

- familia: `regla-nueva-que-cambia-lo-que-otro-reconoce`
- sin esto se repetiría: pedirle al propietario algo nuevo, aquí llamar a Sirius por su
  nombre fuera de la charla, sin mirar qué deja de reconocerse con eso. Las órdenes de
  memoria solo se reconocían con su nombre delante: «olvida eso, Sirius» u «oye, Sirius,
  olvida eso» habrían llegado al modelo como una frase más, y el modelo puede decir que
  olvida sin olvidar. Lo vio la revisión propia al poner su nombre en las pruebas de
  integración, antes de empujar (H-244).
- lo hace cumplir: `tests/unit/test_memory_commands_domain.py`

## Revisión externa

Alcance, escrito antes de la primera petición: esta PR trae la pieza D y nada más. Mira
que la ventana escuche desde que se abre y lo diga, que el silencio cierre el micro y lo
diga, que lo oído y lo contestado se vean como la charla escrita, que no se guarde audio
ni lo que no era para él, y que conteste con su nombre siempre y sin él solo mientras
dura la charla. No trae cortarle (E) ni elegir su voz (F).

- **Ronda 1, sobre `e40d0360`**: un hallazgo P2, cierto. El inicio del turno se fechaba
  cuando el oído leía el trozo, no cuando el micro lo captó. Mientras la charla contesta,
  el micro sigue captando y nadie lo lee; si al final Sirius no dice nada, la charla
  empieza al acabar el turno, y lo que la tele dijo mientras tanto se leía después, se
  fechaba dentro de la charla y llegaba al modelo. Se reprodujo con una prueba antes de
  arreglarlo: con el código de antes, la tele llegaba a la charla. Arreglo: el micro dice
  cuánto esperó cada trozo en su cola (`Captured.age`, sin que el micro y el oído tengan
  que llevar el mismo reloj), el oído fecha la voz con la hora del micro, para la charla
  y para E-R03-02, sin su nombre la voz tiene que empezar después de que Sirius calle, y
  Sirius calla antes de abrir el micro. El hallazgo pedía además adelantar el inicio con
  lo guardado de antes de la voz; no se hace, por lo que dice «Consecuencias». Familia:
  `la-hora-de-quien-lee-y-no-de-quien-capta`.
- **Ronda 2, sobre `5f5e63a8`**, preguntando si el enfoque está mal: no lo dijo, y trajo
  dos hallazgos, los dos ciertos.
  - **P2, de la misma familia que la ronda 1**: la hora de captura se restaba de un reloj
    leído después del detector, y lo que tardara en mirar el trozo volvía a contar; con
    la charla abierta a los 0 s, una voz captada a los 9,9 s con un detector que tarda
    0,2 s quedaba a los 10,1 s, fuera. **Dos rondas seguidas con la misma familia: se
    dejó de parchear y se buscó la raíz.** En la ronda 1 la hora se dejó después del
    detector a sabiendas, para no cambiar una prueba vieja en la que lo que tardaba el
    detector hacía de lo que dura el audio: se acomodó el código a la prueba. Arreglo de
    la raíz: la hora se toma una sola vez, al sacar el trozo del micro, antes de que nada
    lo mire, y en las pruebas el tiempo pasa al llegar el audio (`al_leer` del micro de
    mentira), no al procesarlo. Las otras tres horas que lee el oído son de sucesos, no
    de captura (calla al acabar un turno sin decir nada, calla antes de abrir el micro,
    el primer sonido) y se quedan. Una prueba con el detector lento lo sostiene. Se
    sigue: la raíz se cierra en un solo sitio.
  - **P1, familia nueva, `dos-voces-en-la-misma-ventana-sin-exclusion`**: Model Studio tiene
    su micro y su voz, y el oído que escucha siempre los oía; su voz, con «Sirius»
    dentro, volvía por el micro como un turno, y pulsar su micro dejaba dos capturas a la
    vez. Arreglo, en «Decisión»: mientras Model Studio está abierto el oído no oye, y
    fuera de Model Studio su voz no suena. Al revisarlo apareció un caso que el hallazgo
    no decía: salir de Model Studio callaba lo que sonaba, pero no lo que aún se estaba
    sintetizando, que sonaba después, ya fuera; también se arregla, con su prueba.
- **Ronda 3, sobre `df8de8d6`**, preguntando si el enfoque está mal: no lo dijo. Repite el
  P1 de la ronda 2, pero es el mismo hilo recolocado sobre el head nuevo, con su fecha de
  entonces: no cuenta como hallazgo nuevo. Y trae uno nuevo, cierto.
  - **P2, de la misma familia que el P1 de la ronda 2**: la guarda de la ventana contra la
    voz de Model Studio que acababa de sintetizarse al salir llegaba tarde, porque cuando
    la ventana se enteraba la reproducción ya había empezado; la prueba de la ronda 2 hasta
    lo daba por bueno. **Dos rondas seguidas con la misma familia: se dejó de parchear y se
    buscó la raíz.** Quien decide que algo suene es Model Studio, en un hilo de fondo, y
    nunca volvía a mirar si aún podía sonar: parar solo paraba lo que ya sonaba. Y al
    buscar la raíz salió un segundo sitio igual: los reproductores encolan la orden de
    sonar en el hilo de la ventana, y una orden pedida antes de parar sonaba después; con
    el temporal ya borrado, el de Windows habría sonado su aviso. Arreglo de la raíz, en
    los dos sitios donde empieza el sonido: callar cuenta, y lo que se pidió antes no
    suena. La guarda de la ventana sobra y se quita. Se sigue: no queda ningún camino por
    el que la voz de Model Studio suene después de callarla.
- **Ronda 4, sobre `667cf41b`**, preguntando si el enfoque está mal: no lo dijo, y trajo un
  hallazgo, cierto, que nace del arreglo de la ronda 3.
  - **P2, tercera ronda seguida en la misma familia**: al callar la voz, la síntesis en
    marcha acaba devolviendo «nada que decir», y la ventana lo tomaba por la voz de
    ahora; si ya se sintetizaba otra, la daba por acabada y podía arrancar otra a la vez,
    y un fallo o una excepción de la callada la dejaban en error. La raíz de la ronda 3
    estaba a medias: una petición de voz no tenía identidad en todas sus etapas. La tenía
    donde empieza el sonido y le faltaba donde se recoge lo que devuelve, la ventana.
    Ahora la ventana cuenta también las veces que se calla, cada petición se lleva la
    cuenta de cuando se pidió, y lo que devuelva una anterior se ignora. Con eso, las
    tres etapas que actúan, la voz de Model Studio antes de pedir que suene, los
    reproductores antes de empezar y la ventana antes de atender lo que vuelve, ignoran
    lo pedido antes de callar; el final natural de lo que suena no puede llegar de una
    voz callada, porque parar borra el aviso. Se sigue: no queda otra etapa con efecto.
- **Ronda 5, sobre `78d856a7`**, preguntando si el enfoque está mal: no lo dijo, y trajo un
  hallazgo, cierto.
  - **P2, cuarta ronda seguida en la misma familia**: con «Repetir» o «Leer todo» mientras
    otra voz se sintetiza, las dos peticiones llevan la misma cuenta, que solo sube al
    callar, y lo que devuelve la primera cambia el estado de la segunda. **El patrón, tras
    cuatro rondas: cada arreglo dentro de la tubería de voz de Model Studio destapaba otro
    hueco que ya estaba antes de esta pieza.** Las dos voces a la vez con «Repetir» las
    confirma una prueba de `main`, y lo que sonaba tras salir también ocurría sin el oído.
    Esta pieza no debe rediseñar esa tubería (CLAUDE.md: no rediseñar Sirius por iniciativa
    propia), y lo que le toca garantizar es otra cosa: que el oído nunca oiga a Model
    Studio. **Decisión: se retira lo construido en las rondas 3 y 4** y la garantía se pone
    en el oído, que al salir de Model Studio espera a que su voz calle del todo. Lo que
    Model Studio ya hacía, y no hace esta pieza, queda escrito en «Consecuencias».
- **Ronda 6, sobre `3363af57`**, preguntando si el enfoque está mal: no lo dijo. Repite el
  P1 de la ronda 2, el mismo hilo recolocado, que no cuenta, y trae un hallazgo nuevo,
  cierto.
  - **P2, quinta ronda seguida en la misma familia**: el botón «Escuchar» no esperaba como
    el oído. Con la voz de Model Studio aún sintetizándose al salir, abría el micro, y lo
    que sonaba después podía tomarse por un turno; lo que la ronda 5 dejó escrito como
    salida, «si su síntesis no acabara nunca, el botón lo reabre», era ese hueco. **El
    patrón: la espera estaba en uno de los caminos que abren el oído, no en el sitio por el
    que pasan todos.** La ventana abre el oído por un solo sitio, `_listen`: al abrirse,
    con el botón y al salir de Model Studio, y no hay otro (comprobado con `grep`). La
    espera va ahí: mientras Model Studio está abierto o su voz sigue sintetizando o
    sonando, no lo abre y lo deja pedido para cuando calle, y el botón se ve apagado. Se
    sigue: es la decisión de la ronda 5 en el sitio que no deja ningún camino fuera.
