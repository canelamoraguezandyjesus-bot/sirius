# ADR-239 — Guardar los hechos con su fecha y quién lo dijo como recuerdos, soñar sin leer a Sirius y obedecer las órdenes de memoria sin pasar por el modelo

- Estado: APROBADO
- Fecha: 2026-10-07
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Es la pieza G de ADR-233; lo que hace
  sale de los pasos 3 a 6 de la memoria en la 0.2 del plan del robot, aprobados por el
  propietario el 06-10-2026.

## Nota de arranque

Escrita antes del primer commit de código de la pieza G. El criterio de parada de las
rondas es el de ADR-233.

1. **Dónde vive el fallo y dónde va el arreglo.**
   - Un recuerdo no tiene fecha ni dice quién lo dijo. «Vivía en Madrid» y «vive en
     Valencia» serían dos recuerdos vigentes a la vez, y la charla traería los dos.
   - Lo que dice Sirius puede acabar como recuerdo suyo: «Proponer guardar…» solo sale en
     las respuestas de Sirius (`src/sirius/presentation/message_view.py:259-266`).
   - Borrar un recuerdo lo borra del recuerdo, pero el mensaje donde lo dijo, los
     resúmenes de la pieza D y el índice de palabras lo siguen guardando.
   - Nadie resume el día ni propone hechos, y no hay ninguna orden de memoria.
   - **El arreglo**:
     - Un hecho es un recuerdo con persona y tema, y cada revisión guarda desde cuándo
       vale, hasta cuándo, quién lo dijo y con qué seguridad. Un hecho que cambia es una
       revisión nueva que cierra la anterior con su fecha. Así lo que ya hace la memoria
       vale para los hechos sin construir otra al lado: corregir, borrar, buscar por
       palabras y por significado, y las sugerencias que él confirma. Es lo que el plan
       pide reutilizar.
     - Cada turno lleva los hechos vigentes de su dueño y los de las personas que nombra
       el mensaje.
     - Las órdenes de memoria se atienden en `send_message`, antes de montar el
       contexto: ni el modelo de la charla ni el de huellas las ven.
     - El sueño pide a la base solo los mensajes de su dueño de un día. Los resume con el
       modelo de este ordenador, guarda el resumen y deja cada hecho que propone como
       sugerencia, pendiente de su sí.
     - «Proponer guardar…» pasa a los mensajes de su dueño, y proponer desde una
       respuesta de Sirius se rechaza en el caso de uso, no solo en la ventana.
   - **¿Puede el sitio del arreglo observar el fallo?** Olvidar, sí: la prueba recorre la
     base entera, tabla por tabla, también las del índice de palabras (PA-R02-17). Que una
     orden no llegue al modelo, también: el grabador cuenta cada petición. Lo que el modelo
     de verdad proponga al soñar no lo ve ninguna máquina de aquí: lo verá él, y nada entra
     sin su sí.
2. **Qué NO garantiza.**
   - Que el sueño proponga bien. Lo hace el modelo de su ordenador.
   - Olvidar en las copias de seguridad ya hechas: van cifradas con su contraseña y son su
     red. No se tocan, y Sirius le dice que las anteriores lo siguen guardando.
   - Olvidar lo que ya salió del ordenador: si la charla iba por OpenAI, lo enviado allí
     no se puede borrar desde aquí.
   - «Olvida lo de…» borra lo que contiene esas palabras. Si él lo dijo con otras, no lo
     encuentra; Sirius le dice cuánto borró.
   - Cuándo sueña: al abrirse la ventana, por los días anteriores que aún no ha soñado. Si
     no abre Sirius, no sueña.
   - Que «eso no es así» acierte el hecho cuando hay varios: elige el que más se parece a
     la pregunta de antes, y él lo ve antes de decir que sí.
3. **Criterio de parada.** El de ADR-233. Además, si el banco de memoria con el buscador
   determinista no acierta 14 de 14 en «olvida eso» y 14 de 14 en «quién dijo qué», la
   pieza no se entrega.
4. **Qué lo haría imposible.**
   - **Lo dicho por Sirius como hecho suyo.** El sueño pide a la base solo los mensajes de
     su dueño, filtrados por quién los escribió, y el caso de uso rechaza proponer desde
     una respuesta de Sirius.
   - **Olvidar y dejar el dato donde nadie mira.** Una guarda recorre todas las columnas de
     texto del esquema: cada una tiene que estar entre lo que olvidar limpia o declarada
     como sin texto suyo. Una tabla nueva con texto la rompe hasta que se decida.
   - **Una orden de memoria en el modelo.** Se atiende antes de montar el contexto, y las
     pruebas cuentan las peticiones al modelo y las frases pedidas al de huellas.

## Contexto y problema

Los pasos 3 a 6 de la memoria en la 0.2 del plan (`docs/evolution/PLAN_DEL_ROBOT.md`):

- «Hechos con fecha de inicio y de fin, quién lo dijo y con qué seguridad. Lo que dice
  Sirius nunca cuenta como hecho del propietario.»
- «"Sueño" nocturno: con el ordenador libre, el modelo resume el día y propone hechos
  nuevos. Quedan pendientes del sí del propietario.»
- «Una ficha por persona. Ahí se juntan las charlas y, desde 0.4, su cara y su voz.»
- «Por voz o por texto: "eso no es así", "olvida eso" y "¿qué sabes de mí?". Olvidar
  borra de verdad, también de los resúmenes.»

Y lo que ya está hecho y el plan manda reutilizar: «Recuerdos con su origen, sugerencias
que el propietario confirma o rechaza, corregir, borrar y archivar».

## Opciones consideradas

1. **Una tabla de hechos aparte**, con su búsqueda y su olvido.
2. **Los hechos como recuerdos con persona y tema**, y cada revisión un tramo con su fecha,
   quién lo dijo y con qué seguridad.
3. **Los hechos solo en el texto del recuerdo** («Lucía dijo que…»), sin columnas.

## Decisión

Se adopta la opción 2.

- **Los hechos.** `memories` gana persona y tema; `memory_revisions`, desde, hasta, quién
  lo dijo y seguridad. Un hecho nuevo de la misma persona y el mismo tema cierra el de
  antes con su fecha y pasa a ser la revisión vigente: la búsqueda y la charla solo ven
  esa, y la historia las guarda todas. Corregir un hecho lo cierra hoy y el nuevo lo dice
  él, seguro. Borrarlo borra también de quién era, de qué trataba y quién lo dijo. Nadie
  puede apuntar un hecho que dijo Sirius.
- **Cómo entra un hecho.** Siempre igual: alguien lo propone y él dice que sí. Lo
  proponen el sueño, «eso no es así» y «Proponer guardar…». Las sugerencias llevan la
  persona, el tema, la fecha, quién lo dijo y la seguridad, o el hecho que corrigen.
- **En cada turno.** «# Lo que sabes de tu dueño», hasta 40 hechos suyos; «# Lo que sabes
  de …» de cada persona que nombra el mensaje, hasta 3 personas y 15 hechos de cada una;
  y «# Los últimos días», los 3 últimos resúmenes del sueño. Un hecho que ya va en su
  sección no gasta sitio entre los recuerdos.
- **La ficha** de una persona junta sus hechos vigentes y los mensajes suyos que la
  nombran, por palabras enteras y sin mirar tildes.
- **Las órdenes**, en `send_message` antes de montar el contexto, sin modelo y sin huellas:
  - «olvida eso»: su último mensaje, la respuesta de Sirius a ese turno, lo que se guardó
    desde él o lo repite, y los resúmenes que ya lo cubrían;
  - «olvida lo de …»: todo lo que nombra esas palabras, enteras: mensajes de los dos,
    recuerdos y hechos, sugerencias, y las frases de los resúmenes que las nombran. La
    orden se guarda como «Olvida lo de…», sin el tema, y la pantalla deja de decirlo;
  - «eso no es así: …»: propone corregir el hecho que más casa con lo último que se
    habló, y un «sí» o un «no» justo después lo contesta. Sin hecho que case, va a la
    charla;
  - «¿qué sabes de mí?», y «¿qué sabes de …?» de alguien con ficha.
- **Olvidar de verdad.** La conexión de olvidar pone a ceros lo borrado (`secure_delete`)
  y al acabar compacta el índice de palabras, que hasta entonces guarda los términos
  borrados. `FORGET_COVERAGE` dice qué hace olvidar con cada columna de texto. Las copias
  de seguridad no se tocan: van cifradas y son su red; Sirius le avisa.
- **El sueño.** Al abrirse la ventana, en segundo plano, sueña los días anteriores, hasta
  7, que aún no tienen resumen. Lee solo sus mensajes y usa el modelo de Ollama elegido
  para la charla, como el juez: nunca OpenAI. Si no puede resumir, propone igual y el día
  queda por soñar. No vuelve a proponer lo que ya está apuntado o pendiente. Avisa en la
  barra de estado de cuántos hechos esperan su sí. Pasa por la misma puerta que el juez y
  las huellas (ronda 2 de Codex en ADR-238): si él escribe mientras, el turno espera a que
  acabe el día que está soñando, y los que quedan los sueña la próxima vez que se abra,
  no entre turno y turno, donde cada día haría esperar al turno siguiente.
- **«Proponer guardar…»** pasa a sus mensajes y desaparece de las respuestas de Sirius.
- **Cada hilo, su unidad de trabajo.** Las órdenes corren en el hilo del envío y el sueño
  en el suyo; ninguno comparte la de la ventana.
- **La orden de E-R02-04**: `scripts/pasar_el_banco_de_memoria.py`. Pasa los 100 casos por
  el camino real, con un Sirius nuevo por caso en una carpeta temporal, y nunca toca su
  `sirius.db` ni sus ajustes.

## Comprobación que la sostiene

- **Las pruebas de aceptación de la 0.2, todas en verde**: PA-R02-10 a PA-R02-18 pasan y no
  queda ningún `xfail` de la pieza G.
- **El banco con el buscador determinista**: 99 de 100. «Olvida eso», 14 de 14; «quién
  dijo qué», 14 de 14. En las demás familias el buscador de prueba acierta por cómo está
  hecho: su cifra de verdad es la de E-R02-04, en su ordenador.
- **Olvidar, comprobado byte a byte** en el fichero entero, también en los bloques del
  índice de palabras: un `LIKE` de SQL se para en el primer cero de un bloque.
- **Vistas fallar**, cada una en su prueba, con el código estropeado a propósito:
  - olvidar sin compactar el índice de palabras;
  - «olvida eso» sin la respuesta de Sirius, sin los resúmenes que lo cubrían, sin lo
    guardado desde el mensaje, o sin mirar quién dijo un hecho;
  - «olvida lo de…» sin recortar los resúmenes, o por trozos de palabra;
  - el sueño leyendo también a Sirius;
  - proponer guardar desde una respuesta de Sirius;
  - la charla sin los hechos suyos, o sin la ficha de quien nombra;
  - la orden atendida después de buscar, que pediría la huella de la frase a olvidar;
  - el sueño o las órdenes con la unidad de trabajo de la ventana;
  - el turno empezando sin esperar al día que está soñando, o el sueño volviendo entre
    turnos.
- **Encontrados en la revisión propia, antes de ningún commit**: la unidad de trabajo
  compartida entre hilos, y «olvida lo de casa» llevándose «casado».
- Unitarias: 26 de las órdenes y de los nombres. Integración: 11 de olvidar, 10 de los
  hechos, 7 del sueño y 10 de las órdenes con Sirius montado. Ventana: 5, y 1 de la
  restauración.

## Consecuencias

- «Proponer guardar…» ya no sale en las respuestas de Sirius, sino en sus mensajes.
- Cada turno lleva sus hechos y los de quien nombra: más texto en la petición, fuera del
  presupuesto de los recuerdos.
- Olvidar borra también los mensajes de Sirius que nombran lo olvidado.
- Tras «olvida eso», los resúmenes que cubrían el mensaje se borran enteros y la charla
  rehace el suyo cuando le toca. Tras «olvida lo de…» solo se quitan sus frases: lo que un
  resumen diga con otras palabras se queda.
- Las sugerencias que el modelo propone en cada respuesta siguen; cada una espera su sí.
- Sin un modelo de Ollama elegido, no sueña.
- Si él escribe mientras sueña, el turno espera a que acabe ese día: un resumen y una
  propuesta del modelo de su ordenador.

## Alternativas descartadas y por qué

- **La tabla aparte**: obligaba a repetir para los hechos la búsqueda por palabras y por
  significado, el olvido y las sugerencias, que ya tienen los recuerdos.
- **Los hechos solo en el texto**: sin fecha ni quién lo dijo comparables, «vive en
  Valencia» no puede cerrar «vive en Madrid».
- **Cambiar el hecho al oír «eso no es así»**, sin preguntar: cambiaría un hecho con una
  adivinanza cuando hay varios candidatos.
- **Borrar las copias de seguridad al olvidar**: es irreversible y le quitaría su red.

## La lección

- familia: `estado-compartido-entre-hilos`
- sin esto se repetiría: un caso de uso nuevo que corre en segundo plano reutiliza la
  unidad de trabajo de la ventana, que guarda su sesión mientras dura, y mezcla las
  transacciones de dos hilos
- lo hace cumplir: tests/integration/test_ordenes_de_memoria.py
