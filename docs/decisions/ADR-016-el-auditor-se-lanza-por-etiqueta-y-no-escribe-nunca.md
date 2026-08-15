# ADR-016 — El Auditor se lanza con una etiqueta, y el trabajo que puede escribir no ejecuta modelos

- Estado: PROPUESTO
- Fecha: 2026-08-14
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Numeración: comprobada contra **todas** las ramas remotas antes de asignar.
  011–015 están tomados. En la PR #153 se crearon dos `ADR-008` por no hacerlo.
- Autoriza el Bloque A (`SIRIUS-AGENT-SURFACE-001`) descrito en
  [`AGENTES_SUPERFICIE_DE_INVOCACION.md`](../implementation/AGENTES_SUPERFICIE_DE_INVOCACION.md) §7.

## Contexto y problema

El Auditor v0 pasó su piloto (#154): cuatro hallazgos graves, cuatro defectos
reales, cero falsos positivos. Hoy solo se puede lanzar abriendo una sesión
interactiva y estando delante.

El propietario quiere lanzarlo como lanza todo lo demás: **poniendo una etiqueta
a una incidencia**. Eso añade lo que la sesión no da — registro de cada
ejecución, disparo desde el móvil, y métricas de coste y duración que hoy se
anotan a mano.

El problema no es hacerlo funcionar. Es que un agente que se dispara solo, sin
nadie delante, **no puede tener permiso para escribir en el código**, y a la vez
tiene que publicar su informe en algún sitio. Esas dos cosas chocan, porque
GitHub no ofrece un permiso «solo comentar»: el permiso más pequeño que permite
comentar una incidencia es `issues: write`, que también permite etiquetar y
cerrar. Conceder eso al trabajo que ejecuta el modelo sería darle la llave de la
máquina de estados entera.

## Criterio de parada (escrito ANTES de implementar)

Si para que el informe llegue a la incidencia hiciera falta que **el trabajo que
ejecuta el modelo** tuviera cualquier permiso de escritura, se para y se decide
de nuevo. No se amplía «solo para probar»: esa es la salvaguarda que el
propietario puso por escrito al encargar el piloto, y una ampliación temporal es
permanente en cuanto nadie la revisa.

## Decisión

**El trabajo se parte en dos, y la frontera es estructural, no de confianza.**

| Trabajo | Permisos | ¿Ejecuta un modelo? |
|---|---|---|
| `auditar` | `contents: read` | **Sí** |
| `publicar` | `issues: write` | **No** |

> **Sustitución parcial (ADR-018, 15-08-2026):** la fila de `auditar` la amplía
> ADR-018 a `contents/issues/pull-requests/actions: read` — TODO lectura — para
> entregar la parte declarada en `AUDITOR_AGENT_V0.md` §2c de la fila 1 de su
> §2, que este workflow no entregaba en absoluto (FINDING-002 de RUN-002,
> #167): listados sin cuerpos, informes previos de auditoría y lista de runs
> sin sus logs. La propiedad de esta decisión — el trabajo que ejecuta el
> modelo NO puede escribir — queda intacta y sigue vigilada.

El Auditor lee el repositorio y escribe su informe **en un fichero del runner**.
No recibe ninguna credencial capaz de escribir: no porque se le pida que se
porte bien, sino porque los permisos del trabajo acotan el token que se le pasa.
Un trabajo posterior, que no ejecuta ningún modelo y cuyo guion está en el
repositorio y se lee entero, publica ese fichero como comentario.

**La propiedad que hay que defender es una y se puede comprobar:** *ningún
trabajo que ejecute un modelo declara permisos de escritura.* Es el mismo patrón
que ya usa el ciclo de programación — Claude nunca muta etiquetas: escribe un
veredicto en un fichero y `sirius_apply_verdict.sh` lo aplica reverificando
(parafraseado de la cabecera de `implement-sirius-work.yml`) — y por la misma
razón.

**Y la huella la toma el arnés, no el agente.** `AUDITOR_AGENT_V0.md` §2 dice que
la restricción de escritura del Auditor es **procedimental**, y que la frontera
mecánica «se vuelve obligatoria» si ocurre cualquiera de tres cosas. La primera
es *«los runs pasan a desatendidos o programados»* — que es literalmente lo que
hace este workflow. Cumplirla exige dos mitades:

| Mitad | Cómo |
|---|---|
| Que no escriba en GitHub | `contents: read` acota el token |
| Que no toque el árbol | El workflow compara `HEAD`, `git status` y las ramas antes y después; si difieren, el informe sale marcado **RUN INVALIDADO** |

El runbook ya pedía esa huella en sus pasos 0 y 8, pero se la pedía **al agente**.
Un agente que certifica su propia inocencia es «el observador dentro de lo
observado», que está en el catálogo de patrones. Aquí la toma el arnés.

Esto obliga a una concesión que hay que decir en voz alta: **el agente conserva
la herramienta `Write`**, porque tiene que dejar el informe en un fichero,
cuya ruta se le da **literal** en el prompt — no como variable de entorno, que
sin `Bash` no tendría forma de resolver. La
tabla de §2 marca «editar código o documentación» como **No**, y `Write` sin
restricción de ruta no distingue el informe del resto del árbol. Lo que impide
el abuso no es la herramienta: es que cualquier escritura en el árbol invalida
el run y lo dice en el comentario. Se prefiere **detectar y anular** antes que
una restricción que no se puede expresar.

**Etiqueta `auditoria:solicitada`, sin el prefijo `sirius:`.** La primera
versión usó `sirius:audit-requested` y era un error que la ronda adversarial
demostró: el ciclo reconoce lo suyo por PREFIJO — `sirius_reconcile.sh` filtra
con `grep '^sirius:'` y `complete-sirius-after-merge.yml` selecciona con
`startswith("sirius:")` — así que «no aparece en ninguna transición» no la
dejaba fuera de nada. Con ese prefijo, el reconciliador la contaba como estado
simultáneo y el completador trataba la incidencia como bloque del ciclo. La
etiqueta usa otro prefijo porque esa es la variable que esos mecanismos miran,
y la prueba verifica el supuesto (que siguen filtrando por prefijo) en vez de
darlo por sabido.

**El informe se publica SANEADO.** El hallazgo más serio de la ronda
adversarial: el comentario del informe sale como `github-actions[bot]`, que
está **dentro** del filtro de confianza del ciclo (`SIRIUS_TRUSTED_AUTHOR_JQ`,
equiparado a OWNER). Un informe crudo escrito por un modelo podría — sin
malicia, simplemente citando literales como manda el runbook — sembrar
marcadores `<!-- sirius-round:N -->` o bloques `OBSERVACIONES_ESTRUCTURADAS`
que los escáneres del corrector consumen como propios. El repositorio ya tenía
la defensa exacta, `sanitize_untrusted_text`, aplicada a todo texto de agente;
el Auditor habría sido el único camino sin ella. El saneador se movió de
`sirius_apply_verdict.sh` a `sirius_issue.sh` para que ambos lo compartan, y
«publicar» lo aplica antes de comentar.

**El runbook no se copia.** El prompt se construye leyendo
`docs/implementation/AUDITOR_AGENT_V0.md` del propio árbol. Dos copias del mismo
runbook se desincronizan, y la desincronización documental es uno de los
defectos que la auditoría lleva corrigiendo desde el principio.

## Comprobación que la sostiene

`tests/automation/test_auditor_workflow.py` — reescrita tras la ronda
adversarial, que demostró que la primera versión comprobaba **la forma que se
le ocurrió al autor y no la que usa el código**: derivaba las etiquetas del
ciclo de los `if:` cuando el ciclo decide por prefijo, ignoraba la herencia de
permisos del nivel workflow (con lo que su lista de exenciones era decorativa:
vaciarla no cambiaba nada), y no fijaba el `github_token` del modelo, que es la
mitad del argumento de este ADR.

Diez pruebas. Las que dependen de un supuesto sobre otro fichero lo verifican
en la misma prueba (que el reconciliador sigue filtrando por `^sirius:`, que el
filtro de confianza sigue incluyendo a `github-actions[bot]`) en vez de darlo
por sabido. Verificadas por mutación, cada una en las dos direcciones; entre
ellas: vaciar la lista de exenciones (la herencia delata a los tres roles),
darle el PAT al modelo, devolver la etiqueta al prefijo `sirius:`, y publicar
el informe sin saneador.

## Consecuencias

**Lo que esto NO garantiza.** Que el informe sea bueno. Esto es fontanería de
disparo: la calidad del Auditor la decide su runbook y la sigue midiendo el
propietario. Y **no se ha ejecutado todavía**: la primera ejecución real es la
prueba de fuego, y hasta que ocurra, que `claude-code-action` exponga coste y
turnos sigue siendo una afirmación no verificada — está marcada como tal en
`AGENTES_SUPERFICIE_DE_INVOCACION.md` §2.

**`issues: write` existe en el workflow.** Acotado al trabajo que solo publica un
comentario, pero existe, y permitiría etiquetar si ese guion cambiara. Lo que
protege no es el permiso: es que ese trabajo **no ejecuta ningún modelo**, así
que lo que hace está escrito en el repositorio y se lee entero. Queda anotado
como lo que hay que vigilar si alguien añade pasos ahí.

**No cambia nada del ciclo de programación.** Ni sus workflows, ni sus
etiquetas, ni el contrato. El Auditor es un carril aparte que no toca la
máquina de estados.

**No introduce claves nuevas ni servicios nuevos**: usa el mismo
`CLAUDE_CODE_OAUTH_TOKEN` que el ciclo. Nada de Inspect, ni multimodelo, ni
proveedores nuevos — eso sigue bloqueado tras el Bloque B. Sí consume lo que
todo lo demás: **minutos de Actions** por run, que en este repositorio privado
son la moneda real. Decir «gasto cero» sin esa nota sería afirmar de más.

**El modelo recibe `github.token`, nunca el PAT** — fijado por prueba, porque
un PAT lleva sus propios permisos y anularía el recorte del job.

**El código del agente sigue fuera de `src/sirius/`** (§3 de
`AGENTES_SUPERFICIE_DE_INVOCACION.md`, que este ADR recoge como obligación):
este bloque vive en `.github/workflows/` y `scripts/automation/`, y no toca el
producto.

## Alternativas descartadas y por qué

- **Un solo trabajo con `contents: read` e `issues: write`.** Es lo que decía el
  bloque de trabajo original, y es peor: el modelo tendría en la mano un token
  capaz de mover la máquina de estados. Basta con que el informe contenga texto
  que se interprete como instrucción para que el riesgo deje de ser teórico.
- **Que el Auditor abra una PR con su informe.** Exige `contents: write`. Choca
  de frente con el criterio de parada.
- **Publicar el informe solo en el log del run.** No cuesta permisos, pero
  obliga a entrar en Actions a leerlo, que es justo el trabajo manual que este
  bloque venía a quitar.
- **Reutilizar una etiqueta del ciclo.** Mete el run en la máquina de estados.
