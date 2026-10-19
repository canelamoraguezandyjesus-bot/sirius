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
