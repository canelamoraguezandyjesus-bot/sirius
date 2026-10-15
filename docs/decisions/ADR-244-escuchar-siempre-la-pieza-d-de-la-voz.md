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
puntúa la próxima vez que corra, sin hacer esperar al turno de voz siguiente. Lo que
queda por decidir al escribir el código se anota aquí con su porqué.

## Comprobación que la sostiene

Se escribe al acabar la pieza, con las cifras de sus pruebas, su mutación y su batería.

## Consecuencias

Se escriben al acabar la pieza.

## Alternativas descartadas y por qué

- **Un temporizador en la ventana** (opción 1): la congelaría mientras contesta.
- **Un hilo que arranca la ventana** (opción 2): dos lectores del mismo micro en las
  pruebas.

## La lección

- ninguna: esta es la nota de arranque; si la pieza deja una lección, se escribe al
  acabarla.

## Revisión externa

Alcance, escrito antes de la primera petición: esta PR trae la pieza D y nada más. Mira
que la ventana escuche desde que se abre y lo diga, que el silencio cierre el micro y lo
diga, que lo oído y lo contestado se vean como la charla escrita, que no se guarde audio
ni lo que no era para él, y que conteste con su nombre siempre y sin él solo mientras
dura la charla. No trae cortarle (E) ni elegir su voz (F).
