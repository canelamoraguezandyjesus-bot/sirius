# ADR-160 — Formalizar la separación entre Sirius y su motor: Sirius es el compañero, el motor ejecuta y las IAs externas son el lugar de trabajo

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Contexto: la dirección que el propietario expresó al encargar
  `docs/evolution/PROPUESTA_SEPARACION_SIRIUS_MOTOR.md` y al revisarla
- Entrada en vigor: la fusión de la Pull Request que introduce este ADR, por el
  propietario, conforme al procedimiento establecido en este repositorio. **La
  aprobación documental no ejecuta ninguna retirada técnica** (ver ADR-161)
- Relación con las decisiones canónicas vigentes, en una línea que se repite
  igual en todos los documentos de esta enmienda: **EV-015 precisa EV-001,
  EV-016 sustituye EV-002 y acota EV-003, y EV-004 se mantiene vigente sin
  enmienda.**
- Relacionadas: `docs/evolution/DECISIONS.md` (donde viven EV-001 a EV-004 y las
  nuevas EV-015 a EV-019); `docs/evolution/RECTOR.md` §2, §4, §5 y §9.3, que
  este ADR enmienda por la vía documental; ADR-161 (la retirada de los dos
  carriles); ADR-083 y la decisión D6 (memoria del motor separada de la del
  producto); ADR-001 (disciplina de evidencia)

> **Este ADR es también la nota de arranque de la rama
> `claude/sirius-motor-separation-proposal-svoy0a` para el trabajo de
> formalización.** El apartado siguiente se publicó en su propio commit, antes
> de tocar ningún otro documento, para que la fecha del `git log` lo sostenga.

## Nota de arranque (publicada ANTES del primer cambio documental)

**1. ¿Dónde vive el fallo y dónde va el arreglo?** El fallo es una
contradicción: los documentos aprobados dicen que Sirius es el interlocutor
obligatorio, el integrador y el dueño de una única memoria canónica
(`docs/evolution/RECTOR.md:22`, `:25`, `:58`, `:63`, `:69`;
`docs/evolution/DECISIONS.md` EV-002 y EV-004), y la dirección del propietario
dice otra cosa. El arreglo **no puede vivir editando esas líneas**: están
citadas por número desde documentos ya publicados —`RECTOR.md:136` a `:290` se
cita desde la Arquitectura Técnica 0.2, el Plan de Pruebas 0.2, la Definición de
Producto 0.2, `docs/evolution/STATUS.md` y ADR-102—, así que desplazarlas
falsearía citas ajenas. El arreglo vive, por tanto, **al final de cada documento
y en decisiones nuevas que sustituyen a las viejas**, que es el patrón que este
repositorio ya usa (ADR-082 enmienda a ADR-019 sin editarlo; `STATUS.md` añade
al final por esta misma razón, y lo dice).

¿Puede el sitio del arreglo observar el fallo que arregla? Sí, y de forma
mecánica: una foto de **todas** las líneas citadas del repositorio, tomada antes
de editar, permite comprobar después que ninguna se ha movido. Sin esa foto, la
comprobación sería «he tenido cuidado», que no es una comprobación.

**2. ¿Qué NO va a garantizar esto?**

- **No ejecuta la retirada.** Ningún workflow se desactiva, ningún código se
  toca, ninguna clase deja de despacharse. Lo que se registra es la decisión;
  la ejecución queda pendiente y así se declara (ADR-161).
- **No elige herramienta de memoria**, ni fija dónde vive la memoria común, ni
  la ordena respecto a Sirius 0.2.
- **No cambia prioridades ni alcance de ninguna versión**, ni renumera nada.
- **No arregla otros defectos documentales** del repositorio, aunque estén
  identificados en la propuesta (`README.md:16`, `docs/robotics/head/STATUS.md`,
  el «Próximo paso» de `docs/evolution/STATUS.md`): quedan fuera por orden
  expresa del propietario.
- **No demuestra independencia de ejecución** entre producto y motor: lo
  comprobado sigue siendo separación de paquetes, como acota la propuesta §5.2.

**3. Criterio de parada (decidido ANTES de editar nada).**

- **(a)** Si una edición desplaza **una sola** de las líneas citadas de la foto,
  se revierte esa edición y se rehace por el final del documento. No se
  «reajusta la cita ajena»: la cita ajena no es mía.
- **(b)** Si formalizar exige tocar código, workflows o permisos, se para y se
  deja escrito como pendiente. La orden lo prohíbe expresamente.
- **(c)** Si aparece una contradicción entre lo que el documento diría y lo que
  el árbol hace hoy —por ejemplo, declarar retirada una clase que el
  despachador sigue despachando—, **manda el árbol**: el documento describe la
  decisión y declara la ejecución pendiente, nunca al revés.
- **(d)** Si una decisión aprobada tuviera que cambiar sin que la dirección del
  propietario la cubra, se para y se le pregunta.

**4. ¿Qué haría imposible el error más probable, en vez de improbable?** El
error más probable es el (a): mover una línea citada. Lo haría imposible una
comprobación mecánica, no la atención: se fotografían las 3.469 líneas citadas
desde `docs/` y la raíz —100 ficheros— antes de tocar nada, y se comprueba
después que su contenido es idéntico. Está en «Comprobación que la sostiene».
Lo que **no** se puede hacer imposible: que exista una cita por línea escrita
fuera de `docs/` y de la raíz, o en una rama sin fusionar, que la foto no vea.
Se declara como residuo.

## Contexto y problema

El propietario expresó una dirección al encargar y revisar
`docs/evolution/PROPUESTA_SEPARACION_SIRIUS_MOTOR.md`. Esa propuesta la recoge
en su apartado 7.1 y comprueba, documento por documento, qué contradice hoy cada
punto. Lo que queda es el acto formal: **la dirección no cambia por sí sola los
documentos aprobados**, y mientras `RECTOR.md` §4 y EV-002 sigan escritos como
están, cualquier trabajo posterior es formalmente una desviación.

Este ADR registra la parte de esa formalización que define **quién responde de
qué**. La retirada de los dos carriles dedicados va en ADR-161, porque tiene
consecuencias y ejecución propias.

## Opciones consideradas

1. **Editar `RECTOR.md` §2/§4/§5 y EV-001 a EV-004 en su sitio.**
   Descartada por el criterio (a): esas líneas están citadas por número desde
   cinco documentos y un ADR. Editarlas en su sitio falsearía citas publicadas
   que no son de este trabajo.
2. **Publicar una versión nueva del Rector (v1.1) reescrita entera.** Descartada
   por dos razones: rehace un documento aprobado que la dirección solo modifica
   en tres puntos, y traslada el mismo problema de citas a todos los documentos
   que apuntan a la v1.0.
3. **Decisiones nuevas que sustituyen a las viejas, más una enmienda al final de
   cada documento afectado.** Elegida. Es el patrón vigente del repositorio para
   exactamente este caso, y conserva el histórico legible: EV-002 sigue donde
   estaba, diciendo lo que dijo, con la marca de qué la sustituye.

## Decisión

Se formaliza el reparto siguiente. Cada punto queda además como decisión
canónica en `docs/evolution/DECISIONS.md` (EV-015 a EV-019) y como enmienda al
final de `docs/evolution/RECTOR.md` (§19).

1. **Sirius es el compañero personal, de ingeniería y del robot.** Conserva
   identidad, memoria propia, conversación, voz, cámaras y percepción, ayuda de
   ingeniería y electrónica, manejo del ordenador y de los dispositivos
   autorizados. **Precisa EV-001**: no la sustituye ni cambia su fondo —Sirius
   sigue siendo el sistema personal responsable ante el usuario—, sino que dice
   de qué es compañero.
2. **El trabajo habitual se realiza directamente con las IAs externas.** El
   propietario conversa, encarga y decide desde ChatGPT, Claude o Codex sin que
   Sirius intermedie. **Sustituye a EV-002 y acota EV-003**: Sirius deja de ser
   el interlocutor obligatorio y la síntesis final deja de ser obligatoria; abrir
   una sesión especializada sigue siendo una capacidad suya, no el camino por el
   que llega el trabajo.
3. **El motor conserva ejecución, documentación, comprobaciones, revisión,
   corrección, recuperación y diario operativo**, y no adquiere ninguna
   responsabilidad nueva. Sigue sin conversar, sin decidir producto o
   arquitectura y sin fusionar (contrato §8).
4. **Tres memorias con dueño distinto, sin obligar a tres bases de datos**: la
   memoria propia de Sirius (del producto, en el equipo del propietario), el
   estado y diario operativo del motor (ADR-082, ADR-083, decisión D6) y el
   **conocimiento común del trabajo y los proyectos**, que es categoría nueva.
   Regla: cada dato tiene un dueño, y quien no es dueño **cita en vez de
   copiar**; una copia va marcada como espejo no autoritativo, como ya hace el
   motor (contrato §11.1).
5. **La memoria común es conocimiento del trabajo y de los proyectos, no la
   memoria canónica de Sirius.** Las IAs la mantienen y debe estar disponible con
   el ordenador del propietario apagado. Esta distinción es la que permite que
   **EV-004 siga vigente sin enmienda**: lo que EV-004 protege —que ningún agente
   posea ni escriba la memoria canónica de Sirius— sigue intacto, porque la
   memoria común no es esa memoria.
6. **Sirius conserva ayuda de ingeniería, herramientas, avisos y la posibilidad
   de consultar especialistas.** La delegación de una consulta de ingeniería del
   propietario en un especialista se conserva expresamente como capacidad de
   Sirius, distinta de un encargo del motor en tres rasgos: nace de una
   conversación y no de un WorkItem, no produce PR ni pasa por el ciclo de
   revisión-corrección, y su resultado vuelve a la conversación y no al diario
   operativo.

**Lo que esta decisión NO hace**, dicho para que no se deduzca al revés:

- No autoriza implementar nada. La regla de activación del Rector
  (`docs/evolution/RECTOR.md:282-290`) sigue entera: ninguna etapa post-0.1
  empieza sin Definición de Producto aprobada, pruebas de aceptación
  reproducibles y arquitectura técnica aprobada.
- No cambia prioridades, ni el orden del roadmap, ni el alcance o la numeración
  de ninguna versión.
- No elige herramienta, ubicación ni formato para la memoria común, ni fija su
  relación con Sirius 0.2, que sigue por estudiar.
- No toca el merge humano, la convergencia, ni ninguna prohibición del contrato
  operativo §9.

## Comprobación que la sostiene

**(1) Ninguna línea citada ajena se ha movido.** Antes de editar se
fotografiaron **3.469 líneas** citadas por número desde `docs/**/*.md` y los
`.md` de la raíz, repartidas en **100 ficheros**. Tras las ediciones se comparó
línea a línea:

```
foto previa   -> líneas citadas registradas: 3469 / ficheros: 100
verificación  -> citas desplazadas: 3
```

**Tres, no cero, y conviene decirlo tal cual.** Las tres son
`docs/implementation/bloques_del_motor.yml:186`, `:249` y `:257`, desplazadas a
`:202`, `:273` y `:281` al añadir la marca de retirada a los bloques S2, B1 y C4.
Las tres las cita **un solo documento, y es de este mismo trabajo**:
`docs/evolution/PROPUESTA_SEPARACION_SIRIUS_MOTOR.md`. Se corrigieron en el
mismo commit que las desplazó. El criterio (a) prohíbe mover una cita **ajena**;
una cita propia se arregla en el acto, y se enseña que se arregló:

```
grep -rn 'bloques_del_motor.yml:20[0-9]|:27[0-9]|:28[0-9]' docs/
  cita bloques_del_motor.yml:202  <- PROPUESTA_SEPARACION_SIRIUS_MOTOR.md
  cita bloques_del_motor.yml:273  <- PROPUESTA_SEPARACION_SIRIUS_MOTOR.md
  cita bloques_del_motor.yml:281  <- PROPUESTA_SEPARACION_SIRIUS_MOTOR.md
sed -n '202p;273p;281p' docs/implementation/bloques_del_motor.yml
  - id: C4
  - id: D3
  - id: D4
```

**Y la comprobación se ha visto FALLAR, que es lo que la hace valer.** Insertando
una sola línea intrusa al principio de `docs/evolution/RECTOR.md`, la
verificación pasa de 3 citas desplazadas a **81**: las 78 de ese fichero más las
tres conocidas. Con la mutación revertida vuelve a 3. Una guarda que solo se ha
visto pasar no prueba nada.

**(2) El árbol no ha cambiado.** `git status` no muestra ningún fichero
modificado fuera de `docs/`, y ninguno bajo `src/`, `tests/`, `scripts/` o
`.github/`.

**(3) Las guardas documentales del repositorio pasan.** `sirius_check_docs.py`
sobre los ficheros tocados, y las baterías
`tests/automation/test_citas_de_los_adr.py`,
`tests/automation/test_registro_de_decisiones.py`,
`tests/automation/test_registro_de_bloques.py`,
`tests/automation/test_sirius_check_docs.py` y
`tests/unit/test_documentation_single_source.py`.

Las cifras exactas de cada una están en el mensaje del commit que las produce,
no aquí, porque este ADR se escribe antes de que existan y no se reescribe para
fingir que las tenía delante.

## Consecuencias

- `docs/evolution/DECISIONS.md` gana EV-015 a EV-019 y marca en su sitio la
  relación con las anteriores, con la línea unificada de la cabecera: **EV-015
  precisa EV-001, EV-016 sustituye EV-002 y acota EV-003, y EV-004 se mantiene
  vigente sin enmienda.** Ninguna decisión anterior pierde su texto.
- `docs/evolution/RECTOR.md` gana un §19 de enmienda al final, que dice qué
  apartados quedan sustituidos y por qué no se editan en su sitio.
- `docs/evolution/STATUS.md` registra el cambio.
- **`docs/canonical/STATUS.md` NO se toca en esta enmienda, y es deliberado.**
  `.claude/settings.json` deniega editar `docs/canonical/**`, así que anotar allí
  estas decisiones es un acto reservado al propietario. Queda como paso suyo,
  posterior a la fusión, con el mismo formato que ya usa para EV-001 a EV-014.
- La memoria común entra en el vocabulario del proyecto **sin etapa asignada**:
  no está en el roadmap del Rector y este ADR no se la da.
- Queda una obligación explícita para quien redefina la etapa 0.4: conservar la
  delegación especializada del punto 6, que de otro modo se borraría por omisión
  al decir «esto ya lo hace el motor».
- **Entrada en vigor, unificada en todos los documentos tocados:** la fusión de
  la Pull Request que los introduce, por el propietario, conforme al
  procedimiento establecido. Ese acto es **aprobación documental**; la
  **retirada técnica** de los dos carriles es posterior a él, y ADR-161 la
  mantiene separada.

## Alternativas descartadas y por qué

- **Enmendar EV-004 para dejar escribir a las IAs.** Descartada porque no hace
  falta: la memoria común no es la memoria canónica de Sirius, y así declarado,
  EV-004 protege lo mismo que protegía. Enmendar una decisión aprobada que no
  estorba es coste sin beneficio.
- **Declarar la memoria común dentro de Sirius 0.2.** Descartada por el criterio
  (d) y por la propia propuesta: la relación entre ambas está por estudiar y
  falta la evaluación funcional de qué requisitos cubre ya cada pieza existente.
- **Dar por retirados los dos carriles en este mismo ADR.** Descartada: tienen
  ejecución, riesgo y reversibilidad propios, y mezclarlos ocultaría que uno está
  decidido y sin ejecutar. Van en ADR-161.
