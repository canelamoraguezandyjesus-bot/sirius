# ADR-260 — Darle a Sirius su cara en la ventana, dibujada, viva y sin congelarse

- Estado: APROBADO
- Fecha: 2026-10-18
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Es la pieza B de la 0.4, en el orden
  de ADR-259.

Este ADR es además la **nota de arranque** de la pieza B. Se escribe tras su primer
borrador, que ya pasaba sus cinco pruebas, y antes de la batería y de cualquier revisión.
Lo que la ata no lo decide esta nota: los umbrales de la pieza los fijó ADR-259 en
`docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md`, antes de que la pieza existiera, y aquí no se
añade ni se afloja ninguno.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** La ventana de Sirius no tiene cara: la
   charla es una lista de mensajes. El plan pide su cara dentro de la app, con ojos,
   párpados, cejas y boca dibujados, viva en reposo, sin congelarse aunque el modelo
   tarde y con la boca al volumen de su voz (§6, «Lo que se hace», 4 a 6, y «Terminado
   cuando», 4). El arreglo va en tres sitios:
   - **Cómo está la cara en cada instante**, en el dominio: `FaceLife`, en
     `src/sirius/domain/face.py`, sin Qt y con el reloj que le den.
   - **Quién la dibuja**: `FaceWidget`, en `src/sirius/presentation/face_widget.py`, con
     `QPainter`, encima de la charla, y un temporizador que la redibuja unas 30 veces por
     segundo en el hilo de la ventana.
   - **Lo fuerte que suena su voz**: el altavoz lo dice (`Speaker.level`), bloque a
     bloque y a la hora en que se oye, y el oído se lo da a la cara sin coger su cerrojo
     (`LocalListening.speaking_level`). La cara vive con el reloj de la charla
     (`LocalListening.clock`), el de las pruebas en las pruebas.

   **¿Puede el sitio del arreglo observar el fallo?** Sí: la cara cuenta sus dibujos, y
   una prueba los cuenta mientras el modelo tarda 3 s de verdad en contestar.
2. **Qué NO garantiza.**
   - Que la cara guste ni que parezca viva: lo dice E-R04-05, en su ordenador.
   - Que no se congele si el hilo de la ventana se para por otra cosa: la charla y la voz
     van en sus hilos y la cara no espera a nadie, pero lo que haga la ventana en el suyo
     la para igual.
   - Que la boca vaya exactamente con el sonido: va con el bloque que el altavoz dice que
     se oye, con la hora que da PortAudio. Cuánto se abre con su voz lo ajusta E-R04-05.
   - Mirar a quien habla, apartar la vista al pensar y los gestos: son las piezas D y C.
3. **Criterio de parada**, el de ADR-259 para esta pieza:
   - Las cinco pruebas de la pieza B en verde, PA-R04-01 a PA-R04-04, y la batería
     entera.
   - Si la vida en reposo no cabe en los umbrales de PRUEBAS_0.4 con una cara razonable,
     se para y se dice: los umbrales no se aflojan para que pase.
   - Dos rondas seguidas de Codex con la misma familia: se deja de parchear y se busca la
     raíz.
   - E-R04-05, del propietario: si ve la cara congelada o muerta, se cambia la vida o el
     dibujo, no la prueba.
4. **Qué lo haría imposible.** Que el modelo congele la cara: el modelo va en el hilo de
   la charla, y la cara no coge ningún cerrojo que la charla pueda tener; una prueba lo
   mira con el cerrojo cogido. Lo que no se puede hacer imposible: que otro trabajo en el
   hilo de la ventana la pare.

## Contexto y problema

La 0.4 empezó por sus pruebas de aceptación (ADR-259). La pieza B es la cara: la capa
base del busto de Disney que pide el plan, y lo primero de la 0.4 que el propietario
puede ver, sin cámara ni modelos nuevos.

## Opciones consideradas

1. **Imágenes o una animación grabada.** El plan pide la cara dibujada, y una animación
   no sigue al volumen ni a la mirada.
2. **Un motor de animación** (Live2D, Rive). Trae una dependencia y un formato nuevos para
   cuatro partes que `QPainter` dibuja.
3. **Dibujarla con `QPainter`**, con su vida en un modelo sin Qt y el volumen del
   altavoz. **Esta.**

## Decisión

Se adopta la opción 3.

- **La vida en reposo**, en `FaceLife`: cada parpadeo llega entre 2 y 6 s después del
  anterior, al azar, y dura un cuarto de segundo, 70 ms en cerrarse, 50 cerrado y 130 en
  abrirse; la mirada salta cada 1,2 a 3,5 s a otro punto cerca del frente, a menos de
  0,18 en horizontal y de 0,12 en vertical, y llega en 60 ms; respira con una onda de
  4,4 s; y la boca alcanza el volumen en unas centésimas, con una constante de 40 ms.
  Tras más de un minuto sin mirarla, como al volver el ordenador de dormir, empieza de
  nuevo desde ese instante en vez de repasar cada parpadeo que no se vio.
- **El dibujo**, en `FaceWidget`: la cara, los ojos con su iris, su pupila y un brillo
  quieto, los párpados que bajan sin salirse del ojo, las cejas y la boca, que es una
  línea cerrada y una elipse abierta. Respirar la sube y la baja un poco. Se redibuja
  cada 33 ms y se para al cerrarse la ventana. Si no puede leer el volumen, sigue con la
  boca cerrada y lo apunta una vez en el diario: una cara parada por eso sería
  justo lo que no puede pasar.
- **El volumen**: el altavoz de verdad apunta, de cada bloque que da a PortAudio, la hora
  en que se oye, lo que dura y su media cuadrática sobre `LOUD_RMS`; `level` es la del
  bloque que se oye ahora. El oído lo lee sin cerrojo. Los dobles de las pruebas lo
  tienen: el altavoz de mentira suena con el `volumen` que pone la prueba mientras algo
  sigue en el aire.
- **El conductor** lee la cara de la ventana de verdad: la dibuja con `grab`, que pasa
  por su `paintEvent` en el acto, y lee lo último que dibujó con el instante del reloj
  con que lo dibujó. `repaint` no basta: con la plataforma de Qt de las pruebas no
  dibuja en el acto.

## Comprobación que la sostiene

- Las cinco pruebas de aceptación de la pieza B, en verde; las demás de la 0.4 siguen en
  `xfail` estricto con su pieza.
- La vida en reposo, simulada con 200 semillas con las mismas cuentas que las pruebas de
  aceptación: ninguna falla.
- Pruebas nuevas: 9 del modelo de la cara (`tests/unit/test_cara.py`), 4 del widget
  (`tests/gui/test_cara_en_la_ventana.py`), 3 del volumen del altavoz
  (`tests/unit/test_local_speaking_adapters.py`) y 1 de que la cara lee el volumen con
  el cerrojo del oído cogido (`tests/unit/test_local_listening.py`).
- Con la cara dentro, las pruebas de la ventana, de aceptación, unitarias y de
  integración: 4 046 en verde, 3 omitidas y 25 `xfail`, ninguna roja, en 12 min 49 s.
  Por el camino salieron tres altavoces de mentira de otras pruebas sin `level`, que la
  cara leía al dibujarse.

## Consecuencias

- La ventana tiene cara desde que se abre; sin oído, vive con el reloj de siempre y la
  boca cerrada.
- El puerto del altavoz gana `level`: todo altavoz lo dice, los dobles también.
- El propietario tiene E-R04-05 por delante.

## Alternativas descartadas y por qué

- **Imágenes o animaciones grabadas**: el plan pide la cara dibujada.
- **Live2D o Rive**: una dependencia y un formato nuevos para lo que `QPainter` hace.

## La lección

- ninguna: lo que salió al hacerla, que `repaint` no dibuja en el acto en las pruebas,
  falló a la vista y quedó escrito en el conductor.
