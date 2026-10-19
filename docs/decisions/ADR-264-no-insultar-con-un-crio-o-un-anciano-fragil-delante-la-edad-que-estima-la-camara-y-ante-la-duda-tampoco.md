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
