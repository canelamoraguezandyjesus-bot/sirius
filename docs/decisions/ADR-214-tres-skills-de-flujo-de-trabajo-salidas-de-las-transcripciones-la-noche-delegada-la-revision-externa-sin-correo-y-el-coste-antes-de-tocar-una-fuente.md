# ADR-214 — Tres skills de flujo de trabajo salidas de las transcripciones: la noche delegada, la revisión externa sin correo y el coste antes de tocar una fuente

- Estado: APROBADO
- Fecha: 2026-09-21
- Aprobación: la sesión, por ADR-204 (es método de trabajo, no producto, dinero
  ni salud); el propietario, al fusionar la PR de esta rama

## Contexto y problema

El paso 5 de la auditoría (`docs/audits/AUDITORIA_FORMA_DE_TRABAJO_2026-09.md`)
leyó 28 transcripciones de sesiones de la nube y dejó un informe, ADR-213 y
tres reglas de conversación en `AGENTS.md`. El propietario, al verlo fusionado
el 21-09-2026, dijo lo que faltaba: de esas conversaciones se podían haber
sacado **skills de flujo de trabajo**, y «pasado mañana te vas a olvidar». Tiene
razón en el fondo: en este repositorio, lo que una sesión aprende sobrevive
solo si queda donde la siguiente lo carga (ADR-211), y un informe no se carga.

Las transcripciones ya no existen —se borraron a las 00:25 UTC a petición suya
y no deben volver—, así que las skills salen de lo que esta sesión conserva de
su lectura y de lo que el paso 5 dejó escrito con fecha y hora. Las condiciones
de ADR-211 se aplicaron a cada candidata **antes** de escribirla, en la adenda 6
de `docs/audits/arranque-auditoria-forma-de-trabajo.md`.

## Criterio de parada (escrito ANTES de decidir)

El de la adenda 6: las tres pasan la guarda de ADR-211
(`tests/automation/test_skills.py`) sin tocarla; cada una cita solo ficheros y
ADR que existen; ninguna repite `AGENTS.md`, remiten a sus reglas; la batería
entera vuelve verde salvo la roja por diseño del ADR sin su defecto (ADR-182),
que cierra el commit siguiente con H-214; y una candidata sin dos ocurrencias
fechadas se descarta al escribirla. Las tres llegaron con más de dos.

## Opciones consideradas

- **Dejar lo aprendido en el informe.** Es lo que se hizo primero, y es lo que
  el propietario señaló: nadie carga un informe de 1 400 líneas al empezar una
  sesión.
- **Más reglas en `AGENTS.md`.** Las reglas caben en una línea; un flujo de
  trabajo —qué se hace antes, durante y después de una noche delegada— no. Y
  `AGENTS.md` se lee entero cada vez: lo que crece ahí se paga en cada turno.
- **Skills, con las tres condiciones de ADR-211 y su guarda.** Se cargan solo
  cuando la descripción encaja con lo que está pasando, y la guarda impide que
  citen lo que ya no existe.

## Decisión

**La tercera.** Tres skills nuevas, en `.claude/skills/`:

| Skill | Se repite | Fricción medida | Qué cambia mañana |
|---|---|---|---|
| `modo-nocturno` | 08-08, 10-08, 15-08, 13-09, 14-09 | 3 h 18 min despierto por avisos de permiso (15-08); diez esperas de fondo perdidas por un reinicio (09-09); «que me contestes primero» (14-09); el parte pedido tres veces (14-09); 95 despertares en siete días (08-09) | la noche se pide en un mensaje, no le despierta ningún permiso, el estado se relee de GitHub en cada despertar y el parte tiene tres bloques |
| `revision-externa` | PR #576 (08-09), PR #658 (21-09), la revisión dual (11-08) | cuatro rondas en un día de la misma familia sin que nadie las contara; cuota de Codex agotada (12-09) | la sesión pide la revisión, verifica, corrige, cuenta las rondas y fusiona; el propietario deja de ser el correo |
| `coste-antes-de-tocar-una-fuente` | 28-07, 11-08, 19-08, 20/21-09 | 12 de 23 agentes muertos por límite; 21 subagentes para «nada»; 2,8 M tokens para «todavía no»; 33 turnos y medio uso suyo para un informe y tres reglas | la línea de coste y rendimiento se escribe antes, la fuente barata va primero y lo que toca su cuota se le pregunta antes de gastarlo |

Descartadas antes de escribir: «el parte de la mañana» como skill propia —cabe
en tres párrafos y ya está en `hablar-con-el-propietario` y en la regla 12 de
`AGENTS.md`— y «auditar las transcripciones a fondo con más agentes», porque no
hay transcripciones ni debe volver a haberlas en el repositorio.

Las tres remiten a `AGENTS.md` y a las skills que ya existen en vez de
repetirlas; `MEMORIA.md` las indexa sola, como a las demás (ADR-211).

## Comprobación que la sostiene

| Qué se afirma | Comando | Resultado |
|---|---|---|
| Las tres pasan la guarda de ADR-211 sin tocarla | `uv run --no-sync pytest tests/automation/test_skills.py -q` | 95 pruebas en verde (eran 71 con siete skills; las tres nuevas añaden sus filas) |
| Ninguna cita rota | `scripts/automation/sirius_check_docs.py` sobre las tres skills, la adenda 6, este ADR y `MEMORIA.md` | «Sin defectos documentales en los ficheros comprobados» |
| Los ADR siguen bien formados | `uv run --no-sync pytest tests/automation/test_estado_de_los_adr.py tests/automation/test_registro_de_decisiones.py tests/automation/test_citas_de_los_adr.py tests/engine/test_memoria.py -q` | 823 en verde (con la guarda de skills en el mismo lote), 2,9 s |
| Formato y estilo | `ruff format --check .`, `ruff check .`, `git diff --check` | limpios |
| La batería entera | `uv run --no-sync pytest` | lanzada sobre este árbol a las 10:29 UTC del 21-09; el resultado se escribe en el commit siguiente, el de H-214, y hasta entonces esta fila dice «pendiente» a propósito |
| `MEMORIA.md` al día | `uv run --no-sync sirius-memoria conocimiento` | regenerada en el mismo commit (ADR-171) |

## Consecuencias

- La próxima noche delegada, la próxima PR de sesión y el próximo gasto grande
  tienen un procedimiento que la sesión carga por su descripción, con las
  fechas de por qué existe.
- Escribir skills de flujo sigue costando lo que ADR-211 exige: dos ocurrencias
  fechadas y fricción medida. Aquí las tres sobraban.
- El registro de defectos recibe H-214 en el commit siguiente, con el sha de
  este (ADR-182, ADR-192); por eso la batería de este commit tiene una prueba
  roja por diseño.
- **Lo que sigue sin guarda**: que una sesión cargue la skill cuando toca. La
  descripción es lo único que decide eso, y por eso las tres descripciones
  dicen «cárgala cuando…» con las palabras que él usa.

## Alternativas descartadas y por qué

- **Volver a traer las transcripciones para auditarlas con más agentes.** Es la
  fuente cara que la tercera skill enseña a no tocar sin poner el coste
  delante, y el propietario pidió que no quedara rastro de ellas.
- **Una skill por cada hallazgo del paso 5.** Ocho skills que nadie lee son el
  problema de ADR-211 con más ficheros; solo tres tenían dos ocurrencias y
  fricción medida.

## La lección

- familia: `leccion-que-se-queda-en-el-informe`
- sin esto se repetiría: leer una fuente cara, escribir el informe con lo
  aprendido y no dejar nada que la sesión siguiente cargue, de modo que
  «pasado mañana» la sesión nueva vuelva a hacer de noche lo que ya salió mal
  el 15-08 y el 14-09, y el propietario vuelva a llevar a mano cada ronda de
  Codex
- lo hace cumplir: `tests/automation/test_skills.py`
