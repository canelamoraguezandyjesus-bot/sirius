# ADR-091 — La disciplina de evidencia alcanza también a responder, no solo a modificar código

- Estado: PROPUESTO
- Fecha: 2026-08-25
- Aprobación: la fusión de la PR por el propietario
- Relacionadas: ADR-001 (disciplina de evidencia), ADR-080 (el registro de
  defectos), ADR-087 (el registro de bloques)

## Contexto y problema

El 25-08-2026, en una sola sesión, el propietario tuvo que decir **tres veces**
la misma frase: *«búscalo, no me lo digas de memoria»*. Tenía razón las tres.

1. Preguntó si ya existía algo de investigación. Se le contestó desde el
   razonamiento y no desde el repositorio, y **casi se construye un duplicado
   del auditor con otro nombre**.
2. Preguntó por el plan de investigación. Estaba escrito —ADR-020 nombraba GPT
   Researcher, y el plan detallaba S2 y B1 con su camino sin gasto— y hubo que
   pedirlo otra vez para que se leyera.
3. Preguntó por las inteligencias que se podían enchufar. La respuesta se dio
   como una disyuntiva —«local o de pago»— que el propio repositorio ya
   desmentía en `AGENT_OPPORTUNITY_MATRIX.md` §6, donde constaba NVIDIA NIM y la
   vía compatible con OpenAI.

La causa **no es el descuido**. Es estructural, y se ve leyendo `AGENTS.md`: su
primera sección se titula **«Antes de modificar código»**. Contestar una
pregunta no es modificar código, así que **ninguna de sus reglas se disparaba**.

Y los guardianes de este repositorio —que son muchos y buenos— comprueban todos
**al final**: la evidencia de la rama, el registro de defectos, el de bloques,
el de decisiones, las pruebas. **Al principio no había nada.**

## Criterio de parada (escrito ANTES de decidir)

**(a)** Si el arreglo se queda en **pedir más cuidado**, no vale. «Ten más
cuidado» no es una regla: es la ausencia de una.

**(b)** Si la regla obliga a buscar **sin decir dónde**, tampoco vale. Una
obligación con fricción se incumple, y se incumple justo cuando hay prisa, que
es cuando más daño hace.

**(c)** Si exige un guardián automático para valer, se para y se piensa otra
cosa: no hay forma de comprobar por programa que alguien leyó antes de hablar.
Esta regla se sostiene sola o no se sostiene.

## Decisión

Se añade a `AGENTS.md` una sección **«Antes de RESPONDER»**, por delante de la
que ya existía:

> Toda afirmación sobre qué está planeado, decidido, medido o pendiente sale de
> leer este repositorio, y se dice **dónde** se leyó. Nunca de memoria, nunca de
> lo que parezca razonable. Si no se encontró, se dice «no lo he encontrado»,
> que es una respuesta legítima; inventarlo no lo es.

Y una segunda obligación, de la misma familia:

> Antes de proponer construir algo, **busca si ya existe**.

**Con el mapa incluido** (criterio b): una tabla de dónde vive cada cosa
—decisiones, bloques del motor, defectos, plan, contrato, agentes, uso del motor
y proveedores de IA con su coste—. Buscar deja de ser una virtud y pasa a ser
barato.

Y dos avisos que ya costaron tiempo el mismo día: que **«los bloques» es
ambiguo** —dos listas que comparten hasta el identificador `B1`— y que **un
documento de estado puede estar caducado**, como `STATUS.md`, que estuvo quince
días diciendo que Sirius 0.1 no estaba aceptado.

## Comprobación que la sostiene

**El agujero se verificó leyendo el fichero**, no suponiéndolo: `AGENTS.md`
tenía 39 líneas y su única sección de precondiciones se titula «Antes de
modificar código». No había ninguna palabra sobre responder, ni sobre buscar
antes de proponer.

**Los tres casos del día están documentados fuera de este ADR**, cada uno con su
rastro: la incidencia #349, cerrada como no realizada porque su encargo partía
de una premisa inventada; el spike `experiments/work_engine_spike_i2/INFORME.md`,
que dejó por escrito que su primera versión midió lo que el plan nombraba y no
lo que la herramienta ofrecía; y el comentario de cierre de #349, que nombra al
auditor como la pieza que ya hacía lo que se iba a duplicar.

```
uv run ruff format --check .   -> 0
uv run ruff check .            -> 0
uv run mypy src tests          -> 0
uv run pytest tests/automation -> 765 passed, 5 skipped
```

## Consecuencias

**Una respuesta ahora cuesta más.** Buscar antes de hablar añade segundos a cada
pregunta, y ése es el precio deliberado: la alternativa medida hoy fue perder
una tarde y estar a punto de construir una pieza duplicada.

**«No lo he encontrado» pasa a ser una respuesta correcta**, y conviene que se
diga en voz alta: sin esa salida, la regla empuja a inventar con más adorno.

**Lo que esta regla NO puede hacer, y hay que decirlo** (criterio c): no hay
guardián que la comprueba. No existe forma de verificar por programa que alguien
leyó antes de responder. Es la primera regla de este repositorio que **depende
de que se cumpla**, no de que se compruebe. Por eso va acompañada del mapa: lo
único que se puede hacer por ella es abaratarla.

## Alternativas descartadas y por qué

- **Pedir más cuidado**: criterio de parada (a). No es una regla.
- **Una regla sin el mapa**: criterio (b). Obliga a buscar y deja al que busca
  averiguar dónde, que es la fricción que la haría fallar bajo prisa.
- **Un guardián automático**: no es construible. Lo más cercano —exigir que toda
  afirmación cite un fichero— convertiría cada respuesta en un formulario y se
  incumpliría por otra vía.
