# Plan de implementación por verticales

Cada vertical debe producir una parte usable, probada y documentada antes de iniciar la siguiente.

## Estado global

- V0 a V6B: completadas.
- V7A: completada y endurecida posteriormente.
- V7: en curso; permanecen las funciones de copia cifrada, validación y restauración segura.
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
- pruebas automáticas correspondientes.

### Pendiente dentro del alcance aprobado de V7

- `validate_backup()` y `restore_backup()` (restauración segura);
- integración de la copia cifrada en la interfaz;
- pruebas automáticas correspondientes a la restauración;
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
