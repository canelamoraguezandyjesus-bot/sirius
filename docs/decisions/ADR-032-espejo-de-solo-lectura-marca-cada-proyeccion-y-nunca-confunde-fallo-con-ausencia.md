# ADR-032 — El espejo de solo lectura de la vía GitHub marca cada proyección como no autoritativa y nunca confunde un fallo de lectura con una ausencia

- Estado: PROPUESTO
- Fecha: 2026-08-18
- Aprobación: la fusión de la PR de la incidencia #193 por el propietario.

## Contexto y problema

A3 (`docs/implementation/SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md`, sección
«A3 — Espejo de solo lectura de la vía GitHub + `contexto.recuperar` v0»,
incidencia #193) pide proyectar el estado real de una incidencia de trabajo
dentro del motor **sin escribir nada**, y una capacidad `contexto.recuperar`
v0 con tres proveedores deterministas. El riesgo declarado en el plan es
**divergencia silenciosa espejo↔GitHub**; la mitigación exigida no es un
consejo, es un requisito: cada proyección lleva instante de lectura y
origen, y nada en la API del espejo puede presentarse como verdad presente.

`scripts/automation/sirius_reconcile.sh` ya acumuló **cinco** hallazgos de
la misma familia -un 503 o un cuerpo vacío convertidos en «no hay PR»,
«Quality sin resultado», «sin observaciones»-, y el 17-08-2026 una
degradación real de GitHub tumbó el ciclo cuatro veces por variantes de lo
mismo. Repetir ese defecto en el espejo (que además alimentará
`contexto.recuperar`, cuya respuesta se cita como evidencia) sería
reintroducir el mismo fallo en un componente nuevo.

## Nota de arranque (publicada aquí; la incidencia #193 solo admite el
comentario `PR abierta: <URL>` por contrato de esta ejecución autónoma, así
que este ADR es el lugar acordado por disciplina-evidencia para el «si no,
el ADR de la rama»)

1. **¿Dónde vive el fallo y dónde pongo el arreglo?** No es una corrección
   de un fallo existente: es una vertical nueva, de solo lectura, detrás de
   un puerto sustituible por fixtures. El "arreglo" -la propiedad que este
   bloque demuestra- es que un fallo de lectura SIEMPRE puede observarse
   desde fuera de la función que falla: cada proveedor del puerto devuelve
   un resultado tipado con su propio `LecturaEstado`, así que quien orquesta
   la proyección puede ver la caída sin depender de que el proveedor
   "informe de su propia muerte" en un valor compartido.
2. **¿Qué NO va a garantizar esto?** No garantiza que el espejo esté
   sincronizado con GitHub en todo instante -solo que, cuando proyecta,
   lleva instante de lectura y origen, y que un fallo nunca se disfraza de
   ausencia-. No implementa síntesis ni resumen en `contexto.recuperar`
   (v0 es puramente determinista: referencias, no afirmaciones). No
   reverifica por una llamada adicional que una PR marcada "abierta" en el
   texto siga abierta de verdad -el espejo cita lo que el texto dice,
   marcado no autoritativo-. No sustituye a `sirius_issue.sh` como
   autoridad de escritura: el motor sigue sin escribir nada en GitHub.
3. **Criterio de parada, decidido antes de ver resultados.** Si la
   reconstrucción del ciclo elegido no reproduce fielmente los estados
   observados tras dos rondas de autorevisión con defectos de la misma
   familia, se para y se busca la raíz en vez de seguir parcheando
   expresiones regulares. Si interpretar un marcador exigiera escribir en
   GitHub, `BLOCKED_BY_DECISION`. Si hiciera falta una dependencia nueva,
   `BLOCKED_BY_DECISION`.
4. **¿Qué hace el fallo imposible en vez de improbable?** `autoritativo` es
   un campo `init=False` con valor fijo `False` en `MirroredWorkItem` y
   `MirroredRun`: ningún llamador puede construir una proyección marcada
   autoritativa, ni por descuido (comprobado con
   `test_mirrored_work_item_no_admite_autoritativo_por_constructor`, que
   verifica que el propio constructor RECHAZA el argumento). La distinción
   lectura-fallida/ausencia se hace estructural con `EspejoIlegibleError`:
   es una excepción, no un valor opcional que alguien podría no comprobar.

## Opciones consideradas

1. **Reutilizar `WorkItem`/`Run` de A1 directamente para el espejo**:
   descartada. Esos tipos representan el estado que EL MOTOR posee y hace
   avanzar por sus propias transiciones controladas; una incidencia de
   GitHub no pasa por esas transiciones (no todo lo que un hilo real hace
   -paradas manuales, reanudaciones fuera de banda, ver #186 comentarios
   37-40- tiene una transición limpia en el dominio de A1). Forzarlo
   mezclaría "lo que el motor decidió" con "lo que alguien más observó" y
   haría MÁS fácil confundir el espejo con la autoridad, exactamente lo que
   el bloque prohíbe. Se creó en su lugar `sirius_engine.domain.mirror`, un
   módulo nuevo que REUTILIZA los enums `WorkItemState`/`WorkItemPhase` de
   A1 (vocabulario, no máquina de estados) sin tocar `work_item.py` ni
   `run.py`: A1/A2 quedan intactos y sus pruebas no se modifican.
2. **Reimplementar en Python la lectura robusta (reintentos,
   REST↔GraphQL, filtro de confianza) que ya existe en
   `sirius_issue.sh`**: descartada como reinterpretación completa. Se
   importa en su lugar `scripts/automation/sirius_convergence.py`
   -`parse_round_records`, `ci_failure_streak`,
   `history_after_last_resume`- como módulo Python real (vía
   `sys.path`/`scripts` como raíz, el mismo mecanismo que
   `tests/engine/conftest.py` ya usa para `experiments/`, y que
   `pyproject.toml` ya asume para pytest y mypy): la interpretación de
   `sirius-round`/`RONDA_HALLAZGOS` y de la racha de Quality es la MISMA
   función que gobierna la convergencia real, no una segunda copia. El
   filtro de autor de confianza (`OWNER` o `github-actions[bot]`) no tiene
   equivalente Python importable -vive como filtro `jq` en bash-, así que
   se trasladó como el mismo predicado booleano, documentado línea a línea
   junto al literal bash que reproduce; es la única semántica que se
   traduce en vez de importarse, y por una razón mecánica (no existe forma
   de importar `jq`), no por preferencia.
3. **El adapter real reintenta y golpea REST/GraphQL como
   `sirius_issue.sh`**: descartada para v0. El requisito de este bloque es
   que un fallo se DISTINGA de una ausencia, no que se oculte tras
   reintentos. El adapter (`GitHubCliMirrorReader`) hace una llamada por
   lectura y traduce cualquier fallo a `NO_DISPONIBLE`; el parámetro
   `ejecutar` es un punto de extensión explícito para quien necesite esa
   robustez adicional. La complejidad de reintento/backoff/fallback sigue
   viviendo, sin duplicar, en `sirius_issue.sh`.
4. **Los tres providers de `contexto.recuperar` hacen búsqueda global
   (todo GitHub, todo el árbol) sin acotar**: descartada para v0. Requiere
   red no determinista y no testeable sin red (requisito 7). Se optó por
   proveedores deterministas sobre entradas explícitas (raíz del árbol,
   lista de incidencias, entradas de `git log` ya leídas), con adapters
   delgados e inyectables para la parte que sí toca el mundo.
5. **Una respuesta sintetizada ("lo que pasó con B12e fue...") en
   `contexto.recuperar` v0**: descartada. El requisito 4 exige referencias,
   no afirmaciones; v0 es determinista y no interpreta.

## Decisión

1. Nuevo módulo `sirius_engine.domain.mirror`: `OrigenLectura` (instante +
   procedencia, obligatorio en todo tipo de proyección),
   `MirroredWorkItem`/`MirroredRun` con `autoritativo: bool` `init=False`
   fijo a `False`, y `EspejoIlegibleError` para distinguir "no pude leer"
   de "leí y no hay".
2. Nuevo puerto `sirius_engine.ports.github_mirror.GitHubMirrorPort`, con
   CUATRO métodos separados (`leer_metadatos`, `leer_cuerpo`,
   `leer_comentarios`, `leer_run_actions`), cada uno con su propio
   `LecturaEstado` (`OK`/`NO_DISPONIBLE`), para poder simular el fallo de
   cada proveedor por separado (requisito 2).
3. `sirius_engine.mirror_projection`: interpreta las lecturas y produce las
   proyecciones. Lanza `EspejoIlegibleError` si metadatos, cuerpo o
   comentarios no se pudieron leer -sin esos tres no hay forma honesta de
   decir "no hay etiqueta"/"no hay PR"/"no hay rondas"-. Reutiliza
   `sirius_convergence.py` importado por ruta de fichero vía `scripts/` en
   `sys.path`.
4. `sirius_engine.adapters.github_cli_mirror.GitHubCliMirrorReader`: adapter
   real sobre `gh api`, una llamada por lectura, `ejecutar` inyectable
   (ninguna prueba de este repositorio toca la red).
   `sirius_engine.adapters.fixture_mirror.FixedGitHubMirrorReader`: doble
   de pruebas, configurable por proveedor.
5. `sirius_engine.context_recall`: `contexto.recuperar` v0 con tres
   proveedores deterministas (árbol del repo, incidencias/PR vía el mismo
   puerto y filtro de confianza, `git log` inyectable) y
   `recuperar_contexto` que los combina y reporta `proveedores_fallidos`
   sin esconder ningún fallo parcial.
6. Fixture real: `tests/engine/fixtures/github_issue_186.json`, capturada
   de la incidencia #186 (elegida en vez de la #148 propuesta por el plan;
   ver «Comprobación que la sostiene»).

## Comprobación que la sostiene

- **Elección de #186 en vez de #148**: el plan propone #148 «si al
  inspeccionarla no cubriera el ciclo completo, elige otra que sí lo haga y
  di cuál y por qué»; el propio plan (§2, bloque A3) ya señala a #186 como
  «candidata excelente: tiene 7 rondas de revisión, 7 de corrección, dos
  paradas y una reanudación manual». Se verificó por API real
  (`gh issue view 186 --repo canelamoraguezandyjesus-bot/sirius`,
  `gh api repos/.../issues/186/comments --paginate`, 41 comentarios) que
  cubre el ciclo completo: implementación (3 `precheck` +
  `IMPLEMENTACION_LISTA`) → Quality en verde → revisión dual
  (`CHANGES_REQUESTED` × 7, `## OBSERVACIONES_ESTRUCTURADAS`) → 7 rondas de
  corrección (`FIXED` × 7, `sirius-round:1..7`) → un `sirius-quality:...
  :failure` seguido de `:success` → bloqueo por
  `convergencia-sin-progreso` → `sirius:completed`. `#148` no se llegó a
  inspeccionar porque #186 ya satisface el criterio explícitamente y evita
  una segunda llamada a la API solo para descartarla.
- **Reconstrucción fiel, verificada dato a dato contra la API real** (no
  solo contra la propia fixture): `mirrored.estado is DELIVERED`,
  `fase is ENTREGAR`, `cerrada is True`, `pr_url` =
  `https://github.com/canelamoraguezandyjesus-bot/sirius/pull/189` (el PR
  real de #186), `head_sha` = `88cd7cfdf561c534f736718f5212057584a45c5c`
  (el SHA del cierre real), 7 rondas con `pendientes` estrictamente
  decreciente (3→1) tal como exige la política de convergencia, racha de
  fallos de Quality = 0 (el único `failure` quedó cerrado por un `success`
  posterior sobre el mismo head). Prueba:
  `tests/engine/test_mirror_projection.py::test_reconstruye_ciclo_completo_de_incidencia_186_desde_fixture`.
- **Contraejemplo real encontrado y corregido durante esta implementación**
  (no hipotético): el comentario #8 de la propia #186 contiene la frase
  literal `Comentario 'PR abierta: <URL>' publicado en la incidencia
  #186.` -el implementador citando su propio marcador como texto
  descriptivo-. La primera versión de `_PR_ABIERTA_RE`
  (`PR abierta:\s*(\S+)`) lo interpretaba como una URL real (`<URL>'`),
  exactamente la divergencia silenciosa que este bloque existe para
  evitar. Corregido exigiendo un esquema `https?://` real; verificado de
  nuevo contra la fixture completa
  (`mirrored.pr_url == ".../pull/189"`, no `<URL>'`) y con una prueba
  dedicada
  (`test_marcador_pr_abierta_citado_en_texto_no_se_confunde_con_uno_real`).
- **Prueba por mutación (ADR-001 §3), las tres exigidas por el requisito
  6, sembradas y vistas fallar de verdad durante esta implementación**:
  1. *Quitar el instante de lectura de una proyección*: se retiró
     temporalmente el argumento `ahora=ahora` de la construcción de
     `OrigenLectura` dentro de `proyectar_work_item` (sustituido por un
     `datetime` fijo distinto del que pasa la prueba). Con la mutación,
     `test_reconstruye_ciclo_completo_de_incidencia_186_desde_fixture`
     (que comprueba `mirrored.origen.leido_en == _AHORA`) pasó de verde a
     rojo. Revertido.
  2. *Hacer que un fallo de lectura se devuelva como ausencia*: se
     sustituyó, en `proyectar_work_item`, el `raise EspejoIlegibleError(...)`
     del chequeo de `comentarios` por `comentarios_ok = ()` (tratar
     `NO_DISPONIBLE` como lista vacía). Con la mutación,
     `test_fallo_de_comentarios_lanza_espejo_ilegible_no_ausencia` pasó de
     verde a rojo (ya no se lanzaba la excepción esperada). Revertido.
  3. *Romper la interpretación de un marcador*: se cambió, en
     `_LABEL_STATE`, la entrada de `"sirius:completed"` de
     `(WorkItemState.DELIVERED, WorkItemPhase.ENTREGAR)` a
     `(WorkItemState.ACTIVE, WorkItemPhase.EJECUTAR)`. Con la mutación,
     DOS pruebas pasaron de verde a rojo:
     `test_reconstruye_ciclo_completo_de_incidencia_186_desde_fixture` (que
     comprueba `mirrored.estado is WorkItemState.DELIVERED`) y
     `test_leer_y_proyectar_orquesta_las_tres_lecturas_del_puerto` (mismo
     campo, vía la orquestación del puerto). Revertido.
  Las tres mutaciones se sembraron y revirtieron de verdad, en orden,
  reejecutando `uv run pytest tests/engine/test_mirror_projection.py -q`
  antes y después de cada una (verde -> mutación -> rojo -> revertir ->
  verde), sobre `src/sirius_engine/mirror_projection.py`.
- **Validaciones obligatorias en verde** sobre el repositorio completo:
  `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run mypy src tests`, `uv run pytest` (ver el comentario de la PR
  para el recuento exacto de esta ejecución).
- **Frontera intacta**: `tests/engine/test_boundary.py` cubre todo
  `src/sirius_engine/` por directorio (no por fichero individual), así que
  los módulos nuevos quedan bajo la misma prueba estructural sin
  modificarla.
- **Ninguna prueba nueva accede a la red**: todas las pruebas de
  `test_mirror_projection.py`, `test_context_recall.py` y
  `test_github_cli_mirror.py` operan sobre `LecturaEstado`/fixtures/dobles
  inyectados; el único proceso externo real que invoca alguna prueba es
  `git` local (no red) en `test_context_recall.py`, y con `ejecutar`
  sustituido por un doble salvo en las pruebas puramente de análisis de
  formato.

## Consecuencias

- `contexto.recuperar` v0 puede responder «¿qué pasó con B12e?» con
  referencias verificables (fichero+línea, incidencia+comentario, commit),
  nunca con una afirmación sin sostén, satisfaciendo la prueba de terminado
  del plan.
- Cualquier bloque posterior (A5 en adelante) que necesite leer el estado
  de una incidencia real dispone ya del puerto, el adapter real y el doble
  de pruebas; no necesita reinventar la interpretación de marcadores.
- El adapter real (`GitHubCliMirrorReader`) no reintenta por sí mismo: un
  futuro consumidor con necesidad de esa robustez debe envolver
  `ejecutar` explícitamente, o -si el patrón se repite en varios
  consumidores- promoverlo a una función compartida en un bloque
  posterior. No es una limitación oculta: queda documentada aquí y en el
  docstring del adapter.
- El espejo sigue sin ser autoridad: D1 (conmutación de canonicidad) sigue
  pendiente y sin tocar por este bloque.

## Alternativas descartadas y por qué

Las cinco opciones de la sección «Opciones consideradas». Además: exponer
`contexto.recuperar` como un endpoint HTTP o CLI propio (fuera de alcance;
A3 entrega la capacidad, no una interfaz nueva); cachear las lecturas del
espejo entre invocaciones (introduciría el propio riesgo de divergencia
silenciosa que el bloque prohíbe, y no lo pide ningún requisito de v0).
