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

El Auditor lee el repositorio y escribe su informe **en un fichero del runner**.
No recibe ninguna credencial capaz de escribir: no porque se le pida que se
porte bien, sino porque los permisos del trabajo acotan el token que se le pasa.
Un trabajo posterior, que no ejecuta ningún modelo y cuyo guion está en el
repositorio y se lee entero, publica ese fichero como comentario.

**La propiedad que hay que defender es una y se puede comprobar:** *ningún
trabajo que ejecute un modelo declara permisos de escritura.* Es el mismo patrón
que ya usa el ciclo de programación —«Claude NUNCA muta etiquetas: escribe un
veredicto en un fichero y `sirius_apply_verdict.sh` lo aplica reverificando»— y
por la misma razón.

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
la herramienta `Write`**, porque tiene que dejar el informe en un fichero. La
tabla de §2 marca «editar código o documentación» como **No**, y `Write` sin
restricción de ruta no distingue el informe del resto del árbol. Lo que impide
el abuso no es la herramienta: es que cualquier escritura en el árbol invalida
el run y lo dice en el comentario. Se prefiere **detectar y anular** antes que
una restricción que no se puede expresar.

**Etiqueta propia, fuera de la máquina de estados.** `sirius:audit-requested` no
aparece en ninguna transición del ciclo y ningún workflow del ciclo reacciona a
ella. Un run del Auditor no es un bloque de trabajo: meterlo en la máquina de
estados acabaría en `failed-safely` sin que nada hubiera fallado, que es
exactamente lo que se evitó al crear la incidencia #154 sin etiquetas.

**El runbook no se copia.** El prompt se construye leyendo
`docs/implementation/AUDITOR_AGENT_V0.md` del propio árbol. Dos copias del mismo
runbook se desincronizan, y la desincronización documental es uno de los
defectos que la auditoría lleva corrigiendo desde el principio.

## Comprobación que la sostiene

`tests/automation/test_auditor_workflow.py`, escrita en la forma que impuso
ADR-015 — **busca lo malo, no lo bueno**, y deriva del YAML real en vez de
copiar listas:

1. Ningún trabajo que use `anthropics/claude-code-action` declara permiso de
   escritura de ninguna clase. Se comprueba sobre **todos** los workflows, con
   una lista de exenciones cerrada para los tres roles del ciclo, que sí escriben
   código porque ese es su cometido.
2. El trabajo del Auditor que puede escribir no ejecuta ningún modelo — la misma
   frontera mirada desde el otro lado.
3. El workflow no reacciona a ninguna etiqueta del ciclo. Las etiquetas del ciclo
   **se derivan de los `if:` de los propios workflows**, no de una lista copiada
   ni del bootstrap: lo que importa es qué dispara de verdad a cada workflow.
4. Ningún workflow del ciclo reacciona a `sirius:audit-requested` — la
   comprobación simétrica, que es la que se olvida.
5. El runbook no está duplicado dentro del workflow.
6. El arnés toma la huella **antes** del modelo y la compara **después**, y el
   paso que recoge el informe **usa** ese veredicto. Sin esa última parte la
   comprobación existiría sin consecuencia.
7. Guardián de la guardiana: si el barrido dejara de encontrar el workflow, sus
   trabajos, o la acción del modelo porque cambió de nombre, las comprobaciones
   anteriores pasarían por vacío afirmando que todo va bien.

Las siete verificadas por mutación en las dos direcciones: dar `issues: write` al
trabajo con modelo, apuntar el Auditor a una etiqueta del ciclo, hacer que el
ciclo reaccione a la del Auditor, copiar texto del runbook dentro del workflow,
renombrar la acción del modelo, quitar la consecuencia de la huella, mover la
huella detrás del modelo, y dejar de mirar las ramas. Cada una pone roja la
prueba que le toca, y solo esa.

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

**No introduce gasto nuevo ni claves nuevas**: usa el mismo
`CLAUDE_CODE_OAUTH_TOKEN` que el ciclo. Nada de Inspect, ni multimodelo, ni
proveedores nuevos — eso sigue bloqueado tras el Bloque B.

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
