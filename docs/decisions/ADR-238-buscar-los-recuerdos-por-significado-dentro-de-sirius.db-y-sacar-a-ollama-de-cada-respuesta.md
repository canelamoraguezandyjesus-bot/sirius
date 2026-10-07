# ADR-238 — Buscar los recuerdos por significado dentro de sirius.db y sacar a Ollama de cada respuesta

- Estado: APROBADO
- Fecha: 2026-10-07
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Es la pieza F de ADR-233; lo que hace
  sale de los pasos 1 y 2 de la memoria en la 0.2 del plan del robot y de lo que se deja
  de hacer, aprobados por el propietario el 06-10-2026.

## Nota de arranque

Escrita antes del primer commit de la pieza F. El criterio de parada de las rondas es el
de ADR-233.

1. **Dónde vive el fallo y dónde va el arreglo.**
   - Hoy un recuerdo solo llega a la petición si comparte palabras con el mensaje: de
     todos los recuerdos vigentes, el orden solo deja pasar los que acierta la búsqueda
     por palabras (`src/sirius/domain/relevance.py:233-249` y
     `src/sirius/application/rank_relevant_knowledge.py:685-730`). «¿Qué comida me gusta?»
     no trae «Le pirra el cocido».
   - Ollama se mete donde el plan dice que no. Sin ninguna puerta, al abrir la ventana
     etiqueta por categorías cada recuerdo que no tiene, y otra vez al guardar o corregir
     uno (`src/sirius/presentation/knowledge_widget.py`). Con las puertas viejas
     abiertas, además, dentro de cada turno: el filtro de relevancia y el intérprete de
     la pregunta.
   - El arreglo: una huella por recuerdo, guardada en la misma base, `sirius.db`, y
     buscada con sqlite-vec junto con la búsqueda por palabras de siempre. La búsqueda la
     hace el contexto de cada turno. Las huellas las da el modelo de huellas de Ollama, la
     de cada recuerdo en segundo plano al guardarlo y la de la pregunta al empezar el
     turno. Fuera el etiquetado por categorías y los dos usos de Ollama dentro del turno.
   - **¿Puede el sitio del arreglo observar el fallo?** Lo que encuentra la búsqueda, sí:
     PA-R02-11 la mira con un doble de huellas en el que la pregunta y el recuerdo no
     comparten ni una palabra. Que encuentre lo que él quiere decir con el modelo de
     verdad no lo ve ninguna máquina de aquí: lo mide E-R02-04 en su ordenador.
2. **Qué NO garantiza.**
   - Que el modelo de huellas entienda su español: E-R02-04 pide 90 de 100.
   - Los 150 ms en su ordenador: E-R02-05.
   - Un recuerdo guardado con Ollama cerrado se busca solo por palabras hasta que tenga
     su huella. La ventana calcula las que falten al abrirse.
   - El umbral de parecido se fija sin sus datos. Si E-R02-04 dice que trae de más o de
     menos, se mueve con lo que diga.
3. **Criterio de parada.** El de ADR-233. Si E-R02-04 no llega a 90 de 100 con ninguno de
   los dos modelos de huellas del plan, se le pregunta, porque cambiar de modelo o de
   enfoque es producto.
4. **Qué lo haría imposible.**
   - **Ollama dentro del turno para filtrar o clasificar.** No se monta ningún adaptador
     que lo haga, abra quien abra las puertas viejas. PA-R02-12 lo mira con las puertas
     abiertas.
   - **El etiquetado por categorías.** La ventana no tiene con qué: ni el caso de uso ni
     el botón.
   - **Una base aparte para las huellas.** La tabla está en `sirius.db`, y PA-R02-11 las
     cuenta ahí.

## Contexto y problema

El paso 2 de la memoria pide «búsqueda por significado, además de por palabras. Va dentro
de la misma base de datos y tarda milisegundos». El plan nombra sqlite-vec y, para las
huellas, Qwen3-Embedding 0.6B o EmbeddingGemma. Y dice qué se deja de hacer: «el filtro con
Ollama dentro de cada respuesta y el etiquetado por categorías», porque en el banco de 47
casos el camino real acertaba entre 4 y 7 y tardaba hasta 780 ms.

## Opciones consideradas

1. **Una tabla virtual `vec0` de sqlite-vec**, con su índice. Fija la dimensión de la
   huella al crearla: cambiar de modelo de huellas obligaría a rehacerla, y la migración
   tendría que cargar la extensión.
2. **Una tabla normal con la huella en un BLOB y el nombre del modelo**, buscada con la
   función `vec_distance_cosine` de sqlite-vec, recorriéndolas todas. Medido aquí el
   07-10-2026: 10.000 huellas de 1.024 números, P50 16 ms y P95 23 ms.
3. **Calcular el parecido en Python.** Sin numpy, 10.000 huellas tardarían segundos.

## Decisión

Se adopta la opción 2.

- **Las huellas**: tabla nueva `memory_embeddings`, una fila por recuerdo, con el modelo
  y la revisión de la que salió. Una huella de una revisión vieja no vale: al corregir un
  recuerdo se calcula otra. Borrar o archivar un recuerdo borra su huella, con dos
  disparadores de la base: una huella deja adivinar algo de lo que decía, y así no
  depende de que el código que borra se acuerde.
- **sqlite-vec** se carga solo en las conexiones de esa tabla. Si no carga, Sirius sigue
  buscando por palabras, como hoy, y lo dice el registro.
- **El modelo de huellas**: el de Ollama que digan los ajustes, `ollama_embedding_model`,
  y si no dicen nada, `qwen3-embedding:0.6b`. Solo puede ir a este ordenador, como la
  charla.
- **La búsqueda**: lo que encuentran las palabras, los 12 mejores, más lo que se parece
  por significado con un parecido de 0,5 o más, otros 12. Lo que solo trae el significado
  tiene que parecerse de verdad. Solo esos recuerdos se cargan, de una vez. Entre los que
  trae, va antes lo que más se parece.
- **Las huellas, en segundo plano**: la ventana calcula las que faltan al abrirse y al
  guardar, corregir o confirmar un recuerdo. Para mientras dura un turno y sigue después.
  Una restauración de copia la espera, como al juez.
- **Fuera de cada respuesta**: el filtro de relevancia, el intérprete de la pregunta y el
  motor por etapas ya no se montan. Las puertas viejas ya no se leen.
- **Fuera el etiquetado por categorías**: la ventana ya no etiqueta al abrirse ni al
  guardar, y desaparece «Editar categoría…». Las categorías ya guardadas se quedan en la
  base y se siguen viendo en la lista, pero nada las pone ni las cambia.
- **El banco de 100 casos** en español, de las siete familias del plan
  (`src/sirius/domain/memory_bank.py`). La orden para pasarlo en su ordenador (E-R02-04)
  llega con la pieza G: «olvida eso» y «quién dijo qué» no se pueden puntuar hasta que
  existan, y así él lo pasa una sola vez. La de los 150 ms (E-R02-05) va ya:
  `scripts/medir_busqueda_de_memoria.py`.

## Comprobación que la sostiene

- PA-R02-11 y PA-R02-12 en verde, y la primera prueba de PA-R02-10. Con la pieza F
  entregada, las de la 0.2 dan 40 pasadas y 11 `xfail` de la pieza G.
- **Buscar en 10.000 recuerdos**, aquí y en dos pasadas: P50 de 34 a 38 ms y P95 de 44 a
  49 ms. El camino de antes, que cargaba todos los recuerdos en cada turno, da un P95 de
  350 ms con los mismos 10.000. Dos arreglos lo bajaron de 69 a 34 ms de mediana: el
  parecido se calcula una vez por huella, y no dos, y los recuerdos encontrados se cargan
  en dos consultas, y no en una por recuerdo.
- **Vistas fallar** con el código estropeado a propósito, cada una en su prueba:
  - con el filtro de relevancia de antes montado otra vez, con su propia conexión;
  - con la ventana pidiendo a Ollama clasificar un recuerdo, también con su conexión;
  - con «Editar categoría…» de vuelta;
  - con el significado sin contar como relacionado, y sin contar en el orden;
  - sin el parecido en el orden;
  - sin búsqueda, cargando todos los recuerdos en cada turno: P95 de 350 ms;
  - con las huellas en otra base;
  - sin calcular huellas al abrir la ventana, ni al guardar;
  - sin parar las huellas durante el turno, o sin seguir después;
  - con la restauración sin esperar a las huellas;
  - sin los disparadores: la huella de un recuerdo borrado se quedaba en la base.
- **PA-R02-12 se reforzó**: la prueba aprobada no guardaba ningún recuerdo, así que el
  filtro de antes no tenía nada que filtrar y no llamaba a Ollama aunque estuviera
  montado. Pasaba con él puesto. Ahora guarda uno que casa con la pregunta, y el espía
  del conductor ve también las peticiones de un adaptador con su propia conexión.
- Unitarias: 15 de la búsqueda, 10 del modelo de huellas y 2 del orden. 13 de
  integración sobre SQLite con sqlite-vec y la orden de E-R02-05. 4 de la ventana, 5 del
  panel, 1 del arranque real y 1 de la restauración.
- También vistas fallar: sin la guarda que impide pedir huellas sin fin si guardar no
  sirve, sin cargar el modelo al abrir, con la pregunta usando el modelo paciente y con la
  orden de E-R02-05 midiendo aunque sqlite-vec no cargue.

## Revisión externa

- **Ronda 1 de Codex**, sobre `5e3937b7`: cuatro hallazgos, los cuatro ciertos, cada uno con
  su prueba vista fallar con el arreglo quitado.
  - P1: una huella calculada mientras se archivaba o se borraba su recuerdo se guardaba
    después de que los disparadores la quitaran, y se quedaba para siempre. Ahora guardar
    es una sola sentencia que solo escribe si el recuerdo sigue vigente y esa revisión es
    la actual.
  - P1: al escribir él, el grupo de huellas que iba por la mitad seguía usando Ollama
    durante el turno. El grupo baja de 16 frases a 4: lo que queda por terminar son
    décimas. Esperar a que acabe retrasaría el turno, y cortar la petición no para a
    Ollama.
  - P2: si una restauración fallaba, la ventana seguía con los clientes de huellas
    cerrados y la búsqueda se quedaba en palabras hasta reiniciar. El modelo de huellas
    abre otro cliente si el suyo está cerrado.
  - P2: tras cerrar la ventana, una vuelta pendiente de huellas podía volver a arrancar.
    El cierre la anula, y lo mismo con el juez.
  - Familias: dos hallazgos son de ciclo de vida del segundo plano (el grupo durante el
    turno y la vuelta tras cerrar); no se repiten de ninguna ronda anterior.

## Consecuencias

- Cada turno pide a Ollama la huella de su pregunta, también con la charla en OpenAI. Si
  Ollama no está o no tiene el modelo de huellas, el turno sigue por palabras.
- La huella de la pregunta espera a Ollama como mucho 5 segundos; si tarda más, ese turno
  sigue por palabras. Las de los recuerdos, en segundo plano, esperan hasta un minuto.
- Al abrirse, la ventana pide una huella aunque no falte ninguna, para que Ollama cargue
  el modelo antes del primer turno.
- `TagCategoryUseCase` y `SetCategoryUseCase` siguen en el árbol sin nadie que los monte.
  Se retiran con el banco de 47 casos, que es quien aún los mide.
- Las pruebas que montan Sirius sin el conductor usan el modelo de huellas de verdad: si
  quien las ejecuta tiene Ollama con ese modelo, lo usarán. En la nube no lo hay. El
  conductor, en cambio, monta Sirius sin huellas salvo que la prueba enchufe las suyas.

## Alternativas descartadas y por qué

- **La tabla `vec0`**, por lo de la opción 1.
- **Mezclar palabras y significado por puesto (RRF).** Daría un orden más difícil de
  explicar. Basta con que las dos traigan lo suyo y el parecido ordene.
- **Dejar las puertas viejas como interruptores.** El plan dice que eso se deja de hacer,
  y un interruptor que nadie enciende es código que nadie prueba.

## La lección

- familia: `prueba-que-no-puede-ver-lo-que-vigila`
- sin esto se repetiría: una prueba de «no se hace X» que pasa con X puesto, porque su
  espía solo mira un camino o porque el caso no llega a provocar X. PA-R02-12 pasaba con
  el filtro de antes montado por las dos razones a la vez
- lo hace cumplir: tests/acceptance/test_robot_0_2_memoria.py
