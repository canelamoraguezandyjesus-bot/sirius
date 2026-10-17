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

## Nota de arranque del diagnóstico del banco

Escrita el 16-10-2026, después de lo anterior y antes de tocar
`scripts/pasar_el_banco_de_memoria.py` y de cualquier revisión.

1. **Dónde vive el fallo y dónde va el arreglo.** En su ordenador el banco de memoria de
   E-R02-04 dio 70 de 100 con su modelo de huellas de verdad, `qwen3-embedding:0.6b`. Según
   lo que investigó otra sesión el mismo día, con solo palabras serían 64, y con las huellas
   de mentira de las pruebas salen 99. Los fallos de «cosas que cambian» y el de MB-071 se
   explican leyendo la lógica; los 17 de personas, gustos y fechas no se pueden explicar
   sin ver los parecidos que da su modelo. Lo que falta aquí es medir, no arreglar:
   - **La orden de E-R02-04** gana `--diagnostico`: además de lo de siempre, una línea por
     cada uno de los 100 casos, con lo que llegó al modelo y en qué orden, el puesto por
     palabras de cada recuerdo, el parecido de la pregunta con cada recuerdo y el de los
     recuerdos entre sí, como se piden hoy y con el formato que recomienda cada modelo, y
     el umbral en vigor. Y `--modelo`, para pasarlo con otro modelo de huellas, como
     EmbeddingGemma, sin tocar sus ajustes.
   - **La de E-R02-05** gana `--modelo` también.
   - **El umbral y el formato no se tocan aquí**: se decidirán con sus cifras, en el trabajo
     siguiente.

   **¿Puede el sitio del arreglo observar el fallo?** Sí: cada línea sale del mismo Sirius
   que pasa el caso, por el camino real y con su modelo de verdad, después de preguntarle.
   Por qué su modelo da esos parecidos, no lo observa nadie.
2. **Qué NO garantiza.**
   - Que con esas cifras se llegue a 90 de 100: lo dirá el trabajo siguiente.
   - Que los parecidos sean los de la búsqueda hasta el último decimal: la búsqueda los
     calcula en sqlite-vec con números de 32 bits, y la línea, en Python sobre las mismas
     huellas que da Ollama. Van con cuatro decimales.
   - Que el formato recomendado sea el de su versión de cada modelo: es el de su ficha.
3. **Criterio de parada**, fijado antes de escribir código:
   - **Terminado** cuando las dos opciones funcionan en las dos órdenes; una prueba lee la
     línea de un caso conocido, con huellas de mentira de parecidos sabidos, y la encuentra
     entera; caen las mutaciones de lo que dice la línea (los parecidos, los puestos, el
     orden, el formato de cada modelo, el umbral y el modelo elegido); la cadena entera
     está en verde; y la revisión propia no encuentra nada.
   - **De su base no sale nada**: la línea solo lleva el banco, que es inventado.
   - **Si diagnosticar pidiera cambiar cómo busca Sirius**, se para: eso es el arreglo, y va
     aparte.
4. **Qué lo haría imposible.**
   - Que la línea cuente otra cosa que el camino real: se escribe dentro del mismo caso,
     con el mismo Sirius, y el umbral se lee de donde lo lee la búsqueda.
   - Que no se pueda reconstruir aquí: cada línea lleva todos los parecidos entre la
     pregunta y los tres recuerdos, en cada formato, y con eso se rehacen huellas con los
     mismos cosenos.

## Nota de arranque de las hojas en su pantalla

Escrita el 17-10-2026, antes de tocar las tres hojas y de cualquier revisión. Va en este
ADR y no en uno nuevo porque `MEMORIA.md` no tiene sitio para otro: le quedan 7 bytes.

1. **Dónde vive el fallo y dónde va el arreglo.** En su ordenador, la hoja de la prueba a
   ciegas no se podía usar: un modelo repitió la semilla entera, y la hoja se hizo más
   ancha y más alta que la pantalla. No se podía bajar ni leer, «Siguiente» quedaba fuera,
   y no tenía ni para minimizar. Reproducido aquí con una respuesta de 3 000 caracteres en
   una pantalla de 800 × 800:
   - **La prueba a ciegas.** `src/sirius/presentation/blind_test_dialog.py` pone cada
     respuesta como texto de su `QRadioButton`, que no parte las líneas: la hoja mide
     15 387 px de ancho, y «Siguiente» empieza a 7 695 px de su borde.
   - **Las preguntas trampa.** `trick_questions_dialog.py` sí parte las líneas, pero no se
     baja: a la respuesta de Sirius le tocan 375 px de los 495 que necesita, y el final no
     se ve.
   - **Ninguna de las tres**, tampoco la de voces (`voice_test_dialog.py`), tiene botones
     de minimizar ni de maximizar.

   El arreglo va en las tres hojas, sin rediseñarlas: cada respuesta de la prueba a ciegas
   con su botón de elegir y su texto en una etiqueta que parte las líneas, con la letra, el
   clic, también en el texto, y `choose_letter` como hoy; cada paso de las tres, dentro de
   una barra para bajar; y las tres con botones de minimizar, maximizar y cerrar, sin el
   «?» de ayuda, que cambian de tamaño y se abren a dos tercios de la pantalla disponible.

   **¿Puede el sitio del arreglo observar el fallo?** Sí: son las hojas las que deciden su
   tamaño, y una prueba de interfaz las abre con una respuesta de 3 000 caracteres y las
   mide contra la pantalla.
2. **Qué NO garantiza.**
   - Que en su pantalla se vea igual: aquí se mide en una de 800 × 800 sin Windows, y lo
     dirá él.
   - Cómo minimiza Windows una hoja que depende de la ventana de Sirius y la deja quieta
     mientras está abierta: eso también lo verá él.
   - Que una respuesta larguísima se lea cómoda: se lee entera, bajando.
3. **Criterio de parada**, fijado antes de escribir código:
   - **Terminado** cuando, con una respuesta de 3 000 caracteres, las pruebas ven con el
     código de hoy que la prueba a ciegas pasa del ancho de la pantalla y que las
     preguntas trampa no se bajan, y con el arreglo las dos caben y se bajan hasta sus
     botones; otra prueba mira en las tres los botones de minimizar, maximizar y cerrar sin
     el «?», que cambian de tamaño, que se abren dentro de la pantalla y que cada paso se
     baja; pulsar el texto de una respuesta la elige; caen las mutaciones de cada pieza;
     ruff, mypy y las pruebas de la interfaz están en verde; y la revisión propia no
     encuentra nada.
   - **Si arreglarlo pidiera cambiar los pasos o lo que dicen**, se para: eso es rediseñar.
4. **Qué lo haría imposible.** Que un texto largo vuelva a ensanchar una hoja: las
   respuestas van en etiquetas que parten las líneas, y cada paso, dentro de su barra. Y
   que una hoja se abra más grande que la pantalla: se abre a dos tercios de la disponible.

**Añadido el 17-10-2026, antes de tocar la lista de modelos de la prueba a ciegas:**

1. **Dónde vive el fallo y dónde va el arreglo.** La prueba a ciegas ofrece también los
   modelos de huellas: `list_installed_models`, en `src/sirius/adapters/llm/ollama_chat.py`,
   devuelve todo lo que dice `/api/tags`, y él tiene `embeddinggemma` y
   `qwen3-embedding:0.6b`. Si marca uno, la prueba falla después de muchos minutos, y el
   aviso no dice qué hacer. El arreglo:
   - **La prueba a ciegas solo ofrece los modelos que conversan**: los que, según
     `/api/show`, saben hacer `completion`. Se pregunta a la misma dirección fija, sin
     proxies. Si no contesta o no dice qué sabe hacer, ese modelo se queda fuera con su
     motivo, y los demás se ofrecen igual. La hoja dice cuáles se quedan fuera y por qué.
   - **El aviso de un modelo que no contesta dice qué hacer**: «Vuelve a pulsar Empezar; si
     se repite, desmarca ese modelo».

   **¿Puede el sitio del arreglo observar el fallo?** Sí: el caso de uso de la prueba hace
   la lista, y una prueba con un Ollama de mentira que tiene un modelo de huellas mira lo
   que ofrece.
2. **Qué NO garantiza.**
   - Que su Ollama diga `capabilities`: si es tan viejo que no lo dice, todos sus modelos
     se quedan fuera, cada uno con su motivo.
   - Que un modelo que conversa conteste bien en la prueba: solo que sabe conversar.
3. **Criterio de parada**, fijado antes de escribir código:
   - **Terminado** cuando, con un Ollama de mentira que tiene un modelo de huellas, las
     pruebas ven con el código de hoy que la prueba lo ofrece y con el arreglo no, y la
     hoja dice por qué; un modelo cuyo `/api/show` no contesta o no dice qué sabe hacer se
     queda fuera sin romper la lista; la pregunta va a la dirección fija y sin proxies; el
     aviso dice qué hacer; caen las mutaciones; ruff, mypy y las pruebas de la prueba a
     ciegas y de Ollama están en verde; y la revisión propia no encuentra nada.
   - **Si filtrar pidiera cambiar cómo se elige o se guarda el modelo**, se para.
4. **Qué lo haría imposible.** Que la prueba ofrezca un modelo que no conversa: solo entra
   en la lista el que `/api/show` dice que sabe hacer `completion`.

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

La opción 1: una orden da la cuenta de las marcas, y la de E-R02-05 mide su base y acaba.

En detalle, la orden da la cuenta de PA-R02-06 sobre una copia de su base, sin escribir en
ella; y la de E-R02-05 busca su base donde la ventana, cierra todo lo que abre y dice si
pasa antes de borrar su carpeta:

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
- **El diagnóstico del banco de E-R02-04**, con su propia nota de arranque, arriba:
  - `--diagnostico` escribe primero una línea que dice cómo se leen las demás, y después
    una por caso, en JSON, según pasa: el id, la familia, si acierta, qué recuerdos del
    caso llegaron al modelo y en qué orden, el que tenía que llegar el primero, el puesto
    de cada uno en la búsqueda por palabras, el parecido de la pregunta con cada recuerdo y
    el de cada par de recuerdos, como se piden hoy y con el formato del modelo, y el
    umbral. Lo de siempre va después.
  - Todo sale del mismo caso, después de preguntar: los parecidos con el mismo modelo y el
    coseno que mide la búsqueda; los puestos, de la búsqueda por palabras del turno; y el
    umbral y el límite de esa búsqueda, del módulo de la búsqueda al escribir la línea.
  - Los formatos son los de la ficha de cada modelo. Qwen3-Embedding pide la pregunta con
    su instrucción, `Instruct: Given a question, retrieve the memories that answer it` y
    `Query:`, y los recuerdos tal cual; EmbeddingGemma, `task: search result | query:` y
    `title: none | text:`. Se reconocen por el nombre del modelo en Ollama, y si no es
    ninguno de los dos, la línea dice `null` en vez de inventarlo.
  - `--modelo NOMBRE`, en las dos órdenes de la memoria: el modelo de huellas con el que se
    pasan, sin tocar sus ajustes. Sin él, el de los ajustes, como hasta ahora.
  - Lo que cuenta si un caso acierta no cambia: se saca a `acierta`, para que el
    diagnóstico diga lo mismo que el recuento.
- **La ventana no se toca.**
- **Las hojas en su pantalla**, con su propia nota de arranque, arriba, y sin rediseñarlas:
  - **Las tres comparten `src/sirius/presentation/sheet_window.py`**: `scrollable` mete un
    paso en una barra para bajar que le da el ancho de la hoja, y `fit_as_sheet` les pone
    los botones de minimizar, maximizar y cerrar, sin el «?» de ayuda, y las abre a dos
    tercios de la pantalla disponible donde está Sirius, nunca por debajo de lo menos que
    miden. Cambian de tamaño como cualquier ventana.
  - **Cada paso de las tres va en su propia barra**, también los cortos. Los botones de
    cada paso van con él: «Siguiente» se alcanza bajando hasta el final de las respuestas.
  - **Cada respuesta de la prueba a ciegas** lleva su botón de elegir con la letra, «A)», y
    al lado su texto, en una etiqueta que parte las líneas y lo enseña tal cual, sin
    pintarlo como HTML, como hacía el botón. Pulsar el texto es pulsar el botón, y
    `choose_letter` y lo que se guarda no cambian.
- **La prueba a ciegas, solo con modelos que conversan**, con su añadido a la nota de las
  hojas, arriba:
  - **El conector pregunta a `/api/show` qué sabe hacer cada modelo**
    (`model_capabilities`), a la dirección fija de siempre y sin los proxies del sistema,
    con diez segundos de espera: decirlo no carga el modelo.
  - **El caso de uso de la prueba ofrece solo los que dicen `completion`**, y deja los
    demás fuera con su motivo: «no conversa», o lo que falló al preguntarlo. Los demás se
    ofrecen igual, y la hoja lo dice debajo de la lista.
  - **El aviso de un modelo que no contesta o no termina** acaba en «Vuelve a pulsar
    Empezar; si se repite, desmarca ese modelo.»

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
- **El diagnóstico del banco** (`tests/integration/test_pasar_el_banco_de_memoria.py`, 8
  pruebas), con huellas de mentira de parecidos sabidos y de largos distintos, para que el
  producto no pase por el coseno: la línea de MB-001 sale entera y se lee de vuelta igual;
  con EmbeddingGemma pide la pregunta y los recuerdos con su formato, y lo de hoy sigue tal
  cual; con un modelo desconocido, `null`; con el umbral subido a 0,7, la línea lo dice y
  el café, que se parece 0,6, ya no llega; `--diagnostico` escribe una línea por caso y
  después lo de siempre, y sin él ninguna; y `--modelo` elige el modelo en las dos órdenes
  sin tocar sus ajustes.
- **La orden de las marcas, de punta a punta**, con Sirius de verdad, el conductor de la
  0.2 (`tests/integration/test_contar_las_marcas.py`, 9 pruebas): cuenta lo mismo que
  PA-R02-06 con sus mismas 60 marcas, 40 de 50; con 39 no pasa; con 23 dice cuántas faltan;
  sin ninguna, que faltan 50; sin saber dónde están sus datos, que abra Sirius; lee la base
  de la carpeta que él eligió; no escribe en su base aunque sea de la versión anterior y
  tenga cogido el cerrojo de escritura; al borrar su carpeta no queda ninguna base abierta;
  y si no puede borrarla, la cuenta queda dicha y lo avisa después.
- **Mutación**: 31 mutaciones, caen 30.
  - De la orden de las marcas: el umbral con `>` y con 39, las 50 cambiadas por 49, la cuenta
    hecha con otra ventana que la de `recent`, migrar su base en su sitio, leer su base sin
    copiarla, no cerrar las marcas, leer la carpeta de serie, y que un fallo al borrar se
    coma el veredicto.
  - De la de E-R02-05: no cerrar las decisiones, no cerrar los proyectos, leer la carpeta de
    serie y decir el veredicto después de borrar.
  - Del resto: contar las primeras 50 en vez de las últimas, la función común devolviendo la
    carpeta de serie, y devolviéndola cuando él aún no ha elegido.
  - Del diagnóstico y `--modelo`, caen las 14: el producto en vez del coseno, cada par
    consigo mismo, los puestos desde 1, lo traído al revés, el formato de Qwen con un
    espacio tras `Query:`, los recuerdos de EmbeddingGemma sin su `title`, ningún formato,
    el umbral escrito a mano, `--modelo` sin efecto en cada una de las dos órdenes,
    `--diagnostico` sin líneas, lo de hoy con el formato, el esperado corrido y la pregunta
    contra los recuerdos al revés.
  - **Sobrevive una**, quitar `?mode=ro`, y es equivalente: la copia solo lee, así que una
    conexión de lectura y escritura no escribe nada distinto. Queda como segunda puerta: si
    algún día esa conexión escribiera, fallaría.
- **La batería entera**, con el diagnóstico: 8 818 en verde, 14 omitidas y 2 `xfail`,
  ningún fallo, en 22 min 50 s. Son 21 pruebas nuevas: 9 de la orden de las marcas, 4 de la
  de E-R02-05 y 8 del diagnóstico y `--modelo`. Antes del diagnóstico eran 8 809, en
  22 min 34 s.
- **ruff** limpio; **mypy** sin errores en 733 ficheros; **el comprobador de documentos**,
  sin defectos en ADR-245, ADR-246, ADR-247, `PRUEBAS_0.2_DEL_ROBOT.md` y `MEMORIA.md`.
- **Las hojas en su pantalla**, con una respuesta de 3 000 caracteres, en la pantalla de
  800 × 800 de las pruebas:
  - con el código de antes, la prueba a ciegas medía 15 387 px de ancho, con «Siguiente» a
    7 695 px de su borde; a la respuesta de las preguntas trampa le tocaban 375 px de los
    495 que necesita, sin poder bajar; y ninguna de las tres tenía minimizar ni maximizar;
  - con el arreglo, las dos se abren a 533 × 533 y se bajan, 144 px y 132 px, sin ir de
    lado, hasta sus botones.

  Seis pruebas nuevas en `tests/gui/`, tres de la prueba a ciegas, dos de las preguntas
  trampa y una de la de voces, con lo que miran en común en
  `tests/unit/_hojas_en_su_pantalla.py`; las seis fallaban con el código de antes. Dos de
  las de antes eligen ahora la respuesta por su texto. Mutación: 16, caen las 16. Las
  pruebas de la interfaz, 565 en verde; **ruff** limpio; **mypy** sin errores en 737
  ficheros.
- **La prueba a ciegas, solo con modelos que conversan**: con un Ollama de mentira como el
  suyo, con `gemma3:4b`, `qwen3:4b-instruct`, `embeddinggemma` y `qwen3-embedding:0.6b`, la
  hoja ofrecía los cuatro con el código de antes; con el arreglo ofrece los dos que
  conversan y dice que los otros dos no conversan. Esa prueba va por el camino real, desde
  `build_conversation_dependencies`; además, tres del caso de uso, lo que deja fuera y el
  aviso con un modelo que falla y con otro que acaba sin decir nada, y siete del conector:
  la dirección y lo que pide, cuatro respuestas que no dicen qué sabe hacer, Ollama sin
  contestar y el cliente sin proxies. El Ollama de mentira del conductor de la 0.2 contesta
  ahora `/api/show` como el de verdad. Mutación: 13, caen las 13. Las pruebas de la prueba a
  ciegas y de Ollama, 48 ficheros: 1 206 en verde, 2 omitidas y 2 `xfail`; **ruff**
  limpio; **mypy** sin errores en 737 ficheros.

## Consecuencias

- **Las tres hojas se abren más grandes que antes**, a dos tercios de su pantalla, y se
  pueden minimizar, maximizar y cambiar de tamaño. Cómo minimiza Windows una hoja que
  depende de la ventana de Sirius lo verá él.
- **Una respuesta larga se lee bajando**, y «Siguiente» queda al final de las respuestas.
  Una palabra sin espacios más ancha que la hoja se lee yendo de lado: con una de 2 000
  caracteres, la hoja sigue cabiendo.
- **La prueba a ciegas ya no ofrece los modelos de huellas**, y dice debajo de la lista
  cuáles se quedan fuera y por qué. Con un Ollama que no dijera qué sabe hacer cada modelo,
  todos se quedarían fuera, cada uno con su motivo.
- **Abrir la prueba pregunta a Ollama una vez por modelo**, además de la lista: tarda algo
  más en abrirse, y como mucho diez segundos por modelo si Ollama no contesta.
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
- **Para leer los fallos del banco** él lo pasa con `--diagnostico`, con su modelo y con
  otro por `--modelo`, y pega lo que sale: aquí se rehacen huellas con esos parecidos y se
  prueban por el camino real el umbral y el formato. Hasta entonces no cambia ninguno.
- **Con `--diagnostico` el banco pide dos huellas más por caso**, las de hoy y las del
  formato, y tarda algo más.

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
prueba por cada regla nueva. Encontró cuatro cosas, arregladas:

- **La nota citaba la orden nueva antes de que existiera**, y la guarda de las citas de los
  ADR la rechazó: se nombra por su fichero, sin la ruta, hasta que existe.
- **La orden de E-R02-05 no decía qué significa cada código de salida**, y ahora tiene
  cinco: lo dice su `main`.
- **El bucle del banco llamaba `acierta` a lo que devuelve cada caso**, y con la función
  nueva del mismo nombre se leía como ella: ahora es `bien`.
- **La cabecera del diagnóstico decía «de 0 a 2»**, que vale mientras cada caso tenga tres
  recuerdos: ahora dice «desde 0».

**Las hojas.** Antes de empujar se releyó el diff contra el código y su nota. Encontró
una cosa, arreglada: mypy rechazó la prueba que pulsa el texto de una respuesta con
`qtbot.mouseClick`, que no tiene tipos; pulsa con `QTest.mouseClick`, como las demás.

**La lista de modelos.** Antes de empujar se releyó el diff contra el código y su nota.
Encontró una cosa, arreglada: la prueba de que no se leen los proxies los ponía en el
entorno, y no miraba nada, porque con un transporte enchufado httpx no los usa aunque los
lea. Lo dijo la mutación que vuelve a leerlos, que sobrevivía; ahora la prueba mira el
cliente que se abre, como la de la charla.

## La lección

- familia: `prueba-que-no-puede-ver-lo-que-vigila`
- sin esto se repetiría: probar una orden que él ejecuta en su ordenador solo como es la
  máquina de las pruebas. La de E-R02-05 pasaba en Linux con la carpeta de serie, y en su
  ordenador falló por las dos cosas que su prueba no podía ver: la carpeta que él eligió y
  que Windows no borra un fichero abierto (H-247).
- lo hace cumplir: `tests/integration/test_medir_busqueda_de_memoria.py`

## Revisión externa

Alcance, escrito antes de la primera petición: esta PR trae la orden de E-R02-02, el arreglo
de la de E-R02-05, el diagnóstico del banco de E-R02-04 y los dos apuntes de las rondas
limpias, y nada más. Mira que la orden cuente como PA-R02-06, que las dos lean la base que
abre la ventana y que la de las marcas no escriba en ella, que la línea de cada caso diga lo
que pasó por el camino real, y que lo que dicen al propietario sea cierto en cada caso.

**Alcance añadido para la ronda 2**, escrito antes de pedirla: las tres hojas en su
pantalla. Mira que una respuesta larga no haga ninguna hoja más ancha ni más alta que la
pantalla, que todo se alcance bajando, que la prueba a ciegas elija y guarde como antes, y
que las tres se minimicen, se maximicen y cambien de tamaño. Y la lista de modelos de la
prueba a ciegas: que solo ofrezca los que conversan, que un modelo del que `/api/show` no
dice nada no rompa la lista, y que el aviso diga qué hacer.
