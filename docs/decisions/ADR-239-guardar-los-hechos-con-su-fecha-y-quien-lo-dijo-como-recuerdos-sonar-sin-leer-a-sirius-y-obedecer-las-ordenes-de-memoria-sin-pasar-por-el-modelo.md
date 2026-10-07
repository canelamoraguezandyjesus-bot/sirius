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

Se completa al acabar la pieza.

## Decisión

Se completa al acabar la pieza.

## Comprobación que la sostiene

Se completa al acabar la pieza.

## Consecuencias

Se completa al acabar la pieza.

## Alternativas descartadas y por qué

Se completa al acabar la pieza.

## La lección

- ninguna: se escribe al acabar la pieza, si la hay.
