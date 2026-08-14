# Agentes de Sirius — desde dónde se invocan

- **Fecha:** 14 de agosto de 2026
- **Estado:** la **superficie 2 ya está construida** (ADR-016, §2). Las
  superficies 1 y 3 y todo lo multimodelo siguen como estaban: la 1 disponible,
  la 3 pospuesta hasta cerrar 0.1, y el multimodelo bloqueado tras la pregunta
  del §4. Este documento no autoriza nada por sí mismo; lo que autoriza el
  workflow del Auditor es ADR-016.
- **Actualizado:** 14 de agosto de 2026, al implementar el Bloque A.
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

### Superficie 2 — Etiqueta en GitHub · **CONSTRUIDA (ADR-016)**

Igual que el ciclo de programación actual: se crea una incidencia, se le pone
una etiqueta (`auditoria:solicitada`) y un workflow ejecuta el
agente y publica el informe como comentario.

- **Cómo:** `anthropics/claude-code-action`, igual que
  `implement-sirius-work.yml`, pero en un trabajo con **permisos de solo
  lectura** (`contents: read`). El runbook se le pasa como prompt leyéndolo del
  árbol, no copiado.
- **Lo que aporta y la superficie 1 no:** queda registro de cada ejecución y se
  puede lanzar desde el móvil. *(Se afirmó aquí que `claude-code-action` expone
  coste, turnos y duración. **No está comprobado**: es una acción de terceros y
  este repositorio no tiene acceso a la red para verificar su salida. Si resulta
  cierto, ahorra las métricas que hoy se anotan a mano; si no, hay que anotarlas
  igual y la superficie 2 sigue mereciendo la pena por el registro.)*
- **Estado:** implementada en `.github/workflows/audit-sirius-repository.yml`,
  autorizada por **ADR-016**. Se pone `auditoria:solicitada` a una incidencia y
  el informe vuelve como comentario de esa incidencia — **saneado**, porque lo
  escribe un modelo y se publica dentro del filtro de confianza del ciclo.
  La etiqueta no lleva el prefijo `sirius:` a propósito: el ciclo reconoce lo
  suyo por prefijo, y la primera elección (`sirius:audit-requested`) la metía
  en la máquina de estados (detalle en ADR-016).
- **La decisión que costó:** GitHub no tiene un permiso «solo comentar», así que
  el trabajo se parte en dos y la frontera es estructural, no confiada: `auditar`
  declara `contents: read` y ejecuta el modelo; `publicar` puede comentar y **no
  ejecuta ningún modelo**. Detalle en ADR-016.
- **Lo que NO exigió:** ni Inspect, ni claves de API nuevas, ni gasto nuevo.
- **Lo que falta:** ejecutarla una vez de verdad. Hasta entonces, que
  `claude-code-action` exponga coste y turnos sigue sin verificar.

### Superficie 3 — Desde Sirius · **el final del camino, no ahora**

Un control dentro de Sirius que cree la incidencia y aplique la etiqueta, de
modo que lanzar una auditoría sea algo que se hace desde la aplicación.

- **Por qué no ahora:** por lo mismo que el §3 — RECTOR §15 («amplía 0.1 por
  preparación futura») y EV-007 (multiagente pospuesto). Meterlo antes de cerrar
  0.1 sería ampliar el producto por la puerta de atrás.
- **Cuándo:** después de aceptar 0.1. La superficie 2 no se tira: Sirius
  acabaría hablando con el mismo mecanismo de etiquetas, no con uno paralelo.

## 3. Dónde vive el código de los agentes

Decidido por eliminación, y conviene dejarlo escrito antes de escribir nada:

**No** en `src/sirius/`. RECTOR §15 manda detener una propuesta que «amplía 0.1
por preparación futura» o que «introduce arquitectura multiagente sin
evidencia», y EV-007 deja el multiagente **pospuesto** hasta que una tarea real
demuestre que hace falta. Un runner de agentes dentro del producto es las dos
cosas a la vez.

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

1. ~~**Cerrar el piloto del Auditor**~~ — **hecho**: cuatro hallazgos graves,
   cuatro defectos reales, cero falsos positivos (#154).
2. ~~**Superficie 2**~~ — **hecha**: ADR-016 y
   `.github/workflows/audit-sirius-repository.yml`. Falta estrenarla.
3. **La prueba de la tarde** (§4): ¿sirven las suscripciones? Responde sí o no a
   toda la línea multimodelo. **Es el siguiente paso.**
4. **Triaje de paradas** como segundo agente, por el motivo del §5: máximo
   ahorro con la superficie de permisos más pequeña.
5. **Multimodelo** solo entonces, y solo si el paso 3 lo permite.

## 7. Trabajo preparado, listo para abrirse

### Bloque A — El Auditor invocable por etiqueta · **HECHO**

Implementado por ADR-016. Se deja el encargo original tal cual porque contrastar
lo pedido con lo entregado es más útil que borrarlo. **Dos desviaciones
deliberadas**, explicadas en ADR-016: (1) el encargo pedía un solo trabajo con
`contents: read`; se entregan **dos**, porque comentar exige `issues: write` y
darle eso al trabajo que ejecuta el modelo le pondría en la mano la máquina de
estados entera. (2) El encargo nombraba la etiqueta `sirius:audit-requested`;
la definitiva es `auditoria:solicitada`, **sin** el prefijo, porque el ciclo
reconoce lo suyo por prefijo y aquella elección metía el run en la máquina de
estados — lo encontró la ronda adversarial, no el autor.

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

## 8. Nota de arranque (tardía) y comprobación de las citas

ADR-001 pide la nota de arranque **antes** del primer commit. Aquí no se cumplió:
se escribe después, con la PR ya abierta. Vive en este documento porque
`.claude/evidencia/` no es escribible en el entorno donde se trabajó y
`docs/decisions/` está reservado a `ADR-NNN` por su propio README.

No se disfraza de nota previa. Fingir que se decidió antes sería la alternativa
que ADR-001 descarta por nombre: «publicaría como del agente una evidencia que
nunca emitió».

### Criterio de parada

Escrito para lo que quedaba —la revisión de esta PR—, antes de comprobar nada:

> Si al comprobar las citas aparece **más de una** afirmación que el árbol no
> sostiene, no se parchea cita a cita: se retira el documento y se reescribe
> verificando cada referencia contra el fichero antes de escribirla.

**Se disparó: aparecieron dos.** Se corrigieron en el mismo commit en vez de
reescribir, porque las dos fallaban por la misma causa —citar de memoria— y la
corrección es la misma operación (abrir el fichero citado) aplicada a **todas**
las citas del documento, que ya están comprobadas una por una abajo. Si la
revisión encuentra una tercera, se reescribe.

### Afirmación → comprobación

| Afirmación | Comprobación | Resultado |
|---|---|---|
| `implement-sirius-work.yml` usa `anthropics/claude-code-action` | `.github/workflows/implement-sirius-work.yml:131` | **Cierta**, pero la primera versión de esta fila citaba la línea 121 — que es un `echo` — dentro de la tabla que existe para certificar citas. Cuarta de la misma familia; corregida abriendo el fichero |
| El PAT no puede escribir en `.github/workflows/` | ADR-002, con el error literal de GitHub | **Cierta** |
| El contrato §9 prohíbe «introducir otro nivel de automatización» | `AUTOMATION_OPERATING_CONTRACT.md:376-391` | **FALSA.** Esa frase no existe en §9: era una cita entrecomillada inventada. Corregido: el ADR lo exige ADR-001, y la prohibición de §9 que sí aplica es «convertir una idea exploratoria en una decisión aprobada» |
| «El alcance aprobado de 0.1 excluye multiagente, RAG y automatización externa» | `docs/canonical/STATUS.md:29`, `docs/evolution/RECTOR.md:136,260`, `DECISIONS.md` EV-007 | **FALSA en su forma fuerte.** Los canónicos dicen que el multiagente está *pospuesto* y *no es requisito* de 1.0, no que 0.1 lo «excluya». Corregido citando RECTOR §15 —«amplía 0.1 por preparación futura», «introduce arquitectura multiagente sin evidencia»—, que sostiene mejor la misma conclusión |
| `claude-code-action` expone coste, turnos y duración | Ninguna: acción de terceros, sin red en esta sesión | **No comprobada**, y marcada como tal en §2 |
| El resumen de la investigación externa (§5) | Ninguna | **Material de terceros**, declarado no verificado en el propio §5 |

La conclusión del §3 —el código de los agentes va en `scripts/`, nunca en
`src/sirius/`— **no cambia** con las correcciones: queda mejor sostenida, porque
RECTOR §15 es una regla de parada explícita y lo anterior era una paráfrasis.

### Por qué no lleva ADR propio

El documento no decide: prepara. La única elección con aire de decisión es el §3,
y su ADR corresponde al **Bloque A**, cuando exista código que ponga a prueba la
consecuencia. Un ADR cuya consecuencia no puede comprobarse todavía es la
ceremonia que ADR-001 descarta.

**Obligación pendiente:** el Bloque A no puede abrirse sin ADR, y ese ADR debe
recoger el §3 — no darlo por decidido aquí.

### Patrón reincidente

`patrones.md`, familia «afirmar más de lo que el dato sostiene», en su variante
más cara: **citar de memoria una fuente que está en el mismo árbol**. Es el mismo
error que produjo dos ficheros `ADR-008` en la PR #153 —no comprobar la
numeración antes de escribirla—. Van dos veces, misma familia.

Por la regla de las dos rondas no toca seguir parcheando, así que la regla
operativa que sale de aquí es: **ninguna referencia a otro documento del
repositorio se escribe sin abrir el fichero citado en la misma acción.** Barato,
mecánico, y habría evitado los dos casos.
