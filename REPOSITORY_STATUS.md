# Estado de preparación del repositorio

## Completado

- Estructura modular y paquetes base.
- Esqueleto ejecutable de ventana PySide6.
- Contrato neutral de proveedor LLM y proveedor simulado.
- Configuración central en `pyproject.toml`.
- Ruff, mypy, pytest y pytest-qt.
- Flujo de calidad para GitHub Actions en Windows.
- Scripts PowerShell para preparar, ejecutar, formatear y comprobar.
- Reglas para Claude Code y otros agentes.
- Plan de implementación por verticales.
- Copia de las ocho fuentes documentales aprobadas.
- Verificación local de sintaxis Python, TOML, estructura y presencia documental.
- V1: rutas locales tipadas (configuración, datos, registros, copias de seguridad, exportaciones) con creación automática al arrancar.
- V1: configuración no sensible persistida en el directorio de configuración correcto de Windows.
- V1: contrato `SecretStore` y almacén de secretos simulado en memoria (sin Windows Credential Manager todavía).
- V2: modelos de dominio `Conversation`/`Message` y puerto `ConversationRepository` independiente de SQLAlchemy.
- V2: adaptador SQLite sobre la ruta de datos de `SiriusPaths`, con Alembic activo y la primera migración real (`create conversations and messages`).
- V2: conversación principal única, recuperación de mensajes en orden estable entre sesiones y operaciones transaccionales (sin datos parciales ante fallo).
- V3: modelo de dominio `Project` y puerto `ProjectRepository` independiente de SQLAlchemy, con actualización total o parcial.
- V3: adaptador SQLite y nueva migración (`create projects`) que no modifica la migración publicada de V2.
- V3: proyecto activo único garantizado por índice único parcial, con valores iniciales neutros; bootstrap de persistencia lo crea de forma idempotente al arrancar.
- V4: modelo de dominio `Memory`/`MemoryRevision` con reglas de origen obligatorio y transición de estados en dominio, independiente de SQLAlchemy.
- V4: puerto `MemoryRepository` y adaptador SQLite, con nueva migración (`create memories and memory revisions`) que no modifica las de V2 ni V3.
- V4: corrección versionada sin sobrescritura, archivo que conserva contenido, eliminación que redacta contenido conservando un marcador trazable; el arranque solo aplica la migración, sin crear memorias por defecto.
- V5: modelo de dominio `Identity`/`IdentityVersion` versionado (una sola versión vigente, historial estable) con identidad inicial tomada literalmente de la documentación canónica.
- V5: puerto `IdentityRepository` y adaptador SQLite, con nueva migración (`create identities and identity versions`) que no modifica las de V2, V3 ni V4; bootstrap crea la identidad canónica de forma idempotente.
- V5: `ContextBuilder` (constructor de contexto determinista con 5 secciones en orden fijo, solo a partir de puertos) y `SendMessageUseCase` (invoca `FakeLLMProvider` y persiste ambos mensajes con estrategia explícita ante fallos); sin interfaz de conversación todavía.
- V6A: conversación visual y funcional en la ventana principal (historial, envío, estado, error) usando exclusivamente `FakeLLMProvider`; configuración existente conservada en su propia pestaña.
- V6A: `GetConversationHistoryUseCase` (lectura pura) y `composition_root.py` (fuera de `presentation`) que inyecta repositorios y casos de uso en `MainWindow`.
- V6A: envío en `QThreadPool` sin bloquear el hilo gráfico, doble envío bloqueado, entrada vacía rechazada, cierre de ventana seguro durante un envío en curso; sin migraciones nuevas ni proveedor real.

## Primera acción en el equipo Windows

Ejecutar `scripts/bootstrap.ps1`. Esa operación instalará Python 3.14.6 mediante uv, resolverá las dependencias y generará `uv.lock`. Después debe ejecutarse `scripts/check.ps1` y añadirse `uv.lock` al primer commit.

## Verificaciones pendientes del equipo objetivo

Este paquete no afirma haber ejecutado PySide6, mypy, Ruff ni la suite completa con Python 3.14.6, porque esas dependencias no estaban disponibles en el entorno de generación. La puerta V0 solo quedará cerrada cuando `scripts/check.ps1` pase en Windows 11.
