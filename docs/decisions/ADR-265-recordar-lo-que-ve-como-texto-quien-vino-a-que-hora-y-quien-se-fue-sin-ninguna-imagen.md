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

## Contexto y problema

Con las piezas D y E, Sirius sabe a quién tiene delante en cada fotograma: «# Quién hay»
se lo dice al modelo en cada petición. Pero lo de antes se pierde: si le preguntan quién
ha venido esta tarde, no lo sabe, y al cerrarlo no queda nada. El plan pide recordar lo
que ve como texto, quién vino, a qué hora y qué cambió, y nunca como imagen (§6, «Lo que
se hace», 8); PA-R04-14 lo concreta en quién llega, quién se va y quiénes hay, también
tras cerrar y volver a abrir, y de un desconocido, que vino alguien sin identificar, sin
nada que lo reconozca.

Lo que se recuerda de alguien que dio permiso es un dato suyo: cuándo estuvo delante. Si
retira su permiso, su nombre no puede quedarse ahí. Y la cámara parpadea, la gente se gira
y MediaPipe pierde una cara un momento: tomar cada fotograma al pie de la letra llenaría lo
apuntado de llegadas y salidas que no han pasado.

## Opciones consideradas

Para saber qué cambió:

1. **Cada fotograma tal cual**: un parpadeo de la cámara sería una salida y una llegada.
2. **Dar un cambio por hecho cuando dura**: llega quien se ve 3 s seguidos, y se va quien
   lleva 20 s sin vérsele. **Esta.** Irse pide más que llegar porque perder una cara un
   momento es más común que verla sin estar.

Para guardarlo:

1. **Como frases, tal cual se le dicen al modelo**: quitar un nombre sería reescribir
   texto, y cambiar cómo se dice obligaría a migrar lo guardado.
2. **Cuándo, qué cambió y quién**, y las frases se escriben al leerlo. **Esta.**

## Decisión

Se adoptan las dos últimas.

- **El puerto**, en `src/sirius/ports/sight_log.py`: un cambio es cuándo, en UTC, qué
  cambió, si vino, se fue o ya estaba, y quién, su nombre o nadie.
- **Quien recuerda** (`src/sirius/application/sight_log.py`) recibe de la vista, en cada
  fotograma, quién es cada cara, su nombre si dio permiso o nadie, y cuenta cuántos de
  cada uno ve. Llega quien se ve 3 s seguidos, y se va quien lleva 20 s sin vérsele; la
  hora es la del primer fotograma con él, o sin él. De los desconocidos se cuenta cuántos
  hay: si se ven tres donde había uno, han llegado dos.
- **Lo primero que ve al abrir la cámara**, cuando lleva 3 s igual, se apunta como quien
  ya estaba, no como quien llega. Al perder la cámara, o al pararla, no se sabe quién se
  va: no se apunta nada, y al volver a ver se empieza de nuevo.
- **La base** gana la tabla `sight_log`, con su migración: cuándo, qué cambió y quién. Su
  conexión lleva `secure_delete`, como las huellas. Lo de hace más de 24 horas se borra
  cada vez que se apunta algo, cada vez que la charla lo lee y, con Sirius abierto, cada
  minuto desde el hilo de la vista, vea o no: no depende de que cambie nada delante ni de
  que la charla lo lea (ronda 1 de Codex sobre la PR #703).
- **La charla** le pone al modelo «# Lo que has visto», antes de «# Quién hay»: una línea
  por cambio de las últimas 24 horas, las 30 más nuevas, con su hora en la de este
  ordenador, «A las 18:02 vino Marta.», «A las 18:30 se fue Marta.», y lo de ayer, «Ayer,
  a las…». Quien no tiene nombre es «alguien sin identificar». Como lleva nombres, solo va
  a un modelo de este ordenador, como «# Quién hay».
- **Quitar el permiso** quita su nombre de lo apuntado, en el mismo paso que borra sus
  huellas, y de lo que se está mirando: pasa a ser alguien sin identificar, y no se apunta
  que se fue. Lo que la vista reconoció de él justo antes, si llega después, tampoco lleva
  su nombre: el permiso se mira al apuntar, con el cerrojo con el que se quita (ronda 3 de
  Codex sobre la PR #703). Y lo que se le dice al modelo solo lleva nombres de quien tiene
  permiso: si quitar un nombre falló, se lee como alguien sin identificar y se vuelve a
  quitar. Si falla al quitar el permiso, con sus huellas ya borradas, lo quita el repaso
  que la vista pide cada minuto, vea o no, también tras cerrar y volver a abrir: la ventana
  ya no le lista, y no hace falta repetirlo (ronda 5).
- **La hora** es la de este ordenador; la raíz de composición la recibe, y las pruebas
  ponen la suya.
- Olvidar (ADR-239) no la toca: no guarda nada dicho. Así queda en `FORGET_COVERAGE`.
- Un fallo al apuntar o al leer se dice una vez, con su tipo, sin nombres, y la vista y la
  charla siguen.

## Comprobación que la sostiene

- **Las dos pruebas de PA-R04-14**, en verde con el conductor de la 0.4: recuerda quién
  vino y a qué hora, también tras cerrar y volver a abrir Sirius, y quién se fue; de un
  desconocido, que vino alguien sin identificar, sin su nombre ni nada suyo.
- **35 pruebas nuevas**: 25 de quien recuerda, de la vista que se lo dice y de lo que se le
  dice al modelo, también con la hora de otro sitio (`tests/unit/test_lo_que_ve.py`); 4 de
  la base, con lo quitado y lo borrado fuera del fichero
  (`tests/integration/test_sqlite_sight_log.py`); 1 de lo montado sin dobles, que quita el
  nombre de la base en el acto al quitar el permiso
  (`tests/integration/test_lo_que_ve_montado.py`); 3 de la charla
  (`tests/integration/test_send_message.py`); y 2 de quitar el permiso
  (`tests/unit/test_reconocer.py`).
- **Mutación**: 41 cambios a propósito, de cuándo se da un cambio por hecho a la hora que
  se le dice, la base, el montaje y el conductor. A la primera, las pruebas cazaron 35; las
  seis que vivían pidieron seis pruebas más: un desconocido que se pierde un fotograma al
  llegar, dos que se pierden un momento, un fotograma que aún la nombraba tras quitar el
  permiso, el montaje de quitar el permiso, y la hora de este ordenador en lo que se dice y
  en lo que se guarda, con la de Tokio. Con ellas, las 41.
- Lo que le llega al modelo, con el conductor: tras ver al propietario, llegar a Marta a
  las 18:02 y a alguien más a las 18:10, irse Marta a las 18:30 y cerrar y volver a abrir
  Sirius:

  ```text
  # Lo que has visto
  Lo que has visto con la cámara en las últimas 24 horas, con su hora:
  A las 09:00, al abrir los ojos, estaba delante alguien sin identificar.
  A las 18:02 vino Marta.
  A las 18:10 vino alguien sin identificar.
  A las 18:30 se fue Marta.
  ```

- Lo mismo con `sight_log` en el conductor de la 0.3, que vigila que no se guarde audio en
  la base: la cuenta entre las tablas de Sirius.
- **Al repasar el paquete antes de la revisión externa**, dos cosas:
  - Lo de hace más de 24 horas solo se borraba al apuntar algo nuevo: sin cambios
    delante, se quedaba en la base. Ahora también al leerlo la charla, y un fallo al
    borrarlo se dice una vez y se lee igual. Tres cambios a propósito, y las pruebas cazan
    los tres (`tests/unit/test_lo_que_ve.py`). Aún faltaba la otra mitad, y la encontró la
    ronda 1 de Codex: lo cuenta ADR-262, en «Revisión externa».
  - «# Lo que has visto» iba también a un modelo de fuera, con nombres y horas. Ahora solo
    va a uno de este ordenador, y ni se lee si no; sin esa puerta, la prueba nueva cae
    (`tests/integration/test_send_message.py`).
- **La batería entera, con las cuatro piezas de la 0.4 juntas**: 9 675 en verde, 15 omitidas
  y 2 xfail, en 33 min 9 s, y una roja: la medida de rendimiento de construir el contexto,
  que tras media hora de pruebas pasa en este ordenador de su tope de disparate, 1 500 ms.
  Sola, en verde, con un P95 de 756 ms. Tras las mismas pruebas de la ventana y de
  aceptación, `main` llega a 1 433 ms y el paquete a 1 860: no la mueve ninguna de estas
  piezas, que no tocan el contexto, sino lo que tarda este ordenador al cabo de un rato. Y
  ningún hilo queda vivo al acabar las pruebas de la 0.4.

## Consecuencias

- Cada petición lleva lo que ha visto en el día, hasta 30 líneas, unas 250 palabras como
  mucho.
- Lo que recuerda de cada uno dura 24 horas; después se borra: con Sirius abierto, en un
  minuto como mucho. Con Sirius cerrado, nada lo borra hasta volver a abrirlo.
- Quien pasa menos de 3 s por delante no ha venido, y quien sale menos de 20 s no se ha
  ido.
- Quien da su permiso delante de la cámara deja de ser alguien sin identificar y pasa a
  tener nombre: se apunta que llegó él y, a los 20 s, que se fue alguien sin identificar.
  Es lo que vio la cámara, y no se arregla a mano.
- Con la pieza G, la 0.4 tiene todas sus piezas. Quedan las evaluaciones del propietario,
  E-R04-01 a E-R04-05.

## Alternativas descartadas y por qué

- **Guardar una foto de quien viene**: no se guardan imágenes (§2 del plan).
- **Distinguir a los desconocidos entre sí**: haría falta algo que los reconozca, y sin
  permiso no se guarda nada suyo.
- **Recordarlo para siempre**: lo que recuerda de alguien es suyo; 24 horas bastan para
  «¿quién ha venido?», y es lo único que se le dice al modelo.
- **Apuntar como llegadas lo primero que ve al abrir**: al volver a abrir Sirius diría que
  acaba de llegar quien llevaba una hora delante.

## La lección

- familia: `estado-en-el-que-se-entra-y-del-que-no-se-sale`
- sin esto se repetiría: quien recuerda lo que ve dejaba a alguien a medio llegar aunque en el fotograma siguiente no se le viera, porque solo miraba a quien se veía y a quien ya estaba; quien asomaba, se perdía un fotograma y volvía, habría llegado sin estar 3 s seguidos. Lo cazó su prueba antes del primer commit: ahora mira también a quien estaba llegando o yéndose
- lo hace cumplir: `tests/unit/test_lo_que_ve.py`
