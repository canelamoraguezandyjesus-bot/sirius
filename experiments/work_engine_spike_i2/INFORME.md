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

**Coste: no es por consulta, es hardware.** El plan preguntaba si exigía gasto;
la respuesta medida es que no exige claves. Lo que exige es una máquina que
aguante un modelo local — la que el propietario ya estaba considerando comprar.

**Lo que este spike NO demuestra, y no hay que leerlo de más:**

- **La calidad.** Ni una sola pregunta se ha respondido de verdad. Que la
  configuración exista no dice nada de si su informe sirve. El propietario pidió
  «por lo menos un 80 %» y ese número **sigue sin medir**.
- **El coste del camino de pago.** No se hizo ninguna llamada facturable, así
  que no hay cifra. Se sabe qué claves pediría, no cuánto costaría.
- **Que las fuentes sean accesibles y trazables**, que es lo que B1 tendrá que
  comprobar en su flujo. Aquí no llegó a haber ninguna.

## Qué haría falta para cerrar S2 del todo

Una máquina con Ollama y salida a internet —la del propietario, o el
ordenador pequeño encendido siempre del que habló—. Con ella:

1. `ollama pull` de un modelo pequeño y otro mediano.
2. `RETRIEVER=duckduckgo`, `FAST_LLM`/`SMART_LLM`/`EMBEDDING` apuntando a Ollama.
3. Una pregunta de **respuesta conocida**, como pide el plan, y comparar.
4. Repetir con el modelo mediano: el plan avisa de que el resultado puede
   depender del modelo y no del adaptador, y pide ≥2 configuraciones.

Eso da el número que falta y cierra el bloque.
