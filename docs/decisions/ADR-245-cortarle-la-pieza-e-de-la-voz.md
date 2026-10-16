# ADR-245 — Cortarle: la pieza E de la voz

- Estado: APROBADO
- Fecha: 2026-10-15
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). La pieza y su orden los aprobó el
  propietario con el plan (ADR-232) y con la tabla de piezas de ADR-241. Que la respuesta
  se guarde entera aunque le corten, y que la charla apunte hasta dónde la oyó, lo decidió
  él el 15-10-2026 («guarda entera la respuesta cuando le cortes, y además la charla
  apuntada hasta donde la oíste. Es lo lógico»).

Este ADR es además la **nota de arranque** de la rama `claude/la-0-3-pieza-e-cortarle`
(skill `disciplina-evidencia`): las cuatro preguntas, el criterio de parada y el alcance de
la revisión están escritos antes del primer cambio de código de la pieza y antes de
cualquier revisión.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** Hoy no se le puede cortar: desde la
   primera frase hasta que el altavoz acaba, el micro está cerrado (pieza C, ADR-243), y lo
   que el propietario dice encima se pierde. Las tres pruebas de la pieza E esperan en
   `xfail` estricto: su propia voz con la cancelación de eco (PA-R03-03), callarse y
   atender lo nuevo, y guardar entero lo que iba a decir (PA-R03-07). El arreglo va en
   cuatro sitios:
   - **En el oído** (`LocalListening`): con un cancelador de eco cargado, el micro sigue
     abierto mientras contesta; cada trozo pasa por el cancelador antes del detector; y en
     cuanto el detector oye voz en lo limpio mientras Sirius contesta, pensando o
     hablando, calla la voz y el altavoz. La charla sigue escribiendo y guarda la
     respuesta entera. Mientras la charla escribe, el oído lee el micro cada vez que le
     llega texto de ella; después, como siempre, al atender. Lo que le corta es para él:
     calla en el instante en que empieza esa voz, y ahí empieza la charla.
   - **En el puerto del cancelador y su adaptador de verdad**: el oído le da cada trozo
     con su hora de captura, y el altavoz, lo que suena con su hora. El de verdad usa la
     APM de WebRTC que trae `livekit` (Apache-2.0). Como el oído lee tarde (mientras
     transcribe o contesta, el micro hace cola), le da a la APM lo que suena y lo captado
     intercalados por su hora, no por cuándo le llegan.
   - **En la charla**: la respuesta se guarda entera, y además se apunta hasta dónde la
     oyó; lo que el modelo lee después lleva la marca del corte, para que no dé por dicho
     lo que no sonó.
   - **En el conductor de las pruebas**: el doble del cancelador, que aparta el eco de lo
     que el micro captó mientras el altavoz sonaba, por orden de captura y sin mirar quién
     lo dijo; y una prueba nueva de PA-R03-07, hasta dónde la oyó.

   **¿Puede el sitio del arreglo observar el fallo?** Que no se le pueda cortar, sí: el
   oído ve la voz en lo limpio y sabe que contesta. Que el cancelador deje pasar su propio
   eco, no: el oído no sabe quién habla, y un eco que se cuela le cortaría a él mismo. Eso
   solo se oye en su ordenador (E-R03-03).
2. **Qué NO garantiza.**
   - Que la cancelación de eco por software aparte el eco de su habitación, con su altavoz
     y su micro. Si no basta, el micro de unos 60 € del plan es dinero y se le pregunta
     (ADR-241).
   - Que no le corte la tele o un ruido con voz: hasta la 0.4 no sabe quién habla.
   - Cuánto tarda de verdad en callarse: lo que el altavoz ya tiene en su búfer sigue
     sonando, y el detector confirma la voz un poco después de que empiece. Las pruebas
     miden con los relojes de los dobles; la cifra de verdad, E-R03-03.
   - Cortarle mientras un modelo se para a mitad de escribir: en ese rato no le llega
     texto, y el oído lee el micro cuando le llega.
   - Hasta dónde la oyó, con el altavoz de verdad, se cuenta por frases: la que sonaba al
     cortarle cuenta como oída.
   - Que la biblioteca nativa de `livekit` no abra ninguna conexión: su Python solo carga
     la DLL y crea la APM, no se abre ninguna sala, y la DLL no se ha mirado por dentro.
3. **Criterio de parada**, fijado antes de ver ninguna prueba ni ninguna revisión:
   - **La pieza está terminada** cuando sus tres pruebas y la nueva corren y pasan con el
     conductor de verdad, sin `xfail`, y la de la C sobre su propia voz sigue en verde, ya
     en el régimen con cancelación; la tabla de `PRUEBAS_0.3_DEL_ROBOT.md` lo dice de
     PA-R03-03 y PA-R03-07; la batería entera y la cadena de comprobación están en verde;
     la revisión propia no encuentra nada; y hay una ronda limpia de Codex sobre el head de
     contenido con Quality en verde.
   - **Una prueba de la A que no pueda pasar por un defecto suyo**, no de Sirius, se
     arregla sin quitarle ninguna comprobación, y se dice aquí con el fallo que lo
     demuestra. Ninguna prueba se debilita para que pase.
   - **Revisión propia antes de pedir otra**: quien implementa revisa, corrige y vuelve a
     revisar hasta que no hay nada. Dos rondas seguidas con hallazgos de la misma familia:
     se deja de parchear y se busca la raíz, y a la tercera otra vez, sin dar la anterior
     por buena (ADR-001).
   - **Cada regla nueva, con una prueba que la tumbe** en mutación; si una mutación
     sobrevive, o se escribe por qué es equivalente o el código sobra y se quita.
   - **E-R03-03 en su ordenador**: si cortarle falla con la cancelación por software, se
     para y se le pregunta por el micro, porque es dinero.
   - Si algo pide dinero o cambia el producto, se para y se le pregunta.
4. **Qué lo haría imposible.**
   - Que se corte con su propio eco es imposible con el micro cerrado mientras habla, como
     en la C. La E lo abre, y pasa a improbable. Sin el cancelador, o si no carga, sigue
     como en la C: el micro cerrado mientras habla y sin corte.
   - Que se pierda lo que iba a decir: se corta la voz, no la charla.

**Lo aprendido en las piezas B, C y D, aplicado desde el principio** (ADR-242, ADR-243 y
ADR-244, «Revisión externa»):

- La hora de lo oído es la del micro al captarlo, no la del oído al leerlo.
- Una garantía va en el único sitio por el que pasan todos los caminos, no en el camino que
  se está mirando.
- Lo que se decide con las palabras no se apunta en el diario con ellas.

## Contexto y problema

ADR-241 dejó la 0.3 en seis piezas, con sus pruebas de aceptación escritas antes del
código; la B (ADR-242) trajo el oído, la C (ADR-243) la voz y la D (ADR-244, PR #689,
`654ee7a0`) la escucha siempre. La pieza E es «Cortarle: la cancelación de eco por
software y la interrupción». Sus tres pruebas son de PA-R03-03 (con la cancelación de eco,
el micro sigue abierto mientras habla, el eco entra y no le corta ni se transcribe, y la
voz del propietario, que llega con el eco encima, sí atraviesa y le calla) y de PA-R03-07
(si el propietario habla mientras Sirius habla, se calla en menos de medio segundo desde
que el micro lee su voz, sin esperar al fin del turno, y atiende lo nuevo; y lo que iba a
decir queda escrito entero aunque le corte con el modelo aún escribiendo).

`PRUEBAS_0.3_DEL_ROBOT.md` dejó pendiente del propietario si, al cortarle, la charla
guarda entera la respuesta o solo lo que llegó a decir. Lo contestó el 15-10-2026: entera,
y además la charla apunta hasta dónde la oyó. Lo primero ya lo fija la prueba de la A; lo
segundo necesita una prueba nueva en PA-R03-07, que sube el inventario aprobado de 27 a
28 pruebas: se añade, no se quita ninguna.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

Para apartar el eco:

1. **Cerrar el micro mientras habla**, como en la C. No se le puede cortar: es lo que hay,
   y queda para cuando no hay cancelador.
2. **La APM de WebRTC que trae `livekit`** (AEC3), con rueda para Windows y licencia
   Apache-2.0. Pide lo que suena y lo captado en tramas de 10 ms y el retraso entre los
   dos.
3. **speexdsp**: sin ruedas, habría que compilarla en su ordenador.
4. **Un micro con cancelación de eco**, unos 60 €: es dinero, y el plan lo deja para si
   la de software no basta.

Para leer el micro mientras la charla escribe:

- **Desde lo que la charla le pasa al escribir**, en el mismo hilo que atiende al oído.
- **Un hilo más** que lea el micro mientras contesta: dos lectores del mismo micro.

Para apuntar hasta dónde la oyó:

- **En el mensaje de Sirius**, guardado con la charla, y lo que el modelo lee después
  lleva la marca.
- **Solo en el turno siguiente**, como nota para el modelo: no queda apuntado en la charla,
  que es lo que decidió el propietario.

## Decisión

La opción 2, el micro leído desde lo que la charla escribe, y el corte apuntado en el
mensaje de Sirius. Lo que queda por decidir al escribir el código se anota aquí con su
porqué.

Lo que se decidió al escribir el código, con su porqué:

- **El cancelador va con el altavoz** (`SpeakingEngines.echo_canceller`, puerto
  `EchoCanceller` en `src/sirius/ports/local_voice.py`): es el altavoz quien le da lo que
  suena. El oído le da cada trozo que capta, todos y en orden, y recibe lo limpio y si su
  voz estaba en el aire cuando el micro lo captó (`Cleaned.echoing`). Sin cancelador, el
  oído cierra el micro mientras habla, como en la pieza C.
- **Cuándo le cortan.** Cuando el detector oye voz en lo limpio mientras contesta, desde
  que el turno va a la charla hasta que calla, pensando o hablando; o cuando el trozo se
  captó con su voz en el aire, aunque se lea cuando ya ha callado. Calla lo que dice y el
  altavoz; la charla sigue escribiendo y guarda la respuesta entera.
- **Mientras la charla contesta**, un hilo aparte lee el micro cada 30 ms: cuando escribe,
  cuando se para a pensar y cuando, ya escrita la respuesta, hace lo de después del turno,
  que puede ser otra llamada al modelo para resumir (ronda 1 de Codex, abajo). Y antes de
  decir cada frase lo mira también quien la dice: así no dice otra frase encima de quien ya
  habla. El cerrojo del oído pone en fila a los dos, y cada trozo se lee y se mira de una
  vez. Los turnos que se cierran entonces van a la charla cuando acaba la respuesta, y si
  son de la charla se decide al cerrarse cada uno, con la que corre entonces: contestar al
  primero le hace callar otra vez, y eso no deja fuera al siguiente (revisión propia,
  abajo).
- **Una respuesta a la vez en el altavoz.** Mientras suena lo último que dijo, los turnos
  que esperan siguen esperando, y lo que se cierre entonces va detrás de ellos: nunca hay
  dos respuestas en el altavoz, y si le cortan se sabe de cuál es lo que sonaba y hasta
  dónde se oyó (ronda 1 de Codex, abajo).
- **Lo que le corta es para él**: calla en el instante en que empieza esa voz, y ahí
  empieza la charla. Lo que le siga diciendo mientras la charla escribe no le hace callar
  otra vez: cae en esa charla, sin alargarla, y pasados 10 s del corte necesita su nombre,
  como en la pieza D. Sin corte, la charla empieza con el primer trozo que el micro capta
  sin su voz cuando el altavoz ya no tiene nada que decir: en una pausa entre frase y
  frase aún contesta. Si se para el oído mientras contesta, empieza al parar.
- **Hasta dónde la oyó** son las frases que el altavoz llegó a empezar (`Speaker.started`):
  lo que tiró al callarlo no cuenta. Al cortarle calla el altavoz lo primero, y después
  mira hasta dónde llegó y lo apunta: lo que empezó a sonar mientras callaba cuenta, y
  apuntarlo no le hace seguir hablando. Se apunta en el mensaje de Sirius
  (`messages.heard_when_cut`, migración `b0f472943480`), que sigue entero; si le cortan
  mientras la charla escribe, en cuanto la respuesta queda guardada. Lo que el modelo lee
  después lleva la respuesta y, detrás, la nota de lo que se oyó de ella. La nota sale de
  un solo sitio, `cut_note` en `src/sirius/domain/conversation.py`, y la usa todo lo que le
  lee al modelo una respuesta pasada: los mensajes recientes, lo que cuestan en el
  presupuesto del contexto y lo que se le da a resumir, en tercera persona (ronda 1 de
  Codex, abajo). Olvidar lo busca también ahí y se lo lleva con el mensaje.
- **El cancelador de verdad** (`src/sirius/adapters/audio/echo_cancellation.py`) es la APM
  de WebRTC de `livekit`, con su filtro de paso alto. Lo que suena entra con la hora a la
  que se oye y lo captado con la hora a la que se captó, las del DAC y el ADC que da
  PortAudio en cada bloque, y si no las da, las de su llamada (ronda 1 de Codex, abajo);
  y la APM recibe lo que suena antes
  que lo captado a esa hora, en tramas de 10 ms; lo que suena se pasa de 22 050 Hz a
  16 kHz sin numpy, que Quality no instala. Lo limpio sale con 10 ms de retraso como mucho.
  Su voz está en el aire mientras suena lo que tiene algo más que silencio y 0,25 s
  después, la cola del eco en la habitación. El altavoz suena siempre, silencio incluido,
  y con el micro cerrado nadie limpia: de lo que suena guarda los dos últimos minutos, y lo
  que acabó de sonar más de un segundo antes de lo captado no se le da a la APM. Si no,
  tras una hora con el micro callado, el primer trozo esperaría a que la APM tragara la
  hora entera, con el oído parado.
- **Dos pruebas de la A no podían pasar por un defecto suyo**, y se arreglan sin quitarles
  nada, como pide el criterio de parada. En la de su propia voz con cancelación, el
  detector pide tres silencios desde la mitad de la prueba y el último turno solo traía
  uno: el turno se quedaba abierto (`TurnoDeVoz(oido=None, …)`); ahora trae tres. En la de
  guardar entera la respuesta, lo que dice encima se cerraba en el mismo `oye` que su
  pregunta, y el conductor da un turno por `oye` desde la pieza B (rondas 11 y 12 de Codex
  sobre la PR #687): fallaba con «Sirius cerró 2 turnos de una vez»; ahora el detector pide
  dos silencios, como la de callarse con el turno abierto, y se cierra con `calla(1)`.

## Comprobación que la sostiene

Medido el 15 y el 16-10-2026 en el contenedor de la sesión, sobre la rama de esta PR.

- **La APM de verdad con el adaptador de Sirius**, en Linux: `livekit` 1.1.20 en un
  entorno aparte, con eco sintético (una señal con banda y sílabas de voz a 22 050 Hz, y
  su eco a 16 kHz con 40 ms de retraso, la mitad de fuerte y tres reflexiones). El eco
  baja 16,3 dB entre los 4 y los 8 s, y entre 15,1 y 17,6 dB cada segundo desde el
  primero. Con otra voz encima en los dos últimos segundos, la limpia se le parece 0,79
  con 18 ms de retraso (lo captado sin limpiar, 0,84): la voz del propietario pasa. La
  pista de retraso que se le da no cambia nada: de 0 a 200 ms, entre 16,2 y 16,4 dB.
  Vuelto a medir el 16-10-2026 con el adaptador que guarda solo lo último de lo que suena
  (revisión propia, abajo): lo mismo, 16,3 dB y 0,79.
- **Alinear por la hora es lo que hace que funcione leyendo tarde.** Con el oído ocupado
  1,5 s de cada 3, como mientras transcribe y contesta, el eco baja 16,3 dB alineado por
  la hora, y 5,5 dB dándole a la APM lo que suena en el acto, como hace `livekit` en su
  `media_devices.py`. Lo de 5,5 dB se midió antes de que el adaptador tirara lo que sonó
  mucho antes de lo captado: con ese cambio, lo que llega sin su hora se tira, y la
  comparación ya no se puede repetir con él. Alineado por la hora, vuelto a medir: 16,3 dB.
- **Sin red**: la misma prueba corrió dentro de `unshare -n`, sin ninguna red, y
  vigilada con `strace -e trace=connect,socket`: ninguna llamada.
- **Las cuatro pruebas de la pieza E**, en verde con el conductor de verdad: las tres que
  esperaban en `xfail` y la nueva de PA-R03-07, hasta dónde la oyó. Las de voz de la 0.3
  (`tests/acceptance/test_robot_0_3_voz.py`), 22 en verde y 3 `xfail`, las de la F; los
  dobles del conductor (`tests/acceptance/test_dobles_del_conductor.py`), 22 en verde; y la
  tabla de `docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md` pone en verde PA-R03-03 y PA-R03-07,
  como pide su guarda de trazabilidad, con el inventario en 28.
- **45 pruebas nuevas**, 50 casos con sus parámetros: el oído (19 más en
  `tests/unit/test_local_listening.py`, de 77 a 96: el corte pensando y hablando, la
  charla del corte, lo que se cierra mientras contesta, hasta dónde se oyó y el cancelador
  que falla); el cancelador de verdad con una APM de mentira (12 en
  `tests/unit/test_echo_cancellation.py`); el altavoz que cuenta lo que empezó a sonar y
  le da a la cancelación lo que suena (4 más en
  `tests/unit/test_local_speaking_adapters.py`, de 14 a 18); lo que lee el modelo de una
  respuesta cortada (1 más en `tests/unit/test_render_instructions.py`, de 20 a 21) y lo
  que cuesta en el presupuesto (1 más en `tests/unit/test_context_budget.py`, de 14 a 15);
  la base que apunta el corte y lo borra al redactar (2 más en
  `tests/integration/test_sqlite_conversation_repository.py`, de 17 a 19); olvidar lo que
  se oyó (1 más en `tests/integration/test_olvidar.py`, de 12 a 13); la migración, que
  deja los mensajes de antes enteros y sin corte (1 más en
  `tests/integration/test_migrations.py`); la de aceptación nueva, y 3 más de los dobles
  del conductor, de 19 a 22. Las de la regla de a quién le hablan
  (`tests/unit/test_addressing.py`) miran ahora cada mitad, la charla y el nombre: 8, como
  antes. Con todas las que toca la pieza, 401 en verde y 3 `xfail`.
- **Mutación**, cada mutación con las pruebas que tienen que tumbarla: 51 en el oído, la
  regla, el cancelador de verdad, el altavoz, la base, olvidar, lo que lee el modelo, su
  presupuesto y el doble del conductor, y caen las 51. En la primera pasada sobrevivieron
  cuatro: a dos les faltaba la prueba, que se escribió; a otra la prueba solo la tocaba con
  sonidos de una muestra, y se cambió; y la cuarta era código equivalente, que se quitó
  (`started_answering`: toda voz que empieza mientras contesta le corta, y el corte ya pone
  la charla). Otra no valía, porque dejaba un `if` sin cuerpo, y se repitió con `pass`.
  En la de los arreglos de la revisión propia sobrevivió una, callar el altavoz después
  de mirar lo que se oyó mientras la charla escribe, y se escribió su prueba.
- **mypy** sobre `src` y `tests`, sin errores en 719 ficheros; **ruff**, limpio.
- **La batería entera**, sobre el árbol de esta PR: 8 703 en verde, 14 omitidas y 5
  `xfail`, en 22 min 3 s. Sobre el último head de la pieza D, `d1aec4f5`, eran 8 650 en
  verde, 14 omitidas y 8 `xfail`: las 3 de la E ya no esperan, y entran las nuevas. Su
  primera pasada encontró tres fallos, y se arreglaron: la foto del esquema de la base en
  `tests/integration/test_migrations.py` no tenía la columna nueva (se añade, con una
  prueba que sube y baja la migración y deja los mensajes de antes enteros y sin corte);
  la lista de bibliotecas que mira `sirius-instala-la-voz` no tenía `livekit`, y la prueba
  que la compara con el extra `voz` lo vio; y la prueba del diario al apuntar el corte no
  veía nada detrás de otra que configura el diario
  (`tests/integration/test_secret_leakage.py`): enciende su registrador, como las de la
  pieza D, y así pasa en ese orden, donde antes fallaba.

## Consecuencias

- **Con la tele hablando, le corta**: cualquier voz en lo limpio mientras contesta le
  calla, sea suya o no. Hasta la 0.4 no sabe quién habla ni si le miran. Y lo que le corta
  es para él, así que la charla sigue con lo que dijera la tele.
- **Si le hablan mientras piensa, no empieza a hablar**: la respuesta se guarda entera y
  queda apuntado que no se oyó nada de ella.
- **Si quien le calla es la ventana**, al entrar en Model Studio o al cerrarse, no se
  apunta hasta dónde se oyó: el corte que se apunta es el del propietario hablándole.
- **Si la cancelación de eco falla a mitad**, el oído deja de oír y lo dice, como cuando
  falla el detector; el botón lo reabre. Si no está o no carga al empezar, oye y habla
  como en la pieza C, con el micro cerrado mientras habla, y solo el diario lo dice.
- **La biblioteca nativa de `livekit`** se ha visto en Linux, no en Windows: sin red y
  vigilada, no intentó ninguna conexión (abajo). Al salir del programa puede escribir en
  la consola «Exception ignored … FfiHandle.__del__» al deshacerse de la APM: no es un
  fallo de Sirius.
- **Hasta dónde la oyó se cuenta por frases**: la frase que sonaba al cortarle cuenta
  como oída entera.
- **Lo que le dice al cortarle se contesta cuando la charla acaba de escribir la respuesta
  cortada**: guardarla entera, como decidió el propietario, pide dejarla acabar. Un modelo
  que escribe más deprisa de lo que Sirius habla casi siempre ha acabado cuando le cortan;
  con uno lento, se nota.
- **Lo apuntado lo ve el modelo en los mensajes recientes y en el resumen de lo anterior**
  (PA-R02-05), y el presupuesto del contexto lo cuenta. La exportación abierta no lo lleva,
  como tampoco lleva cuándo se borró un mensaje. Las órdenes de memoria siguen mirando la
  respuesta entera: «corrige eso» busca el hecho con sus palabras, y un «sí» sigue
  contestando a la pregunta del final aunque le cortaran antes de oírla, que es raro y no
  se quiso adivinar.
- **Mientras contesta con cancelador hay un hilo más**, que mira el micro cada 30 ms y se
  para cuando la charla acaba.
- **Si la charla tarda en acabar después del corte**, lo que le diga pasados 10 s del
  corte necesita su nombre, como cuando calla en la pieza D: la charla corre desde que
  calló, y calló al cortarle. Así la tele, hablando mientras la charla escribe, no la
  alarga.
- **Cuánto aparta la APM el eco en su habitación** no se sabe hasta E-R03-03: con eco
  sintético, unos 16 dB (abajo). Si no basta para cortarle sin que se corte solo, es el
  micro de unos 60 €, y se le pregunta.

## Alternativas descartadas y por qué

- **speexdsp** (opción 3): sin ruedas para Windows.
- **El micro con cancelación** (opción 4): es dinero; solo si la de software no basta, y
  preguntándole.
- **Leer el micro solo cuando la charla escribe**, sin un hilo más: la pieza D no quiso
  dos que atendieran al oído en sus pruebas, y al principio se hizo así. La ronda 1 de
  Codex enseñó el hueco: mientras la charla resume después del turno no llega texto, y no
  se le podía cortar. El hilo de ahora no atiende al oído, solo lee el micro con su cerrojo,
  como quien dice cada frase.
- **El corte solo como nota del turno siguiente**: no queda apuntado en la charla.

## Revisión propia

Quien implementó revisó la pieza entera antes de pedir otra revisión, corrigiendo y
volviendo a revisar (punto 3 de la nota de arranque).

- **Primera pasada, 15-10-2026**: si le cortaban dos veces mientras la charla escribía, el
  segundo corte movía la charla a la segunda voz, y la primera quedaba antes de ella y no
  era para él. Se arregló con que un segundo corte no la mueve, y la prueba nueva siguió
  fallando, ahora en lo segundo que dijo: después de contestar a lo primero, Sirius calla
  otra vez, la charla se mueve, y lo segundo queda antes de ella.
- **Segunda pasada, 16-10-2026**: es la misma familia que la primera, la charla se movía
  entre que se oía un turno y que se decidía si era para él, así que se dejó de parchear y
  se buscó la raíz: se decidía al atenderlo, con la charla de ese momento, y no al
  cerrarlo, con la que corría cuando se oyó. Ahora se decide al cerrarlo, como la
  generación (`_ClosedTurn.in_conversation`), y el nombre se mira al transcribir: la regla
  se parte en `Addressing.in_conversation` y `says_his_name`. Que un segundo corte no
  mueva la charla se queda por otra razón: así no se alarga. La misma pasada encontró
  otras tres cosas, de otras familias:
  - **El cancelador de verdad lo guardaba todo**: el altavoz suena siempre, y con el micro
    callado nadie limpiaba, así que lo que sonaba se acumulaba sin fin, unos 150 MB por
    hora, y al volver a escuchar el primer trozo esperaba a que la APM lo tragara todo,
    con el oído parado. Ahora guarda los dos últimos minutos y no le da a la APM lo que
    acabó de sonar más de un segundo antes de lo captado.
  - **Al cortarle, miraba hasta dónde se oyó antes de callar el altavoz**: lo que este
    empezara entretanto sonaba y no contaba, y apuntarlo en la base retrasaba el silencio.
    Ahora calla lo primero.
  - **El presupuesto del contexto no contaba lo que se oyó**, que el modelo lee detrás de
    la respuesta: una respuesta cortada podía costar el doble de lo contado. Ahora lo
    cuenta.

## La lección

- familia: `la-hora-de-quien-lee-y-no-de-quien-capta`
- sin esto se repetiría: decidir algo de lo oído con el estado del momento en que se
  atiende, no con el del momento en que se oyó. La pieza D lo aprendió con la hora (ronda
  1 de Codex sobre la PR #689) y esta nota lo aplicó desde el principio a la hora, pero
  no a la charla: si le hablaban dos veces mientras la charla escribía, contestar a lo
  primero movía la charla, y lo segundo, dicho dentro de ella, dejaba de ser para él. Lo
  vio la revisión propia antes de empujar (H-245).
- lo hace cumplir: `tests/unit/test_local_listening.py`

La ronda 1 de Codex la encontró otra vez, en los adaptadores: el micro y el altavoz ponían
la hora a la que Python atendía la llamada de PortAudio, y no la del ADC ni la del DAC
(abajo).

## Revisión externa

Alcance, escrito antes de la primera petición: esta PR trae la pieza E y nada más de la
voz. Mira que con la cancelación de eco su propia voz no empiece un turno ni le corte, que
la voz del propietario le calle sin esperar al fin del turno ni a la respuesta nueva, que
la respuesta quede entera en la charla y que la charla apunte hasta dónde la oyó. Trae
además, en documentos, las rondas limpias de ADR-240 a ADR-244, que se fusionaron sin que
su ADR lo dijera. No trae elegir su voz (F).

- **Ronda 1, sobre `8715774d`**: cuatro hallazgos, los cuatro ciertos, verificados contra el
  código antes de tocar nada.
  - **P1, las horas del ADC y del DAC.** El altavoz le decía a la cancelación que cada
    bloque se oía a la hora de su llamada más la latencia media del flujo, y el micro
    fechaba cada trozo a la hora a la que llegaba su llamada; PortAudio da en cada una la
    hora del DAC y la del ADC, y si las llamadas llegan antes o después según el sistema,
    la APM recibe otro tramo como referencia. Ahora el altavoz usa la del DAC de la
    primera muestra, y el micro la del ADC de la primera más lo que dura el trozo, que es
    su final, como en la medida de la APM; si PortAudio no las da o no tienen sentido, las
    de antes (`portaudio_seconds` en `src/sirius/adapters/audio/local_listening.py`).
  - **P1, el micro sin leer después del último trozo de texto.** El micro solo se leía
    cuando la charla escribía, y después de escribir la charla puede resumir, que es otra
    llamada al modelo: si le hablaba entonces, no callaba hasta que acabara. Ahora lo lee
    un hilo todo el rato que la charla contesta (`read_meanwhile`), y se para cuando acaba;
    sin cancelador no hay hilo. Cierra también lo que la nota de arranque no garantizaba,
    cortarle mientras el modelo se para a mitad de escribir.
  - **P2, una sola respuesta sonando apuntada.** Si se cerraban dos turnos mientras la
    charla escribía, contestaba al segundo mientras aún sonaba lo del primero, y un corte
    se apuntaba en la segunda respuesta, con lo que había empezado a sonar de las dos.
    Ahora no se atiende otro turno mientras suena lo último que dijo: el error se hace
    imposible en vez de contarlo mejor.
  - **P2, el resumen sin la nota del corte.** La entrada del resumen escribía solo la
    respuesta, y al resumirla quedaba por dicha entera.
  - **Dos hallazgos repiten familia, y se buscó la raíz.** El del resumen es de la familia
    del presupuesto de la revisión propia, la nota del corte en un camino y no en los demás
    que le leen al modelo una respuesta: la nota sale ahora de un solo sitio del dominio
    (`cut_note`), y se miró todo lo que lee mensajes: los recientes, el presupuesto y el
    resumen la llevan; soñar y las fichas de personas solo leen lo que dice él; el juez
    mira cómo escribe Sirius, no qué se oyó; y lo que no la lleva se dice en
    «Consecuencias». El de las horas es de la familia de la lección: se miró cada sitio
    donde el oído pone hora a algo. La captura y lo que suena van ya con las horas de
    PortAudio; la charla, con las de captura; y lo que tarda en sonar la primera frase
    (E-R03-02) sigue siendo la hora de dársela al altavoz más lo más que puede tardar,
    una cota de la pieza C que no decide nada.
  - 7 pruebas más del oído (de 96 a 103 en `tests/unit/test_local_listening.py`), 5 de los
    adaptadores con las horas de PortAudio, 1 del resumen y la del presupuesto, cambiada
    para la nota entera. 20 mutaciones de los arreglos: en la primera pasada sobrevivieron
    dos, que un turno nuevo se adelantara a los que esperaban y que, al callar sin corte,
    no fuera ya lo que esperaba; se escribieron sus pruebas, y caen las 20. Las de
    aceptación de la 0.3 y los dobles, tres veces seguidas, 47 en verde y 3 `xfail`, con el
    hilo de verdad. La batería entera: 8 718 en verde, 1 fallo, 14 omitidas y 5 `xfail`, en
    26 min 36 s, con la máquina más lenta que en las pasadas de antes, de 22 min. El fallo
    es la guarda de rendimiento de construir el contexto, de 1 500 ms, que midió entre
    1 561 y 1 656 ms; sola, con este código, 807 a 870 ms, y con el de antes de la ronda,
    `8715774d`, 864 a 890 ms: la ronda no la mueve.
