# ADR-172 — La memoria de sesión vive en Supermemory y el conocimiento en el repositorio, con una regla de reparto que toda IA lee

- Estado: PROPUESTO
- Fecha: 2026-09-12
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Ejecuta: la decisión 11 de ADR-171, que identificó la captura de sesión como
  el único hueco real y dejó la elección de producto al propietario con dos
  comprobaciones concretas. Las dos se han hecho, y el montaje también
- Relacionadas: ADR-171 (la memoria común generada), ADR-160 (las tres memorias
  con dueño distinto), ADR-001 (disciplina de evidencia)

> **Este ADR es la nota de arranque de su rama**, publicada en su propio commit
> antes de tocar `AGENTS.md`. Lo de abajo quedó escrito antes de hacer el cambio.

## Por qué ahora

ADR-171 dejó el conocimiento resuelto: `MEMORIA.md` se genera y ninguna PR entra
sin ella al día. Pero dejó escrito su propio límite: *«lo que se dice en chat y
no se escribe, se pierde [...] no hay mecanismo posible, solo disciplina»*. El
propietario lo puso en una frase el 12-09: **«quiero que se capture desde aquí,
desde Codex en el móvil y desde ChatGPT y todo lo que ya utilizo»**.

## Nota de arranque (escrita ANTES del cambio)

**1. ¿Dónde vive el fallo y dónde va el arreglo?** El fallo: nada recoge lo que
pasa en una sesión —lo pendiente, el contexto, las preferencias— si nadie lo
escribe a mano en el repositorio. El arreglo tiene dos mitades y **solo una está
en este repositorio**: la instalación de Supermemory en las cuatro superficies
del propietario (hecha fuera, en su máquina y en sus cuentas) y **la regla de
reparto**, que es lo único que se versiona aquí, en `AGENTS.md`.

**2. ¿Qué NO va a garantizar esto?**

- **No garantiza la captura.** En la nube no hay hooks: la IA tiene la
  herramienta y una regla que se lo pide, nada la obliga. En el ordenador del
  propietario los plugins sí capturan solos, y aun así fallan en silencio.
- **No cambia quién manda.** El diario del motor sigue siendo la autoridad sobre
  los desenlaces, y `MEMORIA.md` sobre lo decidido. Supermemory no decide nada.
- **No entra en el ciclo automático.** Los agentes de GitHub Actions no tienen
  el conector y no van a tenerlo por este ADR: la regla se escribe de forma que
  quien no tenga la herramienta simplemente no la use.
- **No promete privacidad.** Lo capturado sale a un tercero, y una sesión
  contiene más que el repositorio público. Se dice, no se disimula.

**3. Criterio de parada (escrito ANTES de ver resultados).**

- **(a)** Si la regla nueva rompe alguna prueba que fija el contenido de
  `AGENTS.md`, se corrige la regla, nunca la prueba.
- **(b)** Si la regla obligara a los agentes del ciclo a llamar a una
  herramienta que no tienen, se reescribe condicionada a que exista.
- **(c)** Si no se puede demostrar con una lectura y una escritura reales desde
  al menos tres superficies distintas, el ADR no se da por cumplido.
- **(d)** Ninguna afirmación sobre el montaje sin `[V]`.

**4. ¿Qué haría imposible el error más probable?** El error más probable es que
la regla se quede escrita y nadie la lea, que es lo que le pasó a la memoria
antes de ADR-171. Lo hace improbable —no imposible— que viva en `AGENTS.md`,
que toda IA lee al entrar, junto a la regla de `MEMORIA.md`, y que
`tests/engine/test_memoria.py` ya exija que ese fichero nombre la memoria. Lo
que no se puede hacer imposible desde aquí: que una IA decida no guardar.

## Comprobación que la sostiene

Hecha el 11 y 12-09-2026, superficie por superficie. `[V]` = observado.

| Superficie | Cómo | Resultado |
|---|---|---|
| Claude Code en el PC | Plugin `supermemory@supermemory-plugins`, clave en `SUPERMEMORY_CC_API_KEY` | **Escribe** `[V]`: guardó PRUEBA-M1 en el espacio general y en el contenedor del repositorio |
| Codex CLI en el PC | `npx codex-supermemory install`, clave en `SUPERMEMORY_CODEX_API_KEY` | **Lee** `[V]`: recuperó PRUEBA-M1 por `search_memory`, guardado desde Claude Code |
| ChatGPT web | Conector MCP en modo desarrollador, `https://mcp.supermemory.ai/mcp` | **Lee** `[V]`: recuperó PRUEBA-M1 |
| Claude Code en la nube | Conector personalizado en claude.ai, misma URL | **Lee y escribe** `[V]`: recuperó PRUEBA-M1 y guardó el estado del montaje |
| Codex en el móvil | — | **Sin comprobar** |

Se cumple el criterio (c): cuatro superficies, no tres, con al menos una lectura
y una escritura reales entre herramientas distintas.

**Lo que costó, y consta porque la próxima vez importa:** Node, Bun y el propio
Codex CLI no estaban instalados; la política de scripts de PowerShell obliga a
llamar `npx.cmd` y `npm.cmd`; y `setx` no afecta a las ventanas ya abiertas.

**Defectos observados, ninguno resuelto aquí** `[V]`:

1. El hook de recuerdo de Codex **se corta a los 5 segundos** y al arrancar
   declaró «no memories saved for sirius yet» cuando sí las había. El recuerdo
   automático no es de fiar; la búsqueda a petición sí funcionó.
2. El plugin de Claude Code guarda por defecto en el espacio general
   (`sm_project_default`), no en el contenedor del repositorio del que él mismo
   carga el contexto al empezar.
3. Los hooks salen sin error cuando el servicio no responde. Un fallo de captura
   no se distingue de una sesión sin nada que capturar.

## Decisión

1. **Supermemory es la memoria de sesión del propietario.** Espacio `Sirius`,
   plan gratuito. No sustituye a nada de ADR-171: lo completa por el lado que
   el repositorio no puede cubrir.
2. **La regla de reparto, que es lo único que este repositorio versiona:**
   - **Al repositorio, con PR, ADR y prueba**: lo decidido, lo investigado, lo
     medido, lo acordado. Nada de esto vale si solo está en la memoria.
   - **A Supermemory**: lo pendiente, el contexto de una sesión, las
     preferencias de trabajo del propietario, lo que se intentó y no salió.
   - **Ninguna de las dos manda sobre el diario del motor.** Si Supermemory y
     el diario discrepan sobre un trabajo, manda el diario (ADR-171, punto 7).
3. **`AGENTS.md` gana una regla**, condicionada a tener la herramienta: buscar
   en la memoria al empezar algo que pueda tener antecedentes, y guardar al
   terminar lo pendiente y lo aprendido que no vaya a un fichero. Quien no tenga
   el conector —los agentes del ciclo— no hace nada distinto de hoy.
4. **Lo capturado es de un tercero y sale de aquí.** El propietario lo sabe y lo
   acepta; se dice en `AGENTS.md` para que ninguna IA lo descubra por su cuenta.
5. **Los tres defectos quedan registrados y sin arreglar**, porque son
   configuración de productos de terceros y no código de este repositorio. Se
   revisan cuando estorben.

**Lo que este ADR deja fuera a propósito:** cambiar el ciclo automático, dar el
conector a los agentes de GitHub Actions, y el registro de pendientes como dato
del repositorio, que sigue siendo una decisión abierta de ADR-171.

## Consecuencias

- Una IA que entre por primera vez tiene dos sitios y sabe cuál es cuál.
- Si el propietario deja Supermemory, no pierde nada de lo decidido: eso vive en
  git. Pierde el contexto de sesión, que es lo que hoy ya se pierde entero.
- `MEMORIA.md` se regenera en esta PR, como exige ADR-171.

## Alternativas descartadas y por qué

- **Mem0**: misma forma, pero sin guía de ChatGPT y sin hooks en Codex Cloud
  (investigación del 11-09). Segunda opción si Supermemory falla.
- **No montar nada y confiar en la disciplina**: es lo que había, y es lo que el
  propietario pidió expresamente cambiar.
- **Meter los pendientes en el repositorio como dato**: sigue siendo buena idea
  y sigue abierta, pero no cubre el contexto de sesión, que era el hueco.
