# ADR-168 — Listar por vigencia cuando la pregunta declara un intervalo y la busqueda lexica no tiene de donde partir

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: la fusión de esta PR por el propietario.
- Esta ficha es además la **nota de arranque** de la rama (ADR-001, skill
  `disciplina-evidencia`): las cuatro preguntas y el criterio de parada de
  abajo se escribieron y se publicaron **antes del primer commit de código**
  (commit de esta ficha sola, anterior a cualquier cambio en `src/`).

## Contexto y problema

Hueco **H1 de ADR-148**, la incidencia #577 (`WI-20260908-H1`). Es el mayor
de los que quedan: cinco de las siete ocurrencias que el banco sigue sin
recuperar.

El caso es `B04-CA-22`, «¿Qué decisiones eran válidas entre enero y marzo?»,
con `cardinalidad=EXHAUSTIVA` y `tiempo_objetivo=2026-01-10T00:00:00Z/
2026-03-20T00:00:00Z`. Espera seis decisiones (`DEC-001`, `DEC-005`,
`DEC-009`, `DEC-011`, `DEC-014`, `DEC-015`) y hoy entra una: `DEC-014`, la
única cuyo texto —«Se habilita el turno reducido de enero»— comparte una
palabra con la pregunta. Entra por accidente léxico, no porque el motor
entienda la vigencia.

La causa está en la generación de candidatas.
`CandidatoLexicoEstructurado.candidatas`
(`src/sirius/adapters/persistence/staged_engine_candidate.py`) parte
**siempre** de `terminos_significativos(consulta)` y devuelve `()` si no hay
ninguno; las cuatro etapas de expansión consultan el puerto por clave, por
término léxico, por prefijo de sujeto o por historial. Una pregunta cuyo
único criterio es un intervalo de vigencia no le da ninguna palabra útil: no
es que ordene mal, es que **no hay camino de entrada**.

### La línea base, medida al empezar y no heredada

Sobre `6371d4c` (`main` con H2/ADR-166 dentro), con
`uv run python scripts/diagnosticar_busqueda_del_banco.py`, las cuatro
configuraciones:

| Configuración | Exactas | De más | Hallados | Críticas perdidas |
|---|---|---|---|---|
| sin banderas | 0/47 | 487 | 72/81 | 0 |
| `--ejes` | 0/47 | 421 | 71/81 | 0 |
| `--peticion` | **17/47** | **162** | **74/81** | **0** |
| `--ejes --peticion` | 21/47 | 144 | 74/81 | 0 |

Coincide con lo que la incidencia declara como suelo y con lo que ADR-166
publica. `--peticion` es el suelo de referencia.

### Dos cosas que el árbol desmiente de la incidencia

La incidencia manda leer el árbol cuando discrepe (deudas 19 y 21), así que
las dos diferencias se registran aquí **antes** de construir:

1. **«El intervalo llega en la `Peticion`» no es cierto hoy.** ADR-164 puso
   la palanca 1 en `main`, pero el intervalo se colapsa a su extremo final
   una línea antes de construir la `Peticion`, en los dos caminos:
   `_instante` (`tests/acceptance/staged_engine_case_translation.py`,
   «Un caso puede declarar su instante objetivo como un intervalo; se toma
   el extremo final») y `_tiempo_objetivo`
   (`src/sirius/adapters/ollama_query_intent_classifier.py`, «Un intervalo se
   resuelve por su extremo final»). `VentanaTemporal`
   (`src/sirius/domain/staged_engine_contracts.py`) solo tiene
   `tiempo_objetivo` y `corte_de_registro`: no hay campo donde el extremo
   inicial pudiera viajar. La información **llega al intérprete** y se tira
   ahí; conservarla es, por tanto, parte de la vía y no un encargo aparte.
2. **`DEC-001` no puede entrar en este encargo, y no por el hueco H1.** Su
   proyecto en el corpus es `LISTA-CERRADA-AB`, distinto del ámbito del caso
   (`PRJ-BETA`), y su eje de ámbito es `MULTI_PROYECTO_CERRADO` **sin
   miembros resueltos**: el arnés lo declara así a propósito
   (`_ejes_declarados`, `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`,
   «el corpus portado no declara la membresía de listas cerradas… `G4` la
   trata como lista sin miembros y la descarta»). Así que `G4` lo descarta
   con ejes (`lista cerrada sin miembros resueltos`) y sin ejes
   (`peticion.ambito.autoriza(project_id)` es falso). Recuperarlo exigiría
   tocar el ámbito o el corpus, las dos cosas fuera de alcance.

## Criterio de parada (escrito ANTES de decidir)

Predicción publicada antes de medir nada del cambio:

- **`--peticion`: `74/81` → `78/81` hallados**, no `79/81`. Las cinco
  ocurrencias de H1 son `DEC-001`, `DEC-005`, `DEC-009`, `DEC-011` y
  `DEC-015`; cuatro entran por vigencia y `DEC-001` no puede entrar por la
  razón registrada arriba, que es de ámbito (`G4`) y no de este hueco. Si
  midiendo resulta que sí entra, se dice y se corrige esta ficha.
- **`DEC-014` sigue entrando**, y se comprueba si pasa a entrar también por
  vigencia además de por el accidente léxico.
- **Exactas: no bajan de `17/47`.** Críticas perdidas: **0**, fijadas con
  prueba y no solo medidas.
- **`de más` sin listón**, por decisión de la incidencia: la vía enumera y
  quien cierra el ruido es la palanca 3. Se transcribe antes y después y, si
  sube, se razona si cae dentro de lo que el filtro puede quitar.
- **Solo `B04-CA-22` cambia de resultado.** Cualquier otro caso que cambie se
  explica uno a uno.
- **Se para** si las exactas bajan, si aparece una crítica perdida, o si el
  arreglo obliga a decidir algo de producto, ámbito o corpus. No se ajusta el
  criterio al resultado.

## Las cuatro preguntas de la nota de arranque

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en la
   **generación de candidatas** (nadie pregunta nunca por vigencia) y en la
   **traducción del tiempo** (el extremo inicial se tira). El arreglo va en
   los tres sitios que pueden observarlo: el contrato conserva el intervalo,
   el puerto aprende a consultar por ventana de vigencia, y la fuente de
   candidatas aporta esa señal. Ninguno de los tres podría observarse desde
   otro sitio: las puertas ya honran el tiempo (`G8`) sobre candidatas que
   nunca llegan, y ordenar mejor no crea un camino de entrada.
2. **¿Qué NO garantiza?** No recupera `DEC-001` (ámbito, no vigencia). No
   baja el ruido: lo sube. No abre `category_matching_enabled`. No persiste
   `valid_from`/`valid_to` en el esquema (palanca 2, cerrada sin fusionar en
   #572), así que en el sustrato real la vía **degrada** a lo que Sirius sí
   guarda: `created_at` y el estado vigente. No infiere «tema» de la
   pregunta: no hay lista de temas y fabricarla sería ajustar el criterio al
   caso.
3. **Criterio de parada:** el de arriba, publicado antes de medir.
4. **¿Qué haría el fallo imposible en vez de improbable?** Que el sustrato
   persistiera la ventana de vigencia por ítem; eso es la palanca 2, medida y
   descartada por no pagar (#572), y no se reabre aquí. Lo que sí queda
   imposible es la regresión concreta: las cuatro pruebas del encargo fijan
   la vía, la permanencia de `DEC-014`, la no interferencia con una pregunta
   con tema y las 0 omisiones críticas.

## Opciones consideradas

## Decisión

## Comprobación que la sostiene

## Consecuencias

## Alternativas descartadas y por qué
