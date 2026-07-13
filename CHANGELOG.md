# Registro de cambios

## No publicado

### Preparado

- Estructura inicial del repositorio.
- Herramientas de calidad y pruebas.
- Esqueleto mínimo ejecutable de PySide6.
- Documentación canónica y reglas para agentes.

### V1 — Aplicación local y configuración básica

- Rutas locales tipadas (configuración, datos, registros, copias de seguridad, exportaciones) resueltas con `platformdirs` y creadas automáticamente al arrancar.
- Configuración no sensible movida al directorio de configuración correcto de Windows en lugar de una ruta relativa.
- Contrato `SecretStore` para almacenamiento de secretos y una implementación simulada en memoria para pruebas.

### V2 — Historial persistente

- Modelos de dominio `Conversation` y `Message` (identidad, rol, contenido, fecha de creación y secuencia estable).
- Puerto `ConversationRepository`, independiente de SQLAlchemy.
- Adaptador SQLite (`SqliteConversationRepository`) sobre la ruta de datos de `SiriusPaths`, sin rutas relativas.
- Alembic activado, con la primera migración real (`create conversations and messages`).
- Conversación principal única, recuperable entre sesiones, con mensajes en orden estable y operaciones transaccionales (sin datos parciales ante fallo).

### V3 — Proyecto activo

- Modelo de dominio `Project` (id, nombre, objetivo, estado actual, siguiente paso, fecha de creación y de actualización).
- Puerto `ProjectRepository`, independiente de SQLAlchemy, con actualización total o parcial.
- Adaptador SQLite (`SqliteProjectRepository`); nueva migración (`create projects`) que no modifica la de V2.
- Proyecto activo único garantizado por índice único parcial en la base de datos, sin impedir futuros proyectos archivados.
- Proyecto inicial con valores neutros (vacíos), sin datos personales ni decisiones de producto inventadas.
- Bootstrap de persistencia extendido: crea el proyecto activo al arrancar, de forma idempotente.

### V4 — Memoria manual, versionada y trazable

- Modelo de dominio `Memory`/`MemoryRevision` y estados `CURRENT`/`ARCHIVED`/`DELETED`, con reglas de origen obligatorio y transición de estados en dominio (`sirius.domain.memory`), sin dependencia de SQLAlchemy.
- Puerto `MemoryRepository`: crear, consultar vigentes, consultar historial completo, corregir (nueva revisión sin sobrescribir), archivar y eliminar.
- Adaptador SQLite (`SqliteMemoryRepository`); nueva migración (`create memories and memory revisions`) que no modifica las de V2 ni V3.
- Corrección versionada: cada corrección añade una revisión nueva y desactiva la anterior sin sobrescribirla; solo una revisión vigente por memoria (puntero único estructural, no un flag booleano).
- Archivar conserva el contenido y retira la memoria de las consultas de vigentes; eliminar redacta el contenido estructurado de toda la historia de revisiones y dispara el estado `DELETED`, conservando un marcador mínimo trazable (regla DR-012).
- No se crea ninguna memoria por defecto: el arranque solo aplica la migración.

### V5 — Identidad versionada y constructor de contexto

- Modelo de dominio `Identity`/`IdentityVersion`, versionado con el mismo patrón de V4 (`is_current` + índice único parcial: como máximo una versión vigente, historial en orden estable).
- Identidad inicial tomada literalmente del Manual de Visión e Identidad v1.2 y de la Definición de Producto 0.1 (propósito, rasgos nucleares, honestidad intelectual, autoridad del usuario); ningún rasgo o regla inventados.
- Puerto `IdentityRepository` y adaptador SQLite (`SqliteIdentityRepository`); nueva migración (`create identities and identity versions`) que no modifica las de V2, V3 ni V4.
- Bootstrap extendido: crea la identidad canónica al arrancar, de forma idempotente.
- `application.context.ContextBuilder`: constructor de contexto determinista, con 5 secciones en orden fijo (identidad, proyecto activo, memorias vigentes, historial reciente, mensaje actual), construido solo a partir de puertos; excluye memorias archivadas/eliminadas y respeta el orden de los mensajes.
- `application.send_message.SendMessageUseCase`: caso de uso mínimo que construye el contexto, invoca `FakeLLMProvider` y persiste el turno de usuario y de Sirius con una estrategia explícita (dos escrituras independientes, cada una atómica) probada ante fallo del proveedor y de la persistencia.
- No se añadió interfaz de conversación ni de edición de identidad; la ventana permanece sin cambios visibles.

### V6A — Conversación visual con FakeLLMProvider

- Nueva pestaña "Conversación" en la ventana principal: historial de la conversación principal, mensajes de usuario y de Sirius visualmente diferenciados (negrita para Sirius), campo de entrada, botón de enviar, estado visible mientras Sirius responde y mensaje de error genérico ante fallo. La pestaña "Configuración" existente se conserva intacta.
- `application.get_conversation_history.GetConversationHistoryUseCase`: caso de uso de solo lectura (independiente de SQLAlchemy) para cargar el historial al arrancar, sin crear ni modificar datos.
- `composition_root.py`: composition root fuera de `presentation`, construye repositorios, `ContextBuilder`, `FakeLLMProvider` y los casos de uso, e inyecta las dependencias en `MainWindow` (cuyo constructor ya no las construye por su cuenta).
- Envío en segundo plano con `QThreadPool` (`presentation.conversation_worker`): la interfaz nunca bloquea el hilo gráfico durante el envío; el resultado o el error vuelven mediante señales Qt, procesadas siempre en el hilo principal.
- Entrada vacía o solo espacios rechazada sin llamar al caso de uso; doble envío bloqueado mientras hay una operación en curso; cierre de ventana espera a que termine el envío en curso antes de cerrar.
- `presentation` sigue sin importar SQLAlchemy, los adaptadores de persistencia ni el proveedor LLM directamente (verificado con una prueba estática de importaciones).
- Sin OpenAI real, sin streaming real, sin migraciones nuevas: se reutiliza íntegramente el esquema y los casos de uso de V2-V5.

### V6B — Proveedor OpenAI real (Responses API)

- `ports/llm.py` rediseñado con eventos tipados de aplicación: `LLMTextDelta`, `LLMCompleted`, `LLMCancelled`, `LLMError` (con `LLMErrorKind`: authentication/permission/rate_limited/connection/timeout/invalid_response/budget_exceeded/unknown). `LLMCancelled` y `LLMError` llevan `partial_text` con lo que se hubiera transmitido antes de cancelar o fallar. `stream_response` ya no lanza excepciones por fallos externos: siempre termina en exactamente uno de estos eventos.
- `adapters/llm/openai_responses.py`: `OpenAIResponsesProvider` sobre la Responses API real, con streaming (`stream=True`), `store=False` siempre, sin `previous_response_id`, sin herramientas/búsqueda/archivos/código. Modelo y `max_output_tokens` configurables por constructor. Reintentos propios (máx. 2, backoff con jitter inyectable) solo en la conexión inicial, nunca tras el primer fragmento; es el único sistema de reintentos activo, ya que el cliente del SDK se construye con `max_retries=0` (evita que ambas políticas se multipliquen). Cancelación cooperativa por `operation_id`, cierra el stream siempre. Mensajes de error fijos y seguros (nunca derivados de la excepción real).
- `adapters/llm/budget.py`: `BudgetTracker` acepta un repositorio de uso opcional (`LLMUsageRepository`); sin uno inyectado usa un contador en memoria (proceso actual). El presupuesto mensual (DR-018: 20 USD/mes, aviso a 15 USD, precio por millón de tokens) debe sobrevivir a reinicios de la aplicación, así que la composición real siempre inyecta la persistencia SQLite.
- `adapters/persistence/sqlite_llm_usage_repository.py`: `SqliteLLMUsageRepository`, una fila por mes UTC (`year_month`), acumula el gasto y sobrevive a que se cierre y reabra la aplicación.
- `config/llm_provider_settings.py`: selección `fake`/`openai` provisional vía `SIRIUS_LLM_PROVIDER` (por defecto `fake`, modo seguro). Un valor no reconocido levanta `LLMProviderConfigurationError` explícito — nunca cae silenciosamente a `fake`. Clave leída únicamente de `OPENAI_API_KEY`, nunca persistida; modelo/límite de salida configurables por variables de entorno no sensibles. Documentado como provisional hasta V7.
- `adapters/llm/fake.py`: ahora multi-fragmento y con cancelación cooperativa (mismo mecanismo que el adaptador real), para pruebas deterministas sin hilos ni esperas reales.
- `domain/conversation.py`: nuevo `MessageStatus` (`COMPLETED`/`CANCELLED`/`FAILED`) según SIRIUS-ARQ-0.1 S5.1/S5.2 — un mensaje de Sirius cancelado o fallido conserva su texto parcial con el estado correspondiente en vez de descartarse; nunca se trata como respuesta completada. El estado `PENDIENTE` de la arquitectura no se modela (no hay recuperación de operaciones en curso tras un cierre inesperado en esta vertical).
- `application/send_message.py`: `SendMessageResult.sirius_message` siempre se persiste (nunca `None`): `COMPLETED` con el texto final, o `CANCELLED`/`FAILED` con el texto parcial transmitido. `ContextBuilder` excluye del contexto futuro los mensajes `CANCELLED`/`FAILED`, conservándolos en el historial para trazabilidad. Nuevo parámetro `on_delta` para progreso y `cancel(operation_id)`.
- Idempotencia real por `operation_id`: `ConversationRepository.append_message` es idempotente por `(conversation_id, operation_id, role)` — reintentar una operación tras un fallo de persistencia nunca duplica el mensaje de usuario. Restricción única (`uq_messages_operation_role`) a nivel de base de datos como respaldo; las filas anteriores a V6B conservan `operation_id` nulo sin colisionar entre sí (SQL trata cada NULL como distinto).
- Migración (`add message operation_id and identity_version`, no publicada): añade `messages.operation_id`, `messages.identity_version`, `messages.status` (con valor por defecto `completed` para las filas existentes) y la restricción única `uq_messages_operation_role`; no modifica ninguna migración publicada de V2-V5.
- Migración nueva (`create llm usage`): crea `llm_usage` (una fila por mes UTC) para el presupuesto persistente.
- Interfaz: respuesta de Sirius mostrada progresivamente mientras llegan fragmentos; un mensaje cancelado o fallido permanece visible en el historial con el sufijo "(cancelado)"/"(fallido)" en lugar de desaparecer. Botón "Cancelar" visible solo durante un envío; cancelar detiene el stream cooperativamente sin bloquear la interfaz; cerrar la ventana durante un streaming solicita cancelación (no espera bloqueante) y cierra al terminar.
- `composition_root.py` decide entre `FakeLLMProvider` y `OpenAIResponsesProvider` según la configuración; construye el cliente OpenAI con `max_retries=0`; `application` y `presentation` verificados (pruebas estáticas de imports) para que nunca importen `openai` ni SQLAlchemy directamente.
- Ninguna prueba realiza llamadas de red reales: el adaptador OpenAI se prueba con un cliente y streams completamente simulados.

### V7A — Almacén seguro de secretos y diagnóstico local

- `ports/secrets.py`: el contrato `SecretStore` añade `is_secure_backend()` (SIRIUS-ARQ-0.1 S4) y `SecretStoreError`, una excepción propia con mensaje siempre seguro (nunca incluye el valor de la clave).
- `adapters/secrets/keyring_store.py`: `KeyringSecretStore`, adaptador real sobre `keyring`/Windows Credential Manager, bajo un nombre de servicio centralizado (`config/secrets_config.py`). `set_secret` nunca cae a texto plano: si `is_secure_backend()` es falso, rechaza la escritura. Errores de `keyring` se traducen a `SecretStoreError`. `FakeSecretStore` se mantiene para pruebas y desarrollo, y ningún test escribe en el Credential Manager real (todas las llamadas a `keyring` están simuladas).
- `config/llm_provider_settings.py` reescrito: proveedor, modelo, límite de tokens de salida y presupuesto mensual pasan a ser configuración no sensible persistida en `settings.json`, ya no variables de entorno. La clave de OpenAI se resuelve desde `SecretStore` (flujo normal); `OPENAI_API_KEY` de entorno se conserva únicamente como mecanismo explícito de desarrollo cuando el almacén no tiene nada guardado (SIRIUS-ARQ-0.1 S11.1). Un proveedor desconocido o una configuración inválida sigue produciendo `LLMProviderConfigurationError`, con mensaje siempre seguro.
- `adapters/llm/unconfigured.py`: `UnconfiguredLLMProvider`, nuevo `LLMErrorKind.CONFIGURATION`. Si "openai" está seleccionado pero mal configurado (sin clave, modelo/límites inválidos), la aplicación arranca igualmente; el error seguro solo aparece al intentar enviar un mensaje, nunca al iniciar.
- `infrastructure/logging.py`: registro local rotatorio en `logs/application.log` (5 archivos de 5 MB, SIRIUS-ARQ-0.1 S13), con filtro de redacción defensivo (claves estilo `sk-...`, cabeceras `Bearer`, patrones `api_key=...`). Se registran arranque, proveedor seleccionado, operaciones (`operation_id`) y errores clasificados; nunca contenido de mensajes ni la clave. Sin `print()`.
- Errores visibles al usuario ahora incluyen un identificador de diagnóstico (`operation_id`) para poder correlacionarlos con el registro técnico, sin exponer detalles sensibles.
- Pestaña "Configuración": conserva los campos existentes; añade selección de proveedor, modelo, límite de tokens y presupuesto mensual (persistidos como configuración no sensible); añade un campo enmascarado para introducir una clave nueva y acciones para guardarla o eliminarla. La clave nunca se prellena ni se vuelve a mostrar; solo se indica si hay una clave configurada o no.
- `composition_root.py` construye e inyecta el `SecretStore` real; el modo `fake` sigue funcionando sin ninguna clave configurada.
- Ninguna prueba toca el Credential Manager real ni realiza llamadas de red; pruebas dedicadas demuestran que la clave nunca aparece en `settings.json`, SQLite, los archivos de registro, excepciones mostradas, textos de la interfaz ni las representaciones de los objetos relevantes.
- Endurecimiento posterior: consultar el estado de la clave traduce de forma segura los errores del almacén y nunca impide construir la ventana; la interfaz muestra un estado no disponible sin revelar detalles.
- Endurecimiento posterior: la configuración rechaza límites de tokens y presupuestos iguales a cero o negativos antes de persistirlos.

### Reconciliación documental

- `README.md`, `REPOSITORY_STATUS.md` y `docs/implementation/PLAN.md` se actualizan para distinguir trabajo completado, validaciones manuales pendientes, alcance restante de V7 y V8.
- Se retiran del estado operativo las instrucciones de preparación inicial ya superadas, sin modificar producto, requisitos, Manual ni arquitectura.
