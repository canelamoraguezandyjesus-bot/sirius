---
titulo: Qué memoria compartida para IAs existe ya hecha y probada, y si supera a la generada en el repositorio
fecha: 2026-09-11
autor: la sesión interactiva de Claude Code, a petición del propietario, sobre los repositorios públicos de cada candidato (clonados el 11-09-2026)
pregunta: >-
  El propietario quiere que cualquier IA que entre al proyecto (Claude Code, Codex,
  ChatGPT) sepa qué se decidió, qué hay pendiente y qué se hace, sin que él mantenga
  nada y sin dedicarle tiempo. ¿Existe ya algo hecho y probado que lo dé mejor que la
  vista generada en el repositorio (ADR-171), y a qué precio?
caduca_con:
  - los precios y límites gratuitos de los servicios alojados (Mem0, Supermemory, Basic Memory Cloud, Letta Cloud, Zep)
  - "qué clientes admiten MCP y cómo (Claude Code, Codex, ChatGPT), que cambia cada pocos meses"
  - las versiones y la actividad de cada proyecto, medidas el día de la clonación
  - la lista de herramientas que leen AGENTS.md
estado: VIGENTE
---

# Qué memoria compartida para IAs existe ya hecha y probada

## Por qué se hace

El propietario, el 11-09-2026, con estas palabras: *«seguramente hay aplicaciones,
hay repositorios, seguramente hay cosas por ahí que ya resuelven estos problemas
[...] yo lo que espero es que tú cojas y busques en todos lados y que me traigas la
mejor opción que hay»*. Y antes: *«que me crees una memoria, y me traes un
fichero»*. Tiene razón en el método: ADR-171 decidió «no elegir herramienta» sin
haber comparado ninguna con datos. Esta investigación hace esa comparación.

## Nota de arranque (escrita ANTES de leer un solo README)

**Lo que se puede comprobar desde aquí y lo que no.** Esta sesión no tiene
navegador ni búsqueda web; sí puede clonar repositorios públicos de GitHub. Por
tanto: lo que diga un README, una carpeta `docs/` o un fichero de un repositorio
se marca `[V]` con la ruta; los precios de servicios alojados, lo que ChatGPT
admite hoy y las cifras de adopción (estrellas, usuarios) **no se pueden verificar
aquí** y van como `[H]`, con la comprobación exacta de un minuto que puede hacer
el propietario.

**Criterios, en el orden que importan al propietario:**

| # | Criterio | De dónde sale |
|---|---|---|
| C1 | Cualquier IA suya lee **y escribe**: Claude Code, Codex (CLI y nube), ChatGPT | sus palabras; R2 |
| C2 | Disponible con su PC apagado | R1 |
| C3 | Sin gasto nuevo, o gratis en lo que él usa; sin minutos de Actions | R12 y su decisión de hoy |
| C4 | Captura sin esfuerzo suyo: lo pendiente y lo decidido en una sesión queda solo | sus palabras; R14 |
| C5 | Conserva origen, fecha y evidencia por dato, y no contradice «el diario manda» | R4, R8, ADR-171 |
| C6 | Sobrevive a dejar el proveedor: se exporta a ficheros planos | R3, R13 |
| C7 | Montarlo y mantenerlo le cuesta minutos, una vez | sus palabras |
| C8 | Probado: proyecto vivo, con versiones, usado por otros | sus palabras |

**Criterio de parada:**

- **(a)** Si una opción cumple C1, C2 y C3 a la vez y está probada (C8), se
  recomienda y se diseña cómo se conecta con lo que ya hay, aunque suponga
  retirar parte de ADR-171.
- **(b)** Si ninguna cumple C1+C2+C3 juntas, la memoria generada en el repositorio
  se queda como base y la mejor candidata se añade **solo para la captura** (C4),
  que es el hueco real que el propietario encontró con su ejemplo.
- **(c)** Si lo que decide entre dos opciones no se puede verificar desde aquí,
  se dice, y se le da al propietario la comprobación exacta; no se decide por él.
- **(d)** Ninguna afirmación sobre un producto sin `[V]` con ruta o `[H]` dicho.

**Qué NO cubre esto:** memorias privadas de un solo proveedor (la memoria de
ChatGPT, la de claude.ai): fallan C1 por diseño. Y Sirius 0.2, que es otro trabajo.

## Candidatos y cómo se examinaron

Clonados el 11-09-2026 (`git clone --depth 1`), con la fecha de su último commit:

| Candidato | Repositorio | Último commit |
|---|---|---|
| Mem0 y OpenMemory MCP | `mem0ai/mem0` | 2026-09-11 |
| Graphiti (Zep) | `getzep/graphiti` | 2026-09-10 |
| Basic Memory | `basicmachines-co/basic-memory` | 2026-09-10 |
| Servidor «memory» oficial de MCP | `modelcontextprotocol/servers` | 2026-09-02 |
| Supermemory | `supermemoryai/supermemory` | 2026-09-09 |
| Letta (antes MemGPT) | `letta-ai/letta` | 2026-09-10 |
| Cognee | `topoteretes/cognee` | 2026-09-09 |
| Codex (para saber qué lee y qué MCP admite) | `openai/codex` | 2026-09-11 |
| El estándar AGENTS.md | `agentsmd/agents.md` | 2026-09-10 |
| Servidor MCP de GitHub | `github/github-mcp-server` | 2026-09-08 |
| «Memory Bank» de Cline | `cline/cline` | 2026-09-11 |

## Lo que dice cada candidato de sí mismo, con la ruta que lo sostiene

Todo `[V]` es una línea de un fichero del repositorio clonado ese día. Todo `[H]`
es lo que no se pudo leer desde aquí.

### Mem0 (Platform, MCP alojado y plugin de Claude Code)

- **Tres formas**: librería, servidor propio o plataforma alojada `[V README:109-117]`.
  La librería exige un modelo de lenguaje, por defecto `gpt-5-mini` de OpenAI, y
  embeddings de OpenAI `[V README:196-198]`: la versión «gratis» cuesta llamadas.
- **MCP alojado** (`https://mcp.mem0.ai/mcp`), «nada corre en tu máquina», clientes
  listados: Claude, Claude Code, **Codex**, Cursor, Windsurf, VS Code, OpenCode;
  montaje «~2 minutos» `[V docs/platform/mem0-mcp.mdx]`.
- **Plugin de Claude Code con captura automática**: «Install once, memories are
  captured automatically and recalled in every future session»; los hooks guardan
  mensajes, respuestas, ficheros cambiados y resultados de pruebas, y la
  extracción corre en segundo plano; exige Python 3.10+ y Git en la máquina
  `[V docs/integrations/claude-code.mdx]`.
- **ChatGPT**: no está entre los clientes MCP; hay una extensión de navegador que
  guarda memorias «across ChatGPT, Perplexity, and Claude» `[V README:244]`.
- **Planes**: Free, Starter, Pro, Enterprise `[V docs/platform/features/dream.mdx:105]`.
  Los límites del plan Free **no se pudieron leer aquí** `[H]`; la única cifra en
  el repositorio es la del plan Hobby por Vercel: 10.000 memorias y 1.000 al mes,
  gratis `[V docs/integrations/vercel.mdx:111]`, que puede no ser la de la
  plataforma.
- Licencia Apache-2.0; 405 etiquetas de versión; último commit 11-09-2026 `[V]`.

### Supermemory (MCP alojado y plugins)

- **MCP alojado** `https://mcp.supermemory.ai/mcp`, sin instalar nada
  `[V README:129-147]`; plugins para Claude Code, Cursor, **Codex**, OpenCode,
  con repositorios propios (`claude-supermemory`, `codex-supermemory`)
  `[V README:114-124]`.
- **Captura automática**: herramienta `memory` («Your AI calls this automatically
  when you share something worth remembering»), `recall`, y `context`, que
  inyecta el perfil al empezar (`/context` en Claude Code) `[V README:150-156]`.
- **ChatGPT**: no aparece en la lista de clientes `[V README:169]`.
- **Precio**: por uso con créditos; planes Free, Pro, Scale, Enterprise; tarifas
  de lista 0,005 USD por 1.000 tokens de memoria y por 1.000 búsquedas
  `[V apps/docs/overview/billing.mdx]`. Los créditos del plan Free **no están en
  el repositorio** `[H]`.
- **Salida**: versión propia con embeddings locales sin clave y datos en
  `./.supermemory` `[V README:327-339]`; exportar desde la nube `[H]`.
- Licencia MIT; último commit 09-09-2026 `[V]`.

### Basic Memory (Markdown local con MCP, y su nube)

- **Markdown en disco**, «Two-way. AI and humans write to the same files»
  `[V README:34-44]`. Local gratis (AGPL-3.0); sincronización entre equipos
  «Manual (Git, Syncthing, etc.)» `[V README:169]`.
- **Nube**: 15 USD al mes, 7 días de prueba; clientes: Claude Desktop, Claude
  Code, **Codex**, Cursor, **ChatGPT (Custom GPTs)**, VS Code; exportación a
  Markdown `[V README:127-160, 186-189, 306-364]`.
- Es el único candidato que **declara ChatGPT** como cliente `[V]`.
- Captura: la IA escribe notas cuando se le pide o cuando decide; no declara
  captura automática de la conversación `[V, ausencia en README]`.

### Servidor «memory» oficial de MCP

- Grafo de entidades, relaciones y observaciones en **un fichero JSON local**,
  lanzado con `npx` o Docker `[V src/memory/README.md]`. Falla C2 por diseño
  (vive en un equipo) salvo que el fichero se guarde en el repositorio, y
  entonces vuelve a ser «un fichero en git».

### Graphiti/Zep, Cognee, Letta

- **Graphiti**: exige Neo4j o FalkorDB más clave de OpenAI; versión gestionada
  de pago (Zep) `[V README:106, 159-177]`.
- **Cognee**: clave de LLM por defecto OpenAI; Docker para el MCP; nube de pago
  `[V README:100-104, 205-229]`.
- **Letta**: el código vivo se movió a `letta-code`; servidor propio o Letta
  Cloud; es un *agente* con memoria, no una memoria para varios agentes
  `[V README:5-39]`.
- Los tres fallan C3 y C7 para un proyecto de una persona: infraestructura
  encendida, clave de pago, horas de montaje.

### Lo que hacen los demás: AGENTS.md y el «Memory Bank»

- **AGENTS.md** es «a simple, open format for guiding coding agents, used by over
  60k open-source projects» `[V agents.md/pages/_app.tsx:9]`. Codex lo lee
  `[V codex/docs/agents_md.md]`. Este repositorio ya lo usa como punto de
  entrada, y `MEMORIA.md` cuelga de él.
- **Cline Memory Bank**: ficheros `projectbrief.md`, `activeContext.md`,
  `progress.md` que el agente «MUST read ALL [...] at the start of EVERY task» y
  actualiza con la orden «update memory bank»
  `[V cline/docs/best-practices/memory-bank.mdx]`. Es exactamente el patrón de
  `MEMORIA.md`, con una diferencia: allí lo cura el agente a mano y se pudre;
  aquí se genera y una prueba lo impide.
- **Codex admite servidores MCP remotos por URL** (`codex mcp add <nombre> --url
  …`, o `[mcp_servers.x] url = "…"` en `config.toml`) `[V codex-rs/skills/src/
  assets/samples/openai-docs/references/mcp-diagnostics.md:12-19]`: cualquiera de
  los servidores alojados de arriba le vale.
- **GitHub MCP remoto**, alojado por GitHub, con guías para Claude Code y Codex
  `[V github-mcp-server/README.md:19-88]`: las incidencias de GitHub como
  registro de pendientes no necesitan nada nuevo.

## Tabla contra los criterios

| Candidato | C1 lee y escribe (Claude Code / Codex / ChatGPT) | C2 PC apagado | C3 gasto | C4 captura sola | C5 origen y evidencia | C6 exportable | C7 montaje | C8 vivo |
|---|---|---|---|---|---|---|---|---|
| Repositorio + `AGENTS.md` + `MEMORIA.md` generada | sí / sí / **solo lee** (por URL) | sí | 0 | **no**: disciplina de la IA | **sí, con prueba** | sí (git) | hecho | estándar de 60k proyectos |
| Mem0 Platform + MCP + plugin | sí (automática) / sí (MCP) / extensión de navegador | sí | plan Free `[V]`, límites `[H]` | **sí** `[V]` | fecha sí; evidencia no | API `[H]` | 2 min | sí |
| Supermemory MCP + plugins | sí / sí / **no listado** | sí | plan Free `[V]`, créditos `[H]` | **sí** `[V]` | fecha sí; evidencia no | local sí; nube `[H]` | 1 línea | sí |
| Basic Memory Cloud | sí / sí / **sí (Custom GPT)** | sí | 15 USD/mes | parcial | Markdown con fecha | **sí, Markdown** | 30 s | sí |
| Basic Memory local | sí / sí / no | **no** | 0 | parcial | Markdown | sí | minutos | sí |
| Servidor memory oficial MCP | sí / sí / no | **no** | 0 | la IA decide | no | JSON | minutos | oficial |
| Graphiti, Cognee, Letta | sí / sí / no | según montaje | **infraestructura + clave** | sí | parcial | según | **horas** | sí |
| Incidencias de GitHub (para pendientes) | sí / sí / `[H]` conector | sí | 0 | una llamada | **sí**: autor, fecha, cierre | sí | hecho | oficial |

## Conclusión, contra el criterio de parada

1. **Ninguna cumple C1+C2+C3 verificadas con las tres IAs a la vez.** Las dos
   más cercanas, Mem0 y Supermemory, cumplen C2 y C4 y tienen plan gratuito, pero
   ChatGPT no está entre sus clientes MCP y sus límites gratuitos no se pueden
   leer desde aquí. Se aplica **(b)** y **(c)**: la memoria del repositorio se
   queda como base, y la captura se cubre con una de ellas, que el propietario
   elige con una comprobación de cinco minutos.
2. **Lo construido en ADR-171 es el patrón que usa todo el mundo**, no una
   ocurrencia: ficheros en el repositorio que toda IA lee primero (AGENTS.md en
   60k proyectos, el Memory Bank de Cline). La diferencia es que aquí no se pudre.
   No hay que tirarlo ni sustituirlo.
3. **El hueco real es la captura**, el ejemplo del propietario: «queda pendiente
   hacer algo en mi ordenador». Eso lo resuelven hoy, sin infraestructura y en
   minutos, Mem0 y Supermemory: la IA lo guarda sola durante la sesión y lo
   recuerda al empezar la siguiente, en Claude Code y en Codex, con el mismo
   servidor alojado. Cuando se hace, se dice en cualquier sesión y la memoria
   lo actualiza. Lo que sea decisión o documento sigue yendo al repositorio, con
   su prueba; lo que sea contexto de sesión, pendientes y preferencias va a la
   memoria alojada. «El diario manda» no cambia.

## Recomendación

**Probar Mem0 primero**, porque es el único de los dos con captura automática
documentada para Claude Code, Codex listado como cliente MCP, plan Free y algo
para ChatGPT (la extensión). **Supermemory segundo**, misma forma, una línea
de configuración. **Basic Memory Cloud** si el propietario prefiere ver la
memoria como notas Markdown y quiere ChatGPT conectado de forma nativa, por
15 USD al mes. Graphiti, Cognee y Letta, no, para este tamaño.

Lo que el propietario tiene que comprobar, cinco minutos, porque desde aquí no
se puede:

1. **Límites del plan Free**: `app.mem0.ai` (precios) y `supermemory.ai/pricing`.
   Si el Free de Mem0 da del orden de miles de memorias, sobra para un proyecto.
2. **Si su ChatGPT admite conectores MCP** (Ajustes → Conectores → modo
   desarrollador, en las cuentas donde existe). Si sí, el mismo servidor de Mem0
   o Supermemory se conecta ahí y las tres IAs comparten memoria. Si no, para
   ChatGPT quedan la extensión de Mem0 o Basic Memory Cloud.

Con esas dos respuestas, montarlo es: instalar el plugin en Claude Code, añadir
el servidor a `~/.codex/config.toml`, y una regla en `AGENTS.md` de qué va a cada
sitio. Todo lo que hay en la nube de un tercero es tan público como se quiera:
las sesiones contienen más que el repositorio, y eso hay que saberlo al elegir.

## Lo que esta investigación NO ha podido hacer

Probar ninguno de los productos: no hay cuenta ni salida a internet desde la
sesión más allá de clonar repositorios. Todo lo de arriba es lo que cada
proyecto **dice** en su repositorio el 11-09-2026, y una afirmación en un README
no es una medición. La primera semana de uso real es la que dirá si la captura
automática recoge lo que importa o ruido.
