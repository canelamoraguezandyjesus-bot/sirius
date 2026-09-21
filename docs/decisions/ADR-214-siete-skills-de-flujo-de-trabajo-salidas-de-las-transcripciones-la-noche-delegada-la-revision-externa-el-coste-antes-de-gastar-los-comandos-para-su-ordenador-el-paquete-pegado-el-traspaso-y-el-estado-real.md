# ADR-214 — Siete skills de flujo de trabajo salidas de las transcripciones: la noche delegada, la revisión externa, el coste antes de gastar, los comandos para su ordenador, el paquete pegado, el traspaso y el estado real

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
Al ver las tres primeras añadió: «así pudimos haber sacado por lo menos diez o
veinte». Se sacaron las que aún salen de lo leído con las tres condiciones
cumplidas: siete. Las demás candidatas no llegaban a dos ocurrencias fechadas o
cabían en una regla que ya existe, y están descartadas por escrito.

Las transcripciones ya no existen —se borraron a las 00:25 UTC a petición suya
y no deben volver—, así que las skills salen de lo que esta sesión conserva de
su lectura y de lo que el paso 5 dejó escrito con fecha y hora. Las condiciones
de ADR-211 se aplicaron a cada candidata **antes** de escribirla, en la adenda 6
y en su bis de `docs/audits/arranque-auditoria-forma-de-trabajo.md`.

## Criterio de parada (escrito ANTES de decidir)

El de la adenda 6, que la bis no cambia: las siete pasan la guarda de ADR-211
(`tests/automation/test_skills.py`) sin tocarla; cada una cita solo ficheros y
ADR que existen; ninguna repite `AGENTS.md`, remiten a sus reglas; la batería
entera vuelve verde salvo la roja por diseño del ADR sin su defecto (ADR-182),
que cierra el commit siguiente con H-214; y una candidata sin dos ocurrencias
fechadas se descarta al escribirla. Las siete llegaron con más de dos.

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

**La tercera.** Siete skills nuevas, en `.claude/skills/`:

| Skill | Se repite | Fricción medida | Qué cambia mañana |
|---|---|---|---|
| `modo-nocturno` | 08-08, 10-08, 15-08, 13-09, 14-09 | 3 h 18 min despierto por avisos de permiso (15-08); diez esperas de fondo perdidas por un reinicio (09-09); «que me contestes primero» (14-09); el parte pedido tres veces (14-09); 95 despertares en siete días (08-09) | la noche se pide en un mensaje, no le despierta ningún permiso, el estado se relee de GitHub en cada despertar y el parte tiene tres bloques |
| `revision-externa` | PR #576 (08-09), PR #658 (21-09), la revisión dual (11-08) | cuatro rondas en un día de la misma familia sin que nadie las contara; cuota de Codex agotada (12-09) | la sesión pide la revisión, verifica, corrige, cuenta las rondas y fusiona; el propietario deja de ser el correo |
| `coste-antes-de-tocar-una-fuente` | 28-07, 11-08, 19-08, 20/21-09 | 12 de 23 agentes muertos por límite; 21 subagentes para «nada»; 2,8 M tokens para «todavía no»; 33 turnos y medio uso suyo para un informe y tres reglas | la línea de coste y rendimiento se escribe antes, la fuente barata va primero y lo que toca su cuota se le pregunta antes de gastarlo |
| `comandos-para-su-ordenador` | 08-08, 09-08, 14-08, 11-09, 20-09 | `.venv` «acceso denegado» y el error 396 de OneDrive; `Sirius.lnk` en un escritorio que no existe; «¿yo qué sé dónde está la carpeta?»; `npx.ps1` bloqueado y `winget` con error 1622; dos comandos tumbados por `$HOME\Desktop` | cada comando lleva dónde / qué / qué sale, y las trampas de su máquina están escritas con su fecha |
| `paquete-de-trabajo-pegado` | 18-07 (seis), 25 al 28-07 (doce), 19-08, 08-09 (diez) | ficheros pedidos que la sesión no puede ver; «como un solo documento, para pasárselo directamente»; el paquete en la sesión equivocada dos veces | el HEAD se comprueba, las prohibiciones son el alcance, la entrega es un solo fichero en su orden y los hallazgos que vuelven se verifican y se cuentan |
| `traspaso-a-otra-sesion` | 08-08, 19-08, 24-08, 13-09, 14-09 | una tarde en balde por reconciliar desde una copia caducada (#165); «otra vez a investigar, otra vez a mirar, otra vez a hablar» | el traspaso lleva sha, pendientes, decisiones con su ADR, vetos suyos, mandos y primera acción, en una pantalla; y lo que es decisión va antes al ADR |
| `verificar-el-estado-real` | 10-08, 14-08 (dos), 17-08, 19-08 | documentos que decían «terminada» lo que no lo estaba; seis correcciones suyas, seis acertadas; una afirmación falsa siete veces en tres documentos | un «hecho» exige PR fusionada o prueba; lo probado a mano por él se anota como tal; lo no demostrado se escribe como no demostrado |

Descartadas antes de escribir: «el parte de la mañana» como skill propia —cabe
en tres párrafos y ya está en `hablar-con-el-propietario` y en la regla 12 de
`AGENTS.md`— y «auditar las transcripciones a fondo con más agentes», porque no
hay transcripciones ni debe volver a haberlas en el repositorio.

Las siete remiten a `AGENTS.md` y a las skills que ya existen en vez de
repetirlas; `MEMORIA.md` las indexa sola, como a las demás (ADR-211).

## Comprobación que la sostiene

| Qué se afirma | Comando | Resultado |
|---|---|---|
| Las siete pasan la guarda de ADR-211 sin tocarla | `uv run --no-sync pytest tests/automation/test_skills.py -q` | 127 pruebas en verde (eran 71 con siete skills; con catorce, 127) |
| Ninguna cita rota | `scripts/automation/sirius_check_docs.py` sobre las siete skills, la adenda 6 y su bis, este ADR y `MEMORIA.md` | «Sin defectos documentales en los ficheros comprobados» |
| Los ADR siguen bien formados | `uv run --no-sync pytest tests/automation/test_estado_de_los_adr.py tests/automation/test_registro_de_decisiones.py tests/automation/test_citas_de_los_adr.py tests/engine/test_memoria.py tests/automation/test_skills.py -q` | **855 en verde, 6,6 s** sobre el árbol de las siete (eran 823 sobre el de las tres primeras; la cifra vieja siguió escrita aquí hasta la relectura de abajo) |
| Relectura adversaria del diff antes de la revisión externa (21-09-2026, sobre aa0560ed) | leer el diff entero de la PR #659 como lo leería Codex | tres restos del borrador de tres skills en este ADR —«las tres descripciones», «la tercera skill», la fila de 823— y la primera línea de la lección cortada a media frase en `MEMORIA.md`; los cuatro, corregidos en el commit siguiente |
| Formato y estilo | `ruff format --check .`, `ruff check .`, `git diff --check` | limpios |
| La batería entera, sobre el árbol final | `uv run --no-sync pytest` (12:26 → 12:39 UTC) | **7 373 en verde, 17 saltadas, 2 xfailed, 0 rojas, 12 min 17 s**, sobre el árbol de 6858e41e: las siete skills, H-214 ya en el registro y las correcciones de la ronda 1 de Codex. El commit que añade esta fila solo cambia esta tabla; la batería de Quality sobre ese head es la comprobación independiente y queda enlazada en la PR #659. Para la historia: la pasada sobre el árbol de las siete sin H-214 dio 7 371 en verde y 1 roja por diseño (`test_todo_adr_que_declara_un_defecto_deja_su_entrada_en_el_registro`, ADR-182) en 10 min 30 s, y la del árbol de tres se detuvo a las 10:29 UTC al añadir las otras cuatro |
| `MEMORIA.md` al día | `uv run --no-sync sirius-memoria conocimiento` | regenerada en el mismo commit (ADR-171) |
| Ronda 1 de Codex (21-09-2026 12:22 UTC, sobre aa0560ed) | `@codex review` en la PR #659 | **1 P1 y 3 P2, los cuatro ciertos**: la pasada «limpia» de Codex se aceptaba sin las cinco comprobaciones del recolector del motor (`revision-externa`); `origin/main` se leía sin traerlo (`verificar-el-estado-real`); los metadatos entraban en una entrega cerrada que no los pedía (`paquete-de-trabajo-pegado`); y la batería registrada aquí era la del árbol de tres skills, no la del head. Los cuatro, atendidos en 6858e41e; tres de esos arreglos quedaron a medias y los terminó la ronda 2 (abajo). El cuarto es la familia `prosa-que-el-cambio-deja-falsa` por segunda PR seguida (#658, segunda pasada; #659, primera): parada por la regla de las dos rondas, y la raíz —la tabla se escribía antes del árbol final— queda escrita en `cadena-de-comprobacion`, no solo corregida aquí |
| Ronda 2 de Codex (21-09-2026 12:44 UTC, sobre 14e1c60d) | `@codex review` en la PR #659 | **3 P2, los tres ciertos y los tres sobre arreglos de la ronda 1**: `git fetch origin main` a secas no mueve `origin/main` en un checkout de una sola rama (reproducido en un repositorio de prueba: tras el fetch, `origin/main` «no existe» y `FETCH_HEAD` sí avanza; arreglo: destino explícito `+main:refs/remotes/origin/main`); los metadatos «aparte» seguían rompiendo la entrega cerrada (arreglo: si no los pide, no van); y exigir un sha al 👍 hacía imposible ese canal, que el recolector correlaciona con el disparador y con el head vigente (`_check_reactions`). Segunda ronda seguida con la misma familia en dos de los tres —**arreglo a medias que conserva lo que el hallazgo mandaba quitar**—: parada por la regla de las dos rondas; la raíz —arreglar en el límite que marca el hallazgo y reproducir el caso que describe— queda escrita en `revision-externa`, paso 2 |

## Consecuencias

- La próxima noche delegada, la próxima PR de sesión, el próximo gasto grande,
  el próximo comando para su ordenador, el próximo paquete pegado, el próximo
  traspaso y la próxima vez que un documento diga «terminado» tienen un
  procedimiento que la sesión carga por su descripción, con las fechas de por
  qué existe.
- Escribir skills de flujo sigue costando lo que ADR-211 exige: dos ocurrencias
  fechadas y fricción medida. Aquí las siete sobraban.
- El registro de defectos recibió H-214 en el commit siguiente al de las
  skills, con el sha de aquel (ADR-182, ADR-192); por eso la batería del primer
  commit tuvo una prueba roja por diseño, y la del árbol final no tiene
  ninguna.
- **Lo que sigue sin guarda**: que una sesión cargue la skill cuando toca. La
  descripción es lo único que decide eso, y por eso las siete descripciones
  dicen «cárgala cuando…» con las palabras que él usa.

## Alternativas descartadas y por qué

- **Volver a traer las transcripciones para auditarlas con más agentes.** Es la
  fuente cara que `coste-antes-de-tocar-una-fuente` enseña a no tocar sin
  poner el coste delante, y el propietario pidió que no quedara rastro de ellas.
- **Una skill por cada hallazgo o por cada queja.** Skills que nadie lee son el
  problema de ADR-211 con más ficheros; las candidatas sin dos ocurrencias
  fechadas («cuándo usar el motor», «presentar un plan sin códigos»,
  «instalar herramientas») quedaron fuera o dentro de otra, y está escrito
  cuáles.

## La lección

- familia: `leccion-que-se-queda-en-el-informe`
- sin esto se repetiría: leer caro y dejar lo aprendido solo en un informe
  sin nada que la sesión siguiente cargue, de modo que «pasado mañana» la
  sesión nueva vuelva a hacer de noche lo que ya salió mal el 15-08 y el
  14-09, y el propietario vuelva a llevar a mano cada ronda de Codex
- lo hace cumplir: `tests/automation/test_skills.py`
