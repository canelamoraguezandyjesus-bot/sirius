# Evidencia — H-32: STATUS.md contradice a PLAN.md

Fecha: 2026-08-28. Rama `h32-status-contradice-a-plan`. Nota de arranque:
`arranque-h32-status-contradice-a-plan.md`.

## Las cuatro preguntas del arranque

**1. ¿El guardián nuevo se vio FALLAR contra el STATUS.md real?** Sí:
`test_status_y_plan_cuentan_la_misma_historia_sobre_la_aceptacion_de_01`
(en `tests/unit/test_documentation_single_source.py`, el sitio que ya fija
«el estado vive en un solo lugar») se escribió primero y falló contra el
repositorio tal cual estaba — no contra una mutación, contra el defecto
vivo. Ese rojo ES la mutación de esta corrección: reintroducir la frase
vieja reproduce exactamente el fallo visto. Tras el arreglo, 8/8 en verde.
El guardián además exige en su segunda mitad que si PLAN.md dejara de
declarar la aceptación, la prueba y STATUS.md cambien JUNTOS.

**2. ¿La línea corregida conserva lo que sigue siendo verdad?** Sí. Antes:
«Sirius 0.1 todavía debe terminarse y aceptarse antes de activar una versión
post-0.1». Ahora: «Sirius 0.1: ACEPTADO y TERMINADO por declaración del
propietario el 10-08-2026 (docs/implementation/PLAN.md). Las versiones
post-0.1 siguen sin activarse.» — el hecho declarado con su fecha y su
fuente, y la mitad operativa (post-0.1 sin activar) intacta.

**3. ¿Ninguna instantánea histórica cambió?** `git diff --stat` de la rama:
solo `docs/canonical/STATUS.md` (1 línea), el guardián nuevo, el registro de
defectos (cierre de H-27, ajeno a H-32) y los dos documentos de esta
auditoría. Nada en `docs/audits/` histórico ni `docs/evolution/`.

**4. ¿El resto de «Estado operativo» quedó intacto?** Sí: las otras cinco
afirmaciones (autorización por verticales, Documento Rector, HEAD-R1,
multiagente, actuadores) no se tocaron.

## Criterio de parada

Se buscó una tercera voz sobre la aceptación de 0.1 antes de tocar nada
(`grep` sobre docs vigentes, excluyendo históricos): solo existen las dos
del hallazgo. Sin parada.

## Estado final

`test_documentation_single_source.py`: 8 en verde. Registro de defectos: 40
en verde (H-27 cerrado por 002022ab, su fusión ya en main). Suite completa,
ruff, format y mypy: en el resumen de la PR.
