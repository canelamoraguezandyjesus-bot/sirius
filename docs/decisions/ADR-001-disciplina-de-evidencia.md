# ADR-001 — Instrumentar la disciplina de evidencia con una skill y este registro

- Estado: PROPUESTO
- Fecha: 2026-08-08
- Aprobación: la fusión de la PR #139 por el propietario

## Contexto y problema

La automatización de Sirius cubre una sola forma de trabajo: la tubería de
programación. Funciona porque **consume** decisiones ya tomadas. El resto del
trabajo —decidir, auditar, investigar, diagnosticar— las **produce**, y no
tenía ni método instrumentado ni sitio donde aterrizar: este directorio llevaba
su convención escrita y cero ADRs, y las decisiones acababan enterradas en
comentarios de PR.

El coste se midió en la PR #136: 19 defectos en 8 rondas de revisión, de dos
familias —*afirmar más de lo que el dato sostiene* y *garantías puestas donde
no pueden cumplirse*— con una raíz (incidencia #138) detectable en el minuto
uno con una pregunta que nadie hizo.

## Criterio de parada (escrito ANTES de decidir)

Si la auditoría previa encuentra defectos de esas familias en este
instrumental, se corrigen y se re-audita una vez; si la segunda ronda vuelve a
traer la misma familia, se para y se replantea el mecanismo. La regla de las
dos rondas, aplicada a sí misma.

**Se cumplió tres veces y las tres se honró**: replantear la puerta del push,
retirarla, y recortar este documento.

## Decisión

Una **skill que se auto-carga** (`disciplina-evidencia`) con el método y su
catálogo de patrones; un **empujón de cierre** que pide la evidencia una vez
por rama; y **este registro** con su plantilla.

Sin puerta mecánica. Se construyó una que bloqueaba `git push` sin evidencia y
se retiró tras 15 defectos en 4 rondas.

Se descartan por ceremonia sin destinatario en un repositorio de dos
participantes: plugin, subagente revisor propio, servidor MCP, output styles y
veredictos JSON para el trabajo que no es código.

## Comprobación que la sostiene

Comprobable en este árbol, hoy:

- `tests/automation/test_evidence_hooks.py`: **7 pruebas** del empujón y del
  cableado —exención bajo Actions, `stop_hook_active` deja terminar el turno,
  el aviso es uno por rama y entorno, calla con evidencia, sin trabajo y en
  `main`, y los settings declaran solo el hook que existe—.
- La skill se auto-carga por descripción, sin invocación manual.

Histórico, **no reproducible aquí**: mientras la puerta existió tuvo 23 pruebas
y cinco mutaciones verificadas en las dos direcciones. Se fueron con ella. Se
deja constancia de que la verificación existió, no como evidencia del código
actual.

## Recuento de las cuatro rondas

| Pieza | Defectos |
|---|---|
| Skill, `patrones.md`, plantilla | 0 |
| Este ADR (texto) | varios, corregidos |
| Empujón de cierre | 2, corregidos: mensaje que prometía de más, y colisión de marcadores entre ramas que normalizan igual |
| **Puerta del push** | **15** |

Quince, y ninguno repetido: refspecs, `--all`, operandos de opciones, comillas,
subshells, sustitución de comandos, continuaciones de línea.

No eran quince problemas. Decidir, desde el **texto** de un comando de shell,
si ese comando ejecutará un push exige un intérprete de shell completo. Es la
incidencia #138 con otro disfraz: allí *un proceso que muere no informa de su
propia muerte*; aquí **un texto de shell no dice qué va a ejecutar sin un shell
que lo interprete**. Las dos veces, el error fue reconstruir por fuera una
decisión que solo el sistema dueño puede tomar.

## Consecuencias

Lo que esto NO garantiza:

- **No hay garantía mecánica.** El empujón vive dentro del proceso que puede
  morir: una sesión cortada no lo dispara. Nada impide publicar sin evidencia.
- **El empujón calla sin base de comparación.** En un clon `--single-branch`
  sin `origin/main`, `main` ni `origin/HEAD` no puede saber qué trabajo es de
  esta rama, así que trabajo confirmado con el árbol limpio no produce aviso.
  Se documenta en vez de inventar una heurística: adivinar sin base es lo que
  costó los quince defectos.
- **El aviso es uno por rama y por entorno**: el marcador es local y no
  sobrevive a un contenedor efímero.
- La skill puede no auto-cargarse si la petición no encaja con su descripción;
  el respaldo son las líneas de `CLAUDE.md`, que se cargan siempre.
- No impide un error de razonamiento; instrumenta su detección temprana.

**Este método no lo sostiene un mecanismo. Lo sostiene quien trabaja**, y lo
que ata es publicar el criterio donde el humano lo ve. Es lo que forzó las tres
decisiones difíciles de esta PR contra la inercia de seguir parcheando.

Queda por ver si sin puerta la disciplina se mantiene. Si aparecen ramas
publicadas sin evidencia, se replantea con casos reales en la mano.

## Por qué este documento es corto

Llegó a tener el triple: una crónica ronda por ronda de cada defecto y cada
arreglo. Las últimas rondas de revisión ya no encontraron nada en el
comportamiento del código y sí afirmaciones que el árbol había dejado de
sostener —un recuento de pruebas caducado, una corrección que conservaba el
exceso que corregía, un «cero defectos» que la tabla de al lado desmentía—.

La señal era clara: **el documento crecía más deprisa de lo que se verificaba**,
y un registro que hay que auditar continuamente deja de ser un registro. Se
recortó a lo comprobable. La crónica completa vive en los mensajes de commit y
en los hilos de la PR #139, que son inmutables y no hay que mantener.

## Alternativas descartadas y por qué

- **Puerta mecánica sobre el push**: 15 defectos. Cubrirla bien exige
  preguntarle a git en vez de adivinar de un texto; si alguna vez hace falta,
  ese es el camino, y no un parser a trozos.
- **Slash command**: solo se carga si alguien lo escribe, y en la sesión que
  motivó esto el propietario no escribió ninguno.
- **Sembrar el artefacto desde el envoltorio**: publicaría como del agente una
  evidencia que nunca emitió, que es la familia A que esto viene a corregir.
