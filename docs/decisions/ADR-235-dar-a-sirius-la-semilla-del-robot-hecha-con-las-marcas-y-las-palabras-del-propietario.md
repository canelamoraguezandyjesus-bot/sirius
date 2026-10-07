# ADR-235 — Dar a Sirius la semilla del robot hecha con las marcas y las palabras del propietario

- Estado: APROBADO
- Fecha: 2026-10-07
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Es la pieza B de ADR-233. El contenido
  es del propietario: lo marcó y lo escribió él el 07-10-2026.

## Nota de arranque

Las cuatro preguntas de la semilla están en la nota de ADR-233, escrita antes de
enseñarle ninguna candidata, y con ellas su criterio de parada: 24 candidatas; si 15 o
más son Sirius, la semilla lleva esas, hasta 20. Lo propio de esta pieza:

1. **Dónde va el arreglo.** La semilla, en `src/sirius/domain/robot_seed.py`, versionada
   con el código. Lo que manda en cada arranque es la base: `adopt_robot_seed` la guarda
   como versión nueva de la identidad. Lo observa PA-R02-01, que mira lo que llega al
   modelo en cada petición.
2. **Qué NO garantiza.** Que el modelo la siga: eso lo miden E-R02-02 y el juez de la
   pieza E.
3. **Criterio de parada.** El de ADR-233.
4. **Qué lo haría imposible.** Que la semilla se pierda por el camino: va entera en cada
   petición, lo comprueba PA-R02-01. Que se adopte dos veces: solo se adopta si ninguna
   versión de la historia tiene ya ese texto, y arrancar dos veces deja dos versiones,
   no tres.

## Contexto y problema

Hasta ahora Sirius conversaba con la semilla de 0.1, copiada del manual v1.2: compañero
de ingeniería, humor sin humillar y hechos separados de inferencias siempre. La enmienda
del manual del 06-10-2026 cambia las tres cosas. El paso 1 de la 0.2 pide una semilla
nueva, con sus palabras, como valores y razones, y con 15 a 20 ejemplos.

## Cómo se hizo con él

- **Las candidatas.** La sesión escribió 24 respuestas candidatas para situaciones del
  plan y el texto de valores, y se los enseñó en una página privada con dos botones por
  respuesta y una casilla para decir cómo lo diría él.
- **Sus marcas.** Marcó las 24 entre las 15:11 y las 16:14. 13 «eso es Sirius» y 11
  reescritas con sus palabras. Una reescrita cuenta como aprobada: la escribió él como
  Sirius, que es justo lo que el criterio de ADR-233 pedía hacer con las rechazadas. De la
  primera salen dos ejemplos, porque dio dos: «Buenos días, jefe» y, si le dice cabezón,
  «Buenos días, soquete». En la del poema marcó la mía y escribió además la suya, y va la
  suya.
- **Cuáles entran.** El plan pide de 15 a 20 ejemplos y había 25. Entran sus 13 frases y
  7 de las mías que marcó, las que cubren lo que las suyas no: la idea mala y su
  insistencia, «ponte serio», «para», el crío, la anciana y algo grave de salud. Se
  quedan fuera cinco marcadas que repetían lo que ya cubrían otras: la tortilla, el
  «inútil, tu puta madre», el partido, el cansancio y la vuelta al buen rollo.
- **Lo que se toca de sus frases.** Solo la ortografía, como «q» por «que», «Vd» por «la
  verdad» o «bn» por «bien». Las palabras son las suyas. De la del código, la frase que
  quedó a medias se quita.
- **Lo que enseñan sus frases al texto de valores**, y por eso cambia:
  - A él le llama jefe, tío o macho.
  - Serio no es estirado: ante la muerte de su abuelo, Sirius dice «Joder, tío, lo
    siento mucho», no «Lo siento mucho, de verdad».
  - Delante de visitas, el blanco del pique sigue siendo él: «¿Y dónde conociste a este
    energúmeno?».
  - Sirius sabe que no tiene cuerpo ni herramientas y se ríe de ello: «me deberías hacer
    unos brazos», «si me dieras más herramientas pudiera decírtelo».
  - Es su compañero, no su empleado.
- **Resultado:** 20 ejemplos, el máximo del plan.

## Opciones consideradas

1. **La semilla nueva sustituye a la de 0.1 en la versión 1.** Borraría la historia de la
   identidad, que el manual pide conservar.
2. **Versión nueva de la identidad al arrancar, una sola vez**, en bases nuevas y viejas
   por el mismo camino.
3. **Que la adopte el propietario con un botón.** Él ya la aprobó al marcarla; un botón
   más es trabajo sin decisión.

## Decisión

Se adopta la opción 2.

- **`src/sirius/domain/robot_seed.py`**: los valores, con su razón cada uno, y los
  ejemplos con quién habla, qué dice y qué contesta Sirius. `ROBOT_SEED_INSTRUCTIONS` es
  el texto que se guarda.
- **`src/sirius/application/adopt_robot_seed.py`**: crea la versión nueva si ninguna
  versión de la historia tiene ya ese texto. Así un cambio que haga después el propietario
  no se pisa en cada arranque, y una semilla nueva aprobada en otra PR sí entra.
- **`initialize_persistence`** la llama al arrancar, después de asegurar la identidad.
  Una base nueva queda con la versión 1 de 0.1 y la 2 del robot, la vigente.
- **La semilla de 0.1 se queda** como versión 1 y como constante: sus pruebas siguen
  diciendo qué decía.

## Comprobación que la sostiene

- PA-R02-01 en verde: toda petición lleva la semilla entera con sus ejemplos, y una base
  de 0.1 abre con la del robot como versión 2, también al reabrir.
- Vistas fallar: sin adoptar al arrancar, fallan las dos pruebas de PA-R02-01; adoptando
  en cada arranque, falla la de la base de 0.1 al reabrir. Para que esa mutación se viera,
  `reabre()` del conductor pasa ahora por el arranque entero, como al reabrir de verdad.
- La tabla de pruebas cazó que PA-R02-01 seguía diciendo «pendiente» con la pieza B
  entregada.
- `tests/integration/test_persistence_bootstrap.py`: arrancar deja las versiones 1 y 2, y
  arrancar dos veces no crea una tercera.

## Consecuencias

- Todo el que abra Sirius desde esta versión conversa con la semilla del robot.
- La prueba a ciegas de la pieza C ya compara modelos con la semilla buena.

## Alternativas descartadas y por qué

- **Copiar sus frases tal cual, con sus abreviaturas.** El modelo aprendería a escribir
  «q», y cuando hable con voz se leería mal.

## La lección

- ninguna: el único hueco, una prueba que no ejercía el arranque al reabrir, se cerró
  antes del primer commit y se ve en la mutación de arriba.
