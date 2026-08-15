# AUDITOR AGENT v0 — Especificación reproducible del agente

- **Naturaleza:** este documento **es el agente**. El modelo que lo ejecuta es una pieza intercambiable. Misión, runbook, superficie de herramientas, formato de salida, límites, métricas y rúbrica de puntuación son independientes del proveedor; el motor (hoy Claude Code) no lo es.
- **Decisión que lo autoriza:** [`ADR-010`](../decisions/ADR-010-auditor-agent-v0-como-primer-piloto.md), aprobado con la fusión de la PR #153 el 2026-08-12.
- **Base:** auditoría de procesos Fase 0 ([`WORK_PROCESS_AUDIT.md`](WORK_PROCESS_AUDIT.md), [`AGENT_OPPORTUNITY_MATRIX.md`](AGENT_OPPORTUNITY_MATRIX.md)) y handoff del propietario del 12-08-2026.

## 0. Qué es y qué no es el primer run

El RUN-001 se ejecuta con Claude Code porque ya existe y no exige infraestructura nueva. Eso obliga a una distinción que, si se borra, contamina todo lo que venga después:

> **El RUN-001 es una calibración del runbook, NO la línea base de un modelo.**

Claude Code aporta su propia superficie de herramientas (búsqueda agéntica, lectura parcial, ejecución de comandos). Un run posterior con otro modelo bajo otro motor tendrá otra superficie. Comparar ambos y atribuir la diferencia al modelo sería medir el arnés y llamarlo modelo — la misma forma que `patrones.md` ya cataloga como «pruebas que dependen del entorno del que las escribe». Una comparación de modelos solo es legítima cuando ambos corren sobre la misma superficie declarada en §2b.

Lo que el RUN-001 sí demuestra o refuta: si esta misión, este runbook y esta disciplina de refutación producen hallazgos reales y verificables, o ruido.

## Nota de arranque de esta preparación

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo que el piloto ataca: defectos reales que sobreviven a pruebas, revisiones y automatización. El arreglo de ESTA fase es solo la especificación (este documento + ADR-010). ¿Puede el auditor observar lo que audita? Sí: código, tests, docs, workflows, historial e issues son legibles desde su perfil de solo lectura. Lo que NO puede observar: comportamiento en Windows real, con proveedor real o con hardware — debe declararlo, nunca inferirlo.
2. **Qué NO garantiza:** que existan hallazgos (un informe vacío honesto es resultado válido); que la cobertura sea total (se declara lo inspeccionado y lo no inspeccionado); que un hallazgo confirmado sea corregible dentro del alcance aprobado; que los resultados sean comparables con otro motor (§0).
3. **Criterio de parada:** el de ADR-010 — un falso positivo grave con confianza Alta detiene el piloto; dos ejecuciones con defectos de la misma familia en el método obligan a revisar el diseño; si supervisar cuesta más que el valor producido, se para y se dice.
4. **¿Qué haría el fallo imposible?** Nada impide que un modelo afirme más de lo que el dato sostiene. Por eso el esquema de salida obliga a evidencia y a refutación por hallazgo, y el criterio de fracaso es de tolerancia cero al falso positivo confiado.

## 1. Misión (texto literal del run)

> Audita Sirius de extremo a extremo **sin modificar nada**, sobre el commit
> `<commit fijado al lanzar>`. Busca defectos funcionales, contradicciones
> entre código, tests, documentación, ADR y contratos, pruebas vacuas o poco
> representativas, estados imposibles o bloqueables, fuentes de verdad
> duplicadas, problemas de idempotencia y concurrencia en la automatización, y
> fallos que puedan escapar de CI (diferencias Linux/Windows incluidas). No
> incluyas un hallazgo si no puedes aportar evidencia concreta (archivo:líneas,
> commit, run, reproducción) y no has intentado refutarlo primero. Prioriza
> problemas reales y demostrables sobre sugerencias de estilo; pocos hallazgos
> sólidos valen más que muchas opiniones. Separa hechos, inferencias e
> incertidumbre. Declara qué áreas inspeccionaste y cuáles no. Produce
> únicamente los hallazgos en el esquema de §4 y el registro de métricas de §5;
> no implementes correcciones, ni siquiera triviales.

Categorías obligatorias (ninguna es opcional):

- **A. Código y tests:** errores lógicos; estados imposibles; carreras y concurrencia; excepciones silenciadas; caminos relevantes sin cubrir; mocks poco representativos; pruebas que aparentan garantizar lo que no garantizan; diferencias Linux/Windows; fallos irreproducibles en CI; permisos y seguridad; código muerto con comportamiento obsoleto; supuestos sin proteger; idempotencia y carreras entre eventos y workflows.
- **B. Arquitectura y contratos:** supuestos incompatibles entre componentes; implementación que viola el contrato operativo; ADR vigentes que el código no respeta; fuentes de verdad duplicadas; estados que pueden quedar bloqueados; invariantes documentadas sin protección; divergencia entre scripts, workflows y contrato; comportamiento real distinto del declarado; mecanismos redundantes que compiten.
- **C. Documentación:** documentación de comportamiento inexistente; funcionalidad sin documentar; documentos vigentes contradictorios; ADR obsoletos o mal marcados; referencias rotas; instrucciones que ya no funcionan; cifras, versiones o conteos caducados; evidencia declarada sin correspondencia con la real; gobernanza fósil.

## 2. Permisos

| Capacidad | v0 |
|---|---|
| Leer repositorio, historial git, issues/PRs/comentarios, runs y logs de Actions | Sí |
| Ejecutar análisis y pruebas seguras (ruff, mypy, pytest, búsquedas) sin escribir fuera de temporales | Sí — cómo la entrega cada superficie, en §2c |
| Búsqueda y lectura web | **No** |
| Editar código o documentación; commit; push; merge | **No** |
| Cambiar etiquetas, issues, workflows, settings | **No** |
| Secretos | **No** |

En v0 la restricción de escritura es **procedimental**, no mecánica: el motor conserva capacidades de escritura y lo que las contiene es este runbook más la verificación de §3. Decirlo es obligatorio (ADR-001: lo que ata es publicar el criterio, no una puerta). La frontera mecánica llega cuando el motor deje de ser Claude Code —un runner propio garantiza «solo lectura» no implementando la herramienta de escritura— y **se vuelve obligatoria** si ocurre cualquiera de estas tres: los runs pasan a desatendidos o programados; el auditor gana acceso web; o un run trabaja sobre una rama que pueda fusionarse. No se amplía ningún permiso para facilitar el piloto y `.claude/settings.json` no se toca.

### 2b. Superficie de herramientas declarada (contrato portable)

Esto es lo que un motor alternativo debe implementar para que su run sea comparable. Es la parte difícil del desacoplamiento entre agente y modelo — no la configuración del proveedor.

| Capacidad | Descripción mínima | Usada en RUN-001 |
|---|---|---|
| `listar_ficheros` | glob por patrón sobre el árbol del commit | sí |
| `leer_fichero` | lectura completa o por rango de líneas | sí |
| `buscar_contenido` | búsqueda por expresión regular con contexto | sí |
| `ejecutar_solo_lectura` | comando que no escribe en el árbol (`git log`, `git show`, linters, pruebas) | declarar por run |
| `leer_historial_git` | log, diff y show sobre commits y ficheros | sí |
| `leer_github` | issues, PRs, comentarios, revisiones, runs de Actions | declarar por run |

Cada run registra qué capacidades usó realmente. Dos runs solo son comparables si su lista coincide; si no coincide, la diferencia se atribuye al arnés antes que al modelo.

### 2c. Cómo entrega cada superficie el contrato de 2b (ADR-018)

El contrato es del AGENTE; **cómo se cumple es del adaptador**, y se declara
aquí para que la diferencia entre superficies nunca vuelva a ser implícita
(la lección de RUN-001 vs RUN-002, medida en
[`RECONCILIACION_LINEA_DE_AGENTES.md`](RECONCILIACION_LINEA_DE_AGENTES.md) §4):

| Capacidad §2b | En sesión (superficie 1) | Por etiqueta (superficie 2, desde ADR-018) |
|---|---|---|
| `listar_ficheros` / `leer_fichero` / `buscar_contenido` | el motor | el motor |
| `leer_historial_git` | el motor | el motor (Bash acotado a `git log/show/diff`) |
| `ejecutar_solo_lectura` | el motor las ejecuta | **el ARNÉS las ejecuta** (los cuatro comandos de CI, antes de la huella) y el modelo LEE salidas y códigos |
| `leer_github` | el motor | **el ARNÉS la vuelca** (listados sin cuerpos + informes previos de auditoría) y el modelo LEE los JSON |
| Subagentes / verificación adversarial multiagente | disponible (así corrió RUN-001) | **NO existe** — se declara en cada informe en «qué no demuestra este informe»; esa capacidad vive en el evaluador ([`BANCO_DE_EVALUACION_DISENO.md`](BANCO_DE_EVALUACION_DISENO.md)) |

Regla: un run que entregue menos que §2b lo DECLARA en el informe y en las
métricas. Un informe que calla un recorte de superficie es un run fallido.

## 3. Runbook

0. **Huella inicial:** registrar `git rev-parse HEAD`, `git status --porcelain` y la lista de ramas locales. Sin esta huella, «cero modificaciones» sería una promesa en vez de una comprobación.
1. **Fijar el objetivo:** anotar el commit exacto a auditar; todo el run se refiere a él.
2. **Cargar contexto normativo:** `AGENTS.md`, `CLAUDE.md`, skill `disciplina-evidencia` y `patrones.md`, `docs/canonical/STATUS.md`, `PLAN.md`, `V8_EXECUTION.md`, `REPOSITORY_STATUS.md`, `AUTOMATION_OPERATING_CONTRACT.md`, ADR-001…010.
3. **Barrido por lentes** sobre las categorías A, B y C, dejando constancia de qué se inspecciona y qué no. Cobertura mínima del primer run: `src/` y `tests/` por módulos, `scripts/automation/` y `.github/workflows/`, y el corpus documental vigente.
4. **Verificación de cada candidato:** demostrarlo contra el código en el commit fijado; descartar duplicados de lo ya conocido (issues abiertas, `patrones.md`, hallazgos de PRs previas).
5. **Refutación obligatoria:** intentar demostrar falso cada candidato (¿hay una guarda que no vi? ¿la prueba sí cubre el caso? ¿el contrato lo permite?). Se registra qué se comprobó y por qué el hallazgo sigue en pie. Ante la duda, se descarta: un falso positivo cuesta más que un hallazgo omitido.
6. **Informe:** hallazgos en el esquema de §4, ordenados por gravedad, más «áreas no inspeccionadas», «duplicados descartados» y «qué no demuestra este informe».
7. **Métricas** (§5).
8. **Huella final:** repetir el paso 0 y comparar. Cualquier diferencia es un fallo del run (§7).
9. **Entrega:** informe y métricas se publican donde el propietario los reciba. El auditor **no escribe en el repositorio**; versionarlos, si se decide, lo hace el flujo normal con revisión.

Presupuesto del run: se declara antes de empezar; si se agota, se entrega lo verificado y se declara el corte. Nunca un informe parcial con apariencia de completo.

## 4. Formato de hallazgo (esquema portable)

Todo hallazgo se emite como objeto JSON con estos campos exactos. El esquema es la unidad de comparación entre modelos: dos runs con el mismo esquema se puntúan uno al lado del otro sin releer prosa.

```json
{
  "id": "FINDING-001",
  "gravedad": "P0 | P1 | P2 | P3",
  "tipo": "Bug | Test | Arquitectura | Contrato | Automatizacion | Documentacion | Seguridad | Rendimiento | Otro",
  "titulo": "una línea",
  "afirmacion": "qué está mal exactamente",
  "evidencia": [{"ruta": "src/…", "lineas": "12-20", "cita": "fragmento literal"}],
  "comportamiento_esperado": "qué debería ocurrir",
  "fuente_normativa": "requisito, ADR, contrato o prueba que lo exige",
  "comportamiento_real": "qué ocurre",
  "reproduccion": "pasos o prueba mínima",
  "impacto": "qué puede romper, degradar o confundir",
  "confianza": "Alta | Media | Baja",
  "intento_refutacion": "qué se comprobó para demostrar que la hipótesis era falsa",
  "resultado_refutacion": "por qué sigue en pie",
  "accion": "Corregir | Necesita decision | Documentar | Investigar mas",
  "no_demostrado": "qué NO permite concluir esta evidencia"
}
```

**Regla central:** un hallazgo sin `evidencia` concreta o sin `intento_refutacion` **no llega al informe final**. Pocos hallazgos sólidos valen más que muchas opiniones.

## 5. Métricas por ejecución

**Conjunto mínimo comparable** (exigible a cualquier motor): identificador del run; agente; misión; modelo y proveedor; commit auditado; duración; capacidades de §2b usadas; áreas inspeccionadas y no inspeccionadas; hallazgos totales; confirmados; falsos positivos; duplicados o ya conocidos; nuevos; distribución de severidad; minutos de supervisión humana.

**Conjunto ampliado** (cuando el motor lo exponga): turnos, tokens de entrada y salida, llamadas al modelo, tool calls, comandos ejecutados, errores y reintentos, coste.

Lo no observable se registra como `unknown`. **No se inventan métricas**; exigir el conjunto ampliado a todos los motores es justamente lo que forzaría a construir el runner antes de tiempo.

## 6. Puntuación y clave de respuestas

Sin una rúbrica estable, dos runs no son comparables aunque todo lo demás coincida, porque el juez habría cambiado de criterio.

Cada hallazgo se clasifica en exactamente una categoría:

- **Confirmado:** la evidencia se sostiene y el problema es real.
- **Falso positivo:** la evidencia no sostiene la afirmación, o existe una guarda que el auditor no vio.
- **Ya conocido:** real, pero ya registrado en una issue abierta, en `patrones.md` o en un ADR.
- **No concluyente:** ni demostrado ni refutado con lo aportado.

**Falso positivo grave** = falso positivo emitido con `confianza: Alta` y `gravedad: P0` o `P1`. Uno solo dispara el criterio de parada de ADR-010.

**Clave de respuestas.** La Fase 0 dejó hallazgos verdaderos ya verificados que sirven para medir el *recall* de cualquier modelo sin que el propietario verifique desde cero. Dos reglas que la hacen válida:

1. **No vive en el árbol auditado.** Una clave dentro del repositorio que el auditor lee es un examen filtrado. Para el RUN-001 se mantiene fuera y se versiona **después** del run, junto con sus métricas.
2. **No aparece en la misión.** El auditor no sabe qué se espera que encuentre.

## 7. Criterios de éxito y de fracaso

Éxito del RUN-001 (todos):

1. Huella inicial y final idénticas: cero modificaciones del repositorio y cero acciones irreversibles.
2. Cada hallazgo final con evidencia verificable e intento de refutación.
3. Hechos, inferencias e incertidumbre separados.
4. Otro humano o modelo puede verificar cada hallazgo sin reconstruir la investigación.
5. Métricas del conjunto mínimo completas.
6. El coste de supervisión no supera el valor producido (lo juzga el propietario y queda registrado).

Fracaso o parada (cualquiera):

- **Un falso positivo grave** según §6 → parar el piloto y analizar el método antes de aumentar autonomía.
- Dos ejecuciones seguidas con defectos de la misma familia en el método del auditor → regla de las dos rondas sobre el diseño.
- Cualquier diferencia entre huella inicial y final → parar de inmediato.

## 8. Rollback

Dejar de lanzarlo. Un run no deja estado en el repositorio; informes y métricas se conservan como evidencia histórica. No hay nada que revertir en settings, workflows ni permisos, porque nada de eso se toca.

## 9. Work item

El run se sigue en una **issue normal, sin etiquetas `sirius:`**: un run del auditor no es un bloque de la tubería, y etiquetarlo lo metería en una máquina de estados que espera una PR con código y acabaría en `failed-safely` sin que nada hubiera fallado.

RUN-001: incidencia **#154**, commit `8e8e38cbc1d8e282b89792c10bb7bc85decc5469`.

## 10. Qué queda explícitamente fuera

No modificar producto Sirius; no reabrir la memoria sin evidencia nueva; no habilitar web al Builder ni al Auditor v0; no introducir secretos; no dar push ni merge al auditor; no construir routing multimodelo ni plataforma; no instalar frameworks; no automatizar decisiones estratégicas; no permitir que el auditor arregle sus hallazgos; no sacrificar trazabilidad por autonomía.

La comparación multimodelo (NVIDIA NIM/Nemotron incluida) llega después, y solo cuando se cumplan las tres condiciones que la hacen honesta: que la superficie de §2b se haya estabilizado entre dos runs consecutivos, que exista clave de respuestas, y que la tasa de hallazgos confirmados justifique el coste. Entonces el runner implementa un contrato conocido en vez de una conjetura, y la abstracción de proveedor —`{provider, base_url, model, api_key}`— es la parte trivial del trabajo.

## 11. Estado

RUN-001 preparado y autorizado (ADR-010). Los resultados y la evaluación del propietario se registran en la incidencia #154.
