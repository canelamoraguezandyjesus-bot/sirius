---
description: Ejecuta scripts/check.ps1 (Ruff format, Ruff lint, mypy, pytest) y resume el resultado
---

Ejecuta `scripts/check.ps1` desde la raíz del repositorio.

Después de la ejecución, presenta un resumen claro con:

1. Resultado de cada comprobación por separado (Ruff format, Ruff lint, mypy, pytest): PASA o FALLA.
2. Si alguna falló, el mensaje de error relevante (archivo y línea cuando esté disponible), sin reformular ni resumir el problema de fondo.
3. Si todas pasaron, confírmalo en una sola frase.

No corrijas nada automáticamente, no hagas commit y no ejecutes ninguna otra acción: solo ejecuta el script e informa el resultado.
