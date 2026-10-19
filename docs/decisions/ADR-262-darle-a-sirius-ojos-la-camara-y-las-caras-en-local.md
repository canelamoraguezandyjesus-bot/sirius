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
