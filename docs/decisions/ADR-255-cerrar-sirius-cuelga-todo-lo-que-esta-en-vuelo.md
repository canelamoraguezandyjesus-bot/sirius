# ADR-255 — Cerrar Sirius cuelga todo lo que está en vuelo

- Estado: APROBADO
- Fecha: 2026-10-17
- Aprobación: la fusión de la PR que lo introduce, la #698, con una ronda limpia de Codex
  sobre el head de contenido y Quality en verde (ADR-205). Es la raíz de los hallazgos de
  las rondas 1 y 2 de Codex sobre esa PR.

## Nota de arranque

Publicada antes del primer commit en la incidencia #699. Aquí, resumida; la incidencia la
tiene entera.

1. **Dónde vive el fallo y dónde va el arreglo.** Al cerrar Sirius, las peticiones de red en
   vuelo de los trabajos de fondo no se cortaban, y la salida esperaba a que acabaran.
   Medido con el mismo `sys.exit(app.exec())` del `main` de Sirius: `app.exec()` vuelve a
   los 0,10 s, y el proceso sale 4,93 s después, cuando acaba un trabajador del pool que
   dormía 5 s. Los topes de lo que podía quedar en vuelo iban de 5 s, en la orden de
   captura, a 600 s, en la voz de Model Studio. Cada trabajador decidía cómo parar, y solo
   la charla sabía colgar una petición ya enviada (ADR-252). El arreglo va en el
   transporte, no en cada trabajador. **¿Puede el sitio del arreglo observar el fallo?** Sí:
   el registro ve cada conexión abierta, y el cierre sabe cuándo ocurre.
2. **Qué NO garantiza.** Que el servidor deje de trabajar al colgarle: Ollama sí, OpenAI
   cobra la petición igual. Lo que no es red, como cargar o sintetizar una voz local, o
   transcribir, sigue hasta acabar, y con ello la salida.
3. **Criterio de parada.** Con el código de antes, salir con una petición de huellas colgada
   espera su tope; con el arreglo, menos de 1 s, visto fallar antes. Las peticiones de
   huellas, de criticidad y del SDK de OpenAI fallan en menos de 0,1 s al colgar. El cierre
   espera a la orden de captura y sabe cómo quedó. La guarda cae con un cliente puesto a
   mano. Cada regla nueva, con su mutación, y la batería entera en verde. Si la ronda 3
   trae otro hallazgo de esta familia, se para y se le dice al propietario.
4. **Qué lo haría imposible en vez de improbable.** La guarda: ningún cliente de red se
   construye fuera de la fábrica, así que una petición nueva nace colgable.

## Contexto y problema

ADR-253 prometió que cerrar no pinta trazas ni espera, y que cerrar una hoja corta sus
peticiones. Lo cumplió trabajador a trabajador: la charla, el juez, el sueño y las tres
hojas sabían cortar en vuelo, cada uno a su manera. La ronda 1 de Codex sobre la #698
encontró dos que no: el veredicto del juez en las preguntas trampa y la lista de modelos en
la prueba a ciegas. Se arreglaron uno a uno. La ronda 2 encontró cuatro más: las huellas, la
propuesta de criticidad, la voz de Model Studio y su orden de captura. Quedaban, sin que
nadie los hubiera señalado aún, la validación de la clave y los clasificadores del contexto.

Son dos rondas seguidas con la misma familia, `cierre-que-no-corta-todo-lo-que-pide`, así
que se dejó de parchear y se buscó la raíz (ADR-001): el cierre no tenía un camino único que
cortara lo que estaba en vuelo.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

1. **A, un registro de cancelaciones que el cierre recorre.** Cada trabajador apunta su
   `cancel`, y cada adaptador aprende a cortar en vuelo: unos diez cortes distintos. Es el
   parche trabajador a trabajador con un índice delante, y un trabajador nuevo que no se
   apuntara volvería a escaparse.
2. **B, colgar en el transporte, en un solo sitio.** Todos los clientes de red se construyen
   en una fábrica que apunta cada conexión abierta, y el cierre las cuelga todas a la vez,
   como ya hacía la charla con la suya. Una guarda impide construir un cliente fuera de ella.
3. **C, no esperar al salir**, con `os._exit` tras cerrar la base y el diario. Ataja la
   espera, pero no corta nada: la petición muere con el proceso, se salta `atexit` y los
   finalizadores, y la orden de captura queda sin saber cómo acabó.

## Decisión

La opción B, con la orden de captura esperada. C queda como segunda línea solo si, con B, la
salida siguiera esperando por trabajo que no es red.

- **La fábrica**, `src/sirius/infrastructure/network.py`. `http_client` construye los
  clientes de httpx y `openai_client` los del SDK de OpenAI, con los ajustes de siempre del
  SDK. Cada petición lleva la extensión `trace` de httpx, encadenada con la que ya traiga,
  como la de la charla, y cada conexión que se abre queda apuntada en un registro único del
  proceso, con referencias débiles. Se apunta también la conexión TLS que envuelve a la TCP,
  que es la que queda viva, y las que abre un proxy.
- **Todos los clientes por la fábrica:** la charla, las huellas, los cuatro clasificadores,
  los dos clientes del SDK de OpenAI de la composición, el de la validación de la clave y el
  del médico de la voz. Con los mismos topes, proxies y transportes que tenían.
- **El cierre.** Cada ventana cuelga lo que está en vuelo. Al principio lo hacía al cerrarse
  de verdad, con `hang_up_all()`; desde las rondas 3 y 4 lo hace al pedir cerrarse, antes de
  aplazarlo, y hasta que se cierra cuelga también lo que se abra, por el puerto
  `ConnectionCloser`, como cuenta «Revisión externa». Al salir de Sirius, antes de soltar la
  voz, `hang_up_all(final=True)`: además de colgar lo abierto, cuelga en el acto lo que se
  abra después. `final` es solo para salir del proceso, porque cerrar una ventana puede abrir
  otra con las mismas dependencias tras cambiar de proyecto. `sirius-oye` cuelga antes de
  cerrar el micro, también con Ctrl+C, y otra vez al salir. El diario apunta cuántas
  conexiones cuelga, nada más.
- **La orden de captura no se cuelga.** El cierre la espera, como a la copia y a la
  exportación, y el diario apunta cómo quedó la grabación, o que no se sabe si la orden
  reventó.
- **La guarda**, `tests/unit/test_toda_conexion_nace_colgable.py`: falla si en `src/`
  se construye un cliente de httpx, del SDK de OpenAI, un socket o un `urlopen` fuera de
  la fábrica. Dos excepciones, declaradas con su porqué: el WebSocket de la captura, que se
  espera, y la descarga de las voces de `sirius-instala-la-voz`, una orden de consola en
  primer plano que corta Ctrl+C.
- **Ninguna prueba sale de Sirius de verdad**: `tests/conftest.py` falla, y lo deshace, si
  una prueba deja el registro colgando todo lo nuevo, que dejaría sin red a las siguientes.

## Comprobación que la sostiene

- **Salir con unas huellas colgadas**, en un proceso offscreen con el `_release_on_quit` de
  Sirius: con el código de `9c68c3a1`, 7,80 s, lo que tardó en saltar su tope de 8 s; con el
  arreglo, 0,47 s. La prueba pide menos de 2 s, con margen para la máquina cargada.
- **Colgar una petición en vuelo**, contra un servidor que acepta y no contesta: las huellas,
  la criticidad y el SDK de OpenAI fallan en menos de 0,1 s; la charla sigue cortando la
  suya con su propio `trace`.
- **Tras salir**, una conexión nueva cae en el acto; tras cerrar una ventana, no.
- **La captura**: la ventana sigue abierta mientras la orden está en vuelo, no cuelga nada,
  y al acabar se cierra con su estado en el diario; si la orden revienta, también.
- **Mutación**: 17, y caen las 17, cada una con su caché de bytecode vacía. Son quitar cada
  llamada de cierre, de la ventana, de la salida y de `sirius-oye`; colgar al salir sin
  `final`; que las huellas, la criticidad o el SDK de OpenAI se salten la fábrica; que
  `final` no cuelgue lo nuevo; que colgar no cuelgue; no apuntar la conexión TLS; que el
  gancho pise el `trace` de la charla; que el cierre no espere a la captura, o no cierre tras
  ella, también si revienta; y contar las conexiones ya cerradas.
- **Las suites que tocan los ficheros cambiados**, 80: 1 708 en verde, 2 omitidas y 2
  `xfail`, en 6 min 27 s. La batería entera, la de la PR, en ADR-253.
- **ruff** limpio; **mypy** sin errores en 749 ficheros.

## Consecuencias

- Cerrar Sirius o `sirius-oye` ya no espera a una petición de red en vuelo, sea del trabajo
  que sea, con dos salvedades escritas abajo: la orden de captura, que se espera a propósito,
  y una conexión que aún no ha acabado de abrirse. Las peticiones cortadas fallan por el
  camino de fallo que ya tenía su trabajador, y el diario dice antes cuántas conexiones colgó
  el cierre.
- Un cliente de red nuevo tiene que salir de la fábrica, o la batería falla.

**Qué NO garantiza, después del código:**
- Que el servidor deje de trabajar: Ollama para al ver la conexión colgada (ADR-252);
  OpenAI cobra la petición igual.
- Lo que no es red: cargar o sintetizar una voz local, o transcribir, sigue hasta acabar, y
  la salida con ello.
- Colgar en Windows: visto en Linux, como en ADR-252.
- La orden de captura puede retrasar el cierre hasta su tope, 5 s.
- Colgar una conexión que aún no ha acabado de abrirse. Mientras resuelve el DNS o conecta,
  el transporte aún no la ha devuelto y no hay nada que colgar: se cuelga en cuanto se abre.
  Si el servidor no contesta nunca al conectar, se espera a su tope de conexión, 10 s en la
  validación de la clave y 5 s en los demás clientes de OpenAI; si no contesta el DNS, lo que
  tarde el sistema. Las de Ollama van a `127.0.0.1` y abren o fallan en el acto. Medido con
  un servidor local que no contesta al conectar, porque tiene llena la cola de aceptar: con
  un tope de conexión de 1,5 s, la petición acaba a los 1,50 s, se cuelgue o no. Cortarla
  exigiría cambiar por dentro el transporte de httpx, y no se hace.
- Si se cierra con una clave de OpenAI a medio validar, la validación se corta y esa clave
  no se guarda: hay que volver a ponerla.
- Mientras una ventana espera para cerrarse, se cuelga todo lo que se abra en el proceso,
  también lo de otra ventana. Hoy solo pasaría si se acaba un proyecto con una orden de
  captura en vuelo y se crea el siguiente antes de que acabe, como mucho 5 s.

## La lección

- familia: `cierre-que-no-corta-todo-lo-que-pide`
- sin esto se repetiría: cada trabajo de fondo nuevo nacería sin saber cortarse al cerrar
  Sirius, y la salida esperaría a su petición hasta el tope, de 5 s a 600 s; cada ronda de
  revisión encontraría uno más, como pasó en las rondas 1 y 2 de Codex sobre la #698.
- lo hace cumplir: `tests/unit/test_toda_conexion_nace_colgable.py`

## Revisión externa

Va en la PR #698, con ADR-253 y ADR-254, y su alcance se suma al de allí: que al cerrar
Sirius ninguna petición de red siga en vuelo ni haga esperar a la salida, que la orden de
captura se espere y se sepa cómo quedó, y que ningún cliente de red nazca fuera de la
fábrica. Las rondas se anotan aquí.

**Ronda 3** de la PR, sobre `fee19290`: un P2 de la misma familia. El cuelgue iba al final
del cierre, detrás de lo que lo aplaza: validar la clave, enviar, copiar, exportar o
capturar. Mientras tanto, lo que estaba en vuelo seguía pidiendo. Era la tercera ronda con
la familia, y el criterio de parada de la #699 mandaba parar y decírselo al propietario.
Se le dijo, y contestó el 18-10-2026 que se siguiera trabajando. Lo arregla `5c8291e1`:
las tres ventanas cuelgan la red al pedir cerrar, antes de aplazarlo, y la principal otra
vez al cerrar de verdad. El proveedor de OpenAI da por corte, y no por fallo, una conexión
colgada tras cancelarla. De sus 6 pruebas nuevas, 5 fallan con el código de antes; la
sexta fija que colgar no toca la captura, y la tumba su mutación. Caen sus 8 mutaciones.
Con una clave a medio validar, cada ventana cierra en menos de 1 s; antes esperaba al tope
de 10 s.

**Ronda 4** de la PR, sobre `814e7b0d`: un P1 y un P2, los dos arreglados en `1e6b1c52`.

- **El P1 es de capas.** La presentación importaba `hang_up_all` de
  `sirius.infrastructure.network`, y AGENTS.md pide las dependencias hacia dentro. Ahora hay
  un puerto, `ConnectionCloser` en `src/sirius/ports/connections.py`, y `sirius.main` da a la
  ventana principal y a la de bienvenida el registro del proceso, que lo implementa. Las
  ventanas solo lo invocan. Una guarda de `tests/unit/test_presentation_boundaries.py` falla
  si la presentación importa de `sirius.infrastructure` algo que no sea el diario.
- **El P2 es de la familia, que llega así a su cuarta ronda.** Una conexión que aún se abría
  al pedir cerrar, en el DNS o en `connect_tcp`, no estaba apuntada al colgar, y seguía hasta
  su tope. Así, el cierre aplazado volvía a esperar a la validación hasta 10 s. Ahora, desde
  que una ventana pide cerrarse hasta que se cierra de verdad, toda conexión que se abre se
  cuelga en el acto. Al cerrarse se vuelve a poder abrir, porque tras cambiar de proyecto se
  abre otra ventana con las mismas dependencias. Un contador deja cerrarse dos ventanas a la
  vez sin pisarse, y al salir sigue `final=True`. El propietario había dicho que se siguiera
  trabajando sin preguntarle.
- **Las cifras.** Con el código de `814e7b0d`, cerrar la bienvenida con la conexión de la
  validación aún abriéndose tardaba 10,03 s, su tope; con el arreglo, 0,014 s. Lo que se
  abría con el cierre de la principal ya pedido acababa a los 10,01 s, y ahora cae en
  0,001 s. Las 13 pruebas nuevas fallan con el código de antes, y las del cierre de la
  ronda 3 siguen en verde. Caen sus 20 mutaciones.
- **Lo que no cubre**, visto al repasar el arreglo antes de pedir la ronda 5: una conexión
  que no acaba de abrirse nunca, porque el servidor no contesta al conectar. Queda en «Qué NO
  garantiza», con su medida.
