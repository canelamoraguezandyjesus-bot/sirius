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
- V8 (parcial, dentro de B2): validación de credencial contra el proveedor antes de
  guardarla (RF-002), integrada en la interfaz (`ValidatedMainWindow`). RF-002 está
  implementado y cubierto automáticamente. Además (B2a, commit local en
  `feat/v8-b2a-first-run-onboarding`, sin PR todavía), la pantalla de primera
  apertura (`OnboardingWindow`) se muestra únicamente cuando
  `ApiKeySettingsUseCase.has_key()` es falso, explica la política de datos, muestra
  proveedor y modelo predeterminados, y activa el proveedor real en la misma
  ejecución tras validar y guardar la clave, sin exigir reinicio. RF-001 está
  implementado y cubierto automáticamente. D-01 permanece abierto hasta demostrar
  el resto de sus condiciones (pruebas formales con proveedor real, PA-001/PA-002).
  Además (B2b, commit local en `feat/v8-b2b-data-path`, sin PR todavía), la
  ubicación de los datos se resuelve, valida y persiste antes de crear directorios
  de datos, configurar el logging dependiente de la ruta, abrir SQLite o construir
  la composición: `BootstrapLocationStore` guarda un puntero JSON atómico y
  mínimo en el directorio de configuración estable de Windows (independiente de
  `data_dir`), `WindowsDataPathValidator` prueba escritura real y detecta
  instalaciones existentes y carpetas bajo OneDrive, y `DataLocationWindow`
  ofrece la ruta predeterminada ya seleccionada con una opción avanzada para
  elegir otra carpeta, solo cuando hace falta una primera elección. Una ruta
  personalizada con datos existentes se bloquea sin adoptarla ni migrarla; un
  archivo de ubicación corrupto nunca abre una base predeterminada en silencio.
  D-10 permanece parcialmente abierto: falta la comprobación real de activación
  en Windows (Credential Manager, pendiente de validación manual) y la
  validación manual de rutas reales de Windows. El saludo con identidad propia y
  la propuesta de proyecto inicial pertenecen a B3 y no son una condición de
  cierre de D-10.

Estas entradas describen infraestructura o hitos de implementación. No demuestran por sí solas que la capacidad completa de producto sea utilizable ni que sus pruebas de aceptación hayan pasado.

En particular:

- el proyecto sigue incompleto como capacidad observable de producto;
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
