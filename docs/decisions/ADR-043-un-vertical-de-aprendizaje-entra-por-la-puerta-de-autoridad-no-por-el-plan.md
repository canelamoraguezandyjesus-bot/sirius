# ADR-043 — Un vertical de aprendizaje entra por la puerta de autoridad, no por el plan

- Estado: PROPUESTO
- Fecha: 2026-08-19
- Aprobación: pendiente; en este repositorio, la fusión de la PR por el propietario

Este ADR es además la **nota de arranque** de la rama
`claude/sirius-learning-audit-ixtr0g` (ADR-001, skill `disciplina-evidencia`):
se escribió y se publicó **antes del primer cambio de contenido**, y su criterio
de parada se decidió **antes de ver ningún resultado de la auditoría**.

## Contexto y problema

El propietario aporta dos documentos —`01_HERMES_LEARNING_AUDIT` (auditoría
factual del mecanismo de aprendizaje de Hermes Agent) y
`02_SIRIUS_LEARNING_INTEGRATION_BRIEF` (brief normativo)— y pide **integración
de diseño, no implementación**: contrastar los adjuntos contra el repositorio,
auditar las costuras de aprendizaje del Work Engine, determinar el punto mínimo
de enganche y proponer dónde entra este vertical en el plan.

El fallo que este trabajo debe evitar no es técnico: es de autoridad. Un brief
bien escrito se lee como una decisión tomada. Si sus contenidos aterrizan
directamente en `PLAN.md`, en el contrato operativo o en `docs/canonical/`, el
repositorio pasa a declarar como aprobado algo que nadie aprobó. Es exactamente
la familia de deriva que `WORK_PROCESS_AUDIT.md` ya registró (PROC-010,
PROC-011) y que ADR-005 cerró para V8.

### ¿Puede el sitio del arreglo observar el fallo que arregla?

Sí, y de forma mecánica. El fallo se manifiesta como una cosa concreta y
observable: **el diff de esta rama tocando un fichero que declara estado o
autoridad aprobados**. El arreglo vive en el mismo sitio que el fallo —el propio
diff—, así que puede observarlo sin reconstruir la semántica de ningún otro
sistema. El predicado es comprobable con un comando, no vigilado a mano:

```
git diff --name-only origin/main...HEAD
```

no debe contener `docs/canonical/**`, `docs/implementation/PLAN.md`,
`docs/implementation/AUTOMATION_OPERATING_CONTRACT.md`,
`docs/implementation/SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md`,
`docs/implementation/SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md`,
`REPOSITORY_STATUS.md`, `src/**`, `.github/**` ni `scripts/**`.

El informe de integración es **evidencia** y vive en `docs/audits/`. Este ADR es
la **propuesta**, y su estado es PROPUESTO hasta que el propietario lo fusione.

### Qué NO garantiza esto (escrito antes de auditar)

- **No autoriza el Learning Engine**, ni su implementación, ni una reserva de
  hueco en el plan aprobado. Un ADR PROPUESTO no mueve una fase.
- **No audita Hermes.** El repositorio `NousResearch/hermes-agent` no está en el
  alcance de esta sesión. El adjunto 01 se toma como **descripción dada** sobre
  Hermes; solo se verifica contra el código lo que afirma **sobre Sirius**.
- **No arregla la PR #207.** Cualquier defecto que la auditoría encuentre en A5
  se reporta, no se corrige aquí: tocar A5 para meter aprendizaje está prohibido
  por el propio brief y por el criterio de parada de más abajo.
- **No mide nada cuantitativo**: ni coste por candidato, ni calidad de modelos,
  ni algoritmo de deduplicación, ni umbrales de auto-promoción. Esas decisiones
  se miden, no se adivinan, y no hay datos que medir todavía.
- **No fija el backend físico** del conocimiento (fichero, SQLite, vector store):
  ADR-019 hace depender la representación definitiva de I3 **e** I4, y I4 sigue
  sin resolverse.
- **No garantiza que el punto de enganche recomendado sobreviva** a las enmiendas
  C1 y C2 del contrato (E1b), que todavía no existen.

## Criterio de parada (escrito ANTES de ver ningún resultado)

Cualquiera de estas condiciones detiene la recomendación y la convierte en una
pregunta al propietario, en vez de en un diseño:

1. **A5 y el dominio son intocables.** Si el enganche mínimo exige modificar
   `src/sirius_engine/domain/**`, el puerto de almacén, o cualquier fichero de la
   rama de la PR #207, no se propone diseño v0: sube la pregunta.
2. **Clase de trabajo nueva = decisión del propietario.** Si el vertical exige
   una fila nueva en la tabla de autoridad por clase (contrato v1.7 §11,
   ADR-041), eso no entra como recomendación técnica: entra como enmienda de
   contrato, que es del propietario.
3. **Una garantía no verificable se declara insostenible, no se suaviza.** Si
   alguna de las tres invariantes duras —el Extractor no puede escribir
   conocimiento activo; el Refutador usa un modelo distinto *y el motor puede
   comprobarlo*; el Promotion Gate falla cerrado— resulta **no comprobable** con
   lo que el motor tiene, se escribe «no sostenible hoy» y por qué. No se
   reformula para que parezca cumplida.
4. **Regla de las dos rondas.** Si dos rondas de refutación adversarial devuelven
   objeciones de la misma familia, se prohíbe seguir parcheando el diseño: se
   escribe el patrón, se busca la raíz y se decide seguir, retirar o escalar.
5. **Sin corpus no hay aprendizaje.** Si el motor no ha ejecutado todavía ningún
   WorkItem real con un Worker real, la recomendación de calendario debe ser
   «todavía no», por muy bueno que resulte el diseño. Un Learning Engine sin
   experiencia de la que aprender es un generador de ruido con coste.

## Opciones consideradas

Pendiente: se rellena con el resultado de la auditoría de costuras y de la pasada
adversarial. Las opciones de enganche se enumeran en el informe de integración,
con ruta y línea, y la elegida se justifica aquí.

## Decisión

Pendiente hasta cerrar la auditoría. Lo único decidido **antes** de auditar es la
forma de entrada, que es lo que este ADR fija: informe en `docs/audits/` como
evidencia; propuesta en este ADR como decisión sujeta a aprobación; cero
escrituras en los documentos que declaran estado o autoridad aprobados.

## Comprobación que la sostiene

Pendiente: comandos concretos y sus resultados.

## Consecuencias

Pendiente.

## Alternativas descartadas y por qué

Pendiente.
