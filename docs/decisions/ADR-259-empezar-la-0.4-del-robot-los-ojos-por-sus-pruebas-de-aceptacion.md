# ADR-259 — Empezar la 0.4 del robot, los ojos, por sus pruebas de aceptación

- Estado: APROBADO
- Fecha: 2026-10-18
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). El plan que ejecuta lo aprobó el
  propietario el 06-10-2026 (ADR-232). El 18-10-2026 decidió que la 0.4 empieza sin
  esperar a sus pruebas (ADR-257) y pidió seguir con lo que falta del plan: «ponte con lo
  que nos falta, lo que tenemos en el plan».

Este ADR es además la **nota de arranque** de la versión 0.4 de
`docs/evolution/PLAN_DEL_ROBOT.md` (skill `disciplina-evidencia`): las cuatro preguntas
y el criterio de parada están escritos antes de la primera línea de código de los ojos y
antes de cualquier revisión.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** Sirius no tiene ojos ni cara: la única
   captura de vídeo que existe es la de grabar con OBS de Model Studio, que no sirve
   para esto (§6 del plan, «Ya está hecho»). El plan pide una cámara que detecte caras
   en local, reconocer a quien dé permiso por la cara y por la voz, una regla para
   críos y ancianos, una cara dibujada y viva en la ventana que mire a quien habla, unos
   gestos de una lista cerrada y recordar lo que ve como texto. Todo va encima de la 0.3:
   la cara en la ventana de siempre, la mirada y el reconocimiento entregan a la misma
   charla quién hay delante y quién habla, y la mirada se suma al oído para saber si le
   hablan a él. **¿Puede el sitio del arreglo observar el fallo?** Una parte sí: que lo
   visto llegue a la charla, que la cara se dibuje y no se congele, que nada salga ni se
   guarde lo ven las pruebas con dobles. La otra no: que le mire a él, que le reconozca,
   que no insulte a un crío y que la cara parezca viva solo se ve en su ordenador, con su
   cámara. Por eso cada «terminado cuando» tiene su evaluación del propietario, con el
   umbral fijado hoy.
2. **Qué NO garantiza.**
   - Las pruebas de máquina usan dobles que llevan escrito lo que hay delante:
     demuestran adónde llega lo visto, no que la cámara y los modelos acierten.
   - En el contenedor de las sesiones no hay cámara ni gráfica: que todo quepa en sus 6 GB
     junto al modelo de la charla, el oído y la voz se mide en su ordenador (E-R04-01).
   - Que las herramientas funcionen en su Windows: aquí se resuelven sus dependencias
     para Windows con Python 3.14; que se instalen y arranquen lo ve E-R04-01.
   - Que el cifrado de las huellas sea bueno: las pruebas ven que no están en claro; con
     qué se cifran y dónde vive la llave lo decide y lo justifica el ADR de la pieza E.
   - Lo que se esconda a propósito: las pruebas buscan imágenes y huellas donde las
     dejaría un error; el engaño lo mira la revisión del código de cada pieza (lección de
     ADR-241).
3. **Criterio de parada**, fijado antes de ver ninguna medida ni ninguna revisión:
   - **Las evaluaciones**, E-R04-01 a E-R04-05, con sus umbrales en
     `docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md`, fijados hoy. Si el día uno lo que ve no
     cabe en su gráfica, va al procesador y se vuelve a medir; si tampoco así, se para y
     se le pregunta, porque lo que queda es dinero o producto.
   - **Las PR de la 0.4**: cadena de comprobación verde, una ronda limpia de Codex sobre
     el head de contenido y Quality en verde. Dos rondas seguidas con la misma familia: se
     deja de parchear y se busca la raíz.
   - **El orden del plan**, como lo dejó ADR-257: la 0.4 empieza sin esperar a sus
     pruebas de la 0.2 y la 0.3, y ninguna versión se da por terminada hasta que pasan.
   - Si una pieza pide dinero o cambia el producto, se para y se le pregunta. Ver más de
     lo que ven las herramientas del plan, como qué lleva puesto la gente, es producto.
4. **Qué lo haría imposible.**
   - **Que una imagen salga o se guarde.** Los fotogramas viven en memoria mientras se
     miran y la base no tiene dónde ponerlos. El vigilante de la 0.3 apunta cualquier
     fichero que algo abra para escribir fuera de la base, los ajustes y el diario, y
     cualquier conexión; al acabar se buscan además ficheros de imagen, la marca de los
     fotogramas y cabeceras de imagen en la base y en el diario (PA-R04-09).
   - **Que se guarde la huella de un desconocido.** Solo se guarda la de quien da
     permiso, y la de cualquier otro se tira tras compararla; una prueba cuenta las
     huellas guardadas antes y después (PA-R04-11).
   - **Que una huella salga del ordenador.** Los modelos los instala una vez la orden de
     instalar, y en marcha nada se conecta a ningún sitio (PA-R04-06, PA-R04-09 y
     PA-R04-12).
   - **Lo que no se puede hacer imposible:** que reconozca siempre a quien es, que
     acierte la edad y que la cara guste. Se hace improbable con la regla de «ante la
     duda, no insulta» y con las medidas del propietario.

## Contexto y problema

La 0.3, «Voz», está programada entera: sus 10 PA están en verde y le quedan las
evaluaciones del propietario. La noche del 17 al 18-10-2026 el propietario pasó E-R02-04 y
E-R02-05 y decidió que la 0.4 empieza sin esperar a las demás (ADR-257).

Lo siguiente del plan es la 0.4, «Ojos» (§6): la cámara del ordenador con MediaPipe;
reconocer a quien dé permiso, por la cara con InsightFace y por la voz con ECAPA, con las
huellas cifradas y sin guardar la de un desconocido; la regla del propietario con críos
y ancianos frágiles; su cara dibujada en la app, viva en reposo, que mira a quien habla,
aparta la vista al pensar y mueve la boca con el volumen de su voz; gestos de una lista
cerrada que el modelo escribe entre corchetes; y recordar lo que ve como texto. Termina
cuando mira al propietario cuando habla, reconoce a los que dieron permiso, no insulta a
un crío en la prueba y nunca se queda congelado aunque el modelo tarde.

La §3 del plan pide, antes de la primera línea de código, sus pruebas de aceptación, y el
plan pide comprobar antes de instalar una herramienta que sigue existiendo y cuál es su
licencia.

## Opciones consideradas

1. **Esperar a sus pruebas de la 0.2 y la 0.3.** Él decidió lo contrario el 18-10-2026.
2. **Empezar la 0.4 como la 0.3**: comprobar las herramientas, su licencia y que se
   resuelven con nuestro Python en Windows, y después la nota de arranque y las pruebas
   de aceptación, antes del código. **Esta.**
3. **Empezar por la cara sin pruebas**, porque es lo que más se ve. Es lo que la §3
   prohíbe, y la 0.2 y la 0.3 enseñaron que una prueba escrita después mira lo que hace el
   código, no lo que pide el plan.

## Decisión

Se adopta la opción 2.

**Las herramientas del plan, comprobadas el 18-10-2026**, con una resolución de
dependencias para Windows x86_64 con Python 3.14, junto a la voz y la voz de personaje
que ya instala (`uv pip compile --python-version 3.14 --python-platform
x86_64-pc-windows-msvc pyproject.toml --extra voz --extra personaje`, con `mediapipe`,
`insightface` y `speechbrain` encima y ruedas para todo lo pesado): 167 paquetes, sin
compilar nada. Las licencias, de los metadatos de cada paquete instalado sin
dependencias:

| Pieza del plan | Qué hay | Licencia |
|---|---|---|
| MediaPipe | `mediapipe` 1.1.1, con `opencv-contrib-python` 5.0.0.93 y `matplotlib` 3.11.2 | Apache-2.0 |
| InsightFace | `insightface` 2.1, con `opencv-python` 5.0.0.93, `scikit-image` 0.26.0 y `onnxruntime` 1.24.4, el mismo que ya usa la voz | El código, MIT. **Los modelos que trae, solo para investigación no comercial**, lo dice su descripción |
| SpeechBrain ECAPA | `speechbrain` 1.1.2, con `torch` 2.14.1 y `torchaudio` 2.11.0, que ya trae la voz de personaje | Apache-2.0 |
| ONNX Runtime | `onnxruntime` 1.24.4 | MIT |

Cuatro cosas que salen de esa comprobación y que el plan no sabía:

- **Dos OpenCV que se pisan.** MediaPipe trae `opencv-contrib-python` e InsightFace
  `opencv-python`, y los dos ponen el mismo `cv2`: instalados juntos, el segundo pisa al
  primero. La pieza D deja solo uno, el de MediaPipe, que lleva todo lo del otro.
- **Los modelos de InsightFace no son libres.** El código es MIT, pero los modelos
  preentrenados que trae son solo para investigación no comercial. Sirius no se
  distribuye ni se vende: su licencia es de lectura pública y uso reservado
  (`LICENSE:3`), y el uso del propietario no es comercial. Queda escrito: si algún día lo
  fuera, harían falta modelos con licencia.
- **InsightFace 2.1 trae más que el análisis de caras**: una interfaz gráfica, una orden
  `insightface-privateframe` y descargas de modelos con `requests`. Sirius solo usa el
  análisis, con los modelos que deja la orden de instalar, y nada descarga en marcha.
- **La telemetría de ONNX Runtime.** ONNX Runtime trae `disable_telemetry_events`, e
  InsightFace 2.1 la apaga al importarse (`ORT_DISABLE_TELEMETRY=1`). La 0.3 lo carga
  sin apagarla. La pieza D la apaga antes de cargar ningún modelo, el del oído incluido.

**El orden de la 0.4**, una PR por pieza, cada una con sus pruebas pasando de esperadas a
verdes:

| Pieza | Qué trae |
|---|---|
| A | Esta nota y las pruebas de aceptación de toda la 0.4, antes del código |
| B | Su cara en la ventana: dibujada, viva en reposo, sin congelarse y con la boca al volumen de su voz. Sin herramientas nuevas; con ella, E-R04-05 |
| C | Gestos de una lista cerrada, que el modelo escribe entre corchetes y la cara hace |
| D | La cámara y las caras en local con MediaPipe: mira a quien habla, aparta la vista al pensar y, si le miran, le hablan a él; sin cámara, lo dice y sigue. Con ella, la orden que instala lo que ve y el día uno de los ojos (E-R04-01) |
| E | Reconocer por la cara y por la voz a quien dé permiso, con las huellas cifradas; quien no lo dio es «sin identificar» y su huella no se guarda |
| F | La regla de los críos y los ancianos frágiles, con la edad que estima InsightFace |
| G | Recordar lo que ve como texto: quién vino, a qué hora, quién se fue y quiénes hay |

**Las pruebas de aceptación** se llaman `PA-R04-NN` y viven en
`docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md`: 14, con 28 pruebas de máquina y cinco
evaluaciones del propietario, E-R04-01 a E-R04-05, con sus umbrales fijados antes de
medir. Salieron del §6 cláusula a cláusula, de lo que la 0.3 dejó para la 0.4 («desde
0.4, si le miran») y del §2, y lo que ninguna prueba puede ver está en «Lo que estas
pruebas no garantizan».

- **Hablan como el plan.** Las pruebas de máquina, en
  `tests/acceptance/test_robot_0_4_*.py`, dicen «Marta se pone delante», «da permiso»,
  «aparta la vista al pensar». Solo el conductor, `tests/acceptance/conductor_robot_0_4.py`,
  sabe cómo se hace cada cosa en el código: es el de la 0.3, con la charla, la memoria, el
  oído, la voz y la ventana montados como en producción, y dobles solo donde irían la
  cámara, el detector de caras, los reconocedores y el estimador de edad.
- **Los dobles hacen algo, y apuntan lo que hacen** (lección de ADR-241). La cámara da
  fotogramas en bytes con una marca dentro, para que una imagen guardada por error se
  reconozca; el detector encuentra en ellos las caras, con su sitio, si mueven la boca y
  si miran a la cámara; cada voz lleva su timbre dentro del audio, y solo el reconocedor
  de voces lo lee. Las huellas son como las de verdad: 512 números las de cara y 192 las
  de voz, de longitud uno exacta, siempre las mismas para la misma persona y poco
  parecidas entre dos distintas. Así una huella guardada en claro se encuentra en las
  formas en que se guardan unos números, en float32, en float64 o como texto, aunque la
  pieza la normalice. La cara de Sirius no es un doble: se lee de la ventana de verdad.
  `tests/acceptance/test_dobles_del_conductor_0_4.py` lo comprueba hoy, con el conductor
  construido de verdad, porque una prueba en `xfail` estricto no ejecuta ni una línea de
  él.
- **Quién es quién.** Sirius reconoce a quien ha dado permiso, y a nadie más: quien no lo
  ha dado, el propietario incluido, es «sin identificar». E-R04-03 empieza por eso: da
  permiso él y otra persona.
- **El inventario aprobado no se reduce**: 14 PA, 28 pruebas y cinco evaluaciones viven
  en `tests/acceptance/test_robot_0_4_trazabilidad.py`, como en la 0.2 y la 0.3.
- **Lo que las pruebas fijan y el código tendrá que cumplir**: lo que se lee de la
  ventana (la cara, cuántas veces se dibuja, sus partes y lo que dice de la cámara); que
  la herramienta de las caras se llame `mediapipe`; que «ceja_arriba» esté en la lista de
  gestos; que quien no es reconocido se diga «sin identificar»; y los umbrales de la vida
  en reposo, de la boca y de la mirada, en la tabla de las pruebas.

## Comprobación que la sostiene

- La resolución: `uv pip compile` para `x86_64-pc-windows-msvc` con Python 3.14, sobre
  `pyproject.toml` con los extras `voz` y `personaje` y `mediapipe`, `insightface` y
  `speechbrain`, con `--only-binary` para cada paquete pesado: 167 paquetes. Con
  `--only-binary :all:` no resuelve solo por `docopt`, que ya trae Pipecat y no tiene
  rueda.
- Las licencias: `uv pip install --no-deps` de `insightface` 2.1, `mediapipe` 1.1.1,
  `speechbrain` 1.1.2, `opencv-python-headless` 5.0.0.93 y `onnxruntime` 1.24.4 en un
  entorno aparte, y sus metadatos con `importlib.metadata`. InsightFace no declara
  licencia en ellos: la dice su descripción, en la sección «License».
- Lo que trae InsightFace 2.1: `top_level.txt` y `entry_points.txt` de su paquete, y
  `insightface/__init__.py:10`, donde apaga la telemetría de ONNX Runtime.
- Las 28 pruebas de máquina se ven fallar por la razón esperada: 28 `xfail` estrictos,
  cada uno con su pieza; ruff y mypy pasan sobre sus cuerpos.
- Los dobles: `tests/acceptance/test_dobles_del_conductor_0_4.py`, 11 en verde. Veinte
  mutaciones del conductor: caen diecinueve a la primera; la que vivía, no mirar el
  «-wal» de la base, pidió una comprobación más en esa prueba, y con ella cae.
- La comprobación de la tabla: `tests/acceptance/test_robot_0_4_trazabilidad.py`, 2 en
  verde con el documento como está.
- Tras la ronda 1 de Codex (abajo): el lector de la cara, contra la cara de verdad, en
  1 700 imágenes con sus ocho gestos y con tres semillas, se aparta como mucho 0,03 en
  los ojos, la mirada y las cejas, y no confunde ni se inventa ningún gesto. Seis caras
  rotas a propósito, sin párpados, con la boca siempre cerrada, sin cejas, con la ceja sola
  quieta, sin respirar y con la pupila quieta: las pruebas de aceptación cazan las seis, y
  con la lectura de antes pasaban las seis. Quitando cada búsqueda nueva de lo guardado,
  su prueba falla. Los dobles, 14 en verde. La batería entera, en dos partes: 5 362 en
  verde, 12 omitidas y 19 xfail en `tests/automation`, `tests/engine` y lo tocado, y
  4 132 en verde, 3 omitidas y 21 xfail en lo demás, con una roja: la prueba de que la
  cara no se congela leyó una vez la pantalla aún sin pintar. Una captura vacía ya no es
  una cara, se salta; con eso, `tests/acceptance` entera, 190 en verde, 2 omitidas y 20
  xfail.
- Tras la ronda 2 de Codex (abajo): con el conductor de antes, una cara que nunca arranca
  su reloj pasa las dos pruebas de la vida en reposo y la de la boca; con el de ahora,
  las tres fallan. Una cara que en la pantalla nunca parpadea y pintada a la fuerza sí se
  lee sin parpadear. Nueve cambios a propósito, en la cara, en cómo la lee el conductor y
  en la búsqueda de imágenes: las pruebas cazan los nueve. Una imagen codificada de cuatro
  maneras, en una dirección, en hexadecimal, en el `repr` de sus bytes y en base64, se ve
  igual en la base y en el diario: 8 casos. Los dobles, 24 en verde. La batería entera:
  hasta `tests/integration`, 6 228 en verde, 15 omitidas y 20 xfail, en 22 min 14 s, y una
  roja, la medida de rendimiento de construir el contexto, con el ordenador ocupado en otra
  cosa a la vez; sola, en verde. Y `tests/integration` y `tests/unit` enteras, otra vez y
  sin nada más: 3 274 en verde, 1 omitida y 1 xfail, en 7 min 12 s.

## Consecuencias

- La batería lleva 28 pruebas `xfail` estrictas de la 0.4 hasta que entre cada pieza.
- Las pruebas fijan nombres que todavía no existen en el código: los del conductor, los
  de la ventana y los de las herramientas. Si una pieza necesita cambiar una prueba, el
  cambio se dice en su PR, y nunca para aflojarla.
- El propietario tiene por delante, cuando entren sus piezas, el día uno de los ojos y
  las cuatro evaluaciones de la 0.4, además de las que quedan de la 0.2 y la 0.3.
- La pieza D deja un solo OpenCV y apaga la telemetría de ONNX Runtime; la E decide el
  cifrado y dónde vive su llave, en su ADR.

## Alternativas descartadas y por qué

- **Mapas del cuarto**: el plan los descarta, Sirius no se mueve.
- **Reconocer sin permiso**: el plan lo prohíbe; quien no lo da es «sin identificar».
- **Guardar fotos para reconocer mejor**: el vídeo no sale nunca y no se guardan
  imágenes (§2 y §6 del plan).

## La lección

- familia: `prueba-que-no-puede-ver-lo-que-vigila`
- sin esto se repetiría: una huella de mentira con una marca en sus bytes la pierde en cuanto la pieza la pasa a números, y la prueba de «cifradas» pasaría con la huella guardada en claro. Volvió en la ronda 1 de Codex de tres maneras: la cara se leía de lo que decía que pintó, y un fotograma o una huella en base64 no se veían en la base. La raíz es la misma: el conductor miraba lo que la pieza dice, o una sola forma de lo guardado, y no lo que se ve. Ahora la cara se lee de los píxeles, y lo guardado se busca en todas sus formas que se deshacen sin llave, en la base igual que en el diario
- lo hace cumplir: `tests/acceptance/test_dobles_del_conductor_0_4.py`

Y volvió en la ronda 2, dos veces más, porque el arreglo de la ronda 1 seguía siendo caso
a caso: una imagen codificada en el diario no se buscaba, y la cara se pintaba a la
fuerza para leerla. Ahora la cara se lee por un solo camino, lo que Qt pinta sola en la
pantalla, y cada cosa guardada se busca con una sola función, la misma en la base y en el
diario.

## Revisión externa

Alcance, escrito antes de la primera petición, el de la PR #702, que trae las piezas A, B
y C: que cada cláusula del §6 tenga su prueba o su evaluación, y que ninguna pueda pasar
con una pieza que haga trampa; que los dobles hagan algo y lo apunten ellos; que la
búsqueda de imágenes y huellas guardadas vea lo que dejaría un error; que la cara no pueda
congelarse por la charla, y que se lea de la ventana de verdad; que ninguna etiqueta llegue
a la ventana, a la voz o a la base, se parta como se parta; y que la tabla, el inventario y
el conductor digan lo mismo.

- **Ronda 1, sobre `80f309f2`**: cinco hallazgos, los cinco ciertos.
  - **P1, la cara se leía de lo que decía que pintó.** El conductor llamaba a `grab`,
    tiraba la imagen y leía `last_drawn`, la pose que la cara apuntaba de sí misma: una
    cara que pintara otra cosa, o nada, pasaba PA-R04-01 a PA-R04-05. Ahora se lee de los
    píxeles (`tests/acceptance/lector_de_la_cara.py`), por los colores con que se pinta
    (`PALETTE`) y las proporciones del dibujo; las veces que se pinta las cuenta Qt, con un
    filtro de eventos puesto desde fuera; y lo que pinta sola mientras el modelo tarda se
    lee de la pantalla, sin pedirle que se pinte. Para leerla con precisión, en las
    pruebas la cara mide 480 píxeles de alto.
  - **P1, un fotograma guardado en base64 en la base no se veía**: la marca de los
    fotogramas se buscaba en la base tal cual, y en el diario en todas sus formas. Ahora,
    en la base, en las mismas que en el diario.
  - **P1, una huella guardada en base64 tampoco**: ahora se busca también en hexadecimal y
    en base64, la normal y la de las direcciones, desde los tres sitios en que puede caer
    en un grupo de tres bytes, y sin blancos, por si va partida en líneas.
  - **P2, un bloque de código abierto con cuatro comillas lo cerraban tres**: ahora lo
    cierran cuatro o más, como en Markdown (pieza C, ADR-261).
  - **P2, las filas de reconocer y de la edad no decían con qué**: PA-R04-10 nombra
    InsightFace y ECAPA, y PA-R04-13, InsightFace; sus pruebas miran, cuando entren sus
    piezas, que sean los que monta Sirius sin dobles.

  Los tres P1 son de la familia de la lección de arriba, y el arreglo va a su raíz, no a
  cada caso.
- **Ronda 2, sobre `8cc180d7`**: dos hallazgos, los dos ciertos, y se le preguntó además
  si el enfoque estaba mal.
  - **P1, una imagen codificada en el diario no se veía**: en la base se buscaban la marca
    de los fotogramas y las cabeceras de imagen; en el diario, solo la marca. Una imagen
    comprimida y escrita en base64 en el diario no lleva la marca, y pasaba PA-R04-09.
    La ronda 1 decía que lo guardado se buscaba igual en la base que en el diario, y para
    las imágenes no era verdad.
  - **P2, la cara se pintaba a la fuerza para leerla**: el conductor la leía con `grab`,
    que pasa por su `paintEvent` en el acto, así que una cara congelada en reposo o al
    hablar se habría leído viva en PA-R04-02 y PA-R04-04. Se comprobó: con el conductor
    de entonces y una cara que nunca arranca su reloj, las tres pruebas pasan.

  **Dos rondas seguidas con la misma familia**, `prueba-que-no-puede-ver-lo-que-vigila`:
  se dejó de parchear y se buscó la raíz (ADR-001). La raíz es que cada sitio por donde el
  conductor mira se hizo caso a caso: la cara se leía de una forma en una prueba y de otra
  en las demás, y lo guardado se buscaba con una lista en la base y con otra en el diario.
  Cada ronda encontraba otra combinación. Se decidió seguir, arreglando eso:
  - **La cara se lee por un solo camino**, el de la pantalla: el conductor deja correr Qt
    hasta que la pinta sola y lee lo que quedó, en todas las pruebas. Nunca le pide que
    se pinte; si en un segundo no se ha pintado sola, está congelada y la prueba falla.
    Se mira fotograma a fotograma, cada 33 ms del reloj de las pruebas, como los pinta, en
    vez de cada 20 ms: ningún umbral cambia, y cada prueba de un minuto tarda un minuto.
  - **Lo guardado se busca con una sola función por cosa**, la misma en cada sitio:
    `lo_que_delata_una_imagen` mira la marca en todas sus formas y lo que lleva dentro una
    imagen codificada, en binario, en hexadecimal, como texto y en base64, en la base y en
    el diario igual. Las huellas ya se buscaban así.
- **Ronda 3, sobre `b6e8d384`**: limpia, «Didn't find any major issues». Se le preguntó
  otra vez si el enfoque estaba mal, y no puso nada en contra. La #702 se fusionó
  aplastada en `c9469442`.
