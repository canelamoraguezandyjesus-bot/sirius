$ErrorActionPreference = "Stop"

# ADR-153: cada comando nativo comprueba su propio código de salida y el guion
# se detiene en el primer rojo. `$ErrorActionPreference` no alcanza a los
# ejecutables nativos, y `pwsh -File` devuelve el código del ÚLTIMO comando:
# hasta el 06-09-2026 el «exit 0» de este guion era el de pytest y solo el de
# pytest, con ruff format, ruff lint o mypy en rojo pasando desapercibidos
# (incidencia #545, rondas 2 y 3).
uv run ruff format --check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run mypy src tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run pytest
exit $LASTEXITCODE
