# ADR-018 — Reconciliación de la línea de agentes: el arnés ejecuta, el modelo interpreta, el evaluador compara

- Estado: PROPUESTO
- Fecha: 15 de agosto de 2026
- Aprobación: la fusión de la PR que lo introduce, por el propietario. La
  fusión es además la aceptación explícita de los dos riesgos residuales
  documentados abajo (contexto de GitHub como entrada no confiable del
  Auditor; consultas web del Investigador).
- Numeración: comprobada contra `docs/decisions/` y las ramas remotas; 017 es
  el último tomado.
- Contexto completo y evidencia: [`RECONCILIACION_LINEA_DE_AGENTES.md`](../implementation/RECONCILIACION_LINEA_DE_AGENTES.md).
  Encargo: documento de reconciliación del propietario (15-08) — verificado
  afirmación a afirmación, sin ningún veredicto FALSA — más su orden operativa.

## Contexto y problema

El Auditor por etiqueta (ADR-016) entregaba una superficie MENOR que la que su
propio runbook declara en el contrato portable (§2b): el prompt ordenaba
«sustituye por lectura estática» y el job no podía leer GitHub — RUN-002 lo
declaró él mismo (FINDING-002, #167). El nombre «el Auditor» había pasado a
designar su adaptador más estrecho. Además, las defensas estructurales
reconocían el trabajo-con-modelo buscando literalmente
`anthropics/claude-code-action`: con cualquier otro runtime, el barrido de
permisos pasaba en silencio. Y el Investigador (ADR-017, PR #171) dejaba sin
resolver la frontera de confidencialidad de un repositorio PRIVADO con acceso
web.

## Nota de arranque

Publicada en #154 (comentario del 15-08, madrugada) ANTES de ver resultados,
con las cuatro preguntas y tres criterios de parada; ninguno se disparó: cero
afirmaciones falsas en el documento del propietario, ningún arreglo exigió
permisos de escritura para el modelo, y ninguna ronda repitió familia de
defectos.

## Decisión

**1. El arnés ejecuta y el modelo interpreta (Auditor).** El trabajo `auditar`
gana pasos de ARNÉS, antes de la huella del árbol: instalar el entorno,
ejecutar los cuatro comandos exactos de CI (`ruff format --check`, `ruff
check`, `mypy src tests`, `pytest`) capturando salida y código de cada uno, y
volcar el contexto de GitHub (`gh issue list`, `gh pr list`, `gh run list`) a
ficheros JSON. El modelo LEE esos resultados; sus herramientas no cambian ni
un carácter. El prompt deja de ordenar lectura estática y pasa a exigir la
declaración de superficie de §2b en cada informe. Los permisos del job pasan a
`contents/issues/pull-requests/actions: read` — todo lectura: la línea roja de
ADR-016 (el modelo no escribe) queda intacta, y la ampliación no amplía al
AGENTE, cuyo runbook §2 ya concedía leer GitHub. La entrega es PARCIAL a
propósito y está declarada en §2c del runbook: listados sin cuerpos (los
cuerpos los escriben terceros y modelos), comentarios solo de las incidencias
de auditoría, y la lista de runs SIN sus logs. Antes el workflow no entregaba
NADA de esa fila; ahora entrega la parte declarada, y lo que falta se dice.

**2. Los runbooks se vuelven neutrales al motor.** La definición de un agente
habla de CAPACIDADES (buscar en la web, leer una URL, subagentes); el mapeo a
nombres de herramienta concretos (`WebSearch`, `Task`…) es del adaptador (el
workflow o la sesión). La regla del observador del Investigador pasa de «sobre
Claude/Anthropic» a «sobre el modelo que ejecuta este run, su fabricante, o
este laboratorio». Lo que el modo desatendido no tiene (subagentes,
verificación adversarial multiagente) se declara en el runbook (§2c del
Auditor) y en cada informe: la diferencia entre RUN-001 y RUN-002 nunca vuelve
a ser implícita.

**3. Las defensas se atan a un registro, no a un nombre.** Nace
`tests/automation/registro_de_acciones.yml`: TODA acción `uses:` de TODO
workflow — la de cada paso Y la de nivel job (reusable workflows), incluidas
las formas `./ruta` y `docker://` — debe estar clasificada (`con_modelo` /
`sin_modelo`); una acción desconocida pone las pruebas en rojo.
`_ejecuta_modelo` deriva del registro en todos los ficheros de prueba. En un
job que ejecute un modelo de un workflow no exento, la única referencia a
`secrets.` admisible — recolectada en los TRES niveles: `env` del workflow,
`env` del job, y `env`+`with` del paso del modelo — es la credencial COMPLETA
registrada de esa acción (input y secreto, no solo el nombre del input). La
exención de los tres roles del ciclo deja de ser una lista local de una
prueba: es un campo del propio registro, DATO visible que las dos reglas (la
de escritura y la de secretos) leen del mismo sitio. Consecuencia: un motor
nuevo no puede entrar sin pasar por el registro, y entrar le aplica todas las
defensas de golpe.

**4. La frontera de confidencialidad del Investigador.** Tres piezas: (a)
regla de contrato en runbook y prompt — ninguna consulta de búsqueda ni URL
solicitada contiene texto literal del repositorio (código, rutas, fragmentos
de documentos); el tema se formula con términos genéricos del dominio público;
(b) pieza MECÁNICA: el arnés extrae del volcado de ejecución del runtime
(verificado en el run 31835428937: `${RUNNER_TEMP}/claude-execution-output.json`)
todas las consultas WebSearch y URLs WebFetch y las publica como apéndice del
informe — el propietario audita lo que salió sin abrir logs. El apéndice se
añade DESPUÉS de evaluar si el informe venía vacío (no puede convertir un run
mudo en válido) y también en runs inválidos; el extractor es defensivo (jq
validado, filtros que degradan a lista vacía) y su degradación es VISIBLE —
aviso ⚠️ en el comentario y `::warning` en el run — porque una auditabilidad
que se apaga en silencio no es auditabilidad. Deuda declarada del adaptador:
el formato interno del volcado no tiene fixture propio; el estreno (F2)
capturará uno real y le pondrá prueba de contrato; (c) el riesgo
residual queda escrito en ADR-017: un modelo dirigido por una página inyectada
puede exfiltrar antes de ser detectado; se acepta porque el job no tiene
secretos que perder, el activo es texto del repo, y todo queda registrado. La
partición en dos fases (imposibilidad mecánica real) es diseño del evaluador,
no de este workflow.

**5. Inspect AI como evaluador — diseño ahora, dependencia después.** La capa
de evaluación de la línea de agentes será Inspect, en un laboratorio FUERA de
este repositorio (`sirius-lab`), según
[`BANCO_DE_EVALUACION_DISENO.md`](../implementation/BANCO_DE_EVALUACION_DISENO.md).
Este ADR autoriza el DISEÑO y la dirección; la implementación espera a las
puertas del §10 del runbook (superficie estable, clave de respuestas, tasa que
justifique el coste) y a las dos decisiones del propietario (prueba de Windows;
gasto OpenAI — el segundo motor puede ser local y gratis). ADR-016 decía «nada
de Inspect»: describía el alcance de aquella decisión con el Bloque B aún
pendiente; el Bloque B ya corrió y midió — esta decisión lo releva en ese punto
concreto y en ningún otro.

## Comprobación que la sostiene

Las pruebas de `tests/automation/` amplían su forma ADR-015: ausencia de
«lectura estática» en el workflow del Auditor; orden arnés→huella→modelo;
herramientas del modelo sin ejecutores; permisos del job de modelo como lista
cerrada; registro de acciones cerrado con guardián; regla de confidencialidad
presente si hay web; extracción de consultas anclada. Todo verificado por
mutación en las dos direcciones antes de comprometer.

## Consecuencias

Un run desatendido del Auditor pasa de leer a COMPROBAR (resultados reales de
pytest/ruff/mypy y contexto de GitHub), con el mismo aislamiento. Entra texto
no confiable nuevo en su prompt (títulos y cuerpos de incidencias): mitigado
como en el Investigador — sin escritura, saneador a la salida, aviso explícito
de datos-no-instrucciones — y aceptado al fusionar. El coste por run sube
~6-8 minutos de Actions (la instalación y la batería). Las cachés que las
comprobaciones crean quedan DENTRO de la línea base de la huella (se ejecutan
antes de capturarla), así que la comparación sigue midiendo al modelo, no al
arnés. Lo que esto NO da: subagentes ni verificación adversarial en
desatendido — eso vive en el evaluador (F4 del plan).

## Alternativas descartadas

- **Darle al modelo las herramientas de ejecución** (pytest/ruff en su Bash):
  ampliaría la superficie de ataque del paso con la credencial del runtime y
  rompería la huella (cachés creadas DESPUÉS de la línea base). El arnés
  ejecuta mejor: mismo dato, cero herramientas nuevas.
- **Declarar el Auditor desatendido «Auditor-Lite» y no arreglar nada**: era
  la opción (b) del documento del propietario; su orden operativa eligió (a)
  «recuperar capacidad mediante una superficie segura», y §2b ya definía cómo.
- **Lista blanca de dominios para el Investigador**: no filtra el texto de las
  consultas (el canal principal), y mata la misión de investigar en abierto.
  Queda como endurecimiento por-run si algún encargo lo pide.
- **Un workflow genérico parametrizado por agente**: re-descartado por lo
  mismo que en ADR-017 — dos ficheros vigilables ganan a uno opaco; el
  registro de acciones da la neutralidad sin la opacidad.
