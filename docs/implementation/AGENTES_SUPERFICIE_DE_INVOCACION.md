# Agentes de Sirius — desde dónde se invocan

- **Fecha:** 14 de agosto de 2026
- **Estado:** PREPARADO, NADA IMPLEMENTADO. Este documento describe el plan y
  deja el trabajo listo para abrirse por el cauce normal. No autoriza nada por
  sí mismo.
- **Base:** [`AGENT_OPPORTUNITY_MATRIX.md`](AGENT_OPPORTUNITY_MATRIX.md),
  [`AUDITOR_AGENT_V0.md`](AUDITOR_AGENT_V0.md), ADR-010, y la investigación
  externa del 14-08-2026 resumida en §5.

## 1. La distinción que ordena todo lo demás

Hay dos preguntas que se confunden fácilmente y que tienen respuestas, costes y
plazos muy distintos:

| | Pregunta | ¿Se puede hoy? | Qué exige |
|---|---|---|---|
| **A** | ¿Desde dónde lanzo un agente? | **Sí, ya** | Nada nuevo en el caso 1; un workflow en el caso 2 |
| **B** | ¿Puedo ejecutarlo con cualquier IA? | Todavía no | Un runner, claves de API y una decisión de gasto |

**A no depende de B.** Se puede tener la etiqueta en GitHub que lanza el Auditor
—con Claude, como todo lo demás del repositorio— sin haber resuelto nada sobre
multimodelo. Y conviene, porque enseña cómo se comporta el agente en el uso real
antes de invertir en la parte cara.

## 2. Las tres superficies, en orden de coste

### Superficie 1 — Sesión de Claude Code · **disponible hoy, coste cero**

Abrir una sesión y decir: «ejecuta AUDITOR-V0-RUN-002 sobre el commit `<sha>`».
Funciona porque el runbook vive en el repositorio, no en la memoria de nadie.
Es lo que se hizo en RUN-001.

- **Ventaja:** cero infraestructura, disponible ahora mismo.
- **Límite:** hay que abrirla a mano y estar delante. No hay historial de
  ejecuciones ni métricas comparables salvo que se registren aparte.

### Superficie 2 — Etiqueta en GitHub · **construible con lo que ya hay**

Igual que el ciclo de programación actual: se crea una incidencia, se le pone
una etiqueta (`sirius:audit-requested`, por ejemplo) y un workflow ejecuta el
agente y publica el informe como comentario.

- **Cómo:** un workflow nuevo que use `anthropics/claude-code-action`, igual que
  `implement-sirius-work.yml`, pero con **permisos de solo lectura**
  (`contents: read`) y sin token de escritura. El runbook se le pasa como
  prompt; el informe vuelve como comentario.
- **Lo que aporta y la superficie 1 no:** queda registro de cada ejecución, se
  puede lanzar desde el móvil, y el propio `claude-code-action` expone coste,
  turnos y duración — que son justo las métricas que hoy hay que anotar a mano.
- **Lo que exige:** (a) un ADR, porque el contrato §9 prohíbe «introducir otro
  nivel de automatización» sin aprobación expresa; (b) trabajo en sesión, porque
  el PAT no puede escribir en `.github/workflows/` (ADR-002).
- **Lo que NO exige:** ni Inspect, ni claves de API nuevas, ni gasto nuevo.

### Superficie 3 — Desde Sirius · **el final del camino, no ahora**

Un control dentro de Sirius que cree la incidencia y aplique la etiqueta, de
modo que lanzar una auditoría sea algo que se hace desde la aplicación.

- **Por qué no ahora:** el alcance aprobado de Sirius 0.1 excluye expresamente
  el multiagente y la automatización externa. Meterlo antes de cerrar 0.1 sería
  ampliar el producto por la puerta de atrás.
- **Cuándo:** después de aceptar 0.1. La superficie 2 no se tira: Sirius
  acabaría hablando con el mismo mecanismo de etiquetas, no con uno paralelo.

## 3. Dónde vive el código de los agentes

Decidido por eliminación, y conviene dejarlo escrito antes de escribir nada:

**No** en `src/sirius/`. El alcance aprobado de 0.1 excluye multiagente, RAG y
automatización externa. Cualquier runner o herramienta de agentes que viva ahí
amplía el producto sin decisión.

**Sí** en `scripts/` (o, más adelante, en un repositorio aparte si crece). Es
utillaje del laboratorio, igual que `scripts/automation/`, que ya es
exactamente eso: automatización que sirve al desarrollo de Sirius sin formar
parte de Sirius.

Los **activos del agente** —lo que de verdad importa— seguirían la forma que
propone la investigación externa y que ya cumple `AUDITOR_AGENT_V0.md`:

```text
agents/
  auditor/
    runbook.md          ← la misión, en Markdown normal
    output.schema.json  ← el contrato de salida
    permissions.yaml    ← qué puede tocar
```

Un agente de Sirius es **misión + contrato de salida + perfil de permisos**. No
es una clase de ningún framework. Esa es la propiedad que hay que defender.

## 4. La pregunta que hay que responder antes de invertir en multimodelo

**¿Sirven las suscripciones que ya se pagan (Claude, ChatGPT Business) para
ejecutar agentes con un runner, o hacen falta claves de API que se pagan por
uso?**

La investigación externa lo dejó marcado como no verificado, y es la única
incógnita capaz de cambiar la decisión entera: si hace falta contratar APIs, eso
choca con la restricción de no introducir gastos nuevos y hay que decidirlo
antes de construir nada, no después.

Se responde con una prueba de una tarde, no con más lectura.

## 5. Qué concluyó la investigación externa (14-08-2026)

Se resume aquí porque el original es un documento en una conversación y el
repositorio es donde tiene que quedar. **Es material de terceros, no
verificado por este repositorio.**

- **Recomienda no construir un runner desde cero ni adoptar una plataforma
  cerrada**, sino una capa muy fina sobre **Inspect AI** (open source, MIT, del
  UK AI Security Institute), usando **MCP** como frontera portable de
  herramientas. Inspect ya trae bucle de agente, +20 proveedores, modelos
  locales, JSON Schema, límites de coste/tiempo/turnos, transcripciones y
  ejecución de la misma tarea contra varios modelos.
- **Corrige una hipótesis previa:** MCP hace portables **las herramientas**, no
  el modelo. Siguen haciendo falta dos piezas: una abstracción de proveedores y
  una capa de herramientas.
- **Dato con valor práctico inmediato:** el GitHub MCP Server oficial ya expone
  herramientas de Actions y repositorio, así que el **triaje de paradas** —el
  proceso con más coste humano según la auditoría— no necesita que se programe
  la integración con GitHub: solo su runbook y unos permisos muy pequeños.
- **Criterio de éxito que propone para la primera prueba multimodelo**, y que se
  adopta aquí porque está mejor formulado que el anterior: no «¿encuentra
  defectos?» sino «¿he ejecutado la misma especificación, sin tocarla, con tres
  motores distintos, y obtengo registros comparables?».
- **No encontró** un mercado neutral donde estos seis agentes existan ya hechos.
  Sí patrones reutilizables. La conclusión es favorable: el activo a conservar
  son las misiones y los criterios propios.

Lo que la investigación **no** verificó, en sus propias palabras: que la
combinación Inspect + NIM + Nemotron + MCP + JSON Schema funcione de extremo a
extremo; que todo modelo local respete un JSON Schema con igual fiabilidad; y
qué parte de las suscripciones actuales es aprovechable (§4).

Un hueco que la investigación no cubre y que sigue abierto: **quién puntúa**.
El banco de modelos que propone tiene columnas de «hallazgos válidos» y «falsos
positivos», y alguien debe decidir cuáles son cuáles. Si es el propietario, cada
modelo nuevo multiplica su trabajo — justo lo que se quiere eliminar. Por eso la
clave de respuestas de `AUDITOR_AGENT_V0.md` §6 no es opcional.

## 6. Orden recomendado

1. **Cerrar el piloto del Auditor**: ejecutar la verificación y fusionar las PR
   pendientes (ver incidencia #154).
2. **Superficie 2**: el Auditor invocable por etiqueta, con Claude, sin gasto
   nuevo. Un ADR y un bloque de trabajo.
3. **La prueba de la tarde** (§4): ¿sirven las suscripciones? Responde sí o no a
   toda la línea multimodelo.
4. **Triaje de paradas** como segundo agente, por el motivo del §5: máximo
   ahorro con la superficie de permisos más pequeña.
5. **Multimodelo** solo entonces, y solo si el paso 3 lo permite.

## 7. Trabajo preparado, listo para abrirse

### Bloque A — El Auditor invocable por etiqueta

Requiere ADR previo (contrato §9). Cuerpo de la incidencia, listo para pegar:

```markdown
## Work ID
SIRIUS-AGENT-SURFACE-001

## Objetivo
Poder lanzar el Auditor de repositorio desde GitHub aplicando una etiqueta a una
incidencia, sin abrir una sesión interactiva, y que el informe vuelva como
comentario de esa incidencia.

## Alcance permitido
- Workflow nuevo `.github/workflows/audit-sirius-repository.yml`, disparado por
  `issues: labeled` con una etiqueta propia (`sirius:audit-requested`), NUNCA
  por las etiquetas del ciclo de programación.
- `permissions: contents: read` y ningún token con capacidad de escritura sobre
  el código. El agente publica su informe como comentario, y nada más.
- El prompt se construye leyendo `docs/implementation/AUDITOR_AGENT_V0.md`; el
  runbook NO se copia dentro del workflow (dos copias se desincronizan).
- Registro de métricas del run (§5 de AUDITOR_AGENT_V0) en el propio comentario.
- Prueba estructural que verifique: que el workflow no reacciona a ninguna
  etiqueta del ciclo de programación, que no declara permisos de escritura, y
  que no duplica el texto del runbook.

## Fuera de alcance
- Cualquier capacidad de corregir lo que el agente encuentre.
- Tocar los workflows del ciclo de programación.
- Inspect, claves de API nuevas, multimodelo.
- Cualquier cambio en `src/sirius/`.

## Condiciones de parada
- BLOCKED_BY_DECISION si el arreglo exige ampliar el alcance de la credencial.
- FAILED_SAFELY si Quality no pasa.

## Salvaguardas
- No introducir secretos nuevos.
- No dar al agente permiso de escritura «temporalmente para probar».
- El merge lo autoriza el propietario, como siempre.
```

### Bloque B — La prueba de la tarde (§4)

No es un bloque de la tubería: es una sesión con una pregunta única. Encargo
listo:

> Comprueba si el runbook del Auditor puede ejecutarse con al menos dos modelos
> distintos usando las suscripciones actuales, sin contratar nada. Instala
> Inspect AI en un entorno desechable, ejecuta el runbook tal cual está y
> registra: qué credencial pide cada proveedor, si la suscripción sirve o exige
> clave de API, y el coste estimado de una ejecución. No construyas el adaptador
> ni conviertas el runbook. Solo responde la pregunta, con la comprobación
> delante.
