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
