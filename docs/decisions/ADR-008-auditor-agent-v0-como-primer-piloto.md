# ADR-008 — Adoptar Auditor Agent v0 (solo lectura) como primer piloto de agentes

- Estado: PROPUESTO
- Fecha: 2026-08-12
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario

## Contexto y problema

La auditoría de procesos de la Fase 0 (`docs/implementation/WORK_PROCESS_AUDIT.md`,
`AGENT_OPPORTUNITY_MATRIX.md`) inventarió 21 procesos y concluyó que el código ya
no es el cuello de botella: las bolsas de trabajo humano son la supervisión y
reparación de la propia automatización, el transporte de contexto/evidencia y la
deriva documental. La matriz recomendó como primer piloto un agente de triaje de
paradas.

El propietario decidió después, mediante un handoff de contexto fechado el 12 de
agosto de 2026, que el primer experimento tecnológico de agentes NO sea el
triaje (que se mantiene como recomendación operativa posterior) ni una
investigación sobre la memoria de Sirius (asunto ya decidido para esta fase),
sino un **auditor de extremo a extremo**: encontrar defectos reales de código,
contradicciones de arquitectura/contratos y deriva documental que hayan
sobrevivido a pruebas, revisiones y automatización.

Hace falta registrar esa decisión y sus fronteras para que ningún trabajo
posterior las reinterprete. Se registra como ADR porque introduce un proceso de
agente nuevo — exactamente la categoría del criterio de parada de `AGENTS.md` —
y porque la propia auditoría dejó escrito que la aprobación del piloto debía
dejar su propio ADR; no es un ADR por costumbre.

## Criterio de parada (escrito ANTES de decidir)

Del handoff, publicado antes de cualquier ejecución del piloto:

1. **Un solo falso positivo grave presentado con alta confianza** detiene el
   piloto y obliga a analizar el método antes de aumentar autonomía.
2. Dos ejecuciones consecutivas con defectos de la misma familia en el método
   del auditor → regla de las dos rondas sobre el diseño, no más parches.
3. Si el coste de supervisar al auditor supera el valor de sus hallazgos, el
   piloto se para y se dice.

## Opciones consideradas

1. **Agente de triaje de paradas** (recomendación original de la matriz): mayor
   toil eliminado, riesgo bajo.
2. **Research Agent sobre la arquitectura de memoria**: descartado por el
   propietario; la memoria está suficientemente decidida para esta fase.
3. **Auditor Agent v0 de solo lectura** (elegida): revisa Sirius de extremo a
   extremo buscando problemas reales demostrables.

## Decisión

Adoptar **Auditor Agent v0** como primer piloto, con estas fronteras no
negociables:

- **Solo lectura estricta**: lee repositorio, historial git, issues/PRs/comentarios
  y runs de Actions; puede ejecutar análisis y pruebas seguras si el entorno lo
  permite. **No** edita, no comitea, no hace push ni merge, no cambia etiquetas,
  issues, workflows ni settings, no accede a secretos, sin WebSearch/WebFetch en v0.
- **No arregla sus propios hallazgos**; produce únicamente un informe estructurado.
- Cada hallazgo cumple el esquema FINDING-### con evidencia concreta e intento
  de refutación; sin ambos, no entra en el informe final.
- No se amplía ningún permiso «para facilitar» el piloto; `.claude/settings.json`
  no se toca.
- Se registran métricas por ejecución (modelo, commit auditado, duración, turnos,
  tokens, coste, hallazgos/confirmados/falsos positivos), con `unknown` cuando
  algo no sea observable — nunca inventadas.

La especificación operativa (runbook, formato de hallazgo, métricas, criterios
de éxito/fracaso, rollback y primera misión) vive en
`docs/implementation/AUDITOR_AGENT_V0.md`.

## Comprobación que la sostiene

- La decisión y sus fronteras constan en el handoff del propietario del
  12-08-2026 (transferido a la sesión de Claude Code que abre esta PR); este ADR
  las transcribe sin ampliarlas.
- La necesidad del piloto se apoya en el inventario con evidencia de
  `WORK_PROCESS_AUDIT.md` (commits `732a0ac`/`fe21ca9`: nota de arranque
  publicada antes que las conclusiones; latencias y fichas con fuentes).
- Precedente de utilidad del patrón: la auditoría paralela de 6 lentes de
  ADR-004 destapó 8 defectos que 9 rondas seriales no vieron.

## Consecuencias

- El primer run del auditor solo puede lanzarse tras la fusión de esta PR y
  sobre un commit fijado de `main`, siguiendo `AUDITOR_AGENT_V0.md`.
- El triaje de paradas queda como candidato posterior (orden: Auditor v0 →
  auditor documental → triaje → Research con perfil web → benchmark multimodelo).
- Un run del auditor no entra en la máquina de estados `sirius:*` (no es un
  bloque de la tubería); su seguimiento usa una issue normal sin etiquetas
  `sirius:`.
- Las decisiones sobre los hallazgos siguen siendo del propietario; el auditor
  no convierte hallazgos en trabajo por sí mismo.

## Alternativas descartadas y por qué

- **Triaje primero**: sigue siendo la mayor eliminación de toil por riesgo, pero
  el propietario prioriza validar la tecnología de agentes con una misión de
  valor directo sobre el producto; el triaje se retoma después.
- **Research/memoria primero**: reabriría un asunto decidido sin evidencia nueva
  y exigiría además la decisión de permisos web, que se pospone.
- **Auditor con permisos de escritura o web desde el inicio**: ampliaría la
  superficie de riesgo (inyección indirecta, autorreparación de hallazgos) sin
  necesidad demostrada; v0 debe demostrar primero calidad de hallazgos.
