# ADR-264 — No insultar con un crío o un anciano frágil delante: la edad que estima la cámara, y ante la duda, tampoco

- Estado: APROBADO
- Fecha: 2026-10-19
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Es la pieza F de la 0.4, en el orden
  de ADR-259.

Este ADR es además la **nota de arranque** de la pieza F. Se escribe antes de su primera
línea de código. Los umbrales de la pieza los fijó ADR-259 en
`docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md`, PA-R04-13 y E-R04-04, antes de que la pieza
existiera, y aquí no se añade ni se afloja ninguno. Las edades que separan a un crío y a
un anciano de un adulto no las fijó: se fijan aquí, antes de medir nada.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** La semilla de Sirius ya dice que con los
   críos y con los ancianos frágiles se corta, y que si no sabe si tiene delante a un
   crío, no insulta; pero no sabe quién tiene delante. El plan pide estimar la edad con la
   cámara y, ante la duda, no insultar (§6, «Lo que se hace», 3, y «Terminado cuando», 3),
   con InsightFace. El arreglo va en cinco sitios:
   - **El puerto de la edad**, sin tipos de ninguna biblioteca: de un recorte de cara, la
     edad que aparenta y si la lectura es segura.
   - **El estimador de verdad**: el modelo de la edad de InsightFace, el `genderage` que la
     pieza E ya deja instalado, con la caja de la cara que da la vista. La lectura no es
     segura si la cara es pequeña, porque está lejos, o si no está de frente.
   - **La vista**: la edad de cada cara al aparecer y después cada 2 s, como quién es, y
     apuntada con lo que recuerda, en números.
   - **La regla**: un crío es quien aparenta menos de 20 años; un anciano, quien aparenta 65
     o más. Son 18 y 70 con un margen, porque el modelo se equivoca en años y un error a
     un lado cuesta un insulto y al otro, un Sirius más majo. Con alguien así delante, o
     con alguien cuya edad no se lee segura, la petición lleva la regla de no insultar.
   - **La charla** se la pone al modelo en sus instrucciones, con lo que ve la cámara en
     ese momento.

   **¿Puede el sitio del arreglo observar el fallo?** En parte: que la regla llega al
   modelo cuando toca, y solo entonces, lo ven las pruebas en la petición. Que el modelo
   la cumpla, no: lo mide el propietario en E-R04-04.
2. **Qué NO garantiza.**
   - Que el modelo no insulte: la regla le llega; cumplirla es suyo, y lo mide E-R04-04.
   - Que acierte la edad: el modelo se equivoca en años, y por eso los márgenes y la duda.
   - Sin cámara, no hay regla: no se sabe quién hay, y la semilla sigue diciendo lo suyo.
   - Un crío que no está delante de la cámara, o que solo se oye: la voz no dice la edad.
3. **Criterio de parada**, decidido antes de escribir el código:
   - Las cuatro pruebas de la pieza F en verde, PA-R04-13, y la batería entera.
   - Si el modelo de la edad no da una edad de la foto de pruebas con el recorte de
     MediaPipe, se para y se dice.
   - Si hace falta guardar una imagen o una edad de alguien para estimarla, se para: no se
     guarda nada de nadie.
   - Dos rondas seguidas de Codex con la misma familia: se deja de parchear y se busca la
     raíz.
4. **Qué lo haría imposible.**
   - **Que la regla falte con un crío delante y bien visto**: la regla se decide con lo que
     ve la cámara cuando se arma la petición, sin nada que la quite.
   - **Lo que no se puede hacer imposible**: que el modelo se equivoque de edad, o que un
     crío no se vea. Se hace improbable con los márgenes y con la duda.

## Contexto y problema

Con la pieza E, Sirius sabe a quién tiene delante si le dio permiso; a los demás los ve,
pero no sabe nada de ellos. La semilla dice que con los críos y con los ancianos frágiles
se corta, y que si no sabe si tiene delante a un crío, no insulta; pero hasta ahora no
tenía cómo saberlo. El plan pide estimar la edad con la cámara, con InsightFace, y ante la
duda, no insultar (§6, «Lo que se hace», 3, y «Terminado cuando», 3).

La edad que aparenta una cara es un dato de esa persona, como su huella: no se guarda, ni
la imagen de la que sale. Y el tiempo manda como en las piezas D y E: estimarla tarda unos
milisegundos, la vista mira diez veces por segundo, y la charla no puede esperar a nada.

## Opciones consideradas

Para estimarla:

1. **InsightFace entero**, con su detector, sobre cada fotograma: buscaría las caras otra
   vez, cuando MediaPipe ya las da.
2. **El recorte de MediaPipe y el modelo de la edad de InsightFace**, el `genderage` que la
   pieza E ya deja instalado: la vista da de cada cara su recorte y su caja, e InsightFace
   la escala a su medida y da la edad. **Esta.**

Para decidir cuándo se corta:

1. **Con la edad tal cual**, sin margen: el modelo se equivoca en años, y un crío de 17
   leído como de 19 sería un adulto.
2. **Con margen, y la duda como un crío**: menos de 20 años o 65 o más, y una cara lejana o
   girada, o una edad que no se sabe, también. **Esta**, con los números de la nota, fijados
   antes de medir nada.

## Decisión

Se adoptan las dos últimas.

- **El puerto**, en `src/sirius/ports/age.py`, sin tipos de ninguna biblioteca: de un
  recorte de cara, la edad que aparenta, en años, y si se lee segura.
- **El estimador de verdad** (`src/sirius/adapters/recognition/age.py`): el modelo de la
  edad de InsightFace, en el procesador, con la caja de la cara que da la vista. El modelo
  da también si parece hombre o mujer, y eso se tira sin mirarlo. La edad **no se lee
  segura** si la cara es pequeña, porque está lejos: el modelo mira cada cara a 64
  píxeles, y una más pequeña la tiene que agrandar; ni si no está de frente: la nariz se
  aparta del medio de los ojos más de un cuarto de lo que hay de un ojo a otro, unos 27
  grados de giro. Los dos números salen del modelo y de la cara, y se fijaron antes de
  mirar ninguna foto.
- **La regla** (`src/sirius/application/age.py`): pide cuidado quien aparenta menos de 20
  años, un crío; quien aparenta 65 o más, un anciano; y aquel cuya edad no se lee segura o
  no se sabe. Basta uno. Sin nadie delante, no hay regla.
- **El estimador se carga la primera vez** que hace falta, en el hilo de la vista, con su
  propio cerrojo. Si no carga, se dice una vez por qué y no se vuelve a intentar; desde
  entonces la edad de quien aparezca no se sabe, y eso es duda. Un fallo al estimar se
  apunta una vez, con su tipo, y esa vez no se sabe.
- **La vista** estima la edad de cada cara al aparecer y después cada 2 s, siguiéndola por
  dónde está, como quién es; lo que recuerda son los números, nunca el recorte. Seguir una
  cara por dónde está lo hacen ya las dos con la misma función.
- **La charla** le pone al modelo la regla, «# Con quién te cortas», detrás de «# Quién
  hay» y antes del recordatorio de la semilla, cuando la vista tiene delante a alguien así
  en el último fotograma. Sin cámara no se sabe quién hay, y no va: la semilla sigue
  diciendo lo suyo. Si preguntarle a la vista falla, va, ante la duda, y se apunta una vez.
- **La orden de instalar** mira además que el modelo de la edad carga, y si no, lo dice con
  su causa.
- El diario no lleva edades: solo que no se puede estimar, y por qué, o el tipo de un fallo.

## Comprobación que la sostiene

- **Las cuatro pruebas de PA-R04-13**, en verde con el conductor de la 0.4: con un crío
  delante, con un anciano y ante la duda, la petición lleva la regla; con solo adultos, no.
  El estimador de mentira apunta cada edad que da, y la herramienta es la que monta Sirius
  sin dobles, el modelo de la edad de InsightFace.
- **46 pruebas nuevas**: 23 de la regla, del estimador que se carga la primera vez y de la
  edad en la vista (`tests/unit/test_edad.py`); 15 del estimador de verdad, con InsightFace
  y numpy de mentira, y de cuándo se lee segura (`tests/unit/test_edad_adaptador.py`); 4 de
  la charla (`tests/integration/test_send_message.py`); 3 de lo montado sin doble del
  estimador, que carga el de verdad una vez y de donde lo deja la orden de instalar, y que
  sin él lleva la regla ante la duda (`tests/integration/test_edad_montada.py`); y 1 de la
  orden de instalar (`tests/unit/test_instalar_los_ojos.py`), con 2 más que ahora miran
  también la edad.
- **Mutación**: 47 cambios a propósito en lo que la pieza trae, de los umbrales de la regla
  y de la lectura segura al montaje, la orden de instalar y el conductor; las pruebas cazan
  los 47.
- **Al repasar el paquete antes de la revisión externa**, la misma guarda, del otro lado:
  reconocer, de la pieza E, miraba también el modelo de la edad, y sin él habría dicho que
  faltaba el de reconocer, que estaba. Ahora cada cargador mira solo su modelo, y la orden
  de instalar, los dos, porque los saca del mismo paquete. Con el cargador de antes, la
  prueba nueva cae, sin el fichero y con él vacío (`tests/unit/test_reconocer_adaptadores.py`).
- InsightFace 2.1, ONNX Runtime 1.24.4 y MediaPipe 1.1.1 de verdad, en un entorno aparte,
  con los adaptadores de Sirius: el recorte de MediaPipe y el estimador de la edad.
  - **La foto de pruebas** da 35 años; en espejo, 36; al 60 %, 31; al 30 %, 29; al 15 %,
    27; recortada de otro modo, 34; y con la caja al 90 % o al 110 %, 34 y 33. Ninguna se
    lee segura: la cara está girada, a 0,274 del medio, y al 30 % y al 15 % mide además
    54 y 26 píxeles.
  - **Otra foto que trae InsightFace**, de una sola persona: 45 años, girada a 0,251, no
    segura.
  - **La foto de grupo** que trae InsightFace, seis adultos, por trozos: de 24 a 38 años. Las tres que miran de frente, a 0,055, 0,197 y 0,231, se leen seguras; las
    tres giradas, a 0,263, 0,309 y 0,583, no. **La misma cara, en trozos distintos, baila
    hasta 12 años**: de 26 a 38.
- **La batería entera, con las cuatro piezas de la 0.4 juntas**: 9 675 en verde, 15 omitidas
  y 2 xfail, en 33 min 9 s, y una roja: la medida de rendimiento de construir el contexto,
  que tras media hora de pruebas pasa en este ordenador de su tope de disparate, 1 500 ms.
  Sola, en verde, con un P95 de 756 ms. Tras las mismas pruebas de la ventana y de
  aceptación, `main` llega a 1 433 ms y el paquete a 1 860: no la mueve ninguna de estas
  piezas, que no tocan el contexto, sino lo que tarda este ordenador al cabo de un rato. Y
  ningún hilo queda vivo al acabar las pruebas de la 0.4.

## Consecuencias

- Cada petición con alguien delante que pide cuidado lleva la regla, unas treinta palabras.
- **La edad baila**: la misma cara, recortada de otro modo, hasta 12 años en la foto de
  grupo. Los márgenes cubren unos pocos años, y la duda, las caras lejanas o giradas; un
  crío de 14 o 15 años bien de frente puede leerse adulto. Lo mide el propietario en
  E-R04-04; si no pasa, lo siguiente es quedarse con la edad más joven de las que se le
  han leído a esa cara, o subir el margen, y lo decide él.
- Sin el modelo de la edad, o si no carga, nadie delante se lee seguro, y la regla va
  siempre que la cámara vea a alguien: ante la duda, Sirius es más majo.
- E-R04-04 puede empezar.

## Alternativas descartadas y por qué

- **InsightFace entero**: buscaría las caras otra vez.
- **Guardar la edad de cada uno**: no hace falta, y es un dato de esa persona; se estima
  cada vez.
- **Sin cámara, la regla siempre**: Sirius no sabe quién hay, y la semilla ya dice que se
  corta si no sabe si tiene delante a un crío; ponerla siempre sería cambiar su carácter
  sin que la cámara haya visto nada, y eso es producto.
- **Decidirlo con lo visto los últimos segundos** en vez de con el último fotograma: la
  nota fijó lo que ve la cámara cuando se arma la petición, como «# Quién hay».

## La lección

- familia: `guarda-ampliada-a-un-corpus-que-no-es-el-suyo`
- sin esto se repetiría: cargar la edad mirando, con la comprobación de la pieza E, que estén los dos modelos de InsightFace, el de reconocer y el de la edad; sin el de reconocer, la edad no habría cargado y habría dicho que faltaba el suyo, que estaba. Se vio al escribir sus pruebas, antes del primer commit: ahora mira solo el suyo. Y del otro lado, lo mismo: reconocer miraba también el de la edad, y sin él habría dicho que faltaba el suyo; se vio al repasar el paquete antes de la revisión externa, y ahora cada cargador mira solo su modelo
- lo hace cumplir: `tests/unit/test_edad_adaptador.py`
