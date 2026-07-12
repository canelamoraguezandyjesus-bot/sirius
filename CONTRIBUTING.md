# Forma de trabajo

## Ramas

- `main`: siempre integrable y protegida cuando exista el repositorio remoto.
- `feat/<tema>`: funciones nuevas dentro del alcance aprobado.
- `fix/<tema>`: correcciones.
- `docs/<tema>`: documentación.
- `chore/<tema>`: herramientas, dependencias o mantenimiento.

No se usará una rama `develop`. Las ramas serán breves y se integrarán mediante squash cuando las comprobaciones estén en verde.

## Antes de integrar

1. El cambio pertenece a la vertical activa.
2. Las pruebas nuevas y existentes pasan.
3. Ruff, mypy y pytest pasan.
4. No se han incluido secretos ni datos personales.
5. La documentación afectada está actualizada.
6. No se amplió el alcance sin aprobación.

## Commits

Usa mensajes claros:

- `feat: ...`
- `fix: ...`
- `test: ...`
- `docs: ...`
- `refactor: ...`
- `chore: ...`
