# ADR-232 — Hacer de Sirius solo el software del robot y revisar el roadmap: primero el cerebro, después la cabeza

- Estado: APROBADO
- Fecha: 2026-10-06
- Aprobación: el propietario, en la sesión del 06-10-2026, después de leer el plan
  entero: «Vale, perfecto. Ya lo he leído. Me parece totalmente razonable.» La fusión
  de esta PR lo deja escrito, con una ronda limpia de Codex sobre el head de contenido
  y Quality en verde (ADR-205).

Este ADR es además la **nota de arranque** de la rama `claude/giro-al-robot` (skill
`disciplina-evidencia`): las cuatro preguntas y el criterio de parada están escritos
antes del primer cambio de documentos y antes de cualquier revisión.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** El fallo: los documentos que una
   sesión lee primero describen un Sirius que el propietario ya no quiere. El Rector de
   evolución, sus decisiones EV, los dos STATUS, el manual de identidad, `AGENTS.md` y
   `README.md` hablan de un compañero de ingeniería, de un roadmap con habilidades sobre
   el PC, delegación, automatización digital y laboratorio, y prohíben escuchar y mirar
   siempre. El arreglo va en esos mismos documentos, que son los que se leen: una
   enmienda al final del Rector (§20) y de los STATUS, como hizo §19; decisiones EV
   nuevas; una enmienda escrita del manual; y el plan aprobado como documento propio.
   El sitio del arreglo puede observar el fallo: el fallo es lo que leen las sesiones y
   el arreglo está en lo que leen.
2. **Qué NO garantiza.** No implementa nada ni toca código. La semilla de identidad del
   código, `src/sirius/domain/identity.py`, sigue copiando el manual v1.2 hasta el paso 1
   de la nueva 0.2. No autoriza compras ni la cabeza física. No verifica las fuentes de
   las cuatro investigaciones: son fotos con fecha hechas en claude.ai. No borra nada: lo
   que sale del roadmap queda aparcado con su disparador. No impide que alguien lea §9
   del Rector sin llegar a §20.
3. **Criterio de parada**, fijado antes de ninguna revisión:
   - Se fusiona con la cadena de comprobación verde, una ronda de Codex limpia sobre el
     head de contenido y Quality en verde (ADR-205).
   - Si dos rondas seguidas de Codex encuentran defectos de la misma familia, por
     ejemplo dos documentos vigentes que se contradicen sin decirlo, se para y se revisa
     el enfoque, enmendar al final frente a reescribir. No se parchea una tercera vez.
   - Ningún cambio mueve líneas citadas por número desde otros documentos: lo que haga
     falta se añade al final, o se sustituye una línea por otra en su sitio.
   - Si una revisión encuentra que algo de esta PR contradice una decisión del
     propietario, se corrige a favor de sus palabras, que van citadas.
4. **Qué lo haría imposible.** Reescribir §9 del Rector en su sitio haría imposible leer
   el roadmap viejo como vigente, pero rompería las citas por número de la Arquitectura,
   el Plan de pruebas y la Definición de producto de 0.2, como ya explicó §19. No se
   hace. Lo que se hace: la primera línea de `AGENTS.md` y la de `README.md`, que lee
   todo el mundo, dicen qué es Sirius ahora y dónde está el plan.

**Corrección antes de la revisión, al escribir el resto.** `AGENTS.md` y `docs/canonical/`
están protegidos contra ediciones de las sesiones en `.claude/settings.json` desde el
13-07-2026, y una enmienda no justifica rodear esa protección por la consola. Así que:
`AGENTS.md` no se toca, la enmienda del manual vive en `docs/evolution/` y el puntero va
en `README.md` y en `MEMORIA.md`, que lista este ADR con los demás. `AGENTS.md` manda
leer `MEMORIA.md` entera antes de responder, así que el camino existe.

## Contexto y problema

El 05-10-2026 el propietario giró el proyecto. Sus palabras: «esa aplicación de Sirius
solo va a ser para el robot, solo software para el robot»; «nada de ayudarme en
ingeniería». Pidió no borrar el repositorio, «hemos construido un Sirius con una buena
base»; repasar el roadmap quitando lo que se pueda omitir, «si más adelante se quiere
añadir se añade»; definir un plan sencillo; y dejar aparcado y bien apuntado lo que
quede por decidir. Los pilares, en su orden: la personalidad, «esto es lo principal» y
«no me vale con una lista de frases»; aprender, del entorno, de él, de sí mismo y de
cómo se mueve; y recordar bien y rápido.

En la entrevista de ese día decidió seis cosas:

1. Primero el cerebro, sin cuerpo. La cabeza se le conecta cuando esté.
2. La personalidad, con sus palabras: gracioso ante todo, directo y a veces mal
   hablado, que le pueda insultar para picarle y discutir, único y reconocible al
   oírlo, y que con «ponte serio» le vacile y se ponga serio de verdad. Fuera
   «compañero de ingeniería» y fuera el «sin humillar» del manual.
3. Con otra gente, sin esos límites salvo con críos y con ancianos frágiles: «Él es la
   estrella».
4. Modelo local. El modelo se elige a ciegas por la gracia, entre dos o tres.
5. Se diseña Sirius, no la máquina. La identidad vive en datos y el modelo es un motor
   sustituible.
6. Escucha y mira siempre, en local, con indicador visible, botón para callarlo y sin
   guardar grabaciones.

Esta sesión no tiene buscador, así que las cuatro investigaciones las hizo claude.ai a
partir de cuatro encargos de la sesión: personalidad, aprendizaje, memoria y cómo se
organiza el cerebro de un robot.

El 06-10, la primera versión del plan solo daba objetivos y el propietario la rechazó
con razón: «eso no es un plan, eso es el objetivo». La segunda va versión por versión
con qué existe ya en Sirius, qué se hace, con qué herramienta, qué no se usa, cuándo
está terminado y cuánto cuesta. La leyó entera y la aprobó.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3. La decisión de producto es del propietario y ya
está tomada; lo que este criterio para es la forma de escribirla en el repositorio.

## Opciones consideradas

1. **Borrar y dejar solo el motor.** Lo propuso el propietario antes del 05-10 y lo
   retiró ese día.
2. **Reescribir en su sitio el Rector, el roadmap y los STATUS.** Limpio para quien lee,
   pero rompe las citas por número que la Arquitectura, el Plan de pruebas y la
   Definición de producto de 0.2 hacen a esos documentos.
3. **Enmendar al final, como §19, con decisiones EV nuevas, el plan aprobado como
   documento propio y punteros en la primera línea de lo que todo el mundo lee.**

## Decisión

La opción 3, en estos documentos:

| Pieza | Dónde | Qué hace |
|---|---|---|
| Enmienda §20 | `docs/evolution/RECTOR.md` | Dice qué cambia en §1, §2, §4, §6 a §8, §9, §10, §11, §12, §13, §17 y el manual, y qué no |
| EV-020 a EV-023 | `docs/evolution/DECISIONS.md` | Solo el robot; el roadmap del robot; escucha y mira siempre; modelo local e identidad en datos. EV-003, EV-006, EV-007, EV-008, EV-009, EV-010, EV-011, EV-015, EV-016 y EV-019 llevan escrito quién las sustituye, las acota o las aparca |
| El plan | `docs/evolution/PLAN_DEL_ROBOT.md` | Versión a versión: qué hay hecho, qué se hace, con qué, qué no se usa, cuándo termina y cuánto cuesta. Hace de definición de producto y de arquitectura de cada versión |
| La personalidad | `docs/evolution/ENMIENDA_MANUAL_IDENTIDAD_2026-10.md` | Las palabras del propietario y qué apartados del manual v1.2 cambian |
| El estado | `docs/evolution/STATUS.md`, `docs/evolution/README.md` y `docs/robotics/head/STATUS.md` | Lo vigente, lo autorizado y lo que no. HEAD-R1 pasa a ser el cuerpo de Sirius y sigue inactiva |
| Lo aparcado | `docs/ideas/registro_de_ideas.yml` y `docs/audits/decisiones-abiertas-del-propietario.md` | I-010 a I-017 con su disparador; D-1 a D-5 aparcadas con el banco de 47 casos. D-6 no es del banco y sigue abierta |
| Las investigaciones | las cuatro de `docs/investigaciones/` del 2026-10-05 | Enteras, con cabecera y caducidad, sin el nombre ni la región del propietario porque el repositorio es público |
| El puntero | `README.md`, líneas 3, 16 y 18, sustituidas en su sitio | Qué es Sirius ahora y dónde está el plan |

La regla de activación de la §17 sigue, con una forma más ligera para el robot: la
sección de cada versión en el plan hace de definición y de arquitectura, y sus pruebas de
aceptación se escriben antes de la primera línea de código. El propietario pidió un plan
sencillo, y tres documentos por versión, como los de 0.2 Memoria útil, no lo son.

## Comprobación que la sostiene

| Afirmación | Dónde se comprobó |
|---|---|
| La charla de Sirius va hoy por OpenAI | `src/sirius/composition_root.py:337-348` construye `OpenAIResponsesProvider` con el cliente de OpenAI |
| Ollama ya está conectado, solo para clasificar | `src/sirius/composition_root.py:526,554,570,623,633`: resuelve el modelo, `qwen3:4b-instruct` por defecto, y construye los cuatro clasificadores |
| La búsqueda es por palabras, sin vectores | `src/sirius/adapters/persistence/sqlite_knowledge_search_repository.py:99`, la consulta FTS5 `MATCH`; `src/sirius/domain/relevance.py:6`, «never embeddings» |
| La identidad está guardada por versiones | `src/sirius/domain/identity.py`, `IdentityVersion` con `personality_instructions`, y `src/sirius/adapters/persistence/sqlite_identity_repository.py:125`, `create_new_version` |
| La voz existe, con OpenAI y por turnos | `src/sirius/composition_root.py:386,434,435` construye la captura de Qt y los adaptadores de OpenAI; `src/sirius/application/studio_voice.py:9`, «síncrono a propósito» |
| El banco de 47 casos falla en el camino real: 4 de 47 y P95 438-780 ms | `docs/evolution/STATUS.md:306-307` |
| En otra variante, 7 de 47 | `docs/audits/decisiones-pendientes-de-la-linea-de-memoria.md:202` |
| El propietario no acepta ni 29 de 47 | `docs/evolution/STATUS.md:310-311` |
| Quedan dos pruebas `xfail(strict=True)` de M11: el suelo de 29 de 47 y el de RNF-003 | `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py:3550` y `tests/integration/test_local_performance.py:701` |
| Las líneas del Rector y de los STATUS están citadas por número | `docs/evolution/RECTOR.md:298-304` y `docs/canonical/STATUS.md:34-36` |
| `AGENTS.md` y `docs/canonical/` están protegidos contra ediciones de sesión | `.claude/settings.json`, reglas `Edit(./AGENTS.md)` y `Edit(./docs/canonical/**)` en `deny` |
| El nombre del propietario ya aparecía en 7 ficheros del repositorio; su región, en ninguno | `git grep` sobre `main` en `4ea76f35`, antes de copiar las investigaciones |
| Sirius usa Python 3.14 | `pyproject.toml:6` |

La cadena de comprobación sobre el árbol final está en el cuerpo de la PR.

**Revisión de Codex, ronda 1, sobre `53a4145c`:** cinco hallazgos, los cinco ciertos al
comprobarlos contra el árbol.

- Dos de la familia «decisión vigente que contradice el giro sin decirlo»: EV-016 seguía
  llamando a Sirius compañero de ingeniería, y EV-010 conservaba el control del ordenador.
  Se cerró la familia entera, no solo los dos: también EV-006 y EV-007, y las líneas viejas
  de «Vigente» de `docs/evolution/STATUS.md`.
- Uno de «afirmación que el árbol no sostiene»: D-6 no era del banco de 47 casos, es lo que
  cabe en `MEMORIA.md`. Sigue abierta; se aparcan D-1 a D-5.
- Uno de datos que salen del ordenador: entrenar en una GPU alquilada sacaría sus
  conversaciones, así que pide una decisión nueva del propietario (EV-023).
- Uno de citas que señalaban la declaración y no el uso. Se revisó la tabla entera.

**Revisión de Codex, ronda 2, sobre `7a0998e0`:** dos hallazgos, los dos ciertos y los dos
de la misma familia que la ronda 1. El propio revisor los marca como goteo: el estado
canónico sigue nombrando como única excepción la 0.2 vieja, y el conjunto de HEAD-R1 sigue
llamándola línea separada.

**Regla de las dos rondas.** Dos rondas seguidas con la misma familia: se dejó de parchear y
se buscó la raíz.

- **El patrón.** Cada conjunto de documentos con autoridad tiene varias frases vigentes, y
  enmendar unas deja otras contradiciendo el giro sin decirlo.
- **La raíz.** El barrido se hizo leyendo a trozos, no recorriendo entero cada conjunto de
  «Fuentes de verdad». Y dos de esas fuentes, `docs/canonical/STATUS.md` y `AGENTS.md`,
  están protegidas contra la sesión.
- **La decisión.** Seguir, con un barrido sistemático, y escalar al propietario lo que la
  sesión no puede tocar. El barrido recorrió cada conjunto entero:
  - `docs/evolution/`: el índice, al día; el Rector, los dos registros y la auditoría,
    con un puntero en su primera línea a la enmienda y la nota al final; las tres piezas
    de la 0.2 vieja, marcadas como sustituidas en su primera línea.
  - `docs/robotics/head/`: el índice, al día; el Rector y la auditoría, con nota al final;
    D-HEAD-14 sustituye a D-HEAD-04; las cuatro con puntero en su primera línea.
  - La raíz: `README.md`, al día; `REPOSITORY_STATUS.md` y
    `docs/implementation/PLAN.md` no dicen nada del giro, y los `ARTIFACTS.md` solo llevan
    huellas.
  - Ninguna primera línea tocada está citada por número. Se comprobó con `grep`.
  - Al pasar el comprobador de documentos por la Arquitectura 0.2, saltó una cita antigua
    de su línea 1598 a la rama `evidence/adr001-spikes`, con «rama» detrás de la ruta y no
    delante. Se corrigió en su sitio, sin mover líneas.

## Consecuencias

- Una sesión que abra el repositorio encuentra este ADR en `MEMORIA.md` y el puntero en
  `README.md`.
- La siguiente obra es la versión 0.2 del plan: primero sus pruebas de aceptación; después
  la semilla con el propietario, el conector local, la prueba a ciegas y los botones.
- Lo construido de 0.2 Memoria útil se queda. Se para el camino de M8 a M11 y la ola de M13
  en adelante.
- `AGENTS.md:3` sigue diciendo «Este repositorio implementa Sirius 0.1», y
  `docs/canonical/STATUS.md` no nombra la §20: los dos están protegidos. Lo vigente lo
  dicen la §20, el plan y `MEMORIA.md`.
- La semilla del código sigue siendo la del manual v1.2 hasta el paso 1 de 0.2.

## Alternativas descartadas y por qué

- **Borrar el repositorio y dejar solo el motor**: el propietario la retiró el 05-10.
- **Reescribir en su sitio**: rompería citas por número que no son de este trabajo.
- **Escribir en `AGENTS.md` y en `docs/canonical/` por la consola**: la protección es del
  propietario y una enmienda no justifica rodearla.
- **Tres documentos por versión**, como en 0.2 Memoria útil: el propietario pidió un plan
  sencillo, y la sección de cada versión con sus pruebas antes del código cumple lo mismo.

## La lección

- ninguna: la forma de enmendar al final, sin mover líneas citadas, ya la fijó la §19
  del Rector de evolución; este ADR la repite sin aprender nada nuevo.
