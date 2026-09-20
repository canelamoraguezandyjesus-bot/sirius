# ADR-211 — Convertir en skills lo que ya costó averiguar dos veces, con una guarda que impida que se pudran

- Estado: APROBADO
- Fecha: 2026-09-20
- Aprobación: el propietario, al fusionar la PR de esta rama

## Contexto y problema

El propietario lo pidió el 20-09-2026: «tenemos si o sí q hacer q se creen
skills como en Hermes para no tener q buscar mil veces como hacer la misma
tarea o trabajo y poder aprender dia a dia de lo q hacemos y de cómo
trabajamos».

Lo que había: **dos** skills —`adr` y `disciplina-evidencia`—, ninguna prueba
que las mirara, y ninguna mención de ellas en `AGENTS.md` ni en `MEMORIA.md`.
Una sesión nueva no sabía que existían salvo que su herramienta se las
enseñara.

El fallo tiene dos caras y solo una se arregla escribiendo texto:

1. **Lo que se repite se vuelve a averiguar desde cero.** El conocimiento está
   repartido entre `AGENTS.md`, 210 ADR y las 21 fichas de
   `docs/audits/AUDITORIA_FORMA_DE_TRABAJO_2026-09.md`. Nadie carga 210 ADR.
2. **Un documento que nadie mantiene se pudre en silencio.** Está medido en
   esta casa: la ficha PROC-010 de esa misma auditoría encontró la base de
   conocimiento de `docs/operations/` **nueve versiones de contrato por
   detrás**, «sin dueño, resuelta por abandono: nadie la hace y nadie la lee».
   Una skill caducada es peor que ninguna, porque se cree.

Y una tercera, descubierta al ir a confirmar: **`.gitignore` descartaba las
skills nuevas**. La lista de admisión de `.claude/` nombraba `settings.json` y
dos ficheros de `commands/`, y nada más. Las dos que existían estaban
versionadas porque en su día se añadieron con `git add -f`. Un `git add`
normal de una skill nueva no añadía nada y no decía nada.

## Criterio de parada (escrito ANTES de decidir)

Publicado antes de elegir ningún candidato, en la adenda 3 de
`docs/audits/arranque-auditoria-forma-de-trabajo.md` (20-09-2026 15:09 UTC),
junto con las cuatro preguntas y las tres condiciones. Estado de sus cinco
filas al cerrar:

| # | Criterio | Qué pasó |
|---|---|---|
| 1 | Una skill que solo repita `AGENTS.md` se descarta | ninguna lo hace: `hablar-con-el-propietario` remite a sus diez reglas en vez de copiarlas |
| 2 | La guarda tiene que fallar al mutar cada regla | **nueve mutaciones, nueve cazadas**; la primera pasada cazó ocho y destapó un defecto real de la guarda (abajo) |
| 3 | Si pasan más de siete candidatos, entran los cinco de mayor fricción | pasaron cinco; no hizo falta recortar |
| 4 | La batería completa tiene que volver verde | verde |
| 5 | Si la cadena de esta sesión se alarga, la skill de la cadena ha fracasado | no se alargó: la guarda de skills corre en 0,19 s |

## Opciones consideradas

- **Dejarlo como está** y confiar en que cada sesión relea `AGENTS.md` y los
  ADR. Es lo que ya pasa, y es lo que el propietario pidió cambiar.
- **Escribir las skills y nada más.** Rápido, y con la vida media de la base de
  conocimiento de PROC-010.
- **Escribir las skills con una guarda fuera de ellas** que impida lo
  mecánico, indexarlas donde una sesión mira al abrir, y dejar escrito qué
  parte no puede comprobar ninguna prueba.
- **Generar las skills automáticamente de las fichas de la auditoría.** Una
  skill es un texto con juicio dentro; generarla de una ficha produce una
  ficha con otro nombre.

## Decisión

**La tercera.** Cinco skills nuevas, una guarda, y las dos puertas de entrada
de una sesión enterándose de que existen.

**Un candidato entra solo si cumple las tres condiciones a la vez**, fijadas
antes de mirar la lista: se repite con al menos dos ocurrencias fechadas,
tiene fricción medida (un número, una fecha o un defecto registrado), y la
decisión no es del propietario (ADR-204). Las cinco que pasaron:

| Skill | Se repite | Fricción medida |
|---|---|---|
| `cadena-de-comprobacion` | cada commit de cada sesión | la batería son 11 min 30 s; el comprobador de documentos rechazó tres veces la misma cita el 20-09 |
| `hablar-con-el-propietario` | 72 órdenes tecleadas entre el 13-07 y el 11-09 | los cinco disparadores fechados del hallazgo E-04; el menú de opciones rechazado siete veces |
| `obra-en-curso` | cuatro sesiones a la vez declaradas el 10-08 | una tarde entera en balde (#165), los dos ADR-016, y un choque real cazado el 20-09 |
| `registro-de-defectos` | siete entradas (H-204 a H-210) en una sola tanda | el pez que se muerde la cola de `cerrado`/`sha`; el caso perdido de #137 (PROC-016) |
| `crear-una-skill` | por construcción: es el bucle que el propietario pidió | nada decía hoy cuándo algo merece ser skill, y las dos que había no tenían guarda |

Se consideraron y **no** entraron: reconstruir contexto al abrir sesión (ya lo
hace `MEMORIA.md` sola desde ADR-171: sin fricción que ahorrar), medir
rendimiento (cabe en `disciplina-evidencia` y su cara conversacional está en
`hablar-con-el-propietario`) y llevar una PR a verde (ADR-205 acaba de cambiar
sus reglas; se mira cuando la forma nueva tenga dos ocurrencias).

**La guarda** vive en `tests/automation/test_skills.py`, fuera de los
documentos que vigila, porque un documento no puede observar su propia
podredumbre. Comprueba, por skill: que existe el `SKILL.md`, que el `name`
coincide con la carpeta, que la descripción supera un suelo y trae la frase que
dice **cuándo** cargarla, que declara sus límites en una sección «Qué NO hace»,
que toda ruta y todo `ADR-NNN` citados existen, que los enlaces a ficheros de
al lado resuelven, y que **`.gitignore` no las descarta**. Reutiliza el
extractor de citas medido de `tests/automation/test_citas_de_los_adr.py` en vez
de copiarlo.

**El índice**: `MEMORIA.md` gana la sección «Las skills», generada del árbol
como todo lo demás, con el nombre y la frase del «cuándo»; va antes del índice
de ADR, que es donde se lee. `AGENTS.md` gana la fila en la tabla de dónde
mirar y una sección corta con las dos direcciones del bucle.

## Comprobación que la sostiene

| Qué se afirma | Comando | Resultado |
|---|---|---|
| La guarda pasa sobre el árbol | `uv run --no-sync pytest tests/automation/test_skills.py -q` | 71 pruebas en verde, 0,19 s |
| La guarda no es vacua | mutación de sus nueve reglas en el árbol, una a una, restaurando desde copia | **9 de 9 cazadas**; árbol limpio al terminar |
| Las skills no rompen nada | `uv run --no-sync pytest` | pendiente de la pasada final sobre el árbol fusionado; la cifra se anota aquí antes de empujar |
| Formato, estilo y tipos | `ruff format --check .`, `ruff check .`, `mypy src tests` | limpio; 604 ficheros |
| Los documentos no tienen citas rotas | `sirius_check_docs.py` sobre los siete `SKILL.md`, `patrones.md`, `AGENTS.md` y `MEMORIA.md` | sin defectos |
| `MEMORIA.md` está al día | `uv run --no-sync sirius-memoria conocimiento` | regenerada en el mismo commit (ADR-171) |

**La primera pasada de mutación cazó ocho de nueve, y la que falló era un
defecto real de la guarda**: `git check-ignore` sin `--no-index` calla sobre
todo fichero ya versionado, así que al borrar la regla de admisión de
`.gitignore` la prueba seguía en verde —las siete skills de hoy están en el
índice— y solo se habría enterado quien escribiera la octava. Es el patrón
«puerta global que se abre sola» del catálogo de
`.claude/skills/disciplina-evidencia/patrones.md`. Corregido en `f5741b5`, y
la segunda pasada caza las nueve.

## Consecuencias

- Una sesión que abra el repositorio ve las siete skills en `MEMORIA.md` con
  su «cuándo», sin abrir ninguna.
- Una skill que cite algo que dejó de existir rompe la batería, así que se
  arregla el día que se rompe y no tres meses después.
- Escribir una skill nueva cuesta más: hay que declarar sus límites y tener
  fricción medida. Es deliberado; el filtro es el valor.
- La regla de `.gitignore` deja de depender de que alguien recuerde
  `git add -f`.
- **Lo que sigue sin estar cubierto**: que la prosa esté caducada aunque cada
  ruta resuelva. Ninguna prueba puede decirlo. Queda la revisión trimestral que
  declara `patrones.md`, y queda dicho aquí para que nadie confunda una skill
  verde con una skill al día.

## Alternativas descartadas y por qué

- **Generar las skills de las fichas de la auditoría.** Produciría fichas con
  otro nombre. Lo que hace útil a una skill es el juicio sobre qué omitir.
- **Un hook que obligue a cargar la skill.** Ya se intentó una puerta parecida
  en este repositorio —la que bloqueaba `git push`— y se retiró tras quince
  defectos (ADR-001). Quien decide cargar una skill es el modelo leyendo su
  descripción; por eso la descripción es lo que la guarda vigila.
- **Meter las skills en `docs/`.** No las encontraría la herramienta que las
  carga, que es el único consumidor que importa.
- **Una skill por cada ficha PROC.** Veintiuna skills que nadie lee son el
  mismo problema con más ficheros. El filtro de las tres condiciones existe
  para eso.

## La lección

- familia: `prosa-que-el-cambio-deja-falsa`
- sin esto se repetiría: escribir un documento de método que nadie vuelve a
  comprobar, y que sigue citando rutas y decisiones que ya no existen mientras
  todo el mundo lo da por bueno, que es exactamente lo que le pasó a la base de
  conocimiento de `docs/operations/` durante nueve versiones de contrato
- lo hace cumplir: `tests/automation/test_skills.py`
