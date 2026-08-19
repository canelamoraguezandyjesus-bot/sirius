# ADR-040 — Convertir una intención en encargo preguntando una cosa cada vez

- Estado: APROBADO
- Fecha: 2026-08-19
- Aprobación: petición explícita del propietario; fusión de la PR #204
- Contexto: método de trabajo del repositorio
- Relacionadas: ADR-001 (disciplina de evidencia), ADR-032 (numeración de ADR),
  ADR-037 (qué gestos son del propietario)

## Contexto y problema

El propietario lo dijo así, y no conviene suavizarlo:

> *«al final tú tomas las decisiones en cierto modo»*

Es exacto. Él firma `fusiona`, pero firma sobre un juicio ajeno: quien decide
que algo está listo es la sesión. La noche del 18-08 lo dejó ver entero — se
escribieron tres ADR, se activó un bloque, se levantó una parada y se eligió la
dirección técnica de una corrección, todo con él aprobando conclusiones que no
había podido examinar.

La causa no es mala voluntad ni exceso de iniciativa: es que **él no puede
escribir especificaciones y por eso delega**. Lo dijo también: *«yo no sé muchas
veces ni lo que me dices»* y *«yo sé lo que quiero»*.

Ese es el problema real. Sabe **qué** quiere y no sabe **cómo** pedirlo en el
formato que la maquinaria consume.

## Criterio de parada (escrito ANTES de decidir)

**No procede, y decirlo importa más que fabricarlo.**

Un criterio de parada acota una investigación: fija qué resultado haría parar o
cambiar de rumbo antes de ver ninguno. Aquí no había nada que investigar. El
propietario trajo el método ya formulado —de una publicación que compartió— y
pidió implementarlo. La única aportación de la sesión fue adaptarlo a este
repositorio.

Tampoco hubo nota de arranque antes del primer commit, y el hook de parada lo
señaló con razón. Redactar ahora una que suene bien sería exactamente lo que
ADR-001 prohíbe: lo que ata no es tenerla, es haberla publicado antes.

## Opciones consideradas

1. **No formalizarlo.** Seguir como hasta ahora y confiar en preguntar cuando
   parezca oportuno.
2. **Un cuestionario.** Una lista fija de preguntas que él rellena de una vez.
3. **Interrogatorio con propuesta.** Una pregunta cada vez, con la mejor
   respuesta ya propuesta, y él solo corrige.

## Decisión

Se adopta la 3, documentada en `docs/implementation/METODO_INTERROGATORIO.md`.

**Regla única: el propietario decide QUÉ quiere; la sesión decide CÓMO se
hace.** Cada pregunta que se le haga sobre el cómo es un fallo de la sesión.

Tres piezas hacen el trabajo:

- **Una pregunta cada vez**, esperando respuesta. Un muro de veinte no es un
  interrogatorio: es un formulario, y se contesta a desgana.
- **La mejor respuesta, ya propuesta.** Él corrige en vez de redactar, que es
  justo lo que puede hacer y lo otro no.
- **Qué haría cambiar esa propuesta.** Sin esto el método se invierte: contesta
  «sí» a todo y el plan vuelve a ser de la sesión con su firma encima.

Y una frontera explícita sobre lo que **no** se le pregunta: nada que se pueda
leer en el repositorio, nada técnico, y nada cuya respuesta no cambie lo que se
construiría.

## Comprobación que la sostiene

**El diagnóstico está comprobado. El remedio NO, y esa asimetría hay que
decirla.**

Lo sostenido por evidencia es el problema, no la solución:

- Las decisiones de esa noche son públicas y verificables en las incidencias
  #193 y #202 y en los ADR 035-038: dirección técnica, activación, reanudación
  y criterios de parada, todos elegidos por la sesión.
- La formulación del propio propietario, citada arriba.

Lo que **no** está comprobado es que este método corrija nada. Es un documento
recién escrito, sin un solo uso. En un repositorio donde todo se ata con una
prueba, esto no la tiene y no puede tenerla todavía: su efecto solo se ve en
si él corrige más propuestas de las que acepta.

Por eso se deja escrito **cómo se sabrá que fracasó**, que es lo más parecido a
una comprobación que admite hoy:

1. Si acepta casi todas las propuestas sin corregir ninguna, el método no está
   devolviéndole el volante: está poniéndole una firma más elegante.
2. Si las preguntas empiezan a sonar a examen, se está preguntando de más.
3. Si alguna respuesta suya estaba en un fichero del repositorio, la sesión no
   leyó antes de preguntar.

Los tres están recogidos en §7 del método como sus modos de fracaso.

## Consecuencias

- Lo que él decide y lo que decide la sesión quedan **separados y nombrados** en
  cada plan, y por tanto son discutibles después.
- La sesión pierde la comodidad de decidirlo todo en silencio: cada propuesta
  tiene que declarar qué la haría cambiar.
- No sustituye a nada. El interrogatorio produce el encargo; la ejecución sigue
  bajo `disciplina-evidencia` y las decisiones bajo `adr`.

## Alternativas descartadas y por qué

**No formalizarlo.** Es el estado que produjo la queja. Confiar en preguntar
«cuando parezca oportuno» ya falló: la noche entera se decidió sin preguntar, y
sin mala intención.

**Un cuestionario de una vez.** Es lo que él no puede contestar, y por dos
motivos: exige tener el mapa completo en la cabeza antes de empezar, y llega sin
propuestas, así que le devuelve el trabajo de redactar en lugar de quitárselo.
Además invita a contestar en bloque y a desgana.

## Nota sobre el número de este ADR

El guion `siguiente_adr.py` propuso **039**, y habría sido un duplicado: el
bloque A4 ya usa ese número en la rama `feature/work-engine-a4-...`, sin
fusionar, así que el árbol local no lo ve. Es exactamente el modo de fallo que
la skill `adr` documenta —*«no coordina ramas paralelas»*— y el mismo que creó
los dos ADR-016 que conviven en el registro.

Se comprobó contra los ficheros de la PR #203 antes de escribir, y se tomó el
**040**. La comprobación que de verdad cierra el agujero sigue siendo
`tests/automation/test_registro_de_decisiones.py`, que falla si dos ADR
comparten número; el guion solo quita fricción.
