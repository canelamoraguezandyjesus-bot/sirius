# Sirius 0.1

Repositorio base del compañero personal de creación e ingeniería Sirius.

## Estado

- Producto 0.1: aprobado.
- Arquitectura técnica 0.1: aprobada.
- Estado del repositorio: preparado para comenzar la implementación por verticales.
- Alcance: no ampliar sin una decisión registrada y aprobada.

## Preparación en Windows 11

1. Instala Git y `uv`.
2. Abre PowerShell en la raíz del repositorio.
3. Ejecuta:

```powershell
.\scripts\bootstrap.ps1
```

El primer arranque generara `uv.lock`. Debe incluirse en el primer commit para que el entorno quede reproducible.

## Crear el repositorio Git

Tras generar `uv.lock` y pasar las comprobaciones:

```powershell
git init -b main
git add .
git commit -m "chore: prepare Sirius 0.1 repository"
```

Despues se conecta el repositorio privado de GitHub.

## Ejecutar el esqueleto

```powershell
uv run sirius
```

## Comprobar calidad

```powershell
.\scripts\check.ps1
```

## Principios operativos

- La interfaz no accede directamente a SQLite ni al proveedor LLM.
- El dominio no depende de PySide6, SQLAlchemy ni del SDK de OpenAI.
- La memoria y el historial son locales y canónicos.
- Cada cambio de alcance requiere una decisión explícita.
- Se implementa una vertical completa cada vez.

Lee `AGENTS.md`, `docs/implementation/PLAN.md` y `docs/canonical/STATUS.md` antes de programar.
