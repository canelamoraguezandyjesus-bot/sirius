# ADR-208 — Las ideas aparcadas tienen registro, y el método de conversación del propietario entra en AGENTS.md

- Estado: APROBADO
- Fecha: 2026-09-20
- Aprobación: el propietario, el 20-09-2026. La decisión 7 con sus palabras
  —«pues en algún sitio o carpeta para identificarlas»— y la 8 condicionada:
  «si es útil pues lo hacemos, pero deja de escribirme mierdas en el repo».
- Nota de arranque: la de ADR-204, que cubre esta tanda entera.

## Contexto y problema

Dos de las diez decisiones de la auditoría, y las dos sobre lo mismo: algo que
existe, que se usa todos los días y que **no está escrito en ninguna parte**.

**Las ideas.** El paso 3 contó nueve ideas en doce conversaciones y encontró que
«aparcado» no tiene sitio. La orquestación grande de agentes se aparcó el
24-07-2026 y volvió el 16-09 como si fuera nueva: hubo que pensarla entera otra
vez. La propia IA había dicho el 10-08 «apúntalo como idea aparcada» y no había
dónde.

**El método de conversación.** El paso 3 sacó siete reglas de cómo el
propietario debate hasta decidir, y el paso 4 añadió cuatro más al verlas en
ejecución. Once reglas que gobiernan todas las sesiones y que vivían en la
memoria de claude.ai y en la de sesión, no en el repositorio. `AGENTS.md` solo
tenía una de ellas.

## Criterio de parada (escrito ANTES de decidir)

Para las ideas: si el registro no va a leerlo nadie, no se crea. Un registro que
no aparece donde se mira al empezar es una `pieza-sin-lector`, que es
exactamente la familia que esta misma tanda acaba de cerrar en ADR-207. **Si no
entra en `MEMORIA.md`, no se hace.**

Para el método: el propietario condicionó la decisión a que sea útil y pidió
expresamente no llenar el repositorio de documentos. Si no cabe en la sección de
un fichero que ya se lee, no se escribe.

## Decisión

### 1. Las ideas van a un registro, con un campo obligatorio por estado

`docs/ideas/registro_de_ideas.yml`, con tres estados y un campo que cada uno
exige:

| Estado | Exige | Por qué |
|---|---|---|
| `aparcada` | `volver_si` | Una aparcada sin disparador no es una idea aparcada: es una idea olvidada con mejor nombre, y vuelve en cada repaso |
| `descartada` | `porque` | Se lee una vez y se acabó. Es la lección de ADR-198 aplicada a las ideas |
| `promovida` | `promovida_a` | Dejó de ser idea: tiene ADR o incidencia, y se dice cuál |

Lo hace cumplir `tests/automation/test_registro_de_ideas.py`, igual que ADR-087
hace con los bloques del motor y ADR-080 con los defectos. Y el registro
**entra en `MEMORIA.md`**, que es lo que el criterio de parada exigía: las ideas
se leen al empezar, sin que nadie tenga que acordarse de abrir el fichero.

Nace con seis entradas, todas sacadas de la auditoría: la orquestación grande,
n8n, Obsidian, las piezas de Memanto, el agente que revisa por módulos y el
cazador de contradicciones —esta última **promovida**, porque se construyó sin
llamarse así: es ADR-005 y su prueba—.

### 2. El método de conversación entra en `AGENTS.md`

Once reglas, en una sección, en el fichero que toda IA de este repositorio lee
antes de responder. No es un documento nuevo: es el sitio donde ya se leen las
demás reglas.

La que más ahorra, y la más incómoda de escribir: **cuando el propietario
corrige el cuadro, suele tener razón**. De seis correcciones suyas medidas en el
paso 4, acertó las seis, y en cinco el hecho no estaba en `main` —vivía en una
rama sin fusionar, en una prueba manual que hizo él, o en su cabeza—. La regla
que sale de ahí no es «hazle caso»: es **compruébalo antes de contradecirle**,
porque el árbol no tiene el dato.

## Comprobación que la sostiene

- **El criterio de parada de las ideas se cumple:** `src/sirius_engine/memoria.py`
  lee el registro nuevo y `MEMORIA.md` trae la sección «Las ideas aparcadas y
  descartadas» y la cuenta en «Qué hay, en números». Una prueba lo fija
  (`test_la_vista_de_conocimiento_lee_este_registro`), así que el registro no
  puede quedarse sin lector en silencio.
- **La guarda del registro, verificada por mutación**, cada una sobre el árbol
  confirmado:

| Mutación | Resultado |
|---|---|
| una idea aparcada se queda sin `volver_si` | falla |
| dos ideas con el mismo identificador | falla |
| un estado que no existe (`quiza`) | falla |
| la vista deja de listar el registro | falla |

- **El criterio de parada del método se cumple:** las once reglas caben en dos
  secciones de `AGENTS.md`; no se ha creado ningún documento nuevo.
- Las once reglas están ancladas: cada una cita la ficha C-03 o E-01 a E-04 de
  `docs/audits/AUDITORIA_FORMA_DE_TRABAJO_2026-09.md`, donde constan con su
  fecha y su fuente.

## Consecuencias

- Una idea que se aparca deja rastro con su disparador, y aparece al empezar
  cualquier sesión. La incidencia #15 del repositorio —«bandeja de preservación»
  de ideas— deja de ser el único sitio donde viven, y puede archivarse.
- Una sesión nueva sabe cómo se conversa con el propietario sin tener que
  aprenderlo a base de escaladas.
- **El coste:** dos secciones más en `AGENTS.md`, que ya es largo. Se acepta
  porque es el único fichero que se lee siempre; repartirlo en documentos
  aparte es lo que produjo las piezas sin lector de ADR-207.

## Alternativas descartadas y por qué

- **Las ideas en un documento en prosa.** Se pudre igual que los mapas de julio
  y nadie puede comprobar que una aparcada declara su disparador.
- **Las ideas como incidencias de GitHub.** Es lo que se hizo con la #15 y lleva
  desde el 15-07-2026 sin tocarse. Además el motor usa las incidencias para
  trabajo despachable, y una idea no lo es.
- **El método de conversación en una skill.** El propietario pidió no crear
  skills hasta que la auditoría dijera qué merece mecanizarse, y esto es una
  regla que hay que leer siempre, no un procedimiento que se invoca.

## La lección

- familia: `regla-del-propietario-que-solo-vive-en-una-conversacion`
- sin esto se repetiría: las ideas aparcadas volverían como nuevas y cada
  sesión reaprendería a base de escaladas cómo quiere el propietario que se
  hable con él.
- lo hace cumplir: `tests/automation/test_registro_de_ideas.py`
