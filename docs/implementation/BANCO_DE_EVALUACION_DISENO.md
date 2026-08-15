# Banco de evaluación de agentes — diseño v0

- **Estado:** DISEÑO. Este documento no introduce dependencias, código ni
  gasto. Lo que autoriza a implementarlo es ADR-018 más las decisiones del
  propietario que el §6 deja explícitas.
- **Encargo:** reconciliación de la línea de agentes (15-08-2026). La pregunta
  que este banco debe poder responder, en palabras del propietario: *«Bajo el
  mismo agente, las mismas herramientas y los mismos casos, A produjo X y B
  produjo Y»* — nunca «Claude parecía mejor».
- **Base ya vigente:** `AUDITOR_AGENT_V0.md` §0 (RUN-001 es calibración, no
  línea base), §2b (contrato portable de herramientas), §5 (métricas), §6
  (rúbrica y clave de respuestas), §10 (las tres puertas del multimodelo);
  `AGENT_OPPORTUNITY_MATRIX.md` AG-07 (router pospuesto sin libro mayor);
  `BLOQUE_B_SUSCRIPCIONES_O_CLAVES.md` (qué credencial tiene cada motor).

## 1. Qué pregunta responde (y cuál no)

Responde, POR AGENTE: ¿qué motor ejecuta mejor **el mismo** Auditor?, ¿y el
mismo Investigador? No responde «qué modelo es mejor» en abstracto: eso es
medir el arnés y llamarlo modelo (`AUDITOR_AGENT_V0.md` §0).

## 2. Las tres puertas de ADR-010/§10, con su estado REAL a 15-08

| Puerta | Estado | Evidencia |
|---|---|---|
| Superficie §2b estable entre dos runs consecutivos | **NO cumplida** | RUN-001 (sesión: subagentes, ejecución, GitHub) y RUN-002 (desatendido: lectura estática, sin GitHub) corrieron con superficies distintas — #154 y #167. El arreglo del Auditor de esta misma PR alinea el workflow con §2b; la puerta se cumple cuando dos runs desatendidos consecutivos declaren la misma superficie |
| Clave de respuestas existente | **NO cumplida — hueco encontrado esta noche** | `AUDITOR_AGENT_V0.md` §6 la exige «versionada después del run»; no existe en `docs/` (grep 15-08). Existe una semilla ejecutable: `scripts/verificar_hallazgos.ps1`, 4 casos con commits fijados | 
| Tasa de confirmados que justifique el coste | Favorable, sin libro mayor formal | RUN-001: 4/4 graves reales, 0 falsos positivos (#154). RUN-002: FINDING-001 real y corregido (#167, #169) |

## 3. El evaluador: Inspect AI, y por qué

Las capas, con los nombres de la reconciliación: el **AGENTE** es el runbook y
su contrato §2b (de Sirius, estable); el **EVALUADOR** es quien ejecuta el
mismo agente bajo condiciones controladas y guarda registros comparables; los
**MOTORES** son intercambiables debajo.

Inspect AI encaja como evaluador por hechos medidos, no por fe:

- El MECANISMO de autenticación por suscripción de Claude está verificado en
  el Bloque B (`ANTHROPIC_AUTH_TOKEN`, cabecera OAuth en `anthropic.py:380-394`
  de inspect-ai 0.3.258, handshake probado con token falso → 401). Lo que el
  Bloque B declara NO demostrado: que un token de suscripción VÁLIDO pase la
  política del servidor — esa es exactamente la prueba de 5 minutos en Windows
  del propietario, la primera con token real, no un flequillo de plataforma.
- Trae Tasks, agentes, herramientas, scorers, límites de coste/tiempo/turnos y
  transcripciones: exactamente el «libro mayor de ejecuciones» (PROC-021) cuya
  ausencia tiene pospuesto al router AG-07.
- Ejecuta la MISMA tarea contra varios proveedores, incluidos modelos locales
  sin credencial.

Lo que Inspect NO trae: el Auditor ni el Investigador de Sirius. La misión, el
runbook, el esquema de hallazgo y la rúbrica son nuestros y ya existen. Inspect
es el arnés de medida, no el agente. Hermes queda fuera de esta línea: es un
runtime operativo generalista, no un marco de evaluación; se reconsiderará solo
si un futuro «Sirius operador» demuestra una ventaja concreta que Inspect más
un runtime simple no cubran.

**Dónde vive:** fuera de este repositorio (recomendación: repositorio hermano
`sirius-lab`), por la misma regla que dejó el código de agentes fuera de
`src/sirius/` (`AGENTES_SUPERFICIE_DE_INVOCACION.md` §3: «un repositorio aparte
si crece» — un laboratorio con datasets, logs y entornos crece seguro). Sirius
conserva la DEFINICIÓN de los agentes; el laboratorio los consume leyéndolos.

## 4. Banco dorado del Auditor

**Principio (§6 del runbook, intacto):** la clave no vive en el árbol auditado
y no aparece en la misión. La primera formulación de esta regla («el caso
apunta a un commit anterior a la clave») era INSUFICIENTE y la refutación la
tumbó: los casos dorados son commits de ESTE repositorio, y un checkout con
historia completa deja leer el futuro por `git log --all` / `git show` — los
mensajes de commit posteriores describen literalmente los defectos (el de
`a22eab0` cuenta el FINDING-001), y las propias correcciones son la clave.
Reglas operativas que SÍ lo garantizan, las dos a la vez:

1. **La clave y la definición de los casos viven SOLO en el laboratorio**
   (`sirius-lab`); jamás se fusionan a `sirius`.
2. **El agente evaluado recibe un árbol SIN futuro:** o `git archive` del
   commit base (sin `.git` — y la superficie declara `leer_historial_git` como
   no disponible en ese run), o un clon truncado donde se borran todas las
   refs posteriores al commit base (`reflog expire` + `gc --prune=now`), de
   modo que el historial alcanzable termine en el caso. La MISMA forma para
   todos los motores del mismo caso: si no, la diferencia medida sería el
   arnés, no el modelo (§0 del runbook).

**Composición inicial propuesta (todo con oráculo verificable):**

| Caso | Defecto conocido | Commit base | Oráculo |
|---|---|---|---|
| CASO-01…04 | Los 4 hallazgos graves de RUN-001 | `fcc3e17` / `0dcd48e` / `cdd103d` (fijados) | `scripts/verificar_hallazgos.ps1` ya los clasifica por código de salida de pytest |
| CASO-05 | FINDING-001 de RUN-002: huella sin `--ignored=matching` | commit anterior a la PR #169 | grep de la línea de captura |
| CASO-06… | Sostenidos de RUN-001 con commit-base identificable (12 candidatos en #154) | a fijar | presencia del defecto en el commit, verificada al construir el caso |

Meta inicial: **≥ 8 casos**. Cada caso registra: commit, ruta:líneas, categoría
(A/B/C del runbook §1), gravedad esperada, cómo verificar su presencia.

**Protocolo por comparación:** mismo commit objetivo; misma misión literal
(§1); misma superficie de herramientas (las tools del evaluador implementan
§2b: `listar_ficheros`, `leer_fichero`, `buscar_contenido`,
`ejecutar_solo_lectura`, `leer_historial_git`, `leer_github`); mismos límites
declarados; **N = 3 repeticiones por motor** (la varianza entre repeticiones se
publica junto a la media: un motor inestable no se tapa con su mejor run).

**Métricas por run** — las once del encargo del propietario, mapeadas a lo que
el runbook ya define:

| Métrica pedida | Cómo se mide |
|---|---|
| Defectos conocidos encontrados | recall contra la clave |
| Defectos nuevos confirmados | categoría Confirmado (§6) ∧ fuera de la clave, confirmación humana |
| Falsos positivos | categoría Falso positivo (§6); un grave con confianza Alta sigue siendo parada (ADR-010) |
| Severidades incorrectas | `gravedad` emitida vs gravedad de la clave |
| Evidencia incorrecta | cada `evidencia` se abre: ¿existe la ruta:líneas y sostiene la afirmación? |
| Cobertura inspeccionada | áreas declaradas vs cobertura mínima del runbook §3 |
| Intentos de refutación | `intento_refutacion` no vacío y real (muestreo humano) |
| Cumplimiento de permisos | huella del árbol + transcripción de tool calls del evaluador |
| Tiempo / tokens / tool calls / coste | conjunto ampliado §5; `unknown` si el motor no lo expone — nunca inventado |
| Supervisión humana | minutos del propietario, registrados por él |

**Puntuación:** automática contra la clave (recall, falsos positivos sobre
casos conocidos); cola humana SOLO para candidatos nuevos. Esto ataca de frente
el hueco «quién puntúa» que la matriz dejó señalado: el propietario juzga lo
nuevo, nunca re-verifica lo conocido.

**Boceto de Task (pseudocódigo, sin dependencia):**

```text
task auditor_bank:
  dataset: [ {commit, mision_literal_§1, clave_oculta} × casos ]
  solver:  agente ReAct con tools = contrato §2b sobre checkout(commit) de solo lectura
  limits:  tiempo, tokens, mensajes — declarados en el registro del run
  scorer:  recall_contra_clave + candidatos_nuevos_a_cola_humana
  log:     transcripcion completa → libro mayor (PROC-021)
```

## 5. Banco del Investigador

Naturaleza distinta: no hay defectos plantados, hay **preguntas cuya verdad y
fuentes primarias se conocen ANTES de preguntar**. El evaluador conoce las
fuentes esperadas; el agente no las recibe.

**Semillas concretas ya disponibles:**

1. La pregunta del Bloque B («¿sirve `ANTHROPIC_AUTH_TOKEN` para el proveedor
   anthropic de Inspect?») — respuesta medida, fuente primaria conocida
   (`anthropic.py:380-394`) y trampa natural: abundante material secundario
   confuso.
2. Preguntas de documentación oficial verificable (permisos de GitHub Actions,
   sintaxis de permisos de herramientas de Claude Code): fuente primaria única
   y estable.
3. Una pregunta histórica del propio repositorio con respuesta en ADR (mide el
   paso 2 del runbook: contexto del repo antes de investigar fuera).

**Métricas por run:**

| Métrica | Cómo se mide |
|---|---|
| Cobertura factual | hechos clave presentes / esperados por la clave de la pregunta |
| Fuentes inventadas | cada URL citada se abre: ¿existe y dice lo que el informe le atribuye? |
| Calibración de confianza | afirmaciones etiquetadas «comprobado» que de verdad lo están |
| Contraargumento buscado | ¿existe la sección EN CONTRA con fuente, o la constancia de búsqueda vacía? |
| Omisiones | hechos conocidos de la clave ausentes del informe |
| Calidad de síntesis | juicio del propietario 1-5 con rúbrica corta (¿decidiría solo con esto?) |
| Confidencialidad | transcripción de consultas: ¿salió texto del repositorio en alguna? (ADR-017) |

## 6. Motores y credenciales — estado medido, no supuesto

| Motor | Credencial | Estado |
|---|---|---|
| Claude (suscripción) | `CLAUDE_CODE_OAUTH_TOKEN` hoy en workflows; `ANTHROPIC_AUTH_TOKEN` en Inspect | Verificado (Bloque B); pendiente prueba 5 min Windows — **propietario** |
| Modelos locales (ollama / llama_cpp / hf) | Ninguna | Disponibles a coste cero: **segundo motor natural** para estrenar la comparación |
| OpenAI / GPT | `OPENAI_API_KEY` de pago por uso | **Decisión de gasto del propietario** (Bloque B §6); nada se contrata sin ella |

## 7. Lo que este diseño NO hace

No instala Inspect ni crea el laboratorio (eso llega tras la fusión de ADR-018
y las puertas del §2); no contrata claves; no elige el modelo de ningún agente
— elegir ANTES de medir es exactamente el error que este banco existe para
impedir; y no promete que las tres puertas se cumplan solas: la clave hay que
construirla (§4) y la superficie estable hay que demostrarla con dos runs.
