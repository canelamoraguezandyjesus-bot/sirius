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
  acabe fuera. Cada vez que Sirius calla empieza otra charla.
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

## Consecuencias

- **Con la tele hablando sin pausa, cada respuesta abre otra charla**: si Sirius le
  contesta una vez dentro de la charla, puede seguir contestándole mientras la tele no
  calle 10 s. Lo que de verdad lo evita es saber si le miran, en la 0.4. E-R03-05 no lo
  mide: pone la tele sin hablarle, fuera de la charla.
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
