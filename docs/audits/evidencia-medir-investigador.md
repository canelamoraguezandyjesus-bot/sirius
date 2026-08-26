# Evidencia — cerrar S2: medir de verdad la calidad del investigador

Rama `medir-investigador`, 26-08-2026. La nota de arranque, con las cuatro
preguntas y el criterio de parada, se publicó **antes del primer commit** en la
incidencia #258. Este fichero recoge las mediciones que la sostienen.

## Afirmación

El spike I2 (#351) dejó S2 en `pendiente` con esta frase: *«ni una sola pregunta
se ha respondido de verdad»*. Falta el número que el propietario pidió —«por lo
menos un 80 %»— y este bloque lo produce comparando **dos** configuraciones,
NVIDIA y Google AI Studio, con el mismo buscador y el mismo banco de preguntas,
para que la única variable sea el modelo.

## Criterio de parada (publicado en #258 antes de medir nada)

- **(a)** Si hiciera falta una clave de las dos APIs que el propietario descartó,
  se para y se le sube. Ninguna de las dos vías elegidas la pide.
- **(b)** Si acaba midiéndose **una sola** configuración, no vale: el plan pide
  ≥2 porque el resultado puede depender del modelo y no del adaptador.
- **(c)** Si el arnés no puede distinguir «respondió mal» de «no llegó a
  intentarlo», se para y se rehace.

## Comprobaciones

### 1. Aquí no se puede medir: la red está cerrada

```
000  https://duckduckgo.com/
000  https://html.duckduckgo.com/html/?q=capital+de+australia
000  https://api.groq.com/openai/v1/models
000  https://integrate.api.nvidia.com/v1/models
```

`000` es «no hubo conexión», no «respondió mal» — coincide con lo que el spike
ya vio (`tunnel error: unsuccessful`). **La medición solo puede correr en
Actions.** No es una preferencia de diseño: es la única forma de que exista.

### 2. La versión nueva de la herramienta está rota

```
$ pip install gpt-researcher   # trae 0.16.0
$ python -c "import gpt_researcher"
File ".../gpt_researcher/actions/query_processing.py", line 6, in <module>
    def _normalize_sub_queries(parsed: Any, fallback_query: str) -> List[str]:
NameError: name 'Any' is not defined
```

Usa `Any` sin importarlo, en su propio código. La **0.15.1** —la que midió el
spike— importa limpio y expone `GPTResearcher`. Queda fijada a esa versión, y
`medir_investigador.py` se **para** si encuentra otra: un número medido sobre una
versión que nadie ha comprobado no vale nada.

### 3. Un modelo gratis no basta: hace falta que vectorice

`EMBEDDING` por defecto es `openai:text-embedding-3-small`. Proveedores que la
herramienta admite para vectorizar, leídos de `memory/embeddings.py`:

```
aimlapi azure_openai bedrock cohere custom dashscope fireworks gigachat
google_genai google_vertexai huggingface minimax mistralai netmind nomic
ollama openai openrouter together voyageai
```

**`groq` no está.** Es buen proveedor de modelo y con capa gratuita, pero
exigiría una **segunda** cuenta solo para vectorizar. `google_genai` sí está en
las dos listas, y NVIDIA entra por la vía compatible con OpenAI —`openai:` o
`custom:` con `OPENAI_BASE_URL`—, así que **una sola cuenta cubre las dos
mitades** en ambos casos. Esto no estaba en el spike y habría costado una noche.

### 4. La trampa que habría falseado la comparación entera

Tanto el proveedor de modelo (`llm_provider/generic/base.py`) como el de
vectorización (`memory/embeddings.py`) leen `OPENAI_BASE_URL`:

```
# Support custom OpenAI-compatible APIs via OPENAI_BASE_URL
if "openai_api_base" not in kwargs and os.environ.get("OPENAI_BASE_URL"):
    kwargs["openai_api_base"] = os.environ["OPENAI_BASE_URL"]
```

Es decir: **las dos configuraciones se pisan las variables**. NVIDIA secuestra
`OPENAI_BASE_URL` para todo el proceso, así que dos configuraciones en el mismo
entorno acabarían hablando con el mismo servidor **y el informe saldría
precioso**. Un verde que mide dos veces lo mismo no falla: miente. Por eso cada
configuración corre en un subproceso con entorno construido desde cero, y cada
una declara en su salida contra qué servidor habló de verdad.

## Lo que esto NO mide, dicho antes de que nadie lo lea de más

- **El precio en dinero.** No hay forma de saberlo desde aquí, y no se inventa.
  Se medirán tiempo, fuentes y aciertos; los euros están en las páginas de
  tarifas de cada proveedor.
- **La calidad de la redacción.** La corrección busca cadenas obligatorias en el
  informe. Es cruda a propósito: un corrector fino exigiría otro modelo juzgando,
  y entonces mediríamos al juez. El informe entero se conserva para que quien
  dude lo lea.
- **Que el número sea bueno.** Este bloque produce el porcentaje, no lo aprueba.
  Si sale por debajo del 80 %, eso también cierra S2 — con un «no».

---

## Segunda ronda: la refutación tumbó el diseño (26-08-2026)

Tres refutadores con lentes distintas —comparación falsa, verde falso, y
secretos y coste— sobre lo construido. **27 hallazgos, 8 de gravedad alta.**

### La raíz, y por qué no se parchean uno a uno

**Seis de los ocho graves son el mismo defecto**, así que se aplica la regla de
las dos rondas de ADR-001: se para de parchear y se busca la raíz.

**La raíz: el arnés medía lo que se le PEDÍA, nunca lo que OCURRÍA.**

| lo que declaraba | de dónde salía de verdad |
|---|---|
| «habló con este servidor» | releía la variable de entorno que el padre acababa de escribir |
| «midió 5 preguntas» | contaba entradas, aunque las cinco hubieran reventado |
| «trajo N fuentes» | se imprimía en una columna y no condicionaba nada |
| «comparación concluyente» | miraba un código de salida que era 0 pase lo que pase |

### El hallazgo que lo demuestra, verificado a mano y no aceptado de palabra

```
$ sed -n '10,12p' .../gpt_researcher/retrievers/duckduckgo/duckduckgo.py
        check_pkg('ddgs')
        from ddgs import DDGS

$ python -c "import importlib.metadata as m; print(m.requires('gpt-researcher'))"
  ... 'duckduckgo-search>=4.1.1' ...

$ python -c "import ddgs"
ModuleNotFoundError: No module named 'ddgs'
```

Importa un paquete y declara otro. **El buscador no puede funcionar.**

Consecuencia exacta: los dos proveedores habrían escrito sus informes de memoria
del modelo, con cero fuentes, y el arnés habría publicado una comparación
concluyente. Y como **ninguna de las cinco preguntas del banco obliga a buscar**
—el propio fichero declaraba ese criterio tres líneas más arriba y lo incumplía—
habrían salido al 100 %.

No falla: **miente**. Y habría gastado cuota de las dos APIs del propietario.

### Lo que se hizo al recibir la refutación

**El disparador se desactivó de verdad, no con un aviso.** `workflow_dispatch`
se sustituyó por `workflow_call` sin llamantes: el fichero sigue siendo válido y
**no existe ningún botón** que pueda gastar cuota. Un aviso en un comentario que
se ignora con un clic no es una salvaguarda. Comprobado:

```
disparadores reales del fichero: ['workflow_call']
```

El cableado que SÍ está medido se conserva, porque sirve: Python 3.12 (con 3.14
`gpt-researcher` no instala — fija `numpy==2.2.6`, sin rueda `cp314`),
`langchain-google-genai` que no viene incluido y sin el cual Google fallaría por
importación, y un tope de 80 minutos que no rompe el margen de dos minutos de D1.

### Lo que falta para reponerlo

1. **Prueba de vida antes de gastar cuota**: una búsqueda real que exija
   fuentes > 0 y una llamada real por proveedor. Si falla, no se mide nada.
2. **Veredicto cerrado sobre evidencia**: sin fuentes no hay medición; una
   pregunta con error nunca entra en un resultado concluyente.
3. **Banco rehecho**: preguntas que exijan buscar, y corrección con límite de
   palabra — hoy `Rust` se aprueba con «trust», comprobado.

Los hallazgos que no son de esta familia —el `-e` del shell que hace inalcanzables
tres veredictos, la clave que puede viajar intacta en el JSON del artefacto, el
plazo que tira la cuota ya gastada— se arreglan aparte, cada uno con su guardián.
