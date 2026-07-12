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

## Primera acción en el equipo Windows

Ejecutar `scripts/bootstrap.ps1`. Esa operación instalará Python 3.14.6 mediante uv, resolverá las dependencias y generará `uv.lock`. Después debe ejecutarse `scripts/check.ps1` y añadirse `uv.lock` al primer commit.

## Verificaciones pendientes del equipo objetivo

Este paquete no afirma haber ejecutado PySide6, mypy, Ruff ni la suite completa con Python 3.14.6, porque esas dependencias no estaban disponibles en el entorno de generación. La puerta V0 solo quedará cerrada cuando `scripts/check.ps1` pase en Windows 11.
