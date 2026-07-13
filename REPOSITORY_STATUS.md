# Estado actual del repositorio

## Estado canónico

- Producto Sirius 0.1: aprobado.
- Arquitectura técnica 0.1: aprobada.
- Decisiones ATD-001 a ATD-012: aprobadas.
- Implementación autorizada por verticales, sin ampliar el alcance aprobado.

## Implementación completada

- V0: repositorio, entorno reproducible, PySide6, Ruff, mypy, pytest y CI en Windows.
- V1: rutas locales y configuración no sensible.
- V2: historial persistente con SQLite y Alembic.
- V3: proyecto activo único y persistente.
- V4: memoria manual, versionada y trazable.
- V5: identidad versionada y constructor de contexto.
- V6A: interfaz de conversación con proveedor simulado.
- V6B: proveedor OpenAI real, streaming, cancelación, errores tipados, idempotencia y presupuesto persistente.
- V7A: Windows Credential Manager, configuración del proveedor, diagnóstico local y protección frente a configuraciones inválidas.
- Endurecimiento de V7A: fallo seguro al consultar credenciales y rechazo de límites no positivos antes de persistirlos.

## Estado de verificación

### Confirmado automáticamente

- GitHub Actions funciona en Windows.
- Ruff format, Ruff lint, mypy estricto y pytest pasan para la rama principal y para pull requests verificadas.
- Las pruebas de OpenAI usan clientes y streams simulados; no realizan llamadas de red reales.
- Las pruebas de `keyring` no leen ni escriben en el Credential Manager real.

### Pendiente de validación manual

- Prueba end-to-end con una clave real de OpenAI.
- Guardar y eliminar una clave desde la interfaz en Windows real y comprobar su presencia en el Credential Manager bajo el servicio `Sirius`.
- Comprobación visual de la aplicación en el equipo objetivo.
- Confirmar si la configuración de proveedor y clave debe recargarse sin reiniciar; actualmente se aplica al próximo arranque y no existe una decisión aprobada que obligue a la recarga en caliente.

## Alcance activo restante

V7 todavía no está completa. Permanecen dentro del alcance ya aprobado:

- copia cifrada;
- validación de integridad;
- restauración segura;
- pruebas automáticas y manuales correspondientes.

El nombre de una posible subdivisión posterior de V7 no se considera canónico hasta que se registre expresamente.

## Fase posterior

V8 — Aceptación de Sirius 0.1:

- prueba completa durante varias sesiones;
- proyecto pequeño real de principio a fin;
- corrección de defectos;
- paquete ejecutable de prueba.

## Método de trabajo vigente

- `main` debe permanecer integrable.
- Los cambios se realizan en ramas breves.
- Se integran mediante pull request y squash cuando las comprobaciones están en verde.
- No se convierten conversaciones exploratorias en requisitos ni cambios de arquitectura.
- Las pruebas visuales, físicas o dependientes del Windows real siguen requiriendo intervención del usuario.
- Antes de volver a trabajar desde el equipo local, debe sincronizarse con `git pull --ff-only origin main`.

## Fuentes históricas

Los documentos anteriores a la aprobación pueden conservar palabras como `PROPUESTO` o instrucciones de preparación inicial ya superadas. `docs/canonical/STATUS.md`, este archivo y `docs/implementation/PLAN.md` reflejan el estado operativo vigente.
