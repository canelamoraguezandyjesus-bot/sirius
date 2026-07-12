# Plan de implementación por verticales

Cada vertical debe producir una parte usable, probada y documentada antes de iniciar la siguiente.

## V0 — Repositorio y humo

- entorno reproducible;
- ventana mínima ejecutable;
- Ruff, mypy, pytest y CI;
- documentación canónica accesible.

## V1 — Aplicación local y configuración básica

- arranque real;
- rutas locales de datos;
- configuración no sensible;
- almacén de secretos abstracto y simulado.

## V2 — Historial persistente

- SQLite y migración inicial;
- conversación y mensajes;
- persistencia transaccional;
- recuperación entre sesiones.

## V3 — Proyecto activo

- creación del único proyecto activo;
- objetivo, estado y siguiente paso;
- recuperación al iniciar.

## V4 — Memoria manual y versionada

- conocimiento estructurado;
- origen obligatorio;
- corrección, sustitución, archivo y eliminación;
- consulta trazable.

## V5 — Contexto y proveedor simulado

- constructor de contexto;
- contrato LLM;
- proveedor simulado determinista;
- personalidad y reglas versionadas.

## V6 — OpenAI real

- adaptador Responses API;
- streaming, cancelación y errores;
- `store=false`;
- consumo y límites locales.

## V7 — Seguridad, copias y recuperación

- Windows Credential Manager;
- copia cifrada;
- validación y restauración segura;
- registros locales sin secretos.

## V8 — Aceptación 0.1

- prueba completa durante varias sesiones;
- proyecto pequeño real de principio a fin;
- corrección de defectos;
- paquete ejecutable de prueba.
