# ADR-001 — Instrumentar la disciplina de evidencia con una skill, un empujón y este registro

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

Aplicada a su propia construcción, antes del primer commit. **Se conserva tal
como se escribió**, incluido lo que el desenlace desmintió: un registro que se
reescribe a posteriori deja de ser evidencia de nada. Los puntos 1 y 4 hablan
de una puerta mecánica que finalmente se retiró (ver «Recuento y decisión
final»); están marcados donde corresponde.

1. *¿Dónde vive el fallo y dónde va el arreglo?* El fallo vive en el método de
   cada sesión; el arreglo vive fuera de la sesión individual: en el
   repositorio, que se carga en todas las futuras. La puerta intercepta la
   **acción de publicar**, no la intención, así que sí puede observar el fallo
   que corrige mientras la sesión está viva.
   → **Desmentido por el desenlace, y la primera corrección de esta línea
   también afirmaba de más.** Escribí que «la puerta sí podía observar el
   fallo»; no podía. Un hook `PreToolUse` recibe el TEXTO de un comando antes
   de ejecutarlo, no el hecho de publicar: reconocía un subconjunto de textos,
   y las formas que se le escapaban —`(git push)`, `$(git push)`, la
   continuación de línea— son la prueba de que el hecho quedaba fuera de su
   alcance. Lo que sí se sostuvo del punto 1 es lo primero: el arreglo vive en
   el repositorio, no en la sesión.
2. *¿Qué NO garantiza?* Ver «Consecuencias».
3. *Criterio de parada*: si la auditoría adversarial previa a publicar
   encuentra defectos de las familias A o B en este instrumental, se corrigen
   y se re-audita UNA vez; si la segunda ronda vuelve a traer la misma
   familia, se para y se replantea el mecanismo (regla de las dos rondas
   aplicada a sí misma).
4. *¿Qué haría el fallo imposible?* Nada: instrucciones se pueden racionalizar
   y hooks se pueden evadir a propósito. Lo más cercano es la puerta mecánica
   sobre el push con evidencia por rama, y se eligió eso.
   → **Desmentido por el desenlace**: la puerta se retiró tras quince defectos.
   La respuesta correcta a esta pregunta acabó siendo la que ya insinuaba su
   primera línea —*nada*—, y de ahí la consecuencia que cierra este ADR: el
   método no lo sostiene un mecanismo.

## Criterio de parada (escrito ANTES de decidir)

El del punto 3 de la nota de arranque, publicado en la conversación con el
propietario antes de implementar y repetido aquí.

## Opciones consideradas

1. Slash command / instrucciones en el prompt (estado previo de facto).
2. Skill auto-cargable + hook de push + hook de cierre + ADR (investigación
   externa contrastada contra el repositorio). Es la que se adoptó, **menos el
   hook de push**, que se construyó y se retiró.
3. Plugin empaquetado, subagente revisor propio, servidor MCP, output styles.
4. Veredictos JSON estructurados para el trabajo que no es código.

## Decisión

La opción 2 **sin el hook de push**, con las adaptaciones que el contraste con
el repositorio —y después la revisión— impusieron a la investigación de origen:

- **Sin puerta mecánica sobre el push.** Se construyó, se revisó cuatro veces
  y se retiró; el recuento y el porqué están abajo. Lo mecánico que queda es
  el empujón de cierre, que no parsea comandos.
- **Exención bajo `GITHUB_ACTIONS`**: los settings del repositorio se cargan
  también en el corrector de la automatización, que publica sin ADR; sin la
  exención la puerta tumbaba la tubería que ya funciona.
- **Hook en Python** (`uv run python`): el propietario trabaja en Windows
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
- **Histórico, ya no reproducible en este árbol**: mientras la puerta existió,
  `test_evidence_hooks.py` llegó a tener 23 pruebas —una por escenario
  reproducido— y cinco mutaciones verificadas en las dos direcciones. Esas
  pruebas se fueron con la puerta. Se deja constancia de que la verificación
  existió, no como evidencia del código actual: **un lector no puede
  reproducirla aquí, y decir lo contrario sería el defecto que este ADR
  documenta**.
- **Comprobable hoy**: `tests/automation/test_evidence_hooks.py` tiene **7
  pruebas**, todas del empujón de cierre y del cableado — que la exención bajo
  Actions funciona, que `stop_hook_active` deja terminar el turno, que el aviso
  es uno por rama y entorno, que calla con evidencia, sin trabajo y en `main`,
  y que los settings declaran solo el hook que existe.
- **Tercera ronda**: dos defectos, ninguno en la propiedad central, los dos en
  la superficie de la puerta —el mensaje prescribía `git fetch origin main`,
  que en un clon `--single-branch` no crea ninguna referencia, y el detector
  bloqueaba `rg 'git push' .` o `git commit -m 'no hagas push'`—. Corregidos.
- **Cuarta ronda: la puerta se retira.** El arreglo del detector partía el
  comando con una expresión regular ANTES de que `shlex` respetara las
  comillas, así que `echo "before; git push; after" > doc.md` volvía a ser un
  falso positivo, y perdía pushes reales en `(git push)`, `$(git push)` o con
  continuación de línea. Además, una prueba de esa ronda hacía `git commit` en
  un clon sin identidad git configurada: pasaba en local y tumbó Quality.

### Recuento y decisión final

| Pieza | Defectos en cuatro rondas |
|---|---|
| Skill, `patrones.md`, ADR, plantilla | **0** |
| Hook `Stop` (empujón) | 1, corregido |
| **Puerta del push** | **15** |

Quince defectos y ninguno repetido: refspecs, `--all`, operandos de opciones,
comillas, subshells, sustitución de comandos, continuaciones de línea. No eran
quince problemas. Decidir, a partir del **texto** de un comando de shell, si
ese comando ejecutará un push exige un intérprete de shell completo, y
escribirlo a trozos es una carrera que se pierde ronda a ronda.

Es la incidencia #138 con otro disfraz: un proceso que muere no informa de su
muerte, y **un texto de shell no dice qué va a ejecutar sin un shell que lo
interprete**. En ambos casos el error fue reconstruir por fuera una decisión
que solo el sistema dueño puede tomar.

El criterio de parada de la ronda 4 se publicó **antes** de ver sus resultados
y se cumplió al pie de la letra: la puerta se retira. Queda la skill que se
auto-carga, el catálogo de patrones, este registro y el empujón de cierre —lo
que acumula cero defectos en cuatro rondas—.

**La consecuencia honesta: este método no lo sostiene un mecanismo.** Lo
sostiene quien trabaja, y lo que ata es publicar el criterio donde el humano lo
ve. Eso es exactamente lo que funcionó en la PR #136 y lo que ha funcionado
aquí: el criterio publicado ha forzado dos decisiones difíciles —replantear en
la ronda 2, retirar en la ronda 4— contra la inercia de seguir parcheando.

## Consecuencias

Lo que esto NO garantiza, escrito sin adornos:

- **No hay ninguna garantía mecánica.** El empujón de cierre vive dentro del
  proceso que puede morir: una sesión cortada no lo dispara. Nada impide
  publicar sin evidencia, ni dentro ni fuera de Claude Code.
- No impide un error de razonamiento; instrumenta su detección temprana.
- La skill puede no auto-cargarse si la petición no encaja con su descripción;
  el respaldo son las líneas de `CLAUDE.md`, que se cargan siempre.
- El empujón avisa una vez por rama **y por entorno**: el marcador es local y
  no sobrevive a un contenedor efímero.
- **El empujón calla si no hay base de comparación.** En un clon
  `--single-branch` sin `origin/main`, `main` ni `origin/HEAD`, no puede saber
  qué trabajo es de esta rama, así que trabajo ya confirmado con el árbol
  limpio no produce aviso (verificado). Se documenta en vez de inventar una
  heurística: adivinar sin base es exactamente lo que costó quince defectos.
- Mantenimiento: `patrones.md` admite solo patrones que mordieron dos veces y
  se poda trimestralmente; si en un mes hay más de tres ADR de trámite
  (creados solo por inercia, sin comprobación real), se afloja la expectativa.
- **Queda por ver si sin puerta la disciplina se mantiene.** Si en unas semanas
  aparecen ramas publicadas sin evidencia, se replantea con casos reales en la
  mano en vez de con la corazonada de que hacía falta un candado.

## Alternativas descartadas y por qué

- **Plugin**: distribuye entre repositorios; hay uno. Envoltorio sin contenido.
- **Subagente revisor propio**: no ataca el problema (que la disciplina
  aparezca sola) y añade orquestación; Codex ya revisa.
- **MCP**: conecta servicios externos; esto es interno y las restricciones
  prohíben servicios nuevos.
- **Output styles**: retirados aguas arriba y solo cambian formato.
- **JSON estructurado para papeleo**: da sensación de control; un ADR con
  secciones fijas hace el mismo trabajo y lo lee un humano.
- **Insistir con la puerta del push**: cuarta versión, tras quince defectos.
  Cubrir bien el caso exige preguntarle a git en vez de adivinar de un texto;
  si alguna vez hace falta, ese es el camino, y no un parser a trozos.
- **Sembrar el artefacto desde el envoltorio** (workflow o hook escribiéndolo
  por el agente): publicaría como del agente una evidencia que nunca emitió —
  exactamente la familia A que esto viene a corregir.
