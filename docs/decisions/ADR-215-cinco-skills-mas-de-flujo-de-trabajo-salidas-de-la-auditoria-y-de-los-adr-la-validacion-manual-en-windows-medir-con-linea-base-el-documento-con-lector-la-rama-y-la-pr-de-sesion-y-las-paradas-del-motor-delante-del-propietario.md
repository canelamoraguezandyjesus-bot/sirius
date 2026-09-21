# ADR-215 — Cinco skills más de flujo de trabajo, salidas de la auditoría y de los ADR: la validación manual en Windows, medir con línea base, el documento con lector, la rama y la PR de sesión y las paradas del motor delante del propietario

- Estado: APROBADO
- Fecha: 2026-09-21
- Aprobación: la sesión, por ADR-204 (es método de trabajo, no producto, dinero
  ni salud); el propietario, al fusionar la PR de esta rama

## Contexto y problema

Tras fusionar la PR #659 (ADR-214, siete skills), el propietario preguntó el
21-09-2026: «entonces ya es imposible sacar buenas skills, ¿no? … de las solo
las tres que me sacaste». Dos cosas ciertas detrás: contaba tres cuando ya eran
siete —el mensaje que lo decía no le había llegado a tiempo—, y quería saber si
sin las transcripciones, borradas a petición suya (ADR-213, ADR-214), la fuente
se había acabado. No se había acabado: quedan las fichas de
`docs/audits/AUDITORIA_FORMA_DE_TRABAJO_2026-09.md` (PROC, E, T), los ADR con su
lección, los guiones de `scripts/` y la historia de git. Cuestan cero y ninguna
es una transcripción. La adenda 7 de
`docs/audits/arranque-auditoria-forma-de-trabajo.md` puso la línea de coste, las
cuatro preguntas, las tres condiciones por candidata y el criterio de parada
**antes** de escribir ninguna.

Y una regla nueva, salida de las rondas 3, 4 y 5 de Codex sobre la PR #659, que
esta tanda aplica desde la primera línea: copiar a medias un criterio que ya
tiene fuente canónica es un defecto antes de nacer. Lo que ya está en el
contrato operativo, en `docs/operations/MOTOR_DE_SIRIUS.md` o en otra skill se
remite, no se copia.

## Criterio de parada (escrito ANTES de decidir)

El de la adenda 7: la guarda de ADR-211 (`tests/automation/test_skills.py`)
pasa sin tocarla; cada skill cita solo ficheros y ADR que existen; ninguna
repite `AGENTS.md`; la batería entera vuelve verde salvo la roja por diseño del
ADR sin su defecto (ADR-182), que cierra el commit siguiente con H-215; una
candidata sin dos ocurrencias fechadas se descarta al escribirla; y lo que
tiene fuente canónica se remite. Las cinco llegaron con dos ocurrencias o más.

## Opciones consideradas

- **Dar la fuente por cerrada**: «sin transcripciones no hay más skills». Es
  falso: las fichas de la auditoría son el destilado fechado de esas mismas
  conversaciones y de la historia del repositorio.
- **Volver a traer las transcripciones.** El propietario pidió que no quedara
  rastro de ellas, y `coste-antes-de-tocar-una-fuente` existe para no repetir
  ese gasto.
- **Sacar de la auditoría y de los ADR las candidatas que pasen las tres
  condiciones, con las condiciones escritas antes.** Esta.

## Decisión

Cinco skills nuevas en `.claude/skills/`:

| Skill | Se repite | Fricción medida | Qué cambia mañana |
|---|---|---|---|
| `validacion-manual-en-windows` | 10-08 14:49 («77 comprobaciones, 0 fallos, 3 omitidas»); 17-08 (PR #122: B13 y B14 en Windows real, aceptación de 0.1) | la PR #122 esperó más de nueve días una ejecución correcta; `quality-windows.yml` con cero ejecuciones; #127 y #134 intactas desde agosto (PROC-008) | la sesión sabe qué pruebas necesitan Windows real (la trazabilidad), con qué tres guiones se le piden, qué devuelve él y cómo se registra lo demostrado y lo no demostrado |
| `medir-con-linea-base` | ADR-154; ADR-202 (14-09); ADR-203 (19-09); la cifra sin comparación del 19-09 | una medición que cerraba una ola no se hizo y la razón no constaba; la línea base de producción no existía (H-203, abierto); una alarma por una línea base recién medida | línea base primero (`--puerta-cerrada`), la cifra que manda y el suelo escritos antes, la cifra anclada al árbol y con su comparación al lado, y qué guion mide qué |
| `documento-con-lector` | PROC-010 (20-09); ADR-207 (20-09); ADR-210 (20-09); ADR-196 | nueve versiones de contrato de retraso; 97 de 150 documentos sin fecha declarada; cinco ADR en `pieza-sin-lector` | antes de crear un `.md`: lector y camino, generar si se puede, fecha declarada y con qué caduca; lo que ya no describe nada se archiva, no se borra (ADR-195) |
| `rama-y-pr-de-sesion` | 20-09 (#658); 21-09 (#659) | un empujón rechazado y una pregunta evitable al propietario; los dos ADR-016 (ADR-180) | rama nueva desde `main` recién traído por unidad, nunca sobre historia fusionada; lo que la sesión no puede hacer; el cuerpo de la PR en tres bloques; el cierre aplastado con el head aprobado |
| `paradas-del-motor-delante-del-propietario` | 13-09 (ADR-189: cuatro paradas, la más antigua diez días); ADR-198 (veinte días); 19-09 (PROC-003) | diez y veinte días de espera; 20 de 91 encargos re-despachados (PROC-005) | al abrir sesión y en cada parte, la decisión que espera al propietario, hasta que conteste; la orden de salida es la que el motor imprimió y va en el lote del ordenador |

Descartadas antes de escribir, con su razón en la adenda 7:
`prueba-intermitente` (una ocurrencia: #137, arreglada por ADR-162 y archivada
por ADR-210), `investigacion-con-fecha` (sin fricción medida; la regla ya está
en la tabla de `AGENTS.md`), `operar-el-ciclo-entero` (su fuente es
`docs/operations/MOTOR_DE_SIRIUS.md` y el contrato: una copia sería
`pieza-sin-lector` al mes) y `exportacion-de-chatgpt` (una ocurrencia).

Las cinco remiten a lo que ya existe en vez de copiarlo: a la trazabilidad y a
los guiones de Windows, al contrato y a `MOTOR_DE_SIRIUS.md`, y a las skills
`revision-externa`, `obra-en-curso`, `comandos-para-su-ordenador` y
`verificar-el-estado-real`. Diecinueve skills en total; `MEMORIA.md` las indexa
sola (ADR-211).

## Comprobación que la sostiene

| Qué se afirma | Comando | Resultado |
|---|---|---|
| Las cinco pasan la guarda de ADR-211 sin tocarla | `uv run --no-sync pytest tests/automation/test_skills.py -q` | **167 pruebas en verde** (127 con catorce skills; 167 con diecinueve), 0,36 s |
| Ninguna cita rota | `scripts/automation/sirius_check_docs.py` sobre las cinco skills, la adenda 7, este ADR y `MEMORIA.md` | «Sin defectos documentales en los ficheros comprobados» |
| Los ADR siguen bien formados | `uv run --no-sync pytest tests/automation/test_estado_de_los_adr.py tests/automation/test_registro_de_decisiones.py tests/automation/test_citas_de_los_adr.py tests/engine/test_memoria.py tests/automation/test_skills.py -q` | **898 en verde**, 2,1 s (eran 855 con catorce skills) |
| `MEMORIA.md` al día | `uv run --no-sync sirius-memoria conocimiento` | regenerada en el mismo commit (ADR-171) |
| La batería entera, sobre la rama anterior (`claude/skills-de-flujo-2`) | `uv run --no-sync pytest` | **7 418 en verde, 17 saltadas, 2 xfailed, 0 rojas, 12 min 22 s** sobre el árbol de 9465b09c (las cinco skills, ADR-215 y H-215) y **7 422 en verde** sobre el de 5bdb3b5e (con I-009); la del primer commit (4a8cff8f) tenía por diseño la roja de ADR-182 hasta H-215. La batería de la rama rehecha va en la fila de abajo |
| `main` avanzó durante la revisión | `git rev-list --count origin/main ^HEAD` tras la ronda 4 | 1: la PR #654 (71feb670) entró en `main` mientras la #660 estaba en revisión y tocó `MEMORIA.md` y el registro de defectos, los mismos ficheros que esta rama. «Update branch» de GitHub falló por conflicto y la sesión no puede hacer `merge`, `rebase` ni `cherry-pick` de `main` (ADR-206; `rama-y-pr-de-sesion`), así que la rama se rehizo desde 71feb670 (`claude/skills-de-flujo-3`) con los mismos ficheros de e77fdab0, H-215 añadida detrás de H-212 y `MEMORIA.md` regenerada; la PR #660 se cierra a favor de la nueva. Las cuatro rondas de Codex de arriba valen para el texto, no para el head: la pasada limpia se pide otra vez sobre el head nuevo |
| La batería entera, sobre el árbol final de esta rama | `uv run --no-sync pytest` (14:36 → 14:48 UTC) | **7 433 en verde, 17 saltadas, 2 xfailed, 0 rojas, 12 min 37 s**, sobre el árbol de 5db285b0: `main` con la #654, las cinco skills, ADR-215, I-009 y H-215 en el registro. El commit que añade esta fila solo cambia esta tabla; Quality de GitHub sobre el head empujado es la batería completa de ese head |
| Ronda 1 de Codex en la PR #661 (21-09-2026 14:56 UTC, sobre 623cdab9) | `@codex review` | **1 P1 y 1 P2, los dos ciertos.** El P1 es otra vez la familia de la orden escrita sin comprobar el caso: la receta nueva de `rama-y-pr-de-sesion` decía restaurar los ficheros propios enteros con `git checkout <head-anterior> -- <rutas>`, y en las rutas que `main` también tocó eso pisa lo que llegó de `main` (la rama se rehizo bien solo porque las dos rutas compartidas no se restauraron: `MEMORIA.md` se regeneró y H-215 se añadió detrás de H-212; la skill no lo decía). Ahora la receta separa las rutas que `main` no tocó (se restauran) de las compartidas (regenerar, reañadir o reaplicar hunk a hunk con `git apply`). El P2: la fila de `documento-con-lector` en la adenda 7 seguía con el criterio inicial de preguntar qué archivar; queda anotada como criterio sustituido. Corregidos en el commit siguiente a 623cdab9 |
| Ronda 1 de Codex (21-09-2026 14:09 UTC, sobre 25bc1099) | `@codex review` en la PR #660 | **6 P1 y 1 P2, los siete ciertos.** Cuatro de la misma familia —una orden copiable escrita de memoria, sin leer las guardas de la herramienta—: `checkout -B` reinicia una rama local con trabajo sin empujar; la orden de `sirius-decidir` fabricada perdía `--repo` y `--bloque`, ofrecía `--continuar` donde está vetado (ADR-188) y callaba que la decisión no llega al diario de `estado-del-motor` (no hay vía: I-009). La raíz queda en `crear-una-skill` (comandos comprobados; si la herramienta imprime la orden, se copia) y la skill deja de fabricar la orden. Los otros tres: la orden del ordenador iba en cada parte (regla 13: al lote); la descripción de `documento-con-lector` se cortaba en el punto de «.md» (el extractor de `MEMORIA.md` corta en el primer punto); y el archivado se le preguntaba al propietario siendo reversible (ADR-204). Corregidos en el commit siguiente a 25bc1099 |
| Ronda 2 de Codex (21-09-2026 14:17 UTC, sobre 5bdb3b5e) | `@codex review` en la PR #660 | **1 P1, cierto, y de la misma familia que cuatro de la ronda 1**: la skill decía que la lista de `sirius-motor` imprime la orden exacta, y `_con_decision_pendiente` imprime una plantilla (`<work_id>`, sin `--repo` ni `--bloque`, siempre con `--continuar`; su prueba solo fija `--diario` y `--ejecutar`). Segunda ronda seguida con la misma familia: parada, y la raíz se afina en `crear-una-skill`: de las tres fuentes de un comando manda la prueba, no el código. La skill copia solo la orden que imprime la parada de `sirius-despachar` y trata la lista como aviso. Corregido en el commit siguiente a 5bdb3b5e |
| Ronda 3 de Codex (21-09-2026 14:25 UTC, sobre 4f36e157) | `@codex review` en la PR #660 | **1 P2, cierto**: el arreglo de la ronda 2 prohibía copiar nada de la lista de `sirius-motor`, y `--terminar` solo necesita el `work_id` y el diario (`_terminar` va antes de `--repo` y `--bloque`; `tests/engine/test_decision_cli.py`). Familia distinta —arreglo que sobrecorrige y cierra una salida segura—, corregida en su límite: la exigencia de la orden original queda solo para `--continuar`. Corregido en el commit siguiente a 4f36e157 |

La fila de la batería de la rama rehecha se escribe sobre su árbol final, con
H-215 ya en el registro, y no antes (skill `cadena-de-comprobacion`: la tabla
se escribe la última y se relee sobre el árbol final).

## Consecuencias

- La pregunta del propietario tiene respuesta demostrada: sin transcripciones
  salieron cinco skills más que pasan las tres condiciones, y quedan
  candidatas para cuando tengan dos ocurrencias (`prueba-intermitente`,
  `investigacion-con-fecha`) o para cuando llegue su exportación de ChatGPT.
- Diecinueve skills: la tabla de `MEMORIA.md` crece una fila por skill, y la
  descripción sigue siendo lo único que decide si una sesión la carga.
- El registro de defectos recibe H-215 en el commit siguiente, con el sha de
  este (ADR-182, ADR-192); por eso la batería del primer commit tuvo una
  prueba roja por diseño, y la del árbol final no tiene ninguna.
- **Lo que sigue sin guarda**: que la prosa de las cinco siga al día. Rutas y
  ADR citados sí; el resto, la revisión trimestral que declara ADR-211.

## Alternativas descartadas y por qué

- **Una skill por ficha PROC** (veintiuna). El filtro de las tres condiciones
  existe para eso: la mayoría de las fichas están «transformadas» en el motor o
  ya cubiertas por skills anteriores.
- **Copiar en `paradas-del-motor-delante-del-propietario` cómo se opera el
  ciclo.** Es exactamente lo que las rondas 3, 4 y 5 de la PR #659 enseñaron a
  no hacer: la fuente es `docs/operations/MOTOR_DE_SIRIUS.md`, y la skill solo
  añade la parte humana que nadie volvía a poner delante.

## La lección

- familia: `leccion-que-se-queda-en-el-informe`
- sin esto se repetiría: creer que sin transcripciones no salen más skills
  cuando su destilado fechado —la auditoría y los ADR— sigue en el árbol y
  basta con aplicarle las tres condiciones de ADR-211
- lo hace cumplir: `tests/automation/test_skills.py`
