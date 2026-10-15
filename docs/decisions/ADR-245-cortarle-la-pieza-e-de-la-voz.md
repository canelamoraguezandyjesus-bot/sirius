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

## Comprobación que la sostiene

Se escribe al acabar la pieza, con las cifras de sus pruebas, su mutación y su batería.

## Consecuencias

Se escriben al acabar la pieza.

## Alternativas descartadas y por qué

- **speexdsp** (opción 3): sin ruedas para Windows.
- **El micro con cancelación** (opción 4): es dinero; solo si la de software no basta, y
  preguntándole.
- **Un hilo más leyendo el micro**: dos lectores del mismo micro, lo que la D ya descartó.
- **El corte solo como nota del turno siguiente**: no queda apuntado en la charla.

## La lección

- ninguna: esta es la nota de arranque; si la pieza deja una lección, se escribe al
  acabarla.

## Revisión externa

Alcance, escrito antes de la primera petición: esta PR trae la pieza E y nada más de la
voz. Mira que con la cancelación de eco su propia voz no empiece un turno ni le corte, que
la voz del propietario le calle sin esperar al fin del turno ni a la respuesta nueva, que
la respuesta quede entera en la charla y que la charla apunte hasta dónde la oyó. Trae
además, en documentos, las rondas limpias de ADR-240 a ADR-244, que se fusionaron sin que
su ADR lo dijera. No trae elegir su voz (F).
