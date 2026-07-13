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
- V6B: `OpenAIResponsesProvider` real (Responses API, streaming, `store=false`, sin herramientas), con eventos tipados de aplicación (`LLMTextDelta`/`LLMCompleted`/`LLMCancelled`/`LLMError`, con texto parcial en cancelación/fallo) y `FakeLLMProvider` mantenido para pruebas y desarrollo.
- V6B: selección `fake`/`openai` provisional por variable de entorno (`SIRIUS_LLM_PROVIDER`, valor no reconocido levanta `LLMProviderConfigurationError` en vez de caer a `fake`); clave leída solo de `OPENAI_API_KEY` y nunca persistida; documentado como provisional hasta V7.
- V6B: único sistema de reintentos activo — el adaptador tiene su propia política probada (máx. 2, solo en la conexión inicial) y el cliente del SDK se construye con `max_retries=0` para que ambas políticas nunca se multipliquen.
- V6B: `MessageStatus` (`COMPLETED`/`CANCELLED`/`FAILED`) en el dominio; un mensaje de Sirius cancelado o fallido conserva su texto parcial con el estado correspondiente, queda excluido del contexto de futuros envíos y se muestra en el historial marcado como tal, sin tratarse nunca como respuesta completa.
- V6B: idempotencia real por `operation_id` — `ConversationRepository.append_message` es idempotente por `(conversación, operation_id, rol)`, con restricción única en base de datos como respaldo; reintentar una operación tras un fallo de persistencia nunca duplica el mensaje de usuario.
- V6B: presupuesto mensual (DR-018) persistido en SQLite (`llm_usage`, una fila por mes UTC) para que sobreviva a reinicios de la aplicación; `BudgetTracker` conserva un modo en memoria cuando no se inyecta el repositorio.
- V6B: migración (no publicada) añade `messages.operation_id`, `identity_version`, `status` y la restricción única de idempotencia; migración nueva independiente crea `llm_usage`. Ninguna migración publicada de V2-V5 se modifica.
- V6B: interfaz con streaming progresivo y botón "Cancelar"; cancelación y cierre de ventana durante un streaming no bloquean el hilo gráfico; los mensajes cancelados/fallidos permanecen visibles en el historial.
- V7A: `KeyringSecretStore` real sobre Windows Credential Manager detrás del puerto `SecretStore` (que añade `is_secure_backend()`); nunca cae a texto plano si el backend seguro no está disponible; `FakeSecretStore` conservado para pruebas.
- V7A: proveedor, modelo, límite de tokens y presupuesto mensual pasan a ser configuración no sensible en `settings.json`, editable desde la pestaña "Configuración"; la clave de OpenAI se resuelve desde el `SecretStore` (flujo normal), con `OPENAI_API_KEY` de entorno como mecanismo explícito de desarrollo únicamente.
- V7A: la aplicación arranca siempre, incluso con "openai" mal configurado (sin clave, límites inválidos); el error seguro (`UnconfiguredLLMProvider`, `LLMErrorKind.CONFIGURATION`) solo aparece al intentar enviar un mensaje.
- V7A: registro local rotatorio (`logs/application.log`, 5 archivos de 5 MB) con redacción defensiva; registra arranque, proveedor, operaciones y errores clasificados, nunca contenido de mensajes ni la clave.
- V7A: pestaña "Configuración" con campo enmascarado para la clave, acciones de guardar/eliminar, y estado (configurada/no configurada) sin mostrar nunca el valor.

## Verificación de V6B (proveedor OpenAI real)

Todo lo descrito en V6B está verificado mediante pruebas automáticas (`scripts/check.ps1`: Ruff, mypy estricto y pytest) usando exclusivamente clientes y streams de OpenAI completamente simulados — `OpenAIResponsesProvider` nunca se ha ejecutado contra la API real. **Pendiente**: prueba manual end-to-end contra la API real de OpenAI, bloqueada porque el usuario todavía no dispone de una clave `OPENAI_API_KEY`. Esta prueba manual debe realizarse antes de considerar V6B validado en condiciones reales de red, límites de la cuenta y respuestas reales del modelo.

## Verificación de V7A (secretos y diagnóstico)

Todo lo descrito en V7A está verificado mediante pruebas automáticas usando `keyring` completamente simulado (todas sus funciones monkeypatcheadas): ningún test lee, escribe ni elimina nada en el Credential Manager real de Windows. **Pendiente**: prueba manual de humo en un equipo Windows real, guardando y eliminando una clave desde la interfaz y confirmando que aparece en el Credential Manager del sistema (`certmgr`/"Administrador de credenciales" de Windows) con el nombre de servicio `Sirius`. Pendiente también: el proveedor/clave guardados desde la pestaña Configuración solo se aplican al próximo arranque de Sirius (no hay recarga en caliente de la sesión en curso); esto no estaba en el alcance obligatorio de V7A y queda como decisión abierta.

## Primera acción en el equipo Windows

Ejecutar `scripts/bootstrap.ps1`. Esa operación instalará Python 3.14.6 mediante uv, resolverá las dependencias y generará `uv.lock`. Después debe ejecutarse `scripts/check.ps1` y añadirse `uv.lock` al primer commit.

## Verificaciones pendientes del equipo objetivo

Este paquete no afirma haber ejecutado PySide6, mypy, Ruff ni la suite completa con Python 3.14.6, porque esas dependencias no estaban disponibles en el entorno de generación. La puerta V0 solo quedará cerrada cuando `scripts/check.ps1` pase en Windows 11.
