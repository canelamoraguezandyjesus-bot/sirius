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
   prueba produce las vistas, y CI falla si una está desactualizada o si una
   pieza nueva no trae lo que la vista necesita. Es la regla de la pregunta 4 de
   la nota de arranque, y la que hace imposible el «mapa» que envejece.
3. **Las vistas viven en `estado-del-motor`, escritas por el motor.** Es la rama
   donde el motor ya tiene permiso de escritura (ADR-083, ADR-137) y la única
   forma de que las vistas estén siempre frescas sin que la automatización
   escriba en `main` (ADR-002). El punto de entrada de cualquier IA pasa a ser
   **un solo fichero**: `estado-del-motor:MEMORIA.md`.
4. **Qué contiene `MEMORIA.md`**, generado:
   - **Decisiones**: una línea por ADR —número, fecha, estado, título, resumen—
     y las decisiones EV vigentes. Exige un campo `Resumen` en cada ADR: se añade
     a la plantilla y a la skill `adr`, y se rellena en los 165 existentes
     (borrador generado de la primera frase de cada Decisión, revisado).
   - **Desenlaces**: los últimos N encargos del diario, con clase, estado,
     desenlace, fecha y enlace a la evidencia. Es la fila del motor en §6.2,
     cumplida.
   - **Estado y visión**: enlaces a `STATUS.md`, `RECTOR.md` y a los documentos
     de dirección, con su fecha; **sin copiar su contenido** (R8).
5. **T-4 queda resuelta por lo que ya existe.** Las IAs escriben conocimiento
   **por PR que fusiona el propietario** —eso es «propuesta más confirmación», y
   ya cumple R6 y R10—; el motor escribe su diario **directamente**, porque es
   suyo; las vistas se derivan de ambos. No se crea un mecanismo nuevo.
6. **Regla de conflicto (R7), escrita ahora:** si el diario del motor y
   cualquier documento discrepan sobre un trabajo, **manda el diario**; si dos
   documentos discrepan entre sí, manda el más reciente **fusionado**, y la vista
   los marca como discrepantes en vez de elegir por su cuenta.
7. **`AGENTS.md` cambia una regla**: la lectura obligatoria pasa a ser
   `MEMORIA.md` y, desde ahí, solo lo que la tarea necesite. El contrato entero
   se lee cuando la tarea toca automatización, como ahora. Este cambio es lo que
   convierte la vista en ahorro; sin él, es un fichero más.
8. **T-6 no se decide aquí, porque su premisa no se cumple**: el repositorio es
   público. Se pone al propietario como primer paso de la guía.

**Lo que este ADR deja fuera a propósito:** la herramienta definitiva; Sirius
0.2 y la memoria del producto; la frontera de salida hasta que el propietario
decida la visibilidad; y cualquier permiso de escritura nuevo para una IA.

## Lo que viene después, en orden

- **PR siguiente (motor):** el generador `sirius-memoria` con sus pruebas, la
  vista de desenlaces, y `reflejar-desenlace.yml` escribiendo `MEMORIA.md` tras
  cada reflejo. Nota de arranque propia.
- **PR siguiente (documentos):** campo `Resumen` en plantilla y skill, los 165
  borradores para revisión, fechas en los 14 documentos sin ella, y la prueba
  que impide un ADR sin resumen.
- **PR siguiente (conducta):** la regla nueva de `AGENTS.md`.

## Lo que el propietario tiene que hacer

1. **Decidir si el repositorio debe ser público.** Compruébalo en
   `github.com/canelamoraguezandyjesus-bot/sirius` → *Settings* → *General* →
   abajo del todo, *Danger Zone* → *Change repository visibility*. Si es
   intencionado, dilo y T-6 queda cerrada por ausencia de frontera; si no,
   cámbialo a privado **antes** de la PR de conducta, porque entonces las IAs
   externas necesitarán acceso explícito.
2. **Decir qué IAs tuyas pueden leer GitHub** (R2): tu Codex de sesiones y tu
   ChatGPT. Con el repositorio público, ambas pueden leer `MEMORIA.md` por su URL
   sin configurar nada; con el repositorio privado, ChatGPT necesita el conector
   de GitHub y Codex el acceso al repositorio.
3. **Fusionar este ADR** si la decisión es la que quieres. La fusión es el «go»
   de la PR del motor, que arranca en el momento.
