# ADR-171 — La memoria común arranca sobre lo que ya existe: evaluación funcional de las tres piezas (T-5) y lo que el motor tiene que publicar

- Estado: PROPUESTO
- Fecha: 2026-09-11
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Ejecuta: la decisión técnica pendiente **T-5** de
  `docs/evolution/PROPUESTA_SEPARACION_SIRIUS_MOTOR.md` §7.2, que ADR-160 dejó
  abierta: *«la evaluación funcional —qué requisitos de 6.3 cumple ya cada pieza
  existente— no se ha hecho, y es trabajo previo a elegir nada»*
- Numeración: 171 y no 170. `main` llega a ADR-169 y la PR abierta #583 tiene
  tomado el 170. Mismo modo de fallo que ADR-069 documenta; se evitó mirando las
  PR abiertas
- Relacionadas: ADR-160 (las tres memorias con dueño distinto, EV-018), ADR-082 y
  ADR-083 (el diario del motor vive en su rama), ADR-161 y ADR-163 (los carriles
  retirados que dejaron la memoria común como decisión pendiente), ADR-001

> **Este ADR es también la nota de arranque de la rama**, publicada en su propio
> commit antes de leer una sola pieza. Las conclusiones se rellenan después, con
> evidencia marcada `[V]` (verificado en el repositorio) o `[H]` (hipótesis).

## Por qué ahora

El propietario lo ha dicho con estas palabras: *«cuando hablo en una sesión de
Claude Code, cuando tomo decisiones, cuando redacto documentos, cuando se trabaja
en el motor, todo quede en un mismo sitio»*, y *«siempre estáis leyendo las
conversaciones todo el rato y me gastáis muchos planes»*. Las dos cosas son la
misma: **nada publica el trabajo al hacerse en una forma barata de consultar**,
así que cada sesión y cada run reconstruye el contexto releyendo el repositorio.

Y la dirección ya está dada (ADR-160, EV-018): la memoria común es memoria **del
trabajo**, las IAs la actualizan, y el propietario **no escribe fichas** (R14).
Lo que falta no es una decisión nueva: es la evaluación que ADR-160 declaró
previa a cualquier elección, y que nadie ha hecho.

## Nota de arranque (publicada ANTES de evaluar)

**1. ¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en dos sitios y
el arreglo también. Primero, **nadie ha medido qué cumplen ya las tres piezas**
—el repositorio, el diario del motor, la memoria del producto— frente a los
catorce requisitos de la propuesta §6.3; sin eso, cualquier herramienta se elige
a ciegas y cualquier «mapa» se pudre. Segundo, **el motor no publica
desenlaces**: la propuesta §6.2 le asigna exactamente esa obligación —*«publicar
desenlaces (qué se encargó, qué salió, dónde está la evidencia); nunca ceder la
autoridad del estado en curso»*— y hoy sus desenlaces viven solo en su diario y
en etiquetas de GitHub. Este ADR hace la evaluación y decide, con ella, dónde
arranca la memoria común **sin comprar nada** y qué tiene que publicar el motor.

**2. ¿Qué NO va a garantizar esto?**

- **No elige la herramienta definitiva.** Graphiti, Obsidian, Basic Memory o
  cualquier otra siguen siendo candidatas para después; este ADR decide dónde
  arranca la memoria con lo que ya existe, que es lo que ADR-160 pide que se
  evalúe primero.
- **No toca la memoria propia de Sirius ni Sirius 0.2.** D6 y EV-018 las dejan
  aparte, y aparte siguen.
- **No resuelve T-6** (qué del repositorio privado puede salir hacia las IAs
  externas) más allá de declararla y de exigir que la protección sea mecánica.
- **No da permiso de escritura general a ninguna IA** (R10). El mecanismo de
  escritura es T-4 y se decide con la evaluación delante, no antes.
- **No promete por sí solo reducir el gasto de las sesiones interactivas**: eso
  exige que las sesiones lean la vista barata, y ese cambio de conducta se
  ordena en `AGENTS.md`, que es un acto aparte.

**3. Criterio de parada (escrito ANTES de ver resultados).**

- **(a)** Si el repositorio más el diario del motor cumplen R1–R14 salvo huecos
  que se cierran **generando** vistas con un guion y una prueba, la memoria común
  arranca sobre el repositorio y **no se propone nada nuevo**.
- **(b)** Si algún requisito de disponibilidad (R1), supervivencia (R3) o
  independencia de proveedor (R13) **no lo cumple ninguna pieza existente**, se
  para y se declara: ahí sí hace falta algo nuevo, y se lista qué, sin elegirlo.
- **(c)** Si publicar desenlaces del motor exigiera cambiar permisos o escribir
  en `.github/**` desde la automatización (ADR-002), se declara la mano humana
  necesaria en vez de sortearla.
- **(d)** Ninguna afirmación sobre una pieza sin `[V]` o `[H]`. Una búsqueda
  vacía por nombre **no** prueba ausencia funcional (lección de la propuesta
  §6.1).
- **(e)** Si la evaluación obligara a leer entero más de un documento por pieza
  para responder un requisito, ese requisito se responde con `[H]` y se dice:
  este ADR no puede ser él mismo un ejemplo del gasto que viene a reducir.

**4. ¿Qué haría imposible el error más probable, en vez de improbable?** El error
más probable ya ocurrió en esta misma sesión: proponer una vista **curada** —un
mapa escrito a mano— que se queda vieja con la siguiente decisión. Lo hace
imposible una regla, no un recordatorio: **toda vista de la memoria común se
genera con un guion que tiene prueba**, de modo que un ADR sin resumen, un
desenlace sin publicar o un índice desactualizado rompan CI. Lo que no se puede
hacer imposible desde aquí: que una IA externa lea la vista y decida releer el
corpus igualmente; eso es conducta, y se ordena en `AGENTS.md`.

## Evaluación funcional (T-5)

Tres piezas, catorce requisitos. `[V]` = comprobado en el repositorio en esta
rama; `[H]` = hipótesis o dato que solo el propietario puede confirmar.

### El hallazgo que va primero

**El repositorio es PÚBLICO** `[V, API de la plataforma: visibility=public]`. La
propuesta §6.3 (R9) y la decisión pendiente T-6 hablan de *«qué del repositorio
**privado** puede reflejarse en la memoria común y llegar a las IAs externas»*.
Hoy esa frontera no existe: todo `docs/`, todos los ADR, el contrato y el diario
del motor son legibles por cualquiera sin credenciales. Este ADR **no cambia la
visibilidad** —es decisión del propietario— pero tiene dos consecuencias que
sí le tocan: si es intencionado, cualquier IA lee la memoria común por una URL
sin configurar nada; si no lo es, hay que cerrarlo antes de seguir, y T-6
vuelve a ser real. La guía del final lo pone como primer paso.

### Pieza 1 — el repositorio (`main`)

| Req. | Cumple | Evidencia |
|---|---|---|
| R1 disponible con el PC apagado | **Sí** | Está en GitHub `[V]` |
| R2 leen/escriben las IAs y el motor | **Parcial** | Claude Code lee y escribe `[V, esta sesión]`; el revisor Codex del ciclo lee `[V, review-sirius-work.yml]`; el motor escribe por PR y por su rama `[V]`. Las sesiones de Codex y de ChatGPT del propietario: `[H]`, lo confirma él |
| R3 sobrevive a dejar una IA | **Sí** | Nada vive en el historial de un proveedor: todo está en git `[V]` |
| R4 origen y fecha por elemento | **Parcial** | Los 165 ADR llevan `Fecha` `[V]`; de 36 documentos en `evolution/` e `implementation/`, **14 no declaran fecha** en cabecera, entre ellos `PLAN.md` y `SIRIUS_AI_CORE_AND_MODEL_STRATEGY.md` `[V]` |
| R5 caducidad declarada | **Solo en `docs/investigaciones/`** | Campo `caduca_con` con prueba que lo exige (4 casos) `[V]`. ADR y demás documentos: sin caducidad |
| R6 exploración ≠ decisión | **Sí** | Contrato línea 147: *«ausencia de señales no es aprobación»* `[V]`; y el mecanismo real es que nada entra en `main` sin PR fusionada por el propietario `[V]` |
| R7 regla de conflicto | **No** | `sirius_check_docs.py` comprueba rutas y citas, no contradicciones `[V]`. No hay regla escrita |
| R8 un dueño por dato | **Sí, por convención** | Las citas por `fichero:línea` son la práctica del repositorio `[V]`; no hay comprobación de copias |
| R9 frontera de confidencialidad | **No existe** | Repositorio público `[V]`. Ver el hallazgo |
| R10 sin permisos generales | **Sí** | Tokens por workflow, `.claude/settings.json` con denegaciones `[V]` |
| R11 «qué sabíamos y cuándo» | **Sí** | `git log` `[V]` |
| R12 sin gasto nuevo | **Sí** | Nada que pagar `[V]` |
| R13 independiente de proveedor | **Sí** | Markdown, JSON y git `[V]` |
| R14 el propietario no escribe fichas | **Sí, y es lo caro** | 57 de los últimos 58 commits de ADR son de la identidad bot que usan las IAs `[V]`. Pero **ninguno de los 165 ADR tiene resumen** y el índice `docs/decisions/README.md` tiene **cero entradas** `[V]`: para saber qué se decidió hay que abrir ficheros de 15–80 KB |

### Pieza 2 — el diario del motor (rama `estado-del-motor`)

| Req. | Cumple | Evidencia |
|---|---|---|
| R1, R3, R11, R12, R13 | **Sí** | Rama de GitHub, JSONL append-only con `checksum_sha256` por entrada `[V]` |
| R2 | **Escribe el motor; leen quienes lean el repositorio** | `reflejar-desenlace.yml` la escribe tras cada cambio de etiqueta del ciclo `[V, ADR-137]` |
| R4 | **Sí** | Cada entrada lleva `recorded_at`, `aggregate_id` y `contexto_origen` `[V]` |
| **§6.2 «publicar desenlaces»** | **Los registra; no los publica** | 451 entradas tipadas —`work_item_delivered` 46, `work_item_failed_safely` 10, `work_item_escalated` 7…— y el `diagnostico` lleva la URL del run `[V]`. Pero son **3,6 MB de JSON sin ninguna vista**: ni `sirius-motor` ni ningún otro guion imprime «qué se encargó, qué salió, dónde está la evidencia» de forma legible `[V, entry points de pyproject]` |
| R5, R6, R7 | No aplican / no hay | Es estado, no conocimiento; su regla de autoridad está escrita: *manda el motor* |

### Pieza 3 — la memoria del producto (SQLite, en el equipo del propietario)

**No es candidata a lugar** —falla R1 por diseño, y D6 la deja aparte a propósito
`[V, ADR-083]`—, pero **sí es fuente de dos patrones** que las otras piezas no
tienen: origen consultable por dato (`GetMemoryOriginUseCase`,
`GetDecisionOriginUseCase`) y detección determinista de conflictos de
precedencia (`DetectPrecedenceConflictsUseCase`) `[V, src/sirius]`.

### Lo que dice la evaluación, en tres frases

1. **El repositorio más el diario ya cumplen R1, R3, R10, R11, R12 y R13 sin
   hacer nada**, que son justo los requisitos que descartarían soluciones. Se
   cumple el criterio de parada **(a)**: no hace falta nada nuevo para arrancar.
2. **Lo que falla no es dónde está el conocimiento, sino que nadie lo puede
   consultar barato**: cero resúmenes, cero índice, cero vista del diario. Es la
   causa directa del gasto que el propietario sufre.
3. **Los huecos reales son cuatro y se cierran generando, no curando**: una
   vista de decisiones, una vista de desenlaces, fechas en los documentos que no
   la tienen, y una regla de conflicto escrita.

## Decisión

1. **La memoria común arranca sobre lo que ya existe: `main` para el
   conocimiento y `estado-del-motor` para los desenlaces.** No se elige ni se
   instala herramienta alguna. Se cumple el criterio (a) de la nota de arranque.
2. **Toda vista de la memoria común se genera; nunca se cura.** Un guion con
   prueba produce las vistas, y CI falla si una está desactualizada. Es la regla
   de la pregunta 4 de la nota de arranque, y la que hace imposible el «mapa»
   que envejece.
3. **El punto de entrada de cualquier IA es un solo fichero en la raíz de
   `main`: `MEMORIA.md`.** Lo genera `uv run sirius-memoria conocimiento` a
   partir del árbol —sin reloj, sin red, sin `git log`—, se confirma en cada PR
   que cambie lo que refleja, y una prueba de Quality falla si el fichero
   confirmado no coincide con lo que el generador produce. Vive en `main` y no
   en la rama del motor porque **es lo primero que tiene que leer una IA al
   entrar**, y una IA entra por `main`: un fichero en otra rama no es «lo
   primero», es una búsqueda más. (Esto corrige la primera versión de este
   ADR, que lo ponía en `estado-del-motor`.)
4. **Los desenlaces del motor se publican en `estado-del-motor:DESENLACES.md`**,
   escrito por `reflejar-desenlace.yml` tras cada reflejo con
   `uv run sirius-memoria desenlaces`, a partir de `diario.jsonl` y
   `diario-despacho.jsonl`. Es la obligación de la propuesta §6.2 —*qué se
   encargó, qué salió, dónde está la evidencia*— cumplida, y `MEMORIA.md` la
   enlaza. Van separadas porque cambian por cauces distintos: el conocimiento
   por PR fusionada; los desenlaces, solos, sin PR (ADR-083, ADR-137).
5. **Qué contiene `MEMORIA.md`**, todo generado:
   - **Decisiones**: una fila por ADR —número, fecha, estado, título y un
     resumen **extraído** del primer párrafo de su sección `## Decisión`—, de
     la más reciente a la más antigua. No se añade ningún campo nuevo a la
     plantilla ni se redactan 165 resúmenes: el resumen es lo que el propio ADR
     dice que decidió, tal cual está escrito. Si eso sale pobre en algún ADR, se
     arregla en ese ADR, no en la vista.
   - **Registros con estado**: los bloques del motor y los defectos, con su
     estado, leídos de sus registros YAML.
   - **Investigaciones**: fecha, estado y de qué dependen para caducar.
   - **Documentos**: cada documento de `docs/` y de la raíz, con su título y la
     fecha que **declara** en cabecera; el que no la declara sale como «sin
     fecha declarada». La vista no data nada por su cuenta (R4, R8).
   - **Las reglas de lectura**: dónde están los desenlaces, la regla de
     conflicto y dónde están las prohibiciones (`AGENTS.md`), sin copiarlas.
6. **T-4 queda resuelta por lo que ya existe.** Las IAs escriben conocimiento
   **por PR que fusiona el propietario** —eso es «propuesta más confirmación», y
   ya cumple R6 y R10—; el motor escribe su diario **directamente**, porque es
   suyo; las vistas se derivan de ambos. No se crea un mecanismo nuevo.
7. **Regla de conflicto (R7), escrita ahora:** si el diario del motor y
   cualquier documento discrepan sobre un trabajo, **manda el diario**; si dos
   documentos discrepan entre sí, manda el más reciente **fusionado**. La vista
   no elige por su cuenta: enuncia la regla.
8. **`AGENTS.md` cambia una regla, en esta misma PR**: lo primero que lee
   cualquier IA, antes de responder y antes de modificar, es `MEMORIA.md`; desde
   ahí, solo lo que la tarea necesite. El contrato entero se sigue leyendo
   cuando la tarea toca automatización. Sin este cambio la vista es un fichero
   más; con él, es el ahorro.
9. **T-6 queda cerrada por decisión del propietario, no por omisión.** El
   repositorio es público **a propósito**: los minutos de GitHub Actions que el
   ciclo consume solo salen gratis en un repositorio público, y pagarlos no es
   una opción (propietario, 11-09-2026). En consecuencia, no hay frontera de
   confidencialidad que construir: **lo que entra en el repositorio es público,
   y quien lo escribe lo sabe**. R9 se cumple por esa regla y no por un filtro.
10. **Qué IAs leen la memoria: cualquiera.** El propietario lo ha dicho igual
    de claro: da igual qué IA entre; la regla es que **toda IA que entre lee
    `MEMORIA.md` primero**. Con el repositorio público, cualquier IA la lee por
    su URL sin configurar nada. No se pregunta más por esto.

**Lo que este ADR deja fuera a propósito:** la herramienta definitiva; Sirius
0.2 y la memoria del producto; cualquier permiso de escritura nuevo para una
IA; y datar a mano los documentos que no declaran fecha (la vista los señala;
quien los toque, los data).

## Nota de arranque del generador (publicada ANTES del primer commit de código)

La decisión de arriba se ejecuta en esta misma PR, no en tres. El propietario
lo pidió con estas palabras: *«quiero terminar, no seguir acumulando parches ni
documentos»*. Estas cuatro respuestas quedan escritas antes de la primera
línea de código.

**1. ¿Dónde vive el fallo y dónde va el arreglo?** El fallo: no existe ninguna
vista consultable del conocimiento ni de los desenlaces (evaluación de arriba).
El arreglo, pieza a pieza:

| Pieza | Dónde | Qué hace |
|---|---|---|
| Generador | `src/sirius_engine/memoria.py` | Funciones puras: lee el árbol y devuelve texto. Sin reloj, sin red, sin git |
| Comando | `src/sirius_engine/memoria_cli.py`, entrada `sirius-memoria` | `conocimiento` escribe `MEMORIA.md` (o `--comprobar`); `desenlaces` escribe la vista del diario |
| La vista | `MEMORIA.md` en la raíz de `main` | Generada y confirmada |
| La guardia | `tests/engine/test_memoria.py` | Falla si `MEMORIA.md` no coincide con lo generado; y las pruebas del generador con árboles de prueba |
| Los desenlaces | paso nuevo en `reflejar-desenlace.yml` | Escribe `DESENLACES.md` en la rama del motor tras cada reflejo, en el mismo grupo de concurrencia |
| La conducta | `AGENTS.md` | `MEMORIA.md` pasa a ser la primera lectura |

**2. ¿Qué NO va a garantizar esto?**

- **No garantiza que una IA la lea.** `AGENTS.md` lo ordena; nada lo fuerza.
- **No resume con criterio.** Extrae el primer párrafo de cada `## Decisión`
  tal cual está escrito. Un ADR mal escrito da un resumen malo, y eso se ve.
- **No data documentos.** El que no declara fecha sale como «sin fecha
  declarada», y son muchos (se cuenta en la comprobación).
- **No mete los desenlaces en `main`.** Cambian sin PR; viven en su rama y
  `MEMORIA.md` los enlaza. Una IA que quiera el estado en curso del motor sigue
  teniendo que ir a la rama.
- **No toca Sirius, la memoria del producto, los permisos, ni ningún workflow
  aparte de `reflejar-desenlace.yml`.**

**3. Criterio de parada (escrito ANTES de ver resultados).**

- **(a)** Si el generador necesitara reloj, red o `git log` para producir la
  vista de conocimiento, se para: una vista que cambia sin que cambie el árbol
  no puede guardarse con una prueba, y sin prueba es un mapa que envejece.
- **(b)** Si la prueba de frescura **no falla** contra una mutación —cambiar el
  título de un ADR sin regenerar; editar `MEMORIA.md` a mano—, no se entrega.
- **(c)** Si `MEMORIA.md` supera **120 KB**, se recorta (resúmenes más cortos o
  una sección fuera): el objetivo es leerla entera de una vez, y un fichero que
  no se lee entero vuelve a ser un corpus.
- **(d)** Si cablear `DESENLACES.md` exigiera tocar los cuatro workflows
  críticos, ampliar permisos o salir del grupo `motor-sirius`, se para
  (ADR-002, ADR-137: puramente aditivo o nada).
- **(e)** Si `tests/automation/test_serializacion_del_motor.py` rechazara el
  cableado, se corrige el cableado, nunca la prueba.

**4. ¿Qué haría imposible el error más probable?** El error más probable es que
la vista se quede vieja. Lo hace imposible la prueba de frescura dentro del
`pytest` de Quality: **ninguna PR entra en `main` con `MEMORIA.md`
desactualizada**, y el mensaje de fallo dice el comando exacto que hay que
ejecutar. El segundo error probable, editarla a mano, cae en la misma prueba.
Lo que no se puede hacer imposible desde aquí: que una IA no la lea.

## Comprobación que la sostiene

Todo `[V]`, ejecutado en esta rama el 11-09-2026 sobre el árbol de esta PR.

**Lo que se generó.**

- `uv run sirius-memoria conocimiento` escribe `MEMORIA.md`: **92,625 bytes**
  (criterio (c): por debajo de 120 KB), con 165 decisiones, 20 bloques del
  motor (17 cerrados, 2 pendientes, 1 fuera de alcance), 32 defectos (todos
  cerrados), 7 investigaciones y 127 documentos, de los que **84 no declaran
  fecha** con la regla del generador (una fecha en una línea de las veinte
  primeras que hable de «fecha» o «actualización», en ISO o en DD-MM-AAAA). La
  cifra de «14 de 36» de la fila R4 de la evaluación salió de otra regla, más
  laxa (cualquier fecha en la cabecera); la del generador es la que cuenta desde
  ahora, porque es la que se puede repetir.
- `uv run sirius-memoria desenlaces --diario diario.jsonl` sobre el diario real
  de `estado-del-motor` (451 sucesos, el último el 08-09-2026 01:06 UTC) escribe
  `DESENLACES.md` de 23.757 bytes con **76 encargos**: 46 `delivered`, 21
  `active`, 5 `failed_safely`, 4 `needs_decision`; cada uno con su incidencia
  enlazada (del diario de despacho cuando el resultado aún no la trae), la
  fusión y el run de evidencia cuando el diagnóstico lo cita. Los 21 `active`
  son encargos del 25 al 28 de agosto que el diario nunca vio avanzar: la vista
  no lo esconde, porque el diario manda.

**Criterio (a), solo el árbol.** `tests/engine/test_memoria.py::
test_el_generador_no_mira_el_reloj_ni_la_red_ni_git` inspecciona el código del
módulo: sin `datetime`, `subprocess`, `urllib`, `httpx`, `time.time` ni
`os.environ`. Dos generaciones seguidas del mismo árbol son idénticas.

**Criterio (b), la guardia falla contra la mutación.** Cuatro mutaciones, cada
una vista FALLAR y el árbol restaurado después:

| Mutación | Prueba | Resultado |
|---|---|---|
| Cambiar el título de `ADR-001` sin regenerar | `test_la_memoria_confirmada_en_este_arbol_esta_al_dia` | **Falla** con el mensaje que nombra `uv run sirius-memoria conocimiento` |
| Añadir una línea a mano a `MEMORIA.md` | la misma | **Falla** |
| Quitar el paso «Publicar la vista de desenlaces» del workflow | `test_el_reflejo_publica_la_vista_de_desenlaces_aunque_el_reflejo_falle` | **Falla**: «la vista existiría y nadie la escribiría» |
| Quitar la regla de `AGENTS.md` | `test_agents_ordena_leer_la_memoria_primero` | **Falla** |

**Criterios (d) y (e), el cableado.** El paso nuevo de `reflejar-desenlace.yml`
es aditivo: mismo grupo `motor-sirius`, mismos permisos, `if: always()`, antes
de «Confirmar el diario», que ya confirma cualquier fichero del worktree.
`tests/automation/test_serializacion_del_motor.py` deriva `sirius-memoria` de
`[project.scripts]` y lo acepta sin tocar la prueba.

**Las validaciones.** `ruff format --check`, `ruff check`, `mypy src tests`
(588 ficheros) en verde; `tests/engine/test_memoria.py` (18 pruebas) más las
de serialización del motor y las de prompts de rol: 78 en verde, 11 saltadas
por su propia condición. La suite completa se corrió antes del push; su
resultado está en la descripción de la PR.

**Lo que NO se ha comprobado.** Que `reflejar-desenlace.yml` escriba
`DESENLACES.md` en la rama real: eso solo ocurre tras la fusión, en la primera
pasada (`workflow_dispatch` la adelanta). Si esa pasada no deja el fichero en
`estado-del-motor`, este ADR no está cumplido y hay que mirar el run.
