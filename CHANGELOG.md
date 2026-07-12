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
