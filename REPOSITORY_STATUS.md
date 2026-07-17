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
- V8 (parcial, dentro de B2 y B3): validación de credencial contra el proveedor
  antes de guardarla (RF-002), integrada en la interfaz (`ValidatedMainWindow`).
  RF-002 está implementado y cubierto automáticamente. Además (B2a, PR #24,
  squash `f7134ca658e6343779ee6bfe89ad05dd2f0a8ba3`, fusionado en `main`), la
  pantalla de primera apertura (`OnboardingWindow`) se muestra únicamente cuando
  `ApiKeySettingsUseCase.has_key()` es falso, explica la política de datos, muestra
  proveedor y modelo predeterminados, y activa el proveedor real en la misma
  ejecución tras validar y guardar la clave, sin exigir reinicio. RF-001 está
  implementado y cubierto automáticamente. D-01 permanece abierto hasta demostrar
  el resto de sus condiciones (pruebas formales con proveedor real, PA-001/PA-002).
  Además (B2b, PR #26, squash `2c60afc2652aadbf3aaa3e8672cd5a1f476e4ac4`,
  fusionado en `main`), la ubicación de los datos se resuelve, valida y persiste
  antes de crear directorios de datos, configurar el logging dependiente de la
  ruta, abrir SQLite o construir la composición: `BootstrapLocationStore` guarda
  un puntero JSON atómico y mínimo en el directorio de configuración estable de
  Windows (independiente de `data_dir`), `WindowsDataPathValidator` prueba
  escritura real y detecta instalaciones existentes y carpetas bajo OneDrive, y
  `DataLocationWindow` ofrece la ruta predeterminada ya seleccionada con una
  opción avanzada para elegir otra carpeta, solo cuando hace falta una primera
  elección. Una ruta personalizada con datos existentes se bloquea sin adoptarla
  ni migrarla; un archivo de ubicación corrupto nunca abre una base
  predeterminada en silencio. D-10 permanece parcialmente abierto: falta la
  comprobación real de activación en Windows (Credential Manager, pendiente de
  validación manual) y la validación manual de rutas reales de Windows. Además
  (B3a, PR #27, squash `882ab62416574e6a77c4714c6510565c1b670b1d`, fusionado en
  `main`), tras resolver la ruta y configurar la clave, Sirius distingue el
  placeholder vacío de arranque de un proyecto realmente configurado
  (`sirius.domain.project.is_configured()`), y `InitialProjectUseCase` crea el
  primero completando ese placeholder (sin insertar una segunda fila) con
  nombre, objetivo y un estado/siguiente paso iniciales mínimos y centralizados;
  `InitialProjectWindow` muestra un saludo determinista (reutiliza
  `INITIAL_IDENTITY_NAME`, nunca generado por el proveedor) y se muestra solo
  cuando hay clave configurada pero ningún proyecto todavía, abriendo
  `ValidatedMainWindow` en la misma ejecución al crearlo. RF-014 y RF-015 están
  implementados y cubiertos automáticamente; RF-016 solo en su parte inicial.
  D-02 queda parcialmente corregido: quedan pendientes bloqueos, decisiones
  relacionadas, completar/archivar conservando historial y el resumen al
  retomar, para un corte posterior de B3. Además (B3b, PR #28, squash
  `a2f74df935f32835506c3228b328c2b9b6eec13b`, fusionado en `main`), Sirius
  conserva y muestra la continuidad del proyecto activo: `Project.blockers`
  (texto libre, migración Alembic no destructiva `66951344e4b9`, probada con
  Alembic real desde el head anterior) se añade junto a estado y siguiente
  paso; `ProjectContinuityUseCase` consulta y actualiza los tres campos en una
  sola escritura, rechazando la ausencia de proyecto o el placeholder y un
  estado o siguiente paso vacío, y traduciendo cualquier fallo de
  infraestructura a un error seguro; `ProjectContinuityWidget`, insertado por
  `MainWindow` encima del historial en la pestaña "Conversación" existente
  (sin pestaña ni ventana nueva), muestra un resumen local y determinista con
  el siguiente paso destacado ("Ahora toca: …") y permite actualizar
  estado/bloqueos/siguiente paso; `render_instructions()` incluye ahora
  nombre y bloqueos en la sección "# Proyecto activo" enviada al proveedor.
  RF-016 queda cubierto salvo la parte de "decisiones" (B4); RF-017 queda
  implementado y cubierto automáticamente. D-02 sigue parcialmente
  corregido: quedan pendientes decisiones relacionadas, completar el
  proyecto conservando historial y habilitar un proyecto posterior. Además
  (B3c, PR #29), Sirius versiona la continuidad del proyecto activo y
  permite cerrarlo: el historial ya no vive en columnas planas sino en
  `project_revisions`, revisiones inmutables versionadas, con
  `projects.current_revision_id` (campo mínimo de la arquitectura aprobada,
  SIRIUS-ARQ-0.1 S7.3) como único
  puntero autoritativo a la revisión vigente — con clave foránea física
  hacia `project_revisions.id`, y validación en el repositorio de que la
  revisión referenciada pertenece al mismo proyecto — sembradas por
  migración Alembic no destructiva `6f710ea6c2d2` (relleno de la fila
  existente en revisión 1 con su puntero fijado, resincronización de
  columnas heredadas vía ese mismo puntero al bajar de versión);
  `ContextBuilder` ya no exige un proyecto activo para construir el
  contexto: su ausencia (ninguno creado todavía, o el último se acaba de
  completar) deja `Context.project` en `None`, conforme al contrato
  aprobado (`LLMRequest.project_context: str | None`), y
  `render_instructions()` omite entonces la sección "# Proyecto activo"
  entera; `ProjectLifecycleUseCase`
  completa el proyecto activo (RF-018, "Marcarlo completado sin borrar su
  historial") sin eliminar ni reescribir nada; `ProjectContinuityWidget` añade
  el botón "Completar proyecto" con confirmación explícita antes de escribir;
  al completar, `sirius.main` cierra la ventana principal y reabre
  `InitialProjectWindow` en el mismo proceso — sin reiniciar Sirius y sin
  reactivar ni sobrescribir jamás el proyecto cerrado — reutilizando el mismo
  camino que ya usa el arranque cuando no hay proyecto configurado. Solo se
  implementa COMPLETED: el texto aprobado de RF-018 no menciona archivar, y
  ARCHIVED queda fuera de alcance de Sirius 0.1. RF-018 queda implementado y
  cubierto automáticamente. D-02 queda cerrado en lo que respecta a B3
  (decisiones relacionadas siguen perteneciendo a B4).

Estas entradas describen infraestructura o hitos de implementación. No demuestran por sí solas que la capacidad completa de producto sea utilizable ni que sus pruebas de aceptación hayan pasado.

En particular:

- el proyecto ya cubre el ciclo de vida hasta donde llega B3: B3a, B3b y B3c
  cubren el saludo inicial, la creación del primer proyecto, su continuidad
  (estado, bloqueos, siguiente paso, resumen al retomar) y completarlo
  conservando su historial, pero las decisiones relacionadas (B4) quedan
  pendientes;
- la memoria no contiene todavía toda la semántica aprobada de decisiones, eventos, sustitución, conflictos y origen consultable;
- no existe todavía el panel de contexto;
- el constructor de contexto no aplica aún toda la selección, precedencia y política de presupuesto aprobadas.

## Estado de verificación

### Confirmado automáticamente

- GitHub Actions funciona en Windows.
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

### Pendiente de validación manual

- Guardar, consultar mediante el sistema y eliminar un valor señuelo en Windows Credential Manager.
- Construir y ejecutar el artefacto empaquetado en Windows 11.
- Comprobar escalado, teclado, foco, rutas, cierre forzado y restauración empaquetada.
- Ejecutar posteriormente la ventana autorizada con proveedor real.
- Completar PA-E2E-01, PS-01 a PS-07 y las pruebas manuales de seguridad y privacidad.

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

No se considera iniciada la aceptación formal con proveedor real.

La ventana con proveedor real permanece bloqueada hasta que:

- estén resueltos D-01, D-02, D-03, D-04, D-05, D-08, D-11 y A-01;
- exista un ejecutable reproducible;
- la suite automática y FakeLLM estén verdes sobre la integración exacta;
- Credential Manager haya sido comprobado con un valor señuelo;
- copia y restauración hayan sido verificadas en el ejecutable;
- no exista una contradicción documental material.

No se crea una fase canónica adicional denominada `Preparación V8`.

## Método de trabajo vigente

- `main` debe permanecer integrable.
- Los cambios se realizan en ramas breves.
- Se integran mediante pull request y squash cuando las comprobaciones están en verde.
- No se convierten conversaciones exploratorias en requisitos ni cambios de arquitectura.
- Las pruebas visuales, físicas o dependientes del Windows real siguen requiriendo intervención del usuario.
- Antes de volver a trabajar desde el equipo local, debe sincronizarse con `git pull --ff-only origin main`.

## Fuentes históricas

Los documentos anteriores a la aprobación pueden conservar palabras como `PROPUESTO` o instrucciones de preparación inicial ya superadas. `docs/canonical/STATUS.md`, este archivo y `docs/implementation/PLAN.md` reflejan el estado operativo vigente.
