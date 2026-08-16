# ADR-021 — Prohibir en el prompt que el corrector cierre el turno esperando trabajo en segundo plano

- Estado: PROPUESTO
- Fecha: 2026-08-16
- Aprobación: la fusión de la PR #179 por el propietario.

## Incumplimiento de ADR-001, dicho primero

**La nota de arranque de este trabajo no se publicó antes del primer commit.** Se
diagnosticó el fallo y se editó el prompt directamente. El criterio de parada de
la sección siguiente se escribió DESPUÉS de ver el resultado, así que no ata
nada: queda como declaración de alcance, no como criterio previo. Se registra
aquí sin adornos, igual que ADR-009 registró el suyo, porque una disciplina que
solo se cita cuando se cumple no es una disciplina.

Lo que sí sostuvo este trabajo fue la regla de las dos rondas: tras dos rondas
perdidas se paró, se escribió el patrón y no se reactivó a ciegas — la tercera
reactivación solo ocurrió después de instrumentar el workflow para poder ver el
corte.

## Contexto y problema

En la incidencia #177 (bloque A1 del Work Engine), tres rondas de corrección
terminaron sin escribir veredicto y sin empujar un solo commit. El veredicto
provisional (ADR de facto del prompt, nacido de la incidencia #135) hizo su
trabajo —convertir el silencio en parada honesta— pero cada ronda se perdía
entera, con su coste de uso.

Las hipótesis obvias quedaron descartadas con datos:

| Hipótesis | Evidencia que la descarta |
|---|---|
| Tope de turnos agotado | 69 de 120 (run 31914145332) |
| Permiso denegado | `permission_denials: []` (run 31953500564) |
| Timeout de paso o de job | 6,4 min contra 30 y 60 |
| Puerta de convergencia | Dejó pasar la ronda; su bloqueo sería `blocked-decision` |

El diagnóstico no se pudo cerrar hasta que el propietario activó
`show_full_output: true` en `repair-sirius-work.yml` (commit `b90e7fb`): hasta
entonces el log decía literalmente «full output hidden for security» y la ronda
moría sin traza inspeccionable.

## Criterio de parada (escrito después de ver el resultado; ver arriba)

Se toca únicamente `scripts/automation/prompts/corrector.md`. No se toca
`reviewer.md` ni `implementer.md`: la misma trampa podría afectarles, pero no
hay evidencia de que les haya ocurrido, y parchear sin caso delante es la
familia de defecto que este repositorio lleva corrigiendo. Si aparece, se
corrige entonces, con su run.

## Opciones consideradas

1. **Subir el tope de turnos del corrector**: descartada — no se quedó corto
   (69 de 120). Habría enmascarado la causa.
2. **Detectar el corte desde el arnés** (por ejemplo, fallar si quedan procesos
   huérfanos): descartada por ahora — es más mecanismo del que el problema pide,
   y toca `.github/workflows/`, con la frontera de ADR-002.
3. **Envolver las validaciones en el arnés** para que el modelo no las lance:
   descartada — cambia el reparto de responsabilidades del rol por un defecto
   que se corrige diciéndoselo.
4. **Decirlo en el prompt, con la evidencia dentro**: elegida.

## Decisión

Añadir al prompt del corrector la sección «Nadie te va a contestar: no termines
el turno esperando nada», con tres reglas: (1) las validaciones se ejecutan en
primer plano y se espera su resultado dentro del mismo turno; (2) nunca cerrar
el turno anunciando trabajo pendiente; (3) lo que no cabe en el turno es un
`FAILED_SAFELY` con diagnóstico, no una espera. La evidencia que lo motiva va
citada dentro del propio prompt.

## Comprobación que la sostiene

- Frase literal con la que terminó la ronda, en el volcado del modelo del run
  31953500564: «Espero a que termine el `pytest` en segundo plano […] y aviso en
  cuanto tenga el resultado», con `terminal_reason: completed`.
- Rastro coherente en los runs anteriores: procesos huérfanos `uv` y `pytest`
  terminados por el cleanup del job (runs 31913075482 y 31914145332).
- `tests/automation/` completo en verde tras el cambio (387 pruebas), incluida
  `test_sirius_repair_workflow.py`, que fija la estructura del veredicto
  provisional del prompt.

## Consecuencias

- El corrector deja de perder rondas por esta causa concreta. **No se afirma que
  cierre todas las formas de terminar sin veredicto**: cierra la demostrada.
- Queda pendiente, si el propietario lo quiere, la misma regla para los otros
  dos roles y la subida del volcado de ejecución como artefacto (hoy solo el
  Auditor lo hace).
- El caso queda como ejemplo de por qué la instrumentación es parte de la
  automatización y no un extra: sin `show_full_output` este defecto era
  indiagnosticable y ya había costado tres rondas.
