# ADR-247 — Dar con una orden la cuenta de las 50 marcas de E-R02-02

- Estado: APROBADO
- Fecha: 2026-10-16
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Las evaluaciones y sus umbrales los
  aprobó el propietario con ADR-233; esta PR no cambia ninguno.

Este ADR es además la **nota de arranque** de la rama `claude/la-cuenta-de-las-50-marcas`
(skill `disciplina-evidencia`): las cuatro preguntas, el criterio de parada y el alcance de
la revisión están escritos antes del primer cambio de código y antes de cualquier
revisión.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** Son dos, y los dos salieron el
   16-10-2026 al preparar el lote de sus evaluaciones.
   - **E-R02-02 no tiene dónde leerse.** Pasa si, de las últimas 50 respuestas marcadas,
     40 o más son «eso es Sirius», y dice «La cuenta la da Sirius»
     (`docs/evolution/PRUEBAS_0.2_DEL_ROBOT.md`). La cuenta existe, `MarkReplyUseCase.count`
     en `src/sirius/application/robot_conversation.py`, y es la que fija PA-R02-06, pero
     solo la llama el conductor de las pruebas: ninguna ventana la enseña y ninguna orden
     la da. El arreglo va en una orden nueva, `contar_las_marcas.py` en `scripts/`, como
     las de E-R02-04 y E-R02-05: dice, con esa misma cuenta, cuántas de las últimas 50 son
     «eso es Sirius», qué modelos las dieron y si pasa. La ventana no se toca.
   - **La orden de E-R02-05 mide una memoria que no es la suya** si él eligió otra carpeta
     para sus datos al configurar Sirius. La ventana y `sirius-oye` buscan la base con
     `DataLocationUseCase`, que respeta esa elección (`src/sirius/listen_console.py:153`);
     `scripts/medir_busqueda_de_memoria.py:182` la busca en la carpeta de serie. Reproducido
     antes de tocar nada: con la base en una carpeta elegida y un recuerdo dentro, la orden
     dijo «Tu memoria, 0 recuerdos» y «Pasa: sí.». El arreglo es que las dos órdenes busquen
     la base como `sirius-oye`, con la misma función, sacada de `sirius-oye` a un sitio
     común en vez de copiarla; y si Sirius aún no sabe dónde están sus datos, que lo digan
     como `sirius-oye`: «Abre Sirius una vez con su ventana». Va al registro de defectos.

   **¿Puede el sitio del arreglo observar el fallo?** Sí: las órdenes leen la base que abre
   la ventana, con la resolución que usa `sirius-oye`, y la cuenta es la del caso de uso. Si
   una respuesta suena a Sirius no lo observa nadie más que él, al marcarla.
2. **Qué NO garantiza.**
   - Que las 50 sean del modelo que elija en E-R02-01 y con la semilla de ahora. La orden
     dice qué modelos las dieron; la evaluación, como está escrita, solo pide 40 de 50.
   - Que la cuenta se vea en la ventana: no se toca.
   - Que funcionen en su Windows: se prueban en Linux, con bases de verdad.
   - Que ninguna otra orden lea sus datos de la carpeta de serie: se han mirado las de
     `scripts/`, y solo la de E-R02-05 lee su base; la de E-R02-04 trabaja en carpetas
     temporales.
3. **Criterio de parada**, fijado antes de escribir código y de cualquier revisión:
   - **Terminado** cuando la orden de las marcas da la cuenta de PA-R02-06 sin poder
     contar distinto, dice qué modelos dieron las 50 y si pasa, y no escribe nunca en su
     base; las dos órdenes leen la base de la carpeta que él eligió, y la prueba de la de
     E-R02-05 que lo mira se ha visto fallar con el código de antes; caen las mutaciones
     del umbral, de las 50 y de solo leer; la cadena de comprobación entera está en verde;
     la revisión propia no encuentra nada; y hay una ronda limpia de Codex sobre el head
     de contenido con Quality en verde.
   - **Dos rondas seguidas con hallazgos de la misma familia**: se deja de parchear y se
     busca la raíz (ADR-001).
   - **Si dar la cuenta pidiera tocar la ventana** o cambiar una evaluación, se para y se le
     pregunta: es producto.
4. **Qué lo haría imposible.**
   - Que la orden y PA-R02-06 cuenten distinto: la orden llama a la cuenta del caso de uso,
     no a una copia suya.
   - Que una orden de consola busque sus datos en otra carpeta que la ventana: una sola
     función los busca, la de `sirius-oye`. Que una orden nueva no la use no lo impide
     nada; lo hace improbable que sea la única que hay.
   - Que la orden de las marcas escriba en su base: la lee con una conexión de solo lectura
     y trabaja sobre una copia. La prueba tiene cogido el cerrojo de escritura de su base
     mientras corre la orden: cualquier escritura fallaría.

## Contexto y problema

La 0.2 está programada entera y le quedan las cinco evaluaciones del propietario, que
hace en su ordenador (ADR-241). Las que piden una cifra tienen su orden, E-R02-04 y
E-R02-05 (`scripts/pasar_el_banco_de_memoria.py` y `scripts/medir_busqueda_de_memoria.py`),
o la da su ventana, E-R02-01 y E-R02-03. La de E-R02-02 no tiene ninguna; y la de E-R02-05
lee la base de la carpeta de serie.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

1. **Una orden**, como las de E-R02-04 y E-R02-05.
2. **Enseñar la cuenta en la ventana.**

## Decisión

La opción 1. Lo que quede por decidir al escribir el código se anota aquí con su porqué.

De paso, en los documentos, las rondas limpias de Codex que no se pudieron anotar en sus
PR sin cambiar el head que revisaron: la de ADR-245 (PR #690) y la de ADR-246 (PR #691).

## Comprobación que la sostiene

Se escribe al acabar.

## Consecuencias

Se escriben al acabar.

## Alternativas descartadas y por qué

- **Enseñar la cuenta en la ventana** (opción 2): cambia la ventana, y nadie lo ha pedido.

## La lección

- ninguna: esta es la nota de arranque; si deja una lección, se escribe al acabar.

## Revisión externa

Alcance, escrito antes de la primera petición: esta PR trae la orden de E-R02-02, el arreglo
de la de E-R02-05 y los dos apuntes de las rondas limpias, y nada más. Mira que la orden
cuente como PA-R02-06, que las dos lean la base que abre la ventana y que la de las marcas
no escriba en ella, y que lo que dicen al propietario sea cierto en cada caso.
