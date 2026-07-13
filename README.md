# Sirius 0.1

Repositorio privado del compañero personal de creación e ingeniería Sirius.

## Estado actual

- Producto Sirius 0.1: aprobado.
- Arquitectura técnica 0.1 y decisiones ATD-001 a ATD-012: aprobadas.
- Implementación completada hasta V7A, incluido su endurecimiento posterior.
- Alcance activo restante de V7: copia cifrada, validación de integridad y restauración segura.
- V8 permanece pendiente para la aceptación completa de Sirius 0.1.
- El alcance no debe ampliarse sin una decisión registrada y aprobada.

La arquitectura modular ya existe y está parcialmente implementada. No debe rediseñarse desde cero salvo que aparezca una contradicción o un riesgo concreto.

## Fuentes de verdad

Antes de modificar el proyecto, lee:

1. `docs/canonical/STATUS.md`;
2. `docs/implementation/PLAN.md`;
3. `REPOSITORY_STATUS.md`;
4. `AGENTS.md`.

Los documentos canónicos conservan en algunos nombres la palabra `PROPUESTO` porque son instantáneas históricas anteriores a su aprobación. Su estado vigente está fijado en `docs/canonical/STATUS.md`.

## Preparar o sincronizar el equipo Windows 11

En una copia local existente:

```powershell
git switch main
git pull --ff-only origin main
.\scripts\bootstrap.ps1
```

Para ejecutar Sirius:

```powershell
uv run sirius
```

Para ejecutar todas las comprobaciones locales:

```powershell
.\scripts\check.ps1
```

GitHub Actions ejecuta también Ruff, mypy y pytest en Windows para cada pull request y cada cambio integrado en `main`.
