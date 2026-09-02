# ADR-126 — M18b: la señal de criticidad como dato propio de cada recuerdo y decisión

- Estado: PROPUESTO
- Fecha: 2026-09-02
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

Esta es también la nota de arranque de la rama `feature/m18b-criticidad-senal`
(incidencia #510, Work ID WI-20260902-225525), publicada antes del primer
cambio de código, con las cuatro preguntas de la disciplina de evidencia
(ADR-001).

## Contexto y problema

`docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md`, sección
«Decisión del propietario y plan (02-09-2026)», registró que producción
pierde 10 críticas frente a 4 del laboratorio porque el laboratorio deriva la
categoría de la criticidad y producción etiqueta por tema (ADR-116): ni el
índice de categoría ni la regla de rescate RF-25/RF-26 ven lo crítico. El
propietario decidió separar las dos señales — `category` (de qué va) y
`criticality` (cuánto importa) — y trazó un plan de cuatro encargos en serie.
M18 se partió en M18a (porte mecánico del filtro fiel al laboratorio, ya
fusionado en `main` vía PR #509) y M18b, este encargo: **solo** la señal de
criticidad como dato propio de `Memory`/`Decision`, calcada del patrón que
`category` ya estableció (M8, #448) — dominio, persistencia, puertos,
repositorios SQLite, caso de uso manual y el cargador del banco de evidencia.
M18b no cablea la señal a nada todavía.

## Nota de arranque (cuatro preguntas, ADR-001)

**1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
observar el fallo que arregla?**

No hay un fallo que reproducir en este encargo: es una carencia de modelo
(`Memory`/`Decision` no tienen forma de guardar "esto es crítico" con
independencia de su tema). El arreglo vive exactamente donde vive la
carencia — dominio (`sirius.domain.memory`/`decision`), persistencia
(`models.py`, migración Alembic), puertos (`MemoryRepository`/
`DecisionRepository`) y el caso de uso manual (`SetCriticalityUseCase`) — el
mismo lugar, capa por capa, donde M8 puso `category`/`category_locked`. Sí
puede observarse: cada capa nueva tiene su propia prueba unitaria/integración
que la ejercita directamente (round-trip en SQLite, caso de uso, migración
upgrade/downgrade), sin depender de que algo aguas abajo la consuma — porque,
deliberadamente, nada aguas abajo la consume todavía.

**2. ¿Qué NO va a garantizar esto?**

- No va a cambiar ninguna métrica del banco de 47 casos: nada consume la
  señal (ni el índice de categoría, ni RF-25/RF-26, ni la siembra, ni la
  interfaz) — eso es M19/M20/M21, en ese orden, después de este encargo.
- No garantiza que la criticidad puesta en el banco sea "correcta" en ningún
  sentido semántico: el cargador solo la copia de `criticidad.nivel` del
  fixture, sin juicio propio.
- No introduce clasificación automática: `criticality` solo la fija el
  usuario (o, en este encargo, el cargador del banco en su papel de
  "usuario" que ya conoce el nivel); M21 es quien hará que Sirius la
  proponga.
- No toca `category`, su vocabulario, `category_locked` ni la semántica D7.

**3. Criterio de parada (decidido antes de ver ningún resultado)**

Predicción escrita antes de construir: **ningún cambio** en
`uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`
respecto a hoy (7/47 aciertos exactos, 285 elementos de más, 9 omisiones
críticas NO_ENTRO, cobertura 62/81) ni en
`uv run python scripts/medir_variantes_de_criticidad.py` (hoy=9 / A=3 / B=3),
porque nada consume todavía la señal. Si cualquiera de las dos mediciones
cambia, o si dos rondas seguidas de revisión encuentran defectos de la misma
familia, se para de insistir por ese camino, se busca la causa raíz y no se
sigue parcheando (regla de las dos rondas, ADR-001).

**4. ¿Qué hace esto imposible, en vez de improbable?**

Que un valor de `criticality` corrupto o desconocido en la base de datos se
traduzca, en silencio, en un nivel de criticidad inventado: los repositorios
SQLite validan el valor leído contra el enum `Criticality` al cargarlo y
fallan explícitamente (`ValueError`) si no es uno de los dos valores
válidos, en vez de mapearlo a `None` o a un valor por defecto. No hace
imposible una clasificación incorrecta del *contenido* (eso no lo decide
esta capa), pero sí hace imposible que ese error pase desapercibido como un
dato válido.

## Criterio de parada (escrito ANTES de decidir)

Ver punto 3 de la nota de arranque, arriba: ningún cambio en las cuatro
métricas del banco de 47 casos ni en `medir_variantes_de_criticidad.py`. Ese
resultado, medido después del cambio, se registra en «Comprobación que la
sostiene».

## Opciones consideradas

1. **Una sola señal** (la que ya existía): seguir derivando el rescate
   crítico de `category`. Descartada por el propio propietario — es la causa
   raíz que la evidencia diagnosticó (el laboratorio deriva la categoría de
   la criticidad; producción no puede replicar eso sin inventar una
   categoría ficticia "crítico").
2. **Dos señales, con `criticality` calculada** (ej. una propiedad derivada
   de reglas sobre el contenido, sin persistir). Descartada: no hay guardado
   explícito del usuario ni margen para que M21 (Sirius propone, el usuario
   confirma) tenga algo que confirmar — necesita persistencia propia, igual
   que `category`.
3. **Dos señales, `criticality` persistida y calcada de `category`**
   (elegida): mismo patrón en las cinco capas que ya demostró funcionar con
   `category` (M8, #448), con la única diferencia deliberada de que
   `criticality` es un enum cerrado de dos valores (más `None`), no una
   cadena libre, y no tiene análogo de `category_locked` ni de
   `set_category`/`TagCategoryUseCase` condicional porque este encargo no
   introduce clasificación automática.

## Decisión

**Decisión 1 — dos señales, no una** (cita literal de la evidencia,
`docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md`, sección
«Decisión del propietario y plan»): «`category` sigue siendo *de qué va* un
item (tema; D7 la necesita). Cada `Memory` y `Decision` gana `criticality:
CRITICO | IMPORTANTE | None`, el concepto del propio canon
(`criticidad.nivel`). El índice de categoría, la regla de rescate RF-25/RF-26
y la siembra pasan a mirar la criticidad, no el tema.» Este encargo (M18b)
implementa la mitad de esa decisión que le corresponde: la señal, sin
cablearla a nada.

**Decisión 2 — la siembra entra** (cita literal, misma sección): «Su
precondición documentada (ampliar el banco o retirarla) se resuelve así: el
propietario la porta **sabiendo** que el banco no puede validarla de forma
independiente (solo B04-CA-34 y otro caso la ejercitan); su aceptación es la
medición de críticas perdidas (3 → 0) y el uso real del propietario, no una
prueba del banco. Queda escrito para que nadie lo lea después como un
olvido.» Esta decisión pertenece a M20; se registra aquí, junto a M18b,
porque ambas nacieron de la misma sesión y del mismo documento, y porque
M18b es quien primero deja la puerta (la señal) por la que M20 tendrá que
pasar.

**Plan, un encargo detrás de otro (sin paralelo), con la predicción escrita
antes de construir** (tabla literal de la evidencia, misma sección):

| Encargo | Qué | Predicción sobre el banco de 47 (Ollama real) |
|---|---|---|
| M18 (M18a + M18b) | Señal de criticidad en dominio/persistencia/caso de uso + filtro fiel al laboratorio portado a `main` | Sin cambio en lo recuperado: 7/47, 285, 9 NO_ENTRO, 62/81 con el doble |
| M19 | Índice y rescate por criticidad | Críticas perdidas **10 → 3**; TIRADO **1 → 0** |
| M20 | Siembra en contexto | Críticas perdidas **3 → 0** |
| M21 | Sirius propone la criticidad, el usuario confirma | Que funcione con los recuerdos reales del propietario, no solo con el banco |

Si tras M19 no salen 3, o tras M20 no sale 0, se para y se busca la raíz
(regla de las dos rondas, ADR-001).

## Comprobación que la sostiene

[Se completa al terminar la implementación, con los comandos y resultados
reales.]

## Consecuencias

- `Memory` y `Decision` ganan un campo `criticality: Criticality | None`,
  simétrico a `category`/`category_locked` mecánicamente pero más simple
  (sin candado, sin escritura condicional): la criticidad la fija
  incondicionalmente quien la fija (usuario o cargador del banco), hasta que
  M21 introduzca una propuesta automática.
- Los ~18-19 dobles de prueba que implementan `MemoryRepository`/
  `DecisionRepository` (`Protocol`) ganan los tres métodos nuevos
  (`set_user_criticality`, `list_current_memories_by_criticality`,
  `list_current_decisions_by_criticality`), casi siempre como una aserción
  de "no usado" — trabajo mecánico, igual que hizo M8 con `category`.
- El cargador del banco (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`)
  pasa a leer `criticidad.nivel` (y solo eso, nunca `razon_segura`) para
  fijar la criticidad de cada `Memory`/`Decision` real que crea, sin que
  ninguna métrica del banco cambie, porque nada la consume todavía.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba.
