# ADR-262 — Darle a Sirius ojos: la cámara y las caras en local

- Estado: APROBADO
- Fecha: 2026-10-19
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Es la pieza D de la 0.4, en el orden
  de ADR-259.

Este ADR es además la **nota de arranque** de la pieza D. Se escribe antes de su primera
línea de código. Los umbrales de la pieza los fijó ADR-259 en
`docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md`, PA-R04-06 a PA-R04-09 y E-R04-01 y E-R04-02,
antes de que la pieza existiera, y aquí no se añade ni se afloja ninguno.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** Sirius tiene cara pero no ve: no sabe
   quién tiene delante, ni quién le habla, ni si le miran. El plan pide la cámara del
   ordenador con MediaPipe, en local; que mire a quien habla y aparte la vista al
   pensar; y, desde la 0.4, que lo que le dice alguien que le mira sea para él aunque
   no diga su nombre (§6, «Lo que se hace», 1 y 6, y la 0.3, «desde 0.4, si le miran»).
   El arreglo va en seis sitios:
   - **Los puertos de la vista**, sin tipos de ninguna biblioteca: la cámara, el detector
     de caras y lo que ve de cada cara: dónde está, si mueve la boca y si mira a la
     cámara.
   - **La vista**, en la aplicación: lee la cámara, busca las caras y recuerda lo visto
     unos segundos, sin guardar ningún fotograma. Dice a quién mirar y si quien habla
     le mira. Sin cámara, o si se desenchufa, lo dice y sigue.
   - **El oído**: un turno es para él si dice su nombre, si sigue la charla, o, desde
     ahora, si quien habla le mira mientras lo dice.
   - **La cara**: mira a quien habla mientras habla; mientras el modelo piensa, aparta la
     vista; al contestar, mira a quien le habló. Lo lee sin cerrojos, como el volumen y
     los gestos.
   - **La ventana** dice si ve o no, y por qué, y arranca la vista al abrirse, como el
     oído; un hilo la atiende, como al oído.
   - **Los adaptadores de verdad**: OpenCV para la cámara y MediaPipe para las caras, que
     instala la orden de la voz con su extra y su modelo, una vez y con internet; y la
     telemetría de ONNX Runtime apagada antes de cargar ningún modelo.

   **¿Puede el sitio del arreglo observar el fallo?** En parte. Que lo visto llegue a la
   cara y al oído, que la cámara que falta se diga, y que nada salga ni se guarde, sí:
   las pruebas lo ven con dobles. Que MediaPipe vea bien quién mueve la boca y quién
   mira, no: eso solo se ve con su cámara, en E-R04-01 y E-R04-02.
2. **Qué NO garantiza.**
   - Que MediaPipe acierte quién habla y quién mira: las pruebas usan dobles que lo
     llevan escrito. Lo mide E-R04-02.
   - Que quepa en su ordenador junto a lo demás: MediaPipe en Windows va por el
     procesador; lo mide E-R04-01.
   - Que la cámara de verdad se abra en su Windows: lo ve E-R04-01.
   - Reconocer a nadie, la edad y recordar lo visto: son las piezas E, F y G.
3. **Criterio de parada**, decidido antes de escribir el código:
   - Las ocho pruebas de la pieza D en verde, PA-R04-06 a PA-R04-09, y la batería entera.
   - Ninguna prueba de la 0.2 ni de la 0.3 abre una cámara: sin vista enchufada, nada la
     carga. Si no se puede asegurar, se para y se dice.
   - Si el día uno lo que ve no cabe en su ordenador, va al procesador y se vuelve a
     medir; si tampoco, se para y se le pregunta, porque lo que queda es dinero o
     producto (ADR-259).
   - Dos rondas seguidas de Codex con la misma familia: se deja de parchear y se busca la
     raíz.
4. **Qué lo haría imposible.**
   - **Que una imagen se guarde o salga**: los fotogramas viven en memoria mientras se
     miran, lo que se recuerda son números y sitios, no recortes, y en marcha nada se
     conecta. El vigilante de la 0.3 y la búsqueda de imágenes de la 0.4 lo comprueban
     (PA-R04-09).
   - **Que el modelo tarde y la vista se pare con él**: la vista va en su hilo, y la cara
     y el oído la leen sin esperarla.
   - **Lo que no se puede hacer imposible**: que mire a quien no es, o que tome por una
     mirada lo que no lo era. Se hace improbable con las medidas del propietario.

## Contexto y problema

Con la cara (ADR-260) y los gestos (ADR-261), Sirius tiene cara pero no ve. La pieza D le
da la cámara del ordenador y las caras, en local, con MediaPipe (§6 del plan, «Lo que se
hace», 1 y 6), y cierra lo que la 0.3 dejó para la 0.4: que lo que le dice alguien que le
mira es para él aunque no diga su nombre. ADR-259 le dejó además dos encargos: un solo
OpenCV y la telemetría de ONNX Runtime apagada antes de cargar ningún modelo.

Lo difícil es el tiempo. La cámara y el detector tardan decenas de milisegundos por
fotograma; la cara se dibuja unas 30 veces por segundo en el hilo de la ventana y no se
puede congelar (PA-R04-03); el oído decide en su hilo si un turno es para él. Ninguno puede
esperar a otro. Y ninguna imagen puede guardarse ni salir del ordenador (§2 del plan).

## Opciones consideradas

1. **Mirar en el hilo de la ventana**, con un temporizador: la cara se pararía mientras el
   detector mira cada fotograma.
2. **Un proceso aparte para la vista**: los fotogramas cruzarían de un proceso a otro, y
   cada sitio por donde pasan es uno más donde podrían quedarse escritos.
3. **Un hilo, como el del oído**, que lee la cámara y busca las caras unas diez veces por
   segundo y solo se queda con números: dónde está cada cara, si mueve la boca y si mira.
   La cara y el oído lo leen sin esperarle. **Esta.**

## Decisión

Se adopta la opción 3.

- **Los puertos**, en `src/sirius/ports/local_sight.py`, sin tipos de ninguna biblioteca:
  la cámara, el detector de caras y lo que ve de cada cara, `SeenFace`: dónde está, de 0
  a 1 con la izquierda y la derecha de la imagen, si mueve la boca, si mira a la cámara y
  su recorte. `SightUnavailable` y `CameraUnavailable` dicen por qué.
- **La vista**, `LocalSight`, en `src/sirius/application/local_sight.py`: no carga nada al
  construirse; al empezar carga la cámara y el detector y abre la cámara. Cada vez que
  mira, lee un fotograma, busca las caras y apunta de cada una dónde está, si habla y si
  mira, con su momento; el fotograma y los recortes se sueltan en cuanto el detector
  acaba. Recuerda 30 s. Sin lo que instala la orden, dice que no puede ver, con la orden;
  sin cámara, si la tiene otro programa o si deja de dar imagen diez lecturas seguidas,
  como al desenchufarla, la suelta y lo dice. Un fallo del detector se apunta una vez,
  con su tipo y nada más, y no la para.
- **Lo que dice de lo visto**: quién habla y quién mira, del último fotograma y, si son
  varios, el más al centro; y si desde un momento alguien movía la boca mirándole a la
  vez, que es lo que dice que le hablan a él.
- **El hilo**, `SightLoop`, en `src/sirius/application/sight_loop.py`: mira cada 0,1 s; un
  fallo que se escape lo apunta por su tipo y vuelve a mirar al segundo; es de fondo, y
  parar es pedírselo, como al del oído.
- **El oído**: un turno sin su nombre y pasada la charla es para él si quien habla le
  miraba mientras lo decía o en el segundo de antes de empezar a oírse su voz. Y dice en
  qué está, sin su cerrojo: oyendo un turno, pensando la respuesta, diciéndola o en nada
  (`LocalListening.phase`).
- **Adónde mira**, `Attention`, en `src/sirius/application/attention.py`: oyendo, a quien
  habla, y se acuerda de él; pensando, aparta la vista arriba y al lado contrario de quien
  le habló; hablando, a quien le habló; en nada, a quien hable, o a quien le mire, o a su
  aire. Sin vista, aparta la vista al pensar igual, y lo demás lo mira a su aire.
- **La cara**: `FaceLife.pose` recibe adónde mirar y llega con el mismo salto de 60 ms,
  desde donde esté la mirada, también a medio salto; allí tiembla menos de 0,04 en
  horizontal y 0,03 en vertical. Un cambio de menos de 0,05 no la hace saltar.
  `FaceWidget` lo lee de la atención y dibuja la pupila al revés en horizontal, porque la
  cámara no es un espejo: quien sale a la derecha de la imagen está a la izquierda de
  quien mira la pantalla. Si no puede saber adónde mirar, mira a su aire y lo apunta una
  vez.
- **La ventana** abre la vista al abrirse, como el oído, y dice «Cámara: te veo» o por qué
  no ve; lo mira cada medio segundo, así que una cámara que se desenchufa se dice sin
  esperar a nada. En Model Studio suelta la cámara, por si la quiere OBS, y al salir la
  vuelve a abrir. Al cerrarse para su hilo y la suelta. La ventana de verdad trae su
  hilo; en las pruebas, la vista la mueve la prueba.
- **Los adaptadores de verdad**, en `src/sirius/adapters/vision/local_sight.py`: la
  primera cámara del ordenador con OpenCV, con DirectShow en Windows; y el Face Landmarker
  de MediaPipe en modo de vídeo, hasta cuatro caras, con cómo tienen la boca y los ojos, y
  dónde está la cabeza y hacia dónde apunta. Dónde está una cara es el centro de sus
  puntos. Mueve la boca si lo abierta que la tiene ha variado más de 0,08 en el último
  segundo, siguiendo cada cara por dónde está. Le mira si adonde apunta la cabeza, más lo
  que se le van los ojos, no se aparta de la dirección de esa cara a la cámara más de 20
  grados a un lado ni más de 15 hacia arriba, y hacia abajo hasta 35, porque Sirius está
  en la pantalla, debajo de la cámara: quien está a un lado le mira girando la cabeza, y
  quien la gira puede mirarle con los ojos. Sus bibliotecas se importan solo al cargar la
  vista y todas por `import_sight_library`: falle como falle una, Sirius se abre igual y
  lo dice.
- **Lo que se instala**: el extra `ojos`, con MediaPipe 1.1, que trae su OpenCV. La orden
  de instalar la voz, escrita con ese extra, baja además el modelo de las caras, la versión
  1 fija de los modelos de MediaPipe, unos 4 MB, a `modelos/ojos` de la carpeta de datos;
  lo baja aparte y solo lo pone en su sitio si su huella es la esperada y lleva dentro lo
  que tiene que llevar; después mira que la vista carga y si la cámara se abre, y sin
  cámara avisa sin fallar. Sin el extra, dice cómo se pone:
  `uv run --link-mode=copy --extra voz --extra ojos sirius-instala-la-voz`.
- **Un solo OpenCV**: `opencv-python` y `opencv-python-headless` quedan fuera con un
  marcador que nunca se cumple, como Chatterbox dejó fuera lo suyo (ADR-246). Cuando la
  pieza E traiga InsightFace, que pide uno de ellos, el `cv2` seguirá siendo el de
  MediaPipe; una prueba mira que el candado lleve solo ese.
- **La telemetría de ONNX Runtime**, apagada antes de importar Silero y Smart Turn, en el
  oído, y Piper, en la voz (`onnx_runtime_quiet`): con la variable que pone InsightFace
  2.1, para los ONNX Runtime que la leen al arrancar, y con `disable_telemetry_events`, que
  trae la 1.24 y vale aunque ya estuviera importado.
- **Los números de partida** los decidió la sesión (ADR-204): 0,08 de boca; 30 grados los
  ojos del todo a un lado, y 20 a un lado, 15 arriba y 35 abajo para que le mire; apartar
  la vista a 0,55 y 0,65; el segundo de antes de la voz, 30 s de memoria y diez miradas
  por segundo. Son ajustes de cómo mira, no producto; los pone a
  prueba E-R04-02, con su cámara.
- PA-R04-06 a PA-R04-09, de esperadas a verdes. Para eso, el conductor de la 0.4 enchufa
  sus dobles donde irían la cámara y MediaPipe, y los de la 0.3 llevan tres ganchos para
  dibujar la cara en el momento justo: cuando el micro lee lo último de un turno, cuando
  el modelo recibe la petición y cuando el altavoz empieza a sonar. En cada uno la cara se
  lee en cuanto se pinta sola, como en todas las pruebas de la cara desde la ronda 2 de
  Codex sobre la PR #702, y después se le deja el tiempo que tarda en mover los ojos.
  Ninguna prueba cambia lo que mira.

## Comprobación que la sostiene

- Las ocho pruebas de aceptación de la pieza D en verde, PA-R04-06 a PA-R04-09; las de
  las piezas B y C siguen en verde, y las demás de la 0.4, en `xfail` estricto con su
  pieza.
- Pruebas nuevas, 126: 44 de la cámara y MediaPipe con módulos de mentira
  (`tests/unit/test_vista_adaptadores.py`), 27 de la vista, su hilo y la atención
  (`tests/unit/test_vista_local.py`), 20 de lo que se instala, 10 de la cámara en la
  ventana, 7 del oído, 5 de la vida de la cara, 4 de la telemetría de ONNX Runtime, 3 del
  widget, 2 y 2 de que el oído y la voz la apagan antes de cargar, y 2 de que las pruebas
  de la 0.2 y la 0.3 no abren ninguna cámara.
- Ninguna prueba de la 0.2 ni de la 0.3 abre una cámara: sus conductores no enchufan
  vista, y la de verdad no carga nada mientras falte el modelo de las caras, que en las
  pruebas falta; con la ventana abierta, ninguna biblioteca de la vista se importa.
- Mutación: 83, cada una con su caché de bytecode vacía y su fichero restaurado byte a
  byte, y caen las 83 sobre el código final. Por el camino vivieron tres, y cada una
  pidió una prueba más fuerte: un cambio de adónde mirar a medio salto, el recorte de una
  cara que se quedaba agarrado al fotograma entero y los ojos que miran arriba con la
  cabeza baja.
- **La batería entera, con las cuatro piezas de la 0.4 juntas**: 9 675 en verde, 15 omitidas
  y 2 xfail, en 33 min 9 s, y una roja: la medida de rendimiento de construir el contexto,
  que tras media hora de pruebas pasa en este ordenador de su tope de disparate, 1 500 ms.
  Sola, en verde, con un P95 de 756 ms. Tras las mismas pruebas de la ventana y de
  aceptación, `main` llega a 1 433 ms y el paquete a 1 860: no la mueve ninguna de estas
  piezas, que no tocan el contexto, sino lo que tarda este ordenador al cabo de un rato. Y
  ningún hilo queda vivo al acabar las pruebas de la 0.4.
- El modelo de las caras: su huella y lo que lleva dentro, mirados en el fichero que baja
  la dirección fija.
- Con MediaPipe 1.1.1 de verdad, en un entorno aparte, el adaptador ve la cara de la foto
  de pruebas de OpenCV, una que mira a la cámara con la cabeza girada unos 20 grados y los
  ojos compensándolo. La primera regla para saber si le miraban, la cabeza de frente y los
  ojos sin irse, decía que no; la de ahora dice que sí, también con la foto volteada. Lo
  que dio MediaPipe de las dos queda en las pruebas, y fija hacia dónde va cada cosa.
- ONNX Runtime 1.24.4 trae `disable_telemetry_events`, mirado en su paquete; la variable
  que pone InsightFace 2.1, en su `__init__.py`.
- El candado: `uv lock` añade MediaPipe 1.1.1 con `opencv-contrib-python` 5.0.0.93 y sus
  dependencias, con ruedas para Windows; ningún otro OpenCV.

## Consecuencias

- Sirius ve, si el propietario instala los ojos; sin ellos oye y habla igual, y lo dice.
- La cara mira a quien habla, aparta la vista al pensar y vuelve a quien le habló.
- Lo que alguien le dice mirándole llega al modelo aunque no diga su nombre; por eso
  también, alguien que pase mirándole y hablando con otro puede llegarle, y E-R04-02 lo
  mide.
- La orden de instalar la voz tiene un extra más. El propietario tiene por delante el día
  uno de los ojos (E-R04-01) y que le mire a él (E-R04-02).
- La pieza E podrá traer InsightFace sin un segundo `cv2`, y con la telemetría de ONNX
  Runtime ya apagada.

## Alternativas descartadas y por qué

- **Mirar en el hilo de la ventana**: la cara se pararía con cada fotograma.
- **Un proceso aparte**: más sitios por donde pasan los fotogramas, y otro Python que
  arrancar y cerrar.
- **Que le mire quien tiene la cabeza de frente y los ojos quietos**: fue la primera regla.
  Quien está a un lado de la cámara gira la cabeza para mirarle, y quien la tiene girada
  le mira con los ojos; la foto de pruebas lo enseñó.
- **Que la cara mire a quien está más al centro siempre**: no miraría a quien habla.
- **Decidir quién habla por la voz**: con un micro no se sabe de dónde viene; la boca que
  se mueve, sí.

## La lección

- ninguna: lo que salió al hacerla quedó arreglado antes de la revisión. La regla de si
  le miran, con MediaPipe de verdad sobre una foto; un aviso de la cámara que se borraba
  al medio segundo, y otro que nadie podía ver, en Model Studio, al repasar la ventana; y
  dos pruebas que no veían lo que vigilaban, con la mutación.

## Revisión externa

La de la PR #703, que trae las piezas D a G, de ADR-262 a ADR-265, se cuenta aquí, en el
primero del paquete.

Alcance, escrito antes de la primera petición: que ninguna imagen ni ninguna huella se
guarde en claro ni salga del ordenador, y que lo de un desconocido no se guarde; que los
reconocedores y el estimador de verdad se carguen en el hilo de la vista, sin parar la
ventana ni la charla; que la regla de no insultar llegue al modelo siempre que tiene delante
a un crío, a un anciano o a alguien cuya edad no se lee segura, y solo entonces; que quitar
el permiso borre sus huellas y su nombre de lo que recuerda haber visto, y que los nombres
de lo que ve solo vayan a un modelo de este ordenador; y que las pruebas de la 0.4 vean lo
que vigilan, sin dobles más permisivos que lo que doblan.

Antes de la primera petición, un repaso propio del paquete entero encontró cuatro cosas, que
cuentan ADR-263, ADR-264 y ADR-265: reconocer miraba también el modelo de la edad; ninguna
prueba fijaba lo que monta Sirius para reconocer; «# Quién hay» y «# Lo que has visto» iban
también a un modelo de fuera; y lo de hace más de un día solo se borraba al apuntar algo
nuevo.

- **Ronda 1, sobre `03c3b0d7`**: tres hallazgos, los tres ciertos.
  - **P1, una cara heredaba nombre y edad solo por la posición.** Lo que se supo de una
    cara valía 2 s para cualquiera que apareciera cerca de donde estaba, aunque entre medias
    no se viera ninguna: si Marta se iba y un crío ocupaba su sitio, «# Quién hay» lo habría
    llamado Marta y la regla no habría ido. Ahora vale solo para la del fotograma siguiente
    que esté cerca, si se la sigue viendo sin hueco: tras un fotograma sin nadie, o medio
    segundo sin mirar, se reconoce y se estima de nuevo.
  - **P1, la voz de las órdenes de memoria no llevaba la regla de no insultar**, y esa
    frase también la escribe el modelo. Ahora la lleva, con las mismas condiciones que la
    charla.
  - **P1, lo de hace más de un día seguía en la base sin cambios ni charla.** El repaso
    propio había añadido el borrado al leer, y con un modelo de fuera ya no se lee. Es la
    misma familia, encontrada a medias en el repaso y entera aquí: un mantenimiento atado a
    un suceso que puede no llegar. Ahora lo borra también la vista, cada minuto como mucho,
    vea o no: con Sirius abierto no depende de nada más.

  Cada arreglo, con su prueba vista caer con el código de antes, y mutación: cuatro
  cambios a propósito en seguir la cara, dos en la voz de la orden y cinco en el borrado;
  las pruebas cazan los once.
- **Ronda 2, sobre `2710c078`**: dos hallazgos P1, los dos ciertos, y los dos de familias
  que ya había traído la ronda 1.
  - **P1, la prueba a ciegas y las preguntas trampa escribían como Sirius sin la regla de
    no insultar**, con la cámara encendida: son diálogos aparte, no Model Studio. Es la
    familia de la voz de las órdenes en la ronda 1: la regla se ponía camino a camino.
  - **P1, si el detector fallaba tras un fotograma bueno, lo de antes seguía valiendo**: el
    nombre y la edad de Marta para quien ocupara su sitio. Es la familia de la cara que
    heredaba por la posición en la ronda 1: lo que se sabe de quién hay se daba por
    actual sin comprobarlo.

  **Dos rondas seguidas con las mismas familias**: se dejó de parchear y se buscó la raíz
  (ADR-001). Se decidió seguir, con estas dos:
  - **La regla, para toda petición que escribe como Sirius.** Decide `CareWatch`, uno por
    sitio y todos con la misma lectura de la vista: la llevan la charla, la voz de las
    órdenes, la prueba a ciegas y las preguntas trampa, mirada en cada pregunta. Y
    `CARE_COVERAGE` dice de cada petición al modelo si la lleva o por qué no: una guarda
    las busca todas en el código, y una nueva no pasa sin que alguien lo decida.
  - **Lo que se sabe de quién hay, solo del último fotograma que se pudo leer.** Al abrir
    la cámara, en la vuelta que no lee fotograma o en la que el detector falla, y mientras
    mira quiénes son y qué edad tienen las caras nuevas, la vista no sabe quién hay: no lo
    dice, la edad es duda y va la regla. Lo que recordaba de cada cara se olvida.

  Cada arreglo, con su prueba vista caer con el código de antes, y mutación: ocho cambios
  a propósito en la duda de la vista y seis en la regla, del montaje a la guarda y las
  cachés de la prueba a ciegas; las pruebas cazan los catorce.
- **Ronda 3, sobre `1f6a9847`**: tres hallazgos P1, los tres ciertos, de las dos mismas
  familias, y los tres nacidos de los arreglos de la ronda 2.
  - **P1, la prueba a ciegas guardaba la regla de cada pregunta para todos los modelos.**
    Hace las 20 de un modelo antes de pasar al siguiente: si llegaba un crío entre medias,
    los demás contestaban sin ella. Familia de la regla.
  - **P1, quien leía la edad podía juntar dos momentos.** Miraba la duda y después las
    caras, por separado: si el hilo de la vista entraba en duda entre las dos, leía que no
    había nadie, y la regla no iba. Familia de lo que se sabe de quién hay.
  - **P1, quitar el permiso con la cara quieta en su sitio no ponía en duda a nadie**, y
    mientras se volvía a reconocer a todos se seguía diciendo su nombre: la duda de la
    ronda 2 miraba la cara, no los permisos. Misma familia.

  **Tres rondas seguidas con las mismas familias, y esta, en lo que se puso como raíz**: lo
  de la ronda 2 eran más sitios donde poner la duda o la regla, cada uno con su forma de
  equivocarse. Se paró, se le contó al propietario y se buscó la raíz otra vez, con la
  nota de arranque de este arreglo:
  1. **Dónde vive el fallo y dónde va el arreglo.** En que quien usa lo que se sabe de quién
     hay lo daba por bueno sin poder comprobarlo: lo leía en varios trozos, o lo guardaba
     para después. El arreglo va donde se usa, que es lo único que puede ver si sigue
     valiendo en ese momento: al leer lo que ve, al escribir cada petición y al apuntar.
  2. **Qué no garantiza.** Una respuesta que ya se está escribiendo cuando llega un crío
     acaba como empezó, sin la regla; y lo que la cámara no ve, como dos caras que se
     cambian de sitio entre dos fotogramas, la vista tampoco lo sabe.
  3. **Criterio de parada**, escrito antes de pedir la ronda 4: si trae otro hallazgo de
     estas familias, no se arregla; se para y se le pregunta al propietario si sacar del
     paquete lo que lo cause.
  4. **Qué lo hace imposible y no improbable.** Juntar dos momentos, una foto que no se
     cambia y se lee de una vez; darla por actual, la comprobación al leerla; la regla
     guardada, mirarla en cada petición. Esto último lo vigilan pruebas, no una guarda: lo
     ya contestado se guarda por la regla con que se pidió, y la guarda tendría que leer
     de dónde sale cada clave.

  Y la raíz, escrita como tres reglas:
  - **Lo que se sabe de quién hay se deja de una vez y se comprueba al leerlo.** La vista
    deja una sola foto (`_View`): si ve, si sabe quién hay, el momento del último fotograma
    que pudo leer entero, con qué permisos reconoció cada cara y lo que vio de ella. Quien
    la lee, la lee una vez, y comprueba que sea de hace como mucho un segundo y, los
    nombres, que nadie haya dado ni quitado su permiso desde que se reconocieron. No la
    deja si entretanto soltó la cámara o la volvió a abrir, y lo que recordaba de cada
    cara no pasa de una vez a la siguiente.
  - **Un nombre solo sale o se guarda si quien lo lleva tiene permiso en ese momento.** La
    charla lo mira al escribir cada petición, para quien le habla y para quienes tiene
    delante; lo que recuerda haber visto, al apuntar, con el cerrojo con el que se quita.
  - **La regla se mira al construir cada petición, y nunca se guarda.** En la prueba a
    ciegas y en las preguntas trampa, también al volver a pedir una que falló; lo ya
    contestado se guarda con la regla con que se pidió.

  Cada arreglo, con su prueba vista caer con el código de antes: de las dieciséis pruebas
  nuevas caen quince, y la otra fija que soltar la cámara mientras mira no deja nada por
  visto, que el código de antes ya hacía bien y ahora vigila la mutación. Y mutación:
  veintiún cambios a propósito, de la foto de la vista a los permisos, lo apuntado y la
  regla; las pruebas cazan los veintiuno.
- **Ronda 4, sobre `95ea6aef`**: tres hallazgos P1, los tres ciertos, de la familia de la
  regla: se mira un momento antes de escribir la petición, y entre medias se eligen los
  ejemplos de la semilla, que pide huellas a Ollama. Pasa en la voz de las órdenes de
  memoria, en la prueba a ciegas y en las preguntas trampa. Por el criterio de parada no
  se arreglaron: se le preguntó al propietario, y decidió el 20-10-2026 no cerrar ese
  hueco, que es de un momento. Queda escrito en ADR-264, en «Consecuencias».
- **Ronda 5, sobre `865ec729`**: un hallazgo P1, cierto, de otra clase. Si al quitar el
  permiso se borraban sus huellas pero no se podía quitar su nombre de lo que recuerda
  haber visto, porque la base estaba ocupada, la ventana decía «Prueba otra vez» y ya no
  le listaba, y el nombre se quedaba en la base hasta que la charla lo leyera. Ahora lo
  quita el repaso que la vista pide cada minuto, que quita el nombre de quien ya no tiene
  permiso, y quitar el permiso no dice que ha fallado: sus huellas están borradas. Con la
  prueba vista caer con el código de antes, y mutación: tres cambios a propósito, y las
  pruebas cazan los tres.
