# Evidencia — Experimento: el filtro de relevancia, fiel a la corrida del laboratorio

**Rama:** `experimento/filtro-fiel-al-laboratorio` · **Fecha:** 2026-09-01
**Estatuto: EXPERIMENTO. No es una propuesta de fusión.** Existe para que el
propietario pueda ejecutar en su máquina, por primera vez, la memoria de Sirius
con el filtro tal y como se midió, y decidir con lo que vea.

## Por qué existe esta rama

El propietario pidió probar la memoria en casa. Antes de que lo hiciera, se
comprobó qué llamada hace hoy `OllamaRelevanceFilterAdapter` y qué llamada hizo
el laboratorio que midió `29/47` (rama `evidence/adr001-spikes`,
`experiments/adr002/modelo_local/`). **No son la misma llamada.** Seis
diferencias, comprobadas leyendo los dos ficheros:

| | Laboratorio (`puerto.py`, `filtro.py`) | `main` antes de esta rama |
|---|---|---|
| Modelo | `qwen3:4b-instruct` (`puerto.py:73`) | `llama3.2` (`composition_root.py:136`) |
| Espera | `10.0 s` (`puerto.py:91`) | `0.05 s` (`composition_root.py:157`) |
| Extremo | `/api/chat` (`puerto.py:319`) | `/api/generate` |
| Formato | esquema JSON impuesto al generar (`filtro.py:139`) | pedido por escrito en el prompt |
| Modo razonador | `think: False` (`puerto.py:316`) | no se envía |
| `temperature` / `num_ctx` | `0.1` / `8192` (`puerto.py:78-86`) | no se envían |

El propio laboratorio declara que el formato impuesto **no es cosmético**:

> «La versión anterior pedía el formato por escrito en la instrucción y confiaba
> en que el modelo obedeciera. **Con un modelo pequeño eso falla.**»

Y sobre el modo razonador:

> «Sin esto, un modelo de la familia Qwen3 escribe su pensamiento antes de
> contestar y estas tareas pasan de segundos a minutos.»

Con esas seis diferencias, una prueba en casa no habría medido la memoria: habría
medido un filtro distinto del que produjo la cifra que se quiere reproducir.

## Nota de arranque

**Escrita antes de tocar el código, tras el diagnóstico de arriba y antes de
ver ningún resultado de ejecución.**

1. **¿Dónde vive el fallo y dónde va el arreglo?** No hay fallo que arreglar: hay
   una divergencia entre dos implementaciones del mismo filtro. El arreglo va en
   `src/sirius/adapters/ollama_relevance_filter.py` (la llamada) y en las dos
   constantes de `src/sirius/composition_root.py` (modelo y espera).
2. **¿Qué NO garantiza esto?** No garantiza que Sirius alcance `29/47`. El
   laboratorio midió sobre su propio corpus con su propio arnés; aquí se ejecuta
   el camino de producción, con el ámbito real de M16 y sin la siembra. Tampoco
   garantiza latencia: se sube la espera a 30 s **a propósito**, sacrificando
   RNF-003 para poder observar la calidad por separado de la velocidad.
3. **Criterio de parada, fijado antes de medir:** el experimento responde una
   sola pregunta — *¿el filtro llega a ejecutarse y descarta algo?*. Si con este
   cambio el registro sigue mostrando «Filtro de relevancia no disponible, se
   falla abierto», el experimento ha fracasado y la causa no eran estas seis
   diferencias. Si el filtro se ejecuta y descarta, el experimento cumple su
   objetivo **sea cual sea la cifra de aciertos**: esa cifra es un dato para el
   propietario, no un aprobado ni un suspenso de esta rama.
4. **¿Qué haría imposible el fallo, en vez de improbable?** Nada de lo que hay
   aquí. La divergencia volverá a abrirse en cuanto alguien toque una de las dos
   implementaciones sin mirar la otra. Cerrarla de verdad exigiría que la corrida
   congelada del laboratorio y el adaptador de producción compartan una prueba
   que falle cuando dejen de coincidir. **Eso no se hace en esta rama** y queda
   escrito aquí como deuda declarada.

## Qué se cambió

- `ollama_relevance_filter.py`: `/api/chat` con `system` + `user`, esquema JSON
  impuesto (`responden`), `think: False`, `keep_alive: 15m`, `temperature: 0.1`,
  `num_ctx: 8192`, y lectura de `message.content`. La instrucción y el esquema se
  portan **literales** del laboratorio, con su cita en el código.
- `composition_root.py`: modelo `qwen3:4b-instruct`, espera `30.0 s`.
- `tests/unit/test_ollama_relevance_filter.py`: los dobles pasan del sobre
  `{"response": ...}` al `{"message": {"content": ...}}` y de la clave `keep` a
  `responden`. **Ninguna prueba cambia de intención**; solo de protocolo.

## Comprobación

- `uv run ruff format --check` y `uv run ruff check` sobre los ficheros tocados: en verde.
- `uv run mypy` sobre el adaptador: sin incidencias.
- `uv run pytest tests/unit`: **1475 pasan**.
- `uv run pytest tests/integration` (sin `test_local_performance.py`): **512 pasan**.
- `uv run pytest tests/unit/test_ollama_relevance_filter.py`: **12 pasan**. Antes
  de acomodar los dobles fallaba **1**, exactamente la que afirmaba el sobre
  viejo — el cambio de protocolo se vio fallar antes de acomodarlo, que es la
  prueba por mutación que ADR-001 pide.

**Lo que NO se ejecutó, y por qué se dice:** `tests/integration/test_local_performance.py`
(el banco de latencia de RNF-003) y `tests/acceptance/` completo no caben en el
límite de tiempo de la máquina donde se preparó esta rama. El de latencia
**mediría peor a propósito**: subir la espera de `0.05 s` a `30.0 s` sacrifica
RNF-003 deliberadamente, que es justo el objeto del experimento. Ninguna de las
dos se declara verde aquí.

## Lo que esta rama NO hace

- No toca `.github/**` (ADR-002 intacto).
- No toca el banco de 47 casos, el corpus, `resultado_esperado` ni ninguna
  adjudicación.
- No abre la puerta `category_matching_enabled`: sigue cerrada por defecto y solo
  abre con el JSON exacto `true` en la configuración local.
- No propone fusionar nada a `main`. Si el experimento resulta útil, el cambio
  entra por el ciclo normal del motor, con su ADR y su revisión.

---
_Generated by [Claude Code](https://claude.ai/code)_

## Añadido: el medidor con Ollama real (`scripts/medir_banco_con_ollama_real.py`)

**Pregunta que responde, y que nunca se había respondido:** ¿cuánto acierta el
camino real de producción sobre el banco de 47 casos **con el modelo puesto**?

Ninguno de los tres arneses del repositorio la responde: el de examen usa la
grabación congelada, `_ejecutar_banco_paquete_completo` usa un doble que
conserva todo, y el de latencia mide tiempos. El guion reutiliza el arnés de
producción **sin reimplementarlo** —única forma de no medir otra cosa por
accidente— y solo le inyecta el adaptador real. Para permitirlo,
`_ejecutar_banco_paquete_completo` gana un parámetro opcional que por defecto
conserva el doble de siempre: ninguna prueba existente cambia de comportamiento.

**Criterio de parada, escrito antes de medir:** una cifra solo vale si el
contador de rendiciones es **cero**. Con una sola rendición, la medición mezcla
consultas filtradas con consultas sin filtrar y no significa nada.

**Defecto encontrado y corregido durante la construcción, declarado porque
importa:** la primera versión contaba las rendiciones leyendo el registro, y
devolvía **cero** aunque el filtro se rindiera en todas las consultas —
`alembic` reconfigura `logging` al migrar y desactiva los `logger` existentes.
Un cero falso ahí es peor que no tener la cifra: haría pasar por válida una
medición inválida, que es exactamente el error que este experimento existe para
evitar. Se sustituyó por un envoltorio que cuenta por identidad del objeto
devuelto, que es exacta: el adaptador devuelve la MISMA tupla al fallar abierto
y una tupla NUEVA cuando el modelo contesta.

**Comprobación:** ejecutado en una máquina sin Ollama, informa `47 llamadas,
40 rendiciones` y declara las cifras no válidas. Antes del arreglo informaba
`0 rendiciones` sobre esa misma ejecución.
