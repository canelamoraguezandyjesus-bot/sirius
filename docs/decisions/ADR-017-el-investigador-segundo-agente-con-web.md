# ADR-017 — El Investigador: segundo agente, con web, sobre el molde del Auditor

- Estado: PROPUESTO
- Fecha: 15 de agosto de 2026
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Numeración: comprobada contra todas las ramas remotas; 016 es el último tomado.
- Extiende el patrón de [ADR-016](ADR-016-el-auditor-se-lanza-por-etiqueta-y-no-escribe-nunca.md)
  a un segundo agente.

## Contexto y problema

El propietario quiere lanzar investigaciones —«cómo hacer la memoria de
Sirius», por ejemplo— sin depender de ChatGPT ni de abrir claude.ai, usando la
suscripción que ya paga. El Bloque B demostró que la suscripción de Claude ya
ejecuta agentes en este repositorio (el Auditor corrió dos veces el 14-08 con
el token de suscripción), así que la única pieza que falta es **un agente cuya
misión sea investigar**, no auditar.

La condición del encargo, literal: poder usarlo **desde ya y desde una sesión**
(«yo desde aquí mismo te digo: utiliza el investigador para investigar cómo
hacer la memoria»), sin salir a claude.ai. La superficie por etiqueta es la
segunda vía, para cuando no hay sesión abierta.

## Nota de arranque (escrita ANTES de implementar)

1. **¿Dónde vive lo que puede fallar?** En tres sitios ya conocidos por el
   Auditor: el encargo (un agente desatendido que no sabe cómo se trabaja
   aquí), la frontera de permisos (un modelo con capacidad de escritura), y el
   canal de confianza (un informe sin sanear publicado como
   `github-actions[bot]`). Y uno nuevo: **el contenido web no confiable** que
   este agente, a diferencia del Auditor, va a leer.
2. **¿Qué NO garantiza esto?** Que las investigaciones sean buenas: eso lo
   decide el runbook y lo juzga el propietario leyendo informes. Ni que la
   web diga la verdad: el runbook obliga a separar lo comprobado de lo leído.
3. **Criterio de parada:** si para que el Investigador funcione hiciera falta
   darle permisos de escritura al trabajo que ejecuta el modelo, o publicar
   su informe sin el saneador, se para y se decide de nuevo — las mismas dos
   líneas rojas de ADR-016, que no se cruzan por comodidad.
4. **¿Qué hace el fallo detectable?** Las mismas pruebas estructurales del
   Auditor, aplicadas a este workflow, verificadas por mutación antes de
   comprometer; y la huella del árbol con `--ignored=matching`, que ya
   incorpora el FINDING-001 del propio Auditor.

## Decisión

**Un segundo agente, el Investigador, sobre el molde exacto de ADR-016**, con
tres diferencias deliberadas y ninguna más:

**1. La web, ENCENDIDA.** `WebSearch` y `WebFetch` estaban prohibidas para el
Auditor por orden expresa del propietario durante el piloto. Para el
Investigador las autoriza el propio encargo: investigar sin web no es
investigar. La autorización es **por agente, no global**: el Auditor sigue sin
web, y la prueba que lo defiende no cambia.

**2. La pregunta viaja en la incidencia.** El cuerpo de la incidencia ES el
encargo de investigación. Se pasa al prompt por variable de entorno (nunca
interpolado en el YAML, que sería inyectable), con la misma guarda de
delimitador que el runbook.

**3. Dos superficies desde el primer día.** El runbook
(`docs/implementation/INVESTIGADOR_AGENT_V0.md`) vive en el árbol y funciona en
sesión desde el momento en que existe: «ejecuta el Investigador sobre X» en
cualquier sesión de Claude Code es la superficie 1. La etiqueta
`investigacion:solicitada` (sin prefijo `sirius:`, por la lección de ADR-016:
el ciclo reconoce lo suyo por prefijo) es la superficie 2.

**Todo lo demás se hereda de ADR-016 sin cambios**: trabajo partido en
`investigar` (modelo, `contents: read`, token del run y nunca el PAT) y
`publicar` (`issues: write`, sin modelo, saneador `sanitize_untrusted_text`);
huella del árbol tomada por el arnés con `--ignored=matching`; informe
incremental en ruta literal; run sin informe termina en rojo; `Task` denegada;
sin `--dangerously-skip-permissions`.

**El saneador importa MÁS aquí que en el Auditor.** El Investigador lee web no
confiable, y su informe puede arrastrar literalmente cualquier cosa que una
página quiera colarle. Ese informe se publica dentro del filtro de confianza
del ciclo. Sin el saneador, una página web podría sembrar marcadores que el
corrector consume como propios; con él, las vallas y los `<!--` llegan
neutralizados. Es la misma defensa, contra un adversario más real.

## Comprobación que la sostiene

`tests/automation/test_investigador_workflow.py`, con la forma de ADR-015
(buscar lo malo, derivar del YAML real, verificar los supuestos en la misma
prueba), más la cobertura automática del barrido global de
`test_auditor_workflow.py`, que vigila TODOS los workflows: el trabajo
`investigar` entra solo en ese barrido por existir.

Reglas propias del Investigador, distintas de las del Auditor: la web está
**permitida** (no se comprueba su ausencia), pero `Task`,
`--dangerously-skip-permissions` y `Bash` sin acotar siguen prohibidos; la
etiqueta no lleva prefijo `sirius:`; el informe se publica saneado; y ningún
workflow del ciclo ni el Auditor reaccionan a la etiqueta nueva.

Verificado por mutación antes de comprometer, en las dos direcciones.

## Consecuencias

**Lo que esto NO garantiza.** La calidad de las investigaciones. Y hereda el
límite de ADR-016: la prueba fija la precondición (permisos, token, saneador),
no la consecuencia (que el informe llegue) — eso lo confirma el estreno.

**El riesgo nuevo es el contenido web.** Un investigador que lee páginas no
confiables puede ser dirigido por ellas (inyección de instrucciones en el
texto que lee). Mitigaciones: no puede escribir en ningún sitio (permisos), su
informe se sanea (canal), y el runbook le obliga a citar fuentes y a separar
lo comprobado de lo leído (contenido). Lo que NO se puede impedir es que un
informe recoja información falsa de una fuente falsa: por eso el formato
obliga a citar cada afirmación, para que el propietario pueda juzgar la fuente.

## La frontera de confidencialidad (añadida por la reconciliación, ADR-018)

El repositorio es PRIVADO (verificado por API el 15-08) y este agente junta,
por primera vez, lectura del árbol y salida a Internet. Los canales por los
que puede salir contenido: el TEXTO de cada consulta de búsqueda y la URL
completa (dominio, ruta, parámetros) de cada lectura de página. Con las
herramientas concedidas no hay más: Bash está acotado a git sin red, no hay
subagentes y el job no tiene secretos que perder.

Tres opciones evaluadas y la decisión:

- **Lista blanca de dominios** — descartada como mitigación principal: no
  filtra el texto de las consultas de búsqueda (el canal principal) y mata la
  misión de investigar en abierto. Queda disponible como endurecimiento
  por-run si un encargo concreto lo pide.
- **Partición en dos fases** (leer-repo sin web / buscar-web sin repo) — la
  única imposibilidad mecánica real, pero exige orquestación que este workflow
  no tiene y rompe el runbook (§3.2 manda contexto del repo ANTES de la web).
  Es diseño del evaluador (`BANCO_DE_EVALUACION_DISENO.md`), no de v0.
- **Contrato + registro auditable** — LO DECIDIDO para v0: la regla de
  confidencialidad con listas CERRADAS (prohibido: fragmentos de código o
  documentos, rutas, nombres propios del código, números/títulos de
  incidencias, nombres de secretos; permitido: los términos de la pregunta
  del propietario, tecnologías públicas, conceptos genéricos, mensajes de
  error públicos) vive en el runbook §3.3b y en el prompt; y el ARNÉS extrae
  todas las consultas del volcado de ejecución del runtime y las publica como
  apéndice del informe. La degradación del extractor es VISIBLE (aviso ⚠️ en
  el comentario y `::warning` en el run), nunca silenciosa.

**Riesgo residual, aceptado al fusionar:** un modelo dirigido por una página
inyectada puede exfiltrar contenido del repositorio ANTES de que nadie lea el
registro — la detección es posterior al hecho. Se acepta porque el job no
expone secretos ni credenciales (token del run con `contents: read`, nunca el
PAT), el activo en riesgo es texto del repositorio, y todo queda publicado
junto al informe. Quien fusione esta PR acepta ESTE párrafo con ella; y la
prohibición de fusionar dictada el 15-08 sigue vigente hasta que el
propietario la levante con una decisión explícita, no por inercia del ciclo.

**Coste:** minutos de Actions por run, como todo lo demás. Sin claves nuevas,
sin servicios nuevos: el mismo token de suscripción del ciclo.

## Alternativas descartadas y por qué

- **Investigar en claude.ai a mano.** Funciona y es gratis, pero no deja
  registro en el repositorio, no se lanza por etiqueta, y era exactamente el
  transporte manual de contexto que la auditoría de procesos midió como coste.
- **Esperar a Inspect para hacerlo multimodelo desde el principio.** Invierte
  el orden probado: primero el agente con lo que ya funciona (ADR-016), luego
  el multimodelo si la prueba de 5 minutos pasa. Un investigador con Claude
  hoy vale más que uno multimodelo dentro de un mes.
- **Un workflow genérico de agentes parametrizado por etiqueta.** Menos
  ficheros, pero cada agente tiene su superficie de herramientas y sus
  prohibiciones propias (el Auditor sin web, el Investigador con ella), y un
  workflow genérico las mezclaría o exigiría una tabla de configuración que
  ninguna prueba estructural simple puede vigilar. Dos ficheros casi iguales
  y vigilables ganan a uno configurable y opaco.
