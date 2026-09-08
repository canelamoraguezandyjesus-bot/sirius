# Propuesta de separación entre Sirius y su motor de trabajo

- **Identificador:** `SIRIUS-PROPUESTA-SEPARACION-001`
- **Estado:** **REVISADA**; su dirección está recogida en las enmiendas del 8 de septiembre de 2026 —EV-015 a EV-019, la §19 del Rector, ADR-160 y ADR-161—, cuya entrada en vigor es la fusión de su Pull Request por el propietario (ver el recuadro siguiente)
- **Fecha:** 8 de septiembre de 2026
- **Árbol sobre el que se comprobó todo:** `main` en `f2085db`
  (`f2085dbbcdef9f33e084131984f1dd6c3daf0101`, 2026-09-07T23:48:23+02:00)
- **Autoridad:** ninguna. Este documento **no decide nada**. Propone, y señala qué
  tendría que decidir el propietario.

> **Lo que este documento NO hace, dicho antes que nada.** No modifica código,
> workflows, permisos ni documentos aprobados. No desactiva ningún agente ni migra
> ningún dato. No cambia numeración ni alcance de versiones. No convierte en decisión
> aprobada ninguna posibilidad discutida. No abre otra auditoría sobre las rondas del
> motor. No prepara el plan detallado de implementación. Y no elige herramienta de
> memoria.
>
> **No produce ADR.** La disciplina de evidencia (ADR-001) exige un ADR por cada
> trabajo que produjo una decisión; este no produjo ninguna, porque las decisiones que
> aquí se enumeran son del propietario y siguen abiertas. Se declara explícitamente,
> como esa misma disciplina pide cuando no hay ADR que escribir.

## 0.0 Qué de esta propuesta está ya formalizado (8 de septiembre de 2026)

Este documento **se conserva tal como quedó tras la revisión del propietario**:
es el análisis con sus comprobaciones, y no se reescribe para que parezca que
siempre supo el final. Lo que sigue dice qué partes suyas están ya recogidas en
las enmiendas de esa fecha.

**Entrada en vigor, unificada:** la fusión de la Pull Request que introduce esas
enmiendas, por el propietario, conforme al procedimiento establecido.
**Aprobación documental y retirada técnica son cosas distintas:** esa fusión
aprueba los documentos y **no** desactiva ningún carril.

| De esta propuesta | Dónde está formalizado |
|---|---|
| La dirección del apartado 7.1, sus seis puntos | **EV-015 a EV-019** (`docs/evolution/DECISIONS.md`) y **ADR-160** |
| Las enmiendas del apartado 4.1, filas 1-4 y 6 | `docs/evolution/RECTOR.md` §19 y `docs/evolution/DECISIONS.md`, con la relación unificada: **EV-015 precisa EV-001, EV-016 sustituye EV-002 y acota EV-003, y EV-004 se mantiene vigente sin enmienda** |
| La fila 5 del apartado 4.1 (EV-004 y la memoria común) | **EV-018**: el conocimiento común **no es** la memoria canónica, así que **EV-004 queda vigente sin enmienda**. La decisión T-3 del apartado 7.2 queda resuelta por esta vía |
| Las enmiendas del apartado 4.1, filas 7-13 | **ADR-161**, contrato operativo **§13 (v1.10)**, `docs/implementation/bloques_del_motor.yml`, `docs/operations/MOTOR_DE_SIRIUS.md`, arquitectura mínima del motor §18, superficie de invocación §9 |
| La recomendación de T-1 (desactivación reversible) | **ADR-161**, apartado «Recomendación técnica de ejecución (no ejecutada)». Sigue siendo recomendación de **forma**: nadie ha ordenado ejecutarla, y su paso 0 —inventariar todas las vías de entrada a cada carril, incluidas activaciones manuales y órdenes en curso— **no se ha hecho** |
| Las decisiones T-2 y T-4 a T-10 del apartado 7.2 | **Siguen abiertas.** Ninguna se ha decidido aquí. En particular **T-2** —el tratamiento de la puerta del implementador— queda expresamente pendiente en ADR-161, punto 4, hasta comprobar todas las vías de entrada |
| Las filas 14 y 17 del apartado 4.2 (`README.md`, HEAD-R1) y el «Próximo paso» de la fila 16 | **No tocadas**, por orden expresa del propietario de no ampliar el trabajo a otros defectos documentales |

**La retirada de los dos carriles está ACORDADA y NO EJECUTADA.** Hoy siguen
funcionando si alguien los dispara: la distinción está escrita en ADR-161 y en el
§13 del contrato, y se puede contrastar con `TABLA_ACTIVACION`, que sigue
teniendo las cuatro clases.

Dos afirmaciones de este documento envejecieron con la formalización, y se dicen
aquí en vez de editarlas en su sitio: el apartado 2.1 decía que la memoria común
«no está declarada como tal en ninguna parte» —**ahora lo está, en EV-018**—, y
el apartado 2.2 llamaba «candidatos a desactivarse» a los dos carriles —**la
decisión de retirarlos ya está tomada; lo que queda pendiente es ejecutarla**—.

---

## 0. Nota de arranque y convención de evidencia

### 0.1 Nota de arranque (ADR-001), escrita ANTES de leer el fondo

**1. ¿Dónde vive el fallo y dónde va el arreglo?** No hay un fallo de software. Hay una
**desalineación** entre lo que la documentación aprobada dice que es Sirius y lo que el
propietario acaba de expresar como visión. El «arreglo» es este documento, que **no
modifica** los documentos desalineados: los señala, apartado por apartado. ¿Puede el
sitio del arreglo observar el fallo que arregla? Sí: un documento nuevo puede citar los
apartados que contradicen la visión sin tocarlos. Lo que un documento **no** puede hacer
es comprobar que la desalineación se resuelve; eso lo decide el propietario.

**2. ¿Qué NO garantiza esto?** No garantiza que el reparto propuesto sea el que el
propietario quiere. No garantiza un inventario exhaustivo de dependencias de código:
se revisan las fronteras relevantes, no todo el árbol. No garantiza que las enmiendas
propuestas sean suficientes: son las que aparecen al leer, y se declara qué no se leyó.
No verifica comportamiento en ejecución: no se ejecutó el motor, ni un run, ni la suite.

**3. Criterio de parada, decidido antes de ver resultados.** Se declara como pregunta
abierta al propietario, en vez de resolverse aquí, cuando: (a) dos documentos vigentes
se contradicen sobre el estado de algo y el historial no lo desempata; (b) la visión
choca con una decisión ya APROBADA —no propuesta—; (c) hay que elegir herramienta,
repositorio, versión o arquitectura; (d) un componente parece candidato a retirada pero
también sostiene una función que el propietario quiere conservar; (e) no se encuentra
respaldo documental: se escribe «no lo he encontrado», no se afirma.

**4. ¿Qué haría imposible el error más probable, en vez de improbable?** El error más
probable aquí es el que AGENTS.md y el propio encargo avisan: confundir una cabecera
«PROPUESTO» con el estado real de aprobación. Lo hace imposible la **tabla del apartado
8**, que para cada documento citado registra su cabecera literal, dónde consta su estado
real y el veredicto. Ninguna afirmación de estado de este documento va sin fila en esa
tabla. Lo que **no** se puede hacer imposible: que un ADR aprobado haya sido superado por
otro posterior que no lo cite. Mitigación aplicada: cruzar por tema, no por número, y
declarar el residuo (apartado 5.5, punto 9).

### 0.2 Convención de evidencia

Se hereda la del inventario del motor (`docs/implementation/SIRIUS_WORK_ENGINE_INVENTARIO.md`):

- **[V] Verificado** — leído en el árbol de `f2085db`, con ruta y línea cuando importa.
- **[D] Declarado** — un documento o registro del repositorio lo afirma; no se
  reverificó contra ejecuciones reales desde esta sesión.
- **[NV] No verificado** — no comprobable desde aquí (secretos, variables de
  repositorio, comportamiento de productos externos, ejecuciones vivas).

---

## 1. Resumen en castellano sencillo

Hoy los documentos aprobados dicen que **Sirius es el sitio por donde pasa todo**: el
interlocutor principal, el dueño de la memoria, el que reúne y resume el trabajo
(`docs/evolution/RECTOR.md:22-25`, `docs/evolution/RECTOR.md:58` y
`docs/evolution/RECTOR.md:63`; `docs/evolution/DECISIONS.md` EV-002). El
propietario acaba de decir otra cosa: que su sitio habitual de trabajo son ChatGPT,
Claude y Codex, y que Sirius **no tiene que intermediar** esas conversaciones ni
sintetizar todo el trabajo.

Esa es la única diferencia de fondo. Y es grande, porque toca documentos APROBADOS. Todo
lo demás encaja mejor de lo que parece:

1. **La separación de PAQUETES ya está hecha y hay una máquina que la vigila.** El
   producto vive en `src/sirius/` y el motor en `src/sirius_engine/`; ninguno importa al
   otro, y dos pruebas lo impiden en las dos direcciones
   (`tests/engine/test_boundary.py:44,50`) [V]. Eso es exactamente lo que está
   demostrado, y ni un paso más: **no** se ha demostrado independencia completa. Siguen
   compartiendo distribución, número de versión y puerta de comprobación, y la
   automatización lee el árbol del motor por ruta de fichero (apartado 5.3). Lo que no
   hay que construir es la frontera de código; lo que falta es **decirla en los
   documentos** y decidir qué se hace con las costuras que quedan.

2. **Las dos primeras memorias ya están separadas, y el propietario ya lo decidió.** La
   del producto vive en su equipo; la del motor, en la rama `estado-del-motor` (decisión
   D6 del 29-08-2026, `docs/evolution/STATUS.md`; ADR-083). La tercera —el conocimiento
   compartido de los proyectos— **no está declarada en ninguna parte**: ni «Obsidian», ni
   «Basic Memory», ni «memoria compartida» aparecen en el repositorio [V]. Con la cautela
   que esa comprobación merece: **una búsqueda por nombres no prueba ausencia
   funcional**. Piezas que ya cubren parte de la función sí existen, y hay que mirarlas
   antes de construir: el propio repositorio es accesible con el equipo apagado, está
   versionado, y ya guarda documentos, ADR e investigaciones con origen y caducidad
   declarada; el diario del motor vive en su rama. Lo que **no** está resuelto no es
   «dónde se guarda», sino quién escribe, con qué autoridad, con qué frontera de salida y
   con qué disponibilidad para las IAs (apartado 6).

3. **Retirar el auditor y el investigador dedicados no toca a los revisores del ciclo.**
   Son piezas distintas y se pueden nombrar una por una (apartado 2.3). Los revisores, el corrector, la convergencia y las comprobaciones de
   Quality **no comparten lógica** con el auditor ni con el investigador [V]. Hay un
   único punto de contacto real, y conviene no descubrirlo tarde: el workflow del
   implementador declina las activaciones de perfil `investigador` para que las atienda
   `investigar-orden.yml` (`.github/workflows/implement-sirius-work.yml:171-180`) [V].
   Esa puerta habría que revisarla al retirar el carril, y toca `.github/**`, donde la
   automatización no puede escribir (ADR-002).

4. **Sirius ya tiene voz y cámara construidas.** Model Studio —voz y control de OBS—
   está cableado en el producto (`src/sirius/composition_root.py:573-577`,
   `src/sirius/presentation/model_studio/`) y declarado verificado contra OBS Studio
   32.2.1 en Windows [V el código, D la verificación]. Pero **no aparece en ningún
   documento de estado ni de roadmap**: ni en `RECTOR.md`, ni en `docs/canonical/STATUS.md`,
   ni en `docs/evolution/STATUS.md`, ni en `docs/implementation/PLAN.md`, ni en
   `REPOSITORY_STATUS.md`, ni en `README.md` [V, búsqueda vacía]. La visión nueva se
   apoya justo en esa capacidad, así que el hueco documental deja de ser inocuo.

5. **A Sirius le falta una cosa concreta, y conviene no describirla de más.** «Que me
   ayude con un Arduino sin abrir ChatGPT» pide que **el turno conversacional** pueda
   buscar y usar herramientas, y eso hoy está apagado por diseño: el adaptador del
   proveedor lo dice por escrito, «No tools, web search, file, or code-execution
   capabilities are enabled» (`src/sirius/adapters/llm/openai_responses.py:5-6`) [V]. No
   significa que Sirius no tenga integraciones: **sí las tiene**, y funcionando —OBS por
   WebSocket, audio de entrada y salida, almacén de credenciales del sistema,
   exportación—. La distinción importa porque cambia el trabajo: no hay que inventar la
   forma de integrar nada, hay que dar al turno de conversación un contrato de
   herramientas con permisos, que es la etapa 0.3 del roadmap («Habilidades y
   permisos»), hoy no autorizada.

En una frase: **la frontera de código no hay que construirla, hay que declararla**; lo
que sí hay que construir es la memoria común y las manos de Sirius (herramientas del
turno conversacional y avisos). Y las dos no están en la misma situación: las manos de
Sirius encajan en etapas que el roadmap aprobado ya tiene (0.3 y 0.6), mientras que la
**memoria común no tiene etapa asignada**: ninguna de las siete etapas de
`docs/evolution/RECTOR.md` §9, leídas una a una, describe un conocimiento compartido que
las IAs externas consulten y actualicen [V]. Su relación con Sirius 0.2 se puede estudiar, pero **no está
decidida**, y esta propuesta no la decide.

---

## 2. Responsabilidades y límites

### 2.1 El reparto propuesto

Cuatro actores, no dos. Los dos que el encargo nombra —Sirius y el motor— más los dos
que la visión introduce de hecho: las **aplicaciones externas** (donde el propietario
trabaja) y la **memoria común** (que no está declarada como tal en ninguna parte, aunque
piezas sueltas cubran parte de su función).

| Actor | De qué responde | Lo que explícitamente NO le corresponde | Estado hoy |
|---|---|---|---|
| **Sirius** (producto, `src/sirius/`) | Identidad y relación; memoria propia del producto; conversación; voz; cámaras y captura; percepción bajo demanda; ayuda directa de ingeniería y electrónica; manejo del ordenador y dispositivos autorizados; avisar al propietario de lo que termina, falla o necesita atención; **y, si el propietario lo quiere, delegar en un especialista una consulta de ingeniería suya** —cosa distinta de un encargo del motor (ver la nota bajo la tabla)— | Ejecutar los encargos del motor; revisar su trabajo; ser el paso obligatorio de las conversaciones del propietario con IAs externas; sintetizar todo el trabajo; poseer el estado operativo del motor | Identidad, memoria, conversación: construidas y aceptadas (0.1). Voz y captura: construidas (Model Studio). Herramientas del turno conversacional, avisos propios y delegación especializada: **no construidos**; caen en 0.3, 0.4 y 0.6 del Rector |
| **Motor de trabajo** (`src/sirius_engine/` + `scripts/automation/` + `.github/workflows/`) | Coordinación; ejecución de encargos; documentación por encargo; comprobaciones; revisión; corrección; convergencia; recuperación de trabajos perdidos; diario operativo; escalado al propietario | Poseer la identidad de Sirius; conversar; decidir producto o arquitectura; fusionar; investigar por su cuenta; auditar por su cuenta (si el propietario retira esos dos carriles) | Construido y en circuito: ciclo por etiquetas, revisión dual, corrección, convergencia, supervisión, diario en rama propia. Pendiente: D1 (conmutación) y D4 (partir objetivos) |
| **Aplicaciones externas** (ChatGPT, Claude, Codex) | Conversación de trabajo del propietario; investigación; auditoría y segunda opinión; redacción de encargos; **ejecutar, cuando el propietario las autoriza, lo que él ha decidido** —incluida la escritura de documentos y enmiendas— | Decidir en su propio nombre; aprobar sus propios cambios; convertir una exploración en decisión aprobada; tomar la autoridad del estado del motor | En uso hoy. Codex ya participa **dentro** del ciclo como segundo revisor (contrato §4.1); eso es otra cosa y no se toca |
| **Memoria común de proyectos** | Documentos, investigaciones, decisiones, aprendizajes y continuidad entre proyectos; consultable y actualizable por las IAs y por el motor; disponible con el ordenador del propietario apagado | Sustituir a la memoria del producto; sustituir al diario del motor; ser autoridad sobre el estado de un trabajo en curso | **No existe.** Ver apartado 6 |

**Dos aclaraciones que la tabla, sola, no da:**

- **Delegación especializada de Sirius: se conserva como posibilidad.** Que el
  propietario trabaje desde aplicaciones externas no cierra la puerta a que Sirius, para
  una consulta de ingeniería suya, abra una sesión especializada acotada y le traiga el
  resultado. Es distinto de un encargo del motor en las tres cosas que importan: nace de
  una conversación y no de un WorkItem, no produce PR ni pasa por el ciclo de
  revisión-corrección, y su resultado vuelve a la conversación, no al diario operativo.
  Esta propuesta **no la descarta ni la pide**: la deja explícitamente viva para que la
  redefinición de 0.4 (apartado 3.1) no la borre por omisión.
- **Autoridad y ejecución no son lo mismo.** Donde este documento dice «lo decide el
  propietario» se refiere a la **autoridad**, no a quién teclea. Una IA autorizada por él
  puede perfectamente redactar la enmienda, abrir la PR o preparar el ADR; lo que no
  puede es decidir en su lugar ni darse la autorización a sí misma. El repositorio ya
  funciona así en su punto más sensible: la fusión exige el gesto del propietario
  (contrato §8), y todo lo demás lo ejecutan agentes.

**La regla que ordena las tres memorias, sin obligar a tres bases de datos:** cada dato
tiene **un** dueño, y quien no es dueño lo cita en vez de copiarlo. El repositorio ya usa
ese patrón y le puso nombre: el motor mantiene un «espejo **explícitamente no
autoritativo**» de lo que no le pertenece (contrato §11.1, línea 637) [V].

### 2.2 Qué se conserva, qué se redefine, qué es candidato a desactivarse

«Candidato» significa exactamente eso: el propietario decide, y este documento no
desactiva nada.

| Pieza | Veredicto propuesto | Por qué |
|---|---|---|
| Ciclo por etiquetas, `sirius_issue.sh`, veredicto JSON + aplicador determinista, head SHA de punta a punta, frontera de confianza | **Conservar tal cual** | Es la vía probada del repositorio y nada de la visión nueva la toca |
| Revisor Claude, revisor Codex, agregador, convergencia, corrector, Quality | **Conservar tal cual** | El encargo lo dice expresamente, y su única costura con esos dos carriles está localizada y nombrada (2.3) |
| Merge humano por `fusiona` (contrato §8) | **Conservar tal cual** | La visión nueva no lo menciona y ninguna de sus piezas lo necesita |
| Diario del motor en `estado-del-motor` (ADR-082/083, D6) | **Conservar tal cual** | Ya es la separación de memorias que la visión pide, y ya está decidida |
| Supervisión, recuperación, reconciliador, contador de racha, reflejo del desenlace | **Conservar tal cual** | Son la parte «recuperación y diario operativo» que el encargo conserva |
| Memoria y conversación del producto (`src/sirius/`) | **Conservar tal cual** | Es la identidad de Sirius; la visión la refuerza, no la recorta |
| Model Studio (voz + captura OBS) | **Conservar, y reconciliar su documentación** | Construido y sin reflejo en ningún documento de estado (apartado 4.2, fila 15) |
| Rol de Sirius como interlocutor obligatorio (RECTOR §4, EV-002) | **Redefinir** | La dirección ya está dada (7.1, dirección 1); lo que falta es el acto formal de enmienda, que es trabajo y puede ejecutarlo una IA autorizada |
| Rol de Sirius como sintetizador de todo el trabajo (RECTOR §4.6) | **Redefinir** | Ídem: pasa a ser opcional, a petición |
| «Superficie 3 — Desde Sirius» para lanzar agentes (`docs/implementation/AGENTES_SUPERFICIE_DE_INVOCACION.md:73`) | **Redefinir** | Se describía como «el final del camino»; con la visión nueva el final del camino es que Sirius **avise** y **ayude**, no que lance auditorías |
| 0.4 «Delegación supervisada» (RECTOR §9.3) | **Redefinir, conservando su núcleo útil** | La delegación de *encargos de trabajo* ya la hace el motor. Lo que **no** hace el motor, y por eso se conserva expresamente como posibilidad, es que Sirius delegue una **consulta de ingeniería del propietario** en un especialista y le devuelva el resultado a la conversación (nota de 2.1) |
| **Auditor dedicado** (carril `auditoria:solicitada`) | **Se retira** (dirección dada, 7.1 punto 2) | El propietario mueve esos encargos a sus sesiones externas. Lo que sigue abierto es **el modo** de retirada, no el hecho: T-1, con recomendación de desactivación reversible |
| **Investigador dedicado** (carril `investigacion`) | **Se retira** (dirección dada, 7.1 punto 2) | Ídem, con su punto de contacto propio en la puerta del implementador (T-2) |
| D3 «Hablar con Sirius por Telegram» (`docs/implementation/bloques_del_motor.yml:273`, hoy `fuera_de_alcance`) | **Revisar la clasificación** | La necesidad que lo motivaba —que un aviso llegue al propietario— vuelve, pero ahora el candidato natural a darlo es Sirius, no Telegram |
| D4 «Partir un objetivo grande» (`docs/implementation/bloques_del_motor.yml:281`, pendiente; ADR-089 lo aplaza) | **Revisar la prioridad** | Si el propietario parte los objetivos en sus sesiones externas, este bloque pierde urgencia; no se descarta |

### 2.3 Lo que NO es candidato a nada: revisores y comprobaciones

El encargo pide identificar exactamente qué componente hace cada función **antes** de
proponer retiradas. Aquí están, comprobados uno a uno en el árbol [V].

**Función «revisión y comprobación de las entregas» — se conserva entera:**

| Pieza | Fichero |
|---|---|
| Revisor del ciclo (Claude) | `.github/workflows/review-sirius-work.yml` |
| Segundo revisor (Codex por GitHub) | `scripts/automation/sirius_codex_review.py` |
| Agregación determinista de las dos revisiones | `scripts/automation/sirius_aggregate_reviews.py` |
| Política de convergencia (termina el bucle revisar-reparar) | `scripts/automation/sirius_convergence.py` |
| Corrector | `.github/workflows/repair-sirius-work.yml` |
| Comprobaciones de la entrega | `.github/workflows/quality.yml`, `scripts/check.ps1` |
| Perfiles y prompts de esos roles | `docs/implementation/work_engine/perfiles/{reviewer,revisor-documental,corrector}.yml`; `scripts/automation/prompts/{reviewer-v2,revisor-documental-v2,corrector}.md` |
| Guardas de calidad del propio ciclo | detector de familia repetida (ADR-121), guardián de goteo (ADR-123), guardián del suelo de prueba muerto (ADR-134) |

**Función «auditoría dedicada» — candidata a retirarse:**

| Pieza | Fichero |
|---|---|
| Workflow del auditor (dos jobs partidos por ADR-016) | `.github/workflows/audit-sirius-repository.yml` |
| Runbook (que *es* el agente, ADR-010) | `docs/implementation/AUDITOR_AGENT_V0.md` |
| Perfil versionado | `docs/implementation/work_engine/perfiles/auditor.yml` |
| Clase, tabla de activación y de perfiles | `src/sirius_engine/domain/work_item.py:80`; `src/sirius_engine/dispatcher.py:110-113`; `src/sirius_engine/dispatch_cli.py:69` |
| Etiqueta propia (fuera del espacio `sirius:*`) | `auditoria:solicitada`, `.github/workflows/bootstrap-sirius-automation-labels.yml` |
| Filas en el contrato operativo | §11.1 línea 632; §12.4, tabla cerrada |
| Bloque del motor | C4, `docs/implementation/bloques_del_motor.yml:202` (cerrado) |
| ADR de origen | ADR-010, ADR-016 |
| Pruebas que lo sostienen | `tests/automation/test_auditor_workflow.py`, y las filas de auditoría de `tests/engine/test_{authority,dispatcher,dispatch_cli,intent_interpreter,seven_day_streak}.py` |

**Función «investigación dedicada» — candidata a retirarse:**

| Pieza | Fichero |
|---|---|
| Ejecutor de la orden de investigación | `.github/workflows/investigar-orden.yml` |
| Atestado previo y medición del instrumento | `.github/workflows/preflight-investigador.yml`, `.github/workflows/medir-investigador.yml` |
| Código del investigador | `scripts/investigacion/` (8 ficheros: `atender_orden.py`, `investigar_orden.py`, `medir_investigador.py`, `preflight.py`, `comparar_investigadores.py`, `configuraciones.yml`, `modelos_atestiguados.yml`, `preguntas.yml`) |
| Clase y perfil | `src/sirius_engine/domain/work_item.py:77`; `src/sirius_engine/dispatcher.py:124-127`; `src/sirius_engine/dispatch_cli.py:74` |
| Filas del manifiesto de prompts (carril `revision`) | `investigador@1` y `investigador@2` en `scripts/automation/prompts/manifiesto.json` |
| Fila en el contrato operativo | §11.1 línea 628 («motor, desde su nacimiento») |
| Bloques del motor | S2 y B1, `docs/implementation/bloques_del_motor.yml:69,118` (ambos cerrados) |
| ADR de origen | ADR-095, ADR-097, ADR-098, ADR-099 |
| Puerta del implementador que le cede la activación | `.github/workflows/implement-sirius-work.yml:171-180` (**único punto de contacto con un workflow del ciclo**; `.github/workflows/review-sirius-work.yml:284` solo lo menciona en un comentario) |
| Pruebas que lo sostienen | `tests/automation/test_{atender_orden_de_investigacion,investigar_orden_workflow,medicion_del_investigador,preflight_y_atestado}.py` |

Tres precisiones que evitan retiradas de más:

- **`docs/investigaciones/` no es el investigador.** Es el resultado: informes fechados
  con su caducidad declarada, que son conocimiento y se conservan. La guarda
  `tests/automation/test_investigaciones_declaran_caducidad.py` protege el formato de esa
  carpeta, no al agente.
- **`docs/audits/` no es el auditor.** De sus 70 ficheros, la mayoría son notas de
  arranque (`arranque-*.md`) y de evidencia (`evidencia-*.md`) de la disciplina de
  ADR-001, más `registro_defectos.yml`, que es el registro de defectos del repositorio
  (ADR-047/075/080). Nada de eso depende del carril de auditoría [V].
- **El perfil `investigador` no tiene fichero YAML de perfil.** `TABLA_PERFILES` lo
  declara como `investigador@2`, pero en `docs/implementation/work_engine/perfiles/` no
  existe `investigador.yml` [V]: su ejecutor no es un agente de modelo, sino el
  investigador medido de ADR-098. Es un detalle que importa al retirar, porque significa
  que hay una referencia menos que limpiar y una asimetría que alguien podría leer como
  defecto sin serlo.

---

## 3. Impacto sobre cada etapa del roadmap existente

Hay **dos** roadmaps y se confunden con facilidad —AGENTS.md avisa de que hasta comparten
identificadores—. Se tratan por separado, y se añade el trabajo de 0.2 que está en vuelo
ahora mismo.

### 3.1 Roadmap del PRODUCTO (`docs/evolution/RECTOR.md` §9, APROBADO)

| Etapa | Estado hoy | Impacto de la visión nueva | Propuesta |
|---|---|---|---|
| **0.2 Memoria útil** (`docs/evolution/RECTOR.md:140-146`) | **Autorizada y en construcción** (excepción del 28-08-2026, incidencia #412) | **Ninguno sobre su alcance.** Sí sobre su lectura: su puerta de salida es «puede construir un paquete de contexto fiable y trazable **para una tarea externa**» (`docs/evolution/RECTOR.md:146`). Con la visión nueva, «tarea externa» deja de ser un ejemplo y pasa a ser el caso de uso central: la tarea externa es una sesión de ChatGPT, Claude o Codex | **No tocar el alcance ni la puerta.** La relación entre esa puerta y la memoria común es una **hipótesis que se puede estudiar**, no una dependencia: esta propuesta **no** hace de 0.2 un requisito previo de la memoria común, ni al revés (apartado 6.1) |
| **0.3 Habilidades y permisos** (`docs/evolution/RECTOR.md:148-154`) | No autorizada | **Sube.** «Buscar información o recurrir a herramientas para ayudarme con ingeniería» y «abrir ChatGPT o Claude y activar su micrófono» son literalmente contrato de habilidades + permisos acotados + acción reversible + registro. Lo apagado es el **turno conversacional**: el adaptador declara que no hay tools ni web (`src/sirius/adapters/llm/openai_responses.py:5-6`) [V]. Integraciones sí hay (OBS, audio, credenciales, exportación), así que lo que falta es el contrato de herramientas y permisos, no la capacidad de integrar | **Candidata a ser la siguiente etapa** tras 0.2, si el propietario lo ordena (apartado 7.2, T-7) |
| **0.4 Delegación supervisada** (`docs/evolution/RECTOR.md:156-162`) | No autorizada | **Se redefine, conservando su núcleo útil.** La delegación de *encargos de trabajo* ya la hace el motor, con perfiles versionados, presupuesto, convergencia y evidencia. Lo que el motor **no** hace, y sigue siendo de Sirius, es delegar una **consulta de ingeniería del propietario** en un especialista y devolver el resultado a la conversación | **Conservar explícitamente esa delegación especializada** al redefinir la etapa, para que no se borre por omisión al decir «esto ya lo hace el motor» (nota de 2.1; decisión T-8). No se construye ahora |
| **0.5 Voz** (`docs/evolution/RECTOR.md:164-170`) | No autorizada… **pero construida** | **Contradicción documental que la visión hace urgente.** Model Studio tiene entrada y salida de voz cableadas en el producto [V]. La visión conserva la voz explícitamente | Reconciliar: declarar qué parte de 0.5 quedó cubierta por Model Studio y qué falta (interrupción, misma conversación, escucha explícita). **No renumerar nada** |
| **0.6 Percepción y automatización digital** (`docs/evolution/RECTOR.md:172-178`) | No autorizada… **parcialmente construida** | **Sube, y también tiene contradicción documental.** El control de OBS (escenas, grabación) es control limitado de una aplicación, y está construido y verificado [V el código / D la verificación]. «Manejo del ordenador y dispositivos» y «avisarme de que un trabajo terminó» caen aquí y en 0.3 | Reconciliar igual que 0.5, y decidir si el **aviso al propietario** entra por aquí o por 0.3 |
| **0.7 Puente de laboratorio y dispositivos** (`docs/evolution/RECTOR.md:180-186`) | No autorizada | **Ninguno de fondo.** Ojo con una confusión fácil: «ayudar con electrónica y montaje» —conversar, calcular, leer una hoja de datos— es 0.3, no 0.7. 0.7 es el puente a dispositivos reales con controlador determinista | Sin cambios. Conviene dejar escrita la distinción para que no se planifique 0.7 por una necesidad que es de 0.3 |
| **1.0 Compañero en la habitación** (`docs/evolution/RECTOR.md:188-192`) | No autorizada | **Se matiza.** Su definición incluye «apoyo de extremo a extremo en un proyecto real». Si el propietario trabaja desde aplicaciones externas, «extremo a extremo» ya no significa «todo pasa por Sirius» | Registrar el matiz cuando se enmiende el Rector; no antes |

**Lo que no cambia en ninguna etapa:** la regla de activación (`docs/evolution/RECTOR.md:282-290`) sigue
exigiendo Definición de Producto aprobada, pruebas de aceptación reproducibles y
arquitectura técnica aprobada antes de empezar una etapa. Esta propuesta no abre ninguna.

### 3.2 El trabajo de 0.2 que está en vuelo (impacto: ninguno)

La ola de paridad en producción sigue su curso y **la separación no la toca**. Se dice
porque el propietario debe poder decidir sin miedo a parar algo:

- `docs/evolution/STATUS.md` fija los encargos M13-M17 (actualización del 31-08-2026).
- El trabajo continuó más allá: ADR-124 (M16, APROBADO), ADR-125 (APROBADO), y la
  subola de criticidad ADR-126 a ADR-131 (M18b a M21b, fechados 02 y 03-09-2026),
  registrada en `docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md:398-435` [V].
- **M17 no está cerrado**: ningún ADR lo declara cumplido, y la ola solo se cierra cuando
  las pruebas `xfail(strict=True)` pasen inesperadamente [V].
- Consecuencia documental, no de alcance: `docs/evolution/STATUS.md` lleva sin
  actualizarse desde el 31-08-2026 (`git log`) [V] y su «Próximo paso» ya no describe
  dónde está la ola. Entra en el apartado 4 como enmienda pendiente.

### 3.3 Roadmap del MOTOR (`docs/implementation/bloques_del_motor.yml`)

| Bloque | Estado hoy | Impacto | Propuesta |
|---|---|---|---|
| E0, A1-A5, S1, S3, E1a, E1b, C1, C2, C3, D2 | cerrados | Ninguno | Sin cambios |
| **S2** (medir el investigador externo) y **B1** (investigar desde una orden) | cerrados con evidencia | Si se retira el investigador, **sus bloques siguen cerrados**: un bloque cerrado registra lo que se midió, no lo que se usa. Lo que cambia es que su conclusión pasa a ser histórica | Añadir una línea de estado a cada uno cuando el propietario decida, sin borrar la evidencia |
| **C4** (la auditoría dentro del motor) | cerrado | Igual que S2/B1 | Igual |
| **D1** (pasar el mando de GitHub al motor, clase por clase) | **pendiente**; sus tres mitades tienen llamante desde el 27-08-2026, y los siete días no han empezado | **Se simplifica.** El orden de conmutación del contrato §11.3 es documental → programación → auditoría. Si la auditoría se retira, D1 pasa de tres clases a dos | Registrar el cambio de orden cuando la retirada se decida. **No conmutar nada** |
| **D3** (Telegram) | `fuera_de_alcance` | **Vuelve la necesidad, no la herramienta.** La dirección 6 del apartado 7.1 ya fija que **avisa Sirius**; hoy el canal es GitHub Mobile (contrato §7, seis estados notificables) y Sirius no lo lee | Mantener `fuera_de_alcance` para Telegram y tratar «Sirius avisa» como capacidad del producto (0.3/0.6), **no** como bloque del motor. Lo que queda abierto es el camino técnico, no el quién (T-9) |
| **D4** (partir un objetivo grande) | **pendiente**; ADR-089 aplaza el descomponedor automático y lo deja en la sesión interactiva | **Pierde urgencia.** Si el propietario parte los objetivos en ChatGPT/Claude/Codex, el descomponedor automático resuelve un problema que deja de tener | Revisar la prioridad. No descartarlo: sigue siendo el único camino para un objetivo del tamaño de una versión |

---

## 4. Documentos y decisiones que habría que enmendar

Se listan con el apartado exacto, qué dice hoy, qué cambiaría y por qué. **Ninguna de
estas enmiendas se ha hecho.** Varias tocan documentos APROBADOS, y ahí la regla es de
**autoridad**, no de teclado: cambiarlos exige una decisión del propietario (`RECTOR.md`
§16 fija la jerarquía; AGENTS.md prohíbe cambiar documentos canónicos sin decisión
explícita), pero una vez tomada, redactarla y abrir la PR puede hacerlo una IA autorizada
por él. Para la mayoría de estas filas la decisión **ya está tomada** (apartado 7.1); lo
que falta es escribirla.

### 4.1 Las que la visión nueva obliga a tocar

| # | Documento y apartado exacto | Qué dice hoy | Qué cambiaría | Por qué |
|---|---|---|---|---|
| 1 | `docs/evolution/RECTOR.md` §2, líneas 22 y 25 | Sirius es «la interfaz principal con el ecosistema digital y físico» y «el integrador de resultados producidos por modelos, agentes y herramientas» | Sirius es **una** interfaz —la personal y de ingeniería—, no el paso obligatorio; integra resultados **cuando se le pide** | La visión sitúa el trabajo habitual del propietario en aplicaciones externas |
| 2 | `docs/evolution/RECTOR.md` §4, líneas 58 y 63 | «1. El usuario habla normalmente con Sirius» … «6. Al cerrar, Sirius sintetiza el resultado y propone qué debe conservarse» | El modelo híbrido deja de ser el único; se admite que el propietario hable directamente con las IAs externas y que la síntesis sea opcional | Es el choque más directo con la visión, y está en un documento APROBADO |
| 3 | `docs/evolution/DECISIONS.md` EV-002, línea 13 | «El usuario se relacionará principalmente con Sirius» | Enmienda o sustitución por una decisión nueva de la serie EV | Una decisión aprobada no se reinterpreta: se sustituye con otra decisión |
| 4 | `docs/evolution/DECISIONS.md` EV-003 | Sirius abre sesiones especializadas, prepara el contexto y «recupera e integra el resultado» | Se conserva como capacidad **posible**, no como el camino por el que llega el trabajo | Ídem |
| 5 | `docs/evolution/DECISIONS.md` EV-004 + `docs/evolution/RECTOR.md:69` (§5) | «Memoria canónica **exclusiva** de Sirius»; «Sirius mantiene una **única** memoria canónica»; los agentes «no poseerán ni modificarán directamente la memoria canónica» | Hace falta decir si la memoria común es (a) parte de la memoria canónica de Sirius, (b) una tercera cosa fuera de EV-004, o (c) el motivo para enmendar EV-004 | La visión pide que **las IAs externas la consulten y la actualicen**. Tal como está redactado EV-004, eso está prohibido. **No se elige aquí**: es la decisión T-3 del apartado 7.2, y puede resolverse sin enmendar EV-004 si la memoria común se declara distinta de la memoria canónica |
| 6 | `docs/evolution/STATUS.md`, apartado «Vigente», líneas 23-24 | «Sirius conserva … síntesis final»; «El modelo de interacción principal es híbrido: Sirius es el interlocutor principal» | Refleja lo que el Rector diga tras su enmienda | Es el espejo del Rector; si el Rector cambia y este no, se repite el error que el propio documento se reprocha (quince días diciendo que 0.1 no estaba aceptado) |
| 7 | `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` §11.1, filas de las líneas 628 y 632 | `investigación` → «motor, desde su nacimiento»; `auditoría` → «sí (etiqueta propia) / incidencia / sí» | Retirar ambas filas, o marcarlas como clases sin ejecutor | La tabla es **cerrada a propósito** y su propia regla lo dice: «Una clase que no aparezca aquí no puede crear WorkItems». Quitar una fila es **enmienda del contrato**, igual que ADR-088 y ADR-099 lo fueron al añadirlas |
| 8 | `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` §12.4, tabla cerrada | Fila `auditoria` → `auditoria:solicitada` | Retirar esa fila si se retira el carril | Ídem: es la única etiqueta fuera del espacio `sirius:*` que el motor puede aplicar |
| 9 | `docs/implementation/SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md` §7.3, línea 476 | Título literal: «GPT Researcher (Worker de investigación, **OBLIGATORIO en el MVP**)» | Deja de ser obligatorio; el apartado pasa a describir una vía no adoptada | Si el propietario retira la investigación dedicada, esa palabra es falsa y bloquearía cualquier lectura futura del diseño |
| 10 | `docs/implementation/AGENTES_SUPERFICIE_DE_INVOCACION.md` §2, «Superficie 3 — Desde Sirius», línea 73 | «el final del camino, no ahora»: un control dentro de Sirius que cree la incidencia y aplique la etiqueta para lanzar auditorías | Si el auditor se retira, esa superficie 3 se queda sin objeto; lo que la visión pide de Sirius es **ayudar y avisar**, no lanzar auditorías | El documento se presenta como preparación; queda desalineado sin enmendarlo |
| 11 | `docs/implementation/AGENTES_SUPERFICIE_DE_INVOCACION.md` §6, pasos 3-5 | «La prueba de la tarde … **Es el siguiente paso**»; luego triaje de paradas; luego multimodelo | Ya no describe el siguiente paso de nada: el multimodelo se resolvió por otra vía (ADR-095 el atestado, ADR-098 la configuración medida) | Es una lista de orden recomendado que quedó atrás; con la visión nueva, además, cambia de destinatario |
| 12 | `docs/implementation/bloques_del_motor.yml`, bloques S2 (línea 69), B1 (118), C4 (186) | `estado: cerrado` con su evidencia | Añadir el hecho, sin borrar la evidencia: «carril retirado por decisión del propietario el <fecha>» | Un bloque cerrado no se reabre por dejar de usarse, pero un lector futuro tiene que poder saber que su carril ya no corre |
| 13 | `docs/implementation/bloques_del_motor.yml`, bloque D1 (línea 191) | «siete días consecutivos en verde **por clase**», con el orden documental → programación → auditoría | Dos clases en vez de tres | Es consecuencia mecánica de la fila 8 |

### 4.2 Las que ya estaban desalineadas, y la visión hace visibles

Estas no las causa la visión nueva. Se registran porque el encargo pide identificar qué
afirmaciones documentales necesitan enmienda, y porque la visión se apoya justo en ellas.

| # | Documento y apartado exacto | Qué dice hoy | Qué falla | Comprobación |
|---|---|---|---|---|
| 14 | `README.md`, línea 16 | «Sirius 0.1 todavía no está aceptado ni terminado» | **Falso.** `docs/canonical/STATUS.md` («ACEPTADO y TERMINADO por declaración del propietario el 10-08-2026») y `REPOSITORY_STATUS.md` («La aceptación formal con proveedor real está **completada**») dicen lo contrario | `grep -n "aceptado" README.md` [V] |
| 15 | Model Studio: ausente de todo documento de estado | Voz y captura de OBS están construidas y cableadas (`src/sirius/composition_root.py:573-577`; `src/sirius/presentation/model_studio/`) y declaradas verificadas contra OBS Studio 32.2.1 | **No aparecen** en `RECTOR.md`, `docs/canonical/STATUS.md`, `docs/evolution/STATUS.md`, `docs/implementation/PLAN.md`, `REPOSITORY_STATUS.md` ni `README.md` | `grep -rin "studio"` sobre esos seis ficheros: **cero resultados** [V] |
| 16 | `docs/evolution/STATUS.md`, «Próximo paso (actualización del 31 de agosto de 2026)» | Ordenar M13-M17 en su orden de dependencias | El trabajo siguió hasta M18b-M21b (ADR-126 a ADR-131, 02 y 03-09-2026) y el documento no lo recoge; lleva sin tocarse desde el 31-08 | `git log -1 -- docs/evolution/STATUS.md` [V] |
| 17 | `docs/robotics/head/STATUS.md`, «Prioridad actual» | «Cerrar Sirius 0.1 …: implementación terminada; pendiente empaquetado, pruebas manuales en Windows 11, configuración de clave real, prueba con proveedor real … y aceptación formal» | Describe como pendiente lo que se cerró el 10-08-2026 | Contraste con `docs/canonical/STATUS.md` [V] |
| 18 | `docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` §7.3 | Lista cuatro «decisiones abiertas del propietario» | Las cuatro están resueltas (D1-D4 del 29-08-2026, registradas en `docs/evolution/STATUS.md`). El documento es una foto fechada y no se reescribe, pero conviene que nadie lo cite como estado vivo | Lectura cruzada de ambos [V] |

### 4.3 Lo que NO hay que enmendar, y por qué se dice

- **`docs/implementation/SIRIUS_WORK_ENGINE_INVENTARIO.md` §1.7** dice «Ninguna
  capacidad de investigación: GPT Researcher no está en el repositorio» (línea 140). Hoy
  eso ya no es cierto —B1 lo cerró—, pero el documento **declara su fecha y su commit
  base** (`e13a1e3`, 2026-08-15). Es una foto correcta de un instante, no un error. No se
  enmienda: se cita con su fecha.
- **ADR-010, ADR-016, ADR-095, ADR-097, ADR-098, ADR-099** no se enmiendan aunque se
  retiren los carriles que autorizan. Un ADR registra por qué se decidió algo entonces;
  retirar lo decidido produce un ADR **nuevo** que lo supera, no una edición del viejo.
  Es el patrón que ya usan ADR-082 (que enmienda a ADR-019) y ADR-120 (que sustituye el
  candado de M10).
- **El contrato §4.1 (revisión dual con Codex)** no se toca. Codex participando como
  segundo revisor **dentro** del ciclo es otra cosa que «el propietario audita desde su
  sesión de Codex»; confundirlas retiraría un revisor que el encargo conserva.

---

## 5. Dependencias comprobadas y cuestiones todavía no verificadas

El encargo pide distinguir cuatro cosas que se confunden. Se responden en ese orden.

### 5.1 Separación de responsabilidades — **parcial, y lo que falta es documental**

El código y el contrato ya reparten: el motor posee el estado del trabajo (ADR-019), su
memoria vive aparte (ADR-082/083, D6), el producto posee identidad, conversación y
memoria propia. Lo que **no** está repartido es el discurso: `RECTOR.md` §2/§3 y `EV-002`
siguen diciendo que Sirius es el centro de todo. Esa es la brecha real, y es la del
apartado 4.

### 5.2 Separación de paquetes — **hecha, y con guarda mecánica** [V]

| Comprobación | Resultado |
|---|---|
| `src/` contiene dos paquetes | `sirius` y `sirius_engine` |
| ¿`sirius_engine` importa `sirius`? | **No.** Búsqueda de imports: cero resultados |
| ¿`sirius` importa `sirius_engine`? | **No.** Cero resultados |
| ¿Hay algo que lo impida, o es casualidad? | Dos pruebas lo prohíben en ambos sentidos: `tests/engine/test_boundary.py:44` y `:50`, con la frontera declarada por ADR-020 e incidencia #177 §10 |
| Dependencias de terceros del motor | Solo biblioteca estándar + `platformdirs` (`src/sirius_engine/cli.py:41`) + `yaml` (4 módulos). **No** necesita PySide6, SQLAlchemy, alembic, pydantic, keyring, openai, cryptography ni argon2 |
| Dependencias de terceros del producto | Las once de `pyproject.toml:11-23` |

Conclusión, dicha con su alcance exacto: **hay separación de paquetes, comprobada de
forma estática y vigilada por prueba**. Eso significa que ningún módulo de uno importa a
otro y que sus dependencias de terceros son disjuntas — no significa independencia
completa demostrada. Lo que sigue compartido está en 5.3, y no se ha ejecutado nada para
comprobar que cada lado arranca y funciona sin el otro.

### 5.3 Independencia de ejecución — **parcial**, con cuatro costuras reales [V]

Ya son independientes en lo importante: el motor corre **dentro de GitHub Actions**
(ADR-082) y el producto en el equipo Windows del propietario; su memoria vive en la rama
huérfana `estado-del-motor`, cuya referencia existe en el remoto [V: `git ls-remote`].
Las costuras que quedan son de **empaquetado y validación**, no de código:

| Costura | Dónde se ve | Qué implica |
|---|---|---|
| **Una sola distribución** | `pyproject.toml`: nombre `sirius-personal-engineer`, `module-name = ["sirius", "sirius_engine"]` (línea 65) | Los cinco comandos del motor (`sirius-despachar`, `sirius-motor`, `sirius-racha`, `sirius-supervisar`, `sirius-reflejar`) se publican dentro del paquete del producto, y viajan al instalarlo |
| **Un solo número de versión** | `pyproject.toml:3` (`version = "0.1.0.dev0"`) | El motor no puede versionarse aparte hoy |
| **Una sola puerta de comprobación** | `scripts/check.ps1` (`mypy src tests` + `pytest` sin filtro) y `.github/workflows/quality.yml` | Un cambio del motor ejecuta las pruebas de GUI del producto (PySide6 en modo offscreen) y al revés. Es una dependencia de **tiempo y de fragilidad**, no de código |
| **La automatización lee el árbol del motor por ruta de fichero** | `scripts/automation/resolver_prompt.py:32`; `scripts/automation/sirius_convergence.py:72` y `:122`; `scripts/automation/sirius_drip_guard_cli.py:38` | Deliberado y documentado: el runner no tiene el proyecto instalado, así que no puede hacer `import sirius_engine`. Ata los scripts a la **ubicación** `src/sirius_engine/`, no al paquete |

Una sola costura cruza la frontera hacia el producto, y es de pruebas, no de código:
`tests/automation/test_tablas_indexadas_por_enum.py:302` importa
`sirius.ports.llm.LLMErrorKind`. Es una guarda de todo el repositorio —no del motor—, así
que la costura es correcta mientras el repositorio sea uno solo [V].

### 5.4 Separación de repositorios — **no hecha, y hoy no hace falta**

El encargo ya fija que se conserva el repositorio actual. Se evalúa qué aportaría más
tarde, sin ejecutarlo ni darlo por necesario:

**Lo que ganaría una extracción:** una puerta de comprobación más pequeña y rápida para
cada lado; versionado independiente del motor; y un paquete del producto que no publique
comandos de motor.

**Lo que costaría, comprobado:**

- Habría que mover, además de `src/sirius_engine/`: `scripts/automation/`,
  `scripts/investigacion/`, nueve workflows que invocan al motor, `tests/engine/`,
  `tests/automation/` y `docs/implementation/work_engine/` (los perfiles, que
  `src/sirius_engine/profile_registry.py:19-21` resuelve por **ruta relativa al árbol**).
- El motor **lee este repositorio como su contexto**: `contexto.recuperar` v0 tiene tres
  proveedores y dos son locales al árbol —búsqueda de ficheros y `git log`—
  (`src/sirius_engine/context_recall.py`) [V]. Un motor extraído tendría que apuntar al
  repositorio de trabajo desde fuera.
- La guarda de citas de los ADR (`tests/automation/test_citas_de_los_adr.py`) comprueba
  que lo que un ADR cita existe en el árbol. Repartir el árbol reparte esas citas.
- El objeto del motor **hoy** es trabajar sobre este repositorio. Extraerlo antes de que
  trabaje sobre más de uno es pagar el coste sin cobrar la ventaja.

**Propuesta:** no extraer. Si algún día se hace, la señal que lo justificaría es concreta
—que el motor reciba encargos sobre un segundo repositorio—, no la incomodidad de
compartir la suite.

### 5.5 Lo que NO se ha verificado

Se declara para que nadie lo lea como comprobado:

1. **Variables y secretos del repositorio**: `SIRIUS_CODEX_REVIEW_ENABLED`,
   `SIRIUS_BOT_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`, `SIRIUS_TRIGGER_TOKEN`, los plazos de
   Codex y `SIRIUS_STUCK_MINUTES`. No son legibles desde esta sesión (misma lista que
   `SIRIUS_WORK_ENGINE_INVENTARIO.md` §3). En particular, **no se afirma que la revisión
   dual esté activa hoy**.
2. **Ninguna ejecución**: no se ha lanzado el motor, ni un run, ni la suite. Esta
   propuesta es documental y el encargo no pide ejecutar la suite completa.
3. **El contenido de la rama `estado-del-motor`**: se comprobó que la referencia existe
   en el remoto; **no** se leyó su diario.
4. **Model Studio en funcionamiento**: su cableado está verificado en el árbol; que la
   voz y la captura funcionen hoy en el equipo del propietario es **declarado** por
   `docs/implementation/model_studio/`, no reverificado aquí.
5. **El estado vivo de incidencias y PR** citadas por otros documentos (#412, #478, #435…):
   se citan tal como los documentos del repositorio los registran.
6. **Coste, cuotas y disponibilidad** de ChatGPT, Claude y Codex para el volumen de
   investigación y auditoría que se les trasladaría. No hay ninguna medida de eso en el
   repositorio, y no se ha hecho.
7. **Huecos de numeración de ADR**: en `main` faltan 017, 018, 049, 107, 108, 147 y 148.
   Los dos primeros están tomados por la PR #171, sin fusionar (documentado en
   `SIRIUS_WORK_ENGINE_INVENTARIO.md` §1.5); ADR-148 vive en la rama
   `claude/adr-memoria-bien-hecha`, sin fusionar [V]. **No se ha investigado** dónde
   están 049, 107, 108 y 147, y no se afirma nada sobre ellos.
   Aviso relacionado, porque este documento cita «ADR-016» varias veces: hay **151
   ficheros y solo 150 números distintos**, porque conviven **dos `ADR-016`** [V]. El que
   aquí se cita para el auditor es
   `docs/decisions/ADR-016-el-auditor-se-lanza-por-etiqueta-y-no-escribe-nunca.md`, no
   `ADR-016-el-estado-se-lee-de-main-no-de-la-rama.md`.
8. **El clon de esta sesión es superficial** (`git rev-list --count HEAD` = 50; existe
   `.git/shallow`) [V]. Por eso **ninguna** afirmación de este documento sobre quién
   fusionó qué, ni sobre commits anteriores a esos 50, sale de leer el historial: sale de
   lo que `docs/evolution/STATUS.md` y los propios ADR registran. Los identificadores
   `80611d5`, `c2a44f8`, `bb851b8` y `a6f8e49` que se citan en el apartado 8 **no son
   resolubles desde aquí**, y se transcriben como el registro los da.
9. **Residuo del cruce por tema**: se cruzaron los ADR por asunto (propiedad del motor,
   memoria, interacción, investigación, auditoría, despliegue), no los 151 ficheros uno por uno.
   Puede existir un ADR aprobado que afecte a esta propuesta y que ninguno de los leídos
   cite. Es el límite declarado en la nota de arranque, punto 4.

---

## 6. Requisitos de la memoria común

**No se elige herramienta.** Obsidian, Basic Memory, el propio repositorio, una base
alojada o cualquier otra cosa son candidatos, y esta propuesta no compara ninguno. Lo que
sí hace falta antes de comparar es la lista de lo que tendría que cumplir, porque sin ella
la comparación no tiene criterio.

**Tampoco se fija su lugar en el roadmap.** La memoria común no tiene etapa asignada, y
esta propuesta no se la asigna ni la ordena respecto a Sirius 0.2: son dos trabajos cuya
relación está por estudiar (apartado 7.2, T-5).

### 6.1 Punto de partida comprobado

- **No hay nada declarado como tal, y eso es lo único que la comprobación sostiene.** Ni
  «Obsidian», ni «Basic Memory», ni «memoria compartida», ni «memoria común» aparecen en
  `docs/`, `src/` ni `scripts/` [V, búsqueda vacía]. **Una búsqueda por nombres no prueba
  ausencia funcional**: dice que nadie ha llamado a esto por su nombre, no que la función
  no esté cubierta en parte por otra pieza. La evaluación funcional —qué requisitos de
  6.3 cumple ya cada pieza existente— **no se ha hecho**, y es trabajo previo a elegir
  nada.
- **La separación de las otras dos memorias ya está decidida** (D6, 29-08-2026): la del
  producto en el equipo del propietario, la del motor en su rama. Esa decisión dice
  «permanecen separadas», no dice nada sobre una tercera.
- **Existen tres piezas que ya hacen parte del trabajo**, y conviene mirarlas antes de
  construir: el repositorio mismo (documentos, ADR, `docs/investigaciones/` con caducidad
  declarada, historial de git), el diario del motor en `estado-del-motor`, y la memoria
  del producto (SQLite, con origen consultable y detección de conflictos).
- **Hay un parecido con la puerta de salida de 0.2, y se deja como hipótesis, no como
  dependencia.** Esa puerta pide «construir un paquete de contexto fiable y trazable para
  una tarea externa» (`docs/evolution/RECTOR.md:146`), que se parece a lo que la memoria
  común necesitaría del lado de Sirius. **Parecerse no es depender**: esta propuesta
  **no** convierte 0.2 en requisito previo de la memoria común, ni la memoria común en
  parte de 0.2. Si conviene ligarlas, eso se estudia y se decide aparte (apartado 7.2,
  T-5).

### 6.2 Las tres responsabilidades, sin obligar a tres bases

| Responsabilidad | Quién es dueño | Qué contiene | Qué necesita intercambiar |
|---|---|---|---|
| **Memoria propia de Sirius** | El producto | Identidad, relación, preferencias, recuerdos y decisiones del propietario, contexto conversacional | Publicar hacia la memoria común lo que el propietario confirme; leer de ella para responder |
| **Estado y diario operativo del motor** | El motor | WorkItems, Runs, transiciones, despachos, supervisión, racha | Publicar **desenlaces** (qué se encargó, qué salió, dónde está la evidencia); nunca ceder la autoridad del estado en curso |
| **Conocimiento compartido de los proyectos** | La memoria común | Documentos, investigaciones, decisiones, aprendizajes, continuidad entre proyectos | Ser leída y escrita por las IAs externas y por el motor; sobrevivir al ordenador apagado |

La distinción es de **responsabilidad**, no de infraestructura: dos de las tres podrían
vivir en el mismo sitio físico si el dueño de cada dato queda claro y quien no es dueño
cita en vez de copiar.

### 6.3 Requisitos

**Disponibilidad y acceso**

- R1. Accesible y actualizable **con el ordenador del propietario apagado**. Es el
  requisito que descarta por sí solo cualquier solución que viva únicamente en ese equipo
  —incluida la memoria actual del producto—.
- R2. Legible y escribible por las tres aplicaciones externas y por el motor, **sin que el
  propietario transporte contexto a mano**. Es el objetivo explícito de la visión, y una
  de las tres «bolsas de trabajo humano» que la auditoría de procesos identificó: «el
  transporte de contexto/evidencia»
  (`docs/decisions/ADR-010-auditor-agent-v0-como-primer-piloto.md:16-19`).
- R3. Superviviente a que una de las IAs deje de usarse: ningún dato queda atrapado en el
  historial de un proveedor.

**Contenido y calidad**

- R4. Cada elemento con **origen y fecha**. El repositorio ya exige esto en dos sitios
  distintos y no debería relajarse aquí: el producto tiene `GetMemoryOriginUseCase`/
  `GetDecisionOriginUseCase`, y las investigaciones declaran de qué dependen para caducar.
- R5. **Caducidad declarada** para lo que envejece. Es la lección más cara del
  repositorio: una investigación caducó en veinticuatro horas y tres de los modelos que
  recomendaba ya no existían (AGENTS.md; ADR-095).
- R6. **Una exploración no se convierte en decisión aprobada** por estar escrita ahí
  (`docs/evolution/RECTOR.md` §5; contrato §9). Una memoria que las IAs escriben solas es exactamente
  donde ese error volvería a ocurrir.
- R7. **Regla de conflicto**: qué pasa cuando dos fuentes dicen cosas distintas. El
  producto ya tiene detección determinista de conflictos y precedencia; la memoria común
  necesita la suya, aunque sea «se marca y se pregunta».

**Autoridad y frontera**

- R8. **Un dueño por dato.** Lo que no es de la memoria común se **cita**, no se copia; y
  si se copia, la copia va marcada como espejo no autoritativo, que es el patrón que el
  motor ya usa.
- R9. **Frontera de confidencialidad explícita.** Una memoria que leen IAs externas es una
  superficie de salida de datos. El motor ya tiene la pieza conceptual para esto —la
  política global de egress y `ExportSafeBrief`, arquitectura §6.1 y §7.3— y su regla es
  que la protección debe ser **mecánica**, no un «no filtres» dicho al modelo.
- R10. **Nada de permisos generales.** `docs/evolution/RECTOR.md` §6 y §15: los permisos amplios e
  indefinidos no son el valor por defecto, y un permiso de escritura sobre toda la memoria
  común sería exactamente eso.

**Operación**

- R11. **Historial recuperable**: se puede responder «qué sabíamos y cuándo». El diario
  append-only del motor y `git` son los precedentes internos.
- R12. **Sin gasto nuevo no decidido** (contrato §9: prohibido introducir servicios,
  APIs o suscripciones no aprobadas).
- R13. **Independiente de proveedor** (`docs/evolution/RECTOR.md:26`: «un sistema
  independiente de cualquier proveedor concreto»).
- R14. **El propietario no escribe fichas.** El coste de mantenimiento recae en las IAs y
  en el motor; lo del propietario es confirmar o corregir, no redactar.

### 6.4 Lo que la elección de herramienta tendrá que responder, y aquí no se responde

Dos cosas ya están dadas por la dirección del propietario y no se vuelven a preguntar: la
memoria común es **memoria del trabajo**, y **las IAs la actualizan** (apartado 7.1,
dirección 5). Lo que queda abierto son decisiones técnicas, y viven en el apartado 7.2:

- **T-3** — si formalizarla fuera de EV-004 o enmendar EV-004.
- **T-4** — con qué mecanismo escriben las IAs, y quién arbitra un conflicto.
- **T-5** — cómo se conecta con la memoria propia de Sirius, con el diario del motor, con
  el propio repositorio y con Sirius 0.2; y la evaluación funcional que falta antes de
  decidirlo.
- **T-6** — qué del repositorio privado puede reflejarse ahí.

Una pregunta más, que ninguna de esas cuatro cubre y conviene contestar antes de escribir
código: **qué ocurre cuando la memoria común y el diario del motor discrepan sobre un
trabajo**. La respuesta previsible —manda el motor, que es quien tiene la autoridad del
estado— conviene escribirla antes, no después.

---

## 7. Dirección expresada y decisiones técnicas pendientes

Este apartado separa dos cosas que la primera versión de esta propuesta mezclaba en un
único interrogatorio: **lo que el propietario ya ha decidido** —y por tanto no se le
vuelve a preguntar— y **lo que queda técnicamente abierto**.

### 7.1 Dirección ya expresada por el propietario

Estas seis afirmaciones son dirección dada. No son preguntas, no son hipótesis y esta
propuesta no las reabre. Lo que sí hace es decir, para cada una, **qué documento vigente
la contradice hoy**, porque mientras esos documentos digan lo contrario cualquier trabajo
posterior chocará con ellos.

| Dirección dada | Qué significa operativamente | Qué documento vigente la contradice hoy |
|---|---|---|
| **1. Sirius no intermedia obligatoriamente el trabajo.** El propietario conversa, encarga y decide desde ChatGPT, Claude o Codex | Sirius deja de ser el paso obligatorio y el sintetizador de todo; sigue siendo el compañero personal y de ingeniería | `docs/evolution/RECTOR.md:22`, `:25`, `:58`, `:63`; `docs/evolution/DECISIONS.md` EV-002 y EV-003; `docs/evolution/STATUS.md:23-24` (apartado 4.1, filas 1-4 y 6) |
| **2. La investigación y la auditoría dedicadas pasan a las sesiones externas** | Los dos carriles propios dejan de ser el camino de esos encargos | `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` §11.1 (líneas 628 y 632) y §12.4; `docs/implementation/SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md:476` («OBLIGATORIO en el MVP»); `docs/implementation/AGENTES_SUPERFICIE_DE_INVOCACION.md:73` (apartado 4.1, filas 7-11) |
| **3. Se conservan los revisores y las comprobaciones del ciclo** | Revisor Claude, revisor Codex, agregador, convergencia, corrector y Quality siguen enteros (apartado 2.3) | Ninguno. La dirección coincide con lo vigente; se registra para que una retirada mal delimitada no se los lleve por delante |
| **4. Sirius conserva su memoria propia** | La memoria del producto sigue siendo suya y vive en su equipo | Ninguno. Coincide con la decisión D6 del 29-08-2026 y con ADR-083 |
| **5. La memoria común corresponde al trabajo, y las IAs la actualizan** | Es memoria del trabajo y de los proyectos, no de Sirius; las IAs escriben en ella | `docs/evolution/DECISIONS.md` EV-004 y `docs/evolution/RECTOR.md:69`, que reservan la memoria canónica a Sirius y prohíben que los agentes la modifiquen (apartado 4.1, fila 5). Ver T-3: puede resolverse declarando que la memoria común **no es** la memoria canónica, sin enmendar EV-004 |
| **6. Sirius debe avisar sobre el estado de los trabajos** | Sirius es quien avisa de que algo terminó, falló o necesita atención | Ninguno lo prohíbe. Hoy simplemente no está construido: el canal vigente es GitHub (contrato §7, seis estados notificables) y Sirius no lo lee |

**La dirección no es la enmienda, y conviene no confundirlas.** Que el propietario haya
dicho hacia dónde va **no cambia por sí solo** los documentos aprobados: mientras
`RECTOR.md` §4 y EV-002 sigan escritos como están, cualquier trabajo que los contradiga
seguirá siendo, formalmente, una desviación. La enmienda es un **acto aparte**, con su
forma propia: una decisión nueva de la serie EV o una versión nueva del Rector, y un ADR
para lo que toque al motor y al contrato operativo.

Y esa enmienda es **trabajo, no otra pregunta**. La autoridad es del propietario; la
ejecución no tiene por qué serlo: una IA autorizada por él puede redactar la enmienda,
abrir la PR y preparar el ADR. Lo único que no puede hacer es decidir en su lugar ni
autorizarse a sí misma — igual que hoy con la fusión (contrato §8).

### 7.2 Decisiones técnicas realmente pendientes

Ninguna de estas la resuelve la dirección de 7.1. Donde hay recomendación, se dice; y
**ninguna se ejecuta aquí**.

| Id | Decisión técnica | Por qué sigue abierta | Recomendación inicial |
|---|---|---|---|
| **T-1** *(recomendación ya registrada en ADR-161; sigue sin ordenarse su ejecución)* | **Modo de retirada de los dos carriles**: desactivación reversible, congelación o borrado | La dirección dice *que* se retiran; no dice *cómo*, y las tres opciones tienen costes muy distintos (apartado 2.3) | **Desactivación reversible**: quitar el disparador de cada carril y dejar de despachar esas clases, **conservando el código, los perfiles, los ADR, el historial y los resultados** —`docs/investigaciones/` y los informes de auditoría no se tocan—. Es lo más barato de deshacer si el traslado a las sesiones externas no rinde, y no destruye nada medido. **No ejecutada** |
| **T-2** | Qué se hace con la puerta del implementador que cede el perfil `investigador` (`.github/workflows/implement-sirius-work.yml:171-180`) | Es el único punto de contacto entre un carril a retirar y un workflow del ciclo, y toca `.github/**`, donde la automatización no puede escribir (ADR-002): exige mano distinta | Bajo T-1, **dejarla puesta**: con el carril desactivado no se dispara, y quitarla es un cambio de workflow que no aporta nada mientras la retirada sea reversible |
| **T-3** *(RESUELTA por EV-018: se declara fuera de la memoria canónica, y EV-004 queda sin enmendar)* | Cómo se formaliza la memoria común frente a EV-004: ¿declararla **fuera** de la memoria canónica de Sirius, o enmendar EV-004? | La dirección fija que las IAs la actualizan; no fija si eso exige tocar una decisión aprobada o basta con declarar que es otra cosa | Explorar primero la vía que **no** enmienda EV-004 (memoria del trabajo ≠ memoria canónica de Sirius): es menos invasiva y coherente con la dirección 5 |
| **T-4** | **Con qué mecanismo** escriben las IAs: escritura directa, o propuesta más confirmación; y quién arbitra un conflicto | «Las IAs la actualizan» fija el permiso, no el mecanismo ni el arbitraje; y el repositorio ya tiene una regla que debe sobrevivir: una exploración no se convierte en decisión aprobada (contrato §9) | Ninguna todavía: depende de T-3 |
| **T-5** | **Conexión de la memoria común con lo que ya existe**: con la memoria propia de Sirius, con el diario del motor, con el propio repositorio y con Sirius 0.2 | Es la decisión que esta propuesta declaró mal en su primera versión. Hoy **no está decidida** ninguna de las dos direcciones: ni que 0.2 sea requisito previo, ni que la memoria común dependa de él | Antes de decidir nada, hacer la **evaluación funcional que falta**: qué requisitos de 6.3 cumple ya cada pieza existente. Sin ese dato, ligar 0.2 y la memoria común sería una decisión sin medida detrás |
| **T-6** | **Frontera de salida**: qué del repositorio privado puede reflejarse en la memoria común y llegar a las IAs externas | La dirección no la menciona, y es la que decide si la memoria común es segura. El motor ya tiene la pieza conceptual (política de egress y `ExportSafeBrief`) | Que la protección sea **mecánica** y no una instrucción al modelo, como ya exige la arquitectura del motor §6.1 |
| **T-7** | **Orden del roadmap del producto**: ¿0.3 «Habilidades y permisos» como siguiente etapa tras 0.2? | Es lo que dan las manos a Sirius —herramientas del turno conversacional y avisos—, y hoy no está autorizada. Ordenarlo es del propietario | Ninguna: es una decisión de prioridad suya, y la regla de activación del Rector §17 se aplica igual sea cual sea |
| **T-8** | Si se construye la **delegación especializada de Sirius** para consultas de ingeniería, y cómo se distingue de un encargo del motor | Se conserva como posibilidad (nota de 2.1) y la dirección no la pide ni la descarta. Redefinir 0.4 sin decidir esto la borraría por omisión | Dejarla explícitamente viva al redefinir 0.4, y no construirla hasta que haya una consulta real que la justifique |
| **T-9** | **Camino técnico del aviso**: cómo llega a Sirius el desenlace de un trabajo, y si GitHub Mobile sigue avisando en paralelo | La dirección fija que Sirius avisa; no fija por dónde se entera. Hoy Sirius no lee GitHub, y el motor notifica seis estados por ahí (contrato §7) | Ninguna todavía: conviene decidirlo con T-7 delante, porque el aviso es una habilidad más |
| **T-10** | Reconciliación de **Model Studio** con las etapas 0.5 y 0.6, sin renumerar versiones | Voz y captura están construidas y no aparecen en ningún documento de estado (apartado 4.2, fila 15). La dirección conserva ambas capacidades, así que el hueco documental estorba | Declarar qué parte de 0.5 y 0.6 quedó cubierta y qué falta, sin tocar la numeración |

**Lo que NO hay que decidir todavía:** la herramienta de la memoria común; la numeración
o el alcance de ninguna versión; si el motor se extrae a otro repositorio; y el plan
detallado de implementación de nada de lo anterior.

---

## 8. Anexo — Estado real de aprobación de cada documento citado

Esta tabla existe por el aviso de AGENTS.md y del propio encargo: **una cabecera
«PROPUESTO» no dice el estado real**. Ninguna afirmación de estado de esta propuesta se
hace sin una fila aquí.

Aviso de alcance, por la limitación declarada en 5.5 punto 8: el clon de esta sesión es
superficial, así que la columna «dónde consta su estado real» cita **el registro del
repositorio**, no una verificación del historial de git.

| Documento | Cabecera literal | Dónde consta su estado real | Veredicto usado en esta propuesta |
|---|---|---|---|
| `docs/evolution/RECTOR.md` | «Estado: APROBADO» (línea 5) | `docs/canonical/STATUS.md`: aprobado por el usuario el 22-07-2026 | **APROBADO.** No se toca sin decisión del propietario |
| `docs/evolution/DECISIONS.md` (EV-001…EV-014) | «Estado: APROBADO» | `docs/canonical/STATUS.md`, misma fecha | **APROBADAS** |
| `docs/canonical/STATUS.md` | Sin cabecera de estado: **es** el registro de aprobaciones | Él mismo | **VIGENTE** |
| `docs/evolution/STATUS.md` | «Estado documental: APROBADO» | Él mismo; última modificación 31-08-2026 (`git log`) | **VIGENTE pero desactualizado** en su «Próximo paso» (apartado 4.2, fila 16) |
| `docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` | «Estado: PROPUESTO» | Su propia regla: la aprobación es la fusión de la PR que lo introduce. `docs/evolution/STATUS.md` registra la fusión de la PR #410 por el propietario el 28-08-2026 | **APROBADO.** La palabra de la cabecera no se reescribe tras la fusión |
| `docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md` | «Estado: PROPUESTO» | Su propia cabecera fija esa regla (líneas 9-15); `docs/evolution/STATUS.md` registra la fusión de la PR #418 (`80611d5`, 29-08-2026) | **APROBADO** |
| `docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md` | «Estado: PROPUESTO» | Misma regla (líneas 9-11); fusión de la PR #420 (`c2a44f8`) según `docs/evolution/STATUS.md` | **APROBADO** |
| `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` | «Versión 1.9 · Estado: VIGENTE» | Él mismo, §10.9; su §7 fue enmendado por ADR-157 el 07-09-2026 | **VIGENTE.** Enmendarlo exige decisión, no edición |
| ADR-019, ADR-020 | «Estado: APROBADO — por la fusión de la PR #173 / #175» | Su propia cabecera | **APROBADOS**, con la enmienda que ADR-082 les introduce |
| `docs/implementation/SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md` | «Estado: APROBADO — por la fusión de la PR #175» | Su propia cabecera (regla de ADR-020) | **APROBADO** |
| ADR-082 | «Estado: PROPUESTO» | Aprobación declarada = fusión de su PR. `docs/evolution/STATUS.md` lo trata como vigente («con las enmiendas que ADR-082 introduce») y `docs/operations/MOTOR_DE_SIRIUS.md` documenta su operación | **APROBADO por fusión** |
| ADR-083 | «Estado: PROPUESTO» | La decisión D6 de `docs/evolution/STATUS.md` registra la fusión de la PR #301 (`bb851b8`, 24-08-2026) y su cierre por ejecución en la PR #304 (`a6f8e49`) | **APROBADO por fusión** |
| ADR-010, ADR-016 (auditor); ADR-095, ADR-097, ADR-098, ADR-099 (investigador) | «Estado: PROPUESTO» | Su regla de aprobación es la fusión de su PR; los seis ficheros están en `main` [V], y el contrato §8 reserva la fusión al propietario | **APROBADOS por fusión.** No se ha verificado el actor de cada fusión desde esta sesión |
| ADR-157 | «Estado: ACEPTADO (fusionado en `main` como `07a51b1` el 07-09-2026)» | Su cabecera; el commit **sí** es resoluble aquí [V] | **VIGENTE** |
| ADR-124, ADR-125 | «Estado: APROBADO» | Su cabecera | **APROBADOS** |
| ADR-119, ADR-120, ADR-126 a ADR-131 | «Estado: PROPUESTO» | Están en `main` [V]; su regla es la fusión | **En vigor como diseño de la ola**; se citan como trabajo en curso, no como cierre |
| `docs/implementation/SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md` | «Estado: DISEÑO / RECONCILIACIÓN. No autoriza implementación, merge ni cambio canónico» | Su cabecera | **DISEÑO.** Se cita como diseño, no como autorización |
| `docs/implementation/SIRIUS_WORK_ENGINE_INVENTARIO.md` | «Estado: DISEÑO / RECONCILIACIÓN» + base `e13a1e3`, 15-08-2026 | Su cabecera | **FOTO FECHADA.** Se cita siempre con su fecha (apartado 4.3) |
| `docs/implementation/AGENTES_SUPERFICIE_DE_INVOCACION.md` | «Este documento no autoriza nada por sí mismo; lo que autoriza el workflow del Auditor es ADR-016» | Su cabecera | **PREPARATORIO**, y desalineado (apartado 4.1, filas 10-11) |
| `docs/implementation/AUDITOR_AGENT_V0.md` | «este documento **es** el agente»; autorizado por ADR-010 | Su cabecera | **VIGENTE mientras el carril exista** |
| `docs/implementation/bloques_del_motor.yml` | Registro con regla propia: `estado: cerrado` exige evidencia repetible, comprobado por `tests/automation/test_registro_de_bloques.py` | Él mismo | **REGISTRO VIGENTE** |
| `docs/evolution/SIRIUS_AI_CORE_AND_MODEL_STRATEGY.md` | «recolección informativa de ideas… no aprobado como cambio de arquitectura» | Su cabecera | **NO NORMATIVO.** No se usa como fuente de ninguna afirmación de esta propuesta |
| `docs/implementation/model_studio/*` | «APROBADA POR EL USUARIO» (reconciliación R-01…R-11); «APROBADO COMO DIRECCIÓN DE DISEÑO» (UI-001) | Sus cabeceras | **APROBADOS en su ámbito**, y sin reflejo en ningún documento de estado (apartado 4.2, fila 15) |
| `README.md`, `REPOSITORY_STATUS.md` | Sin cabecera de estado | `REPOSITORY_STATUS.md` declara que el estado por bloque se lee en `V8_EXECUTION.md` (ADR-005) | `README.md` contiene una afirmación **falsa** (apartado 4.2, fila 14) |
| PR #117 (`evidence/adr001-spikes`), PR #171 | Abiertas, sin fusionar | `docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` §1; `SIRIUS_WORK_ENGINE_INVENTARIO.md` §1.5 | **NO SON `main`.** Nada de esta propuesta se apoya en ellas |

---

## 9. Cómo seguir

1. **La dirección del apartado 7.1 no necesita respuesta**: ya está dada. Lo que necesita
   es que alguien la escriba donde hoy dice lo contrario — una decisión nueva de la serie
   EV o una versión nueva del Rector, y un ADR para el motor y el contrato operativo. Es
   trabajo, y el propietario puede encargarlo a una IA autorizada sin dejar de ser quien
   decide.
2. **Las diez decisiones técnicas del apartado 7.2 sí necesitan respuesta**, y no todas a
   la vez: **T-1** (modo de retirada) desbloquea el trabajo sobre los dos carriles, y
   **T-3/T-5** desbloquean el de la memoria común. Las demás pueden esperar sin bloquear
   nada.
3. Solo entonces se prepara el plan de implementación, que el encargo excluye
   expresamente de aquí.

**Si falta información:** las nueve cuestiones no verificadas del apartado 5.5 son las que
faltan, y ninguna de ellas bloquea las decisiones del apartado 7.2. Se añade una décima
que esta revisión deja abierta a propósito: la **evaluación funcional** de qué requisitos
de 6.3 cumple ya cada pieza existente (T-5). No se ha hecho, y sin ella no debería
decidirse la relación entre la memoria común y Sirius 0.2. La que más se acerca a
bloquear es el coste de trasladar investigación y auditoría a las aplicaciones externas
(5.5, punto 6): **no hay ninguna medida de eso en el repositorio**, y esta propuesta no la
inventa.
