# Plan de implementación por verticales

Cada vertical debe producir una parte usable, probada y documentada antes de iniciar la siguiente.

## Estado global

- V0 a V6B: completadas.
- V7A: completada y endurecida posteriormente.
- V7: en curso; la restauración segura ya está implementada; permanece la integración en interfaz.
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

### Pendiente dentro del alcance aprobado de V7

- integración de copia, validación y restauración en la interfaz;
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
