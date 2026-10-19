# ADR-261 — Hacer los gestos de una lista cerrada que el modelo escribe entre corchetes

- Estado: APROBADO
- Fecha: 2026-10-19
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Es la pieza C de la 0.4, en el orden
  de ADR-259.

Este ADR es además la **nota de arranque** de la pieza C. Se escribe antes de probar
nada: solo había un primer borrador del filtro, sin ejecutar. Los umbrales de la pieza los
fijó ADR-259 en
`docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md`, PA-R04-05, antes de que la pieza existiera, y
aquí no se añade ni se afloja ninguno.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** El modelo no sabe que tiene cara, y si
   escribiera un gesto entre corchetes, la etiqueta saldría en la ventana, la diría la
   voz y quedaría guardada en la charla. El plan pide gestos de una lista cerrada, que el
   modelo escribe como `[ceja_arriba]` y la cara hace, y que lo que no está en la lista
   se ignore (§6, «Lo que se hace», 7). El arreglo va en cinco sitios:
   - **La lista y qué es una etiqueta**, en el dominio, sin Qt:
     `src/sirius/domain/gestures.py`, con el filtro que las quita del texto mientras
     llega a trozos.
   - **La charla**: `SendMessageService` pasa lo que escribe el modelo por el filtro
     antes de enseñarlo, decirlo o guardarlo, y da cada gesto de la lista, en su sitio
     entre los trozos, a quien lo pida (`on_gesture`). Las instrucciones llevan la lista.
   - **La voz**: cada gesto va con la frase en que se escribió, y la cara lo hace cuando
     esa frase empieza a sonar. El oído se lo da a la cara sin coger su cerrojo, como el
     volumen.
   - **Lo escrito en la ventana**, sin voz: la cara lo hace cuando llega el texto.
   - **La cara**: `FaceLife` hace los gestos, uno detrás de otro, y `FaceWidget` los
     dibuja.

   **¿Puede el sitio del arreglo observar el fallo?** Sí: todo lo que escribe el modelo
   de la charla pasa por `SendMessageService` antes de llegar a la ventana, a la voz o a
   la base, y ahí está el filtro.
2. **Qué NO garantiza.**
   - Que el modelo use bien los gestos, ni que los use: un modelo pequeño puede no
     escribir ninguno o escribirlos de más. Si la cara le gusta lo dice E-R04-05.
   - Que el gesto caiga en la palabra exacta: va con la frase, cuando empieza a sonar.
   - Que la cabeza los haga: es la 0.6, con la misma lista.
   - Que lo que escribe entre corchetes y no es una etiqueta desaparezca: un enlace, una
     cifra entre corchetes o lo que va dentro de un código se quedan como están, a
     propósito.
3. **Criterio de parada**, decidido antes de escribir el código:
   - Las cuatro pruebas de PA-R04-05 en verde, y la batería entera.
   - Una respuesta sin etiquetas no cambia ni un byte, y una respuesta a trozos da lo
     mismo que entera, se corte por donde se corte: si no se puede tener las dos cosas,
     se para y se dice.
   - Dos rondas seguidas de Codex con la misma familia: se deja de parchear y se busca la
     raíz.
4. **Qué lo haría imposible.** Que una etiqueta llegue a la ventana, a la voz o a la base
   desde la charla: el filtro está en el único sitio por el que pasa lo que escribe el
   modelo de la charla, antes de todo lo demás. Lo que no se hace imposible es que el
   modelo escriba entre corchetes algo que no es una etiqueta: eso se ve, como cualquier
   texto.
