# Evidencia — registro-cierre-h25: el apunte contable de H-25

Fecha: 2026-08-28. Rama `registro-cierre-h25`.

## Por qué esta rama no lleva nota de arranque propia

Mismo caso que `evidencia-registro-cierre-h32.md`: un defecto no puede
cerrarse en su propia PR porque su SHA de fusión no existe hasta fusionar. La
decisión y la evidencia de H-25 viven en su rama (`arranque-h25-…`,
`evidencia-h25-…`, ADR-101, fusionadas en la #406); aquí solo se anota su
`cerrado_por` (4322989f).

## Afirmación y comprobación

- Afirmación: con este apunte, ningún defecto del registro está `abierto`, y
  el guardián `test_ningun_defecto_abierto_tiene_ya_su_arreglo_en_main` queda
  en verde sobre main.
- Comprobación: `uv run pytest tests/automation/test_registro_de_defectos.py`
  → en verde en esta rama, contra `origin/main` real (la salida se cita en la
  PR).

## Criterio de parada

Si el guardián señalara cualquier otro defecto abierto con arreglo en main, o
el SHA anotado no fuera el de la fusión real de la #406, parar y mirar antes
de fusionar.
