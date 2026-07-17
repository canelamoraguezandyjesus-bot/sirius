# V8 — Ejecución, puertas y evidencia

Este documento es el registro operativo único de V8. No sustituye el Producto, el Plan de Pruebas, la Arquitectura, las ATD ni `docs/implementation/PLAN.md`.

## Estado

- V8.1 — Corrección documental y automatizada: **ACTIVA**.
- V8.2 — Windows sin clave: **BLOQUEADA** hasta integración automática verde.
- V8.3 — Proveedor real: **BLOQUEADA**.
- V8.4 — PA-E2E-01 y cierre: **BLOQUEADA**.
- Sirius 0.1: **NO ACEPTADO** y **NO TERMINADO**.

No se crea una fase canónica adicional denominada `Preparación V8`.

## Fuentes normativas

- `docs/canonical/STATUS.md`
- Definición de Producto Sirius 0.1 aprobada
- Plan de Pruebas y Trazabilidad aprobado
- Arquitectura Técnica Sirius 0.1 aprobada
- ATD-001 a ATD-012
- `docs/implementation/PLAN.md`
- `AGENTS.md`

Los resúmenes de este documento no son normativos. Ante contradicción, prevalecen las fuentes aprobadas.

## Reglas de ejecución

- No ampliar el alcance de Sirius 0.1.
- No cambiar Producto, Arquitectura o ATD sin propuesta y aprobación explícita.
- No usar ni obtener una clave API real hasta abrir formalmente V8.3.
- No introducir voz, robótica, web, archivos externos, herramientas, automatización, RAG, multiagente ni programación supervisada.
- Cada corrección debe enlazar con un requisito aprobado y una prueba identificada.
- Trabajar en ramas breves, con cambios pequeños, reversibles y comprobaciones verdes.
- No confundir infraestructura implementada, comportamiento utilizable, prueba automática, prueba manual y aceptación formal.

## Puertas

### Puerta V8.2 — Windows sin clave

Debe cumplirse:

- integración automática verde sobre el estado exacto que se probará;
- defectos funcionales del bloque correspondiente corregidos;
- ejecutable reproducible disponible cuando la prueba lo requiera;
- guion manual con resultados esperados;
- entorno de datos desechable y copia externa preparada.

### Puerta V8.3 — Proveedor real

Debe cumplirse todo lo anterior y además:

- D-01, D-02, D-03, D-04, D-05, D-08, D-11 y A-01 cerrados;
- D-06, D-07, D-09 y D-10 corregidos o resueltos conforme al Plan de Pruebas;
- A-02 y A-03 verificados;
- suite automática PA/SP sin clave completamente verde;
- Credential Manager comprobado con un valor señuelo;
- copia y restauración comprobadas desde el ejecutable;
- cero defectos bloqueantes o altos conocidos;
- autorización explícita del usuario para obtener y usar una clave temporal.

### Puerta V8.4 — E2E y cierre

Debe cumplirse:

- ventana de proveedor real completada sin defectos bloqueantes;
- PA-001 a PA-025 ejecutables;
- PS-01 a PS-07 preparados para evaluación humana;
- SP-01 a SP-07 ejecutables;
- entorno, versión, commit y artefacto identificados;
- proyecto pequeño de aceptación definido y no canónico.

## Catálogo cerrado de trabajo

| ID | Resumen | Fuente principal | Bloquea proveedor real | Bloquea cierre | Estado | Bloque |
|---|---|---|---:|---:|---|---|
| D-01 | Onboarding y validación de credencial | RF-001/002; PA-001/002 | Sí | Sí | Abierto | B2 |
| D-02 | Proyecto operable | RF-014–018; PA-006–009 | Sí | Sí | Abierto | B3 |
| D-03 | Eventos, memoria y decisiones | RF-019–026; PA-010–016 | Sí | Sí | Abierto | B4 |
| D-04 | Panel de contexto | Producto §9.1 | Sí | Sí | Abierto | B5 |
| D-05 | Reintento sin reescribir | RF-007; PA-003/017 | Sí | Sí | Abierto | B7 |
| D-06 | Markdown seguro y código copiable | RF-008; SP-07 | No | Sí | Abierto | B8 |
| D-07 | Exportación estructurada | RF-031; PA-020; ATD-009 | No | Sí | Abierto | B9 |
| D-08 | Errores accionables | RF-028; RNF-018 | Sí | Sí | Abierto | B7 |
| D-09 | Aviso de presupuesto | RF-030; PA-018 | No | Sí | Abierto | B7 |
| D-10 | Ruta de datos y activación clara | Producto §5.1 | No | Sí | Abierto | B2 |
| D-11 | Contexto pertinente y limitado | RNF-008; SP-03; ATD-007 | Sí | Sí | Abierto | B6 |
| A-01 | Política de acciones fuera de alcance | RF-035; PA-024 | Sí | Sí | Abierto | B10 |
| A-02 | Recuperación tras cierre forzado | RNF-005/006; PA-019 | No | Sí | Abierto | B11 |
| A-03 | Empaquetado reproducible | ATD-011 | Sí, como puerta | Sí | Abierto | B13 |
| A-04 | Evidencia de aceptación trazada | Plan de Pruebas | No, por sí sola | Sí | Abierto | B12/B16 |

Cualquier defecto nuevo debe vincularse a un requisito ya aprobado. Si no puede hacerse, debe detenerse el trabajo y solicitar decisión.

## Bloques operativos

| Bloque | Entrega | Estado |
|---|---|---|
| B1 | Reconciliación documental y trazabilidad | En curso |
| B2 | Onboarding, credencial, ruta y activación | En curso (RF-002, B2a y B2b implementados y cubiertos automáticamente; activación real en Windows pendiente) |
| B3 | Proyecto mínimo y ciclo de vida | En curso (B3a implementado y cubierto automáticamente; bloqueos, decisiones, completar/archivar y resumen al retomar pendientes) |
| B4 | Eventos, recuerdos, decisiones y conflictos | Pendiente |
| B5 | Panel de contexto | Pendiente |
| B6 | Selección y presupuesto de contexto | Pendiente |
| B7 | Reintento, errores y presupuesto | Pendiente |
| B8 | Markdown seguro y copia de código | Pendiente |
| B9 | Exportación estructurada | Pendiente |
| B10 | Política de acciones fuera de alcance | Pendiente |
| B11 | Recuperación tras cierre forzado | Pendiente |
| B12 | Suite PA/SP automática, rendimiento y evidencia | Pendiente |
| B13 | Empaquetado reproducible | Pendiente |
| B14 | Windows sin clave | Bloqueado |
| B15 | Ventana compacta con proveedor real | Bloqueado |
| B16 | PA-E2E-01, regresión y cierre | Bloqueado |

## Criterio de cierre de bloque

Un bloque solo puede marcarse terminado cuando:

- el alcance está trazado a requisitos aprobados;
- las pruebas previstas existen y pasan;
- `scripts/check.ps1` pasa cuando el bloque contiene código;
- CI está verde en la PR;
- no quedan comentarios de revisión sin resolver;
- la documentación operativa refleja el comportamiento real;
- el usuario autoriza el merge.

## Registro de evidencia

Añadir una fila por resultado verificable. No registrar secretos ni contenido sensible.

| Fecha | Bloque | Commit/artefacto | Tipo | Prueba | Resultado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|
| 2026-07-15 | B1 | `a05af3c` | Documental | Reconciliación de estado y puertas | Superada | PR #17, CI Quality verde | Sin cambios funcionales |
| 2026-07-16 | B2 | `fcba319` (PR #19) | automática | `test_validate_and_save_api_key.py`, `test_openai_credential_validator.py`, `test_composition_root_credential_validation.py` | Superada | CI verde, `scripts/check.ps1` verde | RF-002 está implementado y cubierto automáticamente (caso de uso y validador contra el proveedor, sin GUI todavía). D-01 permanece abierto hasta demostrar el resto de sus condiciones |
| 2026-07-16 | B2 | `fba51df` (PR #20) | automática | `test_validated_main_window.py` | Superada | CI verde, `scripts/check.ps1` verde | Integra RF-002 en la GUI (`ValidatedMainWindow`). D-01 permanece abierto: falta RF-001 (pantalla de primera configuración con política de datos); D-10 permanece abierto sin ningún cambio; PA-001 y PA-002 no se declaran superadas — exigen credencial real y quedan bloqueadas hasta V8.3 |
| 2026-07-17 | B2a | `f7134ca` (PR #24) | automática | `test_onboarding_window.py`, `test_app_bootstrap.py`, `test_composition_root_credential_validation.py` (nuevos casos), `test_send_message.py` (`set_llm_provider`), suite GUI de B2a repetida 5 veces | Superada | CI verde, `scripts/check.ps1` verde localmente (Ruff format, Ruff lint, mypy estricto, 360 pytest) | RF-001 implementado y cubierto automáticamente vía `OnboardingWindow` + recomposición segura del proveedor en la misma ejecución (`activate_configured_llm_provider`, sin reinicio). D-01 permanece abierto hasta PA-001/PA-002 con proveedor real; D-10 sigue parcialmente abierto (falta B2b y la comprobación real de Credential Manager); sin clave real ni red |
| 2026-07-16 | B1 | `0f5af4e` (PR #22) | automática | `tests/gui/test_backup_recovery_ui.py` (23/23, 5 repeticiones) | Superada | CI verde, `scripts/check.ps1` verde | Corrección de higiene de prueba (fuga de conexión SQLite en el helper de bootstrap), no defecto de producto; sin cambio de comportamiento aprobado de V7 |
| 2026-07-17 | B2b | `2c60afc` (PR #26) | automática | `test_paths.py`, `test_data_path_validator.py`, `test_bootstrap_location_store.py`, `test_data_location_use_case.py`, `test_data_location_window.py`, `test_app_bootstrap.py`; suite GUI de B2b repetida 5 veces | Superada | CI verde, `scripts/check.ps1` verde localmente (Ruff format, Ruff lint, mypy estricto, 412 pytest) | Selección y persistencia de la ruta local de datos antes de SQLite, logging y composición (D-10, parte de B2). Sin clave real ni red; sin movimiento ni migración de datos existentes |
| 2026-07-17 | B3a | rama `feat/v8-b3-initial-project` (commit local) | automática | `test_project_domain.py` (nuevos casos), `test_initial_project_use_case.py` (unit e integración), `test_initial_project_window.py`, `test_app_bootstrap.py` (nuevos casos); suite GUI de B2a/B2b/B3a repetida 5 veces | Superada | `scripts/check.ps1` verde localmente (Ruff format, Ruff lint, mypy estricto, 455 pytest) | Saludo determinista y creación utilizable del primer proyecto (D-02, parcial). RF-014 cubierto automáticamente; RF-015 protegido en la capa de aplicación; parte inicial de RF-016 (estado y siguiente paso iniciales) cubierta. Sin clave real ni red; sin B3b, B4 ni B5 |

Tipos permitidos: `automática`, `CI`, `manual-Windows`, `proveedor-real`, `evaluación-humana`, `documental`.

## Estado de pruebas de aceptación

Estados permitidos: `no preparada`, `preparada`, `automática superada`, `manual pendiente`, `superada`, `fallida`, `bloqueada`.

| Grupo | Estado | Dependencia principal |
|---|---|---|
| PA-001 a PA-025 | Bloqueada | D-01 a D-11 y A-01/A-02 según prueba |
| PS-01 a PS-07 | Bloqueada | Proveedor real y evaluación humana |
| SP-01 a SP-07 | Bloqueada parcialmente | D-03, D-06, D-11, Windows y proveedor real |
| PA-E2E-01 | Bloqueada | B2 a B15 |

## Próximo trabajo autorizado

B1 (reconciliación documental) integrado. B2 está en curso: RF-002 (validación de
credencial antes de guardar), B2a (primera configuración básica, PR #24, squash
`f7134ca`) y B2b (selección y persistencia de la ruta local de datos, PR #26,
squash `2c60afc`) ya están fusionados en `main`. B3 está en curso: B3a (saludo y
creación del primer proyecto) ya está implementado y cubierto automáticamente, en
la rama `feat/v8-b3-initial-project` (commit local).

### B2a — Primera configuración básica — FUSIONADA (PR #24, squash `f7134ca658e6343779ee6bfe89ad05dd2f0a8ba3`)

Este corte dentro de B2 detecta el estado real de "primera apertura" (ausencia de
clave configurada, mediante `ApiKeySettingsUseCase.has_key()` ya existente) y,
solo en ese estado, presenta un paso distinto de la vista normal
(`OnboardingWindow`, ventana propia construida en `sirius.main`) que:

- detecta ausencia de credencial mediante `ApiKeySettingsUseCase.has_key()`;
- muestra qué datos permanecen locales y qué se envía al proveedor;
- muestra proveedor y modelo predeterminados;
- solicita únicamente la clave;
- reutiliza RF-002 (`ValidateAndSaveApiKeyUseCase`, `CredentialValidationWorker`)
  para validar y guardar;
- tras éxito, activa el proveedor real en la misma ejecución (nueva
  `ConversationDependencies.activate_configured_llm_provider`: selecciona "openai"
  en la configuración no sensible existente y reconstruye el proveedor sobre
  `SendMessageUseCase.set_llm_provider`, sin reiniciar SQLite ni pedir un reinicio
  de Sirius) y abre la conversación principal usando la ruta local predeterminada
  existente (sin editarla en este corte).

Un bloque de texto permanente en Ajustes no equivale a esto: no distingue primera
apertura de uso normal ni conduce a ningún flujo.

La edición de la ruta local queda explícitamente fuera de B2a y pasa a **B2b**,
independiente: la ruta debe resolverse antes de inicializar SQLite y construir las
dependencias completas, no es una modificación limitada a la capa de presentación,
y mezclarla con el onboarding básico ampliaría innecesariamente el riesgo de este
corte.

Con B2a:

- RF-001 queda implementado y cubierto automáticamente.
- D-01 sigue abierto hasta las pruebas formales con proveedor real (PA-001/PA-002).
- D-10 sigue parcialmente abierto: cubre explicar la política de datos y mostrar
  proveedor/modelo predeterminados, pero no la edición de la ruta (B2b) ni la
  comprobación real de activación en Windows (Credential Manager con valor
  señuelo, pendiente de validación manual). El saludo con identidad propia y la
  propuesta de crear/describir el proyecto inicial (última cláusula de Producto
  §5.1) pertenecen a B3 (D-02, capacidad de proyecto utilizable) y no son una
  condición de cierre de D-10.
- PA-001 y PA-002 no se declaran superadas: exigen una credencial real y quedan
  bloqueadas hasta V8.3.

### B2b — Selección y persistencia de la ruta local de datos — FUSIONADA (PR #26, squash `2c60afc2652aadbf3aaa3e8672cd5a1f476e4ac4`)

Este corte dentro de B2 resuelve la ubicación de los datos **antes** de crear
directorios de datos, configurar el logging dependiente de la ruta, abrir
SQLite, ejecutar migraciones o construir repositorios/casos de uso de
persistencia:

- `BootstrapLocationStore` (`sirius.infrastructure.bootstrap_location_store`)
  guarda un puntero JSON mínimo de una única versión de esquema
  (`{"version": 1, "data_dir": "<ruta absoluta>"}`) en el directorio de
  configuración estable de Windows (`SiriusPaths.config_dir`, obtenido vía
  `platformdirs`), ahora fijo e independiente de `data_dir`
  (`resolve_paths(data_dir=...)`); escritura atómica (archivo temporal +
  `os.replace`), lectura segura y error explícito (`LocationFileCorruptedError`)
  ante corrupción, sin caer nunca en una base predeterminada en silencio.
  Separado de `settings.json`, SQLite, el almacén de secretos y la
  configuración del proveedor.
- `WindowsDataPathValidator` (`sirius.infrastructure.data_path_validator`)
  valida cada carpeta candidata: ruta absoluta, caracteres y nombres
  reservados de Windows, ausencia de un archivo ocupando el lugar de la
  carpeta, permiso de escritura probado con un archivo temporal real (nunca
  solo `os.access()`), espacios y Unicode, y reporta si la carpeta ya
  contiene una instalación Sirius (`sirius.db`) o está bajo OneDrive. No deja
  directorios parciales cuando la validación falla tras crear la carpeta.
- `DataLocationUseCase` (`sirius.application.data_location`) orquesta la
  resolución sin conocer SQLite, SQLAlchemy, migraciones ni platformdirs
  directamente: reutiliza silenciosamente una ubicación ya guardada (validada
  de nuevo antes de usarla), conserva sin pantalla de migración una
  instalación existente en la ruta predeterminada cuando todavía no hay
  archivo de ubicación, y solo pide una primera elección cuando ninguna de
  las dos aplica. Bloquea con `DataPathHasExistingInstallationError` una ruta
  personalizada que ya contiene datos de Sirius: este corte no adopta, mueve
  ni migra datos existentes fuera de la ruta predeterminada.
- `DataLocationWindow` (nueva ventana de presentación, independiente de
  `OnboardingWindow`) ofrece la ruta predeterminada ya seleccionada y una
  opción avanzada para elegir otra carpeta; distingue en su texto la ruta
  predeterminada, la personalizada, la advertencia de OneDrive (no
  bloqueante, exige confirmación explícita), el error de acceso y el caso de
  datos existentes no admitidos; se muestra también en modo recuperación
  cuando el archivo de ubicación está corrupto, y solo lo sobrescribe tras
  una elección nueva y válida.
- `sirius.main` resuelve la ubicación antes de cualquier paso dependiente de
  datos (`_build_first_window`) y solo entonces continúa, en la misma
  ejecución, con `initialize_persistence`, la composición y el onboarding de
  credencial de B2a (o la ventana principal si ya hay clave configurada); sin
  reiniciar Sirius y sin duplicar ventanas.

Cubierto con pruebas unitarias y de GUI (`tests/unit/test_paths.py`,
`tests/unit/test_data_path_validator.py`,
`tests/unit/test_bootstrap_location_store.py`,
`tests/unit/test_data_location_use_case.py`,
`tests/gui/test_data_location_window.py`, `tests/gui/test_app_bootstrap.py`),
siempre con dobles deterministas (`tmp_path`, `monkeypatch`, `qtbot`), sin
datos reales, sin clave real, sin Credential Manager real, sin OneDrive real
y sin red. La suite GUI específica de B2b se repitió 5 veces sin fallos.

Con B2b:

- La ruta predeterminada y una ruta personalizada quedan resueltas antes de
  SQLite, cubriendo la parte de D-10 relativa a la ruta de datos (Producto
  §5.1).
- La migración o adopción de datos existentes fuera de la ruta predeterminada
  queda explícitamente fuera de este corte y de D-10.
- D-10 sigue sin cerrarse por completo: falta la comprobación real de
  activación en Windows (Credential Manager con valor señuelo, pendiente de
  validación manual) y la validación manual de rutas reales de Windows
  (unidades de red, permisos reales, OneDrive real).
- PA-001 y PA-002 no se declaran superadas: exigen una credencial real y
  quedan bloqueadas hasta V8.3.
- No se inició B3.

Sin iniciar todavía Windows real ni proveedor real. Sin usar clave real ni red.

### B3a — Saludo inicial y creación utilizable del primer proyecto — IMPLEMENTADA (commit local, rama `feat/v8-b3-initial-project`)

Primer corte dentro de B3: cubre parcialmente RF-014, RF-015 y el inicio de
RF-016, y la cláusula de Producto §5.1 sobre saludar con identidad propia y
proponer crear o describir el proyecto inicial. No completa B3 ni cierra D-02.

- `sirius.domain.project.is_configured()` distingue el placeholder de
  arranque (nombre y objetivo vacíos, sembrado por
  `get_or_create_active_project()` desde V3) de un proyecto realmente
  configurado por el usuario; es la única fuente de verdad para esa
  distinción, reutilizada por el caso de uso y por el arranque.
  `INITIAL_PROJECT_STATE`/`INITIAL_PROJECT_NEXT_STEP` son los valores
  mínimos y centralizados que RF-016 todavía no tenía definidos en ninguna
  fuente aprobada; aplicación, presentación y pruebas comparten esta única
  definición.
- `InitialProjectUseCase` (`sirius.application.initial_project`) consulta si
  el proyecto activo ya está configurado, lo expone de solo lectura y crea
  el primero completando transaccionalmente el placeholder existente (nunca
  insertando una segunda fila: la base ya impone una única fila con
  `is_active=1` mediante su índice único parcial), sin conocer SQLAlchemy ni
  SQLite. Rechaza con `InitialProjectAlreadyConfiguredError` un segundo
  intento cuando ya hay un proyecto configurado, comprobado antes de
  escribir nada y dejando el proyecto existente intacto (RF-015); rechaza
  con `InvalidInitialProjectDataError` un nombre u objetivo vacío tras
  recortar espacios, también antes de tocar el repositorio.
- `InitialProjectWindow` (nueva ventana de presentación, independiente de
  `OnboardingWindow` y de `MainWindow`) muestra un saludo determinista y
  centralizado (`GREETING_TEXT`, nunca generado por el proveedor, que
  reutiliza `sirius.domain.identity.INITIAL_IDENTITY_NAME` en vez de
  duplicar "Sirius" como constante) y solicita únicamente nombre y objetivo;
  foco inicial en el nombre, envío por botón o teclado, controles
  deshabilitados y reactivados de forma segura ante error, sin mostrar
  trazas internas, sin datos parciales al cerrar.
- `sirius.main` extiende la puerta de arranque existente: tras confirmarse
  la clave (ya existente o recién validada en la misma ejecución vía
  `OnboardingWindow`), `_build_post_key_window` consulta
  `InitialProjectUseCase.is_configured()` una única vez —compartida por
  ambos caminos que pueden llegar a "hay clave configurada", sin duplicar la
  comprobación— y solo entonces muestra `InitialProjectWindow`; al crear el
  proyecto se abre `ValidatedMainWindow` en la misma ejecución, sin
  reiniciar SQLite ni reconstruir el resto de repositorios.
- El proyecto configurado llega a `ContextBuilder` mediante el mecanismo ya
  existente (`ProjectRepository.get_active_project()`), sin ningún cambio en
  `sirius.application.context`: como `InitialProjectWindow` bloquea la
  apertura de `ValidatedMainWindow` hasta que el proyecto queda configurado,
  el placeholder vacío nunca llega a construirse un contexto real que se
  envíe al proveedor.

Cubierto con pruebas unitarias, de integración y de GUI
(`tests/unit/test_project_domain.py`,
`tests/unit/test_initial_project_use_case.py`,
`tests/integration/test_initial_project_persistence.py`,
`tests/gui/test_initial_project_window.py`, nuevos casos en
`tests/gui/test_app_bootstrap.py` incluyendo la cadena completa
DataLocationWindow → OnboardingWindow → InitialProjectWindow →
ValidatedMainWindow en una sola ejecución), siempre con dobles deterministas
o SQLite temporal, sin datos reales, sin clave real, sin red y sin
Credential Manager real. La suite GUI de B2a/B2b/B3a se repitió 5 veces sin
fallos.

Con B3a:

- RF-014 (crear con nombre y objetivo) queda implementado y cubierto
  automáticamente.
- RF-015 (impedir dos proyectos activos) queda protegido en la capa de
  aplicación y cubierto automáticamente.
- RF-016 queda cubierto solo en su parte inicial (estado y siguiente paso
  iniciales al crear); la actualización cotidiana, el resumen al retomar y
  el resto de RF-016 quedan pendientes.
- RF-017 y RF-018 no se abordan en este corte.
- D-02 queda parcialmente corregido: la creación del primer proyecto es
  utilizable desde la interfaz. Siguen pendientes de un corte posterior de
  B3: bloqueos del proyecto, decisiones relacionadas, completar y archivar
  conservando historial, y el resumen observable al retomar.
- PA-006 y PA-007 quedan preparadas/cubiertas automáticamente por esta
  implementación, pero no se declaran formalmente superadas (exigen
  evaluación conforme al Plan de Pruebas, no solo cobertura automática).
- No se implementó B3b, B4 ni B5. No se llamó a un proveedor real ni se usó
  una clave real.

## Cierre de V8

V8 solo puede cerrarse cuando:

- PA-001 a PA-025 estén superadas;
- PA-E2E-01 esté superada;
- PS-01 a PS-07 estén evaluadas y aprobadas;
- SP-01 a SP-07 estén superadas;
- no existan defectos bloqueantes o altos;
- los defectos medios estén corregidos o aceptados explícitamente conforme al Plan de Pruebas;
- documentación, código y evidencia coincidan;
- el usuario apruebe explícitamente Sirius 0.1.

Al cerrar Sirius 0.1, este documento se congela como evidencia histórica.