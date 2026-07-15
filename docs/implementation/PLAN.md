# Plan de implementación por verticales

Cada vertical debe producir una parte usable, probada y documentada antes de iniciar la siguiente.

## Estado global

- V0 a V6B: completadas.
- V7A: completada y endurecida posteriormente.
- V7: en curso; la restauración segura y su integración en interfaz ya están implementadas; permanece la prueba manual del Credential Manager en Windows real.
- V8: pendiente.

Las etiquetas de estado de este archivo describen la implementación. No modifican el producto, los requisitos ni la arquitectura aprobados.

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

## V3 — Proyecto activo — COMPLETADA

- creación del único proyecto activo;
- objetivo, estado y siguiente paso;
- recuperación al iniciar.

## V4 — Memoria manual y versionada — COMPLETADA

- conocimiento estructurado;
- origen obligatorio;
- corrección, sustitución, archivo y eliminación;
- consulta trazable.

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

## V7 — Seguridad, copias y recuperación — EN CURSO

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

- prueba manual del Credential Manager en Windows real.

No se asigna todavía un nombre canónico a la siguiente subdivisión de V7.

## V8 — Aceptación 0.1 — PENDIENTE

- prueba completa durante varias sesiones;
- proyecto pequeño real de principio a fin;
- corrección de defectos;
- paquete ejecutable de prueba.

## Reglas para continuar

- No repetir V0-V7A salvo para corregir un defecto concreto.
- No rediseñar la arquitectura modular ya aprobada e implementada parcialmente.
- No convertir ideas exploratorias en requisitos o cambios de alcance.
- Trabajar en ramas breves y fusionar mediante pull request con las comprobaciones en verde.
- Detenerse ante decisiones de producto, contradicciones arquitectónicas, operaciones peligrosas, ambigüedades materiales o pruebas que requieran el Windows real del usuario.
