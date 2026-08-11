# SIRIUS — Auditoría de procesos de trabajo (Fase 0)

- **Estado:** EN CURSO — este commit publica la nota de arranque y el criterio de parada ANTES de cualquier conclusión, conforme a la skill `disciplina-evidencia` (ADR-001).
- **Fecha de arranque:** 11 de agosto de 2026
- **Encargo:** auditoría de procesos de trabajo (process mining) previa al diseño de agentes. No se implementan agentes en esta fase.
- **Vertical:** solo documentación en `docs/implementation/`. Sin cambios en código, `.claude/`, `.github/`, permisos ni workflows.

## Nota de arranque

1. **¿Dónde vive el fallo y dónde va el arreglo?** El «fallo» que se estudia es trabajo humano repetitivo que no deja traza estructurada (transferencia de contexto, vigilancia, reconciliación, coordinación). El «arreglo» (este inventario y la matriz de oportunidades) vive en `docs/implementation/`. ¿Puede el sitio del arreglo OBSERVAR el fallo? **Solo parcialmente.** Desde el repositorio y GitHub se observa lo que pasó por PRs, issues, comentarios, commits, workflows y documentos. NO son observables desde aquí: las conversaciones de ChatGPT, el trabajo local en Windows no comiteado, las sesiones interactivas de Claude Code no publicadas y el tiempo/atención humanos. Todo lo no observable se registrará como límite o como hipótesis marcada, nunca como hecho.
2. **¿Qué NO va a garantizar este trabajo?**
   - No garantiza un inventario exhaustivo: los canales no observables pueden contener procesos enteros que aquí no aparezcan.
   - No garantiza tiempos humanos medidos: no existe time-tracking; toda cifra de minutos u horas será una estimación y se marcará como tal.
   - No garantiza que la hipótesis rectora («el cuello de botella ya no es escribir código sino la coordinación de conocimiento alrededor del código») quede confirmada ni refutada de forma concluyente; solo se contrasta contra las trazas disponibles.
   - No garantiza que los candidatos de agentes propuestos sean viables: eso lo decidirá el diseño y el piloto posterior.
3. **Criterio de parada** (decidido antes de ver resultados; el encargo §13 es la fuente):
   1. todos los procesos repetidos observables en la muestra (PRs #119–#149, issues asociadas, workflows, scripts, docs, historial git; más trazas anteriores como línea base) tienen ficha PROC-###;
   2. cada proceso tiene al menos una evidencia concreta o se marca explícitamente como hipótesis;
   3. los principales handoffs humano↔herramienta están representados;
   4. se puede explicar dónde se va el tiempo humano y por qué;
   5. existe un ranking de automatización basado en trabajo eliminado y riesgo;
   6. queda recomendado un único primer piloto;
   7. no quedan categorías de trabajo conocidas (taxonomía A–F del encargo §4) sin revisar.
   - **Regla de las dos rondas aplicada aquí:** si dos rondas de verificación consecutivas descubren la misma familia de trabajo manual omitida, se detiene la catalogación incremental y se revisa la taxonomía completa antes de seguir añadiendo procesos.
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** Que el contexto se capture una sola vez en un artefacto canónico legible por todas las herramientas (Work Item), de modo que la transferencia manual deje de ser necesaria por construcción. No se construye en esta fase; la auditoría lo evalúa solo como diseño candidato. Se dice explícitamente por qué no se hace ahora: el encargo prohíbe implementar y el coste de equivocarse de diseño antes del inventario es exactamente el fallo que esta auditoría existe para evitar.

## Declaración de alcance de decisión

Este trabajo produce **recomendaciones**, no decisiones. Si al cerrar la auditoría no hay ninguna decisión aprobada por el propietario, no se registrará ADR y se dirá explícitamente (skill `disciplina-evidencia` §5).

## Metodología prevista

1. Inspección de fuentes primarias del repositorio: `AGENTS.md`, `CLAUDE.md`, `.claude/**`, `.github/workflows/**`, `scripts/automation/**`, `docs/implementation/**`, `docs/decisions/**`, `docs/audits/**`, `docs/operations/**`, `docs/canonical/**` (solo lectura), historial git.
2. Inspección de trazas de GitHub: PRs #119–#149 con cuerpos, comentarios, revisiones y tiempos; issues de trabajo y de gobernanza; trazas de la automatización anterior (#42–#90) como línea base de trabajo ya eliminado.
3. Reconstrucción de procesos (no de componentes): ficha PROC-### con disparador, pasos, ejecutor de cada paso, herramientas, fricción, evidencia y oportunidad de eliminación.
4. Verificación adversarial: crítica de completitud contra la taxonomía A–F, verificación por muestreo de que la evidencia citada sostiene cada ficha, e intento de refutación de la hipótesis rectora y del piloto recomendado.
5. Entrega: este documento completado + `AGENT_OPPORTUNITY_MATRIX.md`.

*(El inventario, los diagramas, la matriz y las conclusiones se añadirán a este documento al completarse la inspección. Este commit existe para que el criterio quede publicado antes que los resultados.)*
