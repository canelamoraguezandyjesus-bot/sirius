# ADR-252 — Dejar la voz y la ventana listas para sus pruebas de voz

- Estado: APROBADO
- Fecha: 2026-10-17
- Aprobación: la fusión de la PR que lo lleva a `main`. Son defectos de las piezas B a F de
  la voz y de la ventana, encontrados antes de sus pruebas.

La **nota de arranque** se publicó como incidencia, la #694, antes del primer commit y antes
de medir el código nuevo (ADR-001), porque `MEMORIA.md` no tenía sitio para un ADR nuevo
hasta que se fusionara la PR que la recorta. Va aquí tal cual.

## Nota de arranque

**Por qué.** Antes de las pruebas de voz de la 0.3 en su ordenador, de E-R03-01 a E-R03-05,
se repasaron todos los pasos que le quedan. Salieron siete cosas de nuestro código que le
harían fallar una prueba o le harían creer que algo ha fallado.

### 1. Dónde vive cada fallo y dónde va el arreglo

1. **El juez frena la voz en la ventana.**
   - El juez puntúa en segundo plano tras cada turno (`main_window.py`, `_start_judge`). Cada
     turno de voz espera a que acabe su petición en curso (`begin_voice_turn`), y el juez
     vuelve a arrancar al acabar el turno.
   - Su petición lleva la semilla con los 20 ejemplos y escribe con el tope de la charla,
     4 096.
   - Arreglo:
     - un tope propio para lo que pide el juez, porque solo contesta un número o una
       palabra; el tope va en la petición (`LLMRequest`), y lo respetan los dos proveedores;
     - el juez no arranca hasta 60 s después del último turno de voz;
     - si un turno de voz lo encuentra en marcha, corta su petición en vez de esperarla
       entera.
2. **«Sirius» mal escrito.** faster-whisper transcribe sin pista
   (`adapters/audio/local_listening.py`, `transcribe`). En español puede escribir «Sirio», y
   entonces Sirius no contesta.
   - Arreglo: `hotwords="Sirius"`.
   - El nombre se sigue reconociendo solo exacto: «sirio» es también «de Siria», y una tele
     hablando de Siria no puede despertarle (E-R03-05).
3. **El «FfiHandle» rojo al salir.** La APM de livekit sigue viva cuando Python se cierra, y
   su destructor falla con `AssertionError`: cuatro veces en la orden de instalar y una al
   salir de `sirius-oye`, justo debajo del P95.
   - Arreglo:
     - el cancelador suelta la APM al cerrarse el altavoz;
     - `LocalListening` tiene un cierre que suelta el altavoz;
     - `sirius-oye` y la ventana lo llaman al salir.
4. **Avisos que parecen fallos al cargar Chatterbox:** el de `pkg_resources`, el
   `FutureWarning` de `diffusers` y los `WARNING` del tokenizador, el del Cangjie y el de
   pkuseg. Se silencian solo alrededor de su carga.
5. **El primer turno espera a que se cargue el modelo de la charla.** Ni `sirius-oye` ni la
   ventana lo cargan antes.
   - Arreglo: al arrancar le piden a Ollama que lo cargue, en segundo plano, con el mismo
     `num_ctx` y el mismo `keep_alive` que la charla.
6. **Textos que no dicen qué hacer:**
   - el aviso de que la charla va fuera no dice cómo elegir un modelo de su ordenador;
   - la orden de instalar repite «no carga» dos veces.
7. **Ruido en la consola:** el cartel de Pipecat, que sale porque se importa antes de acallar
   loguru, y las líneas `INFO [alembic…]` cada vez que Sirius migra.

**¿Puede el sitio del arreglo observar el fallo?** Sí en 1, 3, 5, 6 y 7: cada uno se ve en
su prueba con los dobles y, el 3, con livekit de verdad si se instala aquí. En 2 y 4, solo lo
que se le pasa a la biblioteca: cómo transcribe su voz y qué avisos sueltan las versiones de
su ordenador, solo se ve allí.

### 2. Qué NO garantiza

- Que Whisper escriba «Sirius» con su voz y su micro. La pista ayuda, no obliga.
- Que el juez dé nota con un modelo que «piensa» antes de contestar. Con el tope corto se
  quedaría sin nota, y el juez es un aviso, no una puerta. Ninguno de los tres modelos de su
  prueba a ciegas piensa.
- Que cortar la petición del juez sea instantáneo: Ollama la deja cuando se cierra el flujo,
  después de procesar la pregunta, unos segundos como mucho.
- Que lo que se carga antes quepa en su gráfica junto con el modelo de huellas. Eso lo mide
  E-R03-01.
- Avisos nuevos que traigan otras versiones de esas bibliotecas.

### 3. Criterio de parada

- Cada arreglo, con una prueba vista fallar con el código de antes y su mutación.
- Lo que no pueda verse aquí se dice con esas palabras.
- Nada cambia lo que oye, lo que contesta ni lo que guarda Sirius: solo cuándo puntúa el
  juez, cuánto escribe, cuándo se carga el modelo y lo que sale por la consola.
- Dos rondas de revisión con defectos de la misma familia: se para y se busca la raíz.

### 4. Qué lo haría imposible en vez de improbable

- Que el juez haga esperar a la voz: imposible mientras dura la charla de voz, porque no
  arranca hasta 60 s después del último turno. Si lo pilla en marcha, se corta; no se espera
  entera.
- Que la APM sobreviva a la salida: imposible por los dos caminos de salida de su lote,
  `sirius-oye` y cerrar la ventana. Una salida a la fuerza, como matar el proceso, no se
  puede cubrir.

## Contexto y problema

Los de la nota. Las pruebas de voz de la 0.3 las hace él en su ordenador, y cada una que
falle por algo nuestro le cuesta una tarde.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

1. **El tope del juez**: (a) en cada petición, `LLMRequest.max_output_tokens`, que cada
   proveedor recorta a su tope; (b) un proveedor aparte para el juez, con su propio
   `num_predict`.
2. **Cortar al juez**: (a) como hasta ahora, mirando si está cortado con cada trozo; (b)
   colgar la conexión de su petición.
3. **El juez con un modelo que piensa**: (a) dejarlo, como decía la nota; (b) apagar
   `think` en sus peticiones y, si Ollama lo rechaza, preguntar una vez sin apagarlo; (c)
   preguntar antes a Ollama qué sabe hacer el modelo (`/api/show`) y apagarlo solo si piensa.
4. **Soltar la APM**: (a) al cerrarse la ventana; (b) al salir de Sirius.
5. **Las líneas de Alembic**: (a) dejarlas; (b) que Sirius migre sin el registro de
   alembic.ini, la opción 2 que ADR-249 descartó para lo suyo.

## Decisión

Tope propio del juez, cortarle colgando su conexión, `think` apagado con reintento, la APM
soltada al salir y migrar sin el registro de Alembic. Son 1(a), 2(b), 3(b), 4(b) y 5(b); lo
demás, como en la nota.

- **1(a)**: el proveedor que usa el juez lo comparte el sueño, que necesita salidas largas.
  El juez pide 64 tokens, `JUDGE_MAX_OUTPUT_TOKENS`; la nota sale al principio, y cabe una
  frase antes por si la dice. Ollama y OpenAI piden el menor de los dos topes, nunca más que
  el suyo.
- **2(b)**: con el corte de antes, el turno esperaba hasta el primer trozo, y mientras
  Ollama lee la pregunta no manda ninguno. `cancel` cuelga la conexión de esa petición, y
  quien la lee deja de esperar sin que llegue otro trozo: en Linux, al momento; en Windows
  no se ha comprobado. Para saber cuál colgar, cada petición abre su conexión y la cierra
  al acabar (`max_keepalive_connections=0`), y httpx avisa de cuál abrió con su extensión
  `trace`.
- **3(b)**: sin apagarlo, un modelo que piensa se gasta los 64 tokens pensando y el juez se
  queda sin nota siempre; con (c), una petición más y depender de lo que diga cada versión.
  Qué versiones de Ollama rechazan `think: false` con un modelo que no piensa no se ha
  podido comprobar: aquí no hay ni su código ni la red a GitHub. Lo único que consta es que
  el filtro de relevancia lo manda, y que en su ordenador, con `qwen3:4b-instruct`, contestó a
  las 47 llamadas del banco
  (`docs/audits/medicion-banco-completo-ollama-real-2026-09-20.md`). Si Ollama contesta 400
  y su error habla de `think`, sin contar el nombre del
  modelo, la pregunta se repite una vez sin apagarlo, y ese proveedor ya no lo apaga más.
  Cualquier otro 400 sigue siendo un fallo. La charla no lleva `think`.
- **4(b)**: una ventana también se cierra tras acabar un proyecto, cuando se abre la
  siguiente, y esa tendría que volver a cargar la voz, la de personaje tarda. Sirius engancha
  `LocalListening.close` al `aboutToQuit` de la aplicación, que se emite antes de que Python
  se cierre. `sirius-oye` la suelta al acabar, también si no llegó a escuchar.
- **5(b)**: `upgrade_to_head` pone `configure_logger` en `False` en los atributos de su
  configuración, y `migrations/env.py` solo configura el registro de alembic.ini si no lo
  dice. La línea de órdenes de Alembic sigue con el suyo, con
  `disable_existing_loggers=False` (ADR-249).

Al escribir el código se decidió además:

- **El juez corta solo sus notas**, no los veredictos de las preguntas trampa, que él pide
  a propósito y pueden correr a la vez.
- **Ningún corte cae en el hueco de antes de pedir la nota**: el servicio le pasa al juez su
  bandera de parar (`should_stop`), y el juez la mira y apunta la nota bajo el mismo
  cerrojo. Quien le para pone la bandera antes de cortar: o el juez la ve, o el corte
  encuentra la nota apuntada.
- **Una nota cortada no es un fallo**: no se apunta en el diario como «El juez no pudo
  puntuar».
- **Un turno de voz que no va**, porque la ventana está con otra cosa, también cuenta como
  charla: el juez espera desde él.
- **La respuesta de un turno de voz queda para el juez**, como una escrita, y la puntúa
  pasada la charla. Antes solo se puntuaba si el turno había parado al juez, o cuando lo
  lanzaba después un turno escrito o la ventana al abrirse.
- **La orden de instalar suelta la APM de cada voz que comprueba**, donde la nota vio
  cuatro líneas rojas: ya cerraba sus altavoces, y ahora cerrarlos la suelta. Con livekit de
  verdad aquí se vio el cancelador, no la orden entera.
- **La pista y el nombre salen de la misma constante**, `addressing.NAME`.
- **Los tres avisos de Chatterbox se callan por su texto**, mientras se importa y se
  construye, y nada más: cualquier otro aviso sale igual. Sus textos salen del código de las
  versiones fijadas: setuptools 81.0.0, diffusers 0.29.0 y chatterbox-tts 0.1.7.
- **El aviso de la charla de fuera** termina con «Elige uno de este ordenador en la ventana
  de Sirius: Configuración, «Elegir el modelo a ciegas…».», y una prueba mira que esa
  pestaña y ese botón son los de verdad.
- **«No carga» una vez**: si el motivo vuelve a decir que «la/el … no carga (causa)», la
  orden de instalar dice solo la causa. El de una biblioteca, «torch no carga (…)», se deja
  entero, que dice cuál.
- **Lo que servía de Alembic, al diario**: «La base pasa del esquema X al Y», una vez y solo
  si cambia.
- **Al diario, nada de lo que dice Ollama** en lo nuevo de este ADR: la precarga que falla y
  el rechazo de `think` apuntan el modelo y el código, como pide la ronda 2 de Codex sobre la
  #692.

## Qué NO garantiza, después del código

La nota lo escribió antes de medir; el código cambió tres de sus puntos:

- **Cortar al juez** ya no espera a que Ollama acabe de leer la pregunta: el cliente cuelga
  al momento, visto en Linux con un Ollama de mentira por la red de verdad. En Windows no se
  ha comprobado: Quality corre en Linux, y el de Windows solo se lanza a mano y no se ha
  lanzado. Si allí colgar no despierta al hilo que lee, lo despertaría Ollama al cerrar su
  lado cuando ve que la conexión se ha ido, y eso tampoco se ha comprobado aquí con el
  Ollama de verdad. Tampoco que deje de trabajar en la pregunta en cuanto lo ve.
- **Con un modelo que piensa** el juez da nota, si Ollama le deja apagar el pensamiento. Con
  uno que no deja, se puede quedar sin nota.
- **La APM se suelta al salir de Sirius**, cuando se cierra su última ventana, y al acabar
  `sirius-oye`.

Y además:

- Que con la pista, un ruido o una palabra parecida no salgan escritos «Sirius» y le
  despierten. Lo mide E-R03-05.
- Que la precarga funcione con su Ollama: sigue su documentación, que con `messages`
  vacío solo carga el modelo, y aquí no se ha podido probar con uno de verdad.
- Que la carga entera de Chatterbox, con torch de verdad, no suelte otros avisos: aquí no se
  ha podido cargar. Y si dos voces de personaje cargaran a la vez, en dos hilos, los filtros
  de avisos de una podrían quitar los de la otra: son de todo el proceso.
- El hilo de la precarga no retiene la salida: si Sirius se cierra mientras Ollama carga, el
  hilo se corta con el proceso.

## Comprobación que la sostiene

- **Cada regla, con su mutación**: 77 mutaciones sobre el código final, una por regla, y
  caen las 77, cada una con su caché de bytecode vacía. Las pruebas de la ventana se
  vieron fallar antes del arreglo.
- **45 pruebas nuevas**, entre ellas:
  - en Linux, un Ollama de mentira por la red de verdad que no contesta: cortar devuelve al
    momento, leyendo y escribiendo, y el de mentira ve que la conexión se ha ido;
  - el trabajo del juez de verdad con ese Ollama: al pararlo, su `done` llega en menos de
    2 s;
  - un Ollama que acepta `think` y otro que lo rechaza, para la nota, las preguntas trampa y
    la charla.
- **livekit 1.1.20 de verdad**, en un entorno aparte: con la APM viva al salir, el
  `AssertionError` de `FfiHandle.__del__`; soltándola, nada. Lo mismo hace
  `tests/integration/test_la_apm_de_verdad_al_salir.py`, que se salta sin livekit y que
  allí pasa.
- **El `__init__` de Pipecat 1.12.0 y loguru 0.7.3 de verdad**: con el orden de antes sale el
  cartel, y con el de ahora no.
- **Alembic de verdad, en un Python aparte**: antes, las líneas `INFO [alembic…]` y un
  manejador en el registro raíz; ahora, nada por la consola y una línea en el diario.
- **faster-whisper 1.2.1**, instalado aparte: `transcribe` admite `hotwords`.
- **Las suites de lo que toca**, 38 ficheros, sobre el código de esta rama (`39015ebe`): 801
  en verde y 1 saltada, la de livekit.
- **ruff** limpio; **mypy** sin errores en 742 ficheros.
- **La batería entera**, sobre `eef79b5f`, que tiene el mismo código que el head de la PR
  #692 con ADR-251 y este, `c7a30d00`: 8 975 en verde, 15 omitidas y 2 `xfail`, ningún
  fallo, en 25 min 23 s. La omitida de más es la de la APM de livekit, que se salta sin
  livekit.

## Consecuencias

- Mientras dura una charla de voz, el juez no puntúa, tampoco lo escrito: lo hace 60 s
  después del último turno de voz.
- Cada petición a Ollama abre su conexión: a este ordenador, nada.
- Los veredictos de las preguntas trampa también piden 64 tokens y sin pensar.
- La consola de `uv run sirius` ya no enseña las líneas de Alembic; `alembic upgrade head`
  sí.
- **En su ordenador**: traer la rama basta; no hay que volver a instalar nada.

## Alternativas descartadas y por qué

- **Un proveedor aparte para el juez** (1b): el sueño comparte el suyo y necesita salidas
  largas.
- **Seguir cortando con cada trozo** (2a): es lo que hacía esperar a la voz.
- **Dejar sin nota a un modelo que piensa** (3a), y **preguntar antes qué sabe hacer** (3c):
  la primera deja al juez sin nota con esos modelos, y la segunda pide una petición más y
  depende de la versión.
- **Soltar la APM al cerrarse la ventana** (4a): se hizo así primero, y la revisión propia
  lo cambió.
- **Dejar las líneas de Alembic** (5a): le hacen creer que algo falla en cada arranque.

## Revisión propia

Se releyó el diff entero contra el código y la nota, y se cambiaron cinco cosas antes de la
primera entrega:

- la ventana soltaba la voz al cerrarse, también tras acabar un proyecto: ahora la suelta
  Sirius al salir;
- el juez guardaba una sola petición en curso, compartida con los veredictos: ahora corta
  solo sus notas;
- un corte que llegaba antes de que el juez apuntara su nota no la cortaba: primero un
  contador tapó casi todo el hueco, y la revisión adversaria encontró el resto, el de justo
  después de que el servicio mire; ahora la bandera se mira y la nota se apunta bajo el
  mismo cerrojo;
- con 32 tokens y sin apagar `think`, un modelo que piensa no daba nota nunca: ahora pide 64
  y sin pensar;
- un error de tipos de mypy en una prueba.

## La lección

- familia: `cortar-solo-entre-trozos`
- sin esto se repetiría: un corte que se mira entre trozos no corta mientras el otro calla.
  Ollama no manda nada mientras lee la pregunta, y la voz esperaba a un juez que se creía
  cortado (H-252).
- lo hace cumplir: `tests/unit/test_el_juez_no_frena_la_voz.py`

## Revisión externa

Entró en la PR #692, con lo de ADR-247 a ADR-250, y su alcance se sumó al de allí para
la ronda 3, escrito antes de pedirla.

**La ronda limpia.** Ronda 3, sobre `54b208f0`, preguntando si el enfoque está mal:
«Didn't find any major issues», del conector, el 17-10-2026. Con ella y Quality en verde
se fusionó la PR #692 (`c7c378f5`). Se anota desde la PR de ADR-253: anotarlo en su PR
habría cambiado el head que la ronda revisó.
