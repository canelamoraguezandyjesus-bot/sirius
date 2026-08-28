# Nota de arranque — H-32: STATUS.md contradice a PLAN.md

Fecha: 2026-08-28. ANTES del primer cambio (ADR-001). Corrección autorizada.

## Afirmación a corregir (verificada en #396)

`docs/canonical/STATUS.md` («Estado operativo») dice que «Sirius 0.1 todavía
debe terminarse y aceptarse», mientras `docs/implementation/PLAN.md` declara
«Sirius 0.1: ACEPTADO y TERMINADO por declaración del propietario el
10-08-2026». Dos documentos vigentes, dos verdades.

## Lo que se decide construir

1. La línea de STATUS.md pasa a reflejar el hecho declarado en PLAN.md,
   CONSERVANDO la mitad que sigue siendo verdad (las versiones post-0.1 no
   están activadas). No se toca ninguna instantánea histórica.
2. Un guardián en `tests/unit/test_documentation_single_source.py` (el sitio
   que ya fija «el estado vive en un solo lugar»): si PLAN.md declara la
   aceptación, STATUS.md no puede decir a la vez que sigue pendiente.

## Las preguntas

1. ¿El guardián nuevo se ve FALLAR contra el STATUS.md actual?
2. ¿La línea corregida conserva lo que sigue siendo verdad (post-0.1 sin
   activar) y cita la fuente (PLAN.md, 10-08-2026)?
3. ¿Ninguna instantánea histórica (docs/audits/, docs/evolution/) cambia?
4. ¿El resto de afirmaciones de «Estado operativo» quedan intactas?

## Criterio de parada

- Si al leer PLAN.md y STATUS.md enteros apareciera una TERCERA voz sobre la
  aceptación de 0.1, parar y decidir con las tres delante.
- Dos rondas (ADR-001).
