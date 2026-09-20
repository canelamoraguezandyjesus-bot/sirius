# ADR-204 — El propietario decide producto, dinero y salud, y lo técnico lo resuelve la sesión

- Estado: APROBADO
- Fecha: 2026-09-20
- Aprobación: el propietario, el 20-09-2026. **La regla es suya y ya la dio**;
  este ADR solo la escribe donde se pueda volver a leer, que es exactamente la
  lección de ADR-195.

## Nota de arranque de esta tanda (escrita ANTES del primer commit)

Esta nota cubre los ADR-204, ADR-205 y ADR-206 y la ejecución de las diez
decisiones que la auditoría de la forma de trabajar puso delante del
propietario el 20-09-2026.

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en el reparto
   de trabajo: la sesión le devuelve al propietario decisiones que él no puede
   tomar, y él las devuelve sin contestar. El arreglo va en `AGENTS.md` y en
   estos ADR, que es donde toda IA del repositorio lo lee antes de responder.
   ¿Puede el sitio del arreglo observar el fallo? Sí: la sesión que va a
   preguntar lee `AGENTS.md` antes de responder, y ahí está escrito qué puede
   preguntar.
2. **Qué NO garantiza.** No garantiza que las decisiones que tome la sesión
   sean las que el propietario habría tomado. Garantiza que queden escritas,
   con su comprobación, y que él pueda revertirlas leyendo un ADR en vez de
   reconstruyendo una conversación.
3. **Criterio de parada**, decidido antes de escribir nada: si al ejecutar una
   de las diez decisiones aparece algo que toque dinero, salud, seguridad de
   datos o el alcance del producto, **se para y se pregunta**, aunque el
   propietario haya dicho «haz lo que creas». Y si dos decisiones seguidas
   resultan ser la misma familia de problema, se para y se busca la raíz en
   vez de seguir ejecutando la lista.
4. **Qué haría el fallo imposible.** Nada mecánico lo hace imposible: una
   pregunta es texto y ninguna guarda puede leer su intención. Lo más cerca
   que se llega es escribir la lista de lo preguntable donde se lee antes de
   responder, y dejar la cuenta a la vista: cada pregunta al propietario que
   no esté en la lista es un defecto de esta regla.

## Contexto y problema

El encargo que abrió la auditoría lo dijo el propietario el 15-09-2026:
quitarle la carga mental de «tener que pensar qué hacer en cada momento» en
cosas «que ya hemos hecho mil veces». La auditoría terminó, produjo diez
decisiones, y al ponérselas delante ocurrió esto: **siete de las diez
recibieron la misma respuesta**, que no era una decisión sino una devolución.
«No lo sé», «haz lo que tú creas», «yo qué sé, que no tengo ni idea de esto».

Y con ellas, la regla, con sus palabras el 20-09-2026:

> «si todo eso es técnico o de lógica, tu trabajo es resolver y hacer todo esto
> bien; te he dicho mil veces que yo no entiendo nada de esto […] que hagas tú
> todo. No me preguntes más para saber qué quiero yo, luego encárgate de que se
> cumpla. Eres el trabajador de aquí, el que tiene que hacer todo. Solo
> pregúntame cosas que realmente sean importantes: de dinero, salud, cambio de
> producto, no confundir con arreglo de producto.»

No es una regla nueva. Es la misma que el paso 3 de la auditoría ya había
encontrado en una conversación del 24-07 («no me des opciones, dime cuál es el
mejor») y que el paso 4 vio aplicada en ejecución el 10-08 («¿tú eres el que me
tiene que guiar? Y yo, el que responde y decide»). Llevaba catorce meses viva
en conversaciones y **no estaba escrita en ninguna parte del repositorio**.

## Criterio de parada (escrito ANTES de decidir)

Si al escribir la lista de lo preguntable resultara que la mayoría de las
preguntas reales de las transcripciones caen dentro de ella, la regla no
cambiaría nada y no merecería un ADR. Se comprueba contra las preguntas
observadas en el paso 4 antes de dar la decisión por buena.

## Decisión

**Se pregunta al propietario solo por tres cosas:**

1. **Dinero.** Gasto, suscripciones, compras, límites de uso, cualquier cosa
   que consuma su cuota o su dinero.
2. **Salud y seguridad.** Lo que afecte a su salud, a su descanso cuando él lo
   ha pedido, o a la seguridad de sus datos, sus credenciales y su máquina.
3. **Cambio de producto.** Qué es Sirius, qué hace y qué no hace: alcance,
   dirección, prioridad entre líneas de trabajo. **No es cambio de producto**
   arreglar lo que ya está decidido: corregir un defecto, elegir cómo se
   implementa algo aprobado, ordenar el repositorio o decidir entre dos formas
   técnicas de cumplir lo mismo. Esa distinción la puso él con estas palabras:
   «cambio de producto, no confundir con arreglo de producto».

**Todo lo demás lo decide la sesión**, lo ejecuta y lo deja escrito en un ADR
con su comprobación. Si la decisión resulta equivocada, él la revierte leyendo
el ADR; no hace falta que la haya tomado para poder deshacerla.

**Tres salvaguardas**, porque una autorización amplia sin límites escritos es
justo lo que este repositorio prohíbe en todo lo demás:

- **Lo irreversible sigue preguntándose**, aunque sea técnico: borrar una rama,
  reescribir historia, retirar una prueba, cualquier cosa que no se pueda
  deshacer leyendo un ADR. La regla de este repositorio es que no se borra nada
  (ADR-195); lo que no se puede archivar, se pregunta.
- **Una decisión tomada por la sesión nunca se declara del propietario.** El
  ADR dice quién la tomó. Un «según el propietario» que él no dijo es la
  familia de defecto que ADR-001 existe para impedir.
- **Si la sesión no puede decidir con lo que tiene**, no pregunta: investiga,
  lo deja escrito, y solo escala si después de investigar la decisión sigue
  dependiendo de algo que solo él sabe.

## Comprobación que la sostiene

Contra el criterio de parada: de las preguntas al propietario contadas en el
paso 4 de la auditoría —los nueve selectores de opciones de la sesión del ciclo
del 10-08, las tres de la sesión de B13 del 11 y el 14-08, y las diez
decisiones de la auditoría—, **ninguna era de dinero, de salud ni de cambio de
producto**. Todas eran técnicas o de orden. Siete de las diez decisiones las
devolvió sin contestar, y siete de los nueve selectores los rechazó tecleando
«continúa». La regla no es cosmética: cambia el destino de prácticamente todas
las preguntas que se le hicieron.

Lo que sí está en la lista y sí se le preguntó, y se seguiría preguntando: la
autorización para usar la clave real de OpenAI (B15, 17-08), que es dinero; y
la decisión de sacar la cabeza robótica del alcance (19-09), que es producto.

## Consecuencias

- `AGENTS.md` gana la sección «Qué se le pregunta al propietario y qué no», que
  toda IA lee antes de responder.
- Las diez decisiones de la auditoría dejan de estar bloqueadas: las tres que él
  contestó se ejecutan como dijo, y las siete que devolvió las resuelve la
  sesión, cada una con su ADR.
- El coste aceptado: habrá decisiones tomadas por la sesión que él habría tomado
  de otra manera. Se acepta a propósito, porque la alternativa medida es que no
  se tomen: la decisión de la incidencia #137 lleva desde el 10-08 sin cerrarse,
  y la de qué significa PROPUESTO afecta a 149 ADR desde hace meses.

## Alternativas descartadas y por qué

- **Seguir preguntando pero mejor, con menos texto y opciones más cortas.** Es
  lo que la sesión del ciclo intentó el 10-08 con el selector de opciones: él
  lo rechazó siete veces. El problema no es el formato de la pregunta; es que
  la respuesta exige un conocimiento que él dice no tener.
- **Que la sesión decida y no lo registre.** Sería más rápido y es justo lo que
  esta casa lleva un año arreglando: una decisión que solo vive en una
  conversación no está tomada, y a los tres meses nadie sabe por qué algo es
  como es.

## La lección

- familia: `regla-del-propietario-que-solo-vive-en-una-conversacion`
- sin esto se repetiría: la sesión seguiría devolviéndole decisiones técnicas
  que él no puede tomar, y el trabajo se quedaría parado esperando una
  respuesta que no va a llegar.
- lo hace cumplir: `tests/automation/test_reglas_de_agents.py`
