# Evidencia — registro-cierre-h32: el apunte contable final de la fase de corrección

Fecha: 2026-08-28. Rama `registro-cierre-h32`.

## Por qué esta rama no lleva nota de arranque propia

No corrige ningún defecto ni toma ninguna decisión nueva: es el último apunte
del patrón que TODA la fase siguió (cada rama cierra en el registro los
hallazgos cuyo arreglo ya está en main, porque un defecto no puede cerrarse en
su propia PR: su SHA de fusión no existe hasta fusionar). La decisión y la
evidencia de H-32 viven en su rama (`arranque-h32-…` y `evidencia-h32-…`,
fusionadas en la #404); aquí solo se anota su `cerrado_por` (80fb4fe).

## Afirmación y comprobación

- Afirmación: con este apunte, los 7 hallazgos de la auditoría externa
  (H-26…H-32, incidencia #396) constan `cerrado` con su commit de fusión, y
  ningún defecto abierto tiene ya su arreglo en main.
- Comprobación: `uv run pytest tests/automation/test_registro_de_defectos.py`
  → 40 en verde en esta rama, incluido
  `test_ningun_defecto_abierto_tiene_ya_su_arreglo_en_main` contra
  `origin/main` real. El único `estado: abierto` restante es H-25, que espera
  la decisión del propietario en #376 — fuera de esta fase, y exactamente lo
  que ese guardián permite.

## Criterio de parada

Si el guardián hubiera señalado cualquier otro defecto abierto con arreglo en
main, o el SHA anotado no fuera el de la fusión real de la #404, parar y
mirar antes de fusionar. No ocurrió.
