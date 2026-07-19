# Plan de implementación por verticales

Cada vertical debe producir una parte usable, probada y documentada antes de iniciar la siguiente.

## Estado global

- V0 a V6B: infraestructura de las verticales implementada.
- V7A: implementada y endurecida.
- V7: implementación automatizada terminada; permanece la validación manual de Windows Credential Manager con un valor señuelo.
- V8: INICIADA únicamente en corrección documental, corrección funcional y automatización sin clave API.
- Aceptación manual con proveedor real: BLOQUEADA.
- Sirius 0.1: NO ACEPTADO y NO TERMINADO.

Las etiquetas de este archivo describen hitos de implementación. No constituyen evidencia suficiente de cumplimiento funcional ni sustituyen las pruebas PA, PS, SP o PA-E2E-01.

Una vertical puede tener su infraestructura implementada y mantener defectos de producto abiertos que deban corregirse dentro de V8.

## V0 — Repositorio y humo — COMPLETADA

- entorno reproducible;
- ventana mínima ejecutable;
- Ruff, mypy, pytest y CI;
- documentación canónica accesible.

## V1 — Aplicación local y configuración básica — COMPLETADA

- arranque real;
- rutas locales de datos;
- configuración no sensible;
- almacén de secretos abstracto y simulado.

## V2 — Historial persistente — COMPLETADA

- SQLite y migración inicial;
- conversación y mensajes;
- persistencia transaccional;
- recuperación entre sesiones.

## V3 — Infraestructura de proyecto activo — IMPLEMENTADA; CAPACIDAD DE PRODUCTO PARCIALMENTE COMPLETA (B3a, B3b, B3c)

Implementado:

- persistencia de un único proyecto activo, con historial de continuidad
  versionado e inmutable (`project_revisions`, B3c): cada actualización de
  estado, bloqueos o siguiente paso crea una revisión nueva en vez de
  sobrescribir la anterior;
- campos de nombre, objetivo, estado, bloqueos (B3b) y siguiente paso;
- recuperación del registro activo al iniciar;
- restricción estructural de un solo proyecto activo;
- creación utilizable desde un caso de uso de aplicación
  (`InitialProjectUseCase`) y desde la interfaz (`InitialProjectWindow`,
  B3a): nombre y objetivo, con estado y siguiente paso iniciales mínimos y
  centralizados, protegida contra un segundo proyecto activo;
- continuidad utilizable desde un caso de uso de aplicación
  (`ProjectContinuityUseCase`) y desde la interfaz
  (`ProjectContinuityWidget`, B3b): actualización conjunta de estado,
  bloqueos y siguiente paso, resumen observable al abrir la conversación y
  siguiente paso destacado ("Ahora toca: …");
- ciclo de vida del proyecto (`ProjectLifecycleUseCase`, B3c, RF-018):
  completar el proyecto activo sin borrar su historial, con confirmación
  explícita ("Completar proyecto") en `ProjectContinuityWidget`; un
  proyecto siguiente solo puede crearse tras completar el actual —
  `InitialProjectWindow` se reabre en el mismo proceso, sin reiniciar
  Sirius, y nunca reutiliza ni reactiva el proyecto cerrado.

Pendiente dentro de V8:

- decisiones relacionadas (B4);
- pruebas PA-008, PA-009 y la parte correspondiente de PA-E2E-01 (PA-006 y
  PA-007 quedan preparadas/cubiertas automáticamente por B3a, sin declararse
  formalmente superadas; PA-008 exige además una decisión registrada, y
  PA-009 una recomendación evaluada del proveedor real).

Defectos relacionados: D-02 y D-04.

## V4 — Infraestructura de memoria versionada — IMPLEMENTADA; CAPACIDAD DE PRODUCTO INCOMPLETA

Implementado:

- recuerdo genérico versionado;
- origen obligatorio como valor no vacío;
- corrección mediante nueva revisión;
- archivo;
- redacción del contenido estructurado al eliminar.

Implementado además en V8 (B4a, B4b, B4c):

- evento de origen persistente y enlace real recuerdo/decisión-evento-mensaje,
  con guardado manual explícito y consulta de origen (B4a, RF-019, RF-021,
  PA-010);
- entidad de decisión (asunto, proyecto, estado, versión, fecha y origen)
  sobre la infraestructura de conocimiento existente, con los dos estados
  mínimos propuesta/aprobada, un caso de uso explícito para proponer y otro,
  distinto, que exige confirmación explícita para aprobar; una exploración o
  debate conversacional nunca crea ni aprueba una decisión, porque
  `SendMessageUseCase` nunca llama a ninguno de los dos casos de uso (B4b,
  RF-020, PA-011);
- corrección explícita de recuerdos (`CorrectMemoryUseCase`) que consolida,
  bajo el mismo contrato transaccional de B4a, la creación de revisión
  inmutable que V4 ya implementaba: nueva revisión, puntero `current_revision`
  autoritativo, revisión anterior conservada como histórica, evento de origen
  obligatorio y atómico junto con la revisión (B4c, RF-022, PA-012);
  sustitución explícita entre decisiones (`SupersedeDecisionUseCase`, nuevo
  estado `DecisionStatus.SUPERSEDED` y `Decision.supersedes_decision_id`) que
  exige confirmación explícita, valida estados y misma identidad de asunto y
  proyecto, y aprueba la sustituta mientras marca la sustituida como
  histórica en una sola transacción; la decisión sustituida permanece
  consultable y enlazada con su sucesora, y la consulta ordinaria de
  decisiones vigentes (`list_current_decisions`) devuelve solo la sustituta
  (B4c, RF-023, PA-013);
  archivo de recuerdos y decisiones, eliminación de recuerdos con
  confirmación explícita y elección explícita sobre el mensaje fuente
  (`ArchiveMemoryUseCase`, `ArchiveDecisionUseCase`, `DeleteMemoryUseCase`,
  B4d, RF-024, RF-025, PA-015, PA-016, SP-06): archivar consolida, bajo el
  contrato transaccional de B4a, el archivo que
  `MemoryRepository.archive_memory`/`delete_memory` ya implementaban desde
  V4; `DecisionStatus.ARCHIVED` (nuevo, solo alcanzable desde APROBADA) hace
  lo mismo para decisiones; `list_archived_memories()`/
  `list_archived_decisions()` son las consultas explícitas de archivados,
  que las consultas ordinarias siguen excluyendo. `DeleteMemoryUseCase`
  exige `confirmed=True` y una elección explícita y tipada
  (`SourceMessageChoice.PRESERVE`/`REDACT`, sin valor por defecto) antes de
  abrir ninguna transacción; redacta el contenido estructurado de toda la
  historia de revisiones (conserva id, versión, origen y fecha como
  marcador mínimo) y, si se elige redactar, también el mensaje fuente
  (`ConversationRepository.redact_message`, nuevo), todo en la misma
  `UnitOfWork` que el evento de auditoría. La eliminación de decisiones
  queda deliberadamente fuera de este corte: ni PA-016 ni la enumeración de
  estados de decisión de Producto S6 la mencionan (a diferencia de
  "archivada");
  precedencia y detección de conflictos entre recuerdos y decisiones
  (`sirius.domain.precedence`, B4e, RF-026, PA-014, DR-011): identificación
  explícita y opcional de asunto y proyecto en el recuerdo
  (`Memory.subject_key`/`project_id`, el equivalente de
  `Decision.subject`/`project_id` a la granularidad de recuerdo, `None` en
  todo recuerdo que no la declare); una regla de dominio pura y determinista
  (`evaluate_subject_precedence`/`find_subject_conflicts`) que hace
  prevalecer una única decisión `APPROVED` vigente sobre recuerdos vigentes
  incompatibles del mismo asunto y proyecto, y que devuelve un conflicto
  explícito — con todos los elementos implicados, nunca un ganador elegido
  por fecha u orden de inserción — cuando no hay precedencia inequívoca;
  `DetectPrecedenceConflictsUseCase`, de solo lectura, expone la regla en la
  capa de aplicación sin que `SendMessageUseCase` la invoque nunca; y una
  conexión mínima en `ContextBuilder` que excluye del contexto únicamente el
  recuerdo ya superado en autoridad por una decisión vigente inequívoca del
  mismo asunto, sin resolver ni tocar un conflicto genuino entre recuerdos.

Pendiente dentro de V8:

- indexación y búsqueda pertinente;
- casos de uso e interfaz de decisiones, de archivo/eliminación y de
  resolución explícita de conflictos en las superficies existentes (B4f);
- la parte correspondiente de PA-E2E-01.

Defectos relacionados: D-03, D-04 y D-11.

## V5 — Contexto y proveedor simulado — COMPLETADA

- constructor de contexto;
- contrato LLM;
- proveedor simulado determinista;
- personalidad y reglas versionadas.

## V6 — OpenAI real — COMPLETADA AUTOMÁTICAMENTE; VALIDACIÓN REAL PENDIENTE

- adaptador Responses API;
- streaming, cancelación y errores;
- `store=false`;
- consumo y límites locales.

La implementación y las pruebas simuladas están completas. Permanece pendiente una prueba manual end-to-end con una clave y una cuenta reales de OpenAI.

## V7 — Seguridad, copias y recuperación — IMPLEMENTACIÓN AUTOMATIZADA TERMINADA

### Completado en V7A

- Windows Credential Manager;
- configuración segura de proveedor y clave;
- registros locales sin secretos;
- arranque seguro ante configuración inválida;
- manejo seguro de fallos al consultar credenciales;
- rechazo de límites no positivos antes de persistir la configuración.

### Completado dentro de V7 (copia cifrada)

- `BackupService.create_backup()`: instantánea consistente con `VACUUM INTO`,
  empaquetado con `manifest.json` (formato, versión de aplicación, esquema,
  fecha, hash), derivación de clave con Argon2id y cifrado con Fernet;
- guardado como un único archivo `.siriusbackup`, sin la clave API ni logs;
- límite de 100 MB antes de escribir el archivo final;
- autovalidación (descifrado, manifiesto e integridad de SQLite) antes de
  anunciar éxito;
- escritura atómica y nombres sin colisión;
- pruebas automáticas correspondientes.

### Completado dentro de V7 (validación de copia)

- `BackupService.validate_backup()`: lectura sin modificar los datos actuales;
- validación de contraseña, sobre cifrado, versión de formato, perfil Argon2id,
  estructura interna, manifiesto, versión de aplicación y esquema;
- comprobación de hash SHA-256 y `PRAGMA integrity_check` en directorio temporal;
- rechazo temprano de archivos o contenido descomprimido superiores a 100 MB;
- caso de uso de aplicación y pruebas unitarias/de integración.

### Completado dentro de V7 (restauración segura)

- `BackupService.restore_backup()`: exige confirmación explícita (`confirmed=True`)
  antes de tocar cualquier dato; reutiliza la validación completa ya existente
  (descifrado en directorio temporal, contraseña, formato, hashes, versión de
  aplicación e integridad de SQLite) antes de modificar nada;
- validación del esquema real: además de comparar el `schema_version` que
  declara el manifiesto, abre la base extraída en el directorio temporal, lee
  su `alembic_version` real y exige que coincida tanto con el manifiesto como
  con el esquema soportado por esta versión de Sirius
  (`get_supported_schema_version()`, derivado de las migraciones, sin
  necesitar una base de datos actual); esto cierra el hueco de un manifiesto
  internamente coherente (hash correcto) que declarase un esquema distinto al
  del contenido real empaquetado;
- crea una copia de seguridad cifrada y autovalidada de la base de datos actual
  antes del reemplazo;
- reemplazo atómico de la base de datos (mismo patrón de escritura a archivo
  temporal + `os.replace` que `create_backup`), sin dejar archivos parciales;
- validación posterior en modo solo lectura sobre la base ya reemplazada:
  hash SHA-256 contra el manifiesto, `alembic_version` contra el manifiesto y
  el esquema soportado, y `PRAGMA integrity_check`; cualquier fallo dispara el
  rollback automático. `_verify_database_matches_manifest()` es una función
  total: abre la base mediante una URI SQLite `mode=ro` (nunca crea el
  archivo si falta) y conserva además `PRAGMA query_only`; cualquier
  `OSError`, `sqlite3.Error` o fallo al determinar el esquema soportado se
  traduce en `False` en lugar de propagarse;
- el reemplazo atómico está blindado de extremo a extremo: cualquier
  excepción posterior a un `_write_atomically` ya exitoso —al eliminar
  sidecars, al abrir la base para validarla, al calcular el hash, al leer el
  esquema soportado o durante `integrity_check`— se trata igual que un fallo
  de validación posterior y dispara el rollback automático; nunca deja
  instalada una base nueva sin verificar;
- el rollback también se valida en modo solo lectura (mismas tres
  comprobaciones) antes de darse por bueno; si la copia de seguridad
  restaurada no queda íntegra, o si no existía una base previa y el archivo
  recién escrito no pudo eliminarse, se informa explícitamente de un fallo de
  rollback en lugar de reportar solo el fallo de restauración original;
- gestión segura de los sidecars `-wal`, `-shm` y `-journal`: se eliminan
  justo después de cada reemplazo atómico (tanto el de restauración como el
  de rollback), porque `os.replace` solo sustituye el archivo principal y un
  sidecar de la generación anterior podría hacer que SQLite intentara
  "recuperar" el archivo nuevo hacia un estado parcial obsoleto;
- la validación previa de una copia no confiable traduce cualquier fallo al
  leer el esquema real (por ejemplo, una base SQLite válida pero sin tabla
  `alembic_version`) en un `BackupValidationError` con mensaje seguro; nunca
  deja escapar un `sqlite3.OperationalError` crudo;
- `RestoreBackupUseCase` en `application`, siguiendo el mismo patrón que
  `CreateBackupUseCase` y `ValidateBackupUseCase`;
- pruebas unitarias y de integración correspondientes a cada punto anterior,
  incluyendo manifiestos internamente coherentes con esquema real
  incompatible, sidecars residuales presentes durante el reemplazo y el
  rollback, fallos inesperados (`PermissionError`/`OSError`) tras un
  reemplazo ya exitoso, una base sin tabla `alembic_version`, y la apertura
  de validación en modo solo lectura que nunca crea una base inexistente.

### Completado dentro de V7 (integración en interfaz)

- Sección "Copia de seguridad y restauración" añadida a la pestaña
  "Configuración" existente (no se creó ninguna pantalla nueva), usando
  exclusivamente `CreateBackupUseCase`, `ValidateBackupUseCase` y
  `RestoreBackupUseCase` inyectados desde `composition_root`; la presentación
  no importa el adaptador SQLite ni accede a la base de datos directamente;
- **Crear copia**: contraseña y repetición en campos ocultos, rechazo de
  contraseña vacía o distinta antes de llamar al caso de uso, ejecución en
  `QThreadPool` (`CreateBackupWorker`), controles desactivados con estado
  visible mientras trabaja, éxito con la ruta exacta y error con mensaje
  seguro; la contraseña no se persiste ni se registra, se elimina de
  inmediato de los campos tras leerla, y solo permanece transitoriamente en
  memoria mientras dura la operación de creación de la copia;
- **Validar copia**: selector de archivo limitado a `*.siriusbackup`,
  contraseña oculta, ejecución en `QThreadPool` (`ValidateBackupWorker`),
  resultado comprensible (fecha, versión de aplicación, esquema, tamaño) o
  mensaje de error seguro sin trazas ni excepciones internas;
- **Restaurar copia**: valida primero (reutilizando `ValidateBackupWorker`) y
  muestra el resumen; solo entonces pide una confirmación destructiva
  explícita (seam `confirm_restore`, con `QMessageBox.question` bloqueado en
  pruebas) que indica que los datos actuales serán sustituidos, que se
  creará una copia de seguridad previa, que una copia antigua puede
  reintroducir información eliminada, y que la clave de API no forma parte
  de la copia ni se restaura; solo tras confirmar se llama a
  `RestoreBackupUseCase.restore_backup(..., confirmed=True)` exactamente una
  vez, en `QThreadPool` (`RestoreBackupWorker`); tras el éxito se muestra la
  ruta de la copia de seguridad previa;
- **Ciclo de vida real de SQLite/SQLAlchemy inspeccionado y verificado
  empíricamente**: cada repositorio (`conversation`, `identity`, `project`,
  `memory`, `llm_usage`) mantiene un `Engine` con `QueuePool`, que conserva
  conexiones agrupadas abiertas mientras dure la ventana. Se comprobó
  directamente que `os.replace()` falla con `PermissionError` en Windows si
  una conexión sqlite3 al mismo archivo sigue abierta. Cada repositorio
  añadió un método `close()` mínimo (`Engine.dispose()`); `composition_root`
  expone `close_database_connections()` (no es un caso de uso, es el
  mecanismo mínimo de ciclo de vida) y `MainWindow` lo invoca justo antes de
  `RestoreBackupUseCase`, nunca después: así el reemplazo atómico no queda
  bloqueado por las conexiones agrupadas de la propia ventana. Verificado de
  extremo a extremo con los casos de uso reales;
- tras una restauración exitosa, Sirius se cierra de forma controlada
  (mismo patrón que la cancelación diferida ya existente para el envío de
  mensajes) y pide al usuario que lo abra de nuevo; no se introdujo ningún
  proceso auxiliar ni relanzamiento automático;
- se evitan operaciones simultáneas: copia/validación/restauración se
  excluyen mutuamente entre sí y con el envío de mensajes (en ambos
  sentidos), reutilizando el patrón de deshabilitar/rehabilitar controles y
  diferir el cierre ya usado para el envío de mensajes;
- corregido un fallo real de PySide6/`QThreadPool` encontrado durante las
  pruebas: sin una referencia fuerte en Python al `QRunnable`, un worker que
  termina muy rápido puede recolectarse por el recolector de basura antes de
  que su señal en cola entre hilos se entregue, perdiendo el resultado en
  silencio; `MainWindow` retiene ahora una referencia tanto al worker de
  conversación (`SendMessageWorker`, en `_active_send_worker`) como al worker
  de copia en curso (`_active_backup_worker`) hasta que su señal se procesa;
  ambas referencias se mantienen separadas y cada una se limpia únicamente
  tras procesar el `finished`/`crashed` o `succeeded`/`failed` del worker que
  le corresponde;
- pruebas de GUI (`pytest-qt`) para cada escenario requerido: contraseña
  vacía/distinta, controles desactivados durante la operación, éxito y error
  de creación, validación válida e inválida, restauración cancelada en la
  confirmación, restauración confirmada que llama exactamente una vez con
  `confirmed=True` y en el orden correcto (cierre de conexiones antes que la
  restauración), ningún fallo (incluida una excepción inesperada) modifica
  la GUI fuera del hilo principal, composición que entrega los casos de uso
  correctos, y flujo real de extremo a extremo (crear → validar → restaurar)
  que cierra la ventana tras el éxito.

### Pendiente dentro del alcance aprobado de V7

- prueba manual del Credential Manager en Windows real con un valor señuelo.

## Correspondencia con las verticales de la Arquitectura aprobada

La numeración de este plan es una descomposición operativa posterior. No sustituye ni modifica la Arquitectura Técnica aprobada.

Correspondencia principal:

| Arquitectura aprobada | Plan operativo actual |
|---|---|
| V0 · Bootstrap | V0 y parte de V1 |
| V1 · Conversación falsa | V5 y V6A |
| V2 · Persistencia | V2 |
| V3 · Proveedor real | V6B y V7A |
| V4 · Proyecto | V3 y correcciones de V8 |
| V5 · Memoria | V4 y correcciones de V8 |
| V6 · Portabilidad | V7 y exportación pendiente en V8 |
| V7 · Cierre | V8 |

La correspondencia describe contenido, no equivalencia de estado. Una etiqueta `COMPLETADA` del plan no demuestra la aceptación de la vertical arquitectónica completa.

## V8 — Corrección, aceptación y cierre de Sirius 0.1 — INICIADA PARCIALMENTE

V8 no constituye una nueva versión de producto. Ejecuta las correcciones, pruebas, empaquetado y aceptación ya previstos para Sirius 0.1.

### V8.1 — Corrección documental y automatizada — ACTIVA

Permitido:

- reconciliar documentación;
- construir y mantener la matriz requisito–defecto–prueba;
- corregir D-01 a D-11 y A-01 a A-04 sin ampliar el alcance;
- ejecutar pruebas con FakeLLM;
- completar pruebas automáticas PA/SP;
- medir rendimiento local;
- preparar empaquetado;
- recopilar evidencia automática.

Prohibido en esta subetapa:

- usar u obtener una clave API real;
- declarar pruebas manuales como superadas;
- iniciar PA-E2E-01 formal;
- cambiar Producto, Arquitectura o ATD;
- introducir capacidades fuera de Sirius 0.1.

#### Correcciones ya fusionadas dentro de V8.1

- Validación de credencial antes de guardarla (RF-002): `ValidateAndSaveApiKeyUseCase`
  valida la clave contra el proveedor (`OpenAICredentialValidator`) antes de persistirla,
  e integra el flujo en la interfaz mediante `ValidatedMainWindow` (subclase de
  `MainWindow` que sustituye a `_save_api_key`, ejecuta la validación en `QThreadPool`
  vía `CredentialValidationWorker` y nunca accede al almacén de secretos ni al proveedor
  directamente desde la presentación). Cubierto con pruebas unitarias y de GUI
  (`tests/unit/test_validate_and_save_api_key.py`, `tests/unit/test_openai_credential_validator.py`,
  `tests/gui/test_validated_main_window.py`), siempre contra un validador simulado.
  RF-002 está implementado y cubierto automáticamente. D-01 permanece abierto hasta
  demostrar el resto de sus condiciones: falta RF-001 (pantalla de primera
  configuración con política de datos) y D-10 (ruta de datos y activación clara)
  permanece abierto sin ningún cambio; PA-001 y PA-002 formales exigen una
  credencial real y no se declaran superadas — siguen bloqueadas hasta V8.3.
- Corrección de una fuga de conexión SQLite en el helper de test de restauración
  (`tests/gui/test_backup_recovery_ui.py::_bootstrapped_database`), que dejaba
  repositorios temporales sin cerrar y causaba un fallo intermitente y reproducible
  del reemplazo atómico de archivo en Windows (`PermissionError`) durante la prueba
  de extremo a extremo de restauración. Es una corrección de higiene de prueba, no
  un cambio de comportamiento de producto: el helper ahora cierra cada repositorio
  en un `finally`, igual que `initialize_persistence()` ya hacía. Incluye una prueba
  de regresión determinista.
- Primera configuración básica (B2a, RF-001): `OnboardingWindow` (nueva ventana de
  presentación, independiente de `MainWindow`) se muestra únicamente cuando
  `ApiKeySettingsUseCase.has_key()` es falso; explica en un único lugar centralizado
  (`onboarding_window.DATA_POLICY_TEXT`) qué se conserva localmente y qué se envía
  al proveedor, muestra proveedor y modelo predeterminados (reutilizados de
  `LLMProviderKind`/`resolve_openai_provider_settings`, sin selector nuevo) y
  solicita únicamente la clave, reutilizando `ValidateAndSaveApiKeyUseCase` y
  `CredentialValidationWorker` de RF-002 sin duplicar el flujo. Tras una validación
  correcta, activa el proveedor real en la misma ejecución mediante la nueva
  `ConversationDependencies.activate_configured_llm_provider` (composition root:
  fija `llm_provider="openai"` en la configuración no sensible existente y
  reconstruye el proveedor con `SendMessageUseCase.set_llm_provider`) y
  `sirius.main` sustituye la ventana de onboarding por `ValidatedMainWindow` sin
  reiniciar Sirius. Cubierto con pruebas unitarias y de GUI
  (`tests/gui/test_onboarding_window.py`, `tests/gui/test_app_bootstrap.py`,
  nuevos casos en `tests/unit/test_composition_root_credential_validation.py` y
  `tests/integration/test_send_message.py`), siempre contra un validador simulado
  y sin red real. RF-001 está implementado y cubierto automáticamente. D-01
  permanece abierto hasta las pruebas formales con proveedor real (PA-001/PA-002);
  D-10 sigue parcialmente abierto: cubre política de datos y valores
  predeterminados, pero no la edición de la ruta local (B2b) ni la comprobación
  real de activación en Windows (Credential Manager con valor señuelo, pendiente
  de validación manual). El saludo con identidad propia y la propuesta de
  proyecto inicial pertenecen a B3 (D-02) y no son una condición de D-10.
- Selección y persistencia de la ruta local de datos (B2b, parte de D-10):
  la ubicación de datos se resuelve y valida antes de inicializar SQLite,
  configurar el logging dependiente de la ruta o construir la composición.
  Un nuevo componente aislado, `BootstrapLocationStore`
  (`sirius.infrastructure.bootstrap_location_store`), guarda un puntero JSON
  mínimo (`{"version": 1, "data_dir": "<ruta absoluta>"}`) en el directorio de
  configuración estable de Windows (`SiriusPaths.config_dir`, ahora
  independiente de `data_dir`: ver `resolve_paths(data_dir=...)`), separado de
  `settings.json`, SQLite y el almacén de secretos; la escritura es atómica
  (archivo temporal + `os.replace`). `WindowsDataPathValidator`
  (`sirius.infrastructure.data_path_validator`) valida cada carpeta candidata
  con una prueba de escritura real (nunca solo `os.access()`), caracteres y
  nombres reservados de Windows, y detecta una instalación Sirius existente y
  una carpeta bajo OneDrive. `DataLocationUseCase`
  (`sirius.application.data_location`) orquesta resolución, validación y
  persistencia sin conocer SQLite, SQLAlchemy, migraciones ni platformdirs
  directamente. `DataLocationWindow` (nueva ventana de presentación,
  independiente de `OnboardingWindow`) se muestra únicamente cuando hace
  falta una primera elección (instalación nueva sin instalación previa en la
  ruta predeterminada) o cuando el archivo externo de ubicación está dañado;
  ofrece la ruta predeterminada ya seleccionada y una opción avanzada para
  elegir otra carpeta. Una instalación existente en la ruta predeterminada
  sin archivo de ubicación se conserva silenciosamente (sin pantalla de
  migración); una ruta personalizada con datos existentes se bloquea sin
  adoptarla, moverla ni sobrescribirla; un archivo de ubicación corrupto
  nunca abre una base predeterminada en silencio y exige una elección nueva y
  explícita antes de sobrescribirlo. `sirius.main` resuelve la ubicación
  antes de cualquier paso dependiente de datos y solo entonces continúa con
  el onboarding de credencial de B2a, en la misma ejecución. Cubierto con
  pruebas unitarias y de GUI (`tests/unit/test_paths.py`,
  `tests/unit/test_data_path_validator.py`,
  `tests/unit/test_bootstrap_location_store.py`,
  `tests/unit/test_data_location_use_case.py`,
  `tests/gui/test_data_location_window.py`,
  `tests/gui/test_app_bootstrap.py`), siempre con dobles deterministas, sin
  datos reales y sin red. La migración o adopción de datos existentes fuera
  de la ruta predeterminada queda explícitamente fuera de este corte. D-10
  sigue sin cerrarse por completo: falta la comprobación real de activación
  en Windows (Credential Manager con valor señuelo, pendiente de validación
  manual) y las validaciones manuales de rutas reales de Windows.
- Saludo inicial y creación utilizable del primer proyecto (B3a, parte de
  D-02): tras resolver la ruta y configurar la clave, Sirius distingue el
  placeholder vacío que `get_or_create_active_project()` siembra desde V3
  (`sirius.domain.project.is_configured()`) de un proyecto realmente
  configurado, y `InitialProjectUseCase`
  (`sirius.application.initial_project`) crea el primero completando ese
  placeholder transaccionalmente (sin insertar una segunda fila) solo con
  nombre y objetivo, asignando un estado y un siguiente paso iniciales
  mínimos y centralizados (`INITIAL_PROJECT_STATE`/`INITIAL_PROJECT_NEXT_STEP`).
  Rechaza un segundo proyecto activo antes de escribir nada, con un error
  tipado y sin tocar el proyecto existente. `InitialProjectWindow` (nueva
  ventana de presentación) muestra un saludo determinista que reutiliza
  `sirius.domain.identity.INITIAL_IDENTITY_NAME` (nunca generado por el
  proveedor) y solicita únicamente nombre y objetivo; `sirius.main` la
  muestra solo cuando ya hay clave configurada pero ningún proyecto
  configurado todavía, y abre `ValidatedMainWindow` en la misma ejecución al
  crearlo. El proyecto configurado llega a `ContextBuilder` mediante el
  mecanismo ya existente, sin cambios en `sirius.application.context`, porque
  la conversación nunca se abre antes de que el proyecto quede configurado.
  Cubierto con pruebas unitarias, de integración y de GUI
  (`tests/unit/test_project_domain.py`,
  `tests/unit/test_initial_project_use_case.py`,
  `tests/integration/test_initial_project_persistence.py`,
  `tests/gui/test_initial_project_window.py`, nuevos casos en
  `tests/gui/test_app_bootstrap.py`), siempre con dobles deterministas o
  SQLite temporal, sin datos reales, sin clave real y sin red. RF-014 y
  RF-015 quedan implementados y cubiertos automáticamente; RF-016 solo en su
  parte inicial (estado y siguiente paso al crear). D-02 queda parcialmente
  corregido: quedan pendientes de un corte posterior de B3 los bloqueos,
  las decisiones relacionadas, completar/archivar conservando historial y el
  resumen observable al retomar. PA-006 y PA-007 quedan preparadas/cubiertas
  automáticamente, sin declararse formalmente superadas.
- Continuidad observable del proyecto activo (B3b, parte de D-02): texto
  aprobado verificado antes de implementar (RF-016 "Conservar objetivo,
  estado breve, decisiones, bloqueos y siguiente paso"; RF-017 "Recuperar el
  proyecto al iniciar y resumirlo brevemente"). `Project.blockers` (texto
  libre, cero o varias líneas, sin tabla ni entidad `Blocker` independiente)
  se añade mediante la migración Alembic no destructiva `66951344e4b9`
  (`server_default=''`, probada actualizando desde el head anterior con
  Alembic real y conservando todo proyecto existente).
  `ProjectContinuityUseCase` (`sirius.application.project_continuity`)
  consulta y actualiza conjuntamente estado, bloqueos y siguiente paso en
  una sola escritura del repositorio, sin conocer SQLAlchemy ni SQLite;
  rechaza la ausencia de proyecto o el placeholder de arranque
  (`ProjectNotConfiguredError`), un estado o siguiente paso vacío
  (`InvalidProjectContinuityDataError`, bloqueos vacíos sí se permiten), y
  traduce cualquier fallo del repositorio a `ProjectContinuityError` sin
  exponer su detalle interno. `ProjectContinuityWidget` (nuevo widget de
  presentación, no una pestaña ni ventana nueva) se inserta en la pestaña
  "Conversación" existente, encima del historial: resumen determinista y
  local (nunca generado por el proveedor, nunca persistido como mensaje) con
  el siguiente paso destacado ("Ahora toca: …") y una acción "Actualizar
  proyecto" que edita estado/bloqueos/siguiente paso (nombre y objetivo
  quedan de solo lectura en este corte) con guardar/cancelar, doble envío
  impedido y errores seguros sin trazas. `MainWindow`/`ValidatedMainWindow`
  reciben el nuevo caso de uso explícitamente, reutilizando el
  `ProjectRepository` ya construido en `composition_root` (sin repositorio
  adicional, sin reiniciar SQLite). `render_instructions()` añade
  `Nombre:`/`Bloqueos:` a la sección `# Proyecto activo` ya existente
  ("Bloqueos: Ninguno registrado." cuando no hay bloqueos), sin decisiones
  ni recuerdos ficticios y sin cambiar la política de contexto de B6.
  Cubierto con pruebas unitarias, de integración (incluida Alembic real) y
  de GUI (`tests/unit/test_project_domain.py` nuevos casos,
  `tests/unit/test_project_continuity_use_case.py`,
  `tests/unit/test_render_instructions.py`,
  `tests/unit/test_composition_root_project_continuity.py`,
  `tests/integration/test_sqlite_project_repository.py` nuevos casos,
  `tests/integration/test_migrations.py` nuevos casos,
  `tests/integration/test_send_message.py` nuevo caso,
  `tests/gui/test_project_continuity_widget.py`,
  `tests/gui/test_main_window.py` y `tests/gui/test_app_bootstrap.py` nuevos
  casos), sin datos reales, sin clave real y sin red. RF-016 queda cubierto
  salvo la parte de "decisiones" (pertenece a B4); RF-017 queda implementado
  y cubierto automáticamente. D-02 sigue parcialmente corregido: quedan
  pendientes decisiones relacionadas, completar/archivar conservando
  historial y habilitar un proyecto posterior. PA-008 y PA-009 no se
  declaran superadas: PA-008 exige además una decisión registrada (B4) y
  PA-009 una recomendación evaluada del proveedor real.

### V8.2 — Windows sin clave — BLOQUEADA HASTA INTEGRACIÓN AUTOMÁTICA VERDE

Incluye:

- Credential Manager con valor señuelo;
- ejecutable Nuitka;
- rutas y funcionamiento sin administrador;
- escalado, teclado y foco;
- cierre forzado;
- restauración empaquetada;
- rendimiento local;
- inspección de archivos, logs, copias y exportaciones;
- monitorización de tráfico sin proveedor real.

### V8.3 — Ventana con proveedor real — BLOQUEADA

No puede comenzar hasta que:

- D-01, D-02, D-03, D-04, D-05, D-08, D-11 y A-01 estén cerrados;
- D-06, D-07, D-09 y D-10 estén corregidos o exista una resolución admisible según el Plan de Pruebas;
- A-02 y A-03 hayan sido verificados;
- la suite automática completa esté verde;
- exista un ejecutable reproducible;
- Credential Manager haya sido comprobado con un valor señuelo;
- no existan defectos BLOQUEANTES o ALTOS conocidos;
- el usuario autorice expresamente obtener y utilizar una clave temporal.

### V8.4 — PA-E2E-01 y cierre — BLOQUEADA

Incluye:

- proyecto pequeño real durante varias sesiones;
- PS-01 a PS-07;
- PA-E2E-01;
- regresión completa;
- consolidación de evidencia;
- reconciliación documental final;
- aprobación explícita del usuario.

No se crea una fase canónica nueva denominada `Preparación V8`.

## Reglas para continuar

- No repetir V0-V7A salvo para corregir un defecto concreto.
- No rediseñar la arquitectura modular ya aprobada e implementada parcialmente.
- No convertir ideas exploratorias en requisitos o cambios de alcance.
- Trabajar en ramas breves y fusionar mediante pull request con las comprobaciones en verde.
- Detenerse ante decisiones de producto, contradicciones arquitectónicas, operaciones peligrosas, ambigüedades materiales o pruebas que requieran el Windows real del usuario.
