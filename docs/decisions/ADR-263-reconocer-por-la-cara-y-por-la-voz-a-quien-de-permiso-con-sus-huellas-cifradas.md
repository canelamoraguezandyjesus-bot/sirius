# ADR-263 — Reconocer por la cara y por la voz a quien dé permiso, con sus huellas cifradas

- Estado: APROBADO
- Fecha: 2026-10-19
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Es la pieza E de la 0.4, en el orden
  de ADR-259.

Este ADR es además la **nota de arranque** de la pieza E. Se escribe antes de su primera
línea de código. Los umbrales de la pieza los fijó ADR-259 en
`docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md`, PA-R04-10 a PA-R04-12 y E-R04-03, antes de que
la pieza existiera, y aquí no se añade ni se afloja ninguno.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** Con la pieza D, Sirius ve caras pero
   no sabe de quién son, y oye voces sin saber quién habla. El plan pide reconocer a quien
   dé permiso, por la cara con InsightFace y por la voz con ECAPA, con las huellas
   cifradas y sin salir del ordenador; y a quien no lo dio, tratarle como «sin
   identificar» sin guardar su huella (§6, «Lo que se hace», 2). El arreglo va en siete
   sitios:
   - **Los puertos de reconocer**, sin tipos de ninguna biblioteca: de un recorte de
     cara, su huella; de lo que sonó en un turno, la de su voz, o ninguna si no hay voz.
   - **Las huellas guardadas**, en la base, cifradas con una llave que vive en el
     almacén de secretos de Windows, el mismo de las claves de Sirius. Sin un almacén
     seguro no guarda ninguna: lo dice y no reconoce a nadie.
   - **Quién es quién**, en la aplicación: compara cada huella con las guardadas y da un
     nombre o «sin identificar». La huella de quien no dio permiso se compara en memoria
     y se suelta; no hay camino para guardarla.
   - **La vista y el oído** le preguntan: la vista, de cada cara que ve, sin hacerlo en
     cada fotograma; el oído, de la voz de cada turno que va a la charla.
   - **La charla** le dice al modelo quién le habla y a quiénes tiene delante.
   - **La ventana**: dar permiso, con el nombre, la cara delante y una frase dicha en voz
     alta; y quitarlo, que borra sus huellas.
   - Y lo que lo instala: el extra `ojos` trae InsightFace y SpeechBrain, y la orden de
     instalar baja sus modelos, fijos y con su huella.

   **¿Puede el sitio del arreglo observar el fallo?** En parte. Que una huella guardada
   no esté en claro, que la de un desconocido no se guarde y que nada salga, sí: las
   pruebas buscan las huellas de los dobles en la base y en el diario en cada forma en que
   se guardan unos números, y vigilan disco y red. Que InsightFace y ECAPA acierten, no:
   eso se mide en su ordenador, en E-R04-03.
2. **Qué NO garantiza.**
   - Que reconozca bien: los dobles dan la misma huella a la misma persona. Lo mide
     E-R04-03, con sus umbrales.
   - Que la llave esté a salvo de quien entre en su Windows con su usuario: el almacén de
     secretos la protege con su sesión, no de ella.
   - Que quien da permiso sea quien dice: Sirius guarda el nombre que escribe.
   - La edad y lo que recuerda de lo que ve: son las piezas F y G.
3. **Criterio de parada**, decidido antes de escribir el código:
   - Las cinco pruebas de la pieza E en verde, PA-R04-10 a PA-R04-12, y la batería
     entera.
   - Si InsightFace no da una huella de la cara de la foto de pruebas con lo que da
     MediaPipe, o ECAPA no carga sin conexión, se para y se dice.
   - Si hace falta guardar algo de un desconocido para reconocerle, se para: el plan lo
     prohíbe.
   - Dos rondas seguidas de Codex con la misma familia: se deja de parchear y se busca la
     raíz.
4. **Qué lo haría imposible.**
   - **Que la huella de un desconocido se guarde**: la única escritura de huellas es dar
     permiso, con el nombre que se escribe en la ventana; reconocer solo lee.
   - **Que una huella quede en claro**: se cifra antes de llegar a la base, y sin llave de
     un almacén seguro no hay escritura.
   - **Lo que no se puede hacer imposible**: que confunda a dos personas parecidas. Se
     hace improbable con los umbrales y con las medidas del propietario.

## Contexto y problema

Con la pieza D, Sirius ve caras y oye voces, pero no sabe de quién son. El plan pide
reconocer a quien dé permiso, por la cara con InsightFace y por la voz con ECAPA, con sus
huellas cifradas y sin salir del ordenador, y tratar a quien no lo dio como «sin
identificar», sin guardar su huella (§6, «Lo que se hace», 2). Lo aprobado en ADR-259 lo
concreta: el modelo lee en cada petición quién le habla y a quiénes tiene delante, y quien
no ha dado permiso, el propietario incluido, es «sin identificar».

Una huella de una cara o de una voz identifica a una persona: es un dato que no puede
quedar en claro, ni guardarse de quien no lo autorizó, ni quedarse cuando lo retira. Y el
tiempo manda como en la pieza D: cargar los modelos tarda segundos, sacar una huella,
decenas de milisegundos, y la ventana no puede esperar a nada de eso.

## Opciones consideradas

1. **InsightFace entero**, con su detector, sobre cada fotograma: buscaría las caras otra
   vez, cuando MediaPipe ya las da, y con su modelo de detectar, que no hace falta.
2. **El recorte de MediaPipe y el modelo de reconocer de InsightFace**: la vista da de
   cada cara su recorte y cinco puntos, los ojos, la nariz y las comisuras, sacados de
   los de MediaPipe; InsightFace la endereza con ellos y saca su huella. **Esta.**

Y para guardarlas:

1. **En claro en la base**: el plan lo prohíbe.
2. **Cifradas con una llave en la base o en los ajustes**: es lo mismo que en claro para
   quien se lleve el fichero.
3. **Cifradas con Fernet y la llave en el almacén de secretos**, el mismo de las claves de
   Sirius, que en Windows es el administrador de credenciales; y sin almacén seguro, sin
   llave y sin huellas. **Esta.**

## Decisión

Se adoptan las dos últimas.

- **Los puertos**, en `src/sirius/ports/recognition.py`, sin tipos de ninguna
  biblioteca: de un recorte de cara, su huella; de lo que sonó en un turno, la de su voz,
  o ninguna si no hay bastante voz; dónde se guardan, ya cifradas; y quien las cifra.
- **Quién es quién**, `Recognition`, en `src/sirius/application/recognition.py`. Compara
  la huella de una cara o de una voz con las de quien dio permiso, y da su nombre si se
  parece lo bastante, 0,4 la cara y 0,35 la voz; si no, nadie. Sin nadie que haya dado
  permiso, ni la saca. La huella comparada se suelta en el acto: reconocer solo lee.
- **Dar permiso**, desde la ventana, con tres pasos, y cada uno lo da quien lo capta: la
  ventana empieza con el nombre; la vista da la cara en cinco fotogramas en que la
  persona está sola delante, y se queda la huella que más se parece a las demás, que un
  fotograma movido no la estropee; y el oído, lo que sonó en el turno siguiente, una
  frase que se le pide decir en voz alta, que no se transcribe ni va a la charla. Solo
  entonces se cifran las dos huellas y se guardan juntas, en lugar de las que tuviera esa
  persona. Cancelar en cualquier paso no guarda nada.
- **Quitar el permiso** borra todas las huellas de esa persona, y lo borrado se pone a
  ceros en el fichero (`secure_delete`), su nombre incluido. La ventana lista a todos los
  que tienen huellas guardadas, también si ya no se pueden leer, para que siempre se
  puedan borrar.
- **Las huellas, cifradas** (`src/sirius/adapters/recognition/sealer.py`): Fernet, AES con
  su HMAC, sobre sus números en float64. La llave se crea al azar la primera vez que hay
  que cifrar, y solo en un almacén seguro.
- **La base** gana la tabla `recognition_prints`, con su migración: de quién, de qué y la
  huella cifrada. Olvidar (ADR-239) no la toca: no guarda nada dicho, y la borra quitar
  el permiso; así queda en `FORGET_COVERAGE`.
- **La vista** reconoce cada cara al aparecer y después cada 2 s, siguiéndola por dónde
  está; si alguien da o quita su permiso, vuelve a mirar a todos. **El oído** dice a la
  charla quién le habla, de la voz de cada turno que va a ella. Un fallo de quien reconoce
  se apunta una vez, con su tipo, y esa vez es «sin identificar».
- **La charla** le dice al modelo, en «# Quién hay», quién le habla en un turno de voz y a
  quiénes tiene delante, su nombre o «alguien sin identificar», con una regla: solo
  reconoce a quien le dio permiso, y a los demás, aunque le digan quiénes son, no dice que
  los reconoce. Lo escrito en la ventana no lleva quién lo escribe.
- **Cargar**, la primera vez que hace falta, en el hilo de la vista o del oído; la ventana
  lee y cambia el permiso sin esperar a que acabe. Si no carga, se dice una vez por qué y
  no se vuelve a intentar.
- **Lo que se instala**: el extra `ojos` gana InsightFace 2.1 y SpeechBrain 1.1.2, y la
  orden de instalar baja el paquete `buffalo_l` de la versión 0.7 de los modelos de
  InsightFace, mira su huella, se queda solo con el modelo de reconocer caras y el de la
  edad, para la pieza F, y lo borra; y ECAPA de Hugging Face, fichero a fichero, como la
  voz de personaje. Después mira que carguen. ECAPA se carga sin red y sin enlaces
  simbólicos, que en Windows piden administrador.
- El diario no lleva nombres ni huellas: dice que alguien dio o quitó su permiso.

## Comprobación que la sostiene

- **Las cinco pruebas de la pieza E**, PA-R04-10 a PA-R04-12, en verde con el conductor de
  la 0.4: reconoce por la cara y por la voz a quien dio permiso; a un desconocido lo trata
  como «sin identificar» y no guarda su huella; las huellas van cifradas, no salen del
  ordenador, sirven tras cerrar y volver a abrir, y se borran al quitar el permiso. Y los
  reconocedores son los que monta Sirius sin dobles, InsightFace y ECAPA.
- **111 pruebas nuevas**: 29 de quién es quién, de dar y quitar el permiso y de cargar
  (`tests/unit/test_reconocer.py`); 16 de la orden de instalar; 12 de InsightFace y ECAPA
  con módulos de mentira; 11 del cifrado y de la llave; 10 de la vista que reconoce sin
  hacerlo en cada fotograma; 8 de la ventana; 7 de la base, con lo borrado fuera del
  fichero; 7 del oído; 5 de «# Quién hay»; 4 de la charla; y 2 del recorte de la vista.
- **Mutación**: 63 cambios a propósito, de quién es quién y el permiso al cifrado, la base,
  la vista, el oído, la charla, la orden de instalar, la ventana y el montaje. A la primera
  cayeron 62; el que vivía, cargar los reconocedores con el cerrojo de cambiar el permiso,
  pidió que la prueba de la ventana mirara a tiempo mientras se cargan, y con ella caen
  los 63.
- InsightFace 2.1 y MediaPipe 1.1.1 de verdad, en un entorno aparte, con los adaptadores
  de Sirius: de la foto de pruebas, una huella de 512 números de longitud uno. La misma
  cara en espejo se parece 0,919; al 60 %, 0,989; recortada de otro modo, 0,99. En la
  foto de grupo que trae InsightFace, por trozos, la misma cara vista en trozos distintos
  se parece como poco 0,686, en 18 parejas; seis personas distintas, como mucho 0,175,
  en 15; y la foto de otra persona, contra todas, 0,163. El umbral está en 0,4.
- ECAPA, con SpeechBrain 1.1.2 y torch 2.14.1 de verdad y unos pesos al azar con la forma
  de los de verdad, que Hugging Face no se alcanza desde aquí: carga con todas las
  conexiones prohibidas y ningún intento; de 2 s da 192 números de longitud uno, de
  0,4 s ninguna, y no escribe nada en su carpeta. Que reconozca de verdad lo mide el
  propietario en E-R04-03.
- El candado: `uv lock` añade InsightFace 2.1, SpeechBrain 1.1.2, scikit-image 0.26.0 y
  sus dependencias, con el mismo torch que la voz de personaje; `opencv-python` queda en
  él solo con el marcador que nunca se cumple, y una prueba mira que siempre sea así.
- Al pasar la batería entera con las cuatro piezas de la 0.4 juntas, cuatro pruebas de la
  0.3 fallaban: su conductor, que vigila que no se guarde audio en la base, tomaba
  `recognition_prints` por una tabla nueva, y así lo tenía que decir. Ahora la cuenta entre
  las tablas de Sirius y la mira columna a columna, como las demás.
- **La batería entera, con las cuatro piezas de la 0.4 juntas**: 9 675 en verde, 15 omitidas
  y 2 xfail, en 33 min 9 s, y una roja: la medida de rendimiento de construir el contexto,
  que tras media hora de pruebas pasa en este ordenador de su tope de disparate, 1 500 ms.
  Sola, en verde, con un P95 de 756 ms. Tras las mismas pruebas de la ventana y de
  aceptación, `main` llega a 1 433 ms y el paquete a 1 860: no la mueve ninguna de estas
  piezas, que no tocan el contexto, sino lo que tarda este ordenador al cabo de un rato. Y
  ningún hilo queda vivo al acabar las pruebas de la 0.4.

## Consecuencias

- El propietario puede darle permiso, y E-R04-03 empieza por eso. Mientras no lo dé, él
  también es «sin identificar»: lo pide ADR-259.
- Cada petición lleva «# Quién hay», unas cuarenta palabras, cuando habla por voz o la
  cámara ve.
- La orden de instalar baja unos 280 MB de InsightFace, de los que se quedan 175, y unos
  90 de ECAPA. Los modelos de InsightFace son solo para investigación no comercial
  (ADR-259): Sirius no se distribuye ni se vende.
- La huella de la voz sale de una sola frase: si no reconoce bien su voz, se le puede
  pedir más; lo dirá E-R04-03.
- La pieza F tiene ya el modelo de la edad en su sitio.

## Alternativas descartadas y por qué

- **InsightFace entero**: buscaría las caras otra vez.
- **Guardar una foto para reconocer mejor**: no se guardan imágenes (§2 del plan).
- **La media de las cinco caras** en vez de la que más se parece a las demás: la media no
  es ninguna cara vista, y un fotograma movido la arrastra.
- **No decirle al modelo quién hay mientras nadie haya dado permiso**: se probó, y las
  pruebas aprobadas en ADR-259 piden «sin identificar» también entonces.

## La lección

- familia: `cerrojo-cogido-mientras-tarda`
- sin esto se repetiría: un solo cerrojo para todo, cogido también mientras se cargan
  InsightFace y ECAPA, que tarda segundos en el hilo de la vista; la ventana mira el
  permiso dos veces por segundo y se habría quedado esperando, congelada. Salió al
  repasar el código antes de escribir sus pruebas: ahora cargar tiene su propio cerrojo,
  y el de cambiar el permiso nunca se coge mientras algo tarda
- lo hace cumplir: `tests/unit/test_reconocer.py`
