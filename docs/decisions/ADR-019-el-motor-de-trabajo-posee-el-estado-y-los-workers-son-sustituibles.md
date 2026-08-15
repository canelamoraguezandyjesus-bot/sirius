# ADR-019 — Diseñar el Motor de Trabajo como software determinista que posee el estado, con Workers sustituibles detrás de Adapters

- Estado: PROPUESTO
- Fecha: 2026-08-15
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario. La fusión
  aprueba el DISEÑO como material de trabajo; NO autoriza implementación, spikes,
  instalaciones ni enmiendas del contrato operativo (esas decisiones quedan listadas en la
  sección Consecuencias). Numeración: ADR-017 y ADR-018 están tomados por la rama
  `feat/investigador-por-etiqueta` (PR #171, sin fusionar); 019 es el primer libre.

## Contexto y problema

La incidencia #172 (SIRIUS-WORK-ENGINE-DESIGN-001) encarga la arquitectura mínima de un
sistema de trabajo autónomo: el propietario expresa una intención una vez y recibe un
resultado terminado, sin actuar de mensajero entre chats, GitHub, Workers y documentos.

El estado real del repositorio (inventario en
`docs/implementation/SIRIUS_WORK_ENGINE_INVENTARIO.md`): existe una máquina de estados de
trabajo completa por etiquetas sobre GitHub, con Claude Code como Worker real en tres roles,
revisión dual opcional con Codex, política de convergencia y red de seguridad — pero el
único estado del trabajo son etiquetas y comentarios de GitHub, el observador del ciclo
vive dentro de lo observado, y la propia automatización dejó escrito su defecto estructural:
«un proceso que muere no puede informar de su propia muerte […] solo lo cierra un observador
EXTERNO, y el contrato operativo prohíbe hoy programarlo. Queda registrado como decisión
pendiente» (`.github/workflows/repair-sirius-work.yml:67-81`). No existe ningún modelo
persistido de Work Item ni de Run en el código (`src/sirius/adapters/persistence/models.py`,
14 migraciones: comprobado), ni contrato de Worker, ni capacidad de investigación, ni
interfaz sustituible.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la nota de arranque de la sesión (comentario en #172, 2026-08-15, antes del
primer commit): (1) contradicción material con una decisión canónica vigente → esa rama del
diseño se detiene y se presenta con evidencia, sin adaptación silenciosa; (2) máximo dos
rondas de revisión interna del borrador; dos rondas con defectos de la misma familia →
parar y buscar la raíz; (3) lo que exija diseñar fuera de los Puntos 1–4 de #172 se
registra como incógnita/spike, no se resuelve por intuición; (4) terminado cuando las
preguntas de #172 §11 tienen respuesta inequívoca o spike asignado, con el menor número
razonable de documentos.

## Opciones consideradas

1. **Evolucionar la automatización GitHub actual hasta que sea el motor** (más workflows,
   más reconciliación): descartada — el defecto es estructural, no de cantidad: el
   observador seguiría dentro de lo observado, y GitHub seguiría siendo la única memoria.
2. **Adoptar un framework de orquestación de agentes** (LangGraph, AutoGen, Hermes…):
   descartada — #172 §4.5/§4.7/§8 lo excluye; ninguna incógnita actual lo necesita; el
   estado y el ciclo deben ser propiedad de Sirius.
3. **Un Coordinator/Planner Agent que gobierne el ciclo**: descartada — #172 §2.8 lo
   prohíbe; la matriz de agentes ya descartó AG-06 («capa nueva → familia nueva de
   defectos»); persistencia, reintentos y transiciones son software determinista.
4. **Motor determinista propiedad de Sirius + Workers sustituibles tras Adapters,
   reutilizando la automatización existente como primer Adapter**: elegida.

## Decisión

Diseñar (no implementar) el sistema de trabajo así — arquitectura completa en
`docs/implementation/SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md`:

1. **El Motor de Trabajo es software determinista de Sirius** y posee: WorkItem durable,
   máquina de estados (con WAITING, retry, LOST, pause/resume, cancelación, cambio de
   alcance, sustitución de Worker), supervisor externo con cotas absolutas, despachador,
   Capability Resolver, permisos, presupuesto, escalado y diario de evidencia. Su almacén
   es propio, separado del producto 0.1 y vive **detrás de un puerto de persistencia**; la
   representación física NO se decide aquí: la decide el resultado de I3/I4 (el spike
   puede usar SQLite sin convertirlo en decisión). El despliegue del motor exige
   supervisión y reinicio automático externos (servicio del SO o equivalente): el
   propietario no es el detector rutinario de su caída.
2. **Los Workers son temporales y sustituibles** tras el contrato conceptual
   `START/STATUS/RESULT/CANCEL`, con `WorkPackage`/`WorkResult` como E/S. El Worker
   informa; el motor aplica. La cancelación es en dos tiempos: un Run solo queda
   `CANCELLED` con estado terminal remoto o aislamiento demostrado; hasta entonces
   (`CANCELLATION_UNCONFIRMED`) el supervisor lo sigue reconciliando y nada nuevo se
   despacha sobre el mismo recurso mutable. Todo Adapter aplica una **proyección
   determinista** `WorkPackage + AgentProfileRef(version/hash) + capacidades resueltas +
   permisos + esquema de salida → WorkerRequest`, que queda en la evidencia (o su hash y
   versiones, sin secretos); el Worker no reinterpreta alcance, permisos ni criterios de
   aceptación.
3. **La automatización GitHub existente es el primer Adapter de Claude Code**, no una vía a
   sustituir ni a duplicar: etiquetas y marcadores son su protocolo; los scripts
   deterministas, el contrato de observación y la convergencia se conservan.
4. **Codex sigue entrando por la revisión dual de GitHub** como Worker-revisor;
   `sirius_codex_review.py` ya es su Adapter.
5. **GPT Researcher entra tras Adapter con frontera mecánica `ExportSafeBrief`**, bajo una
   **política global de egress del motor**: red externa y acceso irrestricto al contexto
   privado son incompatibles en el Capability Resolver para TODO Worker (fail-closed antes
   de `START`); cada fragmento exportado lleva procedencia y clasificación según política
   versionada o decisión registrada del propietario; un modelo puede redactar el brief,
   nunca autorizarlo. El Investigador de la PR #171 (repo privado + web) queda como
   prototipo/evidencia del carril por etiqueta, fuera de esta arquitectura.
6. **Los Agent Profiles son documentos versionados neutrales al motor** (molde: Auditor
   v0); las capacidades abstractas se resuelven por un registro versionado (Resolver),
   nunca nombrando herramientas en el perfil. El Resolver jamás delega Worker→Worker por
   su cuenta: una capacidad que exige otro Worker devuelve un requerimiento y el motor
   crea un paso/Run hijo de primera clase.
7. **Las interfaces son adaptadores sin estado** (Telegram el primero, sin instalar aún).
8. **La intención se expresa una vez**: una orden explícita e inequívoca del propietario
   crea y activa el WorkItem directamente (la orden ya es la autorización que exige el
   contrato); la ambigüedad pregunta o no crea; solo lo sensible/material (gasto,
   permisos, destructivo, privacidad) exige confirmación o escalado adicional.
9. Las **contradicciones materiales** quedan presentadas con evidencia y DETENIDAS en la
   arquitectura §14; ninguna se resuelve aquí: C1 (activación por máquina, prohibida por
   el contrato §9.1 — conflicto de autorización de implementación, no del diseño), C2
   (vigilancia periódica como motor, prohibida por §9 — enmienda previa a implementar),
   C3 («diseñar arquitectura multiagente» no autorizado en evolución/STATUS frente a la
   orden posterior de #172 — RESUELTA por la PR #174, fusionada el 15-08-2026: la
   excepción de diseño quedó registrada en `docs/evolution/STATUS.md`), C5 (la
   incidencia como fuente de verdad del contrato §2: la dirección la decidió #172 §1.3 y
   lo pendiente es la migración y la enmienda). C4 fue formulada como contradicción con
   ADR-016 y RETIRADA en la primera auditoría: ADR-016 declara «No cambia nada del ciclo
   de programación» (líneas 146-148); queda como lección de mínimo privilegio.

## Comprobación que la sostiene

- Inspección del estado real con evidencia por ruta y línea:
  `docs/implementation/SIRIUS_WORK_ENGINE_INVENTARIO.md` (14 workflows, 9 scripts, 3
  prompts, plantilla, ADR-001..016, PR #171 por API, `src/sirius/` y migraciones, incidencias
  #126/#133/#148/#154/#165/#167 leídas).
- Citas determinantes reverificadas literalmente en el árbol antes de redactar: el descargo
  de durabilidad (`repair-sirius-work.yml:67-81`), el §9/§9.1 del contrato
  (`AUTOMATION_OPERATING_CONTRACT.md`), el «No autorizado todavía» de
  `docs/evolution/STATUS.md`, y la lista de ramas remotas para la numeración de ADRs
  (`git ls-remote`: `feat/investigador-por-etiqueta` presente).
- Ausencia de modelo de trabajo persistido comprobada por dos vías (los 12 modelos de
  `models.py`; todas las `op.create_table` de `migrations/versions/`).
- Lo NO verificable desde el árbol está marcado NO VERIFICADO en ambos documentos
  (secretos, variables como `SIRIUS_CODEX_REVIEW_ENABLED`, runs reales, productos externos).
- **Primera auditoría adversarial del propietario (2026-08-15, método de #172 §10)**:
  veredicto NO APTO con 1 hallazgo bloqueante (B1, frontera de privacidad no cerrada
  universalmente), 5 graves (G1 confirmación doble, G2 proyección WorkerRequest ausente,
  G3 delegación oculta en el Resolver, G4 cancelación no confirmada tratada como terminal,
  G5 caída del motor detectada por el propietario) y 2 menores (M1 SQLite prematuro, M2 C4
  mal formulada — verificada contra `ADR-016:146-148` antes de aceptarla). Los ocho se
  corrigieron sobre la misma PR #173 en este documento y en la arquitectura, sin rediseñar
  el chasis.
- **Segunda auditoría corta del propietario (2026-08-15, sobre `3829cd4`)**: veredicto
  **APTO CON CORRECCIONES** — los ocho hallazgos (B1, G1–G5, M1–M2) CERRADOS; residual
  menor puramente documental (una frase del adapter de Telegram y la descripción de la
  PR), saneado en `0cf1588`. Consecuencia registrada por el auditor: C3 seguía siendo
  precondición para aprobar/fusionar; quedó satisfecha después por la PR #174.

## Consecuencias

- Queda un diseño que responde las preguntas de aceptación de #172 §11 (arquitectura §13)
  y aísla seis incógnitas con spike mínimo (§15), sin código productivo, sin fusionar #171
  y sin tocar canónicos.
- **Decisiones que quedan en manos del propietario** (ninguna se toma aquí): resolver
  C1, C2 y C5 enmendando el contrato al autorizar la implementación (la reconciliación
  documental de C3 quedó SATISFECHA por la PR #174, fusionada el 15-08-2026);
  decidir el destino de la PR #171 (este diseño no la necesita fusionada ni
  rechazada); autorizar los spikes I1–I3 (I2 mide el coste real de GPT Researcher — hoy NO
  VERIFICADO — y solo si la opción elegida exige gasto se escala por presupuesto); aportar
  el dato I5 (valor de `SIRIUS_CODEX_REVIEW_ENABLED`) y la decisión I4 (dónde corre el
  motor, con supervisión y reinicio automático externos como requisito del despliegue).
- Tras la aprobación explícita del diseño (método de #172 §10), y solo entonces, se
  escribirá el plan de implementación.

## Alternativas descartadas y por qué

Las opciones 1–3 de arriba, con sus motivos. Además: convertir MCP en la arquitectura
(#172 §4.4: es un transporte posible, no el chasis); introducir A2A u otro protocolo de
agentes por existir (#172 §4.5); resolver C1–C3 «adaptando» el diseño en silencio —
prohibido por #172 §12 y por la disciplina de evidencia: una contradicción con una decisión
vigente se presenta y se detiene, no se rodea.
