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

Después de publicar la nota, el mismo 16-10-2026, él pasó E-R02-05 en su Windows: la orden
midió las dos memorias y se rompió al borrar su carpeta temporal, «está siendo utilizado
por otro proceso» (WinError 32) sobre `prueba.db`, sin llegar a decir si pasaba. En Linux
se borra un fichero abierto, y por eso su prueba pasaba. Es la misma orden, se arregla en
esta PR y va a la misma entrada del registro de defectos.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3. Lo de Windows llegó después de publicarla y se mide con
la misma vara: la prueba que lo mira se ve fallar con el código de antes.

## Opciones consideradas

1. **Una orden**, como las de E-R02-04 y E-R02-05.
2. **Enseñar la cuenta en la ventana.**

## Decisión

La opción 1: una orden da la cuenta de PA-R02-06 sobre una copia de su base, sin escribir
en ella; y la de E-R02-05 busca su base donde la ventana, cierra todo lo que abre y dice si
pasa antes de borrar su carpeta. En detalle:

- **La orden de las marcas**, `scripts/contar_las_marcas.py`. Copia su base con una
  conexión de solo lectura (`?mode=ro`), pone la copia al día con las migraciones, por si
  su base es de una versión anterior, y cuenta sobre la copia con
  `MarkReplyUseCase.count(50)`, la cuenta de PA-R02-06. Los modelos que nombra salen de
  `MarkReplyUseCase.recent(50)`, que es de donde cuenta `count`: no pueden ser de otras
  respuestas. Dice:
  - con 50 marcadas o más: cuántas «eso es Sirius» y «eso no» hay entre las últimas 50,
    qué modelos las dieron y «Pasa: 40 de 50, y hacen falta 40.» o «No pasa: …»;
  - con menos: cuántas lleva, de cuáles, y cuántas faltan;
  - si Sirius no sabe dónde están sus datos, o allí no hay base: «Abre Sirius una vez con
    su ventana».

  Sale con 0, 1, 2 o 3, uno por caso.
- **Dónde buscan su base las órdenes**: `known_data_paths`, en
  `src/sirius/composition_root.py`, que es la resolución que tenía `sirius-oye`
  (`DataLocationUseCase`), sacada de allí sin cambiarla. La usan `sirius-oye`, la orden de
  las marcas y la de E-R02-05, y las tres dicen lo mismo cuando no sabe dónde están:
  `DATA_PATHS_UNKNOWN`, la frase de `sirius-oye`. Resolverla puede guardar el puntero de una
  instalación antigua que vive en la carpeta de serie, como hace la ventana al abrirse: es
  un fichero de la configuración, no su base.
- **La orden de E-R02-05** busca su base con esa función, y si Sirius no sabe dónde está,
  lo dice y sale con 4, en vez de medir una memoria vacía. Cierra las cinco bases que abre
  para buscar: las de decisiones y proyectos se quedaban abiertas, dos por memoria medida.
  Y dice si pasa antes de borrar su carpeta.
- **La carpeta temporal**, `temporary_folder` en
  `src/sirius/infrastructure/temporary_folder.py`, para las dos órdenes: se borra al salir
  y, si no se puede, lo avisa después de lo que la orden ya dijo, sin tapar el veredicto ni
  su código de salida.
- **La orden de E-R02-04 no se toca**: la va a cambiar otro trabajo, por su resultado en su
  ordenador. Se midió que no deja ninguna base abierta (abajo).
- **La ventana no se toca.**

De paso, en los documentos, las rondas limpias de Codex que no se pudieron anotar en sus
PR sin cambiar el head que revisaron: la de ADR-245 (PR #690) y la de ADR-246 (PR #691).

## Comprobación que la sostiene

- **Los tres fallos de la orden de E-R02-05, reproducidos antes de arreglarlos**, con sus
  pruebas en `tests/integration/test_medir_busqueda_de_memoria.py` sobre el código de
  `main`:
  - con su base en una carpeta elegida y un recuerdo dentro, la orden dijo «Tu memoria,
    0 recuerdos» y «Pasa: sí.»;
  - al borrar la carpeta temporal seguían abiertos cuatro ficheros, `prueba.db` dos veces y
    `su-memoria.db` dos veces, que en Windows no se dejan borrar;
  - y si borrar fallaba, la orden se rompía con el `PermissionError` y no decía si pasaba.

  Con el arreglo, las tres pasan. Los ficheros abiertos se miran en `/proc/self/fd` con el
  recolector de ciclos apagado (`tests/unit/_bases_abiertas.py`): con él encendido, a veces
  cerraría las conexiones antes de borrar y la prueba pasaría por suerte.
- **La orden de E-R02-04**, medida igual: con un caso de cada familia del banco y con 12
  casos por `pasa_el_banco`, ninguna base queda abierta al acabar.
- **La orden de las marcas, de punta a punta**, con Sirius de verdad, el conductor de la
  0.2 (`tests/integration/test_contar_las_marcas.py`, 9 pruebas): cuenta lo mismo que
  PA-R02-06 con sus mismas 60 marcas, 40 de 50; con 39 no pasa; con 23 dice cuántas faltan;
  sin ninguna, que faltan 50; sin saber dónde están sus datos, que abra Sirius; lee la base
  de la carpeta que él eligió; no escribe en su base aunque sea de la versión anterior y
  tenga cogido el cerrojo de escritura; al borrar su carpeta no queda ninguna base abierta;
  y si no puede borrarla, la cuenta queda dicha y lo avisa después.
- **Mutación**: 17 mutaciones, caen 16.
  - De la orden de las marcas: el umbral con `>` y con 39, las 50 cambiadas por 49, la cuenta
    hecha con otra ventana que la de `recent`, migrar su base en su sitio, leer su base sin
    copiarla, no cerrar las marcas, leer la carpeta de serie, y que un fallo al borrar se
    coma el veredicto.
  - De la de E-R02-05: no cerrar las decisiones, no cerrar los proyectos, leer la carpeta de
    serie y decir el veredicto después de borrar.
  - Del resto: contar las primeras 50 en vez de las últimas, la función común devolviendo la
    carpeta de serie, y devolviéndola cuando él aún no ha elegido.
  - **Sobrevive una**, quitar `?mode=ro`, y es equivalente: la copia solo lee, así que una
    conexión de lectura y escritura no escribe nada distinto. Queda como segunda puerta: si
    algún día esa conexión escribiera, fallaría.
- **La batería entera** sobre el código: 8 809 en verde, 14 omitidas y 2 `xfail`, ningún
  fallo, en 22 min 34 s. Son 13 pruebas nuevas: 9 de la orden de las marcas y 4 de la de
  E-R02-05.
- **ruff** limpio; **mypy** sin errores en 732 ficheros; **el comprobador de documentos**,
  sin defectos en ADR-245, ADR-246, ADR-247, `PRUEBAS_0.2_DEL_ROBOT.md` y `MEMORIA.md`.

## Consecuencias

- **El propietario tiene la orden de E-R02-02**: `uv run python scripts/contar_las_marcas.py`.
  La puede ejecutar con Sirius abierto: la copia espera si la ventana está guardando.
- **Las últimas 50 son las de la charla, en su orden**, como en PA-R02-06: una respuesta
  vieja que marque hoy cuenta por su sitio en la charla, no por cuándo la marcó.
- **Una respuesta sin modelo apuntado**, de antes de la pieza D de la 0.2, sale como «un
  modelo sin apuntar».
- **La orden de E-R02-05 mide su memoria de verdad** si él eligió otra carpeta, y en su
  Windows acaba diciendo si pasa. Las cifras que dio el 16-10-2026 eran de la base de la
  carpeta de serie, que puede no ser la suya: hay que volver a pasarla.
- **Ninguna prueba corre en Windows**: lo que Windows rechaza, un fichero abierto al
  borrar, se mira en Linux, en `/proc/self/fd`; donde no lo hay, esas dos pruebas se saltan.

## Alternativas descartadas y por qué

- **Enseñar la cuenta en la ventana** (opción 2): cambia la ventana, y nadie lo ha pedido.
- **Leer su base sin copiarla**: con una base de la versión anterior la cuenta falla, porque
  le faltan columnas, y ponerla al día sería escribir en ella.
- **`TemporaryDirectory(ignore_cleanup_errors=True)`**: no se rompe, pero deja la carpeta sin
  decirlo, y su borrado reintenta por su cuenta de una forma que en Linux no se puede ver
  fallar.
- **Copiar en cada orden la búsqueda de la carpeta**: es como la de E-R02-05 dejó de buscar
  donde la ventana.

## Revisión propia

Antes de empujar se releyó el diff entero contra el código y la nota, y se escribió una
prueba por cada regla nueva. Encontró dos cosas, arregladas:

- **La nota citaba la orden nueva antes de que existiera**, y la guarda de las citas de los
  ADR la rechazó: se nombra por su fichero, sin la ruta, hasta que existe.
- **La orden de E-R02-05 no decía qué significa cada código de salida**, y ahora tiene
  cinco: lo dice su `main`.

## La lección

- familia: `prueba-que-no-puede-ver-lo-que-vigila`
- sin esto se repetiría: probar una orden que él ejecuta en su ordenador solo como es la
  máquina de las pruebas. La de E-R02-05 pasaba en Linux con la carpeta de serie, y en su
  ordenador falló por las dos cosas que su prueba no podía ver: la carpeta que él eligió y
  que Windows no borra un fichero abierto (H-247).
- lo hace cumplir: `tests/integration/test_medir_busqueda_de_memoria.py`

## Revisión externa

Alcance, escrito antes de la primera petición: esta PR trae la orden de E-R02-02, el arreglo
de la de E-R02-05 y los dos apuntes de las rondas limpias, y nada más. Mira que la orden
cuente como PA-R02-06, que las dos lean la base que abre la ventana y que la de las marcas
no escriba en ella, y que lo que dicen al propietario sea cierto en cada caso.
