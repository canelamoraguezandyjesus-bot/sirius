# Reconciliación de la línea de agentes

- **Fecha:** 15 de agosto de 2026 (madrugada).
- **Encargo:** documento de reconciliación del propietario («SIRIUS —
  RECONCILIACIÓN Y AUDITORÍA DE LA LÍNEA DE AGENTES», 15-08) más su orden
  operativa: verificar el mapa, arreglar el Auditor, terminar bien el
  Investigador, y entregar el plan. Nota de arranque publicada en #154 ANTES
  de ver ningún resultado, con criterios de parada.
- **Método:** cada afirmación de este documento se escribió con el fichero o
  la incidencia citada abierta en la misma acción. Las verificaciones las
  hicieron cinco lectores independientes y dos refutadores; los veredictos
  llevan su evidencia al lado.
- **Decisión que lo acompaña:** ADR-018.

## 1. Los cinco conceptos, con los nombres de Sirius

La confusión que el propietario señaló es real y tiene arreglo barato: darle a
cada capa su nombre y su sitio, y no volver a mezclarlas.

| Concepto | Qué es en Sirius | Dónde vive HOY |
|---|---|---|
| **AGENTE** | Misión + runbook + contrato de herramientas + esquema de salida + rúbrica. *«Este documento es el agente»* | `AUDITOR_AGENT_V0.md`, `INVESTIGADOR_AGENT_V0.md` |
| **MODELO** | El cerebro candidato | Hoy Claude (suscripción); candidatos: locales, GPT (con gasto aprobado), Nemotron |
| **RUNTIME / MOTOR** | Lo que deja al modelo usar herramientas | `anthropics/claude-code-action` en los workflows; la sesión de Claude Code en superficie 1 |
| **EVALUADOR** | Quien ejecuta el MISMO agente bajo condiciones comparables y guarda registros | **No existe.** Diseñado esta noche: Inspect AI ([`BANCO_DE_EVALUACION_DISENO.md`](BANCO_DE_EVALUACION_DISENO.md)) |
| **SUPERFICIE DE INVOCACIÓN** | Desde dónde se pide el trabajo | Sesión; etiqueta GitHub; (futuro: Sirius, pospuesto) |

La regla que ordena las capas: **la definición del agente pertenece a Sirius;
modelo y runtime son intercambiables debajo; el evaluador es quien tiene
derecho a compararlos.** Ya estaba escrita (`AUDITOR_AGENT_V0.md:3`); lo que
faltaba era ejecutarla sin excepciones.

## 2. El documento del propietario, verificado afirmación a afirmación

Se verificó contra el árbol y contra GitHub cada afirmación comprobable del
documento de reconciliación. Resultado global: **ningún veredicto FALSA**. El
mapa que trajo el propietario es fiel.

| Afirmación | Veredicto | Evidencia |
|---|---|---|
| El runbook del Auditor dice «el documento es el agente», modelo intercambiable | CIERTA | `AUDITOR_AGENT_V0.md:3` |
| Solo se comparan modelos con la misma superficie de herramientas | CIERTA | `AUDITOR_AGENT_V0.md:13,72` |
| El workflow del Auditor usa claude-code-action, prohíbe subagentes, Bash solo git | CIERTA | `audit-sirius-repository.yml:138,150-152,112` |
| El prompt ordena «sustituye por lectura estática» | CIERTA — instrucción explícita, no solo consecuencia | `audit-sirius-repository.yml:119-120` |
| RUN-001: 8 lentes, verificación adversarial, 16 agentes, 2.428.822 tokens, 815 tool calls, presupuesto agotado a mitad de refutación | CIERTAS las cinco cifras, del run del AUDITOR | #154, comentario 5289523047 (informe y tabla de métricas de RUN-001) |
| RUN-002 declaró que no pudo ejecutar pytest/ruff/mypy ni leer GitHub, y que dejó sin leer gran parte del árbol | CIERTA, con citas textuales | #167, comentario 5297635072 (2 de 152 ficheros de `src/` leídos; 9+ workflows sin abrir; ADR-002…013 sin leer) |
| PR #171 abierta y sin fusionar | CIERTA | head `9f78d12` sobre base `e13a1e3` |
| ADR-017 reconoce que esto no garantiza la calidad de las investigaciones | MATIZADA — lo dice del ADR entero, no de «las pruebas estructurales» | ADR-017:32-34, 99-101 |
| No hay frontera mecánica contra exfiltración por consultas web | CIERTA (y el repositorio es PRIVADO, verificado) | `investigate-sirius-question.yml:155-158`; API: `"private": true` |
| Inspect no es dependencia; los workflows ejecutan Claude Code Action | CIERTA | `pyproject.toml`, `uv.lock` (sin inspect-ai); 5 workflows con la acción |
| Las pruebas reconocen el modelo buscando `anthropics/claude-code-action` | CIERTA | `test_auditor_workflow.py:45` |
| La matriz posponía el router hasta tener libro mayor de ejecuciones | CIERTA | `AGENT_OPPORTUNITY_MATRIX.md:70,113-115` |

## 3. La línea temporal única (qué se quiso, qué se decidió, qué se construyó)

1. **12-08 · Fase 0.** Auditoría de procesos (`WORK_PROCESS_AUDIT.md`,
   `AGENT_OPPORTUNITY_MATRIX.md`): el código ya no era el cuello de botella;
   router multimodelo pospuesto sin libro mayor; nunca un superagente.
2. **12-08 · Handoff.** El propietario elige el primer piloto: Auditor de
   extremo a extremo. ADR-010 (PR #153). Nace `AUDITOR_AGENT_V0.md` con la
   arquitectura correcta YA declarada: documento-como-agente, contrato §2b,
   rúbrica §6, clave de respuestas.
3. **13/14-08 · RUN-001, en sesión.** El Auditor completo: 8 lentes + 8
   verificadores adversariales, 16 agentes, 2.428.822 tokens de subagentes,
   815 tool calls; presupuesto agotado a mitad de refutación (los 5
   verificadores restantes corrieron después). Resultado: 4 hallazgos graves,
   4 defectos reales, 0 falsos positivos (#154).
4. **14-08 · ADR-015.** La refutación de un hallazgo de RUN-001 destapa el
   defecto de las notificaciones; toda escritura de etiqueta pasa a envoltura.
5. **14-08 · ADR-016 + workflow.** Superficie 2: el Auditor por etiqueta, con
   la frontera estructural (el modelo no escribe / quien escribe no ejecuta
   modelo). **Aquí ocurre la desviación:** el workflow entrega una superficie
   MENOR que la del contrato §2b —sin ejecución de comprobaciones, sin lectura
   de GitHub, y un prompt que ordena «lectura estática»— y los documentos
   celebran «Superficie 2 CONSTRUIDA» sin declarar el recorte en términos de
   §2b. No fue mala fe: fue resolver lo desatendido con lo que había. Pero el
   nombre «el Auditor» pasó a designar su adaptador más estrecho.
6. **14-08 · Estreno (RUN-002).** Primer intento: rojo honesto. Segundo:
   informe real que ENCONTRÓ la degradación — FINDING-002 es exactamente «no
   puedo leer GitHub y mi runbook me lo exige» — y un defecto real del arnés
   (FINDING-001, corregido en #169). El propio agente declaró su cobertura:
   2 de 152 ficheros de `src/`, 9+ workflows sin abrir.
7. **15-08 · Bloque B.** Medido: la suscripción de Claude ejecuta agentes hoy
   y tiene camino OAuth verificado en Inspect; ChatGPT Business no sirve para
   runners; OpenAI = clave de pago = decisión del propietario.
8. **15-08 · ADR-017 + PR #171.** El Investigador (web encendida, pregunta por
   entorno, dos superficies). Correcto sobre el molde; sin resolver la
   frontera de confidencialidad (repo privado + web).
9. **15-08 · Esta reconciliación.** El propietario nombra la divergencia; se
   verifica su mapa (§2); se corrige lo corregible esta noche (§5) y se
   planifica el resto (§7).

## 4. Los tres Auditores (la divergencia, con cifras)

| | RUN-001 (sesión) | RUN-002 (etiqueta, antes del arreglo) | Contrato del runbook (§2/§2b) |
|---|---|---|---|
| Lentes / verificación adversarial | 8 lentes + 8 verificadores independientes | Contexto único, sin subagentes | No exigido; «declarar por run» |
| Agentes / tokens / tool calls | 16 · 2.428.822 · 815 | 1 · (no expuesto) · ~decenas | Conjunto ampliado §5: se registra si el motor lo expone |
| ruff/mypy/pytest | Ejecutados | **Prohibidos por el prompt** («lectura estática») | «Sí, si el entorno lo permite» (§2) |
| GitHub (issues/PR/runs) | Leído | **Estructuralmente inaccesible** (FINDING-002) | «Sí» (§2, línea 50) |
| Cobertura de `src/` | Amplia (8 lentes) | 2 de 152 ficheros | Cobertura mínima §3 |
| Resultado | 4 graves, 4 reales, 0 FP | 2 hallazgos (1 real del arnés) | — |

**Conclusión:** el Auditor por etiqueta no era el Auditor: era su versión
estática, y el prompt lo imponía. La corrección de esta noche (ADR-018) alinea
el adaptador con el contrato: **el arnés ejecuta** las cuatro comprobaciones de
CI y vuelca el contexto de GitHub ANTES de la huella, **el modelo los lee** —
sin darle ni una herramienta nueva ni un permiso de escritura. Lo que el modo
desatendido sigue SIN tener — subagentes y verificación adversarial multiagente
— queda declarado en el runbook (§2c) y en cada informe, no disimulado. Esa
capacidad se recupera en el evaluador (§6), que es su sitio.

## 5. Qué se conserva, qué se corrige, qué se degrada, qué se elimina

**Se conserva (y se defiende):** la frontera estructural de ADR-016; el
saneador en todo canal de agente; la huella del árbol por el arnés; mínimo
privilegio por agente; etiquetas fuera del ciclo por prefijo; el contrato §2b;
la rúbrica y la clave §6; el merge siempre humano; «un agente es misión +
contrato + permisos, no una clase de un framework».

**Se corrige esta noche:** el workflow del Auditor (superficie completa por
arnés + declaración §2b + fin de la «lectura estática»); la neutralidad de las
definiciones (los runbooks dejan de nombrar herramientas y motor concretos en
la definición; capacidades en su lugar); la neutralidad de las defensas
(registro cerrado de acciones: una acción de workflow no clasificada pone las
pruebas en rojo; la única referencia a secretos permitida en un paso de modelo
no exento es su credencial registrada); la confidencialidad del Investigador
(regla + extracción mecánica de consultas al comentario); los documentos que
equiparaban adaptador con agente.

**Se degrada a prototipo declarado (sin tocar esta noche):** los tres roles del
ciclo (implement/review/repair) — usan `--dangerously-skip-permissions`,
reciben el PAT por entorno y están exentos por nombre de las pruebas de
agentes. Funcionan y el propietario los aprobó, pero NO son el patrón de la
línea de agentes. Quedan como deuda vigilada en el registro de acciones y en
esta lista, para decidir su convergencia después de 0.1.

**Se elimina:** la instrucción «sustituye por lectura estática» y toda
equiparación entre el Auditor y su adaptador más estrecho. Nada más: no hay
código que borrar, hay nombres que dejar de usar mal.

## 6. Arquitectura objetivo, mapeada a lo que existe

| Capa (del propietario, §9) | Pieza de Sirius | Estado |
|---|---|---|
| 1. Definición de agente | Runbooks (`*_AGENT_V0.md`) | Existe; esta noche se neutraliza el vocabulario |
| 2. Contrato de herramientas | §2b del Auditor; §2 del Investigador | Existe; se generaliza como patrón |
| 3. Adaptador de runtime | Workflows por etiqueta; overlay «Cómo trabajas AQUÍ»; sesión | Existe; esta noche se alinea con el contrato y se registra como capa |
| 4. Evaluación | **Inspect AI** (laboratorio `sirius-lab`, fuera de este repo) | **Diseñado** (`BANCO_DE_EVALUACION_DISENO.md`); implementación tras las puertas |
| 5. Superficie de invocación | Etiquetas + sesión (+ Sirius, pospuesto) | Existe |
| 6. Elección de modelo | Por agente, con datos del evaluador | **Después de medir** — AG-07 sigue pospuesto hasta que el libro mayor exista (los logs de Inspect LO SON) |

## 7. Plan de transición (fases con puertas)

- **F0 — esta noche (hecho).** Reconciliación verificada; Auditor alineado con
  §2b; Investigador con frontera de confidencialidad; defensas neutrales;
  ADR-018; este plan. Coste: 0 € (suscripción + minutos de Actions).
- **F1 — el propietario, al despertar.** (a) Revisar y, si acepta, fusionar la
  PR (la fusión ES la aceptación de los riesgos documentados en ADR-017/018);
  (b) la prueba de 5 minutos en Windows (`BLOQUE_B` §5); (c) la decisión de
  gasto OpenAI — sin prisa: no bloquea F2-F4 (hay motor local gratis).
- **F2 — estrenos calibrados.** RUN-003 del Auditor por etiqueta (con la
  superficie nueva) y estreno del Investigador con la pregunta de la memoria.
  Puerta 1 de §10 del runbook: dos runs consecutivos con la MISMA superficie
  declarada.
- **F3 — la clave de respuestas.** Materializar el banco dorado del Auditor
  (≥8 casos con oráculo; semilla: `verificar_hallazgos.ps1`). Puerta 2.
- **F4 — el laboratorio.** Repositorio `sirius-lab` con Inspect: banco del
  Auditor con Claude (línea base, N=3) y un motor local a coste cero como
  segundo motor. Evalúa la puerta 3 (¿la tasa de confirmados paga el coste?).
- **F5 — elegir modelo POR AGENTE, con datos.** Solo aquí entra el router; y
  GPT solo si su gasto fue aprobado en F1c.

## 8. Lo que esta noche NO hizo (anotado a propósito)

No fusionó nada; no creó un tercer agente; no instaló Inspect ni Hermes; no
contrató claves. No recuperó subagentes ni verificación adversarial en el modo
desatendido — eso no cabe en un contexto único y fingirlo sería repetir el
error; vive en F4. No tocó los tres roles del ciclo (§5, deuda declarada). No
pobló la clave de respuestas (diseñada en el banco; poblarla es una sesión
dedicada de F3). Y no decidió lo que es del propietario: fusión, Windows,
gasto.

## 9. Contradicciones encontradas y cómo se resolvieron (condición §13)

1. **ADR-010: «no se amplía ningún permiso para facilitar el piloto»** vs las
   lecturas de GitHub añadidas al job del modelo del Auditor. Resolución: el
   runbook §2 (línea 50) YA concedía al agente leer issues/PRs/runs; era el
   workflow quien no lo entregaba (FINDING-002 de RUN-002). Se añaden permisos
   de SOLO lectura al job para cumplir el contrato existente, no para ampliar
   el agente. Queda en ADR-018; revocable con revertir la PR.
2. **ADR-016: «Nada de Inspect, ni multimodelo, ni proveedores nuevos»** vs el
   plan del evaluador. Resolución: esa frase describía el alcance de AQUELLA
   decisión (el workflow del Auditor no usa Inspect — y sigue sin usarlo), y su
   condición «bloqueado tras el Bloque B» ya se ejecutó: el Bloque B corrió y
   respondió. ADR-018 autoriza únicamente el DISEÑO del evaluador; la
   dependencia sigue fuera del repositorio hasta F4 y sus puertas.
3. **El encargo de esta noche («arreglar el auditor») vs el §10 del documento
   («NO escribir otro workflow de agentes»).** Resolución: no se crea ningún
   workflow nuevo; se corrige el existente, que es lo que la palabra
   «arreglar» ordena. El Investigador tampoco estrena workflow: se endurece el
   que la PR #171 ya contenía.

Ninguna contradicción exigió parar: las tres se resuelven leyendo la decisión
original completa. Si el propietario no comparte alguna resolución, cada una
tiene su vuelta atrás escrita.
