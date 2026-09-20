# ADR-195 — «Podar» significa archivar: en este repositorio no se borra nada

- Estado: APROBADO
- Fecha: 2026-09-14
- Aprobación: el propietario. **La regla es suya y ya la dio**; este ADR solo la
  escribe donde se pueda volver a leer.

## La regla, con sus palabras

En la conversación de la madrugada del 14-09-2026, al hablar de podar la mina de
lecciones, el propietario corrigió el término:

> «Supongo que a podar te refieres a archivar, no se elimina nada, ¿eh?
> Acuérdate de eso.»

Eso es todo. Y hasta este ADR **no estaba escrito en ninguna parte**: la palabra
«podar» no aparecía ni una vez en `docs/` ni en `AGENTS.md`.

Peor: había prosa que lo contradecía. El punto 3 de
`docs/investigaciones/2026-09-11-flujos-reales-de-agentes-comparados-con-el-motor.md`
—la lista que el propietario pidió para debatir— proponía revisar las lecciones
cada pocas semanas para «mantenerlas, actualizarlas, consolidarlas, sustituirlas
o **borrarlas**». Esa última palabra era exactamente la que él corrigió, y es la
que habría guiado a quien implementara la poda. Se corrige en este mismo cambio
—ahora dice «archivarlas», citando de dónde viene la corrección—, porque la
prosa que una decisión deja falsa se arregla con ella, no después.

Incidencia: #630.

## Por qué esto es un ADR y no una nota

La conversación que lo produjo empezó exactamente por este defecto. El
propietario recordaba haber decidido algo sobre un componente —Curator— y no
podía encontrarlo:

> «Ahora, ¿cómo encuentro yo eso? Otra vez a investigar, otra vez a mirar, otra
> vez a hablar.»

(Ese caso concreto queda resuelto en el mismo cambio: Curator **sí** estaba en el
árbol —en la investigación de la orden #483, del 31-08-2026, como una de once
filas con todo en `ND`—, así que no había ninguna decisión perdida: no se decidió
nada porque no había dato. La sección «Dónde está lo de Curator» del documento de
aprendizaje lo deja escrito para no volver a buscarlo.)

Una regla que solo vive en una conversación cuesta dos veces: la primera cuando
hay que volver a preguntarla, y la segunda —más cara— cuando alguien actúa en
contra de ella sin saber que existía. Y el daño de **esta** regla en concreto no
se puede deshacer: lo borrado no vuelve.

## Qué significa archivar, sitio por sitio

Para que la regla se pueda cumplir hay que decir qué es «archivar» en cada cosa
que se podría querer podar:

| Cosa | Archivar es | Nunca |
|---|---|---|
| Incidencia | cerrarla con la razón escrita en un comentario | borrarla |
| Pull request | cerrarla diciendo qué la sustituye o por qué muere | borrarla |
| Rama | dejarla empujada tal cual | `git push --delete`, ni borrarla en la web |
| Entrada del registro de defectos | `estado: cerrado` con su `cerrado_por` | quitar la entrada |
| Lección de la mina | moverla a un fichero de archivo fechado, citada desde donde estaba | quitarla del árbol |
| Documento | dejarlo donde está y marcar en él qué lo deroga | borrar el fichero |
| Diario del motor | nada: es `append-only` por ADR-026 | reescribirlo |

La forma común es la misma en todas las filas: **lo que deja de estar vigente
deja de estar en medio, pero no deja de estar.** Un archivo no es un cementerio;
es el único sitio donde consta por qué algo se decidió y por qué se dejó de
hacer.

## Lo que ya lo cumplía sin decirlo

No se inventa una política: se nombra la que el repositorio ya practicaba a
trozos.

- **ADR-047** — un defecto encontrado se registra con incidencia y no se borra
  nunca.
- **ADR-026** — el diario del motor es `append-only`.
- **ADR-080** — el commit de cierre de un defecto empieza por `H-N: `, y por eso
  renumerar una entrada vieja rompería el vínculo: otra forma de decir que lo
  viejo no se toca.
- La práctica de esta misma noche: las PR #617, #620, #621 y #631 murieron de
  obsolescencia —cuatro en doce horas— y **se cerraron con la razón escrita, con
  sus ramas intactas**.
- Y la práctica de siempre, medida: `git ls-remote --heads origin` devuelve
  **429 ramas**, incluidas las cinco de esta noche que ya están fusionadas.
  Aquí no se ha borrado una rama nunca; lo que faltaba era decir que es una
  regla y no una casualidad.

Lo que faltaba era la regla general y su nombre.

## La guarda, y hasta dónde llega

Solo una parte de esto se puede hacer cumplir con una prueba, y se hace:

`CONTADOR_MAXIMO = 43` es el último identificador que eligió el contador viejo,
muerto desde ADR-192. Ese bloque —`H-1` a `H-43`— está hoy completo y sin
huecos, y **no puede crecer nunca más**, así que se puede exigir que ninguna de
esas entradas desaparezca. Es la misma forma que `PRIMER_ADR_CON_LECCION` y
`PRIMER_ADR_CON_ID_DERIVADO`: una constante de frontera, no una lista a mano.

**Lo que ninguna prueba puede hacer cumplir, y se dice en vez de fingirlo:** que
nadie borre una incidencia, una rama o una PR. Eso no lo puede ver este
repositorio desde dentro; lo sostiene la regla escrita, las denegaciones de
`git push --delete` y `git branch -D` en `.claude/settings.json`, y el hecho de
que las escrituras externas del motor pasen por gestos declarados.

## Consecuencias

- Podar la mina —que era lo que se estaba hablando cuando salió la regla— pasa a
  significar mover a un archivo fechado, no eliminar.
- Un repaso de «limpieza» nunca es una razón suficiente para quitar algo del
  árbol. Si estorba, se archiva.
- El coste es espacio en disco y un índice más largo. Se acepta a propósito: es
  mucho más barato que volver a investigar una decisión que ya se tomó.

## La lección

- familia: `regla-del-propietario-que-solo-vive-en-una-conversacion`
- sin esto se repetiría: una regla dada de viva voz —«no se elimina nada»— que no
  queda escrita en ningún sitio del árbol, así que cuando hace falta hay que
  volver a preguntarla o, peor, se actúa en contra sin saber que existía; con
  esta regla en concreto el daño no se puede deshacer, porque lo borrado no
  vuelve.
- lo hace cumplir: `tests/automation/test_registro_de_defectos.py`

Esa prueba cubre **solo el registro de defectos**, que es la única mitad
comprobable desde dentro. Para incidencias, ramas y PR no hay prueba posible
—el repositorio no puede ver lo que se borró en GitHub— y así queda dicho en
«La guarda, y hasta dónde llega», arriba.
