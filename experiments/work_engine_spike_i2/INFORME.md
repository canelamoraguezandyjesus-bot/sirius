# Spike I2 — GPT Researcher aislado (S2)

Desechable, como manda el plan. Aquí no hay código de producción: hay
mediciones y un veredicto.

**Fecha:** 25-08-2026 · **Bloque:** S2 del motor · **Entorno:** contenedor de
sesión, 4 CPU, 15 GB RAM, sin GPU, con la red bajo la política del proxy.

## Lo que el plan pedía medir

> «medir el contrato real de GPT Researcher SIN repo […] formato de salida,
> fuentes, calidad, y COSTE real (hoy NO VERIFICADO). **Probar primero el camino
> sin gasto** (modelo local vía Ollama […]); si solo funciona con clave de pago,
> eso es un dato que sube al propietario.»

## Las cuatro preguntas, decididas ANTES de medir

1. ¿Se instala sin pelearse con el entorno?
2. ¿Qué exige para arrancar de fábrica?
3. ¿Existe de verdad un camino **sin ninguna clave**?
4. ¿Se puede medir aquí su calidad, o hace falta otra máquina?

## Criterio de parada, escrito antes de ver resultados

- Si **solo** funciona con claves de pago, se para y sube al propietario como
  decisión de gasto — es literalmente lo que el plan ordena.
- Si el camino sin claves existe pero **no se puede ejercitar aquí**, no se
  declara «funciona»: se declara qué falta y dónde. Un spike que confunde «no
  pude probarlo» con «no funciona» es peor que no hacerlo.
- No se instala nada fuera del spike ni se toca `src/`.

## Medición 1 — Se instala limpio

```
uv pip install gpt-researcher   ->  gpt-researcher 0.15.1
```

Sin compilaciones ni conflictos. Un módulo opcional avisa al importar
(`langchain_mcp_adapters`, para el recuperador MCP) y no estorba a los demás.

## Medición 2 — De fábrica exige dos claves de pago

`config/variables/default.py`, literal:

```python
"RETRIEVER":     "tavily",
"EMBEDDING":     "openai:text-embedding-3-small",
"FAST_LLM":      "openai:gpt-4o-mini",
"SMART_LLM":     "openai:gpt-4.1",
"STRATEGIC_LLM": "openai:o4-mini",
"SCRAPER":       "bs",
"REPORT_SOURCE": "web",
```

Es decir: **clave de OpenAI + clave de Tavily**. Ése es el camino por defecto y
es de pago por uso.

## Medición 3 — El camino sin ninguna clave EXISTE

**Buscadores.** De los dieciséis que trae, **seis no piden clave**:

```
arxiv              SIN CLAVE      bing               necesita clave
custom             SIN CLAVE      bocha              necesita clave
duckduckgo         SIN CLAVE      exa                necesita clave
mcp                SIN CLAVE      google             necesita clave
searx              SIN CLAVE      pubmed_central     necesita clave
semantic_scholar   SIN CLAVE      searchapi          necesita clave
                                  serpapi            necesita clave
                                  serper             necesita clave
                                  tavily             necesita clave
                                  xquik              necesita clave
```

**Modelo y embeddings.** Ollama está soportado en los tres sitios que hacen
falta, no solo en uno:

```
llm_provider/generic/base.py
config/config.py
memory/embeddings.py
```

Que el soporte llegue también a `memory/embeddings.py` es lo que importa: sin
eso, el camino «local» seguiría necesitando la clave de OpenAI para vectorizar,
y no sería un camino sin claves.

**Conclusión de esta medición:** `RETRIEVER=duckduckgo` + LLM y embeddings en
Ollama da una configuración **sin ninguna clave**. El coste deja de ser por
consulta y pasa a ser hardware, exactamente como anticipaba
`BLOQUE_B_SUSCRIPCIONES_O_CLAVES.md`.

## Medición 3b — Y hay una tercera vía que este informe casi se deja fuera

La conclusión de arriba es cierta y **estaba incompleta**. Se escribió mirando
solo la vía local que el plan nombraba, y eso dejaba una falsa disyuntiva:
«o compras hardware, o pagas por consulta».

Contados los proveedores que la herramienta admite: **25**.

```
aimlapi       anthropic     avian         azure_openai  bedrock
cohere        dashscope     deepseek      fireworks     forge
gigachat      google_genai  google_vertexai  groq       huggingface
litellm       minimax       mistralai     netmind       ollama
openai        openrouter    together      vllm_openai   xai
```

Y no se reparten en dos grupos, sino en cuatro:

| | |
|---|---|
| Local, sin claves | `ollama`, `vllm_openai`, `huggingface` — el coste es hardware |
| **Con capa gratuita o muy baratos** | `groq`, `google_genai`, `deepseek`, `openrouter`, `together`, `mistralai`, `fireworks` |
| De pago por uso | `openai`, `anthropic`, `azure_openai`, `bedrock`, `google_vertexai`, `cohere`, `xai` |
| Ni una cosa ni otra | `litellm` es un enrutador hacia los demás, no un proveedor |

**La segunda fila es la que cambia el cálculo.** Un proveedor con capa gratuita
en la nube, más un buscador sin clave, da investigación **sin comprar hardware y
sin las dos APIs que el propietario descartó**. No hay que elegir entre local y
de pago: hay una tercera vía, y es la más barata de estrenar.

Que este informe estuviera a punto de cerrarse sin ella queda dicho aquí y no
disimulado: la primera versión midió lo que el plan nombraba y no lo que la
herramienta ofrecía.

## Medición 4 — Aquí no se puede terminar, y se dice por qué

El recuperador sin clave **se ejecuta**: el código entra, construye la consulta
y sale a la red. Lo que falla es la red de este contenedor:

```
ConnectError('error sending request for url
(https://www.mojeek.com/search?q=cual+es+la+capital+de+Australia)
> tunnel error: unsuccessful'). Failed fetching sources.
resultados: 0
```

No es un fallo de la herramienta: es la política de salida de este entorno.

Y la otra mitad tampoco: **Ollama no se pudo instalar aquí**, el guardián de la
sesión bloquea descargar y ejecutar su instalador. Sin Ollama no hay modelo
local, y sin modelo local no hay nada que medir sobre calidad.

## Veredicto

**Adaptador viable, y por el camino sin gasto.** Las dos condiciones que lo
hacían dudoso están resueltas por medición: hay buscador sin clave, y hay
soporte local para modelo **y** embeddings.

**Coste: hay tres caminos, y dos no cuestan dinero.** El plan preguntaba si
exigía gasto; la respuesta medida es que **no exige nada**:

1. **Local** (`ollama`): sin claves, el coste es hardware.
2. **Capa gratuita en la nube** (`groq`, `google_genai`, `openrouter`…): sin
   hardware y sin las APIs que el propietario descartó. **La más barata de
   estrenar**, y la que este informe casi se deja fuera.
3. De pago por uso: existe, y no hace falta para empezar.

**Lo que este spike NO demuestra, y no hay que leerlo de más:**

- **La calidad.** Ni una sola pregunta se ha respondido de verdad. Que la
  configuración exista no dice nada de si su informe sirve. El propietario pidió
  «por lo menos un 80 %» y ese número **sigue sin medir**.
- **El coste del camino de pago.** No se hizo ninguna llamada facturable, así
  que no hay cifra. Se sabe qué claves pediría, no cuánto costaría.
- **Que las fuentes sean accesibles y trazables**, que es lo que B1 tendrá que
  comprobar en su flujo. Aquí no llegó a haber ninguna.

## Qué haría falta para cerrar S2 del todo

Cualquiera de las dos vías sin gasto, y el plan pide **≥2 configuraciones**
precisamente porque el resultado puede depender del modelo y no del adaptador.
La comparación natural es una de cada:

1. **Una con capa gratuita** (`groq` o `google_genai`) — no necesita máquina
   nueva, así que es la que se puede estrenar antes.
2. **Una local** (`ollama`, modelo pequeño) — en la máquina del propietario o en
   el ordenador pequeño encendido siempre del que habló.
3. Con `RETRIEVER=duckduckgo` en las dos, para que la única variable sea el
   modelo.
4. Una pregunta de **respuesta conocida**, como pide el plan, y comparar.

Eso da el número que falta —el «por lo menos un 80 %»— y cierra el bloque. Cuál
de los proveedores se prueba primero **no lo decide este spike**: es del
propietario, y su decisión de gasto sigue intacta porque ninguna de las dos vías
recomendadas lo tiene.

Eso da el número que falta y cierra el bloque.
