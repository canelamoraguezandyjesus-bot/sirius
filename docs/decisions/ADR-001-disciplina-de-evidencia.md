# ADR-001 — Instrumentar la disciplina de evidencia con una skill, dos hooks y este registro

- Estado: PROPUESTO
- Fecha: 2026-08-07
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario

## Contexto y problema

La automatización de Sirius cubre una sola forma de trabajo: la tubería de
programación (incidencia aprobada → implementar → Quality → revisar → corregir
→ fusionar). Funciona porque **consume** decisiones ya tomadas. Pero la mayor
parte del trabajo restante —decidir, auditar, investigar, diagnosticar— las
**produce**, y no tenía ni método instrumentado ni sitio donde aterrizar: este
directorio llevaba su convención escrita y cero ADRs, y las decisiones reales
acababan enterradas en comentarios de PR.

El coste de esa carencia se midió el 2026-08-07 en la PR #136: 19 defectos en
8 rondas de revisión, todos de dos familias —*afirmar más de lo que el dato
sostiene* (12) y *garantías puestas donde no pueden cumplirse* (7)— con una
raíz («un proceso que muere no puede informar de su propia muerte», incidencia
#138) detectable en el minuto uno con una pregunta que nadie hizo. El revisor
de diffs tuvo razón en los 19 y aun así el conjunto fue mal, porque solo se le
pedía opinión de parche.

## Nota de arranque de este mismo trabajo

Aplicada a su propia construcción, antes del primer commit:

1. *¿Dónde vive el fallo y dónde va el arreglo?* El fallo vive en el método de
   cada sesión; el arreglo vive fuera de la sesión individual: en el
   repositorio, que se carga en todas las futuras. La puerta intercepta la
   **acción de publicar**, no la intención, así que sí puede observar el fallo
   que corrige mientras la sesión está viva.
2. *¿Qué NO garantiza?* Ver «Consecuencias».
3. *Criterio de parada*: si la auditoría adversarial previa a publicar
   encuentra defectos de las familias A o B en este instrumental, se corrigen
   y se re-audita UNA vez; si la segunda ronda vuelve a traer la misma
   familia, se para y se replantea el mecanismo (regla de las dos rondas
   aplicada a sí misma).
4. *¿Qué haría el fallo imposible?* Nada: instrucciones se pueden racionalizar
   y hooks se pueden evadir a propósito. Lo más cercano es la puerta mecánica
   sobre el push con evidencia por rama, y se eligió eso.

## Criterio de parada (escrito ANTES de decidir)

El del punto 3 de la nota de arranque, publicado en la conversación con el
propietario antes de implementar y repetido aquí.

## Opciones consideradas

1. Slash command / instrucciones en el prompt (estado previo de facto).
2. Skill auto-cargable + hook de push + hook de cierre + ADR (investigación
   externa contrastada contra el repositorio).
3. Plugin empaquetado, subagente revisor propio, servidor MCP, output styles.
4. Veredictos JSON estructurados para el trabajo que no es código.

## Decisión

La opción 2, con cinco adaptaciones que el contraste con el repositorio
impuso a la investigación de origen:

- **Evidencia POR RAMA, no global**: «existe algún ADR» es una puerta que el
  primer ADR deja abierta para siempre (familia A en el diseño de origen,
  cazada antes de implementar).
- **Exención bajo `GITHUB_ACTIONS`**: los settings del repositorio se cargan
  también en el corrector de la automatización, que publica sin ADR; sin la
  exención la puerta tumbaba la tubería que ya funciona.
- **Hooks en Python** (`uv run python`): el propietario trabaja en Windows
  (PowerShell) y las sesiones remotas en Linux; bash+jq no sirve en ambos.
- **`docs/decisions/` existente** con su convención `ADR-NNN-titulo.md`, no un
  directorio paralelo; la plantilla añade la sección «Criterio de parada».
- **Los archivos vetados entran por la API a la rama de la PR**: la valla de
  permisos sigue intacta y nada llega a `main` sin la fusión del propietario.

Y los descartes de la opción 3 y 4 se adoptan como decisión explícita de NO
construir: son ceremonia sin destinatario en un repositorio con dos
participantes.

## Comprobación que la sostiene

- Puerta del push probada contra este mismo repositorio antes de publicarla:
  bloqueó el push de esta propia rama hasta que este ADR existió.
- **Auditoría adversarial de seis lentes con refutación por hallazgo**, previa
  a publicar. Confirmó ocho defectos, cinco de ellos la misma familia en la
  misma pieza: la puerta preguntaba «¿existe el archivo?» y aceptaba como
  evidencia una nota vacía, una nota sin confirmar, el README de la carpeta,
  la nota de otra rama y una nota heredada de `main` por reutilizar el nombre
  de rama. Además juzgaba la rama actual en vez de la que el comando publica,
  y moría en clones sin `origin/main`.
- **Segunda ronda (revisión de Codex sobre la PR #139)**: cuatro defectos más,
  los cuatro reproducidos, y otra vez la misma familia en la misma pieza. El
  respaldo al commit raíz abría la puerta en un clon `--single-branch` real; la
  rama publicada se identificaba pero la evidencia se seguía leyendo de `HEAD`;
  `--all` publicaba todas mirando una; un operando de opción (`-o ci.skip`) se
  tomaba por el nombre de la rama y bloqueaba trabajo legítimo. Y la prueba que
  cubría el primero era **vacua**: quitaba `origin` pero dejaba `main` local,
  así que nunca ejercitaba el respaldo.
- **El criterio de parada se cumplió y se honró.** Doce defectos en dos rondas,
  todos en el mismo punto: la puerta reconstruía la semántica de `git push`
  parseando su línea de comandos. `git push` admite `--all`, `--mirror`,
  refspecs múltiples, `HEAD:rama`, opciones con operandos y alias; enumerar sus
  formas es una carrera que se pierde ronda a ronda. No eran doce problemas
  sino uno: **la puerta adivinaba en vez de comprobar**.
- **Replanteamiento (decisión del propietario)**: se retiró el parseo entero.
  Al comando solo se le pregunta «¿es un push?»; la propiedad comprobada es que
  **el `HEAD` actual** lleve evidencia. Y el respaldo al commit raíz desapareció
  de ambos hooks: sin base fiable se falla CERRADO indicando `git fetch origin
  main`, porque comparar contra el raíz metía en el diff todo ADR fusionado en
  la historia. Lo que la puerta ya no cubre —publicar otra rama, `--all`— queda
  escrito abajo en vez de fingido en el código.
- `tests/automation/test_evidence_hooks.py` (23 pruebas) fija cada escenario
  reproducido en las dos rondas, incluido un **clon `--single-branch` de
  verdad** en sustitución de la prueba vacua. **Mutaciones verificadas en las
  dos direcciones** sobre la versión final: devolver el respaldo al raíz,
  devolver el parseo de refspecs, quitar el umbral de sustancia, aceptar la
  nota de otra rama y devolver la vía `isfile`. Las cinco hacen fallar su
  prueba; el hook real cumple los cinco escenarios.
- Sintaxis de los hooks portable a intérpretes anteriores a 3.14 (verificado
  compilando con 3.11): una sintaxis exclusiva de 3.14 habría degradado a
  pase silencioso en cualquier entorno con otro Python.

## Consecuencias

Lo que esto NO garantiza, escrito antes de estrenarlo:

- No impide un error de razonamiento; instrumenta su detección temprana.
- No aplica fuera de Claude Code (pushes manuales del propietario).
- Es evadible a propósito —`git -C`, alias, refspecs exóticos—; protege del
  descuido, no del dolo.
- **Si el lanzador no arranca, el push pasa.** El comando del hook es
  `uv run python ...`: sin `uv` en el PATH o con el entorno sin sincronizar, el
  hook no llega a ejecutarse y no hay bloqueo. Esa degradación no se puede
  cerrar desde dentro —es el observador dentro de lo observado, incidencia
  #138— y por eso se dice aquí en vez de prometer lo contrario. La exención de
  Actions vive dentro del guion, así que comparte esa suerte: si el guion no
  arranca en un runner, tampoco bloquea nada.
- No juzga la calidad de la evidencia, solo que exista y no sea un esbozo
  (tres líneas útiles y 120 caracteres). Un texto largo y vacío la pasa.
- El hook `Stop` es un empujón y no una garantía: vive dentro del proceso que
  puede morir (familia B si se prometiera más).
- La skill puede no auto-cargarse si la petición no encaja con su descripción;
  el respaldo son las líneas de `CLAUDE.md`, que se cargan siempre.
- Mantenimiento: `patrones.md` admite solo patrones que mordieron dos veces y
  se poda trimestralmente; si en un mes hay más de tres ADR de trámite
  (creados solo para pasar la puerta), la puerta se afloja a nota ligera.

## Alternativas descartadas y por qué

- **Plugin**: distribuye entre repositorios; hay uno. Envoltorio sin contenido.
- **Subagente revisor propio**: no ataca el problema (que la disciplina
  aparezca sola) y añade orquestación; Codex ya revisa.
- **MCP**: conecta servicios externos; esto es interno y las restricciones
  prohíben servicios nuevos.
- **Output styles**: retirados aguas arriba y solo cambian formato.
- **JSON estructurado para papeleo**: da sensación de control; un ADR con
  secciones fijas hace el mismo trabajo y lo lee un humano.
- **Sembrar el artefacto desde el envoltorio** (workflow o hook escribiéndolo
  por el agente): publicaría como del agente una evidencia que nunca emitió —
  exactamente la familia A que esto viene a corregir.
