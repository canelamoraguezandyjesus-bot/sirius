# ADR-150 — Dar al corrector tiempo para corregir y validar con la cadena completa dentro de su paso

- Estado: PROPUESTO
- Fecha: 2026-09-06
- Aprobación: la fusión de esta PR por el propietario (toca `.github/**`;
  ficha del operador, deuda 8 de la bitácora en su parte de presupuesto).

## Contexto y problema

El paso «Ejecutar Claude Code (corrector)» de `repair-sirius-work.yml` tenía
`timeout-minutes: 30`, fijado cuando la ronda del corrector era «corregir lo
señalado y volver a pasar las pruebas afectadas». Desde ADR-145 (05-09) la
ronda exige además **una sola invocación de `scripts/check.ps1`** —formato,
lint, mypy y la suite completa, unos 9 minutos en el runner— antes de
escribir `FIXED`. El presupuesto no se movió con la regla.

El dato: en la incidencia #545 el corrector de la ronda 1 (run 33998592213,
23:24:31 → 23:55:03 UTC del 05-09) murió con «The action has timed out» a los
30:00 exactos, y al matarlo tenía vivos `pwsh`, `uv` y `pytest`: había hecho la
corrección (un P1 de diseño y dos P2 de Codex) y estaba validando. No llegó a
commit ni push; la PR #546 quedó en `f877ec7`, la incidencia en
`failed-safely` y el veredicto provisional sin sustituir. M21b (03-09) ya
registró **tres** muertes del corrector con este mismo perfil (entradas 16 y
18 de la bitácora); entonces la corrección la terminó el propietario a mano.

Aritmética del job hoy: checkout 5 + Qt 10 + uv 3 + sync 8 + puerta 8 +
evento 3 + prompt 2 + corrector 30 + aplicación 5 = 74, bajo un job de 80 (el
comentario del workflow aún decía «= 53, con 7 de margen sobre los 60»: se
quedó viejo).

## Criterio de parada (escrito ANTES de decidir)

- El guardián `test_job_timeout_covers_every_bounded_step_plus_margin` sigue
  en verde con los números nuevos (suma de pasos + 5 ≤ job; corrector < job)
  sin tocar su aritmética; si hubiera que debilitarlo, se para.
- En vivo: relanzado el corrector de #545 con `continua`, la ronda tiene que
  terminar en `FIXED` con su cadena completa ejecutada, o morir por una causa
  que NO sea el tiempo. Una segunda muerte por tiempo con 50 minutos
  desmiente este ADR y obliga a mirar la raíz (tamaño de la ronda, deuda 8),
  no a subir otra vez el número.

## Opciones consideradas

1. **Subir el tope del corrector a 50 minutos** (elegida): la corrección de
   una ronda con un P1 de diseño cabe en ~40 y la cadena en ~9; el job pasa a
   100 para conservar el margen que el guardián exige.
2. **Quitar la cadena completa de la ronda del corrector** (volver a «pruebas
   afectadas»). Descartada: ADR-145 la puso porque los comandos sueltos y las
   tandas parciales costaron vueltas enteras (#537, #541).
3. **Partir la ronda: un commit por hallazgo con su propio presupuesto**
   (deuda 8). Es la respuesta de fondo, y es un encargo del motor, no una
   ficha de un número; este ADR no la sustituye, la deja pendiente.
4. **Relanzar con 30 y esperar**. Descartada: el mismo trabajo con el mismo
   presupuesto muere en el mismo sitio.

## Decisión

- «Ejecutar Claude Code (corrector)»: `timeout-minutes: 50` (antes 30).
- Job `repair`: `timeout-minutes: 100` (antes 80); el comentario del
  presupuesto pasa a decir la aritmética real: 5 + 10 + 3 + 8 + 8 + 3 + 2 +
  50 + 5 = 94, con 6 de margen sobre 100.
- Nada más cambia: ni `--max-turns`, ni el prompt, ni la puerta.

## Comprobación que la sostiene

- El dato de la muerte: run 33998592213, paso 9 de 23:24:51 a 23:55:03
  («The action has timed out», `duration_ms=1809925`), procesos huérfanos al
  terminar: `bun`, `claude`, `bash`, `pwsh`, `tail`, `uv`, `pytest`.
- Guardián estructural: `uv run pytest tests/automation/test_sirius_repair_workflow.py`
  en verde con los números nuevos (resultado transcrito en el cuerpo de la
  PR), sin cambiar su aritmética.
- Cadena completa como una sola invocación sobre el head definitivo: código
  de salida transcrito en el cuerpo de la PR.
- Lo que NO se ha medido: la ronda relanzada de #545 (el criterio en vivo de
  arriba). Se registra en la bitácora cuando ocurra.

## Consecuencias

- Una ronda del corrector puede costar hasta 50 minutos de runner en vez de
  30; solo las que lo necesiten los usan.
- Deuda 8 queda como está: presupuesto por hallazgo y cancelación cuando el
  propietario corrige a mano siguen sin resolverse; este ADR solo alinea el
  tope con la regla de ADR-145.
- El comentario del workflow vuelve a decir la verdad de su aritmética.

## Alternativas descartadas y por qué

Ver «Opciones consideradas».
