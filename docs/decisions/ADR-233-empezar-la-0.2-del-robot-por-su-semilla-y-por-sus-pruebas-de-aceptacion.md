# ADR-233 — Empezar la 0.2 del robot por su semilla y por sus pruebas de aceptación

- Estado: APROBADO
- Fecha: 2026-10-07
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre
  el head de contenido y Quality en verde (ADR-205). El plan que ejecuta lo aprobó el
  propietario el 06-10-2026 (ADR-232), y la orden de empezar la dio el 07-10-2026:
  «Pues venga, ponte a trabajar.»

Este ADR es además la **nota de arranque** de la rama
`claude/la-0-2-del-robot-empieza-por-su-semilla` y de la versión 0.2 de
`docs/evolution/PLAN_DEL_ROBOT.md` (skill `disciplina-evidencia`): las cuatro preguntas y
el criterio de parada están escritos antes del primer cambio de código, antes de
enseñarle al propietario ninguna respuesta candidata y antes de cualquier revisión.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** Hoy Sirius conversa con la semilla de
   0.1, que vive en el código (`src/sirius/domain/identity.py:56-90`). Dice que existe
   «para ayudar al usuario a pensar, debatir, recordar, organizar, decidir y construir»
   (línea 57), que el humor no se usa «para degradar, herir, imponerse» (línea 83) y que
   separa siempre hechos, inferencias y propuestas (línea 68). La enmienda del manual del
   06-10-2026 cambia las tres cosas. La charla va por OpenAI
   (`src/sirius/composition_root.py:294-348`) y no por un modelo local. El arreglo: la
   semilla nueva entra como versión nueva de la identidad, que ya se guarda por versiones
   (`src/sirius/adapters/persistence/sqlite_identity_repository.py:125`), y llega al modelo
   por `render_instructions` (`src/sirius/application/send_message.py:77-128`), que la pone
   en cada turno. **¿Puede el sitio del arreglo observar el fallo?** Una parte sí: que la
   semilla llegue entera a cada petición lo ve una prueba. La otra no: que suene a Sirius
   no lo ve ninguna máquina, lo ve el propietario. Por eso la semilla se hace con sus
   marcas y la versión acaba con su evaluación (§3 del plan).
2. **Qué NO garantiza.**
   - Las pruebas automáticas usan dobles deterministas. Demuestran que la semilla, los
     modos y las marcas llegan donde deben. No demuestran que Sirius tenga gracia.
   - En el contenedor de las sesiones no hay Ollama con modelos reales. La prueba a
     ciegas, el juez, las 40 preguntas trampa con respuestas reales, el banco de memoria
     con búsqueda por significado real y los 150 ms se miden en el ordenador del
     propietario. Cada prueba lo dice.
   - Las respuestas candidatas que se le enseñan las escribe una sesión. No son palabras
     del propietario: solo entran en la semilla las que él marque «eso es Sirius».
   - En 0.2 Sirius no ve quién tiene delante, porque la cámara llega en 0.4. El corte con
     críos y ancianos frágiles depende de que se lo digan.
   - No garantiza que un modelo pequeño tenga gracia en español. Es el primer riesgo del
     plan (§10), y lo decide la prueba a ciegas.
3. **Criterio de parada**, fijado antes de ver ninguna marca ni ninguna revisión:
   - **La semilla.** Se le enseñan 24 respuestas candidatas. Si marca 15 o más «eso es
     Sirius», la semilla lleva esas, hasta 20. Si marca menos de 15, se reescriben las
     rechazadas con sus comentarios y se le enseñan solo esas, una vez. Si después de esa
     segunda tanda no se llega a 15, se deja de escribir candidatas, porque el fallo es del
     enfoque: se le pide que diga él cómo lo diría Sirius en cinco de ellas.
   - Si rechaza el texto de valores, no se parchea frase a frase: se rehace desde la
     enmienda del manual.
   - **Las PR de la 0.2.** Cada una se fusiona con la cadena de comprobación verde, una
     ronda limpia de Codex sobre el head de contenido y Quality en verde (ADR-205). Como
     mucho tres rondas por PR, por la orden del propietario de no gastar en rondas («Nada
     de cinco rondas, nada de siete rondas»): lo cierto de la tercera se corrige en un
     solo commit, con su prueba vista fallar, y se fusiona sin cuarta.
   - Si dos rondas seguidas encuentran defectos de la misma familia, se deja de parchear y
     se busca la raíz.
   - Si una pieza pide dinero o cambia el producto, por ejemplo un modelo que no cabe en
     su gráfica o entrenar fuera de su ordenador, se para y se le pregunta.
4. **Qué lo haría imposible.**
   - **Que pierda la semilla en una charla larga.** `render_instructions` la pone en cada
     turno, y una prueba fija que toda petición al modelo la lleva, también cuando la
     charla ya está resumida. Eso lo hace imposible por construcción.
   - **Que se le entrene por «me gusta»**, que es lo que volvió pelota a ChatGPT en abril
     de 2025. Los botones solo recogen «eso es Sirius» o «eso no». La marca «me gusta» no
     existe, así que no hay con qué entrenarle mal.
   - **Que olvidar no borre.** La prueba busca el texto olvidado en todas las tablas de la
     base, resúmenes incluidos.
   - **Que lo que dice Sirius cuente como hecho del propietario.** Cada hecho lleva quién lo
     dijo, y un hecho sacado de un mensaje de Sirius se rechaza por su tipo.
   - **Lo que no se puede hacer imposible:** que un modelo no adule nunca y que tenga
     gracia. Se hace improbable con las 40 preguntas trampa, el juez y las marcas.

## Contexto y problema

El propietario aprobó el plan del robot el 06-10-2026 y el 07-10 dio la orden de empezar.
La versión 0.2 es «Sirius en texto: personalidad y memoria» (§4 del plan). Su primer paso
es la semilla nueva, «con las palabras del propietario», escrita «como valores y razones,
no como prohibiciones», con «de 15 a 20 ejemplos de charla». La parte del propietario es
«hacer la semilla con la sesión, la prueba a ciegas y marcar respuestas».

La §3 del plan pide que las pruebas de aceptación se escriban antes de la primera línea de
código de la versión: con pytest lo que una máquina puede comprobar y como evaluación
humana lo que solo puede juzgar el propietario.

Lo único de la 0.2 que espera al propietario es la semilla. Todo lo demás lo programan las
sesiones.

## Opciones consideradas

1. **Empezar por el código**, el conector de Ollama, y dejar la semilla para después. La
   §3 lo impide, porque las pruebas de aceptación van antes del código. Además dejaría al
   propietario esperando sin nada que hacer.
2. **Empezar por la semilla con sus marcas y, a la vez, por las pruebas de aceptación.** Él
   marca mientras la sesión escribe las pruebas.
3. **Que las respuestas candidatas las escriba un modelo local en el contenedor.** No hay
   Ollama con modelos reales aquí, y bajar varios gigas en cada sesión es gasto sin
   retorno. Los modelos se comparan en la prueba a ciegas, que es su sitio.

## Decisión

Se adopta la opción 2.

**Cómo se hace la semilla.** La sesión escribe el texto de valores con las palabras de la
enmienda y 24 respuestas candidatas que cubren las situaciones del plan: pique diario,
ideas malas del propietario, «ponte serio», «para», una mala noticia, desconocidos, un
crío delante, decir «no lo sé», sus opiniones y algo sin sentido. Se le enseñan en una
página privada con dos botones por respuesta, «eso es Sirius» y «eso no», y una casilla
opcional para decir cómo lo diría. Las candidatas son textos escritos por la sesión, no
conversaciones suyas. A la semilla solo entran las que él marque.

**El orden de la 0.2**, una PR por pieza, cada una con sus pruebas de aceptación pasando de
esperadas a verdes:

| Pieza | Qué trae |
|---|---|
| A | Esta nota y las pruebas de aceptación de toda la 0.2, antes del código |
| B | La semilla, cuando el propietario la marque |
| C | Ollama para la charla y la herramienta de la prueba a ciegas |
| D | «Ponte serio» y «para», lo de la deriva y los dos botones |
| E | La memoria propia de Sirius, el juez y las 40 preguntas trampa |
| F | El banco de memoria de 100 casos y la búsqueda por significado. Sale el filtro de Ollama de cada respuesta |
| G | Hechos con fecha y con quién lo dijo, la ficha por persona, «eso no es así», «olvida eso», «¿qué sabes de mí?» y el «sueño» |

**Las pruebas de aceptación** se llaman `PA-R02-NN` y viven en
`docs/evolution/PRUEBAS_0.2_DEL_ROBOT.md`: 18, con 39 pruebas de máquina y cinco
evaluaciones del propietario, E-R02-01 a E-R02-05, con sus umbrales fijados antes de
medir.

- **Hablan como el plan.** Las pruebas de máquina, en `tests/acceptance/test_robot_0_2_*.py`,
  dicen «el propietario dice», «ponte serio», «eso es Sirius» u «olvida eso». Solo un
  conductor, `tests/acceptance/conductor_robot_0_2.py`, sabe cómo se hace cada cosa en el
  código. El conductor no implementa nada de Sirius: monta la aplicación con
  `build_conversation_dependencies`, como la ventana, y pone un modelo que graba lo que
  recibe. Cuando entra una pieza, cambia su parte del conductor y no las pruebas.
- **Una prueba de una pieza que no ha entrado no corre.** El decorador `pieza(...)` la
  para al empezar con `PiezaPendiente`, bajo un `xfail` estricto que solo acepta esa
  excepción. Al entrar la pieza, su letra pasa a `PIEZAS_ENTREGADAS` y la prueba corre
  entera. La primera versión dejaba correr los pasos que ya existen hasta llegar a lo
  pendiente, y una prueba de la pieza G falló por una aserción y no por la pieza. Ese
  fallo habría vuelto cada vez que entrara una pieza anterior, así que se cortó de raíz.
- **La tabla se comprueba por máquina**, como la de ADR-006:
  `tests/acceptance/test_robot_0_2_trazabilidad.py` falla si nombra una prueba que no
  existe, si deja una sin fila, si las piezas de una fila no cuadran con las de sus
  pruebas o si dice «en verde» de una pieza que no ha entrado.
- **El inventario aprobado no se reduce.** La comprobación guarda, aparte de la tabla y
  de las pruebas, cuántas pruebas de máquina tiene como poco cada PA y qué evaluaciones
  hay. Quitar una es retirar una prueba, que según `AGENTS.md` no hace una sesión sola:
  se cambia ese inventario, a la vista de la revisión.

## Comprobación que la sostiene

- La semilla vigente es la de 0.1: `sed -n 56,90p src/sirius/domain/identity.py` enseña las
  tres frases citadas en la nota, en las líneas 57, 68 y 83.
- La charla no tiene camino local: `src/sirius/config/llm_provider_settings.py:28-32`
  define solo dos proveedores, `fake` y `openai`.
- Nadie más trabaja en estos ficheros: el 07-10-2026 la API de GitHub devolvió 0 PR
  abiertas, con respuesta 200, y `scripts/automation/sirius_obra_en_curso.py` respondió
  libre.
- Las 39 pruebas de máquina se ven fallar por la razón esperada:
  `uv run --no-sync pytest -q tests/acceptance/test_robot_0_2_personalidad.py
  tests/acceptance/test_robot_0_2_memoria.py tests/acceptance/test_robot_0_2_ventana.py`
  da 39 xfailed en 2,0 s, cada una con su pieza. Eran 32 hasta la ronda 2 de Codex.
- La comprobación de la tabla, vista fallar dos veces: con la fila PA-R02-01 en «en verde»
  y una prueba quitada de PA-R02-17, falla con los dos defectos; con el documento como
  está, sus 12 pruebas pasan. Nueve de ellas le dan tablas rotas a propósito.
- Una pieza declarada sin código se ve fallar: con «B» en `PIEZAS_ENTREGADAS` y sin la
  semilla, las dos pruebas de PA-R02-01 fallan en rojo, no como `xfail`.

## Consecuencias

- El propietario recibe primero la semilla para marcar, y mientras marca la sesión escribe
  las pruebas de aceptación.
- La batería tendrá 39 pruebas `xfail` estrictas de la 0.2 hasta que entre cada pieza. Se
  suman a las dos de M11, que siguen como estaban.
- Las pruebas fijan nombres que todavía no existen en el código, como los del conductor y
  los de la ventana: «Eso es Sirius», «Eso no» y «Modo serio». Si una pieza necesita
  cambiar una prueba, el cambio se dice en su PR, y nunca para aflojarla.

## Alternativas descartadas y por qué

- **Enseñarle las candidatas en una lista dentro del chat.** Son 24 respuestas: en el
  móvil, una lista así es larga de leer y de contestar. Los botones le quitan trabajo.
- **Escribir la semilla sin él.** El plan dice que la semilla se hace con él, y la §3 del
  manual enmendado dice que la identidad es lo que se le enseña.

## La lección

- ninguna: lo único que mordió, la prueba que fallaba por otra razón, se cortó antes del
  primer commit de las pruebas, y el arreglo vive en `pieza(...)`, que explica por qué en
  su propio texto. La versión siguiente copiará el conductor, con el arreglo dentro.

## Revisión externa

- **Ronda 1 de Codex, sobre `def8e06e`**: un P2, cierto. La comprobación de la tabla
  deducía las PA esperadas del número de filas, así que quitar a la vez la PA-R02-18 y
  sus dos pruebas pasaba sin ruido. Ahora compara con un inventario aprobado que vive en
  la comprobación: 18 PA, cuántas pruebas pide cada una, 32 en total, y las cinco
  evaluaciones. Visto en los dos sentidos sobre los ficheros de verdad: con la fila 18 y
  sus pruebas quitadas, la comprobación vieja pasa y la nueva falla.
- **Ronda 2 de Codex, sobre `f638e633`**: dos P2, ciertos, y de una familia nueva: una
  cláusula del §4 sin prueba que la vigile. Faltaba que las marcas «eso es Sirius» se le
  enseñen como lo que sí es (pasos 3 y 5), y que cada hecho guarde quién lo dijo y con qué
  seguridad (memoria, paso 3). La raíz es que las pruebas salieron de cada paso del plan,
  no de cada cláusula. Así que, antes de arreglar, se repasó el §4 cláusula a cláusula, y
  salieron seis más sin prueba:
  - el vacile al entrar en el modo serio (paso 4);
  - que el aviso del juez se vea en la ventana (paso 7);
  - la búsqueda por significado (memoria, paso 2), con un doble de huellas en el que la
    pregunta y el recuerdo no comparten ni una palabra;
  - dejar de etiquetar recuerdos por categorías con la ventana abierta (se deja de hacer);
  - el resumen del día en el sueño, sin leer a Sirius (memoria, paso 4);
  - que la ficha junte lo que el propietario dijo de esa persona (memoria, paso 5).

  Entran siete pruebas nuevas y se endurecen dos: la de la ficha y la de «eso no es así»,
  que ahora mira que la corrección conserva quién dijo el hecho de antes. El inventario
  aprobado pasa de 32 a 39 pruebas. Lo que una prueba no puede ver se añade a «Lo que estas
  pruebas no garantizan»: cuándo arranca el sueño, la retirada del banco de 47 casos y las
  órdenes por voz. La comprobación de la tabla se ve fallar quitando de su fila la prueba
  nueva del vacile: pide 4 pruebas a PA-R02-04 y ve 3.
- **Ronda 3 de Codex, sobre `c6128c6e`**: ocho P2, ciertos los ocho. Se corrigen en un
  solo commit y la PR se fusiona sin cuarta ronda, como fija el criterio de parada.
  - Cuatro repiten la familia de la ronda 2, cláusulas del §4 sin prueba ni mención: la
    semilla escrita como valores, que no repita ejemplos ni chistes, las huellas en la
    misma base y las bibliotecas que no se usan. Dos rondas seguidas con la misma familia:
    se paró a buscar la raíz. El repaso de la ronda 2 dio por invisibles algunas frases sin
    declararlas, y no miró «Con qué», «No se usa» ni «Dinero». Esta vez se repasó el §4
    frase a frase, y cada frase tiene su prueba o su línea en «Lo que estas pruebas no
    garantizan». Salieron además el dinero, el entrenamiento de 0.5, la cara y la voz de
    0.4 y lo que se reutiliza de 0.1. Las bibliotecas excluidas las vigila una guarda
    nueva, `tests/automation/test_memoria_sin_bibliotecas_excluidas.py`, vista fallar con
    `mem0ai` en las dependencias.
  - Los otros cuatro son de otra familia, pruebas que pasarían sin su pieza: la búsqueda
    por significado ganaba por orden de guardado, el resumen del día no se miraba tras
    reabrir, el aviso del juez no tenía que desaparecer al recuperarse y el etiquetado por
    categorías podía seguir por otra vía. Las cuatro pruebas se endurecen. El inventario
    sigue en 39.
