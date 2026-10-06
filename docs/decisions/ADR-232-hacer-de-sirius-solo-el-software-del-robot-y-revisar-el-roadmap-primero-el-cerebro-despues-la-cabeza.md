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

La opción 3. Se completa, con el detalle de cada documento, en el commit siguiente de
esta misma rama.

## Comprobación que la sostiene

| Afirmación | Dónde se comprobó |
|---|---|
| La charla de Sirius va hoy por OpenAI | `src/sirius/composition_root.py:40` importa `OpenAIResponsesProvider` |
| Ollama ya está conectado, solo para clasificar | `src/sirius/composition_root.py:160`, modelo `qwen3:4b-instruct` |
| La búsqueda es por palabras, sin vectores | `src/sirius/adapters/persistence/sqlite_knowledge_search_repository.py:1`, FTS5 |
| La identidad está guardada por versiones | `src/sirius/domain/identity.py`, `IdentityVersion` con `personality_instructions` |
| La voz existe, con OpenAI y por turnos | `src/sirius/application/studio_voice.py` y `src/sirius/adapters/audio/` |
| El banco de 47 casos falla en el camino real: 4 de 47 y P95 438-780 ms | `docs/evolution/STATUS.md:306-307` |
| En otra variante, 7 de 47 | `docs/audits/decisiones-pendientes-de-la-linea-de-memoria.md:202` |
| El propietario no acepta ni 29 de 47 | `docs/evolution/STATUS.md:310-311` |
| Las líneas del Rector y de los STATUS están citadas por número | `docs/evolution/RECTOR.md:298-304` y `docs/canonical/STATUS.md:34-36` |
| Sirius usa Python 3.14 | `pyproject.toml:6` |

## Consecuencias

Las detalla el commit siguiente.

## Alternativas descartadas y por qué

- **Borrar el repositorio y dejar solo el motor**: el propietario la retiró el 05-10.
- **Reescribir en su sitio**: rompería citas por número que no son de este trabajo.

## La lección

- ninguna: la forma de enmendar al final, sin mover líneas citadas, ya la fijó la §19
  del Rector de evolución; este ADR la repite sin aprender nada nuevo.
