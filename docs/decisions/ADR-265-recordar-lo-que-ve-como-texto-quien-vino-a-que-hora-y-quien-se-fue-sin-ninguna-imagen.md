# ADR-265 — Recordar lo que ve como texto: quién vino, a qué hora y quién se fue, sin ninguna imagen

- Estado: APROBADO
- Fecha: 2026-10-19
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Es la pieza G de la 0.4, la última, en
  el orden de ADR-259.

Este ADR es además la **nota de arranque** de la pieza G. Se escribe antes de su primera
línea de código. Sus pruebas las fijó ADR-259 en `docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md`,
PA-R04-14, antes de que la pieza existiera, y aquí no se afloja ninguna. Los tiempos con
que se da por hecho un cambio no los fijó: se fijan aquí, antes de medir nada.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** Con las piezas D y E, Sirius sabe a quién
   tiene delante en cada momento, pero lo olvida al instante: no sabe quién vino ni
   cuándo, y al cerrarlo no queda nada. El plan pide recordar lo que ve como texto, quién
   vino, a qué hora y qué cambió, nunca como imagen (§6, «Lo que se hace», 8); PA-R04-14 lee
   «qué cambió» como quién llega, quién se va y quiénes hay. El arreglo va en cuatro sitios:
   - **La vista** saca, de quién es cada cara en cada fotograma, quién llega y quién se va.
     Alguien llega cuando se le ve 3 s seguidos, y se va cuando lleva 20 s sin vérsele; un
     parpadeo de la cámara, o alguien que se gira un momento, no es un cambio. La hora es
     la del primer fotograma con él, o sin él. Lo primero que ve al abrir la cámara no es
     que haya llegado nadie: lo apunta como quien ya estaba.
   - **Lo apuntado** va a la base como texto: cuándo, qué cambió y quién, su nombre si dio
     permiso para que le reconozca y, si no, nadie: «alguien sin identificar», sin nada que
     lo distinga. De dos desconocidos se sabe cuántos hay, no cuál es cuál.
   - **La charla** le pone al modelo «# Lo que has visto», una línea por cambio de las
     últimas 24 horas, con su hora: «A las 18:02 vino Marta.».
   - **No se guarda más de lo que se dice**: lo apuntado hace más de 24 horas se borra, y
     quien quita su permiso deja de tener nombre en lo apuntado, en el mismo paso que se
     borran sus huellas: pasa a ser alguien sin identificar.

   **¿Puede el sitio del arreglo observar el fallo?** Sí: la vista es la que ve las caras y
   sabe quién es cada una; la charla lee lo apuntado de la base, también tras cerrar y
   volver a abrir.
2. **Qué NO garantiza.**
   - Que distinga a dos desconocidos: sin permiso no hay ni nombre ni huella; se cuenta
     cuántos hay.
   - Que acierte quién es: lo dice la pieza E.
   - Un cambio que dure menos de lo que se espera para darlo por hecho: quien pasa 2 s por
     delante no ha venido, y quien sale 10 s no se ha ido.
   - Qué lleva puesto la gente o cómo está la habitación: las herramientas del plan no lo
     ven (`PRUEBAS_0.4_DEL_ROBOT.md`).
   - Que el modelo use bien lo que lee.
3. **Criterio de parada**, decidido antes de escribir el código:
   - Las dos pruebas de PA-R04-14 en verde, y la batería entera.
   - Si para saber que vino alguien hiciera falta guardar una imagen, una huella o
     cualquier cosa de un desconocido que lo distinga, se para.
   - Dos rondas seguidas de Codex con la misma familia: se deja de parchear y se busca la
     raíz.
4. **Qué lo haría imposible.**
   - **Que quede una imagen o algo que distinga a un desconocido**: lo apuntado es una
     hora, qué cambió y un nombre o nada; no hay sitio para otra cosa. PA-R04-09 y
     PA-R04-14 lo buscan.
   - **Que quede el nombre de quien retiró su permiso**: quitarlo lo quita también de lo
     apuntado, y lo borrado se pone a ceros en el fichero, como sus huellas.
   - **Lo que no se puede hacer imposible**: que el modelo lea mal una hora o se invente a
     alguien.
