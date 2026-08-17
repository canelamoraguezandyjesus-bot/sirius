# Estado actual del repositorio

## Estado canónico

- Producto Sirius 0.1: aprobado.
- Arquitectura técnica 0.1: aprobada.
- Decisiones ATD-001 a ATD-012: aprobadas.
- Implementación autorizada por verticales, sin ampliar el alcance aprobado.

## Implementación técnica disponible

- V0: repositorio, entorno reproducible, PySide6, Ruff, mypy, pytest y CI en Windows.
- V1: rutas locales y configuración no sensible.
- V2: historial persistente con SQLite y Alembic.
- V3: infraestructura de proyecto activo único y persistente.
- V4: infraestructura de memoria genérica versionada, archivo y eliminación.
- V5: identidad versionada y constructor básico de contexto.
- V6A: interfaz de conversación con proveedor simulado.
- V6B: adaptador OpenAI, streaming, cancelación, errores tipados internos, idempotencia y presupuesto persistente.
- V7A: Windows Credential Manager, configuración del proveedor, diagnóstico local y protección frente a configuraciones inválidas.
- V7: creación, validación y restauración segura de copias cifradas, incluida su interfaz.
- V8: las correcciones de V8.1 están construidas por bloques (B1 a B11), más
  el empaquetado de B13. Qué entrega cada bloque, en qué estado está y qué
  defecto del catálogo cierra se lee en la tabla de bloques operativos de
  [`docs/implementation/V8_EXECUTION.md`](docs/implementation/V8_EXECUTION.md#bloques-operativos),
  que por ADR-005 es el único registro de estado del repositorio. Este archivo
  describe qué hay construido; no dice en qué punto está, precisamente porque
  la automatización no puede escribirlo y por eso se quedaba atrás.

En términos de capacidad, lo construido dentro de V8 cubre: el onboarding de
primera apertura con política de datos y validación de la credencial antes de
guardarla; la elección y persistencia de la ruta local de datos antes de abrir
SQLite; el proyecto activo completo —creación, continuidad observable con
estado, bloqueos y siguiente paso, y ciclo de vida versionado sobre revisiones
inmutables—; la memoria y las decisiones al completo —guardado manual con
origen consultable, aprobación explícita, corrección versionada, sustitución,
archivo, eliminación con redacción de origen y detección determinista de
conflictos, integrado todo en la pestaña «Memoria y decisiones»—; el panel de
contexto de solo lectura; la selección, relevancia y presupuesto del contexto
sobre índices FTS5; el reintento de un envío fallido sin reescribirlo, los
errores accionables y el aviso de presupuesto; el Markdown seguro con bloques
de código copiables; la exportación estructurada; la política de rechazo de
acciones fuera de alcance; y la prueba de recuperación tras un cierre forzado.

Estas entradas describen infraestructura o hitos de implementación. No demuestran por sí solas que la capacidad completa de producto sea utilizable ni que sus pruebas de aceptación hayan pasado.

En particular:

- el constructor de contexto ya aplica la selección, la relevancia y la
  política de presupuesto aprobadas (B6a a B6d), pero eso lo demuestran
  pruebas automáticas con dobles deterministas, no una prueba de aceptación
  formal;
- el estado de cada prueba de aceptación —incluidas las que exigen proveedor
  real, Windows real o evaluación humana— se lee en el registro, nunca aquí;
- el trazado formal requisito–prueba está declarado en
  [`docs/implementation/TRAZABILIDAD_PA_SP.md`](docs/implementation/TRAZABILIDAD_PA_SP.md)
  y comprobado por máquina (`tests/unit/test_pa_sp_traceability.py`, ADR-006).
  El estado de cada bloque se lee en la tabla de bloques operativos de
  [`docs/implementation/V8_EXECUTION.md`](docs/implementation/V8_EXECUTION.md#bloques-operativos),
  que por ADR-005 es el único sitio que lo declara.

## Estado de verificación

### Confirmado automáticamente

- GitHub Actions ejecuta las comprobaciones en Linux en cada pull request y merge;
  la validación en Windows es puntual y bajo demanda.
- Ruff format, Ruff lint, mypy estricto y pytest han pasado en las pull requests integradas examinadas.
- Las pruebas normales usan proveedores y streams simulados y no realizan llamadas de red reales.
- Las pruebas de `keyring` no leen ni escriben en el Credential Manager real.
- La creación, validación y restauración de copias están cubiertas automáticamente e integradas en la interfaz.
- La validación de credencial antes de guardarla está cubierta automáticamente e
  integrada en la interfaz, siempre contra un validador simulado (nunca contra el
  proveedor real).
- La selección y persistencia de la ruta local de datos (B2b) resuelve la
  ubicación antes de SQLite, logging y composición; cubierta automáticamente con
  dobles deterministas, sin datos reales, sin OneDrive real y sin red.
- El saludo inicial y la creación utilizable del primer proyecto (B3a) están
  cubiertos automáticamente (unidad, integración con SQLite real y GUI), con
  la protección contra un segundo proyecto activo verificada antes de
  escribir cualquier dato; sin datos reales y sin red.
- La continuidad observable del proyecto activo (B3b: estado, bloqueos,
  siguiente paso, resumen al retomar y contexto actualizado) está cubierta
  automáticamente (unidad, integración con SQLite/Alembic real y GUI); la
  migración que añade `blockers` se probó actualizando una base real desde
  el head anterior sin perder datos; sin datos reales y sin red.
- El ciclo de vida y el versionado del proyecto (B3c: historial de
  revisiones inmutable, completar el proyecto activo sin borrar su
  historial, habilitar un proyecto posterior solo tras completar el actual)
  está cubierto automáticamente (unidad, integración con SQLite/Alembic real
  y GUI); la migración que crea `project_revisions` se probó con relleno
  desde el head anterior y con resincronización al bajar de versión, sin
  perder datos; sin datos reales y sin red.
- B5 está cubierto automáticamente con pruebas GUI sobre el panel de contexto,
  incluidos estados vacíos, filtrado de decisiones APPROVED, origen,
  actualización manual y coordinación con operaciones ocupadas.

### Validación manual

Qué pruebas manuales se han ejecutado, quién las ejecutó y con qué salvedades se
lee en la tabla de evidencia de
[`docs/implementation/V8_EXECUTION.md`](docs/implementation/V8_EXECUTION.md), que
por ADR-005 es el único registro de estado. Esta lista vivía aquí y se quedaba
atrás; era una de las derivas que ADR-005 vino a cerrar.

## Estado de V7

La implementación automatizada de V7 está terminada.

Permanece pendiente únicamente la validación manual de Windows Credential Manager con un valor señuelo. Esta validación no autoriza todavía el uso de una clave API real.

Se corrigió un fallo intermitente en `tests/gui/test_backup_recovery_ui.py` (fuga de
conexión SQLite en el helper de test de bootstrap, no un defecto de producto); el
comportamiento aprobado de V7 no cambió.

## Estado de V8

V8 está iniciada solo en su subetapa correctiva y automatizada.

Puede incluir:

- reconciliación documental;
- corrección de los defectos trazados D-01 a D-11 y A-01 a A-04;
- pruebas con FakeLLM;
- suite automática PA/SP;
- rendimiento local;
- empaquetado;
- comprobaciones de Windows sin clave;
- recopilación de evidencia.

Qué bloque está hecho y cuál no se lee en
[`docs/implementation/V8_EXECUTION.md`](docs/implementation/V8_EXECUTION.md#bloques-operativos).
Aquí no se repite.

La aceptación formal con proveedor real está **completada**: el propietario declaró Sirius 0.1
aceptado y terminado el 10 de agosto de 2026. La declaración, con sus salvedades, vive en
[`docs/implementation/V8_EXECUTION.md`](docs/implementation/V8_EXECUTION.md), que por ADR-005
es el único registro de estado.

La ventana con proveedor real permanece bloqueada hasta que se cumplan las
condiciones de la puerta V8.3, que están escritas en `V8_EXECUTION.md` y no se
duplican aquí. En resumen, lo que falta ya no es trabajo automatizable: es
Windows real, una clave real y el trazado formal de las pruebas de aceptación
(B12).

No se crea una fase canónica adicional denominada `Preparación V8`.

## Método de trabajo vigente

- `main` debe permanecer integrable.
- Los cambios se realizan en ramas breves.
- Se integran mediante pull request y squash cuando las comprobaciones están en verde.
- No se convierten conversaciones exploratorias en requisitos ni cambios de arquitectura.
- Las pruebas visuales, físicas o dependientes del Windows real siguen requiriendo intervención del usuario.
- Antes de volver a trabajar desde el equipo local, debe sincronizarse con `git pull --ff-only origin main`.
- Cada bloque actualiza la tabla de bloques operativos de `docs/implementation/V8_EXECUTION.md` y nada más. Ya no hace falta una PR documental posterior al merge para sincronizar los documentos de raíz: por ADR-005 estos dejaron de declarar estado, así que no se quedan atrás. El implementador automático tiene permiso de escritura sobre `docs/implementation/**`, que es justo donde vive ahora el registro.

## Fuentes históricas

Los documentos anteriores a la aprobación pueden conservar palabras como `PROPUESTO` o instrucciones de preparación inicial ya superadas. `docs/canonical/STATUS.md`, este archivo y `docs/implementation/PLAN.md` reflejan el estado operativo vigente.
