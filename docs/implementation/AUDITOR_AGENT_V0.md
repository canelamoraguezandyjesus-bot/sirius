# AUDITOR AGENT v0 — Especificación operativa del primer piloto

- **Estado:** PREPARADO, NO LANZADO. Nada de este documento se ejecuta hasta que el propietario fusione la PR que lo introduce (aprobación de ADR-008) y ordene el primer run.
- **Fecha:** 12 de agosto de 2026
- **Decisión que lo autoriza:** [`ADR-008`](../decisions/ADR-008-auditor-agent-v0-como-primer-piloto.md) (PROPUESTO; se aprueba con la fusión).
- **Base:** auditoría de procesos Fase 0 ([`WORK_PROCESS_AUDIT.md`](WORK_PROCESS_AUDIT.md), [`AGENT_OPPORTUNITY_MATRIX.md`](AGENT_OPPORTUNITY_MATRIX.md)) y handoff del propietario del 12-08-2026.

## Nota de arranque de esta preparación

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo que el piloto ataca: defectos reales que sobreviven a pruebas, revisiones y automatización. El arreglo de ESTA fase es solo preparación (este documento + ADR-008). ¿Puede el auditor observar lo que audita? Sí: todo su objeto (código, tests, docs, workflows, historial, issues) es legible desde su perfil de solo lectura. Lo que NO puede observar: comportamiento en Windows real y con proveedor real — debe declararlo, no inferirlo.
2. **Qué NO garantiza:** que existan hallazgos (un informe vacío honesto es un resultado válido); que los hallazgos cubran todo el repositorio (la cobertura se declara); que un hallazgo confirmado sea corregible dentro del alcance aprobado.
3. **Criterio de parada:** el de ADR-008 (falso positivo grave con alta confianza → parar; dos ejecuciones con defectos del mismo tipo en el método → revisar el diseño; supervisión más cara que el valor → parar).
4. **¿Qué haría el fallo imposible?** Nada hace imposible que un modelo afirme más de lo que el dato sostiene; por eso el formato de hallazgo OBLIGA a evidencia + refutación y el criterio de fracaso es de tolerancia cero al falso positivo confiado.

## 1. Misión (texto de la primera ejecución)

> Audita Sirius de extremo a extremo **sin modificar nada**, sobre el commit
> `<HEAD de main fijado al lanzar>`. Busca defectos funcionales, contradicciones
> entre código, tests, documentación, ADR y contratos, pruebas vacuas o poco
> representativas, estados imposibles o bloqueables, fuentes de verdad
> duplicadas, problemas de idempotencia y concurrencia en la automatización, y
> fallos que puedan escapar de CI (diferencias Linux/Windows incluidas). No
> incluyas un hallazgo si no puedes aportar evidencia concreta (archivo:líneas,
> commit, run, reproducción) y no has intentado refutarlo primero. Prioriza
> problemas reales y demostrables sobre sugerencias de estilo; pocos hallazgos
> sólidos valen más que muchas opiniones. Separa hechos, inferencias e
> incertidumbre. Declara qué áreas inspeccionaste y cuáles no. Produce
> únicamente el informe estructurado FINDING-### y el registro de métricas; no
> implementes correcciones, ni siquiera triviales.

Qué busca, por categorías (del handoff §4; ninguna es opcional):

- **A. Código y tests:** errores lógicos; estados imposibles; carreras y
  concurrencia; excepciones silenciadas; caminos relevantes sin cubrir; mocks
  poco representativos; tests que aparentan garantizar lo que no garantizan
  (candidatos a mutación); diferencias Linux/Windows; fallos irreproducibles en
  CI; permisos/seguridad; código muerto con comportamiento obsoleto; supuestos
  sin proteger; idempotencia y carreras entre eventos/workflows.
- **B. Arquitectura y contratos:** supuestos incompatibles entre componentes;
  implementación que viola el contrato operativo; ADR vigentes que el código no
  respeta; fuentes de verdad duplicadas; estados que pueden quedar bloqueados;
  invariantes documentadas sin protección; divergencia scripts/workflows/
  contratos; comportamiento real distinto del declarado; mecanismos redundantes
  que compiten.
- **C. Documentación:** documentación de comportamiento inexistente;
  funcionalidad sin documentar; documentos vigentes contradictorios; ADR
  obsoletos o mal marcados; referencias rotas; instrucciones que ya no
  funcionan; cifras/versiones/conteos caducados; evidencia declarada sin
  correspondencia con la real; gobernanza fósil.

## 2. Permisos exactos (v0)

| Capacidad | v0 |
|---|---|
| Leer repositorio, historial git, issues/PRs/comentarios, runs y logs de Actions | Sí |
| Ejecutar análisis y pruebas seguras (ruff, mypy, pytest, greps; nada que escriba fuera de directorios temporales) | Sí, si el entorno lo permite |
| WebSearch / WebFetch | **No** |
| Editar código o documentación; commit; push; merge | **No** |
| Cambiar etiquetas, issues, workflows, settings | **No** |
| Secretos | **No** |

Mecanismo: sesión de Claude Code (cloud o local) bajo el perfil vigente del
repositorio, **sin usar** sus capacidades de escritura. No se cambia
`.claude/settings.json`; la restricción de escritura en v0 es de procedimiento
(este runbook + verificación del propietario de que el árbol quedó intacto),
no una garantía mecánica — decirlo es obligatorio (disciplina ADR-001: lo que
ata es publicar el criterio, no una puerta). No se amplía ningún permiso para
facilitar el piloto.

## 3. Runbook del run

1. **Fijar el objetivo:** anotar el commit exacto de `main` a auditar; todo el run se refiere a ese commit.
2. **Cargar contexto obligatorio:** `AGENTS.md`, `CLAUDE.md`, skill `disciplina-evidencia`, `docs/canonical/STATUS.md`, `PLAN.md`, `V8_EXECUTION.md`, `REPOSITORY_STATUS.md`, `AUTOMATION_OPERATING_CONTRACT.md`, ADR-001…008.
3. **Barrido por áreas** (A, B, C de §1), dejando constancia de qué se inspecciona y qué no. Cobertura mínima del primer run: `src/` y `tests/` completos por módulos, `scripts/automation/` + `.github/workflows/`, y el corpus documental vigente.
4. **Verificación de cada candidato a hallazgo:** reproducir o demostrar contra el código/commit; comprobar que no es un duplicado de algo ya conocido (issues abiertas, patrones.md, hallazgos de PRs); ejecutar la comprobación que lo sostiene.
5. **Refutación obligatoria:** para cada candidato, intentar demostrarlo falso (¿hay una guarda que no vi? ¿el test sí cubre el caso? ¿el contrato lo permite?). Registrar qué se comprobó y por qué sigue en pie.
6. **Informe:** hallazgos FINDING-### ordenados por gravedad + secciones «Áreas no inspeccionadas», «Duplicados/conocidos descartados» y «Qué no demuestra este informe».
7. **Métricas:** registro del run (§5).
8. **Entrega:** el informe se publica como comentario/archivo que el propietario recibe; en v0 el auditor no escribe en el repositorio — la incorporación del informe (si se desea versionar) la hace el flujo normal con revisión.

Presupuesto del run: EST ≤3 h de sesión y ≤ coste equivalente a las sesiones actuales; si el presupuesto se agota, se entrega lo verificado y se declara el corte (nunca un informe con apariencia de completo).

## 4. Formato obligatorio de hallazgo

```text
FINDING-###
Gravedad: P0 / P1 / P2 / P3
Tipo: Bug / Test / Arquitectura / Contrato / Automatización / Documentación / Seguridad / Rendimiento / Otro
Afirmación: qué está mal exactamente.
Evidencia: archivos + líneas / commit / issue / PR / run / prueba / reproducción.
Comportamiento esperado: qué debería ocurrir y por qué (con la fuente normativa).
Comportamiento real: qué ocurre.
Reproducción o demostración: pasos o prueba mínima.
Impacto: qué puede romper, degradar o confundir.
Confianza: Alta / Media / Baja.
Intento de refutación: qué se comprobó para demostrar que la hipótesis era falsa.
Resultado de la refutación: por qué el hallazgo sigue en pie.
Acción: Corregir / Necesita decisión / Documentar / Investigar más.
No demostrado: qué NO permite concluir la evidencia.
```

**Regla central:** un hallazgo sin evidencia concreta o sin intento de
refutación **no llega al informe final**. Pocos hallazgos sólidos > muchas
opiniones vagas.

## 5. Métricas por ejecución

Registro por run (en `docs/implementation/agent_runs/AUDIT-RUN-NNN.md`, incorporado por el flujo normal): run id; agente (`auditor-v0`); misión; modelo exacto; proveedor; commit auditado; duración; turnos; tokens in/out; llamadas al modelo; tool calls; comandos/pruebas ejecutados; áreas inspeccionadas y no inspeccionadas; errores/reintentos; coste; hallazgos totales / confirmados por el propietario / falsos positivos / duplicados-conocidos / nuevos; severidades; intervención humana requerida (minutos EST del propietario). **No se inventan métricas:** lo no observable se registra como `unknown`.

## 6. Criterios de éxito y de fracaso

Éxito del run 1 (todos):
1. Cero modificaciones del repositorio y cero acciones irreversibles.
2. Cada hallazgo final con evidencia verificable y refutación intentada.
3. Hechos / inferencias / incertidumbre separados.
4. Otro humano o modelo puede verificar cada hallazgo sin reconstruir la investigación.
5. Métricas suficientes para comparar ejecuciones posteriores.
6. El coste de supervisión del propietario no supera el valor producido (él lo juzga y queda registrado).

Fracaso / parada (cualquiera):
- **Un falso positivo grave presentado con confianza Alta** → parar el piloto y analizar el método antes de aumentar autonomía (ADR-008).
- Dos ejecuciones seguidas con defectos de la misma familia en el método del auditor → regla de las dos rondas sobre el diseño.
- Cualquier modificación del repositorio durante un run → parar de inmediato.

## 7. Rollback

Dejar de lanzarlo. Un run no deja estado en el repositorio (solo lectura); sus informes y métricas se conservan como evidencia histórica. No hay nada que revertir en settings, workflows ni permisos, porque nada de eso se toca.

## 8. Work item del piloto (listo para crear tras la aprobación)

Se creará como **issue normal, sin plantilla de work item y sin ninguna etiqueta `sirius:`** (un run del auditor no entra en la máquina de estados de la tubería; usar la plantilla aplicaría `sirius:planned` y contaminaría la automatización). Cuerpo preparado:

```markdown
# AUDITOR-V0-RUN-001 — Primera auditoría de extremo a extremo (solo lectura)

**Autoriza:** ADR-008 (aprobado con la fusión de la PR que lo introdujo).
**Especificación:** docs/implementation/AUDITOR_AGENT_V0.md (runbook, formato
FINDING-###, métricas, criterios y rollback; este issue no los duplica).

- Commit a auditar: `<fijar al lanzar: HEAD de main>`
- Misión: la de AUDITOR_AGENT_V0.md §1, literal.
- Permisos: solo lectura estricta (§2). Sin web. Sin escritura, push, merge,
  etiquetas ni secretos. El auditor NO corrige nada, ni siquiera trivial.
- Entregables: informe FINDING-### + registro de métricas del run
  (unknown donde no sea observable) + declaración de áreas no inspeccionadas.
- Criterio de parada del piloto: un falso positivo grave con confianza Alta
  detiene el experimento (ADR-008).
- Seguimiento: los resultados y la evaluación del propietario (confirmados /
  falsos positivos / minutos de supervisión) se registran en comentarios de
  esta issue.
```

## 9. Qué queda explícitamente fuera de esta fase

No modificar producto Sirius; no reabrir la memoria sin evidencia nueva; no habilitar web al Builder ni al Auditor v0; no introducir secretos; no dar push/merge al auditor; no construir routing multimodelo ni plataforma; no instalar frameworks; no automatizar decisiones estratégicas; no permitir que el auditor arregle sus hallazgos; no sacrificar trazabilidad por autonomía. La comparación multimodelo (NVIDIA NIM/Nemotron incluida) llega DESPUÉS: repetir esta misma misión sobre el mismo commit con otros modelos usando como mucho la abstracción mínima `{provider, base_url, model, api_key}` — nunca como requisito de v0.

## 10. Pasos siguientes (en orden)

1. El propietario revisa la PR que introduce este documento + ADR-008 y, si está conforme, la fusiona (= aprobación formal).
2. Crear la issue AUDITOR-V0-RUN-001 con el cuerpo de §8 y el commit fijado.
3. Lanzar el run 1 en sesión de Claude Code con la misión de §1.
4. El propietario evalúa hallazgos (confirmados/falsos) y registra su veredicto en la issue; las métricas entran por PR normal.
5. Con el resultado: continuar (runs comparativos con otros modelos), ajustar el método, o parar según §6.
