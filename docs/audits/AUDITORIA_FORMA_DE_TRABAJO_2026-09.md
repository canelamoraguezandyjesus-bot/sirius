# La auditoría de la forma de trabajar, segunda edición: las 21 fichas de agosto, revalidadas el 19 de septiembre de 2026

- Fecha: 2026-09-19
- Estado: **CERRADA SOBRE LAS FUENTES DISPONIBLES** — paso 2 (revalidar las
  fichas de agosto) cerrado el 19-09-2026; paso 3 (conversación, ideas,
  debate) cerrado el 20-09-2026 sobre las conversaciones de claude.ai; paso 4
  (el lado de la ejecución) cerrado el 20-09-2026 sobre las transcripciones de
  Claude Code, locales y de la nube. Queda por leer, con su propia adenda, la
  exportación de ChatGPT.
- Nota de arranque: `docs/audits/arranque-auditoria-forma-de-trabajo.md`,
  publicada antes de abrir ninguna conversación. Ahí están el encargo, el
  alcance, las cuatro preguntas, el criterio de parada y las hipótesis.
- Primera edición: `docs/implementation/WORK_PROCESS_AUDIT.md` (11–12 de
  agosto de 2026, 21 fichas PROC-001…021).
- Rama: `claude/sirius-collaboration-rir6r6`.
- Alcance: Sirius aplicación y Sirius motor. La cabeza robótica queda fuera por
  decisión del propietario del 19-09-2026 (nota de arranque, «Alcance»).

## Cómo se ha revalidado, y qué vale cada veredicto

Tres veredictos posibles, con su prueba mínima, fijados antes de mirar:

- **vigente**: el proceso sigue haciéndose como agosto lo describe, y hay una
  ocurrencia **fechada después del 11-08-2026**. Sin ocurrencia no hay
  «vigente»; hay «vigente, sin ocurrencia observable desde…», que es otra cosa.
- **caducada**: ya no se hace así, y se cita **qué lo mató** —ADR, workflow o
  bloque del motor—.
- **transformada**: se sigue haciendo pero de otra forma; se cita en qué y
  con qué ocurrencia.

**Fuentes de este paso**, todas del repositorio o de GitHub, ninguna de
conversación: el árbol de `main` en `3062a31`; los 196 ADR de
`docs/decisions/` y sus fechas; `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md`
(v1.10); `docs/operations/MOTOR_DE_SIRIUS.md`; los 24 workflows de
`.github/workflows/`; el diario del motor proyectado en `DESENLACES.md` de la
rama `estado-del-motor` (91 encargos, 667 sucesos, último el 14-09 09:24 UTC);
las incidencias abiertas y las ejecuciones de workflows leídas por la API de
GitHub el 19-09; el índice de las 42 sesiones de Claude Code de la cuenta
(metadatos, entregado al propietario, no publicado); la memoria de sesión
(ADR-172) donde se cita.

**Límites de este paso.** El clon de la sesión es superficial (50 commits,
el más antiguo del 07-09), así que ningún recuento sale de `git log`: las
frecuencias vienen del diario del motor, de las fechas de los ADR y de la API
de GitHub. De `merge-sirius-work.yml` solo se leyeron sus 100 últimas
ejecuciones de 2 992. Nada de lo que sigue afirma qué se dijo en una
conversación: eso es el paso 3.

## Resumen: los 21 veredictos

| Ficha | Proceso (agosto) | Veredicto | Qué lo transformó o lo mató | Última ocurrencia observada |
|---|---|---|---|---|
| PROC-001 | Redactar el work item | **transformada** | `sirius-despachar`: la orden en lenguaje llano se convierte en incidencia (ADR-063, 071, 086) | 14-09, WI-20260914-073945 → #627 |
| PROC-002 | Certificar y arrancar con dos etiquetas | **caducada** | el motor aplica la etiqueta de activación con orden del propietario (contrato §12.1/§12.4; ADR-056, 063, 068; bloque E1b) | forma vieja: ninguna observada tras el 11-08 |
| PROC-003 | Vigilar el ciclo y atender avisos | **transformada** | tablero por incidencia (ADR-175), marcadores por parada (157/158), red de seguridad y supervisor | 14-09, `tablero-de-incidencia.yml` |
| PROC-004 | Autorizar el merge (`fusiona`) | **vigente**, con dos vías | `fusiona` para el motor; botón de GitHub para las PR de sesión | 14-09 00:19 (`fusiona`, #615); 14-09 noche (trece PR por botón) |
| PROC-005 | Desatascar estados parados | **transformada** | supervisor y red de seguridad (C1), `continua` (ADR-030/035/147/199), `sirius-decidir` (189), re-despachar | 14-09 (re-despacho de la guarda de citas) |
| PROC-006 | Depurar y endurecer la automatización | **vigente** | sigue siendo la familia dominante: 152 de 196 ADR (EST) | 14-09, trece ADR en un día |
| PROC-007 | Revisión adversarial Claude ↔ Codex | **transformada** | automática en el ciclo (ADR-023, 146, 156); a mano y obligatoria en las PR de sesión | 13-09 (ciclo); 12-09 (a mano, memoria de sesión) |
| PROC-008 | Validación manual en Windows real | **vigente, sin ocurrencia desde el 17-08** | PR #122 cerró B13/B14 y la aceptación de 0.1; `quality-windows.yml` nunca ha corrido | 17-08, PR #122 |
| PROC-009 | Registro de estado y evidencia | **transformada** | vistas generadas y guardas derivadas (ADR-171, 173, 182, 192); barridos con evidencia | 14-09, dos barridos de cierre |
| PROC-010 | Reconciliar documentación derivada | **vigente** (sin dueño; resuelta por abandono) | nadie la hace y nadie la lee: la KB va nueve versiones de contrato atrás | ninguna desde el 20-07 |
| PROC-011 | Registrar decisiones | **vigente**, multiplicada | 7 → 196 ADR; skill `adr`; lección obligatoria (ADR-174); 150 siguen PROPUESTO | 14-09, ADR-202 |
| PROC-012 | Especificaciones y documentos de dirección | **transformada** | clase `documentacion` del motor (C3, ADR-066); el paso DOCX caducó de hecho | 14-09, #627; DOCX: 08-09 en rojo |
| PROC-013 | Reconstruir contexto al abrir sesión | **transformada** | `MEMORIA.md` entera (ADR-171, 196) y memoria de sesión (172) | 19-09, esta sesión |
| PROC-014 | Investigación técnica | **transformada** dos veces | entró en el motor (B1) y el carril se retiró (ADR-161/163); vuelve a la sesión, con fecha y «caduca con» | 11-09, dos investigaciones de sesión |
| PROC-015 | Auditorías | **transformada** | carril del motor retirado (161/163); la mina gana reloj (ADR-201) | 14-09, segunda mina; 19-09, esta |
| PROC-016 | Defectos intermitentes | **transformada**, con una pérdida | registro de defectos versionado (ADR-047, 075, 182, 192); el caso de agosto no llegó al registro | #137 cerrada el 23-08 sin registro |
| PROC-017 | Medir con criterio previo | **vigente**, ampliada | banco de 47, suelos como `xfail(strict)`, cifras ancladas (ADR-154) | 14-09, ADR-202 |
| PROC-018 | Gobernanza y backlog | **vigente** (sin cambios) | #8–#25 intactas desde julio; reclasificadas como «contenedores» el 14-09, sin decisión | ninguna desde el 17-07 (#127/#134: agosto) |
| PROC-019 | Transporte de contexto entre herramientas | **transformada** por diseño | despachador, permiso escrito (ADR-147), reflector, dos memorias | 19-09 (flanco a mano: las exportaciones) |
| PROC-020 | Operar sesiones de agentes | **vigente**, con más estructura | skills como runbooks; ADR-160, 198; 42 sesiones, 25 desde el móvil | 15-09 (índice) y 19-09 |
| PROC-021 | Coste y modelos | **transformada** a medias | presupuesto y modelo por run en el motor (ADR-043, 054, 095, 138); sin libro mayor para las sesiones | 19-09 (coste por sesión visto por primera vez) |

En cifras: **2 caducadas** (PROC-002 entera; el paso DOCX de PROC-012),
**11 transformadas**, **8 vigentes**, de las que tres lo son con matiz (una sin
ocurrencia desde el 17-08, una sin dueño, una sin cambios desde julio).

## Las fichas, una a una

### PROC-001 — Redactar el work item

**Agosto:** conversación → cuerpo de doce campos → pegado a mano en GitHub →
la plantilla aplica `sirius:planned`. Fricción: transporte y cuerpos truncados.

**Hoy:** `uv run sirius-despachar "orden en lenguaje llano"`
(`docs/operations/MOTOR_DE_SIRIUS.md` §1). El despachador
(`src/sirius_engine/dispatcher.py`) interpreta la orden, proyecta el cuerpo
(ADR-071), ensaya por defecto y solo escribe con `--ejecutar`; para antes de
crear la incidencia por cinco causas (ADR-043, 085, 184, 188). La plantilla
`.github/ISSUE_TEMPLATE/sirius-work-item.yml` sigue para la vía manual.

**Comprobación:** 91 encargos en `DESENLACES.md` entre el 25-08 y el 14-09,
todos con objetivo en lenguaje llano; el último, WI-20260914-073945, produjo
#627 y la fusión `aea308c`.

**Veredicto: transformada.** Lo que murió: el pegado de doce campos y el
truncado. Lo que sigue a mano: escribir la orden —y, por hipótesis H1/H4 de la
nota, prepararla en conversación—. Fricción nueva: los verbos admitidos son
pocos y van al principio de la frase; y la puerta de sensibilidad acertó en
1 de 3 paradas reales antes de ADR-184.

### PROC-002 — Certificar y arrancar un bloque

**Agosto:** el propietario aplicaba dos etiquetas a mano; la máquina tenía
prohibido aplicar `sirius:implement-requested` (§9.1).

**Hoy:** el motor la aplica él (`dispatcher.py:78`, `ETIQUETA_ACTIVACION`),
autorizado por el contrato v1.7 §12.1 y generalizado en v1.8 §12.4 a la clase
que despacha (ADR-056, 063, 068; bloque E1b cerrado). §9.1 sigue
prohibiéndoselo al vigilante periódico, que es otra pieza. Los rechazos de la
puerta de validación —que en agosto costaban «3 rechazos en 6 min» y seis días
parados— pasaron a ser paradas del despachador **antes** de crear nada: hoy hay
4 encargos en `needs_decision / preparar`.

**Comprobación:** contrato v1.10, líneas de §12; `dispatcher.py`; los 91
encargos del diario entraron por el despachador; ningún documento posterior al
11-08 describe el etiquetado a mano.

**Veredicto: caducada.** La muerte la firma el bloque E1b. La oportunidad que
agosto proponía —«cola de bloques pre-aprobada»— se cumplió con otra forma:
se pueden despachar varios seguidos y la cola es la de revisión (ADR-191/200).

### PROC-003 — Vigilar el ciclo y atender notificaciones

**Agosto:** menciones en seis estados; el propietario leía crudo; el coste era
la latencia (16 min–37 h hasta `fusiona`; 14 h 50 min hasta un rescate).

**Hoy:** un solo comentario por incidencia que el motor reescribe en cada
cambio de estado (ADR-175, `.github/workflows/tablero-de-incidencia.yml`);
un marcador por parada (ADR-157/158); la red de seguridad
(`.github/workflows/reconcile-sirius-states.yml`) y el supervisor
(`sirius-supervisar`, lanzado por `.github/workflows/motor-sirius.yml`); el
reflector que escribe el desenlace en el almacén del motor (ADR-136/173).
Sigue siendo GitHub y solo GitHub (ADR-004; D3 Telegram fuera de alcance).

**Comprobación:** ejecuciones de `tablero-de-incidencia.yml` el 14-09 en la
ventana del contador de la racha; las cuatro paradas `needs_decision` del
diario: dos desde el **03-09** (M20), que no tuvieron salida posible hasta
`sirius-decidir` (ADR-189, 13-09) y siguen sin ella; una desde el 12-09 y otra
desde el 13-09.

**Veredicto: transformada.** Lo que se lee cambió; la latencia de atención,
no: la lección de ADR-198 (una pregunta veinte días sin que nadie la pusiera
delante) y las cuatro paradas de hoy son el mismo hecho. Y la red de seguridad
estuvo 35 días ciega sin que nadie lo notara (ADR-193): la vigilancia de la
vigilancia sigue siendo humana.

### PROC-004 — Autorizar el merge

**Agosto:** comentar `fusiona` en la incidencia; fricción de canal y de
contabilidad del head aprobado.

**Hoy, dos vías.** Para el motor, `fusiona` sigue
(`.github/workflows/merge-sirius-work.yml`,
`scripts/automation/sirius_merge_on_command.sh`). Para las PR de sesión
interactiva, el botón de GitHub: la noche del 14-09 el propietario fusionó
trece ADR (190–202) haciendo «de cola a mano, poniendo la siguiente al día
antes de tocarla» (memoria de sesión, 14-09).

**Comprobación:** el workflow se dispara con **cada** comentario de incidencia
—2 992 ejecuciones en su historia—; de las 100 últimas (13→19-09), 99 se
saltaron a nivel de job y una fusionó de verdad: #615, el 14-09 00:19. Los 59
encargos `delivered` del diario llevan su commit de fusión. Las fricciones de
agosto están resueltas por ADR-069, 142, 187, 191 y 200.

**Veredicto: vigente.** Lo que ADR-200 no ha demostrado aún es su primera
puesta al día real de una rama que espera
(`docs/audits/PENDIENTE_Y_POR_QUE_2026-09-14.md`, punto 4).

### PROC-005 — Desatascar estados parados

**Agosto:** la mayor bolsa de coste humano: 15–20 episodios en tres semanas y
media, forense a mano, retirar etiquetas «a conciencia».

**Hoy:** la mitad mecánica es del motor —bloque C1 cerrado: el supervisor
cierra lo perdido y reactiva o sustituye; rearme único ante una parada de
infraestructura (ADR-141); relanzar Quality (149); retomar desde donde se
quedó (176); `ci-pending` que distingue «todavía no» de «nunca» (194)—. La
mitad de decisión sigue humana pero ya no es cirugía: `continua`
(`.github/workflows/resume-sirius-on-command.yml`; ADR-030, 035, 147, 199) y
`sirius-decidir` para las paradas sin incidencia (ADR-189). Y una forma nueva:
**re-despachar** la misma orden.

**Comprobación:** en el diario, 9 objetivos tienen más de un encargo y suman
20 de los 91 (22 %): M13 tres veces hasta entregarse; la guarda de citas,
cancelada a las 00:30 del 14-09 y entregada con el despacho de la 01:08. Estado
del diario: 59 entregados, 27 cancelados, 4 esperando decisión, 1 activo.

**Veredicto: transformada.** El riesgo que agosto nombró sigue: la red de
seguridad que vigila lo parado puede quedarse ciega sin avisar (ADR-193).

### PROC-006 — Depurar y endurecer la propia automatización

**Agosto:** la mayor familia de PR; la advertencia: «un plan de agentes que
añada máquinas sin presupuestar su mantenimiento repite este coste».

**Hoy:** la advertencia se cumplió. Clasificando los 196 ADR por su título
(EST), 44 tratan de la aplicación y **152 del motor, del método o de la
automatización**. Veinte ADR el 13 y 14 de septiembre; dieciocho el 21 de
agosto. La mina mide sus propios ciclos (ADR-174, dos ediciones) y el detector
de familia repetida ganó autoridad con cifras (ADR-199: 14 aciertos y 2 falsos
sobre 16).

**Comprobación:** títulos de `docs/decisions/`; fechas `- Fecha:`.

**Veredicto: vigente**, y dominante. Lo que agosto pedía —menos rondas por
PR— tiene mecanismo desde ADR-155 (corrector por hallazgo), 150 (tiempo al
corrector) y 199 (la familia repetida detiene el ciclo).

### PROC-007 — Coordinar la revisión adversarial

**Agosto:** `@codex review` a mano; detección del resultado de Codex rota.

**Hoy:** en el ciclo del motor es automática: el recolector lee los hallazgos
que Codex publica (ADR-156), reintenta su fallo transitorio (146), admite su
«sin hallazgos» (023); los identificadores `CODEX-001` y `CLAUDE-REV-612-001`
del historial de ADR-188 (13-09) son sus huellas. En las PR de sesión
interactiva sigue a mano y se ha vuelto regla: «cinco hallazgos, los cinco
ciertos, cero falsos… no fusionar sin revisión externa» (memoria de sesión,
12-09, cuatro rondas traídas por el propietario para #586–#589).

**Veredicto: transformada.** La hipótesis H1 de la nota queda confirmada por
la memoria de sesión; su contenido —qué se pega, cuánto cuesta— es del paso 3.

### PROC-008 — Validación manual en Windows real

**Agosto:** el bloqueo material de V8; la PR #122 llevaba más de nueve días
esperando una ejecución correcta.

**Hoy:** la PR #122 se fusionó el **17-08** con B13 y B14 ejecutados en
Windows real y la declaración de aceptación de Sirius 0.1 (PA-001…PA-E2E-01;
PS-01 a PS-07 «como un juicio global sobre las siete»). Desde entonces:
`.github/workflows/quality-windows.yml` tiene **cero ejecuciones en toda su
historia**; ningún ADR fechado desde el 15-08 trata una validación física
—los cinco que nombran Windows (025, 032, 044, 076, 153) hablan del runner o de
`scripts/check.ps1`—; Sirius 0.2 se mide con dobles y con el banco de 47
casos; los pendientes físicos de agosto (#127, #134) siguen abiertos e intactos
desde agosto.

**Veredicto: vigente, sin ocurrencia observable desde el 17-08.** Hoy no
bloquea nada porque 0.1 está aceptado; volverá a bloquear cuando 0.2 toque la
interfaz. Es el único proceso físico del inventario y el único sin ninguna
huella en cinco semanas.

### PROC-009 — Mantener el registro de estado y evidencia

**Agosto:** una tabla a mano (`docs/implementation/V8_EXECUTION.md`) que el
implementador actualizaba en la misma PR.

**Hoy:** vistas generadas y guardas derivadas. `MEMORIA.md` la genera un
comando y una prueba falla si no coincide (ADR-171, 196; `tests/engine/test_memoria.py`);
`DESENLACES.md` lo escribe el motor tras cada reflejo (ADR-171, 173);
`docs/audits/registro_defectos.yml` deriva su inventario de los ADR que
declaran lección (ADR-182, 192): 55 cerrados, 1 abierto;
`docs/implementation/bloques_del_motor.yml` sigue a mano (ADR-087). La
conciliación pasó de asientos sueltos a **barridos con evidencia**: dos el
14-09 (`docs/audits/evidencia-cierra-los-defectos-ya-arreglados.md`,
`docs/audits/evidencia-fix-cierra-los-defectos-de-la-noche.md`: siete y seis
defectos que decían `abierto` con su arreglo ya en `main`).

**Comprobación de lo que sigue derivando:** `bloques_del_motor.yml:295` dice
que el descomponedor queda «APLAZADO, no descartado» citando ADR-089, cuando
ADR-198 (14-09) lo descartó; el diario conserva un encargo `active` desde el
28-08 (WI-20260828-122242) cuya incidencia #392 está cerrada.

**Veredicto: transformada.** La parte generada no deriva; la parte a mano,
sí, y `MEMORIA.md` publica lo que la parte a mano dice.

### PROC-010 — Reconciliar documentación derivada

**Agosto:** sin disparador; la KB auditaba el contrato v1.1 cuando el vigente
era v1.6.

**Hoy:** `docs/operations/CLAUDE_SIRIUS_KNOWLEDGE_BASE.md` sigue diciendo
**v1.1**; el vigente es **v1.10**: de cuatro versiones atrás a nueve.
`docs/operations/CLAUDE_PROJECT_ONBOARDING.md` conserva su «Estado ejecutivo a
20 de julio de 2026». Y ya nadie las manda leer: `AGENTS.md`, `CLAUDE.md` y las
skills no las citan; el camino de entrada es `MEMORIA.md`. Solo las citan la
auditoría de agosto, la de julio y ADR-012. Se midió y se decidió **no**
ampliar la guarda de citas a `docs/` (ADR-190: 0 defectos reales, 23 falsos), y
no existe guardián de prosa (ADR-177).

**Veredicto: vigente, sin dueño, y resuelta de hecho por abandono.** Familia
`pieza-sin-lector` (ADR-175, 183). La decisión que falta es del propietario:
archivar —que en esta casa no es borrar, ADR-195— o regenerar.

### PROC-011 — Registrar decisiones

**Agosto:** cuatro registros paralelos; siete ADR en cuatro días; los siete
seguían «PROPUESTO» pese a estar fusionados.

**Hoy:** 196 ADR; 34 de los 38 días entre el 08-08 y el 14-09 tienen alguno.
Herramientas: la skill `adr` (número contra el remoto: ADR-032, 180), el bloque
`## La lección` obligatorio desde ADR-174, el índice completo en `MEMORIA.md`.
Los cuatro registros siguen existiendo (`docs/decisions/`, contrato §10,
`docs/evolution/DECISIONS.md`, `docs/robotics/head/DECISIONS.md`) y
`MEMORIA.md` indexa solo el primero.

**Comprobación:** estados en el índice de `MEMORIA.md`: **150 PROPUESTO, 44
APROBADO, 1 ACEPTADO, 1 RECHAZADO**, todos fusionados.

**Veredicto: vigente, multiplicada por veintiocho.** La fricción de agosto
persiste a escala: tres de cada cuatro decisiones fusionadas dicen que están
propuestas. Decisión pendiente: qué significa PROPUESTO en un ADR fusionado,
o que la plantilla lo diga.

### PROC-012 — Redactar especificaciones y documentos de dirección

**Agosto:** conversación → documento → PR → a veces DOCX materializado.

**Hoy:** la clase `documentacion` del motor (bloque C3, ADR-066) produjo la
Definición de Producto 0.2 (#409, 28-08), la Arquitectura Técnica (#415,
29-08) y el Plan de Pruebas (#419, 29-08), y después #429, #439, #478 y #627.
El paso «workflow materializa DOCX» **caducó de hecho**:
`.github/workflows/materialize-approved-docx.yml` tiene cinco ejecuciones en
su historia, cuatro el 22-07 y la quinta el 08-09 sobre #567 **en rojo**, y
ningún ADR ni entrada del registro de defectos la nombra.

**Veredicto: transformada**, y su paso final caducado sin que nadie lo
leyera: `pieza-sin-lector`. Decisión pendiente: retirarlo o arreglarlo.

### PROC-013 — Reconstruir contexto al abrir cada sesión

**Agosto:** cinco a doce documentos obligatorios; la KB que debía acelerar el
onboarding estaba obsoleta; 24 sesiones en un mes.

**Hoy:** `MEMORIA.md` entero primero (ADR-171; «Antes de RESPONDER» de
`AGENTS.md`, ADR-091), después la memoria de sesión con el espacio canónico
(ADR-172), después solo lo que la tarea necesite. El coste cambió de forma:
de mantener fieles doce documentos a mantener una vista generada que quepa en
una lectura, que se quedó a 630 bytes de no caber (ADR-196).

**Comprobación:** esta sesión, el 15-09 y el 19-09; las siete sesiones de
septiembre del índice.

**Veredicto: transformada** (hipótesis H5 confirmada desde el repositorio).
La KB quedó fuera del camino sin que nadie lo decidiera (PROC-010).

### PROC-014 — Investigación técnica

**Agosto:** spikes en una sesión masiva; la investigación con fuentes externas
ocurría fuera, sin traza.

**Hoy, dos transformaciones seguidas.** Primero entró en el motor: bloque B1
cerrado (28-08), clase `investigacion`, `.github/workflows/investigar-orden.yml`,
investigador medido y atestado (ADR-095, 098, 099), tres informes de orden en
`docs/investigaciones/` (#386, #483; #392 cancelado). Después el carril se
retiró (ADR-161, ejecutado por ADR-163, 08-09;
`docs/implementation/work_engine/carriles_retirados.json`; el despachador
explica y sale con código 6). Las dos investigaciones del 11-09 las hizo la
sesión interactiva («autor: la sesión interactiva de Claude Code»), con la
convención nueva: fecha y «caduca con» (`docs/investigaciones/README.md`).

**Veredicto: transformada dos veces.** Lo que agosto pedía —encargos acotados
con fuentes contrastadas— existió del 28-08 al 08-09 y hoy vuelve a ser
trabajo de sesión, con mejor convención de caducidad que entonces.

### PROC-015 — Auditorías del repositorio y del sistema

**Agosto:** cinco auditorías en un mes; informes que envejecen sin caducidad.

**Hoy:** misma trayectoria que PROC-014: el auditor por etiqueta (ADR-016) y
el bloque C4 «la auditoría dentro del motor», y el carril retirado (ADR-161/163).
Lo periódico ganó reloj: la mina (`docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-08.md`,
`docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09-14.md`) dispara el
día 1 de cada mes (ADR-201, `.github/workflows/mina-mensual.yml`; el primer
disparo, el 01-10, está por demostrar). Las auditorías puntuales siguen en
sesión: `docs/audits/PENDIENTE_Y_POR_QUE_2026-09-14.md` y esta.

**Veredicto: transformada.** La caducidad se resolvió para las
investigaciones y no para las auditorías: la de agosto tiene una adenda, no
una fecha de caducidad, y esta tampoco la tendrá hasta que se decida el
criterio.

### PROC-016 — Seguimiento de defectos intermitentes

**Agosto:** la prueba `test_streaming_message_grows_without_overlapping_neighbours`
fallaba una de cada cuatro veces; el propietario decidió convivir y dejar la
incidencia #137 abierta a propósito «porque cerrarla borraría el único sitio
donde está escrito por qué esa prueba falla a veces».

**Hoy:** el seguimiento de defectos es un registro versionado
(`docs/audits/registro_defectos.yml`; ADR-047, 075, 080, 182, 192): la
incidencia se cierra **con** el registro. El caso de agosto no sobrevivió al
cambio: #137 se cerró el **23-08** como `completed`, sin PR y sin entrada en el
registro; la prueba sigue en `tests/gui/test_conversation_ui.py:1366` sin
ninguna marca. En la única ejecución completa de esta sesión pasó, que no
prueba nada en ninguna dirección.

**Veredicto: transformada, con una pérdida concreta.** El único sitio donde
estaba escrito el porqué se cerró y el porqué no se movió. `pieza-sin-lector`.
Decisión pendiente: registrarlo o darlo por muerto, con la razón escrita.

### PROC-017 — Medición de rendimiento y evidencia antes/después

**Agosto:** dos PR con criterio publicado antes de medir (ADR-007).

**Hoy:** el banco de 47 casos (ADR-104), la ola de paridad medida ADR tras
ADR (109→117), los suelos escritos como pruebas `xfail(strict=True)` que
pasarán solas el día que se alcancen (las dos que la suite lista hoy), las
cifras ancladas al árbol que las produjo (ADR-154), el límite de 300 ms
suspendido mientras se mide (ADR-125).

**Comprobación:** ADR-202 (14-09): 7/47 aciertos contra un suelo de 29/47;
682/671/669 ms contra 300.

**Veredicto: vigente y ampliada.** Lo que agosto pedía —generalizar «criterio
publicado antes de medir»— es hoy la primera línea de cada nota de arranque.

### PROC-018 — Gobernanza y backlog

**Agosto:** #8, #9, #10, #14, #15 y #25 fósiles desde julio; decisión
pendiente: mantener, archivar o sustituir.

**Hoy:** #8, #9, #10, #11, #12, #13, #14, #15 y #25 sin tocar desde el 15–17
de julio; #127 y #134 desde agosto (listado de incidencias abiertas, 15-09).
`PENDIENTE_Y_POR_QUE_2026-09-14.md` §D las reclasificó: «son el sitio donde
vive el plan; cuentan como abiertas porque nunca se cierran». Es una postura
escrita, no la decisión que agosto pedía.

**Veredicto: vigente, sin cambios.** Misma familia que PROC-010.

### PROC-019 — Transporte de contexto y autorizaciones entre herramientas

**Agosto:** el propietario como bus; la dirección: el work item como canal.

**Hoy, cerrado por diseño en varios flancos:** orden → incidencia
(`sirius-despachar`); autorización en canal verificable (`fusiona`,
`continua`, `sirius-decidir`; el permiso escrito acredita la salida de una
parada, ADR-147); GitHub → almacén del motor (reflector, ADR-136/173); sesión
↔ sesión (`MEMORIA.md` y la memoria de sesión, ADR-171/172); el run firma lo
que hizo (ADR-140). **Flancos que siguen a mano, con fecha:** ChatGPT y Codex →
sesión (12-09, cuatro rondas de hallazgos pegados); Windows → repositorio (sin
ocurrencia desde el 17-08); y las propias exportaciones de conversación de
esta auditoría (19-09: el propietario moviendo a mano lo que ninguna
herramienta mueve).

**Veredicto: transformada.** Lo que queda a mano es exactamente lo que el
paso 3 tiene que ver.

### PROC-020 — Operar sesiones de agentes

**Agosto:** 24 sesiones en un mes; el propietario como operador.

**Hoy:** 42 sesiones de Claude Code entre el 14-07 y el 15-09 (27 en julio, 8
en agosto, 7 en septiembre); 25 abiertas desde el móvil; 6 terminaron con la
IA esperando una respuesta. Los «runbooks versionados» que agosto proponía
existen como skills (`adr`, `disciplina-evidencia`, `work`, `check`) y como
`AGENTS.md`. ADR-160 fijó el reparto —Sirius es el compañero, el motor ejecuta,
las IA externas son el lugar de trabajo— y ADR-198 dejó en la sesión partir
los objetivos grandes. La métrica de agosto, «intervenciones del operador por
sesión», sigue sin medirse.

**Veredicto: vigente, con más estructura.** El encargo de esta auditoría
—«antes de elegir skills»— es este proceso mirándose a sí mismo.

### PROC-021 — Gestionar coste y modelos de agentes

**Agosto:** el coste se veía solo cuando dolía.

**Hoy, en el motor:** presupuesto con corte (ADR-043, 045, 092;
`src/sirius_engine/domain/budget.py`), modelo por run (ADR-054,
`src/sirius_engine/domain/run.py`), modelos atestiguados por el servidor y no
por un papel (ADR-095, `scripts/investigacion/modelos_atestiguados.yml`), opus
para los tres agentes (ADR-138), Quality Windows solo bajo demanda (cero
ejecuciones), y el disparo por comentario de `merge-sirius-work.yml` salta a
nivel de job: sus 2 992 ejecuciones no cuestan minutos. **Fuera del motor no
hay libro mayor:** el coste de las sesiones interactivas existe solo como campo
de la plataforma, y ahí está la concentración: tres sesiones largas desde el
móvil (29-07, 15-08, 08-09) reúnen nueve de cada diez dólares declarados en
31 sesiones, y la mediana está dos órdenes de magnitud por debajo del máximo.

**Veredicto: transformada a medias.** Las cifras se entregaron al propietario
y no se publican. Lo que agosto pedía —un libro mayor de ejecuciones— existe
para el motor y no para donde está el gasto.

## Lo que ha nacido después del 11-08 y se repite

Dos procesos con dos o más ocurrencias observables desde el repositorio. Mismo
formato de ficha que agosto.

### N-01 — El ritual de evidencia: nota de arranque → evidencia → ADR con su lección

- **Disparador:** cualquier trabajo del repositorio (ADR-001); desde ADR-091,
  también responder.
- **Objetivo:** que nada se afirme sin la comprobación publicada antes, y que
  toda decisión quede localizable con la lección que deja.
- **Pasos:** nota de arranque (cuatro preguntas, criterio de parada) → trabajo
  → mutaciones vistas caer → evidencia → ADR con `## La lección` (ADR-174) →
  regenerar `MEMORIA.md` (ADR-171) → PR → revisión (externa, si es PR de
  sesión) → fusión → registro de defectos (ADR-182, 192).
- **Quién:** redactan la sesión interactiva o el corrector del motor; decide y
  fusiona el propietario.
- **Frecuencia:** 27 notas de arranque y 51 evidencias en `docs/audits/`, 196
  ADR, 29 de ellos con bloque de lección, entre el 08-08 y el 14-09.
- **Tiempo humano:** EST, no medible desde el repositorio. Lo que sí se ve:
  veinte ADR en dos días.
- **Fricción:** el hook `.claude/hooks/recordar_parada.py` no reconoce
  `arranque-*.md` aunque su mensaje lo nombre (visto el 19-09); 150 ADR
  fusionados en PROPUESTO; cuatro lecciones sin prueba que las haga cumplir,
  las cuatro declaradas a propósito.
- **Riesgo si se automatiza:** el propio ADR-001 lo dice: el método lo
  sostiene una persona, no un mecanismo; la puerta que bloqueaba el push se
  retiró tras quince defectos.
- **Decisión humana:** la decisión, y el criterio de parada.
- **Evidencia:** `docs/audits/`, `docs/decisions/`, skill
  `disciplina-evidencia`, `tests/automation/test_mina_de_lecciones.py`.
- **Oportunidad:** no mecanizar el fondo; medir su coste. ADR-201 lo hará cada
  mes para los ciclos del motor; para las sesiones, nadie.
- **Métrica:** ADR con lección y prueba / total; notas de arranque con
  evidencia pareja / total.

### N-02 — Decidir en ráfaga

- **Disparador:** una sesión larga —desde el móvil, según el índice— o «antes
  de dormir, para que el trabajo nocturno no se pare» (memoria de sesión,
  14-09).
- **Objetivo:** desbloquear varios trabajos de una vez.
- **Forma observada:** varias decisiones en conversación → ADR en cadena el
  mismo día o el siguiente. Picos: 18 ADR el 21-08, 12 el 22-08, 11 el 25-08,
  10 el 05-09, 10 el 08-09, 10 el 12-09, 13 el 14-09.
- **Quién:** decide el propietario; escribe la sesión.
- **Frecuencia:** siete días con diez o más ADR, de 38.
- **Tiempo humano:** EST; no observable.
- **Fricción:** lo que se decide de viva voz y no llega al ADR (ADR-195, 202);
  la #341 esperó veinte días una respuesta (ADR-198); las cuatro paradas
  `needs_decision` esperan hoy.
- **Riesgo si se automatiza:** ninguna automatización decide, y eso no cambia.
- **Decisión humana:** todas.
- **Evidencia:** fechas `- Fecha:` de `docs/decisions/`; memoria de sesión
  del 14-09; `DESENLACES.md`.
- **Oportunidad:** la de ADR-195 y 202: que la ráfaga deje rastro en el
  momento, no después; y que las preguntas pendientes tengan quien las ponga
  delante —ADR-198 dejó escrito «ninguna prueba» a propósito—.
- **Métrica:** decisiones de viva voz que llegan a ADR el mismo día / total;
  solo medible con el paso 3.

### Candidato que espera al paso 3

- **N-03 — La revisión externa traída a mano** (hipótesis H1): un episodio
  con cuatro rondas en la memoria de sesión (12-09) y una regla nacida de él.
  Para la ficha hace falta el contenido: qué se pega, cuánto ocupa, cuánto
  tarda.

## Lo que se ve al juntar los veredictos

Observaciones del paso 2, a confirmar o desmentir en el 3:

1. **El motor se quedó con la mitad mecánica de ocho fichas** (001, 002, 003,
   005, 009, 012, 014, 019) y no con la decisión de ninguna. Lo que le queda
   al propietario está concentrado: decidir en las paradas, fusionar, dirigir
   sesiones y sostener el ritual.
2. **`pieza-sin-lector` aparece en cinco fichas** —la KB y el onboarding
   (010), el workflow DOCX en rojo (012), el porqué de la prueba intermitente
   (016), las incidencias de gobernanza (018) y la línea de D4 (009)—. Agosto
   la llamaba «deriva documental» y la contaba entre sus tres bolsas; el
   repositorio la nombró después como familia (ADR-175, 183) y ahora se cuenta
   sola. Lo que no ha cambiado: nadie tiene asignado leer lo que nadie lee.
3. **Se decide en ráfaga y se registra en ráfaga**, y tres de cada cuatro
   decisiones registradas dicen que siguen propuestas.
4. **Lo físico no ha dejado huella en cinco semanas**, y no bloquea nada
   mientras 0.2 no toque la interfaz.
5. **El dinero está donde no hay libro mayor**: en tres sesiones largas desde
   el móvil, no en el motor.

## Las ocho categorías del propietario, actualizadas tras el paso 3

| Categoría | Fichas | Estado |
|---|---|---|
| investigación | PROC-014 | transformada dos veces |
| decisiones | PROC-011, N-02 | vigente, multiplicada; se decide en ráfaga |
| documentación | PROC-009, 010, 012, 013 | tres transformadas, una vigente sin dueño |
| ejecución | PROC-002…007, 020, 021 | una caducada, cuatro transformadas, tres vigentes |
| cierre | PROC-004, 009, N-01 | vigente; transformada; el ritual |
| **conversación** | **C-01** | **con ficha desde el paso 3**, vista desde el lado claude.ai |
| **ideas** | **C-02** | **con ficha desde el paso 3** |
| **debate** | **C-03, N-03** | **con ficha desde el paso 3** |

**Regla de las dos rondas: disparada.** El paso 2 encontró omitida en el
inventario de agosto una sola familia —lo que la sesión interactiva hace por el
propietario entre la conversación y el repositorio— y el paso 3, con las
conversaciones delante, encuentra exactamente la misma: las tres fichas nuevas
y N-03 son todas de esa familia. Dos rondas seguidas con la misma familia
omitida obligan a revisar la taxonomía, no a seguir añadiendo fichas. La
taxonomía A–F de agosto (transferencia, documentación, investigación/decisión,
GitHub/coordinación, validación/evidencia, administración de agentes) no tiene
sitio para el trabajo que ocurre de viva voz. Se añade una letra:

- **G — conversación y decisión de viva voz**: cómo entra una idea, cómo se
  debate hasta decidir, y por dónde sale (o no) hacia el repositorio. Fichas:
  C-01, C-02, C-03, N-03; y N-02 comparte frontera con C-03.

## Paso 3 — el punto ciego, visto desde claude.ai (20-09-2026)

**Qué se leyó**, según la adenda de la nota de arranque: las 12 conversaciones
de claude.ai dentro del alcance, enteras y en orden (237 mensajes; los del
propietario íntegros, los del asistente hasta 2 500 caracteres); después, y no
antes, las fuentes secundarias: la memoria que claude.ai guarda del proyecto
«Sirius 0.2» y de las preferencias generales (nueve ficheros; los de la cabeza
robótica, de otros proyectos y de personas quedaron sin abrir) y las dos
reflexiones mensuales generadas por claude.ai (junio y julio). **Qué no se
leyó**: el lado ChatGPT de la conversación —que en julio era el que redactaba
los documentos— porque su exportación no ha llegado; las transcripciones
locales de Claude Code; y las cinco conversaciones de julio que la exportación
trae vacías. Las tres fichas que siguen están construidas sobre el lado
claude.ai y así hay que leerlas.

**Cómo se cita.** El repositorio es público. De las conversaciones se citan
solo frases cortas del propietario sobre cómo quiere trabajar; nada personal,
ninguna cifra de dinero, ningún dato de terceros, y las escaladas de
frustración —que existen y son datos— se describen, no se transcriben.

### C-01 — La conversación: cómo entra el trabajo

- **Disparador:** una idea, una duda o un documento que auditar; casi siempre
  desde el móvil.
- **Objetivo:** que la IA entienda qué quiere sin que él tenga que escribir un
  encargo formal.
- **Entradas observadas:** dictado por voz, con erratas sistemáticas que el
  propio modelo anota («sus mensajes llegan por dictado de voz», memoria de
  claude.ai del 21-07); capturas y fotos en vez de descripciones (una lista de
  skills ajena, una infografía, la pantalla del ordenador, la elección de rama
  en Claude Code); documentos `.docx` adjuntos; y encargos largos redactados
  por otra IA y pegados tal cual (24-07 05:17; 25-07 00:56).
- **Pasos:** mensaje corto o dictado → la IA propone → él corrige (ver C-03)
  → cuando hace falta ejecutar o consultar otra herramienta, la IA escribe un
  **prompt puente** que él pega en Claude Code, ChatGPT o Codex y cuyo
  resultado trae de vuelta. El prompt puente aparece al menos ocho veces en las
  doce conversaciones.
- **Quién:** el propietario como bus entre tres IA; la memoria de claude.ai lo
  describe igual: Claude audita e investiga, ChatGPT redacta, «documents
  transferred between them».
- **Frecuencia:** 12 conversaciones dentro del alcance en ocho semanas; 8 de
  ellas con fotos o adjuntos; 334 adjuntos en las 38 de la exportación.
- **Tiempo humano:** las horas son de madrugada: cinco de las doce empiezan
  entre la 01:15 y las 05:50, y la reflexión de julio sitúa el pico a las dos
  de la madrugada. La conversación 02 ocupó dos noches; la 04, una hora y
  cuarenta minutos. EST: no hay medida de esfuerzo.
- **Fricción, medida:** el pegado largo desde el móvil llegó vacío tres veces
  seguidas (25-07, 14:03–14:17); cinco conversaciones de julio están vacías en
  la exportación; y tres veces la IA no miró lo que ya estaba subido a las
  fuentes del proyecto —el repositorio (25-07 21:09), un documento aprobado
  (25-07 23:19) y un fichero que faltó seis rondas (23-07 a 24-07)—; las tres
  produjeron escaladas. La memoria de claude.ai lo tiene registrado como regla
  desde entonces: «comprobar primero las fuentes del proyecto antes de pedir
  que se vuelva a subir nada».
- **Riesgo si se automatiza:** ninguno aquí: es el canal humano, y es el que
  el propietario quiere conservar.
- **Decisión humana:** toda.
- **Evidencia:** conversaciones 01–12; memoria de claude.ai (preferencias,
  21-07; proyecto Sirius 0.2, 07-09); reflexión de junio («el contexto llega
  en notas de voz y capturas, no en encargos escritos»).
- **Oportunidad:** la que él mismo pidió el 15-09 al abrir este encargo: no
  tener que pensar en cada momento cómo se hace lo que ya se ha hecho mil
  veces. La IA lo dijo el 24-07 con otras palabras —un sitio que guarde el
  estado y las reglas ahorraría re-explicar cada sesión— y hoy existen dos:
  `MEMORIA.md` y la memoria de sesión (ADR-171, 172). Lo que aún no está
  escrito en el repositorio es el **método de la conversación** (C-03).
- **Métrica:** mensajes de re-explicación por conversación; adjuntos vacíos;
  veces que la IA pide algo que ya estaba subido.

### C-02 — Las ideas: cómo nace y se filtra una idea

- **Disparador:** algo visto fuera —una infografía, una skill ajena, un
  producto (n8n, Obsidian, Memanto, un control de cámaras)— o una molestia
  propia («quiero poderme ir a dormir y que trabaje», «el revisor siempre
  encuentra algo», «siempre hacemos igual»).
- **Objetivo:** saber si merece la pena sin que le «vendan la moto», que es
  su expresión.
- **Pasos:** la trae dictada → pide opinión o investigación acotada
  («investigación normal, no te flipes») → la IA la contrasta con lo que ya
  existe y, cuando puede, con datos suyos —el banco de 47 casos contra
  Obsidian y contra Memanto— → él decide: adoptar (el revisor independiente, la
  memoria entre sesiones), aparcar (la orquestación grande; n8n como brazo, no
  como cerebro), descartar (Obsidian; el control de cámaras) o aplazar la
  decisión a sí mismo («lo decidiré yo más adelante»).
- **Quién:** él propone; la IA hace de contrario con datos.
- **Salida, y aquí está el hueco:** casi nunca un registro. De las ideas
  leídas, las que llegaron al repositorio lo hicieron semanas después y por
  otra vía: la del revisor y los permisos (24-07) es la frontera de ADR-002
  (09-08), sin cita; la del modelo local intercambiable (10-08) es la serie
  ADR-104…132 (29-08 a 04-09), sin cita; la del investigador que lee blogs en
  vez de código (04-09) es ADR-161/163 (08-09), sin cita. Y **«aparcado» no
  tiene sitio**: la propia IA dijo el 10-08 «apúntalo como idea aparcada» y no
  había dónde; la orquestación grande, aparcada el 24-07, volvió a aparecer el
  16-09 como si fuera nueva.
- **Frecuencia:** nueve ideas en doce conversaciones.
- **Fricción:** la IA se desvía del encargo literal o sobreplanifica, y eso
  produce las escaladas; las ideas aparcadas sin registro reaparecen.
- **Riesgo si se automatiza:** convertir exploración en decisión, que
  `AGENTS.md` prohíbe.
- **Decisión humana:** siempre.
- **Evidencia:** conversaciones 04, 05, 06, 08, 10, 11, 12; reflexión de junio
  («detectas lo que no encaja antes de poder decir por qué»).
- **Oportunidad:** un sitio para «aparcado» y «descartado, con la razón». Es la
  lección de ADR-198 y ADR-202 aplicada a las ideas y no solo a las
  decisiones; `docs/audits/PENDIENTE_Y_POR_QUE_2026-09-14.md` §E lo hizo una
  vez para incidencias y no volvió a hacerse.
- **Métrica:** ideas que reaparecen sin registro / ideas aparcadas.

### C-03 — El debate: cómo se discute hasta decidir

- **Disparador:** una propuesta de la IA que, en sus palabras, «seguro tiene
  fallos».
- **Objetivo:** llegar a una conclusión hablando, no aceptar la primera
  respuesta.
- **Pasos, en el orden en que la conversación 04 (24-07, 03:13–04:54) los
  enseña, y que las demás repiten:**
  1. **Veto al plan prematuro:** «estamos explorando, hablando, deja de hacer
     planes».
  2. **Exigir realidad antes de opinión:** «ni siquiera sabes cómo es
     realmente la automatización que tengo» → prompt de diagnóstico a Claude
     Code → resultado de vuelta.
  3. **Recortar el alcance:** «lo de los tokens bórralo».
  4. **Una recomendación, no un menú:** «no me des opciones, dime cuál es el
     mejor».
  5. **Autoauditoría:** pedir a la IA que contradiga y audite lo que ella
     misma acaba de proponer (24-07 04:36; también el 10-08 con Obsidian).
  6. **Corregir con datos cuando la IA se equivoca**, y ganar: la versión de
     un modelo (24-07), el repositorio que sí estaba en las fuentes (25-07),
     el banco de 47 casos (10-08).
  7. **Cerrar por tamaño:** «hablando se llega a conclusiones… hay que ir poco
     a poco… dentro de una semana vengo y te digo cómo mejorarlo».
- **Quién:** él dirige; la IA propone y se audita.
- **Salida:** una decisión pequeña —«revisor sí; la orquestación, no ahora»—
  que sale como prompt puente o como documento «con las decisiones cerradas
  dentro, para que no me las reabra» (10-08). Casi nunca como registro en el
  momento: ver la trazabilidad de C-02.
- **Frecuencia:** ocho correcciones en la 04; dos rondas sobre Obsidian en la
  05; tres en la 10; dos en la 12; dos preguntas de método en la 02 («¿qué te
  parece la estructura que recomienda ChatGPT?», «¿qué documentos nos faltan,
  lo estamos complicando?»).
- **Tiempo humano:** una hora y cuarenta minutos la 04, de madrugada.
- **Fricción:** la IA responde con planes, menús o texto largo; el propietario
  declara que no puede verificar por sí mismo buena parte de lo técnico —lo
  dice en la 04 y la memoria de claude.ai lo registra— y por eso exige
  «práctico, profesional y directo; si hay un problema, plantéame la
  solución». Cuando se repite, escala. Dos reglas suyas más, de la misma
  familia: «primero desarrollamos y armamos, y ya luego me preguntas» (junio,
  según la reflexión) y «si te falta un documento, para a mitad y pídemelo; no
  termines sin él» (25-07).
- **Riesgo si se automatiza:** el debate es exactamente la parte que él quiere
  conservar: «yo seguiría siendo el que decide» (15-09).
- **Decisión humana:** toda.
- **Evidencia:** conversación 04 entera; memoria de claude.ai del proyecto
  («prefiere poner a prueba las ideas en diálogo antes de cualquier salida
  concreta; recomendar un solo camino, no varias opciones; rechaza la
  sobreelaboración»); reflexión de julio («mantuviste tu posición cuando la
  auditoría pasó por alto algo que tú veías»).
- **Oportunidad:** dos, y las dos las ha pedido él. Que el método del debate
  esté escrito donde toda IA lo lea —hoy vive en la memoria de claude.ai y en
  la de sesión, no en el repositorio; `AGENTS.md` solo tiene una de sus
  reglas, «búscalo, no me lo digas de memoria» (ADR-091)—. Y que la decisión
  con que termina el debate deje rastro en el momento (ADR-195, 202).
- **Métrica:** correcciones hasta la primera respuesta aceptada; decisiones del
  debate que llegan a un registro el mismo día.

### N-03 — La revisión externa traída a mano: confirmada, y con dos formas

La hipótesis H1 de la nota de arranque queda confirmada y precisada.

- **Forma de julio:** ChatGPT redacta el documento, Claude lo audita, ChatGPT
  corrige; él transporta el `.docx` en cada sentido. En la conversación 02, de
  B02 a B08 más el Método, la Corrección Transversal, el Plan de Pruebas,
  ARQ-00 y ADR-001: unas veinte versiones auditadas en dos días y medio, con
  20–30 minutos por versión producida fuera y 3–5 por auditoría dentro. Sus
  mensajes en ese tramo son de una a tres palabras o solo el adjunto. El
  paquete de fuentes incompleto —un fichero que faltó seis rondas seguidas,
  unas 41 horas de reloj— es la fricción más cara que se ha medido en esta
  auditoría; la reflexión de julio lo señala también: «el arreglo a veces iba
  por detrás del hallazgo».
- **Forma de agosto y septiembre:** Claude ↔ Claude Code por prompt puente
  (diagnósticos, instalaciones, cambios de configuración), y la revisión
  externa de las PR de sesión traída a mano y convertida en regla («no
  fusionar sin revisión externa», memoria de sesión del 12-09, cuatro rondas).
- **Lo que el repositorio absorbió:** el tramo Codex → tubería (ADR-156). **Lo
  que sigue a mano:** todo lo que pasa por claude.ai, y el transporte de
  cualquier decisión tomada allí.

### Las cinco hipótesis, contrastadas

| | Hipótesis | Resultado |
|---|---|---|
| H1 | revisión externa traída a mano | **confirmada**, con las dos formas de N-03 |
| H2 | el lote de decisiones antes de dormir | **confirmada** como deseo explícito («quiero poderme ir a dormir, decirte implementa 0.2 y que empieces bloque a bloque», 24-07) y como práctica (la 02 es nocturna; la memoria de sesión del 14-09 lo repite) |
| H3 | el ritual de evidencia es un proceso con coste | **confirmada y anterior al repositorio**: el 25-07 la propia IA avisó de «quince documentos canónicos y unas treinta auditorías para una funcionalidad que todavía no tiene una sola línea de código»; el ritual del repositorio nació doce días después (ADR-001) |
| H4 | partir un objetivo grande es conversación | **confirmada**: «¿cuál sería el siguiente documento?» (25-07), «¿qué te parece la estructura que recomienda ChatGPT?» (25-07), «dime el siguiente paso y empezamos» (04-09) |
| H5 | reconstruir contexto cambió de mecanismo | **confirmada**: el 04-08 la IA proponía un `ESTADO-SIRIUS.md` generado por Claude Code y subido a mano; hoy es `MEMORIA.md` generado y una memoria de sesión |

### Dónde se va la atención del propietario (punto 6 del criterio)

Con el límite de siempre —no hay medida de tiempo; esto es recuento de
mensajes, fechas y horas— y solo sobre el lado claude.ai más los indicios del
paso 2:

1. **El taller: método, automatización y herramientas de IA.** Cinco de las
   doce conversaciones (04, 06, 07, 08, 09), y del lado del repositorio 152 de
   196 ADR (EST). Es donde más decide y donde más corrige.
2. **La documentación de producto de 0.2 y su auditoría.** Dos conversaciones
   (01, 02) pero 105 mensajes y dos noches enteras, en julio; después
   desaparece de claude.ai y pasa al motor (clase `documentacion`).
3. **La investigación** (05, 10, parte de 11): ocho investigaciones profundas
   en una sola conversación; el modelo hace el trabajo y él dirige y decide.
4. **El uso y el coste de las herramientas** (03, 09, 12, parte de 11): una
   preocupación constante, sin instrumento propio (PROC-021).
5. **El código de la aplicación**: casi no aparece en claude.ai. Se delega a
   Claude Code y al motor; en la conversación solo entra como resultado de un
   prompt puente.

Lo que este ranking **no** ve: el lado ChatGPT, que en julio llevaba la
redacción; y las sesiones locales de Claude Code, donde vive la ejecución.

## Paso 4 — el lado de la ejecución, visto desde las transcripciones de Claude Code (20-09-2026)

**Qué se leyó**, según la adenda 2 de la nota de arranque, escrita antes de
abrir ningún fichero: `history.jsonl` entero (las 72 órdenes tecleadas en
Claude Code local entre el 13-07 y el 11-09); las 8 sesiones locales que
sobreviven a la retención de treinta días (del 16-08 al 11-09); y 5 de las 6
sesiones de la nube que el teleport trajo: las dos pruebas de julio y las tres
largas —la del ciclo de pendientes (10 y 11-08), la del empaquetado B13 (del
08 al 17-08) y la de la auditoría forense (19 y 20-09)—. En total, 13
transcripciones, 237 mensajes del propietario y 1 928 del asistente, 31
permisos denegados o rechazos y 7 interrupciones. Se leyó con el protocolo de
la adenda: los mensajes del propietario íntegros, los del asistente hasta
2 500 caracteres, de cada herramienta solo su nombre y la primera línea de su
entrada, y de los resultados solo las denegaciones y las respuestas a preguntas
de la IA. **Qué no se leyó**: 28 de las 34 sesiones de la nube, que no
bajaron; todo lo local anterior al 16-08, borrado por la retención; ChatGPT,
cuya exportación no ha llegado; y los resultados de herramienta, que son el
repositorio y salidas de comandos. Tres de las cinco transcripciones de la nube
empiezan por un resumen de compactación escrito por el propio modelo: ese tramo
se ha usado como fuente secundaria, nunca como única.

**Cómo se cita.** Igual que en el paso 3: frases cortas del propietario sobre
cómo quiere trabajar; las escaladas —hay varias, con insultos, y son datos— se
describen, no se transcriben; ninguna ruta de su máquina, ninguna cifra de
dinero.

### Lo que este lado enseña y el otro no podía

Seis hallazgos, cada uno con su fuente, de más a menos nuevo.

**E-01 — Dos modos de dirigir, y los dos existen desde julio.** Desde el
ordenador la orden llega **pegada**, redactada antes en otro sitio, con un
molde fijo: lista numerada, prohibiciones explícitas («No hagas cambios, commit
ni push todavía», «NO rebase y NO force push», «No abras todavía la PR») y el
formato exacto del informe que quiere («Dame únicamente…», «Al terminar,
confirma:…»). En `history.jsonl`, 38 de las 72 órdenes son texto pegado; la
primera sesión de la nube (18-07) ya tiene el molde entero; y las dos locales
de agosto lo aplican con puerta en cada paso —análisis → solo la skill →
pregunta de permisos → fichero temporal—: cada mensaje autoriza exactamente un
paso. Desde el móvil la orden llega **dictada y a nivel de meta**, no de tarea
(«necesito que me digas qué queda por hacer… quiero dejar cerrado este ciclo»,
10-08 20:42; «vamos a acabar con el empaquetado», 09-08 17:28), y el modelo
construye el mapa. El propietario fijó el segundo modo el 10-08 a las 21:06:
«¿tú eres el que me tiene que guiar? Y yo, el que responde y decide, porque me
pones mucho texto y yo no puedo responderte a todo… me preguntas, y yo te digo
sí, no». Es la regla que la conversación 04 dio en claude.ai el 24-07 («no me
des opciones, dime cuál es el mejor»), vista ahora en ejecución.

**E-02 — La sesión no ve a las otras sesiones, y él es el único que las ve
todas.** El 09-08 el modelo detectó en la pantalla del propietario otra sesión
compilando el mismo repositorio, y el 10-08 el propietario declaró cuatro a la
vez («las otras sesiones activas de model estudio, revisión codex claude code y
auditoría forense adr002»). Las consecuencias están en el árbol:

- la sesión del ciclo reconcilió el registro de estado y cerró B12 la noche
  del 10-08 (ADR-005, 006 y 007, fechados ese día); cuatro días después la
  sesión de B13 «reconcilió» el mismo registro sobre una rama 28 commits por
  detrás de `main` y encargó al motor construir B12 (incidencia #165, 14-08
  15:28). El implementador automático se paró solo porque el trabajo ya
  existía, y el modelo lo escribió: «me he pasado la tarde arreglando deriva
  documental en una copia caducada, con exactamente el error que estaba
  corrigiendo en los demás». De ahí nació ADR-016 «el estado se lee de main,
  no de la rama»;
- ese ADR-016 es uno de los **dos ADR-016** del registro, los dos fechados el
  14-08 y nacidos en ramas distintas. El duplicado es lo que motivó la skill
  `adr` tres días después (sesión local del 17-08), cuyo propio ADR chocó de
  número con otro que entró en `main` mientras la rama estaba abierta (029 →
  030 → hoy ADR-032), y la regla acabó en ADR-180: el número se calcula contra
  las ramas del remoto;
- el 10-08 a las 22:08 el propietario corrigió al modelo —«¿tú sabes bien lo
  que se ha hecho? Porque creo que no lo tienes»— porque Model Studio
  funcionaba con cámaras en una rama sin fusionar, con commits de esa misma
  noche, y las etiquetas de sus incidencias decían lo contrario desde el
  05-08.

El repositorio es la única pizarra compartida, y cada sesión la lee desde su
rama. El motor se dio después su tablero y su cola (ADR-175, 191, 200); las
sesiones interactivas no tienen ninguno. Esto no estaba en la ficha PROC-020 de
agosto y es la evidencia nueva más importante de este paso.

**E-03 — Corrige con hechos que el repositorio no contiene, y acierta.** Seis
correcciones suyas al cuadro del modelo, las seis verificadas después por el
propio modelo: que un `deny` gana a un `allow` (17-08 19:35); que «fallos
específicos de Windows» afirmaba de más y había que rebajarlo a lo que el dato
sostenía (18-08 15:45, con el texto sustituto redactado por él); que Model
Studio estaba hecho y «el benchmark» seguía abierto (10-08 22:08); que «todo
eso ya lo hicimos» sobre las partidas de B14 (14-08 14:51: el modelo retiró su
plan y luego también su hipótesis de recambio, «tenías razón en todo»); que la
voz está fuera del alcance de 0.1 (17-08 15:00: está en la línea 50 del
registro de estado); y que la clave real, el cierre forzado y la partida 3 ya
estaban probados (17-08). En cinco de las seis el hecho no estaba en `main`:
estaba en una rama ajena, en una prueba manual que él había hecho, o en su
cabeza. La regla 6 de C-03 («corregir con datos») se confirma; lo que añade la
ejecución es que **los datos son suyos, no del repositorio**, y por eso ninguna
lectura más cuidadosa del árbol se los habría dado al modelo.

**E-04 — Las esperas y las promesas imposibles son donde se rompe.** Las
escaladas de este lado tienen cinco disparadores medibles: una instrucción que
no sabe dónde ejecutar (14-08 14:15, «no sé ni dónde ponerla… no sé
programar»; se resolvió a la primera cuando el modelo pasó al formato *dónde /
qué hacer / qué va a salir*); creer que el modelo trabaja cuando está ocioso
esperando su turno (10-08, ocho líneas dictadas en un minuto sin actividad del
modelo entre las 15:17 y las 21:14); que el modelo prometa avisar («te aviso en
cuanto…», cuatro veces en la sesión del ciclo) cuando no puede hablar entre
turnos —él lo preguntó el 11-08 y el modelo lo reconoció: «fue una promesa que
no podía cumplir»—; que el modelo le pida evidencia de lo que él ya hizo (17-08
15:00 y 15:06); y una cifra presentada sin su comparación al lado (19-09: leyó
la línea base recién medida como una regresión). Al selector de opciones de la
IA lo rechazó siete veces (cinco en una noche, tecleando «continúa» cada vez,
mientras el modelo reescribía el mismo mapa cuatro veces en dieciocho minutos).
Nada de esto se veía desde claude.ai, donde no hay espera ni permisos.

**E-05 — El coste está donde el paso 2 dijo, y ahora se ve cómo se gasta.**
La sesión del ciclo llegó a 521 k tokens de contexto, el 52 % de su ventana,
según el informe de contexto de la propia sesión, y en ella hay 24 esperas
por temporizador; la sesión de la auditoría forense, según su propio resumen,
agotó el límite de la API de GitHub sondeando cada 45 segundos, y el 19-09
gastó ocho despertares horarios «sin cambios» esperando un `fusiona` (de 16:24
a 23:23). En el ordenador, cada sesión local carga dos plugins de memoria a la
vez —claude-mem y Supermemory; 21 skills y 14 herramientas MCP del primero—
aunque ADR-172 eligió el segundo. Y el propietario administra el coste a mano y
sin instrumento: cambia de modelo por consumo («ya está aquí opus para
continuar con las vigilancias, que si no fable me come el uso», 19-09) y
estuvo días parado «porque se me acabó el uso» (19-09). PROC-021, confirmada
desde dentro.

**E-06 — Lo que la sesión hace por él y él no ve.** En las transcripciones el
ejecutor cumple el ritual del repositorio sin que se lo pidan: nota de arranque
como ADR en el primer commit (17-08 19:11; 10-08 21:12), siete mutaciones por
prueba nueva, línea base en `origin/main` antes de atribuir un fallo (dos
suites de ocho minutos el 18-08), criterio de parada publicado antes de medir
(10-08 21:43; 20-09 00:08 y 00:19), y la regla de las dos rondas aplicada a
mano el 19-09 —la incidencia #650 cerró en cuatro rondas donde H4 había
necesitado catorce— con una predicción escrita antes de la ronda siguiente que
se cumplió. También se retracta con evidencia («me equivoqué al recomendarte la
otra», 19-09; «era falso: Nuitka trae su propia copia», 10-08). El propietario
paga ese ritual en espera, no en trabajo, y lo llama «dar vueltas»; la tensión
entre lo que pide («hay que hacerlo bien cada cosa, pensar bien todo») y lo que
le cuesta esperar es la segunda cara de H3.

### Lo que cambia en las fichas del paso 3

- **C-01 (conversación).** Confirmada, con tres precisiones. (a) El prompt
  puente tiene **viaje de vuelta**: el 08-08 el propietario pidió al ejecutor
  «genera un prompt adecuado para dejar esto funcionando, que me voy a dormir»
  y pegó de vuelta lo que el modelo redactó; el puente lo escribe la IA en los
  dos extremos. (b) Los dos modos de E-01 son la ficha vista desde cada lado:
  pegado desde el ordenador, dictado desde el móvil. (c) Fricción nueva y
  medible: el selector de opciones (siete rechazos), el mapa repetido y la
  instrucción sin lugar; la forma que funcionó a la primera fue *dónde / qué
  hacer / qué va a salir*.
- **C-02 (ideas).** Confirmada, con un paso más que solo se ve aquí: en
  ejecución, convertir una molestia en encargo lo hace el modelo y él lo
  aprueba con una palabra («si venga», 14-08; «retira la etiqueta», 11-08;
  «fusiona», 19-09). Es justo el paso donde E-02 muerde: el encargo #165
  duplicó trabajo hecho por otra sesión. Y «aparcado» sigue sin sitio: el
  19-09 pidió que las piezas de Memanto quedaran anotadas con su momento de
  disparo, sin implementarlas; quedaron en la bitácora de la rama de la
  auditoría forense, que no tiene PR (decisión 9).
- **C-03 (debate).** Las siete reglas se cumplen en ejecución. Se añaden
  cuatro formas observadas solo aquí: (8) la corrección con hechos propios de
  E-03; (9) la petición de ser llevado un comando cada vez, con el lugar y la
  salida esperada («paso a paso», «en cristiano», «dónde lo pongo»); (10) el
  alcance por exclusión («deja Model Studio y los ADR», 11-08; «tenemos la
  automatización, no te pongas a escribir código a lo tonto», 14-08); (11) la
  autorización acotada («tienes diez o quince minutos y permiso mientras no me
  toques las otras sesiones», 10-08; la de fusionar #581, que el modelo no
  extendió a #650). Los disparadores de escalada de E-04 completan la fricción
  de la ficha.
- **N-03 (revisión externa a mano).** Tercera forma: **el propietario como
  revisor del texto de la IA**. El 18-08 sustituyó, palabra por palabra, una
  afirmación del modelo por otra que solo decía lo que el dato sostenía; es
  ADR-001 aplicado por él a la IA. Y la primera prueba observada de para qué
  existe la revisión dual está en la sesión del ciclo: el 11-08 Claude aprobó
  su propio arreglo y Codex encontró el defecto real (PR #149).

### Las fichas de agosto que este lado toca

Sin cambiar veredictos. PROC-008 (validación manual en Windows) tiene su última
ocurrencia observable el 17-08, en la sesión de B13, y coincide con lo que el
paso 2 midió. PROC-013 (reconstruir contexto) se ve en cada arranque: el 11-09
abrió cinco sesiones en tres horas y en cada una el modelo se reorientó y
preguntó la vertical. PROC-019 (transporte) es C-01 visto desde el receptor.
PROC-020 (operar sesiones) recibe E-02 y E-04 como evidencia nueva. PROC-021
(coste) recibe E-05. Y el caso de la ronda que el motor dio por «interrumpida»
sin estarlo, que la ficha PROC-005 de agosto ya recoge, nació en la sesión del
ciclo el 11-08 a las 05:12.

### Las hipótesis, otra vez

H2 (el lote antes de dormir) es la más reforzada: «sigue solo hasta acabar
B12» a las 21:42 y ocho horas y media de trabajo autónomo (10-08); «me voy a
dormir… al despertar… o ya tengas esto listo» (08-08); «déjalo compilando y
vete a dormir» (09-08). H3 gana su segunda cara (E-06). H4 se ve en el primer
minuto de la sesión del ciclo: «qué queda por hacer» → el modelo parte en B1,
B12 y cuatro PR, y pregunta por dónde. H5 tiene aquí su fallo fundacional:
ADR-016 nació de reconstruir el contexto desde una copia atrasada. H1 recibe la
tercera forma de N-03.

### Dónde se va la atención, desde este lado

Por recuento de mensajes, no de tiempo: 1) dirigir la ejecución en Windows un
comando cada vez (100 mensajes en la sesión de B13, repartidos en cuatro
tardes); 2) esperar y vigilar el motor con mensajes de una o dos palabras
separados por horas (las sesiones del ciclo y de la auditoría forense); 3)
instalar y probar herramientas de IA de noche, con sondas nombradas (16-08,
17-08, 11-09); 4) el código, solo a través del modelo. Coincide con el ranking
del paso 3: el taller primero; el código, nunca directamente.

### Regla de las dos rondas: no se dispara en el paso 4

Lo que este paso encuentra cabe en la letra G (las revisiones de C-01, C-02,
C-03 y N-03) y en fichas que ya existían (PROC-005, 008, 013, 019, 020, 021).
El único patrón nuevo, E-02, pertenece a PROC-020, que agosto ya tenía: se le
añade evidencia, no letra. **Este paso no encuentra una familia omitida de la
taxonomía.**

## Criterio de parada — estado a 20-09-2026

| # | Condición | Estado |
|---|---|---|
| 1 | veredicto fechado por ficha, con evidencia | **cumplido**: 21 de 21 (paso 2) |
| 2 | ficha para conversación, ideas y debate, o «no observable» escrito | **cumplido sobre claude.ai y sobre Claude Code**: C-01, C-02, C-03 (paso 3), revisadas con la ejecución (paso 4); el lado ChatGPT, pendiente de su fuente |
| 3 | ficha para todo proceso repetido nacido después del 11-08 | **cumplido**: N-01, N-02, N-03 |
| 4 | las ocho categorías mapeadas; taxonomía confirmada o revisada | **cumplido**: revisada por la regla de las dos rondas, con la letra G |
| 5 | cada afirmación con fuente, o marcada EST/hipótesis | **cumplido** |
| 6 | ranking de dónde se va la atención | **cumplido con límite**: recuento, no tiempo; desde claude.ai y desde Claude Code; sin ChatGPT |
| 7 | se detiene sin elegir skills | **cumplido**: ninguna elegida |
| 8 | parada por muestra agotada | no aplicó: las doce se leyeron enteras |

La auditoría queda **cerrada sobre las fuentes disponibles**. Las
transcripciones de Claude Code llegaron el 20-09 y tienen su adenda y su paso
4. Cuando llegue la exportación de ChatGPT tendrá su adenda de muestra en la
nota de arranque y una sección propia aquí; las fichas C se revisan entonces
otra vez, no se dan por definitivas.

## Decisiones que esta auditoría pone delante del propietario, sin tomarlas

Las seis del paso 2, que siguen abiertas, dos que añade el paso 3 y dos que
añade el paso 4. Se listan
porque la lección de ADR-198 es que una pregunta que nadie vuelve a poner
delante se pudre.

1. `docs/operations/CLAUDE_SIRIUS_KNOWLEDGE_BASE.md` y
   `docs/operations/CLAUDE_PROJECT_ONBOARDING.md`: archivar o regenerar.
2. Las incidencias de gobernanza #8–#25: mantener, archivar o sustituir.
3. `.github/workflows/materialize-approved-docx.yml`: retirar o arreglar.
4. La prueba intermitente de #137: registrarla o darla por muerta con razón.
5. Qué significa PROPUESTO en un ADR fusionado: 150 de 196 lo dicen.
6. `bloques_del_motor.yml`, bloque D4: la línea es aplicar ADR-198; el estado
   es decisión nueva.
7. **Dónde se escribe una idea aparcada o descartada, con su razón**, para
   que no vuelva como nueva (C-02). Hoy no hay sitio.
8. **Si el método del debate** —las siete reglas de C-03, que hoy viven en la
   memoria de claude.ai y en la de sesión— **se escribe en el repositorio**,
   donde toda IA lo lea, como ya está una de ellas en `AGENTS.md`.
9. **La bitácora de la auditoría forense** —114 entradas y 32 deudas, más la
   medición de la palanca 1 del 20-09 y las piezas de Memanto aparcadas con su
   momento de disparo— vive en la rama de la auditoría forense de ADR-002, sin
   PR y, según la propia sesión, 340 commits por detrás de `main`: fusionar en
   `docs/audits/`, archivar, o dejarla con la razón escrita (E-02, C-02).
10. **Cuántas sesiones a la vez, y cómo se enteran unas de otras.** Hoy la
    única pizarra compartida es `main`, cada sesión la lee desde su rama, y el
    propietario es el único que sabe qué hace cada una (E-02). El motor tiene
    tablero por incidencia (ADR-175) y cola (ADR-191, 200); las sesiones
    interactivas no tienen nada. Limitar el número, asignar una vertical por
    sesión, o darles un sitio donde anotar rama, objetivo y hora: es decisión
    suya.

Y tres acciones, no decisiones, para la pila del ordenador. La retención de
sesiones locales de Claude Code ya está subida a 3 650 días (20-09): antes se
borraban a los treinta y por eso no queda nada local anterior al 16-08. Quedan
dos: desinstalar claude-mem, que sigue cargando 21 skills y 14 herramientas
MCP en cada sesión local aunque ADR-172 eligió Supermemory (E-05). La de las
dos ramas `wip/` del 09-08 **queda resuelta aquí**: se comparó su contenido con
`main` el 20-09 y no guardan nada que no esté ya fusionado. `main` tiene 19
ficheros de Model Studio y ellas 16, y **ninguno existe solo en ellas**; lo
único que traen de más son versiones viejas de documentos y pruebas. Los 143
commits que `git log origin/main..` lista como suyos son la historia previa al
aplastado de la rama, no trabajo perdido: se comprobó fichero a fichero antes
de decirlo, porque el recuento de commits, solo, decía lo contrario. Se pueden
archivar cuando se quiera (ADR-195: archivar, nunca borrar) y no corre prisa.

### Las cuatro vías probadas para traer las 28 que faltan (20-09-2026)

Se intentó completar la muestra y **no se pudo**. Queda escrito con lo que dio
cada intento, para que nadie repita la tarde:

| Vía | Qué pasó |
|---|---|
| `claude --teleport <id>` en bucle, con la salida capturada para registrarla | Las 34 fallan con código 1. La causa está en el registro que el propio guion escribe: al capturar la salida, Claude Code deja de verse en una consola, se pasa a modo `--print` y exige un prompt. **El registro rompía lo que venía a medir.** |
| La misma, a mano y en consola de verdad, sobre una sesión archivada | No escribe nada. 23 de las 34 están `ARCHIVED`, y una sesión archivada no se reanuda |
| La misma, a mano, sobre una sesión `IDLE` (`session_01J2Hucr…`, del 08-09) | Tampoco. El fichero más reciente de `~/.claude/projects` siguió siendo el de las 02:45, del intento original |
| `claude --teleport` **sin identificador**, que abre un selector con las sesiones traíbles, eligiendo una y saliendo con `/exit` | El selector sí las lista —18 entradas—, pero elegir y salir sin escribir nada tampoco escribe la transcripción en local |

Lo que las cuatro juntas enseñan: **la transcripción local se escribe cuando la
sesión tiene un turno, no cuando se abre.** Traer las 28 costaría un turno de
modelo por sesión, y eso es dinero, que decide el propietario (ADR-204). Para
una mejora opcional de una muestra ya cerrada con su límite declarado, no se le
pidió. La idea queda aparcada con su disparador en
`docs/ideas/registro_de_ideas.yml` (I-007).

Dos cosas más que este intento dejó, y que sí valen: el guion
`scripts/traer_sesiones_de_la_nube.ps1`, que registra por sesión y se reanuda
donde se cortó —el intento del 20-09 no registraba nada y por eso no se supo
nunca por qué bajaron 6—; y el dato de que **23 de las 34 sesiones de la nube
están archivadas**, que no se sabía.

## Lo que esta auditoría NO dice

- Qué se dijo en ChatGPT: su exportación no ha llegado. En julio, ChatGPT era
  el que redactaba; esa mitad del debate no se ha visto.
- Qué había en 28 de las 34 sesiones de Claude Code en la nube, que no
  bajaron, ni en las sesiones locales anteriores al 16-08, borradas por la
  retención de treinta días: entre ellas, todo julio y la primera quincena de
  agosto en el ordenador.
- Qué hicieron las herramientas: los resultados de herramienta no se leyeron,
  salvo denegaciones y respuestas a preguntas de la IA; y tres transcripciones
  de la nube empiezan por un resumen escrito por el modelo, usado solo como
  fuente secundaria.
- Cuánto tiempo costó nada: las horas son marcas de reloj, no esfuerzo.
- Qué había en las cinco conversaciones de julio que la exportación trae
  vacías; una de ellas, de 80 mensajes, es de la noche en que nació el
  contrato de automatización.
- Nada sobre la cabeza robótica, por decisión del propietario.
- La memoria y las reflexiones de claude.ai las escribió un modelo: se usaron
  para contrastar, nunca como fuente única de ninguna afirmación.

## Declaración de alcance de decisión

Esta auditoría produce veredictos, fichas y una lista de decisiones
pendientes; no toma ninguna. No se registra ADR. Si el propietario decide
alguna de las diez de arriba —o la que el encargo tenía detrás, qué merece
mecanizarse y qué no—, esa decisión dejará su ADR con la skill `adr`.
