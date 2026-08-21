# ADR-055 — Dar al motor un comando de consola que conversa y consulta, y que no puede crear trabajo

- Estado: PROPUESTO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR por el propietario

## Nota de arranque (publicada ANTES de escribir una línea de código)

Este apartado se confirmó en su propio commit, antes que el arreglo, para que
la fecha del `git log` lo sostenga y no haya que creerme.

**1. ¿Dónde vive el fallo y dónde va el arreglo?**

El fallo es una **ausencia**, y vive en dos sitios a la vez:

- `pyproject.toml`, `[project.scripts]`: tres entradas, ninguna del motor.
- `src/sirius_engine/session.py`: `SesionCLI` existe y funciona, pero nadie
  fuera de `tests/` la construye nunca.

El arreglo NO vive dentro de lo que falla: va en un módulo nuevo
(`src/sirius_engine/cli.py`) más una entrada nueva en `[project.scripts]`.
La pregunta que caza la raíz —*¿puede el sitio del arreglo observar el fallo
que arregla?*— aquí se responde que sí, y de la única forma que vale: una
prueba puede leer `pyproject.toml`, resolver la entrada declarada e
**invocarla**. Si mañana alguien borra la entrada, o renombra el módulo, la
prueba cae. Una prueba que solo importara el módulo no observaría el fallo:
el fallo es «no hay comando», no «no hay código».

**2. ¿Qué NO va a garantizar esto?** (escrito antes, no como excusa después)

- **No permite dar órdenes.** Crear trabajo desde este comando queda fuera a
  propósito (requisito del encargo y primera propiedad de A5). El comando
  declina las órdenes en vez de ejecutarlas.
- **No consulta incidencias ni PR de GitHub**: eso exige red, y el encargo la
  prohíbe. Las consultas se responden con el árbol del repositorio y el
  historial de `git`. El comando lo **dice** en su salida: «no pude leerlo»
  nunca se disfraza de «no hay» (ADR-036).
- **No mejora al intérprete de intención v0.** Hereda sus límites: si la
  heurística clasifica mal un mensaje, el comando clasificará igual de mal.
- **No hace que M1 esté vivido.** Eso lo hace el propietario tecleando. Lo
  que esto hace es que pueda.
- **No decide dónde vive el almacén para siempre.** D2 fija la representación
  física (ADR-019, ADR-029); aquí solo se elige un sitio por defecto y se deja
  cambiar sin tocar código.

**3. Criterio de parada** (decidido antes de ver ningún resultado)

Se para cuando se cumplan las tres, y no antes:

1. El comando **declarado en `[project.scripts]`** —no un `python -m` ni un
   `import` desde una prueba— se ejecuta de verdad, y la sesión real queda
   pegada en este ADR y en el cuerpo de la PR.
2. Existe prueba automática que parte de `pyproject.toml` y llega a invocar
   el punto de entrada.
3. Cada mutación prevista hace caer al menos una prueba, **o** se declara
   equivalente y se explica por qué; ninguna se tapa inventando una prueba.

Y se para **antes** de terminar, escalando en vez de seguir, si aparece
cualquiera de estas dos:

- No consigo impedir que el comando cree trabajo sin reimplementar
  `SesionCLI` (el encargo prohíbe reimplementarla).
- Dos rondas seguidas de defectos de la misma familia (regla de las dos
  rondas, ADR-001).

**4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?**

Son dos fallos distintos y se responden por separado.

- *«M1 vuelve a quedarse sin comando»*: lo hace imposible que la prueba del
  punto de entrada corra en Quality **sobre el árbol fusionado**. Ninguna
  fusión en verde puede volver a dejar el motor sin comando. Esto se hace.
- *«El comando crea trabajo»*: lo haría imposible un envoltorio de solo
  lectura del `WorkEngineStore`, que levantara ante cualquier método de
  escritura. **No se hace**, y la razón irá escrita en «Alternativas
  descartadas»: el puerto tiene decenas de métodos y el envoltorio sería más
  código que el propio comando, con su propio riesgo de desincronizarse del
  puerto. Lo que se hace en su lugar irá en «Decisión».

---

## Contexto y problema

M1 —el primer hito del motor— prometía que el propietario pudiera **hablar con
Sirius y preguntarle por cualquier trabajo**. Se dio por alcanzado con las 449
pruebas del motor en verde. Pero lo que existía era una clase de Python:

    $ git grep -n "SesionCLI" origin/main -- src
    origin/main:src/sirius_engine/session.py:1:"""``SesionCLI``: la interfaz v0 …
    origin/main:src/sirius_engine/session.py:59:class SesionCLI:

Dos líneas, las dos de su propia definición. Nadie fuera de `tests/` la
construía. Y no había nada que teclear:

    $ git show origin/main:pyproject.toml | grep -A3 'project.scripts'
    [project.scripts]
    sirius = "sirius.main:main"
    sirius-voz = "sirius.voice_doctor:main"
    sirius-obs = "sirius.capture_setup:main"

Un hito que solo verifican las máquinas y que su dueño no puede usar no está
alcanzado del todo (`docs/implementation/DONDE_ESTAMOS_2026-08-21.md` §1).

## Opciones consideradas

1. **Una cáscara de consola que solo conversa y consulta**, apoyada en
   `SesionCLI` tal y como está.
2. Una cáscara **completa**, capaz también de dar órdenes que crean trabajo.
3. Un `python -m sirius_engine.session` sin entrada en `[project.scripts]`.
4. Meter el arranque dentro de `SesionCLI`.

## Decisión

**La opción 1.** `sirius-motor`, declarado en `[project.scripts]`, sobre un
módulo nuevo `src/sirius_engine/cli.py` que es solo cáscara: lee de la entrada,
escribe en la salida y monta las dependencias. Ninguna línea de lógica de turno
sale de `SesionCLI`.

Tres piezas de la decisión merecen su propio párrafo.

**Por qué no puede crear trabajo, y cómo se impide.** Crear trabajo desde la
consola es Fase B/C: no existe todavía ni la puerta que arranca un trabajador
(`ports/worker.py` no está). Y A5-P1 fija que conversar y consultar no crean
WorkItem. La cáscara, antes de entregar el turno a la sesión, le pregunta a la
**misma puerta determinista** que decidiría dentro de ella
(`decidir(interpretar_intencion_v0(mensaje))`); si el desenlace no es
`NO_CREAR`, el mensaje no llega a la sesión y el comando lo declina explicando
por qué. Las dos son funciones puras del mensaje —el módulo de la puerta lo
dice: «no toca ningún almacén ni ningún puerto»—, así que **no pueden
discrepar**: lo que la cáscara admite es exactamente lo que la sesión no
convertiría en trabajo. Esto no es reimplementar `SesionCLI`: es preguntarle a
su propia puerta antes de llamarla.

**Dónde vive el diario por defecto, y cómo se cambia sin tocar código.** En el
directorio de datos de la plataforma (`platformdirs`, la misma raíz que ya usa
la aplicación de escritorio en `sirius.infrastructure.paths`), bajo
`motor/diario.jsonl`. Se elige fuera del repositorio a propósito: el diario es
estado del propietario, no del árbol de código, y un fichero de estado dentro
del repositorio acaba en un `git status` sucio o, peor, confirmado. El
propietario lo mueve con `--diario` o con `SIRIUS_MOTOR_DIARIO`, y el argumento
manda sobre la variable. **Esto no decide la representación física del
almacén**, que sigue siendo de D2 (ADR-019, ADR-029): decide un sitio.

**Qué contesta a una consulta, y qué no mira.** `contexto.recuperar` tiene tres
proveedores. Los dos locales —árbol del repositorio e historial de `git`— se
cablean. El tercero, incidencias y PR, exigiría red, que el encargo prohíbe:
no se cablea, y el comando lo **dice** en cada respuesta. «No lo he mirado»
nunca se disfraza de «no hay nada» (ADR-036). Lo mismo si `git log` falla: se
dice, con el motivo.

## Comprobación que la sostiene

### La prueba, vista fallar antes del arreglo

Primera pasada, sin código todavía:

    $ uv run pytest tests/engine/test_cli_entrypoint.py -q
    E   ImportError: cannot import name 'cli' from 'sirius_engine'
    1 error in 0.10s

Segunda pasada, con `src/sirius_engine/cli.py` ya escrito pero **sin** la
entrada en `[project.scripts]` — este es el fallo que nombra el agujero de M1:

    E   AssertionError: `[project.scripts]` no declara 'sirius-motor': sin esa
        entrada no existe ningún comando del motor que el propietario pueda
        teclear. Declaradas: ['sirius', 'sirius-obs', 'sirius-voz']
    13 failed, 2 passed in 0.20s

Con la entrada declarada:

    $ uv run pytest tests/engine/test_cli_entrypoint.py -q
    16 passed in 0.19s

### La sesión real, ejecutada de verdad

No un `import` desde una prueba: el ejecutable que `uv sync` deja en el
entorno, con el diario apuntado por la variable de entorno.

    $ SIRIUS_MOTOR_DIARIO=/tmp/.../diario_demo.jsonl ./.venv/bin/sirius-motor < guion.txt

    Sirius Work Engine — sesión de consola (v0). Diario: /tmp/.../diario_demo.jsonl
    Raíz consultada: /home/user/sirius/.claude/worktrees/wf_c8d233e1-03e-3
    Órdenes de la sesión:
      /trabajos  lista los trabajos que ya hay en el diario (solo lee)
      /ayuda     esto
      /salir     termina la sesión

    Cualquier otra línea es un turno de conversación. Este comando conversa y
    consulta; no crea trabajo.
    > hola
    tipo de intención 'conversar': no crea WorkItem
    > estado de V8
    Encontré 11 referencia(s) para 'estado de V8': fichero:REPOSITORY_STATUS.md:116;
    fichero:docs/audits/AUDITORIA_INTEGRAL_INCORPORACION_CLAUDE_2026-07.md:92;
    fichero:docs/decisions/ADR-005-un-solo-registro-de-estado-para-v8.md:1;
    fichero:docs/decisions/ADR-005-un-solo-registro-de-estado-para-v8.md:9;
    fichero:docs/implementation/V8_EXECUTION.md:148
      (contexto.recuperar v0 desde consola no consulta incidencias ni PR: haría
      falta red. No es que no haya nada ahí; es que no lo he mirado.)
    > que paso con el bloque A5
    No encontré referencias para 'que paso con el bloque A5'.
      (contexto.recuperar v0 desde consola no consulta incidencias ni PR: haría
      falta red. No es que no haya nada ahí; es que no lo he mirado.)
    > implementa el despachador de programacion
    Esto es una orden, y este comando no crea trabajo: en v0 solo conversa y
    consulta (A5-P1, ADR-055). La puerta lo clasificó como crear_y_activar:
    orden explícita e inequívoca: la orden ya es la autorización
    > borra la base de produccion
    Esto es una orden, y este comando no crea trabajo: en v0 solo conversa y
    consulta (A5-P1, ADR-055). La puerta lo clasificó como crear_y_escalar: el
    mensaje contiene 'borra': causa operacion_destructiva_o_irreversible
    > /trabajos
    El diario no contiene ningún trabajo todavía.
    > gracias
    tipo de intención 'conversar': no crea WorkItem
    > /salir

    $ ls -l /tmp/.../diario_demo.jsonl
    ls: cannot access '…/diario_demo.jsonl': No such file or directory

**El diario no llegó a existir.** Dos órdenes, dos consultas y tres turnos de
charla no escribieron un solo byte.

Y leyendo un diario que sí tiene contenido (sembrado a mano con el almacén
durable, porque el comando no puede crear trabajo):

    $ stat -c%s diario_sembrado.jsonl   → 870
    $ SIRIUS_MOTOR_DIARIO=…/diario_sembrado.jsonl ./.venv/bin/sirius-motor
    > /trabajos
      WI-DEMO-1  planned/preparar  investigar el bloque S2
    > /salir
    $ stat -c%s diario_sembrado.jsonl   → 870

Los mismos 870 bytes: consultar tampoco escribe.

Un turno suelto, sin sesión interactiva:

    $ ./.venv/bin/sirius-motor "estado de V8"
    Encontré 11 referencia(s) para 'estado de V8': …

### El comando estaba muerto en el paquete construido, y no lo veía nadie

Al declarar la entrada apareció un defecto que ninguna prueba existente podía
ver: el backend de construcción empaquetaba **un solo módulo**.

    $ uv build --wheel   # con module-name = "sirius"
    sirius_engine files: 0
    sirius files: 172

    $ uv build --wheel   # con module-name = ["sirius", "sirius_engine"]
    sirius_engine files: 48
    sirius files: 172

En desarrollo no se nota porque la instalación editable publica `src/` entero
con un `.pth`, y `sirius_engine` se importa igual esté o no en el paquete. Una
vez instalado de verdad, `sirius-motor` habría arrancado y muerto en el
`import`. Se corrige aquí, y la prueba
`test_todo_comando_declarado_apunta_a_un_modulo_que_el_paquete_construido_contiene`
lo fija como regla general, no como parche: **toda** entrada de
`[project.scripts]` tiene que apuntar a un módulo que el backend empaquete.

### Prueba por mutación

Siete mutaciones, sembradas y revertidas por un guion que guarda el texto
original en memoria y lo reescribe en un `finally` —nunca `git checkout` sobre
el fichero, que se llevaría por delante el resto del trabajo.

| # | Mutación | Resultado |
|---|---|---|
| M1 | La puerta deja de filtrar: `if decision.resultado is not NO_CREAR` → `if False` | **cae** (3): órdenes declinadas, orden sensible, conversación intercalada |
| M2 | La sesión se monta con `contexto_recuperar=None` | **cae** (2): cita del árbol, historial ilegible |
| M3 | La entrada de consola se renombra a `sirius-motorr` | **cae** (13): todo lo que parte de `pyproject.toml` |
| M4 | `resolver_diario` ignora `SIRIUS_MOTOR_DIARIO` | **cae** (2): resolutor y comando entero |
| M5 | `_historial` se traga el `EspejoIlegibleError` y devuelve vacío | **cae** (1): «no pude leer» ≠ «no hay» |
| M6 | `module-name` vuelve a ser solo `"sirius"` | **cae** (1): entrada que apunta a un módulo no empaquetado |
| M7 | `/trabajos` deja de reconocer los eventos de WorkItem | **cae** (2): listado y gobierno por entorno |

Ninguna sobrevivió. La salida literal de cada una está en el cuerpo de la PR.

### Validaciones

    $ uv run ruff format --check .   → 433 files already formatted
    $ uv run ruff check .            → All checks passed!
    $ uv run mypy src tests          → Success: no issues found in 414 source files
    $ uv run pytest tests/engine/test_cli_entrypoint.py tests/engine/test_session.py
          tests/automation/test_registro_de_decisiones.py -q → 28 passed
    $ uv lock --check                → Resolved 60 packages
    $ git diff --check               → (sin salida)

La batería completa la valida Quality sobre el árbol fusionado: correrla aquí
en paralelo con otros agentes es lo que mató por OOM al intento anterior de
este mismo trabajo.

## Consecuencias

- **M1 ya se puede vivir.** `uv run sirius-motor` y hay con qué hablar.
- La prueba del punto de entrada corre en Quality **sobre el árbol fusionado**:
  ninguna fusión en verde puede volver a dejar el motor sin comando.
- La regla «toda entrada de consola apunta a un módulo empaquetado» queda
  fijada para los cuatro comandos, no solo para el nuevo.
- El comando **declina las órdenes**. Cuando exista `ports/worker.py` y el
  contrato v1.8 esté firmado, quitar esa barrera es cambiar una condición y
  borrar dos pruebas —que es exactamente lo que se quiere que cueste.
- Aparece una superficie nueva que mantener: `--diario`, `--raiz`, sus dos
  variables de entorno y tres órdenes de sesión (`/trabajos`, `/ayuda`,
  `/salir`).

### Un defecto que este trabajo destapó y NO arregla

La demo de arriba lo enseña sin maquillar: `que paso con el bloque A5` no
encuentra nada, y `estado de V8` sí. La razón está en
`intent_interpreter.py`, no en la cáscara:

    return IntentSignal(tipo=TipoIntencion.CONSULTAR_PASADO,
                        mensaje_original=mensaje, consulta=mensaje)

La `consulta` es **el mensaje entero**, y `buscar_en_arbol_repo` busca esa
cadena como subcadena literal. O sea: una consulta solo acierta si la frase
completa que el propietario teclea aparece tal cual en un fichero. `estado de
V8` acierta por poco —es corta y aparece literalmente—; cualquier pregunta
normal no acertará nunca.

No se arregla aquí por dos razones, y las dos son de alcance: el encargo de
esta rama es la cáscara («reutiliza `SesionCLI`, no la reimplementes»), y el
arreglo vive en la clasificación de A5, que es otra vertical. Tampoco entra en
`docs/audits/registro_defectos.yml`: ese registro exige número de incidencia
para un defecto abierto, abrir una incidencia despierta el ciclo automático, y
eso es decisión del propietario, no mía. Queda dicho aquí y en la PR, que es
donde se ve.

Segundo detalle, menor y del mismo origen: a `hola` el motor responde `tipo de
intención 'conversar': no crea WorkItem`. Es el `motivo` que devuelve la
puerta, y la cáscara lo enseña tal cual en vez de inventar una respuesta más
amable. Escribir aquí una frase que el motor no ha dicho sería exactamente el
defecto que este repositorio persigue.

## Alternativas descartadas y por qué

- **Una cáscara que también dé órdenes (opción 2).** Rompe A5-P1 y promete algo
  que el motor no puede cumplir: no existe todavía la puerta que arranca un
  trabajador (`src/sirius_engine/ports/worker.py` no está en `main`). Un
  comando que creara WorkItems que nadie va a ejecutar sería un generador de
  trabajo muerto en el diario.
- **Un envoltorio de solo lectura del `WorkEngineStore`** que levantara ante
  cualquier método de escritura. Es la respuesta que haría el fallo
  *imposible* y no solo improbable, y por eso se consideró en serio. Se
  descarta por su coste: el puerto declara más de cuarenta métodos, el
  envoltorio sería bastante más código que el propio comando, y quedaría
  obligado a seguir al puerto en cada cambio —una fuente nueva de deriva
  silenciosa. Lo que se hace en su lugar tiene casi la misma fuerza y ninguna
  duplicación: preguntar a la MISMA función pura que decide dentro de la
  sesión. Lo que no cubre, dicho: si algún día el intérprete dejara de ser
  puro (uno con modelo real, por ejemplo), las dos llamadas podrían discrepar,
  y entonces sí haría falta el envoltorio. Está anotado aquí para el día que
  pase.
- **`python -m sirius_engine.session` (opción 3).** No arregla el fallo: el
  propietario seguiría sin tener un comando, solo una forma más corta de
  escribir el `import`. Y nada impediría que la siguiente fusión lo dejara
  otra vez sin nada que teclear, porque no habría entrada declarada que una
  prueba pudiera vigilar.
- **Meter el arranque dentro de `SesionCLI` (opción 4).** La sesión es «sin
  estado propio» por contrato (objetivo 5 de #206) y Telegram será otro
  adapter (D3). Meterle dentro la lectura de `stdin`, `argparse` y la
  resolución de rutas la ata a la consola y obliga a deshacerlo en D3.
