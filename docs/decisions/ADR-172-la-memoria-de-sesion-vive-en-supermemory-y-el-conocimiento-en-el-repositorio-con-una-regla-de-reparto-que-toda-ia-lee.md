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

**El criterio (c), ahora sí, cumplido** `[V, 12-09]`. Se sembró `PRUEBA-M2`
desde la sesión de la nube, **una sola vez y solo** en
`repo_sirius__e87a5bbe75fe00b6`, sin copiarla a ningún otro espacio. El
complemento de Claude Code del propietario la recuperó, copia única, en ese
espacio. Escrita por una herramienta, leída por otra, sin duplicar: eso es lo
que PRUEBA-M1 no demostraba.

Y la misma comprobación **midió el modo de fallo que la regla evita**, que es lo
que la convierte en necesaria y no en una precaución de papel:

| Búsqueda | Espacio en que buscó | ¿La encontró? |
|---|---|---|
| Complemento local, **nombrando** el espacio | `repo_sirius__e87a5bbe75fe00b6` | **Sí**, la primera |
| Complemento local, sin nombrarlo | `sm_project_default` | **No** |
| Conector de claude.ai, sin nombrarlo | `sm_project_default` | **No** |

Dos de cada tres búsquedas fallan si nadie nombra el espacio. Por eso la regla
dice «en **cada** búsqueda y en **cada** guardado», y no «cuando convenga».

**Esa tabla afirmaba de más, y la revisión de la PR lo encontró** (12-09). Las
cuatro superficies alcanzaron PRUEBA-M1, sí, **pero PRUEBA-M1 estaba copiada a
mano en los dos espacios**: recuperarla no demostraba que compartieran nada. Al
medirlo, el reparto real era este `[V, listMemories el 12-09]`:

| Espacio | Qué contenía | Quién lo escribió |
|---|---|---|
| `repo_sirius__e87a5bbe75fe00b6` | 7 recuerdos | **solo** la captura automática del complemento local |
| `sm_project_default` | 12 recuerdos, entre ellos toda esta decisión | **solo** lo escrito por MCP: la nube, ChatGPT |

Dos memorias paralelas que no se veían. El criterio (c) **no estaba cumplido**
con esa evidencia: no había ni una lectura, desde una herramienta, de algo
escrito por otra y no copiado. La corrección es el punto 3 de la Decisión, y su
comprobación está **hecha**, justo debajo: no queda nada por repetir.

**La regla, y su guardia** `[V]`. La sección nueva de `AGENTS.md` no rompía
ninguna prueba —criterio (a) satisfecho— y eso era, en sí, el defecto: una regla
que se puede borrar sin que salte nada es la que se pudre (ADR-171). Se le puso
guardia, y **la primera versión de esa guardia era mala**: comprobaba cuatro
expresiones sueltas sobre el fichero entero, así que se podían borrar las dos
instrucciones y la tabla de reparto completa y seguía en verde. Lo encontró la
misma revisión, reproduciéndolo.

La segunda versión comprobaba doce obligaciones, una a una y dentro de su
sección, con una prueba parametrizada que retiraba cada una. **Y también estaba
mal**, lo encontró la misma revisión en la ronda siguiente: esa prueba borraba
la frase y comprobaba que la frase ya no estaba, que es cierto por construcción.
**Nunca llamaba al detector**, así que anularlo entero la dejaba en verde.

La versión buena, la tercera, tiene el detector en **una sola función**,
`_obligaciones_ausentes`, y las pruebas la **ejecutan** sobre el texto mutado.
Comprobado anulando el detector de tres maneras `[V, 12-09]`:

| Detector anulado así | ¿Lo detectan las pruebas? |
|---|---|
| Devuelve siempre la lista vacía | **Sí**, caen las doce |
| Devuelve siempre todas | **Sí** |
| Busca en el fichero entero y no en la sección | **No** — hueco real |

El tercero destapó que nada obligaba a mirar dentro de la sección, así que la
regla se podía desmontar repartiéndola por `AGENTS.md`. Se cerró con
`test_la_obligacion_escrita_fuera_de_su_seccion_no_cuenta`, que mueve cada
obligación fuera de su sección y exige que el detector siga acusándola; con
ella, las **tres** anulaciones caen. Y la mutación de las doce sigue,
ahora ejecutando el detector de verdad. No comprueba
conducta, que no se puede: comprueba que la regla siga escrita y completa donde
toda IA la lee. El criterio (b) se cumple: la sección empieza diciendo que solo
aplica a quien tenga la herramienta.

**Las validaciones:** `ruff format --check` y `ruff check` en verde, `mypy src
tests` sobre 588 ficheros sin incidencias, y la suite completa antes del push.

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
4. **El recuerdo automático va por detrás de lo guardado** `[V, 12-09]`. Al
   recuperar `PRUEBA-M2`, el recuerdo automático de esa misma sesión trajo
   `PRUEBA-M1` y no `PRUEBA-M2`: se alimenta del resumen del espacio, que
   todavía no la incluía. Lo escrito hace un momento **solo** aparece buscándolo
   a propósito. Consecuencia práctica: no confíes en que lo último quede
   recordado solo; si importa, búscalo.

## La raíz, porque fueron dos rondas de la misma familia (ADR-001)

Las dos primeras guardias fallaron por lo mismo, y conviene nombrarlo antes de
seguir: **afirmaban comprobar algo sin ejecutarlo nunca contra un caso malo
conocido.** La primera buscaba cuatro expresiones sueltas y llamaba a eso
«proteger la regla». La segunda borraba una frase y comprobaba que la frase ya
no estaba —cierto por construcción— y llamaba a eso «prueba por mutación». Las
dos pasaban en verde sin medir nada.

La regla de las dos rondas obliga a no poner un tercer parche, así que la
corrección no es una aserción más: es **un solo detector, y todas las pruebas lo
ejecutan**. Eso es lo que permite anularlo y ver caer las pruebas, que es la
única forma de saber que una guardia guarda. Vale para cualquier guardia futura
de este repositorio: *si no la has visto fallar contra una versión rota a
propósito, no sabes si comprueba algo*. Es la anti-vacuidad que el repositorio
ya aplica en otras pruebas, y que aquí se saltó dos veces seguidas.

## Decisión

1. **Supermemory es la memoria de sesión del propietario.** Cuenta suya, espacio
   de trabajo `Sirius`, plan gratuito. Ojo con los nombres, que en esta
   herramienta no son lo mismo: el **espacio de trabajo** es la cuenta y el
   **espacio** (`containerTag`) es el cajón donde caen los recuerdos; el punto 3
   fija cuál. No sustituye a nada de ADR-171: lo completa por el lado que el
   repositorio no puede cubrir.
2. **La regla de reparto, que es lo único que este repositorio versiona:**
   - **Al repositorio, con PR, ADR y prueba**: lo decidido, lo investigado, lo
     medido, lo acordado. Nada de esto vale si solo está en la memoria.
   - **A Supermemory**: lo pendiente, el contexto de una sesión, las
     preferencias de trabajo del propietario, lo que se intentó y no salió.
   - **Ninguna de las dos manda sobre el diario del motor.** Si Supermemory y
     el diario discrepan sobre un trabajo, manda el diario (ADR-171, punto 7).
3. **El espacio canónico es `repo_sirius__e87a5bbe75fe00b6`, y se nombra en
   cada llamada.** Buscar y guardar no basta: sin `containerTag` explícito cada
   herramienta usa el suyo por omisión, que es como nacieron las dos memorias
   paralelas de arriba. Se elige el del repositorio, y no el de la cuenta, por
   dos razones: es donde ya cae la captura automática —la parte que nadie
   controla— y lo deriva el complemento del remoto de git, así que no mezcla
   este proyecto con lo que el propietario hable de cualquier otra cosa. Si el
   espacio no aparece, la regla obliga a **parar y decirlo**, nunca a escribir
   en otro. No se confía en el «espacio activo»: es un selector interactivo y
   `whoAmI` lo devolvía vacío `[V]`.
4. **`AGENTS.md` gana la regla entera**, condicionada a tener la herramienta:
   buscar al empezar, guardar al terminar, nombrar el espacio siempre, y el
   reparto de abajo. Quien no tenga el conector —los agentes del ciclo— no hace
   nada distinto de hoy.
5. **Lo capturado es de un tercero y sale de aquí.** El propietario lo sabe y lo
   acepta; se dice en `AGENTS.md` para que ninguna IA lo descubra por su cuenta.
6. **Los tres defectos quedan registrados y sin arreglar**, porque son
   configuración de productos de terceros y no código de este repositorio. Se
   revisan cuando estorben.

**El espacio viejo no se migra ni se borra.** Los 12 recuerdos que quedaron en
`sm_project_default` son de antes de esta regla; lo que de ellos importaba —el
reparto, los defectos, las preferencias del propietario— se reescribió en el
espacio canónico, así que nada se pierde. Borrarlos exigiría una máquina que no
compensa, y dejarlos no hace daño: nadie los busca, porque la regla manda
nombrar el espacio.

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
