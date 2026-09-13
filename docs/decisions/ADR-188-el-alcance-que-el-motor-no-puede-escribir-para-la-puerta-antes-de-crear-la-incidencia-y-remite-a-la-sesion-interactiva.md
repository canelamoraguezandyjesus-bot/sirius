# ADR-188 — Parar antes de crear la incidencia cuando la orden pide tocar lo que el motor no puede escribir

- Estado: PROPUESTO
- Fecha: 2026-09-13
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario

## Nota de arranque (publicada ANTES del primer commit)

Las cuatro preguntas de la disciplina de evidencia (ADR-001), respondidas antes
de tocar código y antes de ver ningún resultado.

1. **¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
   OBSERVAR el fallo que arregla?** El fallo vive en el `git push` del runner,
   una hora después del despacho y en otro proceso: GitHub rechaza la escritura
   y el trabajo muere ahí. El arreglo va en la puerta del despachador, antes de
   crear la incidencia. **No, el sitio del arreglo no puede observar el fallo:**
   cuando la puerta decide, el push no ha ocurrido ni ocurrirá hasta mucho
   después, en una máquina distinta. La puerta no puede *reaccionar* al rechazo;
   solo puede **predecirlo** a partir de lo único que tiene delante, el texto de
   la orden. Por eso lo que hay que medir no es si la puerta se puede escribir
   —se puede— sino con qué precisión ese texto distingue «voy a tocar eso» de
   «no toques eso».
2. **¿Qué NO va a garantizar esto?** No va a garantizar que se pare una orden
   cuyo alcance toque esa carpeta sin nombrar ninguna ruta («arregla el workflow
   del corrector»). No va a impedir que el motor escriba ahí: los permisos no
   cambian, ADR-002 sigue intacto. Y no va a parar solo lo que hay que parar:
   una predicción léxica para de más, y este ADR mide cuánto.
3. **Criterio de parada (decidido ANTES de contar nada).** Si la medida dice que
   el lenguaje natural no separa el alcance declarado de la mera mención sin
   inventar reglas nuevas ronda a ronda, **no se amplía el detector con más
   patrones**: se implementa la variante conservadora que ya sostiene la
   maquinaria de ADR-184, se escribe exactamente cuánto para de más, y se dice
   qué haría falta para cerrarlo de verdad. Un detector que necesita un patrón
   nuevo por cada frase es la misma familia de parche que este repositorio ya
   decidió no seguir.
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** Que cada orden
   declarase su alcance de ficheros de forma explícita y obligatoria, y que la
   puerta comprobase esa declaración en vez de adivinarla. **No está disponible
   para este encargo, y se midió por qué**: el único camino de despacho en
   producción es `.github/workflows/despachar-orden.yml:129`, que llama
   `uv run sirius-despachar "$ORDEN" --ejecutar` y no pasa ningún alcance. Hacer
   obligatoria la declaración exige editar ese fichero — que es exactamente el
   que el motor no puede escribir. El defecto se protege a sí mismo también aquí.

## Contexto y problema

ADR-002 decidió que la credencial de la automatización **no** tenga permiso de
escritura bajo `.github/`, y dejó escrito que los encargos con ese alcance se
resuelvan en sesión interactiva. Ese mismo ADR avisó de que lo que quedaba era
«un **procedimiento operativo manual**, no una garantía», y anotó la corrección
de raíz como trabajo pendiente: «si el olvido llega a ser frecuente, la
corrección de raíz es que la puerta de activación reconozca ese alcance y
rechace antes de arrancar».

El olvido llegó. La incidencia #607 se mandó al ciclo automático con un encargo
cuyo alcance era un fichero de workflow. El encargo hizo el trabajo **entero** —
implementación, doce casos de prueba, siete mutaciones vistas caer, ADR y
validaciones en verde— y al empujar, GitHub rechazó el push por falta de alcance
sobre ficheros de workflow. El commit vivía solo en el runner y murió con él.

Es la familia `regla-que-depende-de-que-alguien-se-acuerde`, la misma que
ADR-174, ADR-179, ADR-182 y ADR-183 han ido cerrando derivando lo vigilado del
repositorio en vez de confiar en la memoria de nadie.

## La medida (criterio declarado ANTES de contar)

**Criterio, escrito antes de mirar el diario:** sobre `diario.jsonl` de la rama
`estado-del-motor`, un encargo «nombra la carpeta» si el texto de su
`peticion_original` o su `objetivo` contiene la subcadena `.github`; y «declara
alcance» si el trabajo que pide se hace **escribiendo** en un fichero de ahí.
La segunda clasificación se hace leyendo las 29 apariciones una por una, y se
publica entera más abajo para que se pueda rebatir.

Sobre los **87 encargos** del diario (13-09-2026):

| | encargos | de ellos, alcance real |
|---|---|---|
| Nombran `.github` | 29 (33 %) | 1 |
| No lo nombran | 58 | 0 |

**Ha ocurrido una sola vez.** Lo digo con esas palabras, como pedía el encargo:
un único encargo de los 87 declaró alcance sobre esa carpeta —
`WI-20260913-075355` («Corrige que la puerta del corrector … En
`.github/workflows/repair-sirius-work.yml`, la condición de la línea 51 …»),
que es la incidencia #607 y acabó en `cancelled` tras pasar por
`needs_decision`. Y se decide igualmente, porque una puerta que depende de que
nadie se despiste es justo la familia que hay que cerrar.

Los otros 28 nombran la carpeta **para excluirla**: «no toques `.github/**`
(ADR-002)», «Ni `.github/**` ni ningún workflow cambian», «PROHIBICIONES DURAS:
no tocar `.github/**`». La mención dice exactamente lo contrario del alcance.

### ¿Basta el objetivo en lenguaje natural? Tres variantes, medidas

Cada variante se corrió contra los 87 encargos reales. «Para» = la puerta
escalaría; «acierta» = el encargo declaraba alcance de verdad.

| Variante | Para | Acierta | Precisión |
|---|---|---|---|
| **A** — la subcadena `.github` aparece | 29 | 1 | 3 % |
| **B** — A + frontera de ruta + la maquinaria de negación de ADR-184 | 9 | 1 | 11 % |
| **C** — B, pero solo si se nombra un **fichero concreto** (con extensión) | 2 | 1 | 50 % |

La frontera de ruta de B quita un falso positivo que A tenía y que no era
lingüístico sino de tokenización: `sirius_engine.ports.github_mirror` contiene
`.github`. La maquinaria de ADR-184 —`_marcador_pedido`, que solo cuenta una
aparición si **no va negada**— quita 19 de las 28 menciones que excluían la
carpeta, sin una línea nueva de detección: son las que llevan `no`, `ni` o `sin`
delante.

Los 8 falsos positivos que B conserva, con la frase exacta que los dispara:

| Encargo | Desenlace real | Lo que dispara |
|---|---|---|
| `WI-20260831-202117` | delivered | «cablearlo exige tocar `.github/workflows/**`, que ADR-002 prohíbe» |
| `WI-20260831-202513` | cancelled | «si cablearlo exigiera tocar `.github/**`, deténte» |
| `WI-20260904-105149` | delivered | «(scripts/automation o `.github/**`), PARA con BLOCKED_BY_DECISION» |
| `WI-20260904-172312` | delivered | «el enganche en `.github/**` (C1b) lo hace el propietario a mano» |
| `WI-20260905-131022` | delivered | «leyendo TODOS los `schedule: cron:` de `.github/workflows/*.yml`» |
| `WI-20260913-132115` | cancelled | «FUERA DE ALCANCE DURO: …; `.github/**` (ADR-002…)» |
| `WI-20260913-142937` | needs_decision | el encargo que describe este mismo defecto |
| `WI-20260913-143715` | active | este mismo encargo |

Son condicionales, paréntesis, encabezados de exclusión y frases que *hablan*
del límite. Separarlos del alcance real pide distinguir leer de escribir,
entender «si … entonces deténte» y reconocer un encabezado de sección: eso es un
intérprete con modelo, que ADR-043 ya dice que este módulo no es. **Aquí es
donde muerde el criterio de parada publicado arriba: no se añade un patrón por
frase.**

**Respuesta a la pregunta del encargo: no, el objetivo en lenguaje natural no
basta para reconocer el alcance declarado.** Su precisión es del 11 %.

## Opciones consideradas

1. **Variante B**, conservadora: para siempre que la orden nombre una ruta bajo
   el prefijo sin negarla.
2. **Variante C**, permisiva: para solo si nombra un fichero concreto.
3. **Alcance de ficheros declarado y obligatorio** en la orden, comprobado por
   la puerta: lo más robusto y lo más caro.
4. No hacer nada y seguir con el procedimiento manual de ADR-002.

## Decisión

**Opción 1 (variante B), como QUINTA causa de sensibilidad del intérprete, con
la causa `permisos_o_credenciales_sensibles`.**

Por qué B y no C, teniendo C mejor precisión: **C es fail-open y B es
fail-closed**, y este detector ya tiene elegido su lado. El módulo lo lleva
escrito desde #324 (H-19): «fail-closed, que avise siempre aunque a veces avise
de más, nunca que una orden sensible se escape por otra rama», y es una decisión
del propietario, no del implementador. C deja pasar «corrige todos los workflows
de `.github/workflows/**`», que es una orden perfectamente escribible y que
moriría en el push igual que #607. Además C está ajustada a un corpus con **un
solo** caso positivo: una regla afinada sobre un ejemplo no es una regla medida,
es una coincidencia con forma de regla. Elegirla sería afirmar más de lo que el
dato sostiene, que es la familia que ADR-001 nombra.

Por qué no la opción 3, que es la que haría el fallo imposible: **no está
disponible para este encargo**, y no por pereza sino por la medida de la
pregunta 4 de la nota de arranque. El único camino de despacho en producción es
`.github/workflows/despachar-orden.yml:129`; hacer obligatoria la declaración
del alcance obliga a editar ese fichero, que es justo lo que el motor no puede
escribir. Un `--alcance` **opcional** sí cabría aquí, pero un flag que hay que
acordarse de poner es literalmente la familia
`regla-que-depende-de-que-alguien-se-acuerde` con otra ropa, y no la cierra:
la deja igual con una casilla más.

La causa es `permisos_o_credenciales_sensibles` —la tercera de las siete de
arquitectura §10— y no `decision_producto_o_arquitectura`, porque la decisión de
producto ya está tomada (ADR-002) y lo que falta no es decidirla otra vez: lo
que falta es un **permiso** que la credencial del motor deliberadamente no
tiene. La escalada le pide al propietario que haga ese trabajo donde el permiso
existe, no que reabra ADR-002.

Y la parada ocurre **antes de crear la incidencia**: la quinta causa produce
`CREAR_Y_ESCALAR`, y `sirius-despachar` sale con código 3 sin llegar a construir
el escritor de GitHub. No se crea incidencia, no se aplica etiqueta y no arranca
ningún ciclo, que es lo que costó una hora de motor en #607.

## Comprobación que la sostiene

- La medida de arriba sale de los 619 registros de
  `git show origin/estado-del-motor:diario.jsonl`, 87 `work_item` distintos, y
  las tres variantes se corrieron contra ese mismo corpus.
- La llamada sin alcance que descarta la opción 3 está en
  `.github/workflows/despachar-orden.yml:129`.
- La quinta causa reutiliza `_marcador_pedido` **sin copiarlo**: la ruta se
  sustituye por una palabra marcadora y se pasa por la misma función que ya
  distingue pedir de prohibir (ADR-184). Que la reutilice es lo que hace que
  «no toques `.github/**`» siga despachándose, y hay una prueba por cada
  dirección.
- Las pruebas nuevas están en `tests/engine/test_intent_interpreter.py` y
  `tests/engine/test_dispatch_cli.py`, y cada regla nueva se vio caer con su
  mutación; las mutaciones y lo que rompió cada una están anotadas en la PR.
- Las cuatro causas anteriores no se tocaron: sus pruebas siguen en verde sin
  retocarlas, y la quinta se consulta **después** de ellas, así que ninguna
  entrada que antes daba una de las cuatro da otra cosa ahora.

## Consecuencias

- Un encargo que nombre una ruta bajo `.github/` sin negarla no llega al ciclo
  automático: queda anotado en `needs_decision`, sin incidencia detrás, y el
  mensaje remite a la sesión interactiva con la orden lista para copiar.
- **Para de más, y está medido:** 8 de 87 encargos del corpus (9 %) se habrían
  parado sin necesitarlo, y 6 de ellos acabaron entregados. La salida no es un
  interruptor: es redactar la mención como exclusión —«no toques `.github/**`»—,
  que es como ya están escritas 19 de las 29 del diario.
- Lo que esto **no** hace: no amplía lo que el motor puede escribir, no reabre
  ADR-002, y no para una orden cuyo alcance toque esa carpeta sin nombrar
  ninguna ruta.
- La corrección de raíz que ADR-002 anotó como pendiente queda **medio hecha**:
  la puerta ya reconoce el alcance cuando la orden lo escribe. Cerrarla del todo
  pide la opción 3, y la opción 3 pide tocar el workflow del despacho: es trabajo
  de sesión interactiva, igual que el que esta puerta desvía.

## Alternativas descartadas y por qué

- **Variante C (solo ficheros concretos)**: mejor precisión sobre el corpus, pero
  fail-open y ajustada a un único positivo. Cambia el lado seguro del detector
  sin una decisión del propietario que lo respalde.
- **Añadir patrones hasta separar los 8 falsos positivos**: condicionales,
  paréntesis y encabezados de exclusión. Es el patrón de parche que el criterio
  de parada publicado arriba prohíbe seguir.
- **`--alcance` opcional en `sirius-despachar`**: no cierra la familia; añade
  una casilla que también se puede olvidar, y en el camino real de producción
  nadie la pondría porque el workflow que despacha no la pasa.

## La lección

- familia: `regla-que-depende-de-que-alguien-se-acuerde`
- sin esto se repetiría: despachar al ciclo automático un encargo cuyo alcance cae donde la credencial del motor no llega, hacer el trabajo entero y perderlo en el push, porque la única regla que lo evitaba vivía en la cabeza de quien despacha.
- lo hace cumplir: `tests/engine/test_intent_interpreter.py`
